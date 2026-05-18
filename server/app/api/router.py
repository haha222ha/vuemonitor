from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.sync import router as sync_router
from app.api.products import router as products_router
from app.api.monitor import router as monitor_router
from app.api.collect import router as collect_router
from app.api.ai import router as ai_router
from app.api.admin import router as admin_router
from app.api.dashboard import router as dashboard_router
from app.api.notifications import router as notifications_router
from app.api.license import router as license_router
from app.api.users import router as users_router
from app.api.feature import router as feature_router
from app.api.teams import router as teams_router
from app.api.alert_rules import router as alert_rules_router
from app.api.ai_templates import router as ai_templates_router
from app.api.security_audit import router as security_audit_router
from app.api.gdpr import router as gdpr_router
from app.api.operation_audit import router as operation_audit_router
from app.api.task_queue import router as task_queue_router
from app.api.system import router as system_router

api_router = APIRouter()

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
async def diagnose():
    from sqlalchemy import text
    from app.core.database import engine, async_session_factory
    from app.core.redis import get_redis
    import traceback

    results = {"database": {}, "redis": {}, "tables": {}, "auth_test": {}}

    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            results["database"]["connection"] = "ok"
    except Exception as e:
        results["database"]["connection"] = f"error: {e}"
        results["database"]["traceback"] = traceback.format_exc()

    try:
        async with engine.begin() as conn:
            result = await conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
            )
            tables = [row[0] for row in result]
            results["tables"]["list"] = tables
            results["tables"]["count"] = len(tables)
    except Exception as e:
        results["tables"]["error"] = str(e)

    required_tables = ["users", "refresh_tokens", "products", "monitor_tasks", "alert_rules", "alert_events", "security_audit_log"]
    if "list" in results["tables"]:
        results["tables"]["missing"] = [t for t in required_tables if t not in results["tables"]["list"]]

    try:
        async with async_session_factory() as session:
            result = await session.execute(text("SELECT count(*) FROM users"))
            count = result.scalar()
            results["auth_test"]["user_count"] = count
    except Exception as e:
        results["auth_test"]["query_error"] = str(e)
        results["auth_test"]["traceback"] = traceback.format_exc()

    try:
        redis = await get_redis()
        await redis.ping()
        results["redis"]["connection"] = "ok"
        info = await redis.info()
        results["redis"]["version"] = info.get("redis_version", "unknown")
    except Exception as e:
        results["redis"]["connection"] = f"error: {e}"

    return results
