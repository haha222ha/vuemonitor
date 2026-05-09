from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import CurrentUser
from app.models.collect import CollectTask, CollectTaskItem
from app.models.ai import AIAnalysis
from app.models.product import Product, ProductFeature

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    product_count_result = await db.execute(
        select(func.count()).select_from(Product).where(Product.user_id == user.id)
    )
    product_count = product_count_result.scalar() or 0

    active_product_count_result = await db.execute(
        select(func.count()).select_from(Product).where(
            Product.user_id == user.id, Product.is_active == True
        )
    )
    active_product_count = active_product_count_result.scalar() or 0

    latest_features_subq = (
        select(
            ProductFeature.product_id,
            ProductFeature.sales_count,
            func.row_number()
            .partition_by(ProductFeature.product_id)
            .order_by(ProductFeature.collected_at.desc())
            .label("rn"),
        )
        .where(ProductFeature.product_id.in_(
            select(Product.id).where(Product.user_id == user.id)
        ))
        .subquery()
    )

    prev_features_subq = (
        select(
            ProductFeature.product_id,
            ProductFeature.sales_count,
            func.row_number()
            .partition_by(ProductFeature.product_id)
            .order_by(ProductFeature.collected_at.desc())
            .label("rn"),
        )
        .where(ProductFeature.product_id.in_(
            select(Product.id).where(Product.user_id == user.id)
        ))
        .subquery()
    )

    trend_up_result = await db.execute(
        select(func.count()).select_from(
            select(
                latest_features_subq.c.product_id,
                latest_features_subq.c.sales_count.label("latest_sales"),
                prev_features_subq.c.sales_count.label("prev_sales"),
            )
            .select_from(latest_features_subq)
            .join(
                prev_features_subq,
                (latest_features_subq.c.product_id == prev_features_subq.c.product_id)
                & (prev_features_subq.c.rn == 2),
            )
            .where(latest_features_subq.c.rn == 1)
            .where(latest_features_subq.c.latest_sales > prev_features_subq.c.prev_sales)
            .where(prev_features_subq.c.prev_sales > 0)
            .subquery()
        )
    )
    trend_up_count = trend_up_result.scalar() or 0

    trend_down_result = await db.execute(
        select(func.count()).select_from(
            select(
                latest_features_subq.c.product_id,
            )
            .select_from(latest_features_subq)
            .join(
                prev_features_subq,
                (latest_features_subq.c.product_id == prev_features_subq.c.product_id)
                & (prev_features_subq.c.rn == 2),
            )
            .where(latest_features_subq.c.rn == 1)
            .where(latest_features_subq.c.latest_sales < prev_features_subq.c.prev_sales)
            .where(prev_features_subq.c.prev_sales > 0)
            .subquery()
        )
    )
    trend_down_count = trend_down_result.scalar() or 0

    if trend_up_count + trend_down_count > 0:
        trend_pct = round((trend_up_count - trend_down_count) / (trend_up_count + trend_down_count) * 100, 1)
        today_trend = f"+{trend_pct}%" if trend_pct >= 0 else f"{trend_pct}%"
    else:
        today_trend = "0%"

    ai_recommend_result = await db.execute(
        select(func.count()).select_from(AIAnalysis).where(
            AIAnalysis.user_id == user.id,
            AIAnalysis.analysis_type.in_(["basic_analysis", "trend_score", "prediction"]),
            AIAnalysis.status == "completed",
        )
    )
    ai_recommendations = ai_recommend_result.scalar() or 0

    risk_alert_result = await db.execute(
        select(func.count()).select_from(AIAnalysis).where(
            AIAnalysis.user_id == user.id,
            AIAnalysis.analysis_type == "risk_warning",
            AIAnalysis.status == "completed",
        )
    )
    risk_alerts = risk_alert_result.scalar() or 0

    today_collect_result = await db.execute(
        select(func.count()).select_from(CollectTask).where(
            CollectTask.user_id == user.id,
            CollectTask.created_at >= today_start,
        )
    )
    today_collect = today_collect_result.scalar() or 0

    active_tasks_result = await db.execute(
        select(func.count()).select_from(CollectTask).where(
            CollectTask.user_id == user.id,
            CollectTask.status.in_(["pending", "running"]),
        )
    )
    active_tasks = active_tasks_result.scalar() or 0

    completed_items_result = await db.execute(
        select(func.count()).select_from(CollectTaskItem).where(
            CollectTaskItem.task_id.in_(
                select(CollectTask.id).where(CollectTask.user_id == user.id)
            ),
            CollectTaskItem.status == "completed",
        )
    )
    completed_items = completed_items_result.scalar() or 0

    total_items_result = await db.execute(
        select(func.count()).select_from(CollectTaskItem).where(
            CollectTaskItem.task_id.in_(
                select(CollectTask.id).where(CollectTask.user_id == user.id)
            ),
        )
    )
    total_items = total_items_result.scalar() or 0

    success_rate = round(completed_items / total_items * 100, 1) if total_items > 0 else 0

    collect_running_result = await db.execute(
        select(func.count()).select_from(CollectTask).where(
            CollectTask.user_id == user.id,
            CollectTask.status == "running",
        )
    )
    collect_running = (collect_running_result.scalar() or 0) > 0

    today_ai_result = await db.execute(
        select(func.count()).select_from(AIAnalysis).where(
            AIAnalysis.user_id == user.id,
            AIAnalysis.created_at >= today_start,
            AIAnalysis.status == "completed",
        )
    )
    today_ai_count = today_ai_result.scalar() or 0

    recent_products_result = await db.execute(
        select(Product).where(Product.user_id == user.id)
        .order_by(Product.updated_at.desc())
        .limit(5)
    )
    recent_products = recent_products_result.scalars().all()

    recent_items = []
    for p in recent_products:
        feat_result = await db.execute(
            select(ProductFeature)
            .where(ProductFeature.product_id == p.id)
            .order_by(ProductFeature.collected_at.desc())
            .limit(2)
        )
        features = feat_result.scalars().all()

        trend = 0.0
        if len(features) >= 2 and features[0].sales_count and features[1].sales_count and features[1].sales_count > 0:
            trend = round((features[0].sales_count - features[1].sales_count) / features[1].sales_count * 100, 1)

        recent_items.append({
            "id": str(p.id),
            "name": p.product_name,
            "platform": p.platform,
            "price": float(features[0].price) if features and features[0].price else None,
            "trend": trend,
            "image_url": p.image_url,
            "is_active": p.is_active,
        })

    platform_dist_result = await db.execute(
        select(Product.platform, func.count().label("count"))
        .where(Product.user_id == user.id)
        .group_by(Product.platform)
    )
    platform_dist = {row[0]: row[1] for row in platform_dist_result.all()}

    return {
        "code": 0,
        "data": {
            "product_count": product_count,
            "active_product_count": active_product_count,
            "today_trend": today_trend,
            "trend_up_count": trend_up_count,
            "trend_down_count": trend_down_count,
            "ai_recommendations": ai_recommendations,
            "risk_alerts": risk_alerts,
            "today_collect": today_collect,
            "active_tasks": active_tasks,
            "success_rate": success_rate,
            "collect_running": collect_running,
            "today_ai_count": today_ai_count,
            "recent_products": recent_items,
            "platform_distribution": platform_dist,
        },
    }
