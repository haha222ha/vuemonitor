import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import CurrentUser
from app.models.monitor import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    is_read: bool | None = None,
    type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = select(Notification).where(Notification.user_id == user.id)
    if is_read is not None:
        query = query.where(Notification.is_read == is_read)
    if type:
        query = query.where(Notification.type == type)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    result = await db.execute(
        query.order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    notifications = result.scalars().all()

    return {
        "code": 0,
        "data": {
            "total": total,
            "items": [
                {
                    "id": str(n.id),
                    "type": n.type,
                    "title": n.title,
                    "content": n.content,
                    "is_read": n.is_read,
                    "related_id": str(n.related_id) if n.related_id else None,
                    "related_type": n.related_type,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                }
                for n in notifications
            ],
        },
    }


@router.get("/unread-count")
async def get_unread_count(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(func.count()).where(
            Notification.user_id == user.id,
            Notification.is_read == False,
        )
    )
    count = result.scalar() or 0
    return {"code": 0, "data": {"unread_count": count}}


@router.put("/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == uuid.UUID(notification_id),
            Notification.user_id == user.id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        from app.core.exceptions import NotFoundException
        raise NotFoundException(message="通知不存在")

    notification.is_read = True
    return {"code": 0, "message": "已标记为已读"}


@router.put("/read-all")
async def mark_all_as_read(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.is_read == False)
        .values(is_read=True)
    )
    return {"code": 0, "message": "全部已标记为已读"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(
            Notification.id == uuid.UUID(notification_id),
            Notification.user_id == user.id,
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        from app.core.exceptions import NotFoundException
        raise NotFoundException(message="通知不存在")

    await db.delete(notification)
    return {"code": 0, "message": "已删除"}
