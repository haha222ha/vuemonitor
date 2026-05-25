from fastapi import APIRouter

from app.api.intelligence.admin import router as admin_router
from app.api.intelligence.auth import router as auth_router
from app.api.intelligence.dashboard import router as dashboard_router
from app.api.intelligence.data import router as data_router
from app.api.intelligence.emotions import router as emotions_router
from app.api.intelligence.opportunities import router as opportunities_router
from app.api.intelligence.reports import router as reports_router
from app.api.intelligence.risks import router as risks_router
from app.api.intelligence.signals import router as signals_router
from app.api.intelligence.sync import router as sync_router
from app.api.intelligence.topics import router as topics_router
from app.api.intelligence.trends import router as trends_router

intel_router = APIRouter(prefix="/intel")

intel_router.include_router(auth_router)
intel_router.include_router(sync_router)
intel_router.include_router(admin_router)
intel_router.include_router(dashboard_router)
intel_router.include_router(trends_router)
intel_router.include_router(opportunities_router)
intel_router.include_router(risks_router)
intel_router.include_router(topics_router)
intel_router.include_router(signals_router)
intel_router.include_router(emotions_router)
intel_router.include_router(reports_router)
intel_router.include_router(data_router)