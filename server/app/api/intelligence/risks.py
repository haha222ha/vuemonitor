from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.intelligence.content_filter import is_demo_content
from app.api.intelligence.deps import get_intel_plan
from app.core.database import get_db
from app.models.intelligence import IntelligenceRisk

router = APIRouter(prefix="/risks", tags=["intel-risks"])

_DISPLAY_STATUSES = (
    "active",
    "monitoring",
    "escalating",
    "dead",
    "dying",
)


@router.get("")
async def list_risks(
    plan: str = Depends(get_intel_plan),
    severity: str | None = Query(None),
    risk_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    if plan == "free":
        return {"plan": "free", "count": 0, "items": [], "message": "free tier does not include risks"}

    stmt = select(IntelligenceRisk).where(IntelligenceRisk.status.in_(_DISPLAY_STATUSES))

    if severity:
        stmt = stmt.where(IntelligenceRisk.severity == severity)
    if risk_type:
        stmt = stmt.where(IntelligenceRisk.risk_type == risk_type)

    stmt = stmt.order_by(IntelligenceRisk.severity.desc(), IntelligenceRisk.created_at.desc())

    result = await db.execute(stmt)
    all_risks = result.scalars().all()

    risks = [
        r for r in all_risks
        if not is_demo_content(r.name, r.reason, r.risk_description, r.alternative)
    ]

    if plan == "weekly":
        risks = risks[:3]

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