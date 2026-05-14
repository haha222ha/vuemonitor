import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.middleware.auth import CurrentUser
from app.ai.service import AIService
from app.ai.providers import ANALYSIS_PROMPTS, get_available_providers

router = APIRouter(prefix="/ai", tags=["ai"])

_VALID_ANALYSIS_TYPES = "|".join(ANALYSIS_PROMPTS.keys())


class AnalysisRequest(BaseModel):
    product_id: str
    analysis_type: str = Field(..., description=f"分析类型，可选: {_VALID_ANALYSIS_TYPES}")
    provider: str | None = None


class ReportRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    report_type: str = Field(..., pattern="^(product|category|trend|risk)$")
    product_ids: list[str] = Field(..., min_length=1)
    provider: str | None = None


@router.get("/status")
async def ai_status():
    available = get_available_providers()
    analysis_types = list(ANALYSIS_PROMPTS.keys())
    return {
        "code": 0,
        "data": {
            "available_providers": available,
            "default_provider": available[0] if available else None,
            "analysis_types": analysis_types,
            "ai_enabled": len(available) > 0,
        },
    }


@router.post("/analyze")
async def analyze_product(
    req: AnalysisRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    if req.analysis_type not in ANALYSIS_PROMPTS:
        from app.core.exceptions import BadRequestException
        raise BadRequestException(message=f"不支持的分析类型：{req.analysis_type}，可选类型：{', '.join(ANALYSIS_PROMPTS.keys())}")

    svc = AIService(db)
    result = await svc.analyze_product(
        user_id=user.id,
        product_id=uuid.UUID(req.product_id),
        analysis_type=req.analysis_type,
        provider_name=req.provider,
    )
    return {"code": 0, "data": result}


@router.post("/report")
async def generate_report(
    req: ReportRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = AIService(db)
    result = await svc.generate_report(
        user_id=user.id,
        title=req.title,
        report_type=req.report_type,
        product_ids=req.product_ids,
        provider_name=req.provider,
    )
    return {"code": 0, "data": result}


@router.get("/analyses")
async def list_analyses(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    product_id: str | None = None,
    analysis_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    from app.models.ai import AIAnalysis

    query = select(AIAnalysis).where(AIAnalysis.user_id == user.id)
    if product_id:
        query = query.where(AIAnalysis.product_id == uuid.UUID(product_id))
    if analysis_type:
        query = query.where(AIAnalysis.analysis_type == analysis_type)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    result = await db.execute(
        query.order_by(AIAnalysis.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    analyses = result.scalars().all()

    return {
        "code": 0,
        "data": {
            "total": total,
            "items": [
                {
                    "id": str(a.id),
                    "product_id": str(a.product_id) if a.product_id else None,
                    "analysis_type": a.analysis_type,
                    "provider": a.provider,
                    "model": a.model,
                    "result": a.result,
                    "confidence": float(a.confidence) if a.confidence else None,
                    "status": a.status,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in analyses
            ],
        },
    }


@router.get("/reports")
async def list_reports(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    from app.models.ai import AIReport

    query = select(AIReport).where(AIReport.user_id == user.id)
    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar() or 0

    result = await db.execute(
        query.order_by(AIReport.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )
    reports = result.scalars().all()

    return {
        "code": 0,
        "data": {
            "total": total,
            "items": [
                {
                    "id": str(r.id),
                    "title": r.title,
                    "report_type": r.report_type,
                    "status": r.status,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in reports
            ],
        },
    }


@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    from app.models.ai import AIReport

    result = await db.execute(
        select(AIReport).where(AIReport.id == uuid.UUID(report_id), AIReport.user_id == user.id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise NotFoundException(message="报告不存在")

    return {
        "code": 0,
        "data": {
            "id": str(report.id),
            "title": report.title,
            "report_type": report.report_type,
            "content": report.content,
            "status": report.status,
            "created_at": report.created_at.isoformat() if report.created_at else None,
        },
    }


@router.delete("/reports/{report_id}")
async def delete_report(
    report_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    from app.models.ai import AIReport

    result = await db.execute(
        select(AIReport).where(AIReport.id == uuid.UUID(report_id), AIReport.user_id == user.id)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise NotFoundException(message="报告不存在")

    await db.delete(report)
    await db.flush()
    return {"code": 0, "data": {"deleted": True}}


@router.delete("/analyses/{analysis_id}")
async def delete_analysis(
    analysis_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    from app.models.ai import AIAnalysis

    result = await db.execute(
        select(AIAnalysis).where(AIAnalysis.id == uuid.UUID(analysis_id), AIAnalysis.user_id == user.id)
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise NotFoundException(message="分析记录不存在")

    await db.delete(analysis)
    await db.flush()
    return {"code": 0, "data": {"deleted": True}}


@router.get("/recommendations")
async def get_recommendations(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(5, ge=1, le=20),
):
    from app.models.product import Product, ProductFeature
    from app.models.alert_rule import AlertEvent

    recommendations = []

    trending_products = await db.execute(
        text("""
            SELECT p.id, p.product_name, p.category, p.image_url,
                   pr.overall_rank, pr.category_rank, pr.lifecycle_stage,
                   pr.trend_short, pr.growth_rate_7d, pr.sales_velocity
            FROM product_rankings pr
            JOIN products p ON p.id = pr.product_id
            WHERE p.user_id = :uid
              AND pr.trend_short = 'rising'
            ORDER BY pr.growth_rate_7d DESC NULLS LAST
            LIMIT :lim
        """),
        {"uid": user.id, "lim": limit},
    )
    for row in trending_products.mappings().all():
        recommendations.append({
            "type": "trending",
            "priority": 1,
            "product_id": str(row["id"]),
            "product_name": row["product_name"],
            "category": row["category"],
            "image_url": row["image_url"],
            "reason": f"7日增长率 {row['growth_rate_7d']:.1f}%，趋势上升" if row["growth_rate_7d"] else "趋势上升中",
            "metric": {"growth_rate_7d": float(row["growth_rate_7d"]) if row["growth_rate_7d"] else None, "rank": row["overall_rank"]},
        })

    unack_events = await db.execute(
        select(AlertEvent)
        .where(AlertEvent.user_id == user.id, AlertEvent.is_acknowledged == False)
        .order_by(AlertEvent.severity.desc(), AlertEvent.created_at.desc())
        .limit(limit),
    )
    for event in unack_events.scalars().all():
        recommendations.append({
            "type": "alert",
            "priority": 0 if event.severity == "critical" else 2,
            "event_id": str(event.id),
            "rule_id": str(event.rule_id),
            "title": event.title,
            "detail": event.detail,
            "severity": event.severity,
            "reason": f"未处理告警：{event.title}",
            "metric": {"metric_value": event.metric_value, "threshold_value": event.threshold_value},
        })

    hot_categories = await db.execute(
        text("""
            SELECT p.category, COUNT(*) as cnt,
                   AVG(pf.sales_count) as avg_sales,
                   AVG(pf.rating) as avg_rating
            FROM products p
            JOIN product_features pf ON pf.product_id = p.id
            WHERE p.user_id = :uid
              AND p.category IS NOT NULL
            GROUP BY p.category
            ORDER BY avg_sales DESC NULLS LAST
            LIMIT 3
        """),
        {"uid": user.id},
    )
    for row in hot_categories.mappings().all():
        recommendations.append({
            "type": "category_insight",
            "priority": 3,
            "category": row["category"],
            "reason": f"品类「{row['category']}」平均销量 {int(row['avg_sales'] or 0)}，评分 {float(row['avg_rating'] or 0):.1f}",
            "metric": {"avg_sales": int(row["avg_sales"] or 0), "avg_rating": float(row["avg_rating"] or 0), "product_count": row["cnt"]},
        })

    low_rank_products = await db.execute(
        text("""
            SELECT p.id, p.product_name, p.category, p.image_url,
                   pr.overall_rank, pr.competition_index, pr.volatility
            FROM product_rankings pr
            JOIN products p ON p.id = pr.product_id
            WHERE p.user_id = :uid
              AND pr.competition_index > 0.7
            ORDER BY pr.competition_index DESC
            LIMIT :lim
        """),
        {"uid": user.id, "lim": 3},
    )
    for row in low_rank_products.mappings().all():
        recommendations.append({
            "type": "risk",
            "priority": 2,
            "product_id": str(row["id"]),
            "product_name": row["product_name"],
            "category": row["category"],
            "image_url": row["image_url"],
            "reason": f"竞争指数 {float(row['competition_index'] or 0):.2f}，波动率 {float(row['volatility'] or 0):.2f}",
            "metric": {"competition_index": float(row["competition_index"] or 0), "volatility": float(row["volatility"] or 0)},
        })

    recommendations.sort(key=lambda x: x["priority"])

    return {
        "code": 0,
        "data": {
            "total": len(recommendations),
            "items": recommendations[:limit * 2],
        },
    }
