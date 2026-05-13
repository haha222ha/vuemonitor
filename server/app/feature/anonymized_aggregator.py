import hashlib
import logging
import math
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product, ProductFeature

logger = logging.getLogger(__name__)

MIN_K_ANONYMITY = 3
LAPLACE_SENSITIVITY = 1.0
NOISE_SCALE = 0.1


class AnonymizedAggregate:
    def __init__(
        self,
        category: str,
        user_count: int,
        product_count: int,
        avg_price: Optional[float],
        median_price: Optional[float],
        avg_sales: Optional[float],
        avg_rating: Optional[float],
        price_range: Optional[str],
        sales_range: Optional[str],
        top_lifecycle: Optional[str],
        dominant_trend: Optional[str],
        is_k_anonymous: bool,
    ):
        self.category = category
        self.user_count = user_count
        self.product_count = product_count
        self.avg_price = avg_price
        self.median_price = median_price
        self.avg_sales = avg_sales
        self.avg_rating = avg_rating
        self.price_range = price_range
        self.sales_range = sales_range
        self.top_lifecycle = top_lifecycle
        self.dominant_trend = dominant_trend
        self.is_k_anonymous = is_k_anonymous

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "user_count": self.user_count,
            "product_count": self.product_count,
            "avg_price": self._add_noise(self.avg_price) if self.avg_price else None,
            "median_price": self._add_noise(self.median_price) if self.median_price else None,
            "avg_sales": self._add_noise(self.avg_sales) if self.avg_sales else None,
            "avg_rating": self._add_noise(self.avg_rating) if self.avg_rating else None,
            "price_range": self.price_range,
            "sales_range": self.sales_range,
            "top_lifecycle": self.top_lifecycle,
            "dominant_trend": self.dominant_trend,
            "is_k_anonymous": self.is_k_anonymous,
        }

    @staticmethod
    def _add_noise(value: Optional[float]) -> Optional[float]:
        if value is None:
            return None
        import random
        noise = random.gauss(0, NOISE_SCALE * abs(value) + 0.01)
        return round(max(0, value + noise), 2)

    @staticmethod
    def _laplace_noise(value: Optional[float], epsilon: float = 1.0) -> Optional[float]:
        if value is None:
            return None
        import random
        scale = LAPLACE_SENSITIVITY / epsilon
        u = random.uniform(-0.5, 0.5)
        noise = -scale * math.copysign(1, u) * math.log(1 - 2 * abs(u))
        return round(max(0, value + noise), 2)


class CategoryHeatPoint:
    def __init__(
        self,
        category: str,
        product_count: int,
        user_count: int,
        avg_sales: Optional[float],
        avg_favorites: Optional[float],
        avg_rating: Optional[float],
        heat_score: float,
        heat_level: str,
    ):
        self.category = category
        self.product_count = product_count
        self.user_count = user_count
        self.avg_sales = avg_sales
        self.avg_favorites = avg_favorites
        self.avg_rating = avg_rating
        self.heat_score = heat_score
        self.heat_level = heat_level

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "product_count": self.product_count,
            "user_count": self.user_count,
            "avg_sales": AnonymizedAggregate._add_noise(self.avg_sales) if self.avg_sales else None,
            "avg_favorites": AnonymizedAggregate._add_noise(self.avg_favorites) if self.avg_favorites else None,
            "avg_rating": AnonymizedAggregate._add_noise(self.avg_rating) if self.avg_rating else None,
            "heat_score": round(self.heat_score, 1),
            "heat_level": self.heat_level,
        }


