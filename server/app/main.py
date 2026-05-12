from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.core.database import init_db
from app.core.exceptions import register_exception_handlers
from app.core.redis import close_redis
from app.middleware.rate_limit import RedisRateLimitMiddleware
from app.middleware.logging import StructuredLoggingMiddleware
from app.middleware.security_audit import SecurityAuditMiddleware
from app.middleware.quota import QuotaEnforcementMiddleware
from app.middleware.prometheus import PrometheusMiddleware, generate_prometheus_output, collect_system_metrics
from app.middleware.tracing import TracingMiddleware
from app.scheduler.tasks import setup_scheduler
from app.services.alert_service import configure_structlog, alert_service
from app.services.error_capture import setup_error_capture, error_capture
from app.services.sla_monitor import sla_monitor
from app.task_queue.handlers import register_builtin_handlers
from app.task_queue.queue import start_worker, stop_worker
from app.core.graceful_shutdown import graceful_shutdown, setup_signal_handlers
from app.ws.manager import router as ws_router

settings = get_settings()

configure_structlog()

scheduler = setup_scheduler()

_INSECURE_DEFAULTS = {
    "JWT_SECRET": "change-me-in-production",
    "JWT_REFRESH_SECRET": "change-me-refresh-in-production",
    "ENCRYPTION_KEY": "0123456789abcdef0123456789abcdef",
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    scheduler.start()
    register_builtin_handlers()
    await start_worker()
    setup_signal_handlers()
    setup_error_capture()
    await sla_monitor.start()
    recovered = await graceful_shutdown.recover_from_checkpoints()
    if recovered:
        logger.info(f"Recovered {len(recovered)} tasks from previous shutdown")
    if not settings.DEBUG:
        for key, default in _INSECURE_DEFAULTS.items():
            if getattr(settings, key, None) == default:
                import logging
                logging.critical(f"SECURITY: {key} is using default value! Change it in production!")
    yield
    scheduler.shutdown(wait=False)
    await stop_worker()
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(QuotaEnforcementMiddleware)
app.add_middleware(PrometheusMiddleware)
app.add_middleware(TracingMiddleware)
app.add_middleware(SecurityAuditMiddleware)
app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(RedisRateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

register_exception_handlers(app)

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
