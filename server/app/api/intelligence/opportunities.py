from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.intelligence.deps import get_intel_plan
from app.core.database import get_db
from app.models.intelligence import IntelligenceOpportunity

router = APIRouter(prefix="/opportunities", tags=["intel-opportunities"])


@router.get("")
async def list_opportunities(
    plan: str = Depends(get_intel_plan),
    category: str | None = Query(None),
    verdict: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    if plan == "free":
        return {"plan": "free", "count": 0, "items": [], "message": "free tier does not include opportunities"}

    stmt = select(IntelligenceOpportunity).where(IntelligenceOpportunity.status == "active")

    if plan == "weekly":
        stmt = stmt.limit(3)

    if category:
        stmt = stmt.where(IntelligenceOpportunity.category == category)
    if verdict:
        stmt = stmt.where(IntelligenceOpportunity.verdict == verdict)

    stmt = stmt.order_by(IntelligenceOpportunity.verdict_score.desc())

    result = await db.execute(stmt)
    opps = result.scalars().all()

    return {
        "plan": plan,
        "count": len(opps),
        "items": [
            {
                "id": str(o.id), "name": o.name, "category": o.category,
                "sub_category": o.sub_category, "verdict_score": o.verdict_score,
                "verdict": o.verdict, "verdict_detail": o.verdict_detail,
                "difficulty": o.difficulty, "startup_cost": o.startup_cost,
                "monthly_ceiling": o.monthly_ceiling,
                "time_to_first_revenue": o.time_to_first_revenue,
                "risk_level": o.risk_level, "risk_flag": o.risk_flag,
                "persona_fit": o.persona_fit, "platform": o.platform,
                "lifecycle_stage": o.lifecycle_stage,
                "key_metrics": o.key_metrics,
                "commercial_paths": o.commercial_paths,
                "score_history": o.score_history,
                "trend_direction": o.trend_direction,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in opps
        ],
    }