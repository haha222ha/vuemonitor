import asyncio
import logging
import os
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, select

from app.config import get_settings
from app.core.database import async_session_factory
from app.models.aipic import AipicGenerateQueue
from app.services.aipic.credits_service import refund_credits

logger = logging.getLogger(__name__)

_cleanup_task: asyncio.Task | None = None


async def _cleanup_loop():
    settings = get_settings()
    while True:
        try:
            await _cleanup_temp_files()
            await _cleanup_stuck_tasks()
        except Exception as e:
            logger.error(f"AI作图清理异常: {e}", exc_info=True)
        await asyncio.sleep(settings.AIPIC_CLEANUP_INTERVAL_SECONDS)


async def _cleanup_temp_files():
    settings = get_settings()
    temp_dir = settings.AIPIC_TEMP_DIR or os.path.join(os.getcwd(), "aipic_temp")
    if not os.path.exists(temp_dir):
        return

    cutoff = datetime.now() - timedelta(hours=24)
    cleaned = 0

    for filename in os.listdir(temp_dir):
        filepath = os.path.join(temp_dir, filename)
        if not os.path.isfile(filepath):
            continue
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            if mtime < cutoff:
                os.remove(filepath)
                cleaned += 1
        except Exception:
            logger.warning("Silent exception")

    if cleaned > 0:
        logger.info(f"AI作图清理了 {cleaned} 个过期临时文件")


async def _cleanup_stuck_tasks():
    settings = get_settings()
    timeout_minutes = settings.AIPIC_STUCK_TASK_TIMEOUT_MINUTES
    cutoff = datetime.now(UTC) - timedelta(minutes=timeout_minutes)

    async with async_session_factory() as db:
        result = await db.execute(
            select(AipicGenerateQueue).where(
                and_(
                    AipicGenerateQueue.task_status == "执行中",
                    AipicGenerateQueue.execute_time < cutoff,
                )
            )
        )
        stuck_tasks = result.scalars().all()

        for task in stuck_tasks:
            try:
                task.task_status = "失败"
                task.finish_time = datetime.now(UTC)
                task.fail_reason = "任务超时自动关闭"

                if task.credits_cost > 0:
                    await refund_credits(
                        db,
                        task.user_id,
                        task.credits_cost,
                        f"任务超时退还：{task.prompt[:20]}",
                    )
            except Exception as e:
                logger.error(f"退还超时任务失败 {task.task_id}: {e}")

        if stuck_tasks:
            await db.commit()
            logger.info(f"AI作图清理了 {len(stuck_tasks)} 个超时任务并退还积分")


async def start_aipic_cleanup():
    global _cleanup_task
    settings = get_settings()
    if not settings.AIPIC_ENABLED:
        return
    _cleanup_task = asyncio.create_task(_cleanup_loop())
    logger.info("AI作图清理Worker已启动")


async def stop_aipic_cleanup():
    global _cleanup_task
    if _cleanup_task:
        _cleanup_task.cancel()
        try:
            await _cleanup_task
        except asyncio.CancelledError:
            logger.warning("Silent exception")
        _cleanup_task = None
    logger.info("AI作图清理Worker已停止")
