import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundException, ForbiddenException
from app.middleware.auth import CurrentUser, AdminUser
from app.middleware.feature_gate import FeatureGateMiddleware
from app.models.collect import CollectTask, CollectTaskItem

router = APIRouter(prefix="/collect", tags=["collect"])


class CollectTaskCreateRequest(BaseModel):
    task_type: str = Field(..., pattern="^(product|shop|category)$")
    platform: str = Field(..., pattern="^(xhs|douyin|taobao|jd|pdd)$")
    target_type: str = Field(..., pattern="^(product_id|shop_id|category_url)$")
    target_ids: list[str] = Field(..., min_length=1)


@router.post("/tasks", status_code=201)
async def create_collect_task(
    req: CollectTaskCreateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    gate = FeatureGateMiddleware(db)
    await gate.check_gate(user, "gate:collect:create")

    task = CollectTask(
        user_id=user.id,
        task_type=req.task_type,
        platform=req.platform,
        target_type=req.target_type,
        target_ids=req.target_ids,
        status="pending",
    )
    db.add(task)
    await db.flush()

    for target_id in req.target_ids:
        item = CollectTaskItem(task_id=task.id, target_id=target_id)
        db.add(item)

    await gate.record_usage(user.id, "gate:collect:create")

    return {"code": 0, "data": {"id": str(task.id), "item_count": len(req.target_ids)}}


@router.get("/tasks")
async def list_collect_tasks(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    status: str | None = None,
    platform: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = select(CollectTask).where(CollectTask.user_id == user.id)
    if status:
        query = query.where(CollectTask.status == status)
    if platform:
        query = query.where(CollectTask.platform == platform)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    result = await db.execute(
        query.order_by(CollectTask.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    tasks = result.scalars().all()

    return {
        "code": 0,
        "data": {
            "total": total,
            "items": [
                {
                    "id": str(t.id),
                    "task_type": t.task_type,
                    "platform": t.platform,
                    "target_type": t.target_type,
                    "target_ids": t.target_ids,
                    "status": t.status,
                    "progress": t.progress,
                    "result_summary": t.result_summary,
                    "error_message": t.error_message,
                    "started_at": t.started_at.isoformat() if t.started_at else None,
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in tasks
            ],
        },
    }


@router.get("/tasks/{task_id}")
async def get_collect_task(
    task_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CollectTask).where(CollectTask.id == uuid.UUID(task_id), CollectTask.user_id == user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundException(message="采集任务不存在")

    items_result = await db.execute(
        select(CollectTaskItem).where(CollectTaskItem.task_id == task.id)
    )
    items = items_result.scalars().all()

    return {
        "code": 0,
        "data": {
            "id": str(task.id),
            "task_type": task.task_type,
            "platform": task.platform,
            "target_type": task.target_type,
            "target_ids": task.target_ids,
            "status": task.status,
            "progress": task.progress,
            "result_summary": task.result_summary,
            "items": [
                {
                    "id": str(i.id),
                    "target_id": i.target_id,
                    "status": i.status,
                    "result": i.result,
                    "error_message": i.error_message,
                    "completed_at": i.completed_at.isoformat() if i.completed_at else None,
                }
                for i in items
            ],
        },
    }


@router.post("/tasks/{task_id}/cancel")
async def cancel_collect_task(
    task_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CollectTask).where(CollectTask.id == uuid.UUID(task_id), CollectTask.user_id == user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundException(message="采集任务不存在")

    if task.status not in ("pending", "running"):
        return {"code": 0, "data": {"message": "任务已完成，无法取消"}}

    task.status = "cancelled"
    return {"code": 0, "data": {"cancelled": True}}


@router.get("/admin/tasks")
async def admin_list_tasks(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = select(CollectTask)
    if user_id:
        query = query.where(CollectTask.user_id == uuid.UUID(user_id))
    if status:
        query = query.where(CollectTask.status == status)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    result = await db.execute(query.order_by(CollectTask.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
    tasks = result.scalars().all()

    return {
        "code": 0,
        "data": {
            "total": total,
            "items": [
                {
                    "id": str(t.id),
                    "user_id": str(t.user_id),
                    "task_type": t.task_type,
                    "platform": t.platform,
                    "status": t.status,
                    "progress": t.progress,
                    "result_summary": t.result_summary,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in tasks
            ],
        },
    }
