from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.intelligence.deps import get_intel_plan
from app.core.database import get_db
from app.models.intelligence import IntelligenceReport

router = APIRouter(prefix="/reports", tags=["intel-reports"])


@router.get("")
async def list_reports(
    plan: str = Depends(get_intel_plan),
    report_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(IntelligenceReport)

    if plan == "free":
        return {"plan": "free", "count": 0, "items": [], "message": "free tier does not include reports"}
    elif plan == "weekly":
        stmt = stmt.where(IntelligenceReport.report_type == "weekly")
    elif plan == "monthly":
        stmt = stmt.where(IntelligenceReport.report_type.in_(["weekly", "monthly"]))
    elif plan in ("yearly", "enterprise"):
        pass

    if report_type:
        stmt = stmt.where(IntelligenceReport.report_type == report_type)

    stmt = stmt.order_by(IntelligenceReport.report_date.desc())

    result = await db.execute(stmt)
    reports = result.scalars().all()

    return {
        "plan": plan,
        "count": len(reports),
        "items": [
            {
                "id": str(r.id), "report_type": r.report_type,
                "title": r.title, "week_number": r.week_number,
                "report_date": r.report_date.isoformat() if r.report_date else None,
                "content_json": r.content_json, "content_html": r.content_html,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in reports
        ],
    }