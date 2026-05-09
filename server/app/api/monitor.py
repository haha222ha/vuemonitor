import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.middleware.auth import CurrentUser
from app.models.monitor import MonitorRule, Notification

router = APIRouter(prefix="/monitor", tags=["monitor"])


class RuleCreateRequest(BaseModel):
    product_id: str
    rule_name: str = Field(..., min_length=1, max_length=200)
    rule_type: str = Field(..., pattern="^(price_drop|sales_surge|stock_change|rating_drop|custom)$")
    conditions: dict


class RuleUpdateRequest(BaseModel):
    rule_name: str | None = None
    conditions: dict | None = None
    is_active: bool | None = None


@router.post("/rules", status_code=201)
async def create_rule(
    req: RuleCreateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    rule = MonitorRule(
        user_id=user.id,
        product_id=uuid.UUID(req.product_id),
        rule_name=req.rule_name,
        rule_type=req.rule_type,
        conditions=req.conditions,
    )
    db.add(rule)
    await db.flush()
    return {"code": 0, "data": {"id": str(rule.id)}}


@router.get("/rules")
async def list_rules(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    product_id: str | None = None,
    is_active: bool | None = None,
):
    query = select(MonitorRule).where(MonitorRule.user_id == user.id)
    if product_id:
        query = query.where(MonitorRule.product_id == uuid.UUID(product_id))
    if is_active is not None:
        query = query.where(MonitorRule.is_active == is_active)

    result = await db.execute(query.order_by(MonitorRule.created_at.desc()))
    rules = result.scalars().all()

    return {
        "code": 0,
        "data": [
            {
                "id": str(r.id),
                "product_id": str(r.product_id),
                "rule_name": r.rule_name,
                "rule_type": r.rule_type,
                "conditions": r.conditions,
                "is_active": r.is_active,
                "last_triggered_at": r.last_triggered_at.isoformat() if r.last_triggered_at else None,
                "trigger_count": r.trigger_count,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rules
        ],
    }


@router.put("/rules/{rule_id}")
async def update_rule(
    rule_id: str,
    req: RuleUpdateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MonitorRule).where(MonitorRule.id == uuid.UUID(rule_id), MonitorRule.user_id == user.id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise NotFoundException(message="规则不存在")

    if req.rule_name is not None:
        rule.rule_name = req.rule_name
    if req.conditions is not None:
        rule.conditions = req.conditions
    if req.is_active is not None:
        rule.is_active = req.is_active

    return {"code": 0, "data": {"updated": True}}


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MonitorRule).where(MonitorRule.id == uuid.UUID(rule_id), MonitorRule.user_id == user.id)
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise NotFoundException(message="规则不存在")

    await db.delete(rule)
    return {"code": 0, "data": {"deleted": True}}


@router.get("/notifications")
async def list_notifications(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    is_read: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = select(Notification).where(Notification.user_id == user.id)
    if is_read is not None:
        query = query.where(Notification.is_read == is_read)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    result = await db.execute(
        query.order_by(Notification.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
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


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(Notification.id == uuid.UUID(notification_id), Notification.user_id == user.id)
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise NotFoundException(message="通知不存在")

    notification.is_read = True
    return {"code": 0, "data": {"read": True}}


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Notification).where(Notification.user_id == user.id, Notification.is_read == False)
    )
    for n in result.scalars().all():
        n.is_read = True
    return {"code": 0, "data": {"read_all": True}}
