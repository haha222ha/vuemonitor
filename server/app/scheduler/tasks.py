import logging
import statistics
import uuid
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.collect.engine import CollectEngine
from app.core.database import async_session_factory
from app.models.admin import ProxyPool
from app.models.collect import CollectTask
from app.ws.manager import manager
logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def process_pending_tasks():
    async with async_session_factory() as db:
        result = await db.execute(
            select(CollectTask)
            .where(CollectTask.status == "pending")
            .order_by(CollectTask.priority.asc(), CollectTask.created_at.asc())
            .limit(5)
        )
        tasks = result.scalars().all()

        for task in tasks:
            try:
                async with async_session_factory() as task_db:
                    engine = CollectEngine(task_db)
                    summary = await engine.execute_task(task.id)
                    await task_db.commit()

                await manager.send_to_user(str(task.user_id), {
                    "type": "collect:completed",
                    "data": {"task_id": str(task.id), "summary": summary},
                    "ts": datetime.now(UTC).isoformat(),
                })
            except Exception as e:
                logger.error(f"Task {task.id} failed: {e}")


async def check_proxy_health():
    async with async_session_factory() as db:
        result = await db.execute(
            select(ProxyPool).where(ProxyPool.status == "available")
        )
        proxies = result.scalars().all()

        for proxy in proxies:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://httpbin.org/ip",
                        proxy=f"{proxy.protocol}://{proxy.ip}:{proxy.port}",
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status == 200:
                            proxy.health_score = min(100, proxy.health_score + 5)
                            proxy.fail_count = 0
                        else:
                            proxy.health_score = max(0, proxy.health_score - 15)
                            proxy.fail_count += 1
            except Exception:
                proxy.health_score = max(0, proxy.health_score - 20)
                proxy.fail_count += 1

            if proxy.health_score <= 0 or proxy.fail_count >= 5:
                proxy.status = "banned"

            proxy.last_checked_at = datetime.now(UTC)

        await db.commit()


async def cleanup_expired_tokens():
    async with async_session_factory() as db:
        from app.models.user import RefreshToken
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.expires_at < datetime.now(UTC))
        )
        expired = result.scalars().all()
        for token in expired:
            await db.delete(token)
        await db.commit()
        logger.info(f"Cleaned up {len(expired)} expired refresh tokens")


async def evaluate_monitor_rules():
    from app.monitor.evaluator import RuleEvaluator

    async with async_session_factory() as db:
        try:
            evaluator = RuleEvaluator(db)
            triggered_count = await evaluator.evaluate_all_active_rules()
            await db.commit()
            if triggered_count > 0:
                logger.info(f"Monitor rules evaluated: {triggered_count} rules triggered")
        except Exception as e:
            logger.error(f"Monitor rule evaluation failed: {e}")


async def downgrade_expired_plans():
    async with async_session_factory() as db:
        from app.models.license import LicenseCode
        from app.models.user import User
        now = datetime.now(UTC)

        result = await db.execute(
            select(User).where(
                User.plan != "free",
                User.plan_expires_at is not None,
                User.plan_expires_at < now,
            )
        )
        expired_users = result.scalars().all()

        downgraded_count = 0
        for user in expired_users:
            user.plan = "free"
            user.plan_expires_at = None
            downgraded_count += 1

            await manager.send_to_user(str(user.id), {
                "type": "plan:downgraded",
                "data": {"reason": "套餐已过期", "current_plan": "free"},
                "ts": now.isoformat(),
            })

        if downgraded_count > 0:
            await db.commit()
            logger.info(f"Auto-downgraded {downgraded_count} expired plan users to free")

    async with async_session_factory() as db:
        from app.models.license import LicenseCode
        result = await db.execute(
            select(LicenseCode).where(
                LicenseCode.status == "active",
                LicenseCode.expires_at is not None,
                LicenseCode.expires_at < now,
            )
        )
        expired_licenses = result.scalars().all()

        for lic in expired_licenses:
            lic.status = "expired"

        if expired_licenses:
            await db.commit()
            logger.info(f"Marked {len(expired_licenses)} licenses as expired")


async def compute_feature_rankings():
    from app.feature.cloud_engine import CloudFeatureEngine

    async with async_session_factory() as db:
        try:
            engine = CloudFeatureEngine(db)
            count = await engine.compute_all_rankings()
            await db.commit()
            if count > 0:
                logger.info(f"Feature rankings computed for {count} products")
        except Exception as e:
            logger.error(f"Feature ranking computation failed: {e}")


