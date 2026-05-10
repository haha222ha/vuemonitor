import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_get, cache_set, cache_delete
from app.core.database import get_db
from app.core.exceptions import BadRequestException, NotFoundException, UnauthorizedException
from app.core.security import hash_password, verify_password, create_access_token
from app.middleware.auth import CurrentUser
from app.models.user import User
from app.schemas.auth import UserInfoResponse

router = APIRouter(prefix="/user", tags=["user"])


class UpdateProfileRequest(BaseModel):
    nickname: str | None = Field(None, min_length=2, max_length=50)
    avatar_url: str | None = Field(None, max_length=500)


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)


class ResetPasswordRequestRequest(BaseModel):
    email: EmailStr


class ResetPasswordConfirmRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=8, max_length=128)


class VerifyEmailRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


class ResendVerifyEmailRequest(BaseModel):
    pass


_VERIFICATION_TTL = 600
_RESET_TTL = 300


@router.get("/profile", response_model=UserInfoResponse)
async def get_profile(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    return UserInfoResponse(
        id=str(user.id),
        email=user.email,
        nickname=user.nickname,
        avatar_url=user.avatar_url,
        plan=user.plan,
        plan_expires_at=user.plan_expires_at,
        role=user.role,
        is_active=user.is_active,
    )


@router.put("/profile", response_model=UserInfoResponse)
async def update_profile(
    req: UpdateProfileRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    if req.nickname is not None:
        user.nickname = req.nickname
    if req.avatar_url is not None:
        user.avatar_url = req.avatar_url

    await db.flush()

    return UserInfoResponse(
        id=str(user.id),
        email=user.email,
        nickname=user.nickname,
        avatar_url=user.avatar_url,
        plan=user.plan,
        plan_expires_at=user.plan_expires_at,
        role=user.role,
        is_active=user.is_active,
    )


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(req.old_password, user.password_hash):
        raise UnauthorizedException(message="原密码错误")

    user.password_hash = hash_password(req.new_password)
    await db.flush()

    return {"code": 0, "message": "密码修改成功"}


@router.post("/reset-password/request")
async def request_reset_password(
    req: ResetPasswordRequestRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if not user:
        return {"code": 0, "message": "如果该邮箱已注册，您将收到重置验证码"}

    code = f"{secrets.randbelow(1000000):06d}"
    cache_key = f"pwd_reset:{req.email}"
    await cache_set(cache_key, {"code": code, "user_id": str(user.id)}, _RESET_TTL)

    _send_email_mock(req.email, "password_reset", code)

    return {"code": 0, "message": "如果该邮箱已注册，您将收到重置验证码"}


@router.post("/reset-password/confirm")
async def confirm_reset_password(
    req: ResetPasswordConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"pwd_reset:{req.email}"
    cached = await cache_get(cache_key)

    if not cached or cached.get("code") != req.code:
        raise BadRequestException(message="验证码无效或已过期")

    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if not user:
        raise NotFoundException(message="用户不存在")

    user.password_hash = hash_password(req.new_password)
    await db.flush()

    await cache_delete(cache_key)

    return {"code": 0, "message": "密码重置成功"}


@router.post("/verify-email/request")
async def request_verify_email(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    code = f"{secrets.randbelow(1000000):06d}"
    cache_key = f"email_verify:{user.id}"
    await cache_set(cache_key, {"code": code, "email": user.email}, _VERIFICATION_TTL)

    _send_email_mock(user.email, "email_verify", code)

    return {"code": 0, "message": "验证码已发送"}


@router.post("/verify-email/confirm")
async def confirm_verify_email(
    req: VerifyEmailRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"email_verify:{user.id}"
    cached = await cache_get(cache_key)

    if not cached or cached.get("code") != req.code:
        raise BadRequestException(message="验证码无效或已过期")

    await cache_delete(cache_key)

    return {"code": 0, "message": "邮箱验证成功"}


@router.delete("/account")
async def delete_account(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    user.is_active = False
    await db.flush()

    return {"code": 0, "message": "账户已停用，数据将在30天后删除"}


def _send_email_mock(email: str, email_type: str, code: str):
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[EMAIL MOCK] type={email_type}, to={email}, code={code}")
