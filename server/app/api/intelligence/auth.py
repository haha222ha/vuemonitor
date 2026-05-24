import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import create_access_token, create_refresh_token, hash_password
from app.middleware.auth import CurrentUser
from app.models.intelligence import IntelAuthCode, IntelMembership
from app.models.user import RefreshToken, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["intel-auth"])

_INTEL_SESSION_PREFIX = "intel_session:"
_INTEL_SESSION_TTL = 86400 * 365


async def _create_intel_session(user_id: uuid.UUID) -> str:
    session_id = secrets.token_hex(16)
    redis = await get_redis()
    key = f"{_INTEL_SESSION_PREFIX}{user_id}"
    await redis.set(key, session_id, ex=_INTEL_SESSION_TTL)
    return session_id


async def get_intel_session_id(user_id: uuid.UUID) -> str | None:
    try:
        redis = await get_redis()
        key = f"{_INTEL_SESSION_PREFIX}{user_id}"
        val = await redis.get(key)
        return val.decode() if val else None
    except Exception:
        return None


class CodeLoginRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)


class CodeLoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    membership: "IntelMembershipResponse"


class ActivateCodeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)


class IntelMembershipResponse(BaseModel):
    plan: str
    started_at: str
    expires_at: str
    status: str
    days_remaining: int


@router.post("/code-login", response_model=CodeLoginResponse)
async def code_login(
    req: CodeLoginRequest,
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

    existing_membership_result = await db.execute(
        select(IntelMembership).where(
            IntelMembership.auth_code_id == auth_code.id,
            IntelMembership.status == "active",
        ).order_by(IntelMembership.expires_at.desc())
    )
    existing_membership = existing_membership_result.scalars().first()

    if existing_membership:
        user_result = await db.execute(
            select(User).where(User.id == existing_membership.user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=500, detail="关联用户不存在")

        days_remaining = (existing_membership.expires_at - now).days
        if days_remaining <= 0:
            existing_membership.status = "expired"
            raise HTTPException(status_code=400, detail="授权码已过期，请使用新的授权码")

        session_id = await _create_intel_session(user.id)

        old_rts = await db.execute(
            select(RefreshToken).where(RefreshToken.user_id == user.id)
        )
        for old_rt in old_rts.scalars().all():
            await db.delete(old_rt)

        access_token = create_access_token(
            subject=str(user.id),
            extra={"plan": user.plan, "role": user.role, "sid": session_id},
        )
        refresh_token = create_refresh_token(subject=str(user.id))

        token_hash = sha256(refresh_token.encode()).hexdigest()
        rt = RefreshToken(user_id=user.id, token_hash=token_hash, expires_at=now + timedelta(days=7))
        db.add(rt)

        user.last_login_at = now

        membership_resp = IntelMembershipResponse(
            plan=existing_membership.plan,
            started_at=existing_membership.started_at.isoformat(),
            expires_at=existing_membership.expires_at.isoformat(),
            status=existing_membership.status,
            days_remaining=days_remaining,
        )
    else:
        nickname = f"intel_{secrets.token_hex(4)}"
        random_password = secrets.token_hex(16)
        user = User(
            nickname=nickname,
            email=None,
            password_hash=hash_password(random_password),
            plan=auth_code.plan,
            role="user",
            is_active=True,
        )
        db.add(user)
        await db.flush()

        if auth_code.status == "unused":
            auth_code.status = "active"
            auth_code.activated_at = now
            auth_code.expires_at = now + timedelta(days=auth_code.duration_days)

        auth_code.current_activations += 1

        expires_at = auth_code.expires_at or (now + timedelta(days=auth_code.duration_days))
        membership = IntelMembership(
            user_id=user.id,
            auth_code_id=auth_code.id,
            plan=auth_code.plan,
            started_at=now,
            expires_at=expires_at,
            status="active",
        )
        db.add(membership)

        user.plan = auth_code.plan
        user.plan_expires_at = expires_at
        user.last_login_at = now

        await db.flush()

        days_remaining = (expires_at - now).days

        session_id = await _create_intel_session(user.id)

        access_token = create_access_token(
            subject=str(user.id),
            extra={"plan": user.plan, "role": user.role, "sid": session_id},
        )
        refresh_token = create_refresh_token(subject=str(user.id))

        token_hash = sha256(refresh_token.encode()).hexdigest()
        rt = RefreshToken(user_id=user.id, token_hash=token_hash, expires_at=now + timedelta(days=7))
        db.add(rt)

        membership_resp = IntelMembershipResponse(
            plan=membership.plan,
            started_at=membership.started_at.isoformat(),
            expires_at=membership.expires_at.isoformat(),
            status=membership.status,
            days_remaining=days_remaining,
        )

    await db.flush()

    return CodeLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=1800,
        membership=membership_resp,
    )


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