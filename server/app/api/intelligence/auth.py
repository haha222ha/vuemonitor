import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import CurrentUser
from app.models.intelligence import IntelAuthCode, IntelMembership
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["intel-auth"])


class ActivateCodeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)


class IntelMembershipResponse(BaseModel):
    plan: str
    started_at: str
    expires_at: str
    status: str
    days_remaining: int


@router.post("/activate", response_model=IntelMembershipResponse)
async def activate_intel_code(
    req: ActivateCodeRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(UTC)
    code = req.code.strip().upper()

    result = await db.execute(
        select(IntelAuthCode).where(IntelAuthCode.code == code)
    )
    auth_code = result.scalar_one_or_none()

    if not auth_code:
        raise HTTPException(status_code=404, detail="授权码不存在")

    if auth_code.status == "revoked":
        raise HTTPException(status_code=400, detail="授权码已被吊销")

    if auth_code.current_activations >= auth_code.max_activations:
        raise HTTPException(status_code=400, detail="授权码已达最大激活次数")

    existing_result = await db.execute(
        select(IntelMembership).where(
            IntelMembership.auth_code_id == auth_code.id,
            IntelMembership.user_id == user.id,
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="你已使用此授权码激活过")

    if auth_code.status == "unused":
        auth_code.status = "active"
        auth_code.activated_at = now
        auth_code.expires_at = now + timedelta(days=auth_code.duration_days)

    auth_code.current_activations += 1

    membership = IntelMembership(
        user_id=user.id,
        auth_code_id=auth_code.id,
        plan=auth_code.plan,
        started_at=now,
        expires_at=auth_code.expires_at or (now + timedelta(days=auth_code.duration_days)),
        status="active",
    )
    db.add(membership)

    await db.flush()

    days_remaining = (membership.expires_at - now).days

    return IntelMembershipResponse(
        plan=membership.plan,
        started_at=membership.started_at.isoformat(),
        expires_at=membership.expires_at.isoformat(),
        status=membership.status,
        days_remaining=days_remaining,
    )


@router.get("/me", response_model=IntelMembershipResponse)
async def get_intel_membership(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(UTC)
    result = await db.execute(
        select(IntelMembership).where(
            IntelMembership.user_id == user.id,
            IntelMembership.status == "active",
        ).order_by(IntelMembership.expires_at.desc())
    )
    membership = result.scalars().first()

    if not membership:
        raise HTTPException(status_code=404, detail="无有效情报系统会员")

    days_remaining = (membership.expires_at - now).days

    return IntelMembershipResponse(
        plan=membership.plan,
        started_at=membership.started_at.isoformat(),
        expires_at=membership.expires_at.isoformat(),
        status=membership.status,
        days_remaining=days_remaining,
    )