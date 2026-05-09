import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import CurrentUser
from app.services.sync_service import SyncService

router = APIRouter(prefix="/sync", tags=["sync"])


class SyncPushRequest(BaseModel):
    platform: str
    platform_product_id: str
    features: list[dict]


class SyncPullRequest(BaseModel):
    product_id: str | None = None
    since: datetime | None = None


@router.post("/push")
async def sync_push(
    req: SyncPushRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = SyncService(db)
    result = await svc.push_features_to_cloud(
        user_id=user.id,
        platform=req.platform,
        platform_product_id=req.platform_product_id,
        features=req.features,
    )
    return {"code": 0, "data": result}


@router.post("/pull")
async def sync_pull(
    req: SyncPullRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = SyncService(db)
    product_id = uuid.UUID(req.product_id) if req.product_id else None
    features = await svc.pull_features_from_cloud(
        user_id=user.id,
        product_id=product_id,
        since=req.since,
    )
    return {"code": 0, "data": features}
