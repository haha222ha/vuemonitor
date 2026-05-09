import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product, ProductFeature
from app.ws.manager import manager


class SyncService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def push_features_to_cloud(
        self,
        user_id: uuid.UUID,
        platform: str,
        platform_product_id: str,
        features: list[dict],
    ) -> dict:
        result = await self.db.execute(
            select(Product).where(
                Product.user_id == user_id,
                Product.platform == platform,
                Product.platform_product_id == platform_product_id,
            )
        )
        product = result.scalar_one_or_none()

        if not product:
            product = Product(
                user_id=user_id,
                platform=platform,
                platform_product_id=platform_product_id,
                product_name=features[0].get("product_name", "unknown") if features else "unknown",
                shop_name=features[0].get("shop_name") if features else None,
            )
            self.db.add(product)
            await self.db.flush()

        saved_count = 0
        for feat in features:
            pf = ProductFeature(
                product_id=product.id,
                price=feat.get("price"),
                original_price=feat.get("original_price"),
                sales_count=feat.get("sales_count"),
                monthly_sales=feat.get("monthly_sales"),
                rating=feat.get("rating"),
                review_count=feat.get("review_count"),
                favorite_count=feat.get("favorite_count"),
                stock_status=feat.get("stock_status"),
                extra_features=feat.get("extra_features", {}),
                source="local",
                collected_at=datetime.fromisoformat(feat["collected_at"]) if "collected_at" in feat else datetime.now(timezone.utc),
            )
            self.db.add(pf)
            saved_count += 1

        product.last_collected_at = datetime.now(timezone.utc)

        await manager.send_to_user(str(user_id), {
            "type": "sync:push",
            "data": {"product_id": str(product.id), "features_count": saved_count},
            "ts": datetime.now(timezone.utc).isoformat(),
        })

        return {"product_id": str(product.id), "saved_count": saved_count}

    async def pull_features_from_cloud(
        self,
        user_id: uuid.UUID,
        product_id: uuid.UUID | None = None,
        since: datetime | None = None,
    ) -> list[dict]:
        query = (
            select(ProductFeature)
            .join(Product)
            .where(Product.user_id == user_id)
        )

        if product_id:
            query = query.where(ProductFeature.product_id == product_id)
        if since:
            query = query.where(ProductFeature.collected_at >= since)

        query = query.order_by(ProductFeature.collected_at.desc())
        result = await self.db.execute(query)
        features = result.scalars().all()

        return [
            {
                "id": str(f.id),
                "product_id": str(f.product_id),
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
        ]
