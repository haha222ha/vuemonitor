import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import ProductCategory
from app.models.product import Product, ProductFeature
from app.ws.manager import manager

logger = logging.getLogger(__name__)


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
                collected_at=datetime.fromisoformat(feat["collected_at"]) if "collected_at" in feat else datetime.now(UTC),
            )
            self.db.add(pf)
            saved_count += 1

        product.last_collected_at = datetime.now(UTC)

        await manager.send_to_user(str(user_id), {
            "type": "sync:push",
            "data": {"product_id": str(product.id), "features_count": saved_count},
            "ts": datetime.now(UTC).isoformat(),
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

    async def batch_push(
        self,
        user_id: uuid.UUID,
        products: list[dict],
        features: list[dict],
        categories: list[dict],
        deletions: list[dict],
    ) -> dict:
        stats = {"products": 0, "features": 0, "categories": 0, "deletions": 0, "errors": 0}

        for cat_data in categories:
            try:
                async with self.db.begin_nested():
                    cat_id = uuid.UUID(cat_data["id"]) if "id" in cat_data else uuid.uuid4()
                    result = await self.db.execute(
                        select(ProductCategory).where(ProductCategory.id == cat_id)
                    )
                    existing = result.scalar_one_or_none()

                    if existing:
                        for key in ["name", "icon", "color", "sort_order", "parent_id"]:
                            if key in cat_data:
                                setattr(existing, key, cat_data[key])
                    else:
                        category = ProductCategory(
                            id=cat_id,
                            user_id=user_id,
                            name=cat_data.get("name", ""),
                            icon=cat_data.get("icon"),
                            color=cat_data.get("color"),
                            sort_order=cat_data.get("sort_order", 0),
                            parent_id=uuid.UUID(cat_data["parent_id"]) if cat_data.get("parent_id") else None,
                        )
                        self.db.add(category)
                    stats["categories"] += 1
            except Exception as e:
                logger.warning(f"sync category failed: {e}")
                stats["errors"] += 1

        for prod_data in products:
            try:
                async with self.db.begin_nested():
                    prod_id = uuid.UUID(prod_data["id"]) if "id" in prod_data else uuid.uuid4()
                    result = await self.db.execute(
                        select(Product).where(
                            Product.user_id == user_id,
                            Product.id == prod_id,
                        )
                    )
                    existing = result.scalar_one_or_none()

                    if existing:
                        for key in ["product_name", "shop_name", "image_url", "category_id", "category", "product_url", "is_active"]:
                            if key in prod_data:
                                if key == "category_id" and prod_data[key]:
                                    prod_data[key] = uuid.UUID(prod_data[key])
                                if key == "is_active":
                                    setattr(existing, key, int(prod_data[key]))
                                else:
                                    setattr(existing, key, prod_data[key])
                    else:
                        product = Product(
                            id=prod_id,
                            user_id=user_id,
                            platform=prod_data.get("platform", "xhs"),
                            platform_product_id=prod_data.get("platform_product_id", ""),
                            product_name=prod_data.get("product_name"),
                            shop_name=prod_data.get("shop_name"),
                            image_url=prod_data.get("image_url"),
                            category_id=uuid.UUID(prod_data["category_id"]) if prod_data.get("category_id") else None,
                            category=prod_data.get("category"),
                            product_url=prod_data.get("product_url"),
                            is_active=int(prod_data.get("is_active", True)),
                            last_collected_at=datetime.fromisoformat(prod_data["last_collected_at"]) if prod_data.get("last_collected_at") else None,
                        )
                        self.db.add(product)
                    stats["products"] += 1
            except Exception as e:
                logger.warning(f"sync product failed: {e}")
                stats["errors"] += 1

        for feat_data in features:
            try:
                async with self.db.begin_nested():
                    feat_id = uuid.UUID(feat_data["id"]) if "id" in feat_data else uuid.uuid4()
                    product_id = uuid.UUID(feat_data["product_id"]) if feat_data.get("product_id") else None
                    if not product_id:
                        continue

                    pf = ProductFeature(
                        id=feat_id,
                        product_id=product_id,
                        price=feat_data.get("price"),
                        original_price=feat_data.get("original_price"),
                        sales_count=feat_data.get("sales_count"),
                        monthly_sales=feat_data.get("monthly_sales"),
                        rating=feat_data.get("rating"),
                        review_count=feat_data.get("review_count"),
                        favorite_count=feat_data.get("favorite_count"),
                        stock_status=feat_data.get("stock_status"),
                        extra_features=feat_data.get("extra_features", {}),
                        source=feat_data.get("source", "local"),
                        collected_at=datetime.fromisoformat(feat_data["collected_at"]) if feat_data.get("collected_at") else datetime.now(UTC),
                    )
                    self.db.add(pf)
                    stats["features"] += 1
            except Exception as e:
                logger.warning(f"sync feature failed: {e}")
                stats["errors"] += 1

        for deletion in deletions:
            try:
                async with self.db.begin_nested():
                    del_type = deletion.get("type")
                    del_id = deletion.get("id")
                    if not del_type or not del_id:
                        continue

                    if del_type == "product":
                        result = await self.db.execute(
                            select(Product).where(Product.id == uuid.UUID(del_id), Product.user_id == user_id)
                        )
                        product = result.scalar_one_or_none()
                        if product:
                            product.is_active = 0
                            stats["deletions"] += 1
                    elif del_type == "category":
                        result = await self.db.execute(
                            select(ProductCategory).where(ProductCategory.id == uuid.UUID(del_id), ProductCategory.user_id == user_id)
                        )
                        category = result.scalar_one_or_none()
                        if category:
                            await self.db.delete(category)
                            stats["deletions"] += 1
            except Exception as e:
                logger.warning(f"sync deletion failed: {e}")
                stats["errors"] += 1

        await self.db.commit()

        await manager.send_to_user(str(user_id), {
            "type": "sync:batch-push",
            "data": stats,
            "ts": datetime.now(UTC).isoformat(),
        })

        return stats

    async def get_changes_since(
        self,
        user_id: uuid.UUID,
        since: datetime | None = None,
        include_products: bool = True,
        include_features: bool = True,
        include_categories: bool = True,
        include_deletions: bool = True,
    ) -> dict:
        result_data: dict = {"server_time": datetime.now(UTC).isoformat()}

        if include_products:
            query = select(Product).where(Product.user_id == user_id)
            if since:
                query = query.where(Product.updated_at >= since)
            result = await self.db.execute(query.order_by(Product.updated_at.asc()))
            products = result.scalars().all()
            result_data["products"] = [
                {
                    "id": str(p.id),
                    "platform": p.platform,
                    "platform_product_id": p.platform_product_id,
                    "product_name": p.product_name,
                    "shop_name": p.shop_name,
                    "image_url": p.image_url,
                    "category_id": str(p.category_id) if p.category_id else None,
                    "category": p.category,
                    "product_url": p.product_url,
                    "is_active": bool(p.is_active),
                    "last_collected_at": p.last_collected_at.isoformat() if p.last_collected_at else None,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                }
                for p in products
            ]

        if include_features:
            query = (
                select(ProductFeature)
                .join(Product)
                .where(Product.user_id == user_id)
            )
            if since:
                query = query.where(ProductFeature.collected_at >= since)
            result = await self.db.execute(query.order_by(ProductFeature.collected_at.asc()).limit(5000))
            features = result.scalars().all()
            result_data["features"] = [
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

        if include_categories:
            query = select(ProductCategory).where(ProductCategory.user_id == user_id)
            if since:
                query = query.where(ProductCategory.updated_at >= since)
            result = await self.db.execute(query.order_by(ProductCategory.updated_at.asc()))
            categories = result.scalars().all()
            result_data["categories"] = [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "icon": c.icon,
                    "color": c.color,
                    "sort_order": c.sort_order,
                    "parent_id": str(c.parent_id) if c.parent_id else None,
                    "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                }
                for c in categories
            ]

        if include_deletions and since:
            result_data["deletions"] = []
            if include_products:
                del_query = select(Product).where(
                    Product.user_id == user_id,
                    not Product.is_active,
                    Product.updated_at >= since,
                )
                del_result = await self.db.execute(del_query)
                deleted_products = del_result.scalars().all()
                for p in deleted_products:
                    result_data["deletions"].append({
                        "type": "product",
                        "id": str(p.id),
                        "platform_product_id": p.platform_product_id,
                        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                    })

        return result_data

    async def full_pull(
        self,
        user_id: uuid.UUID,
        since: datetime | None = None,
        include_products: bool = True,
        include_features: bool = True,
        include_categories: bool = True,
    ) -> dict:
        return await self.get_changes_since(
            user_id=user_id,
            since=since,
            include_products=include_products,
            include_features=include_features,
            include_categories=include_categories,
            include_deletions=True,
        )

    async def get_sync_status(self, user_id: uuid.UUID) -> dict:
        product_count = await self.db.scalar(
            select(func.count()).select_from(Product).where(Product.user_id == user_id, Product.is_active)
        )
        feature_count = await self.db.scalar(
            select(func.count()).select_from(ProductFeature)
            .join(Product).where(Product.user_id == user_id)
        )
        category_count = await self.db.scalar(
            select(func.count()).select_from(ProductCategory).where(ProductCategory.user_id == user_id)
        )
        last_product_update = await self.db.scalar(
            select(func.max(Product.updated_at)).where(Product.user_id == user_id)
        )
        last_feature_update = await self.db.scalar(
            select(func.max(ProductFeature.collected_at))
            .join(Product).where(Product.user_id == user_id)
        )

        return {
            "product_count": product_count or 0,
            "feature_count": feature_count or 0,
            "category_count": category_count or 0,
            "last_product_update": last_product_update.isoformat() if last_product_update else None,
            "last_feature_update": last_feature_update.isoformat() if last_feature_update else None,
            "server_time": datetime.now(UTC).isoformat(),
        }
