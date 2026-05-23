from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import AdminUser, CurrentUser
from app.models.operation_audit import OperationAuditLog

router = APIRouter(prefix="/audit/operations", tags=["操作审计"])


@router.get("")
async def list_operation_logs(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: str | None = None,
    resource_type: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
):
    is_admin = user.role in ("super_admin", "admin")
    conditions = []

    if not is_admin:
        conditions.append(OperationAuditLog.user_id == str(user.id))

    if action:
        conditions.append(OperationAuditLog.action == action)
    if resource_type:
        conditions.append(OperationAuditLog.resource_type == resource_type)
    if start_date:
        conditions.append(OperationAuditLog.created_at >= start_date)
    if end_date:
        conditions.append(OperationAuditLog.created_at <= end_date)

    count_query = select(func.count(OperationAuditLog.id))
    for cond in conditions:
        count_query = count_query.where(cond)
    total = (await db.execute(count_query)).scalar() or 0

    query = select(OperationAuditLog)
    for cond in conditions:
        query = query.where(cond)
    query = query.order_by(desc(OperationAuditLog.id)).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "code": 0,
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "detail": log.detail,
                    "old_value": log.old_value,
                    "new_value": log.new_value,
                    "ip_address": log.ip_address,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ],
        },
    }


@router.get("/summary")
async def operation_summary(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
    hours: int = Query(24, ge=1, le=720),
):
    since = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()

    total_ops = await db.execute(
        select(func.count()).select_from(OperationAuditLog).where(OperationAuditLog.created_at >= since)
    )
    action_dist = await db.execute(
        select(OperationAuditLog.action, func.count().label("cnt"))
        .where(OperationAuditLog.created_at >= since)
        .group_by(OperationAuditLog.action)
        .order_by(desc(func.count()))
        .limit(20)
    )
    resource_dist = await db.execute(
        select(OperationAuditLog.resource_type, func.count().label("cnt"))
        .where(OperationAuditLog.created_at >= since)
        .group_by(OperationAuditLog.resource_type)
        .order_by(desc(func.count()))
        .limit(10)
    )
    top_users = await db.execute(
        select(OperationAuditLog.user_id, func.count().label("cnt"))
        .where(OperationAuditLog.created_at >= since)
        .group_by(OperationAuditLog.user_id)
        .order_by(desc(func.count()))
        .limit(10)
    )

    return {
        "code": 0,
        "data": {
            "hours": hours,
            "total_operations": total_ops.scalar() or 0,
            "action_distribution": [{"action": a, "count": c} for a, c in action_dist],
            "resource_distribution": [{"type": t, "count": c} for t, c in resource_dist],
            "top_users": [{"user_id": u, "count": c} for u, c in top_users],
        },
    }
