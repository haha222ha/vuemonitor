import asyncio
import json
import logging
import os
import signal
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_CHECKPOINT_DIR = "data/checkpoints"
_SHUTDOWN_TIMEOUT = 30


class GracefulShutdown:
    def __init__(self):
        self._shutting_down = False
        self._active_tasks: dict[str, dict] = {}
        self._on_shutdown_callbacks = []

    @property
    def is_shutting_down(self) -> bool:
        return self._shutting_down

    def register_shutdown_callback(self, callback):
        self._on_shutdown_callbacks.append(callback)

    def register_task(self, task_id: str, task_info: dict):
        self._active_tasks[task_id] = {
            **task_info,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }

    def unregister_task(self, task_id: str):
        self._active_tasks.pop(task_id, None)

    async def initiate_shutdown(self):
        if self._shutting_down:
            return
        self._shutting_down = True
        logger.info(f"Graceful shutdown initiated, {len(self._active_tasks)} active tasks")

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
                await self._save_checkpoints()

        logger.info("Graceful shutdown complete")

    async def _save_checkpoints(self):
        if not self._active_tasks:
            return

        checkpoint_dir = Path(_CHECKPOINT_DIR)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        checkpoint_file = checkpoint_dir / f"shutdown_{timestamp}.json"

        checkpoint_data = {
            "shutdown_time": datetime.now(timezone.utc).isoformat(),
            "active_tasks": self._active_tasks,
        }

        with open(checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Checkpoint saved: {checkpoint_file} ({len(self._active_tasks)} tasks)")

    async def recover_from_checkpoints(self) -> list[dict]:
        checkpoint_dir = Path(_CHECKPOINT_DIR)
        if not checkpoint_dir.exists():
            return []

        recovered = []
        for cp_file in sorted(checkpoint_dir.glob("shutdown_*.json")):
            try:
                with open(cp_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for task_id, task_info in data.get("active_tasks", {}).items():
                    task_info["recovered_from"] = cp_file.name
                    recovered.append(task_info)

                os.remove(cp_file)
                logger.info(f"Recovered tasks from checkpoint: {cp_file.name}")
            except Exception as e:
                logger.error(f"Failed to recover checkpoint {cp_file}: {e}")

        return recovered


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
            pass
