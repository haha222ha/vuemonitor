import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.database import get_db
from app.core.exceptions import BadRequestException, ForbiddenException
from app.middleware.auth import CurrentUser
from app.models.aipic import AipicGenerateQueue
from app.services.aipic.credits_service import (
    check_daily_quota,
    deduct_credits,
    get_or_create_credits,
)
from app.services.aipic.generate_service import PRESET_RATIOS, QUALITY_TIERS, get_credits_cost
from app.services.aipic.queue_service import cancel_task, get_queue_stats, get_user_tasks, submit_task
from app.services.aipic.style_service import get_style_list

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/aipic/generate", tags=["aipic-generate"])


class Text2ImgRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    negative_prompt: str = Field("", max_length=1000)
    model: str = Field("gpt-image-2", max_length=50)
    ratio: str = Field("square", max_length=20)
    quality: str = Field("standard", pattern="^(standard|hd|ultra)$")
    style: str = Field("", max_length=100)


class Img2ImgRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    negative_prompt: str = Field("", max_length=1000)
    model: str = Field("gpt-image-2", max_length=50)
    ratio: str = Field("square", max_length=20)
    quality: str = Field("standard", pattern="^(standard|hd|ultra)$")
    style: str = Field("", max_length=100)
    input_image_path: str = Field("", max_length=500)


PLAN_QUALITY_ACCESS = {
    "free": "standard",
    "pro": "hd",
    "premium": "ultra",
    "enterprise": "ultra",
}

QUALITY_RANK = {"standard": 0, "hd": 1, "ultra": 2}


def _check_quality_access(plan: str, quality: str) -> None:
    allowed = PLAN_QUALITY_ACCESS.get(plan, "standard")
    if QUALITY_RANK.get(quality, 0) > QUALITY_RANK.get(allowed, 0):
        raise ForbiddenException(
            code=43001,
            message=f"{quality}画质为{allowed}及以上会员专属，请升级套餐",
        )


