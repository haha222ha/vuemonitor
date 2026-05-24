import asyncio
import logging

from app.config import get_settings
from app.core.database import async_session_factory
from app.services.aipic.credits_service import refund_credits
from app.services.aipic.generate_service import generate_image_async
from app.services.aipic.queue_service import complete_task, fail_task, get_next_task
from app.services.aipic.style_service import get_style_by_name

logger = logging.getLogger(__name__)

_workers: list["AipicWorker"] = []
_workers_running = False


class AipicWorker:
    def __init__(self, worker_id: int):
        self.worker_id = worker_id
        self.running = False
        self.current_task: str | None = None
        self._task = None

    async def start(self):
        if self.running:
            return
        self.running = True
        self._task = asyncio.create_task(self._worker_loop())
        logger.info(f"AipicWorker-{self.worker_id} 已启动")

    async def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                logger.debug("AIPIC worker %s task cancelled", self.worker_id)

    def get_status(self) -> dict:
        return {
            "worker_id": self.worker_id,
            "running": self.running,
            "current_task": self.current_task,
        }

    async def _worker_loop(self):
        settings = get_settings()
        while self.running:
            try:
                async with async_session_factory() as db:
                    task = await get_next_task(db)
                    if not task:
                        await asyncio.sleep(settings.AIPIC_WORKER_INTERVAL)
                        continue

                    self.current_task = task.task_id

                    style_prompt = ""
                    if task.style_name:
                        style = await get_style_by_name(db, task.style_name)
                        if style:
                            style_prompt = style["style_prompt"]

                    result = await generate_image_async(
                        prompt=task.prompt,
                        negative_prompt=task.negative_prompt,
                        model_name=task.model_name,
                        ratio_key=task.ratio_key,
                        style_prompt=style_prompt,
                        input_image_path=task.input_image_path,
                        task_type=task.task_type,
                        quality_tier=task.quality_tier,
                    )

                    if result.get("success"):
                        await complete_task(
                            db,
                            task.task_id,
                            result["output_path"],
                            seed=result.get("seed", -1),
                        )
                    else:
                        await fail_task(
                            db,
                            task.task_id,
                            result.get("error", "未知错误"),
                        )

                        credits_cost = task.credits_cost
                        if credits_cost > 0:
                            await refund_credits(
                                db,
                                task.user_id,
                                credits_cost,
                                f"生成失败退还：{task.prompt[:20]}",
                            )

                    await db.commit()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"AipicWorker-{self.worker_id} 执行异常: {e}", exc_info=True)
                if self.current_task:
                    try:
                        async with async_session_factory() as db:
                            await fail_task(db, self.current_task, f"Worker异常: {str(e)[:200]}")
                            await db.commit()
                    except Exception:
                        logger.error(f"AipicWorker-{self.worker_id} 异常处理失败")
            finally:
                self.current_task = None

            await asyncio.sleep(settings.AIPIC_WORKER_INTERVAL)


async def start_aipic_workers():
    global _workers, _workers_running
    settings = get_settings()
    if not settings.AIPIC_ENABLED:
        logger.info("AI作图模块未启用，跳过Worker启动")
        return

    _workers_running = True
    for i in range(settings.AIPIC_WORKER_COUNT):
        worker = AipicWorker(worker_id=i)
        await worker.start()
        _workers.append(worker)
    logger.info(f"AI作图Worker池已启动，共 {settings.AIPIC_WORKER_COUNT} 个Worker")


async def stop_aipic_workers():
    global _workers_running
    _workers_running = False
    for worker in _workers:
        await worker.stop()
    _workers.clear()
    logger.info("AI作图Worker池已停止")


def get_worker_status() -> dict:
    return {
        "total_workers": len(_workers),
        "running": _workers_running,
        "workers": [w.get_status() for w in _workers],
    }