class TrendTimePoint:
    def __init__(
        self,
        period: str,
        category: str,
        avg_sales: Optional[float],
        avg_price: Optional[float],
        avg_rating: Optional[float],
        product_count: int,
        user_count: int,
        sales_growth_rate: Optional[float] = None,
        price_change_rate: Optional[float] = None,
    ):
        self.period = period
        self.category = category
        self.avg_sales = avg_sales
        self.avg_price = avg_price
        self.avg_rating = avg_rating
        self.product_count = product_count
        self.user_count = user_count
        self.sales_growth_rate = sales_growth_rate
        self.price_change_rate = price_change_rate

    def to_dict(self) -> dict:
        return {
            "period": self.period,
            "category": self.category,
            "avg_sales": AnonymizedAggregate._laplace_noise(self.avg_sales) if self.avg_sales else None,
            "avg_price": AnonymizedAggregate._laplace_noise(self.avg_price) if self.avg_price else None,
            "avg_rating": AnonymizedAggregate._add_noise(self.avg_rating) if self.avg_rating else None,
            "product_count": self.product_count,
            "user_count": self.user_count,
            "sales_growth_rate": round(self.sales_growth_rate, 4) if self.sales_growth_rate is not None else None,
            "price_change_rate": round(self.price_change_rate, 4) if self.price_change_rate is not None else None,
        }


