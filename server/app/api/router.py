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


@api_router.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
