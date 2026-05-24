import csv
import io
import re
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from shared.constants.feature_gates import PLAN_LIMITS
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get, cache_set, invalidate_user_cache
from app.core.database import get_db
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.middleware.auth import CurrentUser
from app.middleware.feature_gate import FeatureGateMiddleware
from app.models.product import Product, ProductFeature
from app.services.operation_audit import record_operation

router = APIRouter(prefix="/products", tags=["products"])

PLATFORM_PATTERNS = {
    "xhs": [
        re.compile(r"xiaohongshu\.com/explore/([a-f0-9]{24})", re.I),
        re.compile(r"xiaohongshu\.com/discovery/item/([a-f0-9]{24})", re.I),
        re.compile(r"xhslink\.com/(\w+)", re.I),
    ],
    "douyin": [
        re.compile(r"douyin\.com/video/(\d+)", re.I),
        re.compile(r"iesdouyin\.com/share/video/(\d+)", re.I),
        re.compile(r"v\.douyin\.com/(\w+)", re.I),
    ],
    "taobao": [
        re.compile(r"item\.taobao\.com/item\.htm\?.*id=(\d+)", re.I),
        re.compile(r"detail\.tmall\.com/item\.htm\?.*id=(\d+)", re.I),
        re.compile(r"m\.taobao\.com/\?.*id=(\d+)", re.I),
    ],
    "jd": [
        re.compile(r"item\.jd\.com/(\d+)", re.I),
        re.compile(r"item\.jd\.hk/(\d+)", re.I),
        re.compile(r"item\.m\.jd\.com/product/(\d+)", re.I),
    ],
    "pdd": [
        re.compile(r"yangkeduo\.com/goods\.html\?.*goods_id=(\d+)", re.I),
        re.compile(r"mobile\.yangkeduo\.com/goods\.html\?.*goods_id=(\d+)", re.I),
        re.compile(r"pinduoduo\.com/goods\.html\?.*goods_id=(\d+)", re.I),
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
    platform: str | None = Field(None, pattern="^(xhs|douyin|taobao|jd|pdd)$")
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
        select(func.count()).where(Product.user_id == user.id, Product.is_active)
    )
    limits = PLAN_LIMITS.get(user.plan, PLAN_LIMITS["free"])
    if limits["maxProducts"] > 0 and (count_result.scalar() or 0) >= limits["maxProducts"]:
        raise ForbiddenException(code=42011, message=f"当前套餐最多监控{limits['maxProducts']}个商品")

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

    product_name = req.product_name or f"{platform}商品{platform_product_id[:8]}"

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

    await record_operation(
        user_id=str(user.id),
        action="create",
        resource_type="product",
        resource_id=str(product.id),
        detail=f"platform={platform}, name={product_name[:30]}",
    )

    await invalidate_user_cache(str(user.id))

    return {"code": 0, "data": {"id": str(product.id), "platform": platform, "platform_product_id": platform_product_id}}


class BatchImportItem(BaseModel):
    platform: str = Field(..., pattern="^(xhs|douyin|taobao|jd|pdd)$")
    platform_product_id: str = Field(..., min_length=1, max_length=255)
    product_name: str | None = Field(None, min_length=1, max_length=500)
    url: str | None = None
    shop_name: str | None = None
    category: str | None = None
    image_url: str | None = None


class BatchImportRequest(BaseModel):
    items: list[BatchImportItem] = Field(..., min_length=1, max_length=100)


@router.post("/batch-import")
async def batch_import_products(
    req: BatchImportRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    gate = FeatureGateMiddleware(db)
    await gate.check_gate(user, "gate:import:excel")

    limits = PLAN_LIMITS.get(user.plan, PLAN_LIMITS["free"])
    count_result = await db.execute(
        select(func.count()).where(Product.user_id == user.id, Product.is_active)
    )
    current_count = count_result.scalar() or 0
    remaining = limits["maxProducts"] - current_count if limits["maxProducts"] > 0 else len(req.items)

    added = []
    skipped = []
    for item in req.items:
        if limits["maxProducts"] > 0 and len(added) >= remaining:
            skipped.append({"platform_product_id": item.platform_product_id, "reason": "商品数量已达上限"})
            continue

        existing = await db.execute(
            select(Product).where(
                Product.user_id == user.id,
                Product.platform == item.platform,
                Product.platform_product_id == item.platform_product_id,
            )
        )
        if existing.scalar_one_or_none():
            skipped.append({"platform_product_id": item.platform_product_id, "reason": "商品已存在"})
            continue

        product_url = item.url
        if item.url and not product_url:
            product_url = item.url

        product = Product(
            user_id=user.id,
            platform=item.platform,
            platform_product_id=item.platform_product_id,
            product_name=item.product_name or f"{item.platform}商品{item.platform_product_id[:8]}",
            shop_name=item.shop_name,
            category=item.category,
            image_url=item.image_url,
            product_url=product_url,
        )
        db.add(product)
        added.append(item.platform_product_id)

    await db.flush()
    await gate.record_usage(user.id, "gate:import:excel")

    await record_operation(
        user_id=str(user.id),
        action="batch_import",
        resource_type="product",
        resource_id="batch",
        detail=f"added={len(added)}, skipped={len(skipped)}",
    )

    await invalidate_user_cache(str(user.id))

    return {
        "code": 0,
        "data": {
            "added_count": len(added),
            "skipped_count": len(skipped),
            "skipped": skipped[:10],
        },
    }


@router.get("")
async def list_products(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    platform: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    cache_key = f"products:list:{user.id}:{platform}:{page}:{page_size}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return {"code": 0, "data": cached}

    query = select(Product).where(Product.user_id == user.id)
    if platform:
        query = query.where(Product.platform == platform)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    query = query.order_by(Product.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    products = result.scalars().all()

    product_ids = [p.id for p in products]

    items = []
    if product_ids:
        ranked_features = (
            select(
                ProductFeature.product_id,
                ProductFeature.id,
                ProductFeature.price,
                ProductFeature.original_price,
                ProductFeature.sales_count,
                ProductFeature.monthly_sales,
                ProductFeature.rating,
                ProductFeature.review_count,
                ProductFeature.favorite_count,
                ProductFeature.source,
                ProductFeature.collected_at,
                func.row_number()
                .over(partition_by=ProductFeature.product_id, order_by=ProductFeature.collected_at.desc())
                .label("rn"),
            )
            .where(ProductFeature.product_id.in_(product_ids))
            .subquery()
        )

        feat_rows = await db.execute(
            select(
                ranked_features.c.product_id,
                ranked_features.c.id,
                ranked_features.c.price,
                ranked_features.c.original_price,
                ranked_features.c.sales_count,
                ranked_features.c.monthly_sales,
                ranked_features.c.rating,
                ranked_features.c.review_count,
                ranked_features.c.favorite_count,
                ranked_features.c.source,
                ranked_features.c.collected_at,
                ranked_features.c.rn,
            )
            .where(ranked_features.c.rn <= 2)
            .order_by(ranked_features.c.product_id, ranked_features.c.rn)
        )

        feat_map: dict = {}
        for row in feat_rows.all():
            pid = row[0]
            if pid not in feat_map:
                feat_map[pid] = []
            feat_map[pid].append(row)

        for p in products:
            feats = feat_map.get(p.id, [])
            latest = feats[0] if len(feats) >= 1 else None
            prev = feats[1] if len(feats) >= 2 else None

            trend = 0.0
            if latest and prev and latest[5] and prev[5] and prev[5] > 0 and latest[5]:
                trend = round((latest[5] - prev[5]) / prev[5] * 100, 1)

            growth_24h = None
            if latest and prev and latest[11] and prev[11]:
                time_diff = (latest[11] - prev[11]).total_seconds()
                if time_diff <= 86400 and prev[5] is not None and latest[5] is not None:
                    sales_delta = latest[5] - prev[5]
                    sales_pct = round(sales_delta / prev[5] * 100, 1) if prev[5] > 0 else None
                    revenue_delta = None
                    if latest[3] is not None and sales_delta > 0:
                        revenue_delta = round(float(latest[3]) * sales_delta, 2)
                    growth_24h = {
                        "sales_delta": sales_delta,
                        "sales_pct": sales_pct,
                        "revenue_delta": revenue_delta,
                    }

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
                "growth_24h": growth_24h,
                "latest_feature": {
                    "id": str(latest[1]),
                    "price": float(latest[3]) if latest and latest[3] else None,
                    "original_price": float(latest[4]) if latest and latest[4] else None,
                    "sales_count": latest[5] if latest else None,
                    "monthly_sales": latest[6] if latest else None,
                    "rating": float(latest[7]) if latest and latest[7] else None,
                    "review_count": latest[8] if latest else None,
                    "favorite_count": latest[9] if latest else None,
                    "source": latest[10] if latest else None,
                    "collected_at": latest[11].isoformat() if latest and latest[11] else None,
                } if latest else None,
            })
    else:
        for p in products:
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
                "trend": 0.0,
                "growth_24h": None,
                "latest_feature": None,
            })

    list_data = {"total": total, "page": page, "page_size": page_size, "items": items}
    await cache_set(cache_key, list_data, ttl_seconds=60)

    return {"code": 0, "data": list_data}


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

    await record_operation(
        user_id=str(user.id),
        action="delete",
        resource_type="product",
        resource_id=product_id,
        detail=f"name={product.product_name[:30] if product.product_name else ''}",
    )

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


