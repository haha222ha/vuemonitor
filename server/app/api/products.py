import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.middleware.auth import CurrentUser
from app.middleware.feature_gate import FeatureGateMiddleware
from shared.constants.feature_gates import PLAN_LIMITS
from app.models.product import Product, ProductFeature

router = APIRouter(prefix="/products", tags=["products"])


class ProductCreateRequest(BaseModel):
    platform: str = Field(..., pattern="^(xhs|douyin|taobao|jd|pdd)$")
    platform_product_id: str = Field(..., min_length=1, max_length=255)
    product_name: str = Field(..., min_length=1, max_length=500)
    shop_name: str | None = None
    category: str | None = None
    image_url: str | None = None
    product_url: str | None = None


class ProductUpdateRequest(BaseModel):
    product_name: str | None = None
    shop_name: str | None = None
    category: str | None = None
    image_url: str | None = None
    is_active: bool | None = None


class ProductFeatureResponse(BaseModel):
    id: str
    price: float | None
    original_price: float | None
    sales_count: int | None
    monthly_sales: int | None
    rating: float | None
    review_count: int | None
    favorite_count: int | None
    stock_status: str | None
    extra_features: dict
    source: str
    collected_at: str | None


class ProductDetailResponse(BaseModel):
    id: str
    platform: str
    platform_product_id: str
    product_name: str
    shop_name: str | None
    category: str | None
    image_url: str | None
    product_url: str | None
    is_active: bool
    last_collected_at: str | None
    latest_feature: ProductFeatureResponse | None


@router.post("", status_code=201)
async def create_product(
    req: ProductCreateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    gate = FeatureGateMiddleware(db)
    await gate.check_gate(user, "gate:monitor:add")

    count_result = await db.execute(
        select(func.count()).where(Product.user_id == user.id, Product.is_active == True)
    )
    limits = PLAN_LIMITS.get(user.plan, PLAN_LIMITS["free"])
    if limits["maxProducts"] > 0 and (count_result.scalar() or 0) >= limits["maxProducts"]:
        raise ForbiddenException(code=42011, message=f"当前套餐最多监控{limits['maxProducts']}个商品")

    existing = await db.execute(
        select(Product).where(
            Product.user_id == user.id,
            Product.platform == req.platform,
            Product.platform_product_id == req.platform_product_id,
        )
    )
    if existing.scalar_one_or_none():
        raise BadRequestException(message="该商品已添加")

    product = Product(
        user_id=user.id,
        platform=req.platform,
        platform_product_id=req.platform_product_id,
        product_name=req.product_name,
        shop_name=req.shop_name,
        category=req.category,
        image_url=req.image_url,
        product_url=req.product_url,
    )
    db.add(product)
    await db.flush()

    await gate.record_usage(user.id, "gate:monitor:add")

    return {"code": 0, "data": {"id": str(product.id)}}


@router.get("")
async def list_products(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    platform: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    query = select(Product).where(Product.user_id == user.id)
    if platform:
        query = query.where(Product.platform == platform)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    query = query.order_by(Product.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    products = result.scalars().all()

    items = []
    for p in products:
        feat_result = await db.execute(
            select(ProductFeature)
            .where(ProductFeature.product_id == p.id)
            .order_by(ProductFeature.collected_at.desc())
            .limit(1)
        )
        feat = feat_result.scalar_one_or_none()

        items.append({
            "id": str(p.id),
            "platform": p.platform,
            "platform_product_id": p.platform_product_id,
            "product_name": p.product_name,
            "shop_name": p.shop_name,
            "category": p.category,
            "image_url": p.image_url,
            "is_active": p.is_active,
            "last_collected_at": p.last_collected_at.isoformat() if p.last_collected_at else None,
            "latest_feature": {
                "id": str(feat.id),
                "price": float(feat.price) if feat and feat.price else None,
                "sales_count": feat.sales_count if feat else None,
                "rating": float(feat.rating) if feat and feat.rating else None,
                "review_count": feat.review_count if feat else None,
                "source": feat.source if feat else None,
                "collected_at": feat.collected_at.isoformat() if feat and feat.collected_at else None,
            } if feat else None,
        })

    return {"code": 0, "data": {"total": total, "page": page, "page_size": page_size, "items": items}}


@router.get("/{product_id}")
async def get_product(
    product_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(Product.id == uuid.UUID(product_id), Product.user_id == user.id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundException(message="商品不存在")

    feat_result = await db.execute(
        select(ProductFeature)
        .where(ProductFeature.product_id == product.id)
        .order_by(ProductFeature.collected_at.desc())
        .limit(1)
    )
    feat = feat_result.scalar_one_or_none()

    return {
        "code": 0,
        "data": {
            "id": str(product.id),
            "platform": product.platform,
            "platform_product_id": product.platform_product_id,
            "product_name": product.product_name,
            "shop_name": product.shop_name,
            "category": product.category,
            "image_url": product.image_url,
            "product_url": product.product_url,
            "is_active": product.is_active,
            "last_collected_at": product.last_collected_at.isoformat() if product.last_collected_at else None,
            "latest_feature": {
                "id": str(feat.id),
                "price": float(feat.price) if feat and feat.price else None,
                "original_price": float(feat.original_price) if feat and feat.original_price else None,
                "sales_count": feat.sales_count if feat else None,
                "monthly_sales": feat.monthly_sales if feat else None,
                "rating": float(feat.rating) if feat and feat.rating else None,
                "review_count": feat.review_count if feat else None,
                "favorite_count": feat.favorite_count if feat else None,
                "stock_status": feat.stock_status if feat else None,
                "extra_features": feat.extra_features if feat else {},
                "source": feat.source if feat else None,
                "collected_at": feat.collected_at.isoformat() if feat and feat.collected_at else None,
            } if feat else None,
        },
    }


@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(Product.id == uuid.UUID(product_id), Product.user_id == user.id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundException(message="商品不存在")

    await db.delete(product)
    return {"code": 0, "data": {"deleted": True}}


@router.get("/{product_id}/features")
async def list_product_features(
    product_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    product_result = await db.execute(
        select(Product).where(Product.id == uuid.UUID(product_id), Product.user_id == user.id)
    )
    if not product_result.scalar_one_or_none():
        raise NotFoundException(message="商品不存在")

    query = (
        select(ProductFeature)
        .where(ProductFeature.product_id == uuid.UUID(product_id))
        .order_by(ProductFeature.collected_at.desc())
    )
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    features = (await db.execute(query.offset((page - 1) * page_size).limit(page_size))).scalars().all()

    return {
        "code": 0,
        "data": {
            "total": total,
            "items": [
                {
                    "id": str(f.id),
                    "price": float(f.price) if f.price else None,
                    "original_price": float(f.original_price) if f.original_price else None,
                    "sales_count": f.sales_count,
                    "monthly_sales": f.monthly_sales,
                    "rating": float(f.rating) if f.rating else None,
                    "review_count": f.review_count,
                    "favorite_count": f.favorite_count,
                    "stock_status": f.stock_status,
                    "extra_features": f.extra_features,
                    "source": f.source,
                    "collected_at": f.collected_at.isoformat() if f.collected_at else None,
                }
                for f in features
            ],
        },
    }
