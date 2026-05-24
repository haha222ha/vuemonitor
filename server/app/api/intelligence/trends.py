from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.intelligence.deps import get_intel_plan
from app.core.database import get_db
from app.models.intelligence import IntelligenceTrend

router = APIRouter(prefix="/trends", tags=["intel-trends"])


@router.get("")
async def list_trends(
    plan: str = Depends(get_intel_plan),
    category: str | None = Query(None),
    platform: str | None = Query(None),
    lifecycle: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(IntelligenceTrend).where(IntelligenceTrend.trend_status == "active")

    if plan == "free":
        stmt = stmt.limit(3)
    elif plan == "weekly":
        stmt = stmt.limit(5)
    elif plan == "monthly":
        stmt = stmt.where(IntelligenceTrend.direction != "falling")

    if category:
        stmt = stmt.where(IntelligenceTrend.category == category)
    if platform:
        stmt = stmt.where(IntelligenceTrend.platform == platform)
    if lifecycle:
        stmt = stmt.where(IntelligenceTrend.lifecycle == lifecycle)

    stmt = stmt.order_by(IntelligenceTrend.opportunity_score.desc())

    result = await db.execute(stmt)
    trends = result.scalars().all()

    return {
        "plan": plan,
        "count": len(trends),
        "items": [
            {
                "id": str(t.id), "title": t.title, "category": t.category,
                "platform": t.platform, "opportunity_score": t.opportunity_score,
                "lifecycle": t.lifecycle, "competition": t.competition,
                "risk_level": t.risk_level, "direction": t.direction,
                "evidence": t.evidence, "actionable_insight": t.actionable_insight,
                "affected_opportunities": t.affected_opportunities,
                "risk_note": t.risk_note, "trend_history": t.trend_history,
                "peak_expected": t.peak_expected.isoformat() if t.peak_expected else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in trends
        ],
    }