@router.get("/export/csv")
async def export_products_csv(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    platform: str | None = None,
):
    query = select(Product).where(Product.user_id == user.id)
    if platform:
        query = query.where(Product.platform == platform)

    result = await db.execute(query.order_by(Product.updated_at.desc()))
    products = result.scalars().all()

    product_ids = [p.id for p in products]
    latest_features: dict[uuid.UUID, ProductFeature] = {}
    if product_ids:
        feat_result = await db.execute(
            select(ProductFeature)
            .where(ProductFeature.product_id.in_(product_ids))
            .order_by(ProductFeature.product_id, ProductFeature.collected_at.desc())
        )
        for feat in feat_result.scalars().all():
            if feat.product_id not in latest_features:
                latest_features[feat.product_id] = feat

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "商品ID", "平台", "平台商品ID", "商品名称", "店铺名称", "分类",
        "最新价格", "最新销量", "月销量", "评分", "评论数", "收藏数",
        "最后采集时间", "商品链接",
    ])

    for p in products:
        feat = latest_features.get(p.id)

        writer.writerow([
            str(p.id),
            p.platform,
            p.platform_product_id,
            p.product_name or "",
            p.shop_name or "",
            p.category or "",
            float(feat.price) if feat and feat.price else "",
            feat.sales_count if feat else "",
            feat.monthly_sales if feat else "",
            float(feat.rating) if feat and feat.rating else "",
            feat.review_count if feat else "",
            feat.favorite_count if feat else "",
            feat.collected_at.isoformat() if feat and feat.collected_at else "",
            p.product_url or "",
        ])

    output.seek(0)
    filename = f"xhs365_products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/json")