class AnonymizedAggregator:
    def __init__(self, db: AsyncSession, k: int = MIN_K_ANONYMITY):
        self.db = db
        self.k = max(k, MIN_K_ANONYMITY)

    async def get_category_aggregates(self) -> list[AnonymizedAggregate]:
        result = await self.db.execute(
            select(
                Product.category,
                func.count(func.distinct(Product.user_id)).label("user_count"),
                func.count(Product.id).label("product_count"),
                func.avg(ProductFeature.price).label("avg_price"),
                func.avg(ProductFeature.sales_count).label("avg_sales"),
                func.avg(ProductFeature.rating).label("avg_rating"),
            )
            .join(ProductFeature, ProductFeature.product_id == Product.id)
            .where(Product.is_active == True, Product.category.isnot(None))
            .group_by(Product.category)
            .having(func.count(func.distinct(Product.user_id)) >= self.k)
        )
        rows = result.all()

        aggregates = []
        for row in rows:
            if not row.category:
                continue

            is_k_anonymous = row.user_count >= self.k

            percentile_result = await self.db.execute(
                select(
                    func.percentile_cont(0.5).within_group(ProductFeature.price).label("median"),
                    func.min(ProductFeature.price).label("min_price"),
                    func.max(ProductFeature.price).label("max_price"),
                )
                .join(Product, Product.id == ProductFeature.product_id)
                .where(Product.category == row.category, Product.is_active == True)
            )
            price_stats = percentile_result.one_or_none()

            sales_range_result = await self.db.execute(
                select(
                    func.min(ProductFeature.sales_count).label("min_sales"),
                    func.max(ProductFeature.sales_count).label("max_sales"),
                )
                .join(Product, Product.id == ProductFeature.product_id)
                .where(Product.category == row.category, Product.is_active == True)
            )
            sales_stats = sales_range_result.one_or_none()

            lifecycle_result = await self.db.execute(
                text("""
                    SELECT lifecycle_stage, COUNT(*) as cnt FROM product_rankings
                    WHERE category = :cat
                    GROUP BY lifecycle_stage
                    ORDER BY cnt DESC LIMIT 1
                """),
                {"cat": row.category},
            )
            lifecycle_row = lifecycle_result.one_or_none()

            trend_result = await self.db.execute(
                text("""
                    SELECT trend_short, COUNT(*) as cnt FROM product_rankings
                    WHERE category = :cat
                    GROUP BY trend_short
                    ORDER BY cnt DESC LIMIT 1
                """),
                {"cat": row.category},
            )
            trend_row = trend_result.one_or_none()

            price_range = None
            if price_stats and price_stats.min_price is not None and price_stats.max_price is not None:
                price_range = f"¥{float(price_stats.min_price):.0f} - ¥{float(price_stats.max_price):.0f}"

            sales_range = None
            if sales_stats and sales_stats.min_sales is not None and sales_stats.max_sales is not None:
                sales_range = f"{sales_stats.min_sales} - {sales_stats.max_sales}"

            aggregates.append(AnonymizedAggregate(
                category=row.category,
                user_count=row.user_count,
                product_count=row.product_count,
                avg_price=float(row.avg_price) if row.avg_price else None,
                median_price=float(price_stats.median) if price_stats and price_stats.median else None,
                avg_sales=float(row.avg_sales) if row.avg_sales else None,
                avg_rating=float(row.avg_rating) if row.avg_rating else None,
                price_range=price_range,
                sales_range=sales_range,
                top_lifecycle=lifecycle_row.lifecycle_stage if lifecycle_row else None,
                dominant_trend=trend_row.trend_short if trend_row else None,
                is_k_anonymous=is_k_anonymous,
            ))

        return aggregates

    async def get_price_benchmark(
        self, category: str, price: float
    ) -> Optional[dict]:
        user_count_result = await self.db.execute(
            select(func.count(func.distinct(Product.user_id)))
            .where(Product.category == category, Product.is_active == True)
        )
        user_count = user_count_result.scalar() or 0

        if user_count < self.k:
            return None

        percentile_result = await self.db.execute(
            select(
                func.percentile_cont(0.25).within_group(ProductFeature.price).label("p25"),
                func.percentile_cont(0.50).within_group(ProductFeature.price).label("p50"),
                func.percentile_cont(0.75).within_group(ProductFeature.price).label("p75"),
            )
            .join(Product, Product.id == ProductFeature.product_id)
            .where(Product.category == category, Product.is_active == True)
        )
        pct = percentile_result.one_or_none()

        if not pct or pct.p50 is None:
            return None

        below_result = await self.db.execute(
            select(func.count())
            .select_from(ProductFeature)
            .join(Product, Product.id == ProductFeature.product_id)
            .where(
                Product.category == category,
                Product.is_active == True,
                ProductFeature.price < price,
            )
        )
        below = below_result.scalar() or 0

        total_result = await self.db.execute(
            select(func.count())
            .select_from(ProductFeature)
            .join(Product, Product.id == ProductFeature.product_id)
            .where(
                Product.category == category,
                Product.is_active == True,
                ProductFeature.price.isnot(None),
            )
        )
        total = total_result.scalar() or 1

        price_percentile = round((below / total) * 100, 1)

        if price <= float(pct.p25):
            price_level = "low"
        elif price <= float(pct.p50):
            price_level = "below_average"
        elif price <= float(pct.p75):
            price_level = "above_average"
        else:
            price_level = "high"

        return {
            "category": category,
            "price_percentile": price_percentile,
            "price_level": price_level,
            "category_p25": AnonymizedAggregate._add_noise(float(pct.p25)),
            "category_p50": AnonymizedAggregate._add_noise(float(pct.p50)),
            "category_p75": AnonymizedAggregate._add_noise(float(pct.p75)),
            "is_k_anonymous": user_count >= self.k,
        }

    async def get_category_heatmap(self) -> list[CategoryHeatPoint]:
        result = await self.db.execute(
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
            .having(func.count(func.distinct(Product.user_id)) >= self.k)
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

            heat_score = min(heat_score, 100)
            heat_level = "hot" if heat_score >= 70 else "warm" if heat_score >= 40 else "cold"

            heatmap.append(CategoryHeatPoint(
                category=row.category,
                product_count=row.product_count,
                user_count=row.user_count,
                avg_sales=float(row.avg_sales) if row.avg_sales else None,
                avg_favorites=float(row.avg_favorites) if row.avg_favorites else None,
                avg_rating=float(row.avg_rating) if row.avg_rating else None,
                heat_score=heat_score,
                heat_level=heat_level,
            ))

        heatmap.sort(key=lambda x: x.heat_score, reverse=True)
        return heatmap

    async def get_trend_timeseries(
        self,
        category: Optional[str] = None,
        days: int = 30,
    ) -> dict[str, list[TrendTimePoint]]:
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
            HAVING COUNT(DISTINCT p.user_id) >= :k
            ORDER BY period ASC, p.category
        """
        params["k"] = self.k

        result = await self.db.execute(text(base_query), params)
        rows = result.mappings().all()

        series_map: dict[str, list[TrendTimePoint]] = {}
        for row in rows:
            cat = row["category"] or "unknown"
            if cat not in series_map:
                series_map[cat] = []

            series_map[cat].append(TrendTimePoint(
                period=row["period"].isoformat() if row["period"] else "",
                category=cat,
                avg_sales=float(row["avg_sales"]) if row["avg_sales"] else None,
                avg_price=float(row["avg_price"]) if row["avg_price"] else None,
                avg_rating=float(row["avg_rating"]) if row["avg_rating"] else None,
                product_count=row["product_count"],
                user_count=row["user_count"],
            ))

        for cat in series_map:
            points = series_map[cat]
            for i in range(1, len(points)):
                prev = points[i - 1]
                curr = points[i]
                if prev.avg_sales and curr.avg_sales and prev.avg_sales > 0:
                    curr.sales_growth_rate = (curr.avg_sales - prev.avg_sales) / prev.avg_sales
                if prev.avg_price and curr.avg_price and prev.avg_price > 0:
                    curr.price_change_rate = (curr.avg_price - prev.avg_price) / prev.avg_price

        return series_map

    async def get_behavior_patterns(
        self, category: Optional[str] = None
    ) -> dict:
        category_filter = "AND p.category = :cat" if category else ""
        params = {"cat": category} if category else {}

        lifecycle_result = await self.db.execute(
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

        trend_result = await self.db.execute(
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

        price_band_result = await self.db.execute(
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
                "avg_sales": AnonymizedAggregate._add_noise(float(r.avg_sales)) if r.avg_sales else None,
                "avg_rating": AnonymizedAggregate._add_noise(float(r.avg_rating)) if r.avg_rating else None,
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

    async def get_sales_benchmark(
        self, category: str, sales_count: int
    ) -> Optional[dict]:
        user_count_result = await self.db.execute(
            select(func.count(func.distinct(Product.user_id)))
            .where(Product.category == category, Product.is_active == True)
        )
        user_count = user_count_result.scalar() or 0

        if user_count < self.k:
            return None

        percentile_result = await self.db.execute(
            select(
                func.percentile_cont(0.25).within_group(ProductFeature.sales_count).label("p25"),
                func.percentile_cont(0.50).within_group(ProductFeature.sales_count).label("p50"),
                func.percentile_cont(0.75).within_group(ProductFeature.sales_count).label("p75"),
            )
            .join(Product, Product.id == ProductFeature.product_id)
            .where(Product.category == category, Product.is_active == True)
        )
        pct = percentile_result.one_or_none()

        if not pct or pct.p50 is None:
            return None

        below_result = await self.db.execute(
            select(func.count())
            .select_from(ProductFeature)
            .join(Product, Product.id == ProductFeature.product_id)
            .where(
                Product.category == category,
                Product.is_active == True,
                ProductFeature.sales_count < sales_count,
            )
        )
        below = below_result.scalar() or 0

        total_result = await self.db.execute(
            select(func.count())
            .select_from(ProductFeature)
            .join(Product, Product.id == ProductFeature.product_id)
            .where(
                Product.category == category,
                Product.is_active == True,
                ProductFeature.sales_count.isnot(None),
            )
        )
        total = total_result.scalar() or 1

        sales_percentile = round((below / total) * 100, 1)

        if sales_count <= float(pct.p25):
            sales_level = "low"
        elif sales_count <= float(pct.p50):
            sales_level = "below_average"
        elif sales_count <= float(pct.p75):
            sales_level = "above_average"
        else:
            sales_level = "high"

        return {
            "category": category,
            "sales_percentile": sales_percentile,
            "sales_level": sales_level,
            "category_p25": AnonymizedAggregate._add_noise(float(pct.p25)),
            "category_p50": AnonymizedAggregate._add_noise(float(pct.p50)),
            "category_p75": AnonymizedAggregate._add_noise(float(pct.p75)),
            "is_k_anonymous": user_count >= self.k,
        }