async def auto_detect_anomalies():
    from app.models.product import Product
    from app.models.product import ProductFeature
    from app.models.alert_rule import AlertEvent

    METRICS = ["price", "sales_count"]
    Z_THRESHOLD = 2.5
    DAYS = 7
    MIN_SAMPLES = 5

    since = datetime.now(UTC) - timedelta(days=DAYS)

    async with async_session_factory() as db:
        result = await db.execute(
            select(Product).where(Product.is_active == 1)
        )
        products = result.scalars().all()

        total_anomalies = 0

        for p in products:
            feat_result = await db.execute(
                select(ProductFeature)
                .where(
                    ProductFeature.product_id == p.id,
                    ProductFeature.collected_at >= since,
                )
                .order_by(ProductFeature.collected_at.desc())
                .limit(30)
            )
            features = feat_result.scalars().all()

            if len(features) < MIN_SAMPLES:
                continue

            for metric in METRICS:
                values = []
                for f in features:
                    v = getattr(f, metric, None)
                    if v is not None:
                        values.append(float(v))

                if len(values) < MIN_SAMPLES:
                    continue

                latest_val = values[0]
                historical = values[1:]

                if len(historical) < 2:
                    continue

                mean_val = statistics.mean(historical)
                stdev_val = statistics.stdev(historical)

                if stdev_val == 0:
                    continue

                z_score = (latest_val - mean_val) / stdev_val

                if abs(z_score) < Z_THRESHOLD:
                    continue

                direction = "up" if z_score > 0 else "down"
                severity = "critical" if abs(z_score) >= 3.0 else "warning"

                metric_labels = {"price": "价格", "sales_count": "销量"}
                direction_labels = {"up": "异常升高", "down": "异常下降"}

                recent_event = await db.execute(
                    select(AlertEvent).where(
                        AlertEvent.user_id == p.user_id,
                        AlertEvent.is_acknowledged == False,
                        AlertEvent.created_at >= datetime.now(UTC) - timedelta(hours=24),
                    )
                )
                recent = recent_event.scalars().first()
                if recent and recent.context:
                    ctx = recent.context if isinstance(recent.context, dict) else {}
                    if ctx.get("product_id") == str(p.id) and ctx.get("metric") == metric:
                        continue

                event = AlertEvent(
                    rule_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                    user_id=p.user_id,
                    severity=severity,
                    title=f"{p.product_name or p.platform_product_id} {metric_labels.get(metric, metric)}{direction_labels[direction]}",
                    detail=f"商品「{p.product_name or p.platform_product_id}」的{metric_labels.get(metric, metric)}出现异常{direction_labels[direction]}，当前值 {latest_val:.2f}，历史均值 {mean_val:.2f}，Z-score {z_score:.2f}",
                    metric_value=latest_val,
                    threshold_value=Z_THRESHOLD,
                    context={
                        "auto_detect": True,
                        "product_id": str(p.id),
                        "product_name": p.product_name,
                        "platform": p.platform,
                        "metric": metric,
                        "direction": direction,
                        "z_score": round(z_score, 2),
                        "mean": round(mean_val, 2),
                        "stdev": round(stdev_val, 2),
                        "latest_value": latest_val,
                    },
                )
                db.add(event)
                total_anomalies += 1

                try:
                    await manager.send_to_user(str(p.user_id), {
                        "type": "alert:anomaly",
                        "data": {
                            "product_name": p.product_name,
                            "metric": metric,
                            "direction": direction,
                            "z_score": round(z_score, 2),
                            "severity": severity,
                        },
                        "ts": datetime.now(UTC).isoformat(),
                    })
                except Exception:
                    logger.warning("Silent exception")

        if total_anomalies > 0:
            await db.commit()
            logger.info(f"Auto-detect found {total_anomalies} anomalies across {len(products)} products")


def setup_scheduler():
    scheduler.add_job(
        process_pending_tasks,
        IntervalTrigger(seconds=30),
        id="process_pending_tasks",
        name="处理待执行采集任务",
        replace_existing=True,
    )

    scheduler.add_job(
        check_proxy_health,
        IntervalTrigger(minutes=10),
        id="check_proxy_health",
        name="代理池健康检测",
        replace_existing=True,
    )

    scheduler.add_job(
        cleanup_expired_tokens,
        CronTrigger(hour=3, minute=0),
        id="cleanup_expired_tokens",
        name="清理过期Token",
        replace_existing=True,
    )

    scheduler.add_job(
        evaluate_monitor_rules,
        IntervalTrigger(minutes=5),
        id="evaluate_monitor_rules",
        name="评估监控规则",
        replace_existing=True,
    )

    scheduler.add_job(
        downgrade_expired_plans,
        CronTrigger(hour=2, minute=0),
        id="downgrade_expired_plans",
        name="自动降级过期套餐",
        replace_existing=True,
    )

    scheduler.add_job(
        compute_feature_rankings,
        CronTrigger(hour="*/2", minute=30),
        id="compute_feature_rankings",
        name="计算商品群体排名",
        replace_existing=True,
    )

    scheduler.add_job(
        auto_detect_anomalies,
        IntervalTrigger(hours=1),
        id="auto_detect_anomalies",
        name="自动异常检测",
        replace_existing=True,
    )

    return scheduler