async def export_products_json(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    platform: str | None = None,
):
    query = select(Product).where(Product.user_id == user.id)
    if platform:
        query = query.where(Product.platform == platform)

    result = await db.execute(query.order_by(Product.updated_at.desc()))
    products = result.scalars().all()

    product_ids = [p.id for p in products]
    latest_features: dict[uuid.UUID, ProductFeature] = {}
    if product_ids:
        feat_result = await db.execute(
            select(ProductFeature)
            .where(ProductFeature.product_id.in_(product_ids))
            .order_by(ProductFeature.product_id, ProductFeature.collected_at.desc())
        )
        for feat in feat_result.scalars().all():
            if feat.product_id not in latest_features:
                latest_features[feat.product_id] = feat

    export_data = []
    for p in products:
        feat = latest_features.get(p.id)

        product_data = {
            "id": str(p.id),
            "platform": p.platform,
            "platform_product_id": p.platform_product_id,
            "product_name": p.product_name,
            "shop_name": p.shop_name,
            "category": p.category,
            "product_url": p.product_url,
            "is_active": p.is_active,
            "last_collected_at": p.last_collected_at.isoformat() if p.last_collected_at else None,
        }

        if feat:
            product_data["latest_feature"] = {
                "price": float(feat.price) if feat.price else None,
                "sales_count": feat.sales_count,
                "monthly_sales": feat.monthly_sales,
                "rating": float(feat.rating) if feat.rating else None,
                "review_count": feat.review_count,
                "favorite_count": feat.favorite_count,
                "collected_at": feat.collected_at.isoformat() if feat.collected_at else None,
            }

        export_data.append(product_data)

    return {"code": 0, "data": {"items": export_data, "total": len(export_data)}}


