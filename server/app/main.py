from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.core.database import init_db
from app.core.exceptions import register_exception_handlers
from app.core.redis import close_redis
from app.middleware.rate_limit import RedisRateLimitMiddleware
from app.scheduler.tasks import setup_scheduler
from app.ws.manager import router as ws_router

settings = get_settings()

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
    if not settings.DEBUG:
        for key, default in _INSECURE_DEFAULTS.items():
            if getattr(settings, key, None) == default:
                import logging
                logging.critical(f"SECURITY: {key} is using default value! Change it in production!")
    yield
    scheduler.shutdown(wait=False)
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(RedisRateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

register_exception_handlers(app)

app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router)