@router.post("/text2img")
async def text2img(
    req: Text2ImgRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    if not settings.AIPIC_ENABLED:
        raise ForbiddenException(code=43000, message="AI作图模块未启用")

    plan = user.plan or "free"
    _check_quality_access(plan, req.quality)

    credits = await get_or_create_credits(db, user.id, plan)
    credits_cost = get_credits_cost(req.quality)

    if credits.credits < credits_cost:
        raise ForbiddenException(
            code=43002,
            message=f"积分不足，当前{credits.credits}积分，需要{credits_cost}积分",
        )

    if not await check_daily_quota(db, user.id):
        raise ForbiddenException(
            code=43003,
            message="今日生成次数已达上限",
        )

    queue_stats = await get_queue_stats(db)
    if queue_stats["pending"] >= settings.AIPIC_MAX_QUEUE_SIZE:
        raise ForbiddenException(
            code=43004,
            message="生成队列已满，请稍后再试",
        )

    success, remaining = await deduct_credits(
        db, user.id, credits_cost, f"文生图：{req.prompt[:30]}"
    )
    if not success:
        raise ForbiddenException(code=43002, message="积分扣除失败")

    task = await submit_task(
        db=db,
        user_id=user.id,
        prompt=req.prompt,
        negative_prompt=req.negative_prompt,
        model_name=req.model,
        ratio_key=req.ratio,
        style_name=req.style,
        task_type="text2img",
        quality_tier=req.quality,
        credits_cost=credits_cost,
    )
    await db.commit()

    return {
        "code": 0,
        "data": {
            "task_id": task.task_id,
            "credits_cost": credits_cost,
            "remaining_credits": remaining,
            "queue_position": queue_stats["pending"] + 1,
        },
    }


@router.post("/img2img")
async def img2img(
    req: Img2ImgRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    if not settings.AIPIC_ENABLED:
        raise ForbiddenException(code=43000, message="AI作图模块未启用")

    plan = user.plan or "free"
    _check_quality_access(plan, req.quality)

    if not req.input_image_path:
        raise BadRequestException(code=43005, message="图生图必须提供参考图片")

    credits = await get_or_create_credits(db, user.id, plan)
    credits_cost = get_credits_cost(req.quality)

    if credits.credits < credits_cost:
        raise ForbiddenException(
            code=43002,
            message=f"积分不足，当前{credits.credits}积分，需要{credits_cost}积分",
        )

    if not await check_daily_quota(db, user.id):
        raise ForbiddenException(code=43003, message="今日生成次数已达上限")

    queue_stats = await get_queue_stats(db)
    if queue_stats["pending"] >= settings.AIPIC_MAX_QUEUE_SIZE:
        raise ForbiddenException(code=43004, message="生成队列已满，请稍后再试")

    success, remaining = await deduct_credits(
        db, user.id, credits_cost, f"图生图：{req.prompt[:30]}"
    )
    if not success:
        raise ForbiddenException(code=43002, message="积分扣除失败")

    task = await submit_task(
        db=db,
        user_id=user.id,
        prompt=req.prompt,
        negative_prompt=req.negative_prompt,
        model_name=req.model,
        ratio_key=req.ratio,
        style_name=req.style,
        task_type="img2img",
        quality_tier=req.quality,
        credits_cost=credits_cost,
        input_image_path=req.input_image_path,
    )
    await db.commit()

    return {
        "code": 0,
        "data": {
            "task_id": task.task_id,
            "credits_cost": credits_cost,
            "remaining_credits": remaining,
            "queue_position": queue_stats["pending"] + 1,
        },
    }


@router.get("/status/{task_id}")
async def get_task_status(
    task_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AipicGenerateQueue).where(
            AipicGenerateQueue.task_id == task_id,
            AipicGenerateQueue.user_id == user.id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise BadRequestException(code=43006, message="任务不存在")

    return {
        "code": 0,
        "data": {
            "task_id": task.task_id,
            "task_status": task.task_status,
            "prompt": task.prompt[:100],
            "model_name": task.model_name,
            "quality_tier": task.quality_tier,
            "credits_cost": task.credits_cost,
            "submit_time": task.created_at.isoformat() if task.created_at else None,
            "execute_time": task.execute_time.isoformat() if task.execute_time else None,
            "finish_time": task.finish_time.isoformat() if task.finish_time else None,
            "output_image_path": task.output_image_path if task.task_status == "已完成" else None,
            "fail_reason": task.fail_reason if task.task_status == "失败" else None,
        },
    }


@router.get("/queue")
async def get_queue(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    status: str = Query("", max_length=20),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=50),
):
    result = await get_user_tasks(db, user.id, status=status, page=page, page_size=page_size)
    return {"code": 0, "data": result}


@router.post("/cancel/{task_id}")
async def cancel_generate_task(
    task_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    from app.services.aipic.credits_service import refund_credits

    result = await db.execute(
        select(AipicGenerateQueue).where(
            AipicGenerateQueue.task_id == task_id,
            AipicGenerateQueue.user_id == user.id,
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise BadRequestException(code=43006, message="任务不存在")

    success, msg = await cancel_task(db, task_id, user.id)
    if not success:
        raise BadRequestException(code=43007, message=msg)

    if task.credits_cost > 0:
        await refund_credits(db, user.id, task.credits_cost, f"取消任务退还：{task.prompt[:20]}")

    await db.commit()
    return {"code": 0, "data": {"message": "取消成功"}}


@router.get("/models")
async def get_models():
    return {
        "code": 0,
        "data": {
            "models": [
                {"name": "gpt-image-2", "label": "GPT Image 2", "default": True},
            ],
            "quality_tiers": {k: {"label": k.upper(), "credits_cost": v["credits_cost"]} for k, v in QUALITY_TIERS.items()},
            "ratios": {k: {"label": v["label"]} for k, v in PRESET_RATIOS.items()},
        },
    }


@router.get("/styles")
async def get_styles(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    category: str = Query("", max_length=50),
):
    styles = await get_style_list(db, category=category)
    return {"code": 0, "data": {"items": styles}}


@router.get("/pricing")
async def get_pricing():
    return {
        "code": 0,
        "data": {
            "quality_tiers": {
                "standard": {"credits_cost": 1, "description": "标准画质"},
                "hd": {"credits_cost": 2, "description": "高清画质", "required_plan": "pro"},
                "ultra": {"credits_cost": 4, "description": "超清画质", "required_plan": "premium"},
            },
            "plan_daily_limits": {
                "free": 3,
                "pro": 50,
                "premium": 200,
                "enterprise": -1,
            },
        },
    }
