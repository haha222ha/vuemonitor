import secrets
import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundException, ForbiddenException
from app.core.security import verify_password, create_access_token
from app.middleware.auth import CurrentUser, AdminUser
from app.models.user import User
from app.models.admin import ProxyPool, AdminAuditLog, RiskEvent
from app.models.collect import CollectTask
from app.models.license import LicenseCode

router = APIRouter(prefix="/admin", tags=["admin"])

_admin_login_attempts: dict[str, list[float]] = {}
_ADMIN_MAX_ATTEMPTS = 5
_ADMIN_LOCKOUT_SECONDS = 300


class AdminLoginRequest(BaseModel):
    username: str
    password: str


class LicenseGenerateRequest(BaseModel):
    plan: str = Field(..., pattern="^(pro|premium|enterprise)$")
    duration_days: int = Field(30, ge=1, le=3650)
    count: int = Field(1, ge=1, le=100)


class ProxyAddRequest(BaseModel):
    ip: str
    port: int = Field(..., ge=1, le=65535)
    protocol: str = Field("http", pattern="^(http|https|socks5)$")


class UserUpdateRequest(BaseModel):
    plan: str | None = Field(None, pattern="^(free|pro|premium|enterprise)$")
    is_active: bool | None = None


@router.post("/login")
async def admin_login(req: AdminLoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    attempts = _admin_login_attempts.get(client_ip, [])
    attempts = [t for t in attempts if now - t < _ADMIN_LOCKOUT_SECONDS]
    if len(attempts) >= _ADMIN_MAX_ATTEMPTS:
        raise ForbiddenException(message=f"登录尝试过多，请{_ADMIN_LOCKOUT_SECONDS}秒后重试")
    _admin_login_attempts[client_ip] = attempts

    result = await db.execute(select(User).where(User.email == req.username, User.role == "admin"))
    admin = result.scalar_one_or_none()
    if not admin or not verify_password(req.password, admin.password_hash):
        _admin_login_attempts[client_ip].append(now)
        raise ForbiddenException(message="管理员账号或密码错误")
    _admin_login_attempts.pop(client_ip, None)
    token = create_access_token(subject=str(admin.id), extra={"role": "admin"})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/stats")
async def admin_stats(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    active_users = (await db.execute(select(func.count()).where(User.is_active == True))).scalar() or 0
    today = datetime.now(timezone.utc).date()
    today_tasks = (await db.execute(
        select(func.count()).select_from(CollectTask).where(CollectTask.created_at >= today)
    )).scalar() or 0
    available_proxies = (await db.execute(
        select(func.count()).select_from(ProxyPool).where(ProxyPool.status == "available")
    )).scalar() or 0

    return {
        "code": 0,
        "data": {
            "totalUsers": total_users,
            "activeUsers": active_users,
            "todayTasks": today_tasks,
            "availableProxies": available_proxies,
        },
    }


@router.get("/users")
async def list_users(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    total = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    users = result.scalars().all()

    return {
        "code": 0,
        "data": {
            "total": total,
            "items": [
                {
                    "id": str(u.id),
                    "email": u.email,
                    "nickname": u.nickname,
                    "plan": u.plan,
                    "is_active": u.is_active,
                    "created_at": u.created_at.isoformat() if u.created_at else None,
                }
                for u in users
            ],
        },
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    req: UserUpdateRequest,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    target = result.scalar_one_or_none()
    if not target:
        raise NotFoundException(message="用户不存在")

    if req.plan is not None:
        target.plan = req.plan
    if req.is_active is not None:
        target.is_active = req.is_active

    await db.flush()

    await _log_action(db, str(admin.id), "update_user", f"user:{user_id}", f"plan={req.plan}, active={req.is_active}")
    return {"code": 0, "message": "更新成功"}


@router.get("/licenses")
async def list_licenses(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(LicenseCode).order_by(LicenseCode.created_at.desc()))
    licenses = result.scalars().all()

    return {
        "code": 0,
        "data": {
            "items": [
                {
                    "id": str(l.id),
                    "code": l.code,
                    "plan": l.plan,
                    "duration_days": l.duration_days,
                    "status": l.status,
                    "current_activations": l.current_activations,
                    "max_activations": l.max_activations,
                    "created_at": l.created_at.isoformat() if l.created_at else None,
                }
                for l in licenses
            ],
        },
    }


@router.post("/licenses/generate")
async def generate_licenses(
    req: LicenseGenerateRequest,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    created = []
    for _ in range(req.count):
        code = f"VM-{req.plan.upper()}-{secrets.token_hex(8).upper()}"
        license_key = LicenseCode(
            code=code,
            plan=req.plan,
            duration_days=req.duration_days,
            status="unused",
            created_by=admin.id,
        )
        db.add(license_key)
        created.append(code)

    await db.flush()
    await _log_action(db, str(admin.id), "generate_licenses", "batch", f"count={req.count}, plan={req.plan}")
    return {"code": 0, "data": {"codes": created, "count": len(created)}}


@router.get("/collect/tasks")
async def list_all_collect_tasks(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = select(CollectTask)
    if status:
        query = query.where(CollectTask.status == status)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
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
                    "target_type": t.target_type,
                    "status": t.status,
                    "progress": t.progress,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in tasks
            ],
        },
    }


@router.put("/collect/tasks/{task_id}/cancel")
async def cancel_collect_task(
    task_id: str,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(CollectTask).where(CollectTask.id == uuid.UUID(task_id)))
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundException(message="任务不存在")
    task.status = "cancelled"
    await db.flush()
    await _log_action(db, str(admin.id), "cancel_task", f"task:{task_id}", "")
    return {"code": 0, "message": "已取消"}


@router.get("/proxies")
async def list_proxies(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ProxyPool).order_by(ProxyPool.health_score.desc()))
    proxies = result.scalars().all()

    return {
        "code": 0,
        "data": {
            "items": [
                {
                    "id": str(p.id),
                    "ip": p.ip,
                    "port": p.port,
                    "protocol": p.protocol,
                    "health_score": p.health_score,
                    "status": p.status,
                    "fail_count": p.fail_count,
                    "last_checked_at": p.last_checked_at.isoformat() if p.last_checked_at else None,
                }
                for p in proxies
            ],
        },
    }


@router.post("/proxies")
async def add_proxy(
    req: ProxyAddRequest,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    proxy = ProxyPool(ip=req.ip, port=req.port, protocol=req.protocol, status="available", health_score=100)
    db.add(proxy)
    await db.flush()
    await _log_action(db, str(admin.id), "add_proxy", f"proxy:{req.ip}:{req.port}", "")
    return {"code": 0, "data": {"id": str(proxy.id)}}


@router.delete("/proxies/{proxy_id}")
async def delete_proxy(
    proxy_id: str,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ProxyPool).where(ProxyPool.id == uuid.UUID(proxy_id)))
    proxy = result.scalar_one_or_none()
    if not proxy:
        raise NotFoundException(message="代理不存在")
    await db.delete(proxy)
    await db.flush()
    return {"code": 0, "message": "已删除"}


@router.get("/risk-events")
async def list_risk_events(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RiskEvent).order_by(RiskEvent.occurred_at.desc()).limit(100)
    )
    events = result.scalars().all()

    return {
        "code": 0,
        "data": {
            "items": [
                {
                    "id": str(e.id),
                    "platform": e.platform,
                    "risk_type": e.risk_type,
                    "severity": e.risk_level,
                    "detail": e.detail,
                    "resolved": False,
                    "created_at": e.occurred_at.isoformat() if e.occurred_at else None,
                }
                for e in events
            ],
        },
    }


@router.get("/audit-logs")
async def list_audit_logs(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    total = (await db.execute(select(func.count()).select_from(AdminAuditLog))).scalar() or 0
    result = await db.execute(
        select(AdminAuditLog).order_by(AdminAuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    logs = result.scalars().all()

    return {
        "code": 0,
        "data": {
            "total": total,
            "items": [
                {
                    "id": str(l.id),
                    "operator_id": str(l.user_id) if l.user_id else None,
                    "action": l.action,
                    "target": l.resource_type or "",
                    "detail": l.detail,
                    "ip": l.ip_address,
                    "created_at": l.created_at.isoformat() if l.created_at else None,
                }
                for l in logs
            ],
        },
    }


async def _log_action(db: AsyncSession, operator_id: str, action: str, resource_type: str, detail: str):
    log = AdminAuditLog(
        user_id=uuid.UUID(operator_id) if operator_id else None,
        action=action,
        resource_type=resource_type,
        detail={"info": detail},
    )
    db.add(log)
    await db.flush()
