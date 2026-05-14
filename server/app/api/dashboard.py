from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get, cache_set
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
    cache_key = f"dashboard:stats:{user.id}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return {"code": 0, "data": cached}
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

    recent_product_ids = [p.id for p in recent_products]

    recent_items = []
    if recent_product_ids:
        ranked_features = (
            select(
                ProductFeature.product_id,
                ProductFeature.price,
                ProductFeature.sales_count,
                func.row_number()
                .partition_by(ProductFeature.product_id)
                .order_by(ProductFeature.collected_at.desc())
                .label("rn"),
            )
            .where(ProductFeature.product_id.in_(recent_product_ids))
            .subquery()
        )

        feat_rows = await db.execute(
            select(
                ranked_features.c.product_id,
                ranked_features.c.price,
                ranked_features.c.sales_count,
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
            feat_map[pid].append({"price": row[1], "sales_count": row[2]})

        for p in recent_products:
            feats = feat_map.get(p.id, [])
            latest = feats[0] if len(feats) >= 1 else None
            prev = feats[1] if len(feats) >= 2 else None

            trend = 0.0
            if latest and prev and prev["sales_count"] and prev["sales_count"] > 0 and latest["sales_count"]:
                trend = round((latest["sales_count"] - prev["sales_count"]) / prev["sales_count"] * 100, 1)

            recent_items.append({
                "id": str(p.id),
                "name": p.product_name,
                "platform": p.platform,
                "price": float(latest["price"]) if latest and latest["price"] else None,
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

    stats_data = {
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
    }

    await cache_set(cache_key, stats_data, ttl_seconds=120)

    return {
        "code": 0,
        "data": stats_data,
    }


@router.get("/trend")
async def get_dashboard_trend(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    days: int = 7,
):
    cache_key = f"dashboard:trend:{user.id}:{days}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return {"code": 0, "data": cached}

    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)

    product_daily_result = await db.execute(
        select(
            func.date_trunc("day", Product.created_at).label("day"),
            func.count().label("count"),
        )
        .where(Product.user_id == user.id, Product.created_at >= start_date)
        .group_by(func.date_trunc("day", Product.created_at))
        .order_by(text("day"))
    )
    product_map = {row[0].date(): row[1] for row in product_daily_result.all()}

    collect_daily_result = await db.execute(
        select(
            func.date_trunc("day", CollectTask.created_at).label("day"),
            func.count().label("count"),
        )
        .where(CollectTask.user_id == user.id, CollectTask.created_at >= start_date)
        .group_by(func.date_trunc("day", CollectTask.created_at))
        .order_by(text("day"))
    )
    collect_map = {row[0].date(): row[1] for row in collect_daily_result.all()}

    ai_daily_result = await db.execute(
        select(
            func.date_trunc("day", AIAnalysis.created_at).label("day"),
            func.count().label("count"),
        )
        .where(AIAnalysis.user_id == user.id, AIAnalysis.created_at >= start_date)
        .group_by(func.date_trunc("day", AIAnalysis.created_at))
        .order_by(text("day"))
    )
    ai_map = {row[0].date(): row[1] for row in ai_daily_result.all()}

    dates = []
    product_daily = []
    collect_daily = []
    ai_daily = []

    for i in range(days):
        d = (now - timedelta(days=days - 1 - i)).date()
        dates.append(d)
        product_daily.append(product_map.get(d, 0))
        collect_daily.append(collect_map.get(d, 0))
        ai_daily.append(ai_map.get(d, 0))

    trend_data = {
        "dates": [d.isoformat() for d in dates],
        "products": product_daily,
        "collects": collect_daily,
        "ai_analyses": ai_daily,
    }

    await cache_set(cache_key, trend_data, ttl_seconds=300)

    return {
        "code": 0,
        "data": trend_data,
    }


@router.get("/activities")
async def get_recent_activities(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    limit: int = 10,
):
    activities = []

    recent_tasks_result = await db.execute(
        select(CollectTask)
        .where(CollectTask.user_id == user.id)
        .order_by(CollectTask.created_at.desc())
        .limit(limit)
    )
    recent_tasks = recent_tasks_result.scalars().all()

    for t in recent_tasks:
        summary = ""
        if t.status == "completed" and t.result_summary:
            s = t.result_summary
            summary = f"成功 {s.get('success', 0)} / 失败 {s.get('failed', 0)} / 风控 {s.get('risk_detected', 0)}"
        elif t.status == "failed":
            summary = t.error_message or "采集失败"
        elif t.status == "running":
            summary = f"进度 {t.progress or 0}%"
        elif t.status == "pending":
            summary = "等待执行"

        activities.append({
            "type": "collect",
            "title": f"{_platform_label(t.platform)} 采集任务",
            "status": t.status,
            "summary": summary,
            "time": t.created_at.isoformat() if t.created_at else None,
            "id": str(t.id),
        })

    recent_ai_result = await db.execute(
        select(AIAnalysis)
        .where(AIAnalysis.user_id == user.id)
        .order_by(AIAnalysis.created_at.desc())
        .limit(limit)
    )
    recent_ai = recent_ai_result.scalars().all()

    for a in recent_ai:
        activities.append({
            "type": "ai",
            "title": f"AI {_analysis_label(a.analysis_type)}",
            "status": a.status,
            "summary": f"模型: {a.model or 'unknown'}" if a.status == "completed" else "分析中",
            "time": a.created_at.isoformat() if a.created_at else None,
            "id": str(a.id),
        })

    activities.sort(key=lambda x: x["time"] or "", reverse=True)

    return {
        "code": 0,
        "data": {
            "items": activities[:limit],
        },
    }


def _platform_label(platform: str) -> str:
    mapping = {"xhs": "小红书", "taobao": "淘宝", "jd": "京东", "pdd": "拼多多", "douyin": "抖音"}
    return mapping.get(platform, platform)


def _analysis_label(analysis_type: str) -> str:
    mapping = {
        "basic_analysis": "基础分析",
        "trend_score": "趋势评分",
        "prediction": "爆品预测",
        "risk_warning": "风险预警",
    }
    return mapping.get(analysis_type, analysis_type)


@router.get("/home")
async def get_home_data(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"dashboard:home:{user.id}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return {"code": 0, "data": cached}

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    product_count_result = await db.execute(
        select(func.count()).select_from(Product).where(Product.user_id == user.id)
    )
    product_count = product_count_result.scalar() or 0

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
            select(latest_features_subq.c.product_id)
            .select_from(latest_features_subq)
            .join(
                prev_features_subq,
                (latest_features_subq.c.product_id == prev_features_subq.c.product_id)
                & (prev_features_subq.c.rn == 2),
            )
            .where(latest_features_subq.c.rn == 1)
            .where(latest_features_subq.c.sales_count > prev_features_subq.c.sales_count)
            .where(prev_features_subq.c.sales_count > 0)
            .subquery()
        )
    )
    trend_up_count = trend_up_result.scalar() or 0

    trend_down_result = await db.execute(
        select(func.count()).select_from(
            select(latest_features_subq.c.product_id)
            .select_from(latest_features_subq)
            .join(
                prev_features_subq,
                (latest_features_subq.c.product_id == prev_features_subq.c.product_id)
                & (prev_features_subq.c.rn == 2),
            )
            .where(latest_features_subq.c.rn == 1)
            .where(latest_features_subq.c.sales_count < prev_features_subq.c.sales_count)
            .where(prev_features_subq.c.sales_count > 0)
            .subquery()
        )
    )
    trend_down_count = trend_down_result.scalar() or 0

    if trend_up_count + trend_down_count > 0:
        trend_pct = round((trend_up_count - trend_down_count) / (trend_up_count + trend_down_count) * 100, 1)
        today_trend = f"+{trend_pct}%" if trend_pct >= 0 else f"{trend_pct}%"
    else:
        today_trend = "0%"

    today_ai_result = await db.execute(
        select(func.count()).select_from(AIAnalysis).where(
            AIAnalysis.user_id == user.id,
            AIAnalysis.created_at >= today_start,
            AIAnalysis.status == "completed",
        )
    )
    today_ai_count = today_ai_result.scalar() or 0

    rankings_result = await db.execute(
        text("""
            SELECT pr.product_id, pr.overall_rank, pr.overall_score,
                   pr.trend_short, pr.lifecycle_stage, p.product_name, p.category
            FROM product_rankings pr
            JOIN products p ON p.id = pr.product_id
            WHERE p.user_id = :uid
            ORDER BY pr.overall_rank ASC NULLS LAST
            LIMIT 5
        """),
        {"uid": user.id},
    )
    rankings = [
        {
            "product_id": str(r.product_id),
            "product_name": r.product_name,
            "category": r.category,
            "overall_rank": r.overall_rank,
            "overall_score": float(r.overall_score) if r.overall_score else None,
            "trend_short": r.trend_short,
            "lifecycle_stage": r.lifecycle_stage,
        }
        for r in rankings_result.mappings().all()
    ]

    from app.models.alert_rule import AlertEvent
    alert_events_result = await db.execute(
        select(AlertEvent)
        .where(AlertEvent.user_id == user.id, AlertEvent.is_acknowledged == False)
        .order_by(AlertEvent.created_at.desc())
        .limit(5)
    )
    alert_events = [
        {
            "id": str(e.id),
            "rule_id": str(e.rule_id),
            "severity": e.severity,
            "title": e.title,
            "detail": e.detail,
            "metric_value": e.metric_value,
            "threshold_value": e.threshold_value,
            "is_acknowledged": e.is_acknowledged,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in alert_events_result.scalars().all()
    ]

    unack_alert_count_result = await db.execute(
        select(func.count()).select_from(AlertEvent).where(
            AlertEvent.user_id == user.id, AlertEvent.is_acknowledged == False
        )
    )
    unack_alert_count = unack_alert_count_result.scalar() or 0

    home_data = {
        "biz_stats": {
            "opportunity_count": len(rankings),
            "today_trend": today_trend,
            "trend_up_count": trend_up_count,
            "trend_down_count": trend_down_count,
            "alert_count": unack_alert_count,
            "ai_insight_count": today_ai_count,
            "product_count": product_count,
        },
        "rankings": rankings,
        "alert_events": alert_events,
    }

    await cache_set(cache_key, home_data, ttl_seconds=60)

    return {"code": 0, "data": home_data}
