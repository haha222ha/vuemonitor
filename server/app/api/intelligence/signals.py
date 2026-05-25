from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.intelligence.deps import get_intel_plan
from app.core.database import get_db
from app.models.intelligence import IntelligencePlatformSignal

router = APIRouter(prefix="/signals", tags=["intel-signals"])


@router.get("")
async def list_signals(
    plan: str = Depends(get_intel_plan),
    db: AsyncSession = Depends(get_db),
):
    if plan in ("free", "weekly"):
        return {"plan": plan, "count": 0, "items": [], "message": "platform signals require monthly or higher plan"}

    result = await db.execute(select(IntelligencePlatformSignal))
    signals = result.scalars().all()

    return {
        "plan": plan,
        "count": len(signals),
        "items": [
            {
                "id": str(s.id),
                "title": s.current_focus or s.platform,
                "description": s.impact_on_side_hustle or s.traffic_signal or "",
                "platform": s.platform,
                "type": s.change_direction or "market",
                "impact_level": s.magnitude or "medium",
                "detected_at": s.created_at.isoformat() if s.created_at else None,
                "current_focus": s.current_focus,
                "traffic_signal": s.traffic_signal,
                "policy_risk": s.policy_risk,
                "change_direction": s.change_direction,
                "magnitude": s.magnitude,
                "impact_on_side_hustle": s.impact_on_side_hustle,
                "signal_history": s.signal_history,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in signals
        ],
    }
