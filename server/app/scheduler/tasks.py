import asyncio
import logging
import uuid
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.core.database import async_session_factory
from app.collect.engine import CollectEngine
from app.models.collect import CollectTask
from app.models.admin import ProxyPool
from app.ws.manager import manager

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
                    "ts": datetime.now(timezone.utc).isoformat(),
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

            proxy.last_checked_at = datetime.now(timezone.utc)

        await db.commit()


async def cleanup_expired_tokens():
    async with async_session_factory() as db:
        from app.models.user import RefreshToken
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.expires_at < datetime.now(timezone.utc))
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
        from app.models.user import User
        from app.models.license import LicenseCode, LicenseActivation
        now = datetime.now(timezone.utc)

        result = await db.execute(
            select(User).where(
                User.plan != "free",
                User.plan_expires_at != None,
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
                LicenseCode.expires_at != None,
                LicenseCode.expires_at < now,
            )
        )
        expired_licenses = result.scalars().all()

        for lic in expired_licenses:
            lic.status = "expired"

        if expired_licenses:
            await db.commit()
            logger.info(f"Marked {len(expired_licenses)} licenses as expired")


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

    return scheduler
