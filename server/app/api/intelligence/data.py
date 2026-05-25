import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.intelligence.deps import get_intel_plan
from app.core.database import get_db
from app.middleware.auth import CurrentUser
from app.models.intelligence import (
    IntelligenceOpportunity,
    IntelligencePlatformSignal,
    IntelligenceRisk,
    IntelligenceTrend,
    IntelligenceUserEmotion,
    IntelligenceXhsTopic,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data", tags=["intel-data-management"])


async def _verify_admin_or_owner(user: CurrentUser, db: AsyncSession):
    if user.role == "admin":
        return True
    raise HTTPException(status_code=403, detail="only admin can delete data")


@router.delete("/trends/{item_id}")
async def delete_trend(
    item_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    await _verify_admin_or_owner(user, db)
    result = await db.execute(select(IntelligenceTrend).where(IntelligenceTrend.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="not found")
    await db.delete(item)
    await db.flush()
    return {"status": "deleted", "id": item_id}


@router.delete("/opportunities/{item_id}")
async def delete_opportunity(
    item_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    await _verify_admin_or_owner(user, db)
    result = await db.execute(select(IntelligenceOpportunity).where(IntelligenceOpportunity.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="not found")
    await db.delete(item)
    await db.flush()
    return {"status": "deleted", "id": item_id}


@router.delete("/risks/{item_id}")
async def delete_risk(
    item_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    await _verify_admin_or_owner(user, db)
    result = await db.execute(select(IntelligenceRisk).where(IntelligenceRisk.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="not found")
    await db.delete(item)
    await db.flush()
    return {"status": "deleted", "id": item_id}


@router.delete("/topics/{item_id}")
async def delete_topic(
    item_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    await _verify_admin_or_owner(user, db)
    result = await db.execute(select(IntelligenceXhsTopic).where(IntelligenceXhsTopic.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="not found")
    await db.delete(item)
    await db.flush()
    return {"status": "deleted", "id": item_id}


@router.delete("/signals/{item_id}")
async def delete_signal(
    item_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    await _verify_admin_or_owner(user, db)
    result = await db.execute(select(IntelligencePlatformSignal).where(IntelligencePlatformSignal.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="not found")
    await db.delete(item)
    await db.flush()
    return {"status": "deleted", "id": item_id}


@router.delete("/emotions/{item_id}")
async def delete_emotion(
    item_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    await _verify_admin_or_owner(user, db)
    result = await db.execute(select(IntelligenceUserEmotion).where(IntelligenceUserEmotion.id == item_id))
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="not found")
    await db.delete(item)
    await db.flush()
    return {"status": "deleted", "id": item_id}
