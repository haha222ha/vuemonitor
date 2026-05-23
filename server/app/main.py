import logging
import os
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
    await close_redis()
    from app.services.discovery_db import DiscoveryDatabase
    instance = DiscoveryDatabase.get_instance()
    if instance:
        await instance.close()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger = logging.getLogger("uvicorn.error")
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "服务器内部错误",
            "detail": str(exc) if settings.DEBUG else "Internal Server Error",
        },
    )


@app.get("/health")
async def root_health():
    return {"status": "ok"}


@app.get("/metrics")
async def metrics():
    from fastapi.responses import PlainTextResponse
    await collect_system_metrics()
    return PlainTextResponse(content=generate_prometheus_output(), media_type="text/plain")

app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router)
