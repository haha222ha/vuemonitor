import logging
import os
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.router import api_router
from app.config import get_settings
from app.core.database import init_db
from app.core.exceptions import register_exception_handlers
from app.core.graceful_shutdown import graceful_shutdown, setup_signal_handlers
from app.core.redis import close_redis
from app.core.seed import seed_feature_gates
from app.middleware.logging import StructuredLoggingMiddleware
from app.middleware.prometheus import PrometheusMiddleware, collect_system_metrics, generate_prometheus_output
from app.middleware.quota import QuotaEnforcementMiddleware
from app.middleware.rate_limit import RedisRateLimitMiddleware
from app.middleware.security_audit import SecurityAuditMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.tracing import TracingMiddleware
from app.scheduler.tasks import setup_scheduler
from app.services.aipic.cleanup_service import start_aipic_cleanup, stop_aipic_cleanup
from app.services.aipic.worker_service import start_aipic_workers, stop_aipic_workers
from app.services.alert_service import configure_structlog
from app.services.email_service import email_service
from app.services.error_capture import setup_error_capture
from app.services.sla_monitor import sla_monitor
from app.task_queue.handlers import register_builtin_handlers
from app.task_queue.queue import start_worker, stop_worker
from app.ws.manager import router as ws_router

settings = get_settings()

configure_structlog()

logger = logging.getLogger(__name__)

scheduler = setup_scheduler()

_INSECURE_DEFAULTS = {
    "JWT_SECRET": "change-me-in-production",
    "JWT_REFRESH_SECRET": "change-me-refresh-in-production",
    "ENCRYPTION_KEY": "0123456789abcdef0123456789abcdef",
    "DB_PASSWORD": "saas_pass",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await seed_feature_gates()
    scheduler.start()
    register_builtin_handlers()
    await start_worker()
    setup_signal_handlers()
    setup_error_capture()
    await sla_monitor.start()
    await start_aipic_workers()
    await start_aipic_cleanup()
    email_service.start_worker()
    graceful_shutdown.start_heartbeat()
    recovered = await graceful_shutdown.recover_from_checkpoints()
    if recovered:
        logger.info(f"Recovered {len(recovered)} tasks from previous shutdown")

    from app.services.discovery_db import DiscoveryDatabase
    db_path = settings.DISCOVERY_DB_PATH or os.environ.get("DISCOVERY_DB_PATH", "")
    if db_path and os.path.exists(db_path):
        discovery_db_instance = DiscoveryDatabase.initialize(db_path)
        await discovery_db_instance.connect()
        logger.info(f"Discovery database initialized from {db_path}")

    if not settings.DEBUG:
        for key, default in _INSECURE_DEFAULTS.items():
            if getattr(settings, key, None) == default:
                import logging
                logging.critical(f"SECURITY: {key} is using default value! Change it in production!")
    for key in ["JWT_SECRET", "JWT_REFRESH_SECRET", "ENCRYPTION_KEY", "DB_PASSWORD"]:
        if not getattr(settings, key, None):
            import logging
            logging.critical(f"SECURITY: {key} is empty! Application cannot start securely.")
            raise RuntimeError(f"SECURITY: {key} is empty. Set it in .env before starting the application.")
    yield
    scheduler.shutdown(wait=False)
    await stop_worker()
    await stop_aipic_workers()
    await stop_aipic_cleanup()
    await email_service.stop_worker()
    await close_redis()
    from app.services.discovery_db import DiscoveryDatabase
    instance = DiscoveryDatabase.get_instance()
    if instance:
        await instance.close()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    openapi_url="/openapi.json" if settings.is_development else None,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(QuotaEnforcementMiddleware)
app.add_middleware(PrometheusMiddleware)
app.add_middleware(TracingMiddleware)
app.add_middleware(SecurityAuditMiddleware)
app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(RedisRateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS_SAFE,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

register_exception_handlers(app)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    settings = get_settings()
    errors = []
    for err in exc.errors():
        loc = " -> ".join(str(l) for l in err.get("loc", []))
        errors.append(f"{loc}: {err.get('msg', '')}")
    response_detail = errors if not settings.is_production else ["参数验证失败"]
    return JSONResponse(
        status_code=422,
        content={
            "code": 422,
            "message": "请求参数验证失败",
            "detail": response_detail,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger = logging.getLogger("uvicorn.error")
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}\n{traceback.format_exc()}")

    detail = "Internal Server Error"
    if settings.is_development:
        detail = f"{type(exc).__name__}: {str(exc)[:200]}"

    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "服务器内部错误",
            "detail": detail,
        },
    )


@app.get("/health")
async def root_health():
    import time

    from app.core.database import async_session_factory
    from app.core.redis import check_redis_health

    checks: dict[str, any] = {}
    overall = "healthy"

    start = time.time()
    try:
        async with async_session_factory() as db:
            await db.execute(text("SELECT 1"))
        checks["database"] = {"status": "up", "latency_ms": round((time.time() - start) * 1000, 1)}
    except Exception as e:
        checks["database"] = {"status": "down", "error": str(e)[:100]}
        overall = "degraded"

    start = time.time()
    redis_ok = await check_redis_health()
    checks["redis"] = {
        "status": "up" if redis_ok else "down",
        "latency_ms": round((time.time() - start) * 1000, 1),
        "fallback": "memory" if not redis_ok else None,
    }
    if not redis_ok:
        overall = "degraded"

    from app.config import get_settings
    s = get_settings()
    checks["scheduler"] = {"status": "running" if scheduler.running else "stopped"}

    return {
        "status": overall,
        "timestamp": time.time(),
        "version": getattr(s, "VERSION", "unknown"),
        "checks": checks,
    }


@app.get("/metrics")
async def metrics():
    from fastapi.responses import PlainTextResponse
    await collect_system_metrics()
    return PlainTextResponse(content=generate_prometheus_output(), media_type="text/plain")

app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router)

REPORTS_STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "reports")
os.makedirs(REPORTS_STATIC_DIR, exist_ok=True)
app.mount("/static/reports", StaticFiles(directory=REPORTS_STATIC_DIR), name="static-reports")


@app.post("/api/v1/monitoring/web-vitals")
async def receive_web_vitals(request: Request):
    import logging
    try:
        body = await request.json()
        metrics = body.get("metrics", [])
        logger = logging.getLogger("web_vitals")
        for m in metrics:
            logger.info(
                "metric=%s value=%.2f rating=%s nav=%s",
                m.get("name"), m.get("value", 0), m.get("rating"), m.get("navigationType"),
            )
    except Exception as e:
        logger.debug("Web vitals metrics parse failed: %s", e)
    return {"ok": True}
