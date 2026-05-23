import logging
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BadRequestException
from app.middleware.auth import CurrentUser
from app.models.aipic import AipicUserWork
from app.services.aipic.credits_service import get_credits_log, get_or_create_credits

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/aipic/user", tags=["aipic-user"])


@router.get("/works")
async def get_works(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=50),
    favorite_only: bool = Query(False),
):
    query = select(AipicUserWork).where(
        AipicUserWork.user_id == user.id,
        not AipicUserWork.is_deleted,
    )
    count_query = select(func.count()).where(
        AipicUserWork.user_id == user.id,
        not AipicUserWork.is_deleted,
    )

    if favorite_only:
        query = query.where(AipicUserWork.is_favorite)
        count_query = count_query.where(AipicUserWork.is_favorite)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(AipicUserWork.created_at.desc()).offset(offset).limit(page_size)
    )
    works = result.scalars().all()

    return {
        "code": 0,
        "data": {
            "total": total,
            "items": [
                {
                    "id": str(w.id),
                    "task_id": w.task_id,
                    "prompt": w.prompt[:100],
                    "negative_prompt": w.negative_prompt[:50],
                    "model_name": w.model_name,
                    "ratio_key": w.ratio_key,
                    "style_name": w.style_name,
                    "task_type": w.task_type,
                    "quality_tier": w.quality_tier,
                    "output_image_path": w.output_image_path,
                    "is_favorite": w.is_favorite,
                    "created_at": w.created_at.isoformat() if w.created_at else None,
                }
                for w in works
            ],
            "page": page,
            "page_size": page_size,
        },
    }


@router.post("/works/{work_id}/favorite")
async def toggle_favorite(
    work_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AipicUserWork).where(
            AipicUserWork.id == uuid.UUID(work_id),
            AipicUserWork.user_id == user.id,
            not AipicUserWork.is_deleted,
        )
    )
    work = result.scalar_one_or_none()
    if not work:
        raise BadRequestException(code=43010, message="作品不存在")

    work.is_favorite = not work.is_favorite
    await db.flush()
    await db.commit()

    return {"code": 0, "data": {"is_favorite": work.is_favorite}}


@router.delete("/works/{work_id}")
async def delete_work(
    work_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AipicUserWork).where(
            AipicUserWork.id == uuid.UUID(work_id),
            AipicUserWork.user_id == user.id,
        )
    )
    work = result.scalar_one_or_none()
    if not work:
        raise BadRequestException(code=43010, message="作品不存在")

    work.is_deleted = True
    await db.flush()
    await db.commit()

    return {"code": 0, "data": {"message": "删除成功"}}


@router.get("/credits")
async def get_credits(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    plan = user.plan or "free"
    credits = await get_or_create_credits(db, user.id, plan)
    await db.commit()

    return {
        "code": 0,
        "data": {
            "credits": credits.credits,
            "total_purchased": credits.total_purchased,
            "total_used": credits.total_used,
            "daily_generate_limit": credits.daily_generate_limit,
            "today_generated_count": credits.today_generated_count,
            "remaining_today": max(0, credits.daily_generate_limit - credits.today_generated_count)
            if credits.daily_generate_limit > 0
            else -1,
        },
    }


@router.get("/credits/log")
async def get_credits_history(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=50),
):
    result = await get_credits_log(db, user.id, page=page, page_size=page_size)
    await db.commit()
    return {"code": 0, "data": result}
