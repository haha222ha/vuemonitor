import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import CurrentUser
from app.feature.cloud_engine import CloudFeatureEngine
from app.feature.anonymized_aggregator import AnonymizedAggregator

router = APIRouter(prefix="/feature", tags=["feature"])


@router.get("/category-stats")
async def get_category_stats(
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    engine = CloudFeatureEngine(db)
    stats = await engine.compute_category_stats(category)
    return {"categories": [s.to_dict() for s in stats]}


@router.get("/product-ranking/{product_id}")
async def get_product_ranking(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    engine = CloudFeatureEngine(db)
    ranking = await engine.compute_product_ranking(product_id)
    if not ranking:
        return {"ranking": None}
    return {"ranking": ranking.to_dict()}


@router.get("/product-rankings")
async def get_my_product_rankings(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        text("""
            SELECT pr.* FROM product_rankings pr
            JOIN products p ON p.id = pr.product_id
            WHERE p.user_id = :uid
            ORDER BY pr.overall_rank ASC NULLS LAST
        """),
        {"uid": user.id},
    )
    rows = result.mappings().all()
    return {"rankings": [dict(r) for r in rows]}


@router.post("/compute-all")
async def compute_all_rankings(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    engine = CloudFeatureEngine(db)
    count = await engine.compute_all_rankings()
    await db.commit()
    return {"computed": count}


@router.get("/anonymous/aggregates")
async def get_anonymous_aggregates(
    db: AsyncSession = Depends(get_db),
):
    aggregator = AnonymizedAggregator(db)
    aggregates = await aggregator.get_category_aggregates()
    return {"aggregates": [a.to_dict() for a in aggregates]}


@router.get("/anonymous/price-benchmark")
async def get_price_benchmark(
    category: str = Query(...),
    price: float = Query(...),
    db: AsyncSession = Depends(get_db),
):
    aggregator = AnonymizedAggregator(db)
    benchmark = await aggregator.get_price_benchmark(category, price)
    if not benchmark:
        return {"benchmark": None, "reason": "数据不足，无法生成匿名基准"}
    return {"benchmark": benchmark}


@router.get("/anonymous/sales-benchmark")
async def get_sales_benchmark(
    category: str = Query(...),
    sales_count: int = Query(...),
    db: AsyncSession = Depends(get_db),
):
    aggregator = AnonymizedAggregator(db)
    benchmark = await aggregator.get_sales_benchmark(category, sales_count)
    if not benchmark:
        return {"benchmark": None, "reason": "数据不足，无法生成匿名基准"}
    return {"benchmark": benchmark}
