from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.intelligence.deps import get_intel_plan
from app.core.database import get_db
from app.models.intelligence import IntelligenceUserEmotion

router = APIRouter(prefix="/emotions", tags=["intel-emotions"])


@router.get("")
async def list_emotions(
    plan: str = Depends(get_intel_plan),
    db: AsyncSession = Depends(get_db),
):
    if plan in ("free", "weekly", "monthly"):
        return {"plan": plan, "count": 0, "items": [], "message": "user emotions require yearly or higher plan"}

    result = await db.execute(select(IntelligenceUserEmotion))
    emotions = result.scalars().all()

    return {
        "plan": plan,
        "count": len(emotions),
        "items": [
            {
                "id": str(e.id), "keyword": e.keyword,
                "emotion_type": e.emotion_type, "intensity": e.intensity,
                "keyword_cluster": e.keyword_cluster, "platform_source": e.platform_source,
                "trend_direction": e.trend_direction,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in emotions
        ],
    }