import secrets
import time
import uuid
import psutil
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, engine, async_session_factory
from app.core.exceptions import NotFoundException, ForbiddenException
from app.core.security import verify_password, create_access_token
from app.core.redis import get_redis
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
    plan: str = Field(..., pattern="^(free|pro|premium|enterprise)$")
    duration_days: int = Field(30, ge=1, le=3650)
    count: int = Field(1, ge=1, le=500)
    max_activations: int = Field(1, ge=1, le=10)
    note: str | None = Field(None, max_length=500)


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
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    plan: str | None = None,
    batch_id: str | None = None,
    search: str | None = None,
):
    from app.services.license_service import LicenseService
    svc = LicenseService(db)
    result = await svc.list_licenses(page, page_size, status, plan, batch_id, search)
    return {"code": 0, "data": result}


@router.post("/licenses/generate")
async def generate_licenses(
    req: LicenseGenerateRequest,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    from app.services.license_service import LicenseService
    svc = LicenseService(db)
    licenses = await svc.batch_generate(
        plan=req.plan,
        duration_days=req.duration_days,
        count=req.count,
        max_activations=req.max_activations if hasattr(req, "max_activations") else 1,
        note=req.note if hasattr(req, "note") else None,
        created_by=admin.id,
    )
    codes = [l.code for l in licenses]
    await _log_action(db, str(admin.id), "generate_licenses", "batch", f"count={req.count}, plan={req.plan}")
    return {"code": 0, "data": {"codes": codes, "count": len(codes), "batch_id": licenses[0].batch_id if licenses else None}}


@router.post("/licenses/{license_id}/revoke")
async def admin_revoke_license(
    license_id: uuid.UUID,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
    reason: str | None = None,
):
    from app.services.license_service import LicenseService
    svc = LicenseService(db)
    result = await svc.revoke(license_id, admin.id, reason)
    await _log_action(db, str(admin.id), "revoke_license", f"license:{license_id}", reason or "")
    return result


@router.post("/licenses/{license_id}/renew")
async def admin_renew_license(
    license_id: uuid.UUID,
    admin: AdminUser,
    extra_days: int = Query(..., ge=1, le=3650),
    db: AsyncSession = Depends(get_db),
):
    from app.services.license_service import LicenseService
    svc = LicenseService(db)
    result = await svc.renew(license_id, extra_days, admin.id)
    await _log_action(db, str(admin.id), "renew_license", f"license:{license_id}", f"extra_days={extra_days}")
    return result


@router.post("/licenses/{license_id}/upgrade")
async def admin_upgrade_license(
    license_id: uuid.UUID,
    admin: AdminUser,
    new_plan: str = Query(..., pattern="^(pro|premium|enterprise)$"),
    db: AsyncSession = Depends(get_db),
):
    from app.services.license_service import LicenseService
    svc = LicenseService(db)
    result = await svc.upgrade(license_id, new_plan, admin.id)
    await _log_action(db, str(admin.id), "upgrade_license", f"license:{license_id}", f"new_plan={new_plan}")
    return result


@router.get("/licenses/{license_id}/logs")
async def admin_license_logs(
    license_id: uuid.UUID,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    from app.services.license_service import LicenseService
    svc = LicenseService(db)
    logs = await svc.get_change_logs(license_id)
    return {"code": 0, "data": {"items": logs}}


@router.get("/licenses/export")
async def export_licenses(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
    status: str | None = None,
    plan: str | None = None,
    batch_id: str | None = None,
):
    from app.services.license_service import LicenseService
    svc = LicenseService(db)
    result = await svc.list_licenses(page=1, page_size=10000, status=status, plan=plan, batch_id=batch_id)
    return {"code": 0, "data": result}


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


class AdminCollectTaskCreateRequest(BaseModel):
    task_type: str = Field(..., pattern="^(product|shop|category)$")
    platform: str = Field(..., pattern="^(xhs|douyin|taobao|jd|pdd)$")
    target_type: str = Field(..., pattern="^(product_id|shop_id|category_url)$")
    target_ids: list[str] = Field(..., min_length=1)


@router.post("/collect/tasks", status_code=201)
async def admin_create_collect_task(
    req: AdminCollectTaskCreateRequest,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import User as UserModel
    first_admin = (await db.execute(select(UserModel).where(UserModel.role == "admin").limit(1))).scalar_one_or_none()
    owner_id = first_admin.id if first_admin else admin.id

    task = CollectTask(
        user_id=owner_id,
        task_type=req.task_type,
        platform=req.platform,
        target_type=req.target_type,
        target_ids=req.target_ids,
        status="pending",
    )
    db.add(task)
    await db.flush()

    from app.models.collect import CollectTaskItem
    for target_id in req.target_ids:
        item = CollectTaskItem(task_id=task.id, target_id=target_id)
        db.add(item)

    await _log_action(db, str(admin.id), "create_collect_task", f"task:{task.id}", f"type={req.task_type}, platform={req.platform}")
    return {"code": 0, "data": {"id": str(task.id), "item_count": len(req.target_ids)}}


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


@router.get("/monitoring/system")
async def system_health(admin: AdminUser):
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    boot_time = datetime.fromtimestamp(psutil.boot_time(), tz=timezone.utc)

    return {
        "code": 0,
        "data": {
            "cpu": {
                "percent": cpu_percent,
                "count": psutil.cpu_count(),
                "load_avg": psutil.getloadavg() if hasattr(psutil, "getloadavg") else None,
            },
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "percent": memory.percent,
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": round(disk.used / disk.total * 100, 1),
            },
            "uptime_seconds": (datetime.now(timezone.utc) - boot_time).total_seconds(),
            "processes": len(psutil.pids()),
        },
    }


@router.get("/monitoring/performance")
async def performance_metrics(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)
    twenty_four_hours_ago = now - timedelta(hours=24)

    recent_tasks = await db.execute(
        select(func.count()).select_from(CollectTask).where(CollectTask.created_at >= one_hour_ago)
    )
    recent_count = recent_tasks.scalar() or 0

    success_tasks = await db.execute(
        select(func.count()).select_from(CollectTask).where(
            CollectTask.created_at >= one_hour_ago,
            CollectTask.status == "completed",
        )
    )
    success_count = success_tasks.scalar() or 0

    failed_tasks = await db.execute(
        select(func.count()).select_from(CollectTask).where(
            CollectTask.created_at >= one_hour_ago,
            CollectTask.status == "failed",
        )
    )
    failed_count = failed_tasks.scalar() or 0

    total_24h = (await db.execute(
        select(func.count()).select_from(CollectTask).where(CollectTask.created_at >= twenty_four_hours_ago)
    )).scalar() or 0

    success_24h = (await db.execute(
        select(func.count()).select_from(CollectTask).where(
            CollectTask.created_at >= twenty_four_hours_ago,
            CollectTask.status == "completed",
        )
    )).scalar() or 0

    error_rate = round(failed_count / recent_count * 100, 2) if recent_count > 0 else 0
    qps = round(recent_count / 3600, 2)

    return {
        "code": 0,
        "data": {
            "last_hour": {
                "total_tasks": recent_count,
                "success_tasks": success_count,
                "failed_tasks": failed_count,
                "qps": qps,
                "error_rate": error_rate,
            },
            "last_24h": {
                "total_tasks": total_24h,
                "success_tasks": success_24h,
                "success_rate": round(success_24h / total_24h * 100, 2) if total_24h > 0 else 0,
            },
            "active_tasks": (await db.execute(
                select(func.count()).select_from(CollectTask).where(CollectTask.status == "running")
            )).scalar() or 0,
            "pending_tasks": (await db.execute(
                select(func.count()).select_from(CollectTask).where(CollectTask.status == "pending")
            )).scalar() or 0,
        },
    }


@router.get("/monitoring/infrastructure")
async def infrastructure_status(admin: AdminUser, db: AsyncSession = Depends(get_db)):
    db_status = "healthy"
    db_pool_size = engine.pool.size() if hasattr(engine.pool, "size") else 0
    db_checked_out = engine.pool.checkedout() if hasattr(engine.pool, "checkedout") else 0

    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    redis_status = "healthy"
    redis_info = {}
    try:
        redis = await get_redis()
        redis_info_raw = await redis.info()
        redis_info = {
            "used_memory_human": redis_info_raw.get("used_memory_human"),
            "connected_clients": redis_info_raw.get("connected_clients"),
            "uptime_in_seconds": redis_info_raw.get("uptime_in_seconds"),
            "total_commands_processed": redis_info_raw.get("total_commands_processed"),
        }
        await redis.ping()
    except Exception:
        redis_status = "unhealthy"

    return {
        "code": 0,
        "data": {
            "database": {
                "status": db_status,
                "pool_size": db_pool_size,
                "checked_out": db_checked_out,
                "available": db_pool_size - db_checked_out,
            },
            "redis": {
                "status": redis_status,
                **redis_info,
            },
        },
    }


@router.get("/monitoring/risk-stats")
async def risk_statistics(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    twenty_four_hours_ago = now - timedelta(hours=24)
    seven_days_ago = now - timedelta(days=7)

    risk_24h = await db.execute(
        select(RiskEvent.risk_type, func.count().label("count"))
        .where(RiskEvent.occurred_at >= twenty_four_hours_ago)
        .group_by(RiskEvent.risk_type)
    )
    risk_by_type = {row[0]: row[1] for row in risk_24h.all()}

    risk_7d = await db.execute(
        select(RiskEvent.risk_level, func.count().label("count"))
        .where(RiskEvent.occurred_at >= seven_days_ago)
        .group_by(RiskEvent.risk_level)
    )
    risk_by_level = {row[0]: row[1] for row in risk_7d.all()}

    risk_by_platform = {}
    try:
        risk_platform_result = await db.execute(
            select(RiskEvent.platform, func.count().label("count"))
            .where(RiskEvent.occurred_at >= twenty_four_hours_ago)
            .group_by(RiskEvent.platform)
        )
        risk_by_platform = {row[0]: row[1] for row in risk_platform_result.all()}
    except Exception:
        pass

    total_24h = sum(risk_by_type.values())
    total_7d = sum(risk_by_level.values())

    return {
        "code": 0,
        "data": {
            "last_24h": {
                "total": total_24h,
                "by_type": risk_by_type,
                "by_platform": risk_by_platform,
            },
            "last_7d": {
                "total": total_7d,
                "by_level": risk_by_level,
            },
        },
    }


class BenchmarkRequest(BaseModel):
    concurrency_levels: list[int] = Field([10, 50, 100], description="并发级别列表")
    items_per_level: int = Field(50, ge=10, le=200, description="每个级别的请求数")
    platform: str = Field("xhs", pattern="^(xhs|douyin|taobao|jd|pdd)$")
    include_proxy_test: bool = Field(True)
    include_risk_test: bool = Field(False)


_benchmark_results: dict | None = None
_benchmark_running: bool = False


@router.post("/monitoring/benchmark")
async def run_benchmark(
    req: BenchmarkRequest,
    admin: AdminUser,
):
    global _benchmark_running, _benchmark_results
    if _benchmark_running:
        return {"code": 1, "message": "基准测试正在运行中，请稍后查询结果"}

    _benchmark_running = True
    try:
        from tests.benchmark_collect import (
            run_concurrency_benchmark,
            run_proxy_benchmark,
            run_risk_threshold_test,
        )
        from dataclasses import asdict

        results = {}

        for conc in req.concurrency_levels:
            result = await run_concurrency_benchmark(conc, req.items_per_level, req.platform)
            results[f"concurrency_{conc}"] = asdict(result)

        if req.include_proxy_test:
            async with async_session_factory() as db:
                proxy_result = await run_proxy_benchmark(db)
                results["proxy"] = asdict(proxy_result)

        if req.include_risk_test:
            risk_result = await run_risk_threshold_test(req.platform)
            results["risk_threshold"] = risk_result

        _benchmark_results = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "benchmarks": results,
            "triggered_by": str(admin.id),
        }

        return {"code": 0, "data": _benchmark_results}
    except Exception as e:
        return {"code": 1, "message": f"基准测试失败: {str(e)}"}
    finally:
        _benchmark_running = False


@router.get("/monitoring/benchmark")
async def get_benchmark_results(admin: AdminUser):
    if not _benchmark_results:
        return {"code": 0, "data": None, "message": "暂无基准测试结果，请先运行测试"}
    return {"code": 0, "data": _benchmark_results}


@router.get("/monitoring/alerts")
async def get_alerts(
    admin: AdminUser,
    level: str | None = None,
    limit: int = Query(50, ge=1, le=200),
):
    from app.services.alert_service import alert_service
    alerts = alert_service.get_alert_history(level=level, limit=limit)
    return {"code": 0, "data": {"items": alerts, "total": len(alerts)}}


@router.get("/monitoring/alerts/stats")
async def get_alert_stats(admin: AdminUser):
    from app.services.alert_service import alert_service
    return {"code": 0, "data": alert_service.get_alert_stats()}


class AlertChannelRequest(BaseModel):
    channel_type: str = Field(..., pattern="^(webhook|email|log)$")
    config: dict


@router.post("/monitoring/alerts/channels")
async def add_alert_channel(
    req: AlertChannelRequest,
    admin: AdminUser,
):
    from app.services.alert_service import alert_service
    alert_service.add_channel(req.channel_type, req.config)
    return {"code": 0, "message": "告警通道已添加"}
