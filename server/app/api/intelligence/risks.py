from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.intelligence.deps import get_intel_plan
from app.core.database import get_db
from app.models.intelligence import IntelligenceRisk

router = APIRouter(prefix="/risks", tags=["intel-risks"])


@router.get("")
async def list_risks(
    plan: str = Depends(get_intel_plan),
    severity: str | None = Query(None),
    risk_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    if plan == "free":
        return {"plan": "free", "count": 0, "items": [], "message": "free tier does not include risks"}

    stmt = select(IntelligenceRisk).where(
        IntelligenceRisk.status.in_(["active", "monitoring"])
    )

    if plan == "weekly":
        stmt = stmt.limit(3)

    if severity:
        stmt = stmt.where(IntelligenceRisk.severity == severity)
    if risk_type:
        stmt = stmt.where(IntelligenceRisk.risk_type == risk_type)

    stmt = stmt.order_by(IntelligenceRisk.severity.desc())

    result = await db.execute(stmt)
    risks = result.scalars().all()

    return {
        "plan": plan,
        "count": len(risks),
        "items": [
            {
                "id": str(r.id), "name": r.name, "category": r.category,
                "severity": r.severity, "status": r.status,
                "reason": r.reason, "alternative": r.alternative,
                "early_signal": r.early_signal, "early_signals": r.early_signals,
                "risk_type": r.risk_type, "risk_description": r.risk_description,
                "recommended_action": r.recommended_action,
                "affected_track": r.affected_track,
                "eliminated_date": r.eliminated_date.isoformat() if r.eliminated_date else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in risks
        ],
    }