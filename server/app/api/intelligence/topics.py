from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.intelligence.deps import get_intel_plan
from app.core.database import get_db
from app.models.intelligence import IntelligenceXhsTopic

router = APIRouter(prefix="/topics", tags=["intel-topics"])


@router.get("")
async def list_topics(
    plan: str = Depends(get_intel_plan),
    hook_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    if plan in ("free", "weekly"):
        return {"plan": plan, "count": 0, "items": [], "message": "topics require monthly or higher plan"}

    stmt = select(IntelligenceXhsTopic)

    if hook_type:
        stmt = stmt.where(IntelligenceXhsTopic.hook_type == hook_type)

    stmt = stmt.order_by(IntelligenceXhsTopic.ctr_prediction.desc())

    result = await db.execute(stmt)
    topics = result.scalars().all()

    return {
        "plan": plan,
        "count": len(topics),
        "items": [
            {
                "id": str(t.id), "title": t.title, "hook_type": t.hook_type,
                "emotion": t.emotion, "platform": t.platform,
                "content_type": t.content_type, "ctr_prediction": t.ctr_prediction,
                "competition": t.competition, "topic_data": t.topic_data,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in topics
        ],
    }