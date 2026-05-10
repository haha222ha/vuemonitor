import re
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

PLATFORM_PATTERNS = {
    "xhs": [
        re.compile(r"xiaohongshu\.com/explore/([a-f0-9]{24})", re.I),
        re.compile(r"xiaohongshu\.com/discovery/item/([a-f0-9]{24})", re.I),
        re.compile(r"xhslink\.com/(\w+)", re.I),
    ],
}


def parse_product_url(url: str) -> tuple[str | None, str | None]:
    for platform, patterns in PLATFORM_PATTERNS.items():
        for pattern in patterns:
            m = pattern.search(url)
            if m:
                return platform, m.group(1)
    return None, None


class ProductCreateRequest(BaseModel):
    platform: str | None = Field(None, pattern="^xhs$")
    platform_product_id: str | None = Field(None, min_length=1, max_length=255)
    product_name: str | None = Field(None, min_length=1, max_length=500)
    url: str | None = None
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
        raise ForbiddenException(code=42011, message=f"当前套餐最多监控{limits['maxProducts']}个笔�?)

    platform = req.platform
    platform_product_id = req.platform_product_id
    product_url = req.product_url

    if req.url and (not platform or not platform_product_id):
        parsed_platform, parsed_id = parse_product_url(req.url)
        if parsed_platform and parsed_id:
            platform = platform or parsed_platform
            platform_product_id = platform_product_id or parsed_id
            product_url = product_url or req.url
        else:
            raise BadRequestException(message="无法识别该链接，请手动输入商品ID")

    if not platform or not platform_product_id:
        raise BadRequestException(message="请提供商品URL或手动输入商品ID")

    product_name = req.product_name or f"小红书笔�?{platform_product_id[:8]}"

    existing = await db.execute(
        select(Product).where(
            Product.user_id == user.id,
            Product.platform == platform,
            Product.platform_product_id == platform_product_id,
        )
    )
    if existing.scalar_one_or_none():
        raise BadRequestException(message="该商品已添加")

    product = Product(
        user_id=user.id,
        platform=platform,
        platform_product_id=platform_product_id,
        product_name=product_name,
        shop_name=req.shop_name,
        category=req.category,
        image_url=req.image_url,
        product_url=product_url,
    )
    db.add(product)
    await db.flush()

    await gate.record_usage(user.id, "gate:monitor:add")

    return {"code": 0, "data": {"id": str(product.id), "platform": platform, "platform_product_id": platform_product_id}}


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

        prev_feat = None
        if feat:
            prev_result = await db.execute(
                select(ProductFeature)
                .where(ProductFeature.product_id == p.id, ProductFeature.id != feat.id)
                .order_by(ProductFeature.collected_at.desc())
                .limit(1)
            )
            prev_feat = prev_result.scalar_one_or_none()

        trend = 0.0
        if feat and prev_feat and feat.sales_count and prev_feat.sales_count and prev_feat.sales_count > 0:
            trend = round((feat.sales_count - prev_feat.sales_count) / prev_feat.sales_count * 100, 1)

        items.append({
            "id": str(p.id),
            "platform": p.platform,
            "platform_product_id": p.platform_product_id,
            "product_name": p.product_name,
            "shop_name": p.shop_name,
            "category": p.category,
            "image_url": p.image_url,
            "product_url": p.product_url,
            "is_active": p.is_active,
            "last_collected_at": p.last_collected_at.isoformat() if p.last_collected_at else None,
            "trend": trend,
            "latest_feature": {
                "id": str(feat.id),
                "price": float(feat.price) if feat and feat.price else None,
                "original_price": float(feat.original_price) if feat and feat.original_price else None,
                "sales_count": feat.sales_count if feat else None,
                "monthly_sales": feat.monthly_sales if feat else None,
                "rating": float(feat.rating) if feat and feat.rating else None,
                "review_count": feat.review_count if feat else None,
                "favorite_count": feat.favorite_count if feat else None,
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
        raise NotFoundException(message="商品不存�?)

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
        raise NotFoundException(message="商品不存�?)

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
        raise NotFoundException(message="商品不存�?)

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
