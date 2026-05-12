import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.monitor import MonitorRule, Notification
from app.models.product import Product, ProductFeature
from app.models.user import User
from app.ws.manager import manager
from app.services.email_service import email_service

logger = logging.getLogger(__name__)

RULE_TYPE_LABELS = {
    "price_drop": "价格下跌",
    "sales_surge": "销量激增",
    "stock_change": "库存变化",
    "rating_drop": "评分下降",
    "custom": "自定义规则",
}


class RuleEvaluator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate_all_active_rules(self) -> int:
        result = await self.db.execute(
            select(MonitorRule).where(MonitorRule.is_active == True)
        )
        rules = result.scalars().all()
        triggered_count = 0

        for rule in rules:
            try:
                triggered = await self._evaluate_rule(rule)
                if triggered:
                    triggered_count += 1
            except Exception as e:
                logger.error(f"Rule evaluation error for rule {rule.id}: {e}")

        return triggered_count

    async def _evaluate_rule(self, rule: MonitorRule) -> bool:
        latest_feature = await self._get_latest_feature(rule.product_id)
        if not latest_feature:
            return False

        prev_feature = await self._get_prev_feature(rule.product_id, latest_feature.collected_at)
        if not prev_feature:
            return False

        matched = self._check_conditions(rule, latest_feature, prev_feature)
        if not matched:
            return False

        product_result = await self.db.execute(
            select(Product).where(Product.id == rule.product_id)
        )
        product = product_result.scalar_one_or_none()
        product_name = product.product_name if product else "未知商品"

        await self._create_notification(
            user_id=rule.user_id,
            rule=rule,
            product_name=product_name,
            latest=latest_feature,
            prev=prev_feature,
        )

        rule.last_triggered_at = datetime.now(timezone.utc)
        rule.trigger_count = (rule.trigger_count or 0) + 1

        return True

    async def _get_latest_feature(self, product_id: uuid.UUID) -> ProductFeature | None:
        result = await self.db.execute(
            select(ProductFeature)
            .where(ProductFeature.product_id == product_id)
            .order_by(ProductFeature.collected_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _get_prev_feature(
        self, product_id: uuid.UUID, after_collected_at: datetime
    ) -> ProductFeature | None:
        result = await self.db.execute(
            select(ProductFeature)
            .where(
                ProductFeature.product_id == product_id,
                ProductFeature.collected_at < after_collected_at,
            )
            .order_by(ProductFeature.collected_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    def _check_conditions(
        self,
        rule: MonitorRule,
        latest: ProductFeature,
        prev: ProductFeature,
    ) -> bool:
        conditions = rule.conditions or {}
        rule_type = rule.rule_type

        if rule_type == "price_drop":
            return self._check_price_drop(conditions, latest, prev)
        elif rule_type == "sales_surge":
            return self._check_sales_surge(conditions, latest, prev)
        elif rule_type == "stock_change":
            return self._check_stock_change(conditions, latest, prev)
        elif rule_type == "rating_drop":
            return self._check_rating_drop(conditions, latest, prev)
        elif rule_type == "custom":
            return self._check_custom(conditions, latest, prev)

        return False

    def _check_price_drop(
        self, conditions: dict, latest: ProductFeature, prev: ProductFeature
    ) -> bool:
        if latest.price is None or prev.price is None:
            return False
        if prev.price == 0:
            return False

        threshold_pct = conditions.get("threshold_pct", 5)
        price_drop_pct = float((prev.price - latest.price) / prev.price * 100)
        return price_drop_pct >= threshold_pct

    def _check_sales_surge(
        self, conditions: dict, latest: ProductFeature, prev: ProductFeature
    ) -> bool:
        if latest.sales_count is None or prev.sales_count is None:
            return False
        if prev.sales_count == 0:
            return latest.sales_count > 0

        threshold_pct = conditions.get("threshold_pct", 50)
        sales_increase_pct = float(
            (latest.sales_count - prev.sales_count) / prev.sales_count * 100
        )
        return sales_increase_pct >= threshold_pct

    def _check_stock_change(
        self, conditions: dict, latest: ProductFeature, prev: ProductFeature
    ) -> bool:
        if latest.stock_status is None or prev.stock_status is None:
            return False
        return latest.stock_status != prev.stock_status

    def _check_rating_drop(
        self, conditions: dict, latest: ProductFeature, prev: ProductFeature
    ) -> bool:
        if latest.rating is None or prev.rating is None:
            return False

        threshold = conditions.get("threshold", 0.5)
        rating_drop = float(prev.rating - latest.rating)
        return rating_drop >= threshold

    def _check_custom(
        self, conditions: dict, latest: ProductFeature, prev: ProductFeature
    ) -> bool:
        field = conditions.get("field")
        operator = conditions.get("operator", "gt")
        value = conditions.get("value")

        if not field or value is None:
            return False

        latest_val = getattr(latest, field, None)
        if latest_val is None:
            return False

        if isinstance(latest_val, Decimal):
            latest_val = float(latest_val)
        if isinstance(value, (int, float)):
            pass
        else:
            try:
                value = float(value)
            except (ValueError, TypeError):
                return str(latest_val) == str(value)

        if operator == "gt":
            return latest_val > value
        elif operator == "gte":
            return latest_val >= value
        elif operator == "lt":
            return latest_val < value
        elif operator == "lte":
            return latest_val <= value
        elif operator == "eq":
            return latest_val == value
        elif operator == "neq":
            return latest_val != value

        return False

    async def _create_notification(
        self,
        user_id: uuid.UUID,
        rule: MonitorRule,
        product_name: str,
        latest: ProductFeature,
        prev: ProductFeature,
    ) -> Notification:
        rule_label = RULE_TYPE_LABELS.get(rule.rule_type, rule.rule_type)
        content = self._build_notification_content(
            rule, product_name, latest, prev
        )

        notification = Notification(
            user_id=user_id,
            type="monitor_triggered",
            title=f"[{rule_label}] {product_name}",
            content=content,
            related_id=rule.product_id,
            related_type="product",
        )
        self.db.add(notification)
        await self.db.flush()

        await manager.send_to_user(str(user_id), {
            "type": "monitor:triggered",
            "data": {
                "notification_id": str(notification.id),
                "rule_id": str(rule.id),
                "rule_name": rule.rule_name,
                "rule_type": rule.rule_type,
                "product_id": str(rule.product_id),
                "product_name": product_name,
                "title": notification.title,
                "content": content,
            },
            "ts": datetime.now(timezone.utc).isoformat(),
        })

        try:
            user_result = await self.db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            if user and user.email and user.email_notify_enabled:
                await email_service.send_monitor_triggered_email(
                    to_email=user.email,
                    rule_name=rule.rule_name,
                    product_name=product_name,
                    trigger_detail=content,
                )
        except Exception as e:
            logger.error(f"Failed to send email notification for rule {rule.id}: {e}")

        return notification;

    def _build_notification_content(
        self,
        rule: MonitorRule,
        product_name: str,
        latest: ProductFeature,
        prev: ProductFeature,
    ) -> str:
        rule_type = rule.rule_type

        if rule_type == "price_drop":
            old_price = float(prev.price) if prev.price else 0
            new_price = float(latest.price) if latest.price else 0
            drop_pct = ((old_price - new_price) / old_price * 100) if old_price > 0 else 0
            return f"商品「{product_name}」价格从 ¥{old_price:.2f} 降至 ¥{new_price:.2f}，降�?{drop_pct:.1f}%"

        elif rule_type == "sales_surge":
            old_sales = prev.sales_count or 0
            new_sales = latest.sales_count or 0
            increase = new_sales - old_sales
            surge_pct = (increase / old_sales * 100) if old_sales > 0 else 0
            return f"商品「{product_name}」销量从 {old_sales} 增至 {new_sales}，增幅{surge_pct:.1f}%"

        elif rule_type == "stock_change":
            return f"商品「{product_name}」库存状态从「{prev.stock_status}」变为「{latest.stock_status}」"

        elif rule_type == "rating_drop":
            old_rating = float(prev.rating) if prev.rating else 0
            new_rating = float(latest.rating) if latest.rating else 0
            return f"商品「{product_name}」评分从 {old_rating:.1f} 降至 {new_rating:.1f}"

        else:
            return f"商品「{product_name}」触发了监控规则「{rule.rule_name}」"
