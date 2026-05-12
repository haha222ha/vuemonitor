import uuid
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert_rule import AlertRule, AlertEvent
from app.services.alert_service import alert_service
from app.core.cache import cache_get, cache_set

import structlog

logger = structlog.get_logger()

SUPPORTED_METRICS = {
    "price": {"label": "价格", "unit": "元"},
    "sales_count": {"label": "销量", "unit": "件"},
    "monthly_sales": {"label": "月销量", "unit": "件"},
    "rating": {"label": "评分", "unit": "分"},
    "review_count": {"label": "评论数", "unit": "条"},
    "favorite_count": {"label": "收藏数", "unit": "个"},
    "price_change_pct": {"label": "价格变化率", "unit": "%"},
    "sales_change_pct": {"label": "销量变化率", "unit": "%"},
    "error_rate": {"label": "采集错误率", "unit": "%"},
    "response_time": {"label": "响应时间", "unit": "ms"},
    "queue_length": {"label": "队列长度", "unit": "个"},
    "risk_score": {"label": "风控分数", "unit": "分"},
}

SUPPORTED_OPERATORS = {
    "gt": lambda v, t: v > t,
    "gte": lambda v, t: v >= t,
    "lt": lambda v, t: v < t,
    "lte": lambda v, t: v <= t,
    "eq": lambda v, t: v == t,
    "neq": lambda v, t: v != t,
    "change_up": lambda v, t: v >= t,
    "change_down": lambda v, t: v <= -t,
}

SEVERITY_LEVELS = ["info", "warning", "critical"]