@router.post("/compare")
async def compare_products(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    product_ids: list[str] = Query(..., description="商品ID列表"),
):
    if len(product_ids) < 2 or len(product_ids) > 10:
        raise BadRequestException(message="对比商品数量需在2-10之间")

    uuid_ids = [uuid.UUID(pid) for pid in product_ids]
    result = await db.execute(
        select(Product).where(Product.id.in_(uuid_ids), Product.user_id == user.id)
    )
    products = result.scalars().all()

    if len(products) < 2:
        raise BadRequestException(message="有效商品不足2个")

    product_id_list = [p.id for p in products]
    feat_result = await db.execute(
        select(ProductFeature)
        .where(ProductFeature.product_id.in_(product_id_list))
        .order_by(ProductFeature.product_id, ProductFeature.collected_at.desc())
    )
    all_features = feat_result.scalars().all()

    latest_features: dict[uuid.UUID, ProductFeature] = {}
    for feat in all_features:
        if feat.product_id not in latest_features:
            latest_features[feat.product_id] = feat

    compare_items = []
    for p in products:
        feat: ProductFeature | None = latest_features.get(p.id)
        compare_items.append({
            "id": str(p.id),
            "product_name": p.product_name,
            "platform": p.platform,
            "shop_name": p.shop_name,
            "category": p.category,
            "image_url": p.image_url,
            "product_url": p.product_url,
            "price": float(feat.price) if feat and feat.price else None,
            "original_price": float(feat.original_price) if feat and feat.original_price else None,
            "sales_count": feat.sales_count if feat else None,
            "monthly_sales": feat.monthly_sales if feat else None,
            "rating": float(feat.rating) if feat and feat.rating else None,
            "review_count": feat.review_count if feat else None,
            "favorite_count": feat.favorite_count if feat else None,
        })

    metrics = ["price", "original_price", "sales_count", "monthly_sales", "rating", "review_count", "favorite_count"]
    comparison: dict[str, dict] = {}
    for metric in metrics:
        values = [(item["product_name"], item[metric]) for item in compare_items if item[metric] is not None]
        if not values:
            comparison[metric] = {"best": None, "worst": None, "values": [], "direction": ""}
            continue

        if metric in ("price", "original_price"):
            sorted_vals = sorted(values, key=lambda x: x[1] if x[1] is not None else 0)
            comparison[metric] = {
                "best": sorted_vals[0],
                "worst": sorted_vals[-1],
                "values": values,
                "direction": "lower_better",
            }
        else:
            sorted_vals = sorted(values, key=lambda x: x[1] if x[1] is not None else 0, reverse=True)
            comparison[metric] = {
                "best": sorted_vals[0],
                "worst": sorted_vals[-1],
                "values": values,
                "direction": "higher_better",
            }

    return {"code": 0, "data": {"items": compare_items, "comparison": comparison}}


