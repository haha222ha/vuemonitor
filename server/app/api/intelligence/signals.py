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
                "id": str(s.id), "platform": s.platform,
                "current_focus": s.current_focus, "traffic_signal": s.traffic_signal,
                "policy_risk": s.policy_risk, "change_direction": s.change_direction,
                "magnitude": s.magnitude, "impact_on_side_hustle": s.impact_on_side_hustle,
                "signal_history": s.signal_history,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in signals
        ],
    }