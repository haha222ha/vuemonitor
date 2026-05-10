import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundException
from app.middleware.auth import CurrentUser
from app.ai.service import AIService

router = APIRouter(prefix="/ai", tags=["ai"])


class AnalysisRequest(BaseModel):
    product_id: str
    analysis_type: str = Field(..., pattern="^(basic_analysis|trend_score|prediction|risk_warning|report|product_optimization)$")
    provider: str | None = None


class ReportRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    report_type: str = Field(..., pattern="^(product|category|trend|risk)$")
    product_ids: list[str] = Field(..., min_length=1)
    provider: str | None = None


@router.post("/analyze")
async def analyze_product(
    req: AnalysisRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
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
):
    from app.models.ai import AIReport

    result = await db.execute(
        select(AIReport).where(AIReport.user_id == user.id).order_by(AIReport.created_at.desc())
    )
    reports = result.scalars().all()

    return {
        "code": 0,
        "data": [
            {
                "id": str(r.id),
                "title": r.title,
                "report_type": r.report_type,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reports
        ],
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
