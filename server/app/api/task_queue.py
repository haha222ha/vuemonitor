from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import AdminUser
from app.task_queue.queue import enqueue, get_task_status, cancel_task, list_tasks, TaskPriority

router = APIRouter(prefix="/tasks", tags=["task-queue"])


@router.get("")
async def list_queue_tasks(
    admin: AdminUser,
    status: str | None = None,
    task_type: str | None = None,
    limit: int = Query(50, ge=1, le=200),
):
    tasks = await list_tasks(status=status, task_type=task_type, limit=limit)
    return {"code": 0, "data": {"items": tasks, "count": len(tasks)}}


@router.get("/{task_id}")
async def get_task_detail(
    task_id: str,
    admin: AdminUser,
):
    task = await get_task_status(task_id)
    if not task:
        return {"code": 404, "message": "任务不存在"}
    return {"code": 0, "data": task}


@router.post("/{task_id}/cancel")
async def cancel_queue_task(
    task_id: str,
    admin: AdminUser,
):
    success = await cancel_task(task_id)
    if success:
        return {"code": 0, "message": "任务已取消"}
    return {"code": 400, "message": "无法取消该任务"}


@router.post("/enqueue")
async def manual_enqueue(
    admin: AdminUser,
    task_type: str = Query(...),
    payload: dict | None = None,
    priority: TaskPriority = TaskPriority.NORMAL,
):
    task_id = await enqueue(task_type, payload, priority)
    return {"code": 0, "data": {"task_id": task_id}}