class AlertRuleEngine:
    def __init__(self):
        self._metric_providers: dict[str, Any] = {}

    def register_metric_provider(self, metric_name: str, provider: Any):
        self._metric_providers[metric_name] = provider

    async def evaluate_rule(self, rule: AlertRule, db: AsyncSession) -> AlertEvent | None:
        if not rule.is_active:
            return None

        if rule.last_triggered_at:
            cooldown = timedelta(minutes=rule.cooldown_minutes)
            if datetime.now(timezone.utc) - rule.last_triggered_at < cooldown:
                return None

        metric_value = await self._get_metric_value(rule, db)
        if metric_value is None:
            return None

        operator_fn = SUPPORTED_OPERATORS.get(rule.operator)
        if not operator_fn:
            logger.warning("alert_engine_unknown_operator", operator=rule.operator)
            return None

        triggered = operator_fn(metric_value, rule.threshold)
        if not triggered:
            return None

        event = AlertEvent(
            rule_id=rule.id,
            user_id=rule.user_id,
            severity=rule.severity,
            title=f"{rule.name} 触发告警",
            detail=f"指标 {SUPPORTED_METRICS.get(rule.metric, {}).get('label', rule.metric)} 当前值 {metric_value}，阈值 {rule.threshold}，操作符 {rule.operator}",
            metric_value=metric_value,
            threshold_value=rule.threshold,
            context={
                "rule_name": rule.name,
                "rule_type": rule.rule_type,
                "metric": rule.metric,
                "operator": rule.operator,
                "window_minutes": rule.window_minutes,
            },
        )
        db.add(event)

        rule.last_triggered_at = datetime.now(timezone.utc)
        rule.trigger_count += 1
        await db.commit()
        await db.refresh(event)

        await self._dispatch_alert(rule, event)

        return event

    async def evaluate_all_rules(self, user_id: uuid.UUID, db: AsyncSession) -> list[AlertEvent]:
        result = await db.execute(
            select(AlertRule).where(
                AlertRule.user_id == user_id,
                AlertRule.is_active == True,
            )
        )
        rules = result.scalars().all()

        events = []
        for rule in rules:
            try:
                event = await self.evaluate_rule(rule, db)
                if event:
                    events.append(event)
            except Exception as e:
                logger.error("alert_engine_evaluate_failed", rule_id=str(rule.id), error=str(e))

        return events

    async def _get_metric_value(self, rule: AlertRule, db: AsyncSession) -> float | None:
        cache_key = f"alert:metric:{rule.user_id}:{rule.metric}:{rule.id}"
        cached = await cache_get(cache_key)
        if cached is not None:
            return float(cached)

        provider = self._metric_providers.get(rule.metric)
        if provider:
            try:
                value = await provider(rule.user_id, rule.filters, db)
                if value is not None:
                    await cache_set(cache_key, value, ttl_seconds=60)
                    return float(value)
            except Exception as e:
                logger.error("alert_engine_metric_provider_failed", metric=rule.metric, error=str(e))
            return None

        return await self._default_metric_query(rule, db)

    async def _default_metric_query(self, rule: AlertRule, db: AsyncSession) -> float | None:
        from app.models.product import Product, ProductFeature

        if rule.metric in ("price", "sales_count", "monthly_sales", "rating", "review_count", "favorite_count"):
            product_id = rule.filters.get("product_id") if rule.filters else None
            if not product_id:
                return None

            result = await db.execute(
                select(ProductFeature)
                .where(ProductFeature.product_id == uuid.UUID(product_id))
                .order_by(ProductFeature.collected_at.desc())
                .limit(2)
            )
            features = result.scalars().all()
            if not features:
                return None

            latest = features[0]
            value = getattr(latest, rule.metric, None)
            if value is not None:
                return float(value)

        elif rule.metric in ("price_change_pct", "sales_change_pct"):
            product_id = rule.filters.get("product_id") if rule.filters else None
            if not product_id:
                return None

            result = await db.execute(
                select(ProductFeature)
                .where(ProductFeature.product_id == uuid.UUID(product_id))
                .order_by(ProductFeature.collected_at.desc())
                .limit(2)
            )
            features = result.scalars().all()
            if len(features) < 2:
                return None

            latest, prev = features[0], features[1]
            base_metric = "price" if rule.metric == "price_change_pct" else "sales_count"
            latest_val = getattr(latest, base_metric, None)
            prev_val = getattr(prev, base_metric, None)

            if latest_val is not None and prev_val is not None and prev_val != 0:
                return round((latest_val - prev_val) / prev_val * 100, 2)

        return None

    async def _dispatch_alert(self, rule: AlertRule, event: AlertEvent):
        channels = rule.channels or {}
        level_map = {"info": "info", "warning": "warning", "critical": "error"}
        level = level_map.get(event.severity, "warning")

        await alert_service.send_alert(
            level=level,
            title=event.title,
            detail=event.detail,
            extra={
                "rule_id": str(rule.id),
                "event_id": str(event.id),
                "metric": rule.metric,
                "metric_value": event.metric_value,
                "threshold": event.threshold_value,
                "severity": event.severity,
            },
        )

        if channels.get("webhook"):
            try:
                import httpx
                async with httpx.AsyncClient(timeout=10) as client:
                    await client.post(
                        channels["webhook"],
                        json={
                            "event_id": str(event.id),
                            "rule_name": rule.name,
                            "severity": event.severity,
                            "title": event.title,
                            "detail": event.detail,
                            "metric_value": event.metric_value,
                            "threshold": event.threshold_value,
                            "timestamp": event.created_at.isoformat() if event.created_at else None,
                        },
                    )
            except Exception as e:
                logger.error("alert_webhook_failed", error=str(e))

        if channels.get("email"):
            recipients = channels["email"] if isinstance(channels["email"], list) else [channels["email"]]
            for recipient in recipients:
                try:
                    from app.services.email_service import EmailService
                    email_service = EmailService()
                    await email_service.send_email(
                        recipient,
                        f"[{event.severity.upper()}] {event.title}",
                        event.detail,
                    )
                except Exception:
                    pass

    async def get_events(
        self,
        user_id: uuid.UUID,
        db: AsyncSession,
        severity: str | None = None,
        acknowledged: bool | None = None,
        limit: int = 50,
    ) -> list[AlertEvent]:
        query = select(AlertEvent).where(AlertEvent.user_id == user_id)
        if severity:
            query = query.where(AlertEvent.severity == severity)
        if acknowledged is not None:
            query = query.where(AlertEvent.is_acknowledged == acknowledged)
        query = query.order_by(AlertEvent.created_at.desc()).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def acknowledge_event(self, event_id: uuid.UUID, user_id: uuid.UUID, db: AsyncSession) -> bool:
        result = await db.execute(
            select(AlertEvent).where(AlertEvent.id == event_id, AlertEvent.user_id == user_id)
        )
        event = result.scalar_one_or_none()
        if not event:
            return False
        event.is_acknowledged = True
        event.acknowledged_at = datetime.now(timezone.utc)
        await db.commit()
        return True


alert_rule_engine = AlertRuleEngine()
