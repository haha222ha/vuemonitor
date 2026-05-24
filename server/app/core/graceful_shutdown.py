import asyncio
import json
import logging
import os
import signal
import time
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_CHECKPOINT_DIR = "data/checkpoints"
_SHUTDOWN_TIMEOUT = 30
_MAX_CHECKPOINT_AGE_HOURS = 24
_HEARTBEAT_INTERVAL = 60


class GracefulShutdown:
    def __init__(self):
        self._shutting_down = False
        self._active_tasks: dict[str, dict] = {}
        self._on_shutdown_callbacks = []
        self._task_progress: dict[str, float] = {}
        self._heartbeat_task: asyncio.Task | None = None

    @property
    def is_shutting_down(self) -> bool:
        return self._shutting_down

    def register_shutdown_callback(self, callback):
        self._on_shutdown_callbacks.append(callback)

    def register_task(self, task_id: str, task_info: dict):
        self._active_tasks[task_id] = {
            **task_info,
            "registered_at": datetime.now(UTC).isoformat(),
            "status": "running",
        }
        self._task_progress[task_id] = 0.0

    def unregister_task(self, task_id: str):
        self._active_tasks.pop(task_id, None)
        self._task_progress.pop(task_id, None)

    def update_task_progress(self, task_id: str, progress: float, status: str = "running"):
        if task_id in self._active_tasks:
            self._active_tasks[task_id]["progress"] = progress
            self._active_tasks[task_id]["status"] = status
            self._task_progress[task_id] = progress

    def update_task_checkpoint(self, task_id: str, checkpoint_data: dict):
        if task_id in self._active_tasks:
            self._active_tasks[task_id]["checkpoint"] = checkpoint_data
            self._active_tasks[task_id]["checkpoint_at"] = datetime.now(UTC).isoformat()

    def start_heartbeat(self):
        if self._heartbeat_task and not self._heartbeat_task.done():
            return
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self):
        while not self._shutting_down:
            try:
                await asyncio.sleep(_HEARTBEAT_INTERVAL)
                if self._active_tasks:
                    await self._save_checkpoints()
                    logger.debug(f"Heartbeat: {len(self._active_tasks)} active tasks checkpointed")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    async def initiate_shutdown(self):
        if self._shutting_down:
            return
        self._shutting_down = True
        logger.info(f"Graceful shutdown initiated, {len(self._active_tasks)} active tasks")

        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()

        await self._save_checkpoints()

        for callback in self._on_shutdown_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback()
                else:
                    callback()
            except Exception as e:
                logger.error(f"Shutdown callback error: {e}")

        if self._active_tasks:
            logger.info(f"Waiting up to {_SHUTDOWN_TIMEOUT}s for {len(self._active_tasks)} tasks to complete")
            deadline = time.time() + _SHUTDOWN_TIMEOUT
            while self._active_tasks and time.time() < deadline:
                await asyncio.sleep(0.5)

            if self._active_tasks:
                logger.warning(f"Forcing shutdown with {len(self._active_tasks)} tasks still active")
                for task_id in self._active_tasks:
                    self._active_tasks[task_id]["status"] = "interrupted"
                await self._save_checkpoints()

        logger.info("Graceful shutdown complete")

    async def _save_checkpoints(self):
        if not self._active_tasks:
            return

        checkpoint_dir = Path(_CHECKPOINT_DIR)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        checkpoint_file = checkpoint_dir / f"shutdown_{timestamp}.json"

        checkpoint_data = {
            "shutdown_time": datetime.now(UTC).isoformat(),
            "active_tasks": self._active_tasks,
        }

        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Checkpoint saved: {checkpoint_file} ({len(self._active_tasks)} tasks)")

    async def recover_from_checkpoints(self) -> list[dict]:
        checkpoint_dir = Path(_CHECKPOINT_DIR)
        if not checkpoint_dir.exists():
            return []

        self._cleanup_old_checkpoints(checkpoint_dir)

        recovered = []
        for cp_file in sorted(checkpoint_dir.glob("shutdown_*.json")):
            try:
                with open(cp_file, encoding="utf-8") as f:
                    data = json.load(f)

                for task_id, task_info in data.get("active_tasks", {}).items():
                    task_info["recovered_from"] = cp_file.name
                    task_info["original_task_id"] = task_id
                    recovered.append(task_info)

                os.remove(cp_file)
                logger.info(f"Recovered tasks from checkpoint: {cp_file.name}")
            except Exception as e:
                logger.error(f"Failed to recover checkpoint {cp_file}: {e}")

        return recovered

    def _cleanup_old_checkpoints(self, checkpoint_dir: Path):
        cutoff = time.time() - (_MAX_CHECKPOINT_AGE_HOURS * 3600)
        for cp_file in checkpoint_dir.glob("shutdown_*.json"):
            try:
                if cp_file.stat().st_mtime < cutoff:
                    cp_file.unlink()
                    logger.info(f"Cleaned up old checkpoint: {cp_file.name}")
            except Exception as e:
                logger.error(f"Failed to cleanup checkpoint {cp_file}: {e}")

    def get_active_tasks_summary(self) -> dict:
        return {
            "total": len(self._active_tasks),
            "tasks": {
                tid: {
                    "status": info.get("status", "unknown"),
                    "progress": info.get("progress", 0.0),
                    "type": info.get("type", "unknown"),
                }
                for tid, info in self._active_tasks.items()
            },
        }


graceful_shutdown = GracefulShutdown()


def setup_signal_handlers():
    loop = asyncio.get_event_loop()

    def _signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(graceful_shutdown.initiate_shutdown())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            logger.debug("Signal handlers not supported on this platform")
