from fastapi import APIRouter, Depends

from app.api.admin import router as admin_router
from app.api.ai import router as ai_router
from app.api.ai_templates import router as ai_templates_router
from app.api.aipic.admin_routes import router as aipic_admin_router
from app.api.aipic.generate_routes import router as aipic_generate_router
from app.api.aipic.user_routes import router as aipic_user_router
from app.api.alert_rules import router as alert_rules_router
from app.api.auth import router as auth_router
from app.api.categories import router as categories_router
from app.api.collect import router as collect_router
from app.api.dashboard import router as dashboard_router
from app.api.discovery import router as discovery_router
from app.api.feature import router as feature_router
from app.api.gdpr import router as gdpr_router
from app.api.xhs_cloud import router as xhs_cloud_router
from app.api.intelligence.router import intel_router
from app.api.license import router as license_router
from app.api.monitor import router as monitor_router
from app.api.notifications import router as notifications_router
from app.api.operation_audit import router as operation_audit_router
from app.api.products import router as products_router
from app.api.public import router as public_router
from app.api.security_audit import router as security_audit_router
from app.api.sync import router as sync_router
from app.api.system import router as system_router
from app.api.task_queue import router as task_queue_router
from app.api.teams import router as teams_router
from app.api.users import router as users_router
from app.middleware.auth import AdminUser


async def require_admin(user: AdminUser):
    return user

api_router = APIRouter()

api_router.include_router(public_router)
api_router.include_router(auth_router)
api_router.include_router(sync_router)
api_router.include_router(products_router)
api_router.include_router(monitor_router)
api_router.include_router(collect_router)
api_router.include_router(ai_router)
api_router.include_router(admin_router)
api_router.include_router(dashboard_router)
api_router.include_router(notifications_router)
api_router.include_router(license_router)
api_router.include_router(users_router)
api_router.include_router(feature_router)
api_router.include_router(teams_router)
api_router.include_router(alert_rules_router)
api_router.include_router(ai_templates_router)
api_router.include_router(security_audit_router)
api_router.include_router(gdpr_router)
api_router.include_router(operation_audit_router)
api_router.include_router(task_queue_router)
api_router.include_router(system_router)
api_router.include_router(discovery_router)
api_router.include_router(categories_router)
api_router.include_router(aipic_generate_router)
api_router.include_router(aipic_user_router)
api_router.include_router(aipic_admin_router)
api_router.include_router(intel_router)
api_router.include_router(xhs_cloud_router)


@api_router.get("/health", tags=["health"])
async def health_check():
    from app.core.database import health_check as db_health
    from app.core.redis import get_redis

    db = await db_health()
    redis_status = "ok"
    try:
        redis = await get_redis()
        await redis.ping()
    except Exception as e:
        redis_status = f"error: {e}"

    return {
        "status": "ok" if db["status"] == "healthy" and redis_status == "ok" else "degraded",
        "version": "0.1.0",
        "database": db,
        "redis": redis_status,
    }


@api_router.get("/diagnose", tags=["health"])
async def diagnose(user=Depends(require_admin)):
    import logging
    import traceback

    from sqlalchemy import text

    from app.core.database import async_session_factory, engine
    from app.core.redis import get_redis

    _logger = logging.getLogger("diagnose")
    results = {"database": {}, "redis": {}, "tables": {}, "auth_test": {}}

    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            results["database"]["connection"] = "ok"
    except Exception as e:
        _logger.error("Database connection check failed: %s\n%s", e, traceback.format_exc())
        results["database"]["connection"] = "error"

    try:
        async with engine.begin() as conn:
            result = await conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
            )
            tables = [row[0] for row in result]
            results["tables"]["list"] = tables
            results["tables"]["count"] = len(tables)
    except Exception as e:
        _logger.error("Table listing failed: %s", e)
        results["tables"]["error"] = "query_failed"

    required_tables = ["users", "refresh_tokens", "products", "monitor_tasks", "alert_rules", "alert_events", "security_audit_log"]
    if "list" in results["tables"]:
        results["tables"]["missing"] = [t for t in required_tables if t not in results["tables"]["list"]]

    try:
        async with async_session_factory() as session:
            result = await session.execute(text("SELECT count(*) FROM users"))
            count = result.scalar()
            results["auth_test"]["user_count"] = count
    except Exception as e:
        _logger.error("Auth test query failed: %s\n%s", e, traceback.format_exc())
        results["auth_test"]["query_error"] = "query_failed"

    try:
        redis = await get_redis()
        await redis.ping()
        results["redis"]["connection"] = "ok"
        info = await redis.info()
        results["redis"]["version"] = info.get("redis_version", "unknown")
    except Exception as e:
        results["redis"]["connection"] = f"error: {e}"

    return results
