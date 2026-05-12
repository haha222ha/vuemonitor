import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product, ProductFeature
from app.models.monitor import MonitorRule

logger = logging.getLogger(__name__)


class CategoryStats:
    def __init__(
        self,
        category: str,
        product_count: int,
        avg_price: Optional[float],
        median_price: Optional[float],
        avg_sales: Optional[float],
        avg_rating: Optional[float],
        price_p25: Optional[float],
        price_p75: Optional[float],
        sales_p25: Optional[float],
        sales_p75: Optional[float],
    ):
        self.category = category
        self.product_count = product_count
        self.avg_price = avg_price
        self.median_price = median_price
        self.avg_sales = avg_sales
        self.avg_rating = avg_rating
        self.price_p25 = price_p25
        self.price_p75 = price_p75
        self.sales_p25 = sales_p25
        self.sales_p75 = sales_p75

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "product_count": self.product_count,
            "avg_price": self.avg_price,
            "median_price": self.median_price,
            "avg_sales": self.avg_sales,
            "avg_rating": self.avg_rating,
            "price_p25": self.price_p25,
            "price_p75": self.price_p75,
            "sales_p25": self.sales_p25,
            "sales_p75": self.sales_p75,
        }


class ProductRanking:
    def __init__(
        self,
        product_id: uuid.UUID,
        category: Optional[str],
        price_percentile: Optional[float],
        sales_percentile: Optional[float],
        rating_percentile: Optional[float],
        overall_rank: Optional[int],
        category_rank: Optional[int],
        category_total: Optional[int],
        lifecycle_stage: Optional[str],
        trend_short: Optional[str],
        trend_long: Optional[str],
        sales_velocity: Optional[float],
        growth_rate_7d: Optional[float],
        growth_rate_30d: Optional[float],
        volatility: Optional[float],
        competition_index: Optional[float],
    ):
        self.product_id = product_id
        self.category = category
        self.price_percentile = price_percentile
        self.sales_percentile = sales_percentile
        self.rating_percentile = rating_percentile
        self.overall_rank = overall_rank
        self.category_rank = category_rank
        self.category_total = category_total
        self.lifecycle_stage = lifecycle_stage
        self.trend_short = trend_short
        self.trend_long = trend_long
        self.sales_velocity = sales_velocity
        self.growth_rate_7d = growth_rate_7d
        self.growth_rate_30d = growth_rate_30d
        self.volatility = volatility
        self.competition_index = competition_index

    def to_dict(self) -> dict:
        return {
            "product_id": str(self.product_id),
            "category": self.category,
            "price_percentile": self.price_percentile,
            "sales_percentile": self.sales_percentile,
            "rating_percentile": self.rating_percentile,
            "overall_rank": self.overall_rank,
            "category_rank": self.category_rank,
            "category_total": self.category_total,
            "lifecycle_stage": self.lifecycle_stage,
            "trend_short": self.trend_short,
            "trend_long": self.trend_long,
            "sales_velocity": self.sales_velocity,
            "growth_rate_7d": self.growth_rate_7d,
            "growth_rate_30d": self.growth_rate_30d,
            "volatility": self.volatility,
            "competition_index": self.competition_index,
        }


class CloudFeatureEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def compute_category_stats(self, category: Optional[str] = None) -> list[CategoryStats]:
        base_query = (
            select(
                Product.category,
                func.count(Product.id).label("product_count"),
                func.avg(ProductFeature.price).label("avg_price"),
                func.avg(ProductFeature.sales_count).label("avg_sales"),
                func.avg(ProductFeature.rating).label("avg_rating"),
            )
            .join(ProductFeature, ProductFeature.product_id == Product.id)
            .where(Product.is_active == True, Product.category.isnot(None))
            .group_by(Product.category)
        )

        if category:
            base_query = base_query.where(Product.category == category)

        result = await self.db.execute(base_query)
        rows = result.all()

        stats_list = []
        for row in rows:
            cat = row.category
            if not cat:
                continue

            percentile_result = await self.db.execute(
                select(
                    func.percentile_cont(0.25).within_group(ProductFeature.price).label("p25"),
                    func.percentile_cont(0.50).within_group(ProductFeature.price).label("median"),
                    func.percentile_cont(0.75).within_group(ProductFeature.price).label("p75"),
                )
                .join(Product, Product.id == ProductFeature.product_id)
                .where(Product.category == cat, Product.is_active == True)
            )
            price_pct = percentile_result.one_or_none()

            sales_pct_result = await self.db.execute(
                select(
                    func.percentile_cont(0.25).within_group(ProductFeature.sales_count).label("p25"),
                    func.percentile_cont(0.75).within_group(ProductFeature.sales_count).label("p75"),
                )
                .join(Product, Product.id == ProductFeature.product_id)
                .where(Product.category == cat, Product.is_active == True)
            )
            sales_pct = sales_pct_result.one_or_none()

            stats_list.append(CategoryStats(
                category=cat,
                product_count=row.product_count,
                avg_price=float(row.avg_price) if row.avg_price else None,
                median_price=float(price_pct.median) if price_pct and price_pct.median else None,
                avg_sales=float(row.avg_sales) if row.avg_sales else None,
                avg_rating=float(row.avg_rating) if row.avg_rating else None,
                price_p25=float(price_pct.p25) if price_pct and price_pct.p25 else None,
                price_p75=float(price_pct.p75) if price_pct and price_pct.p75 else None,
                sales_p25=float(sales_pct.p25) if sales_pct and sales_pct.p25 else None,
                sales_p75=float(sales_pct.p75) if sales_pct and sales_pct.p75 else None,
            ))

        return stats_list

    async def compute_product_ranking(self, product_id: uuid.UUID) -> Optional[ProductRanking]:
        product_result = await self.db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = product_result.scalar_one_or_none()
        if not product:
            return None

        latest_feature_result = await self.db.execute(
            select(ProductFeature)
            .where(ProductFeature.product_id == product_id)
            .order_by(ProductFeature.collected_at.desc())
            .limit(1)
        )
        latest = latest_feature_result.scalar_one_or_none()

        prev_feature_result = await self.db.execute(
            select(ProductFeature)
            .where(ProductFeature.product_id == product_id)
            .order_by(ProductFeature.collected_at.desc())
            .offset(1)
            .limit(1)
        )
        prev = prev_feature_result.scalar_one_or_none()

        price_percentile = await self._compute_percentile(product_id, "price", product.category)
        sales_percentile = await self._compute_percentile(product_id, "sales_count", product.category)
        rating_percentile = await self._compute_percentile(product_id, "rating", product.category)

        overall_rank = await self._compute_overall_rank(product_id)
        category_rank = await self._compute_category_rank(product_id, product.category)
        category_total = await self._compute_category_total(product.category)

        sales_velocity = self._compute_sales_velocity(latest, prev)
        growth_rate_7d = await self._compute_growth_rate(product_id, 7)
        growth_rate_30d = await self._compute_growth_rate(product_id, 30)
        volatility = await self._compute_volatility(product_id)
        competition_index = self._compute_competition_index(latest)
        lifecycle_stage = self._compute_lifecycle_stage(growth_rate_7d, latest, prev)
        trend_short = self._compute_trend(growth_rate_7d)
        trend_long = self._compute_trend(growth_rate_30d)

        return ProductRanking(
            product_id=product_id,
            category=product.category,
            price_percentile=price_percentile,
            sales_percentile=sales_percentile,
            rating_percentile=rating_percentile,
            overall_rank=overall_rank,
            category_rank=category_rank,
            category_total=category_total,
            lifecycle_stage=lifecycle_stage,
            trend_short=trend_short,
            trend_long=trend_long,
            sales_velocity=sales_velocity,
            growth_rate_7d=growth_rate_7d,
            growth_rate_30d=growth_rate_30d,
            volatility=volatility,
            competition_index=competition_index,
        )

    async def compute_all_rankings(self) -> int:
        result = await self.db.execute(
            select(Product.id).where(Product.is_active == True)
        )
        product_ids = result.scalars().all()

        computed = 0
        for pid in product_ids:
            try:
                ranking = await self.compute_product_ranking(pid)
                if ranking:
                    await self._save_ranking(ranking)
                    computed += 1
            except Exception as e:
                logger.error(f"Failed to compute ranking for product {pid}: {e}")

        return computed

    async def _compute_percentile(
        self, product_id: uuid.UUID, field: str, category: Optional[str]
    ) -> Optional[float]:
        if not category:
            return None

        latest_result = await self.db.execute(
            select(getattr(ProductFeature, field))
            .where(ProductFeature.product_id == product_id)
            .order_by(ProductFeature.collected_at.desc())
            .limit(1)
        )
        product_value = latest_result.scalar_one_or_none()
        if product_value is None:
            return None

        if isinstance(product_value, Decimal):
            product_value = float(product_value)

        count_result = await self.db.execute(
            select(func.count())
            .select_from(ProductFeature)
            .join(Product, Product.id == ProductFeature.product_id)
            .where(
                Product.category == category,
                Product.is_active == True,
                getattr(ProductFeature, field).isnot(None),
            )
        )
        total = count_result.scalar() or 1

        below_result = await self.db.execute(
            select(func.count())
            .select_from(ProductFeature)
            .join(Product, Product.id == ProductFeature.product_id)
            .where(
                Product.category == category,
                Product.is_active == True,
                getattr(ProductFeature, field) < product_value,
            )
        )
        below = below_result.scalar() or 0

        return round((below / total) * 100, 1) if total > 0 else None

    async def _compute_overall_rank(self, product_id: uuid.UUID) -> Optional[int]:
        result = await self.db.execute(
            text("""
                WITH ranked AS (
                    SELECT p.id, pf.sales_count,
                           RANK() OVER (ORDER BY pf.sales_count DESC NULLS LAST) as rnk
                    FROM products p
                    JOIN LATERAL (
                        SELECT sales_count FROM product_features
                        WHERE product_id = p.id
                        ORDER BY collected_at DESC LIMIT 1
                    ) pf ON true
                    WHERE p.is_active = true
                )
                SELECT rnk FROM ranked WHERE id = :pid
            """),
            {"pid": product_id},
        )
        row = result.one_or_none()
        return row.rnk if row else None

    async def _compute_category_rank(
        self, product_id: uuid.UUID, category: Optional[str]
    ) -> Optional[int]:
        if not category:
            return None

        result = await self.db.execute(
            text("""
                WITH ranked AS (
                    SELECT p.id, pf.sales_count,
                           RANK() OVER (ORDER BY pf.sales_count DESC NULLS LAST) as rnk
                    FROM products p
                    JOIN LATERAL (
                        SELECT sales_count FROM product_features
                        WHERE product_id = p.id
                        ORDER BY collected_at DESC LIMIT 1
                    ) pf ON true
                    WHERE p.is_active = true AND p.category = :cat
                )
                SELECT rnk FROM ranked WHERE id = :pid
            """),
            {"pid": product_id, "cat": category},
        )
        row = result.one_or_none()
        return row.rnk if row else None

    async def _compute_category_total(self, category: Optional[str]) -> Optional[int]:
        if not category:
            return None
        result = await self.db.execute(
            select(func.count(Product.id)).where(
                Product.category == category, Product.is_active == True
            )
        )
        return result.scalar()

    def _compute_sales_velocity(
        self, latest: Optional[ProductFeature], prev: Optional[ProductFeature]
    ) -> Optional[float]:
        if not latest or not prev or not latest.sales_count or not prev.sales_count:
            return None

        days_diff = (latest.collected_at - prev.collected_at).total_seconds() / 86400
        if days_diff < 0.5:
            return None

        delta = max(0, latest.sales_count - prev.sales_count)
        return round(delta / days_diff, 2)

    async def _compute_growth_rate(self, product_id: uuid.UUID, days: int) -> Optional[float]:
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            select(ProductFeature)
            .where(
                ProductFeature.product_id == product_id,
                ProductFeature.sales_count.isnot(None),
                ProductFeature.collected_at >= cutoff,
            )
            .order_by(ProductFeature.collected_at.asc())
        )
        features = result.scalars().all()

        if len(features) < 2:
            return None

        first = features[0]
        last = features[-1]

        if first.sales_count == 0:
            return 1.0 if last.sales_count and last.sales_count > 0 else 0.0

        if not last.sales_count:
            return None

        return round((last.sales_count - first.sales_count) / first.sales_count, 4)

    async def _compute_volatility(self, product_id: uuid.UUID) -> Optional[float]:
        result = await self.db.execute(
            select(ProductFeature.price)
            .where(ProductFeature.product_id == product_id, ProductFeature.price.isnot(None))
            .order_by(ProductFeature.collected_at.desc())
            .limit(30)
        )
        prices = [float(p) for p in result.scalars().all() if p is not None]

        if len(prices) < 3:
            return None

        mean = sum(prices) / len(prices)
        if mean == 0:
            return None

        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        return round((variance ** 0.5) / mean, 4)

    def _compute_competition_index(self, latest: Optional[ProductFeature]) -> Optional[float]:
        if not latest:
            return None

        score = 50.0

        if latest.rating is not None:
            score += (float(latest.rating) - 3) * 10

        if latest.review_count is not None:
            if latest.review_count > 100:
                score += 15
            elif latest.review_count > 50:
                score += 10
            elif latest.review_count > 10:
                score += 5

        if latest.favorite_count is not None:
            if latest.favorite_count > 1000:
                score += 15
            elif latest.favorite_count > 500:
                score += 10
            elif latest.favorite_count > 100:
                score += 5

        if latest.sales_count is not None:
            if latest.sales_count > 10000:
                score += 10
            elif latest.sales_count > 1000:
                score += 5

        return round(max(0, min(100, score)), 1)

    def _compute_lifecycle_stage(
        self,
        growth_rate: Optional[float],
        latest: Optional[ProductFeature],
        prev: Optional[ProductFeature],
    ) -> str:
        if not latest or not prev:
            return "new"

        if growth_rate is None:
            return "stable"

        if growth_rate > 0.5:
            return "growth"
        if growth_rate > 0.1:
            return "rising"
        if growth_rate > -0.1:
            return "stable"
        if growth_rate > -0.3:
            return "declining"
        return "decline"

    def _compute_trend(self, growth_rate: Optional[float]) -> str:
        if growth_rate is None:
            return "unknown"
        if growth_rate > 0.1:
            return "up"
        if growth_rate < -0.1:
            return "down"
        return "stable"

    async def _save_ranking(self, ranking: ProductRanking) -> None:
        from app.models.base import Base
        from sqlalchemy import Table, Column, String, Integer, Float, DateTime
        from sqlalchemy.dialects.postgresql import UUID as PG_UUID

        result = await self.db.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = 'product_rankings'
                )
            """)
        )
        exists = result.scalar()

        if not exists:
            await self.db.execute(text("""
                CREATE TABLE product_rankings (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                    category VARCHAR(100),
                    price_percentile FLOAT,
                    sales_percentile FLOAT,
                    rating_percentile FLOAT,
                    overall_rank INTEGER,
                    category_rank INTEGER,
                    category_total INTEGER,
                    lifecycle_stage VARCHAR(20),
                    trend_short VARCHAR(10),
                    trend_long VARCHAR(10),
                    sales_velocity FLOAT,
                    growth_rate_7d FLOAT,
                    growth_rate_30d FLOAT,
                    volatility FLOAT,
                    competition_index FLOAT,
                    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            await self.db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_product_rankings_product_id ON product_rankings(product_id)
            """))
            await self.db.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_product_rankings_product_unique
                ON product_rankings(product_id)
            """))

        await self.db.execute(text("""
            INSERT INTO product_rankings
            (product_id, category, price_percentile, sales_percentile, rating_percentile,
             overall_rank, category_rank, category_total, lifecycle_stage, trend_short, trend_long,
             sales_velocity, growth_rate_7d, growth_rate_30d, volatility, competition_index)
            VALUES (:pid, :cat, :pp, :sp, :rp, :or, :cr, :ct, :ls, :ts, :tl, :sv, :g7, :g30, :vol, :ci)
            ON CONFLICT (product_id) DO UPDATE SET
                category = EXCLUDED.category,
                price_percentile = EXCLUDED.price_percentile,
                sales_percentile = EXCLUDED.sales_percentile,
                rating_percentile = EXCLUDED.rating_percentile,
                overall_rank = EXCLUDED.overall_rank,
                category_rank = EXCLUDED.category_rank,
                category_total = EXCLUDED.category_total,
                lifecycle_stage = EXCLUDED.lifecycle_stage,
                trend_short = EXCLUDED.trend_short,
                trend_long = EXCLUDED.trend_long,
                sales_velocity = EXCLUDED.sales_velocity,
                growth_rate_7d = EXCLUDED.growth_rate_7d,
                growth_rate_30d = EXCLUDED.growth_rate_30d,
                volatility = EXCLUDED.volatility,
                competition_index = EXCLUDED.competition_index,
                calculated_at = NOW()
        """), {
            "pid": ranking.product_id,
            "cat": ranking.category,
            "pp": ranking.price_percentile,
            "sp": ranking.sales_percentile,
            "rp": ranking.rating_percentile,
            "or": ranking.overall_rank,
            "cr": ranking.category_rank,
            "ct": ranking.category_total,
            "ls": ranking.lifecycle_stage,
            "ts": ranking.trend_short,
            "tl": ranking.trend_long,
            "sv": ranking.sales_velocity,
            "g7": ranking.growth_rate_7d,
            "g30": ranking.growth_rate_30d,
            "vol": ranking.volatility,
            "ci": ranking.competition_index,
        })