@router.get("/{product_id}/growth-24h")
async def get_product_growth_24h(
    product_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    gate = FeatureGateMiddleware(db)
    await gate.check_gate(user, "gate:monitor:growth_24h")

    try:
        pid = uuid.UUID(product_id)
    except ValueError:
        raise BadRequestException(message="无效的商品ID")

    result = await db.execute(
        select(Product).where(Product.id == pid, Product.user_id == user.id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundException(message="商品不存在")

    from datetime import timedelta


    now_24h_ago = datetime.now(UTC) - timedelta(hours=24)

    feat_result = await db.execute(
        select(ProductFeature)
        .where(ProductFeature.product_id == pid, ProductFeature.collected_at >= now_24h_ago)
        .order_by(ProductFeature.collected_at.asc())
    )
    features_24h = feat_result.scalars().all()

    latest_result = await db.execute(
        select(ProductFeature)
        .where(ProductFeature.product_id == pid)
        .order_by(ProductFeature.collected_at.desc())
        .limit(1)
    )
    latest = latest_result.scalar_one_or_none()

    if not latest or not features_24h:
        return {
            "code": 0,
            "data": {
                "product_id": product_id,
                "growth": None,
                "snapshots": [],
            },
        }

    oldest = features_24h[0]
    growth = {}
    metric_fields = [
        ("price", "price"),
        ("sales_count", "sales_count"),
        ("monthly_sales", "monthly_sales"),
        ("review_count", "review_count"),
        ("favorite_count", "favorite_count"),
    ]

    for field_name, label in metric_fields:
        old_val = getattr(oldest, field_name, None)
        new_val = getattr(latest, field_name, None)
        if old_val is not None and new_val is not None and float(old_val) != 0:
            change = float(new_val) - float(old_val)
            pct = (change / float(old_val)) * 100
            growth[label] = {
                "old_value": float(old_val),
                "new_value": float(new_val),
                "change": round(change, 2),
                "change_pct": round(pct, 2),
            }
        elif old_val is not None and new_val is not None:
            growth[label] = {
                "old_value": float(old_val),
                "new_value": float(new_val),
                "change": float(new_val) - float(old_val),
                "change_pct": None,
            }

    snapshots = []
    for f in features_24h:
        snapshots.append({
            "collected_at": f.collected_at.isoformat() if f.collected_at else None,
            "price": float(f.price) if f.price else None,
            "sales_count": f.sales_count,
            "monthly_sales": f.monthly_sales,
            "review_count": f.review_count,
            "favorite_count": f.favorite_count,
        })

    return {
        "code": 0,
        "data": {
            "product_id": product_id,
            "growth": growth,
            "snapshots": snapshots,
        },
    }


@router.post("/compare-trends")
async def compare_products_trends(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    product_ids: list[str] = Query(..., description="商品ID列表"),
    days: int = Query(7, ge=1, le=30, description="趋势天数"),
):
    gate = FeatureGateMiddleware(db)
    await gate.check_gate(user, "gate:monitor:compare")

    if len(product_ids) < 2 or len(product_ids) > 10:
        raise BadRequestException(message="对比商品数量需在2-10之间")

    from datetime import timedelta

    uuid_ids = [uuid.UUID(pid) for pid in product_ids]
    result = await db.execute(
        select(Product).where(Product.id.in_(uuid_ids), Product.user_id == user.id)
    )
    products = result.scalars().all()

    if len(products) < 2:
        raise BadRequestException(message="有效商品不足2个")

    since = datetime.now(UTC) - timedelta(days=days)
    product_id_list = [p.id for p in products]

    feat_result = await db.execute(
        select(ProductFeature)
        .where(
            ProductFeature.product_id.in_(product_id_list),
            ProductFeature.collected_at >= since,
        )
        .order_by(ProductFeature.product_id, ProductFeature.collected_at.asc())
    )
    all_features = feat_result.scalars().all()

    product_map = {str(p.id): p for p in products}
    trends: dict[str, list] = {str(p.id): [] for p in products}

    for feat in all_features:
        pid = str(feat.product_id)
        trends[pid].append({
            "collected_at": feat.collected_at.isoformat() if feat.collected_at else None,
            "price": float(feat.price) if feat.price else None,
            "sales_count": feat.sales_count,
            "monthly_sales": feat.monthly_sales,
            "review_count": feat.review_count,
            "favorite_count": feat.favorite_count,
        })

    series = []
    for pid, data_points in trends.items():
        p = product_map.get(pid)
        if not p:
            continue
        series.append({
            "product_id": pid,
            "product_name": p.product_name,
            "platform": p.platform,
            "data": data_points,
        })

    return {
        "code": 0,
        "data": {
            "days": days,
            "series": series,
            "metrics": ["price", "sales_count", "monthly_sales", "review_count", "favorite_count"],
        },
    }


@router.get("/{product_id}/sparkline")
async def get_product_sparkline(
    product_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    metric: str = Query("sales_count", pattern="^(price|sales_count|monthly_sales|review_count|favorite_count)$"),
    days: int = Query(7, ge=1, le=30),
):
    try:
        pid = uuid.UUID(product_id)
    except ValueError:
        raise BadRequestException(message="无效的商品ID")

    result = await db.execute(
        select(Product).where(Product.id == pid, Product.user_id == user.id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundException(message="商品不存在")

    from datetime import timedelta

    since = datetime.now(UTC) - timedelta(days=days)
    feat_result = await db.execute(
        select(
            ProductFeature.collected_at,
            getattr(ProductFeature, metric),
        )
        .where(ProductFeature.product_id == pid, ProductFeature.collected_at >= since)
        .order_by(ProductFeature.collected_at.asc())
    )
    rows = feat_result.all()

    values = []
    for row in rows:
        val = row[1]
        values.append(float(val) if val is not None else None)

    min_val = min(v for v in values if v is not None) if any(v is not None for v in values) else 0
    max_val = max(v for v in values if v is not None) if any(v is not None for v in values) else 0

    return {
        "code": 0,
        "data": {
            "product_id": product_id,
            "metric": metric,
            "days": days,
            "values": values,
            "min": min_val,
            "max": max_val,
            "count": len(values),
        },
    }
