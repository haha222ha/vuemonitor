from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import AdminUser
from app.models.security_audit import SecurityAuditLog
from app.models.user import User

router = APIRouter(prefix="/admin/security", tags=["安全审计"])


@router.get("/audit-logs")
async def list_audit_logs(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    min_risk: int | None = None,
    method: str | None = None,
    path: str | None = None,
    client_ip: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
):
    query = select(SecurityAuditLog)

    if min_risk is not None:
        query = query.where(SecurityAuditLog.risk_score >= min_risk)
    if method:
        query = query.where(SecurityAuditLog.method == method)
    if path:
        query = query.where(SecurityAuditLog.path.ilike(f"%{path}%"))
    if client_ip:
        query = query.where(SecurityAuditLog.client_ip == client_ip)
    if start_date:
        query = query.where(SecurityAuditLog.timestamp >= start_date)
    if end_date:
        query = query.where(SecurityAuditLog.timestamp <= end_date)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    query = query.order_by(desc(SecurityAuditLog.id)).offset((page - 1) * page_size).limit(page_size)
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
                    "request_id": log.request_id,
                    "timestamp": log.timestamp,
                    "method": log.method,
                    "path": log.path,
                    "query": log.query,
                    "client_ip": log.client_ip,
                    "user_agent": log.user_agent[:80] if log.user_agent else "",
                    "user_id": log.user_id,
                    "risk_score": log.risk_score,
                    "risk_flags": log.risk_flags,
                    "status_code": log.status_code,
                    "response_time_ms": log.response_time_ms,
                }
                for log in logs
            ],
        },
    }


@router.get("/audit-summary")
async def audit_summary(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
    hours: int = Query(24, ge=1, le=720),
):
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    total_requests = await db.execute(
        select(func.count()).select_from(SecurityAuditLog).where(SecurityAuditLog.timestamp >= since)
    )
    high_risk = await db.execute(
        select(func.count()).select_from(SecurityAuditLog).where(
            SecurityAuditLog.timestamp >= since, SecurityAuditLog.risk_score >= 50
        )
    )
    auth_failures = await db.execute(
        select(func.count()).select_from(SecurityAuditLog).where(
            SecurityAuditLog.timestamp >= since, SecurityAuditLog.status_code == 401
        )
    )
    rate_limited = await db.execute(
        select(func.count()).select_from(SecurityAuditLog).where(
            SecurityAuditLog.timestamp >= since, SecurityAuditLog.status_code == 429
        )
    )
    top_ips = await db.execute(
        select(SecurityAuditLog.client_ip, func.count().label("cnt"))
        .where(SecurityAuditLog.timestamp >= since)
        .group_by(SecurityAuditLog.client_ip)
        .order_by(desc(func.count()))
        .limit(10)
    )
    top_paths = await db.execute(
        select(SecurityAuditLog.path, func.count().label("cnt"))
        .where(SecurityAuditLog.timestamp >= since)
        .group_by(SecurityAuditLog.path)
        .order_by(desc(func.count()))
        .limit(10)
    )

    return {
        "code": 0,
        "data": {
            "hours": hours,
            "total_requests": total_requests.scalar() or 0,
            "high_risk_count": high_risk.scalar() or 0,
            "auth_failure_count": auth_failures.scalar() or 0,
            "rate_limited_count": rate_limited.scalar() or 0,
            "top_ips": [{"ip": ip, "count": cnt} for ip, cnt in top_ips],
            "top_paths": [{"path": path, "count": cnt} for path, cnt in top_paths],
        },
    }
