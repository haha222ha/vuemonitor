import logging
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BadRequestException
from app.middleware.auth import AdminUser
from app.models.aipic import (
    AipicAuthCode,
    AipicConfig,
    AipicGenerateQueue,
    AipicUserCredits,
)
from app.services.aipic.queue_service import get_queue_stats
from app.services.aipic.style_service import add_style, delete_style, get_style_list
from app.services.aipic.worker_service import get_worker_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/aipic/admin", tags=["aipic-admin"])


@router.get("/stats")
async def get_stats(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    total_users = await db.execute(select(func.count()).select_from(AipicUserCredits))
    total_generated = await db.execute(
        select(func.count()).where(AipicGenerateQueue.task_status == "已完成")
    )
    today_generated = await db.execute(
        select(func.count()).where(
            AipicGenerateQueue.task_status == "已完成",
            func.date(AipicGenerateQueue.finish_time) == date.today(),
        )
    )
    queue_stats = await get_queue_stats(db)
    worker_status = get_worker_status()

    return {
        "code": 0,
        "data": {
            "total_users": total_users.scalar() or 0,
            "total_generated": total_generated.scalar() or 0,
            "today_generated": today_generated.scalar() or 0,
            "queue": queue_stats,
            "workers": worker_status,
        },
    }


@router.get("/config")
async def get_config(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AipicConfig))
    config = result.scalar_one_or_none()
    if not config:
        return {"code": 0, "data": {"default_model": "gpt-image-2", "daily_generate_limit": 500, "content_filter_enabled": True}}
    return {
        "code": 0,
        "data": {
            "default_model": config.default_model,
            "daily_generate_limit": config.daily_generate_limit,
            "content_filter_enabled": config.content_filter_enabled,
            "max_queue_size": config.max_queue_size,
            "worker_count": config.worker_count,
        },
    }


class UpdateConfigRequest(BaseModel):
    default_model: str | None = None
    daily_generate_limit: int | None = None
    content_filter_enabled: bool | None = None
    max_queue_size: int | None = None
    worker_count: int | None = None


@router.post("/config")
async def update_config(
    req: UpdateConfigRequest,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AipicConfig))
    config = result.scalar_one_or_none()
    if not config:
        config = AipicConfig(id=uuid.uuid4())
        db.add(config)

    if req.default_model is not None:
        config.default_model = req.default_model
    if req.daily_generate_limit is not None:
        config.daily_generate_limit = req.daily_generate_limit
    if req.content_filter_enabled is not None:
        config.content_filter_enabled = req.content_filter_enabled
    if req.max_queue_size is not None:
        config.max_queue_size = req.max_queue_size
    if req.worker_count is not None:
        config.worker_count = req.worker_count

    await db.flush()
    await db.commit()
    return {"code": 0, "data": {"message": "配置更新成功"}}


class GenerateAuthCodesRequest(BaseModel):
    count: int = Field(1, ge=1, le=100)
    package_type: str = Field("基础版", max_length=20)
    valid_days: int = Field(30, ge=1, le=3650)
    credits: int = Field(0, ge=0)
    batch_name: str = Field("", max_length=100)


@router.post("/codes/generate")
async def generate_auth_codes(
    req: GenerateAuthCodesRequest,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    import secrets

    batch_no = f"batch_{secrets.token_hex(4)}"
    codes = []

    for _ in range(req.count):
        auth_code = secrets.token_hex(8)
        code = AipicAuthCode(
            auth_code=auth_code,
            package_type=req.package_type,
            valid_days=req.valid_days,
            credits=req.credits,
            batch_no=batch_no,
            batch_name=req.batch_name,
        )
        db.add(code)
        codes.append(auth_code)

    await db.flush()
    await db.commit()

    return {"code": 0, "data": {"batch_no": batch_no, "codes": codes, "count": len(codes)}}


@router.get("/codes")
async def get_auth_codes(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
    status: str = Query("", max_length=20),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=100),
):
    query = select(AipicAuthCode)
    count_query = select(func.count()).select_from(AipicAuthCode)

    if status:
        query = query.where(AipicAuthCode.status == status)
        count_query = count_query.where(AipicAuthCode.status == status)

    total = (await db.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(AipicAuthCode.created_at.desc()).offset(offset).limit(page_size)
    )
    codes = result.scalars().all()

    return {
        "code": 0,
        "data": {
            "total": total,
            "items": [
                {
                    "id": str(c.id),
                    "auth_code": c.auth_code,
                    "package_type": c.package_type,
                    "valid_days": c.valid_days,
                    "credits": c.credits,
                    "status": c.status,
                    "activate_user_id": str(c.activate_user_id) if c.activate_user_id else None,
                    "batch_no": c.batch_no,
                    "batch_name": c.batch_name,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in codes
            ],
        },
    }


@router.get("/styles")
async def admin_get_styles(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
    category: str = Query("", max_length=50),
):
    styles = await get_style_list(db, category=category)
    return {"code": 0, "data": {"items": styles}}


class AddStyleRequest(BaseModel):
    style_name: str = Field(..., min_length=1, max_length=100)
    style_prompt: str = Field(..., min_length=1)
    negative_prompt: str = Field("", max_length=1000)
    category: str = Field("通用", max_length=50)


@router.post("/styles")
async def admin_add_style(
    req: AddStyleRequest,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    success, msg = await add_style(
        db, req.style_name, req.style_prompt, req.negative_prompt, req.category
    )
    if not success:
        raise BadRequestException(code=43020, message=msg)
    await db.commit()
    return {"code": 0, "data": {"message": msg}}


@router.delete("/styles/{style_name}")
async def admin_delete_style(
    style_name: str,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    success, msg = await delete_style(db, style_name)
    if not success:
        raise BadRequestException(code=43021, message=msg)
    await db.commit()
    return {"code": 0, "data": {"message": msg}}


@router.get("/queue")
async def admin_get_queue(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    stats = await get_queue_stats(db)
    worker_status = get_worker_status()
    return {"code": 0, "data": {"queue": stats, "workers": worker_status}}


@router.get("/workers")
async def admin_get_workers(
    admin: AdminUser,
):
    return {"code": 0, "data": get_worker_status()}


@router.get("/credits/overview")
async def admin_credits_overview(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    total_users = (await db.execute(select(func.count()).select_from(AipicUserCredits))).scalar() or 0
    total_credits = (await db.execute(select(func.sum(AipicUserCredits.credits)))).scalar() or 0
    total_purchased = (await db.execute(select(func.sum(AipicUserCredits.total_purchased)))).scalar() or 0
    total_used = (await db.execute(select(func.sum(AipicUserCredits.total_used)))).scalar() or 0

    return {
        "code": 0,
        "data": {
            "total_users": total_users,
            "total_credits": total_credits,
            "total_purchased": total_purchased,
            "total_used": total_used,
        },
    }
