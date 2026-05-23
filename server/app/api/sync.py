import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
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


class SyncProductItem(BaseModel):
    id: str
    platform: str
    platform_product_id: str
    product_name: str | None = None
    shop_name: str | None = None
    image_url: str | None = None
    category_id: str | None = None
    category: str | None = None
    product_url: str | None = None
    is_active: bool = True
    last_collected_at: datetime | None = None
    updated_at: datetime | None = None


class SyncFeatureItem(BaseModel):
    id: str
    product_id: str
    price: float | None = None
    original_price: float | None = None
    sales_count: int | None = None
    monthly_sales: int | None = None
    rating: float | None = None
    review_count: int | None = None
    favorite_count: int | None = None
    stock_status: str | None = None
    extra_features: dict | None = None
    source: str | None = None
    collected_at: datetime | None = None


class SyncCategoryItem(BaseModel):
    id: str
    name: str
    icon: str | None = None
    color: str | None = None
    sort_order: int = 0
    parent_id: str | None = None
    updated_at: datetime | None = None


class SyncBatchPushRequest(BaseModel):
    products: list[SyncProductItem] = []
    features: list[SyncFeatureItem] = []
    categories: list[SyncCategoryItem] = []
    deletions: list[dict] = []


class SyncChangesRequest(BaseModel):
    since: datetime | None = None
    include_products: bool = True
    include_features: bool = True
    include_categories: bool = True
    include_deletions: bool = True


class SyncFullPullRequest(BaseModel):
    include_products: bool = True
    include_features: bool = True
    include_categories: bool = True
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


@router.post("/batch-push")
async def sync_batch_push(
    req: SyncBatchPushRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = SyncService(db)
    result = await svc.batch_push(
        user_id=user.id,
        products=[p.model_dump() for p in req.products],
        features=[f.model_dump() for f in req.features],
        categories=[c.model_dump() for c in req.categories],
        deletions=req.deletions,
    )
    return {"code": 0, "data": result}


@router.post("/changes")
async def sync_changes(
    req: SyncChangesRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = SyncService(db)
    result = await svc.get_changes_since(
        user_id=user.id,
        since=req.since,
        include_products=req.include_products,
        include_features=req.include_features,
        include_categories=req.include_categories,
        include_deletions=req.include_deletions,
    )
    return {"code": 0, "data": result}


@router.post("/full-pull")
async def sync_full_pull(
    req: SyncFullPullRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = SyncService(db)
    result = await svc.full_pull(
        user_id=user.id,
        since=req.since,
        include_products=req.include_products,
        include_features=req.include_features,
        include_categories=req.include_categories,
    )
    return {"code": 0, "data": result}


@router.get("/status")
async def sync_status(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = SyncService(db)
    result = await svc.get_sync_status(user_id=user.id)
    return {"code": 0, "data": result}
