import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import CurrentUser
from app.feature.cloud_engine import CloudFeatureEngine
from app.feature.anonymized_aggregator import AnonymizedAggregator
from app.models.product import Product, ProductFeature

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


@router.get("/crowd/category-heatmap")
async def get_category_heatmap(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(
            Product.category,
            func.count(Product.id).label("product_count"),
            func.count(func.distinct(Product.user_id)).label("user_count"),
            func.avg(ProductFeature.sales_count).label("avg_sales"),
            func.avg(ProductFeature.favorite_count).label("avg_favorites"),
            func.avg(ProductFeature.rating).label("avg_rating"),
        )
        .join(ProductFeature, ProductFeature.product_id == Product.id)
        .where(Product.is_active == True, Product.category.isnot(None))
        .group_by(Product.category)
    )
    rows = result.all()

    heatmap = []
    for row in rows:
        if not row.category:
            continue

        heat_score = 0.0
        if row.user_count:
            heat_score += min(row.user_count / 10, 3) * 10
        if row.avg_sales:
            heat_score += min(float(row.avg_sales) / 1000, 3) * 20
        if row.avg_favorites:
            heat_score += min(float(row.avg_favorites) / 500, 3) * 15
        if row.avg_rating and float(row.avg_rating) > 4:
            heat_score += 15

        heatmap.append({
            "category": row.category,
            "product_count": row.product_count,
            "user_count": row.user_count,
            "avg_sales": float(row.avg_sales) if row.avg_sales else None,
            "avg_favorites": float(row.avg_favorites) if row.avg_favorites else None,
            "avg_rating": float(row.avg_rating) if row.avg_rating else None,
            "heat_score": round(min(heat_score, 100), 1),
            "heat_level": "hot" if heat_score >= 70 else "warm" if heat_score >= 40 else "cold",
        })

    heatmap.sort(key=lambda x: x["heat_score"], reverse=True)
    return {"heatmap": heatmap}


@router.get("/crowd/trend-timeseries")
async def get_trend_timeseries(
    category: Optional[str] = Query(None),
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
):
    interval = "day" if days <= 30 else "week"

    date_trunc = f"'{interval}'" if interval == "week" else "'day'"

    base_query = f"""
        SELECT
            DATE_TRUNC({date_trunc}, pf.collected_at) AS period,
            p.category,
            AVG(pf.sales_count) AS avg_sales,
            AVG(pf.price) AS avg_price,
            AVG(pf.rating) AS avg_rating,
            COUNT(DISTINCT p.id) AS product_count,
            COUNT(DISTINCT p.user_id) AS user_count
        FROM product_features pf
        JOIN products p ON p.id = pf.product_id
        WHERE p.is_active = true
          AND pf.collected_at >= NOW() - INTERVAL '{days} days'
    """

    params = {}
    if category:
        base_query += " AND p.category = :cat"
        params["cat"] = category

    base_query += f"""
        GROUP BY DATE_TRUNC({date_trunc}, pf.collected_at), p.category
        ORDER BY period ASC, p.category
    """

    result = await db.execute(text(base_query), params)
    rows = result.mappings().all()

    series_map: dict[str, list] = {}
    for row in rows:
        cat = row["category"] or "unknown"
        if cat not in series_map:
            series_map[cat] = []
        series_map[cat].append({
            "period": row["period"].isoformat() if row["period"] else None,
            "avg_sales": float(row["avg_sales"]) if row["avg_sales"] else None,
            "avg_price": float(row["avg_price"]) if row["avg_price"] else None,
            "avg_rating": float(row["avg_rating"]) if row["avg_rating"] else None,
            "product_count": row["product_count"],
            "user_count": row["user_count"],
        })

    for cat in series_map:
        points = series_map[cat]
        for i in range(1, len(points)):
            prev = points[i - 1]
            curr = points[i]
            if prev["avg_sales"] and curr["avg_sales"] and prev["avg_sales"] > 0:
                curr["sales_growth_rate"] = round((curr["avg_sales"] - prev["avg_sales"]) / prev["avg_sales"], 4)
            else:
                curr["sales_growth_rate"] = None
            if prev["avg_price"] and curr["avg_price"] and prev["avg_price"] > 0:
                curr["price_change_rate"] = round((curr["avg_price"] - prev["avg_price"]) / prev["avg_price"], 4)
            else:
                curr["price_change_rate"] = None

    return {"series": series_map, "interval": interval, "days": days}


@router.get("/crowd/behavior-patterns")
async def get_behavior_patterns(
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    category_filter = "AND p.category = :cat" if category else ""
    params = {"cat": category} if category else {}

    lifecycle_result = await db.execute(
        text(f"""
            SELECT lifecycle_stage, COUNT(*) as cnt
            FROM product_rankings pr
            JOIN products p ON p.id = pr.product_id
            WHERE p.is_active = true {category_filter}
            GROUP BY lifecycle_stage
            ORDER BY cnt DESC
        """),
        params,
    )
    lifecycle_dist = [{"stage": r.lifecycle_stage, "count": r.cnt} for r in lifecycle_result.all()]

    trend_result = await db.execute(
        text(f"""
            SELECT trend_short, COUNT(*) as cnt
            FROM product_rankings pr
            JOIN products p ON p.id = pr.product_id
            WHERE p.is_active = true {category_filter}
            GROUP BY trend_short
            ORDER BY cnt DESC
        """),
        params,
    )
    trend_dist = [{"trend": r.trend_short, "count": r.cnt} for r in trend_result.all()]

    price_band_result = await db.execute(
        text(f"""
            SELECT
                CASE
                    WHEN pf.price < 50 THEN 'under_50'
                    WHEN pf.price < 100 THEN '50_100'
                    WHEN pf.price < 200 THEN '100_200'
                    WHEN pf.price < 500 THEN '200_500'
                    ELSE 'over_500'
                END AS price_band,
                COUNT(*) AS cnt,
                AVG(pf.sales_count) AS avg_sales,
                AVG(pf.rating) AS avg_rating
            FROM product_features pf
            JOIN products p ON p.id = pf.product_id
            WHERE p.is_active = true AND pf.price IS NOT NULL {category_filter}
            GROUP BY price_band
            ORDER BY MIN(pf.price)
        """),
        params,
    )
    price_bands = [
        {
            "band": r.price_band,
            "count": r.cnt,
            "avg_sales": float(r.avg_sales) if r.avg_sales else None,
            "avg_rating": float(r.avg_rating) if r.avg_rating else None,
        }
        for r in price_band_result.all()
    ]

    best_seller_band = None
    if price_bands:
        bands_with_sales = [b for b in price_bands if b["avg_sales"] is not None]
        if bands_with_sales:
            best_seller_band = max(bands_with_sales, key=lambda b: b["avg_sales"])

    dominant_lifecycle = lifecycle_dist[0]["stage"] if lifecycle_dist else None
    dominant_trend = trend_dist[0]["trend"] if trend_dist else None

    return {
        "lifecycle_distribution": lifecycle_dist,
        "trend_distribution": trend_dist,
        "price_bands": price_bands,
        "best_seller_price_band": best_seller_band,
        "dominant_lifecycle": dominant_lifecycle,
        "dominant_trend": dominant_trend,
        "category": category,
    }
