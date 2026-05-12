import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any, Callable, Coroutine

from app.core.redis import get_redis

logger = logging.getLogger(__name__)


class TaskPriority(IntEnum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class TaskStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


TASK_QUEUE_KEY = "task_queue"
TASK_RESULT_PREFIX = "task_result:"
TASK_RUNNING_KEY = "task_running"
TASK_CHANNEL = "task_events"

_handlers: dict[str, Callable[..., Coroutine]] = {}
_max_concurrent = 5
_retry_limit = 3
_default_ttl = 3600


def register_handler(name: str, handler: Callable[..., Coroutine]):
    _handlers[name] = handler


async def enqueue(
    task_type: str,
    payload: dict[str, Any] | None = None,
    priority: TaskPriority = TaskPriority.NORMAL,
    max_retries: int = _retry_limit,
    delay_seconds: int = 0,
    task_id: str | None = None,
) -> str:
    tid = task_id or str(uuid.uuid4())
    task = {
        "id": tid,
        "type": task_type,
        "payload": payload or {},
        "priority": int(priority),
        "max_retries": max_retries,
        "retry_count": 0,
        "status": TaskStatus.PENDING,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "completed_at": None,
        "error": None,
        "result": None,
    }

    redis = await get_redis()
    score = int(priority) * 1e12 + time.time() + delay_seconds

    pipe = redis.pipeline()
    pipe.zadd(TASK_QUEUE_KEY, {json.dumps(task): score})
    pipe.hset(TASK_RUNNING_KEY, tid, json.dumps(task))
    pipe.publish(TASK_CHANNEL, json.dumps({"event": "enqueued", "task_id": tid, "type": task_type}))
    await pipe.execute()

    logger.info(f"Task enqueued: {tid} type={task_type} priority={priority.name}")
    return tid


async def get_task_status(task_id: str) -> dict | None:
    redis = await get_redis()
    data = await redis.hget(TASK_RUNNING_KEY, task_id)
    if data:
        return json.loads(data)

    result = await redis.get(f"{TASK_RESULT_PREFIX}{task_id}")
    if result:
        return json.loads(result)
    return None


async def cancel_task(task_id: str) -> bool:
    redis = await get_redis()
    data = await redis.hget(TASK_RUNNING_KEY, task_id)
    if not data:
        return False

    task = json.loads(data)
    if task.get("status") in (TaskStatus.RUNNING, TaskStatus.COMPLETED):
        return False

    task["status"] = "cancelled"
    task["completed_at"] = datetime.now(timezone.utc).isoformat()

    pipe = redis.pipeline()
    pipe.hset(TASK_RUNNING_KEY, task_id, json.dumps(task))
    pipe.set(f"{TASK_RESULT_PREFIX}{task_id}", json.dumps(task), ex=_default_ttl)
    pipe.publish(TASK_CHANNEL, json.dumps({"event": "cancelled", "task_id": task_id}))
    await pipe.execute()
    return True


async def list_tasks(
    status: str | None = None,
    task_type: str | None = None,
    limit: int = 50,
) -> list[dict]:
    redis = await get_redis()
    all_data = await redis.hgetall(TASK_RUNNING_KEY)
    tasks = []
    for _, data in all_data.items():
        task = json.loads(data)
        if status and task.get("status") != status:
            continue
        if task_type and task.get("type") != task_type:
            continue
        tasks.append(task)

    tasks.sort(key=lambda t: t.get("created_at", ""), reverse=True)
    return tasks[:limit]


class TaskWorker:
    def __init__(self, concurrency: int = _max_concurrent):
        self.concurrency = concurrency
        self._running = False
        self._semaphore = asyncio.Semaphore(concurrency)
        self._active_tasks: dict[str, asyncio.Task] = {}

    async def start(self):
        self._running = True
        logger.info(f"TaskWorker started with concurrency={self.concurrency}")
        asyncio.create_task(self._poll_loop())

    async def stop(self):
        self._running = False
        for task in self._active_tasks.values():
            task.cancel()
        logger.info("TaskWorker stopped")

    async def _poll_loop(self):
        while self._running:
            try:
                await self._process_next()
            except Exception as e:
                logger.error(f"Task poll error: {e}")
            await asyncio.sleep(1)

    async def _process_next(self):
        redis = await get_redis()

        now = time.time()
        candidates = await redis.zrangebyscore(
            TASK_QUEUE_KEY, 0, now, start=0, num=10, withscores=True
        )

        for raw_task, score in candidates:
            task = json.loads(raw_task)
            if task.get("status") != TaskStatus.PENDING:
                await redis.zrem(TASK_QUEUE_KEY, raw_task)
                continue

            handler = _handlers.get(task["type"])
            if not handler:
                logger.warning(f"No handler for task type: {task['type']}")
                await redis.zrem(TASK_QUEUE_KEY, raw_task)
                continue

            await redis.zrem(TASK_QUEUE_KEY, raw_task)

            async with self._semaphore:
                atask = asyncio.create_task(self._execute(task, handler))
                self._active_tasks[task["id"]] = atask
                atask.add_done_callback(lambda t, tid=task["id"]: self._active_tasks.pop(tid, None))

            break

    async def _execute(self, task: dict, handler: Callable[..., Coroutine]):
        task_id = task["id"]
        redis = await get_redis()

        task["status"] = TaskStatus.RUNNING
        task["started_at"] = datetime.now(timezone.utc).isoformat()
        await redis.hset(TASK_RUNNING_KEY, task_id, json.dumps(task))

        try:
            result = await asyncio.wait_for(
                handler(task["payload"]),
                timeout=600,
            )

            task["status"] = TaskStatus.COMPLETED
            task["result"] = result
            task["completed_at"] = datetime.now(timezone.utc).isoformat()

            pipe = redis.pipeline()
            pipe.hset(TASK_RUNNING_KEY, task_id, json.dumps(task))
            pipe.set(f"{TASK_RESULT_PREFIX}{task_id}", json.dumps(task), ex=_default_ttl)
            pipe.publish(TASK_CHANNEL, json.dumps({
                "event": "completed",
                "task_id": task_id,
                "type": task["type"],
            }))
            await pipe.execute()

            logger.info(f"Task completed: {task_id} type={task['type']}")

        except asyncio.TimeoutError:
            await self._handle_failure(task, "Task timed out (600s)")
        except Exception as e:
            await self._handle_failure(task, str(e))

    async def _handle_failure(self, task: dict, error: str):
        task_id = task["id"]
        redis = await get_redis()

        task["retry_count"] += 1
        task["error"] = error

        if task["retry_count"] < task["max_retries"]:
            task["status"] = TaskStatus.RETRYING
            delay = min(30 * (2 ** task["retry_count"]), 300)

            await redis.hset(TASK_RUNNING_KEY, task_id, json.dumps(task))

            retry_task = {**task, "status": TaskStatus.PENDING}
            score = int(task["priority"]) * 1e12 + time.time() + delay
            await redis.zadd(TASK_QUEUE_KEY, {json.dumps(retry_task): score})

            logger.warning(f"Task retrying: {task_id} attempt={task['retry_count']}/{task['max_retries']}")
        else:
            task["status"] = TaskStatus.FAILED
            task["completed_at"] = datetime.now(timezone.utc).isoformat()

            pipe = redis.pipeline()
            pipe.hset(TASK_RUNNING_KEY, task_id, json.dumps(task))
            pipe.set(f"{TASK_RESULT_PREFIX}{task_id}", json.dumps(task), ex=_default_ttl)
            pipe.publish(TASK_CHANNEL, json.dumps({
                "event": "failed",
                "task_id": task_id,
                "type": task["type"],
                "error": error,
            }))
            await pipe.execute()

            logger.error(f"Task failed permanently: {task_id} type={task['type']} error={error}")


worker = TaskWorker()


async def start_worker():
    await worker.start()


async def stop_worker():
    await worker.stop()
