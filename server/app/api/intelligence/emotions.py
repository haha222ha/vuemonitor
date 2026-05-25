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
                "id": str(e.id),
                "keyword": e.keyword,
                "sentiment": e.emotion_type or "neutral",
                "intensity": _parse_intensity(e.intensity),
                "volume": 0,
                "keyword_cluster": e.keyword_cluster if isinstance(e.keyword_cluster, list) else [],
                "related_keywords": e.keyword_cluster if isinstance(e.keyword_cluster, list) else [],
                "platform_source": e.platform_source,
                "trend_direction": e.trend_direction,
                "emotion_type": e.emotion_type,
                "intensity_raw": e.intensity,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in emotions
        ],
    }


def _parse_intensity(val) -> float:
    if val is None:
        return 0.5
    if isinstance(val, (int, float)):
        return float(val)
    mapping = {"high": 0.9, "medium": 0.6, "low": 0.3, "极高": 0.95, "高": 0.8, "中": 0.5, "低": 0.3, "极低": 0.1}
    return mapping.get(str(val).lower(), 0.5)
