import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException, UnauthorizedException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.models.user import RefreshToken, User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserInfoResponse


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, req: RegisterRequest) -> UserInfoResponse:
        if req.email:
            result = await self.db.execute(select(User).where(User.email == req.email))
            if result.scalar_one_or_none():
                raise BadRequestException(message="邮箱已注册")

        result = await self.db.execute(select(User).where(User.nickname == req.nickname))
        if result.scalar_one_or_none():
            raise BadRequestException(message="昵称已被使用")

        user = User(
            email=req.email,
            nickname=req.nickname,
            password_hash=hash_password(req.password),
            plan="free",
            role="user",
            is_active=True,
        )
        self.db.add(user)
        await self.db.flush()

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

    async def login(self, req: LoginRequest) -> TokenResponse:
        account = req.account.strip()
        result = await self.db.execute(
            select(User).where(
                or_(User.email == account, User.nickname == account)
            )
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(req.password, user.password_hash):
            raise UnauthorizedException(message="账号或密码错误")

        if not user.is_active:
            raise UnauthorizedException(message="账户已禁用")

        user.last_login_at = datetime.now(timezone.utc)

        access_token = create_access_token(subject=str(user.id), extra={"plan": user.plan, "role": user.role})
        refresh_token = create_refresh_token(subject=str(user.id))

        from hashlib import sha256

        token_hash = sha256(refresh_token.encode()).hexdigest()
        rt = RefreshToken(user_id=user.id, token_hash=token_hash, expires_at=datetime.now(timezone.utc) + timedelta(days=7))
        self.db.add(rt)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=1800,
        )

    async def refresh_access_token(self, refresh_token_str: str) -> TokenResponse:
        try:
            payload = decode_refresh_token(refresh_token_str)
        except Exception:
            raise UnauthorizedException(message="Refresh Token无效")

        from hashlib import sha256

        token_hash = sha256(refresh_token_str.encode()).hexdigest()
        result = await self.db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        rt = result.scalar_one_or_none()

        if not rt:
            raise UnauthorizedException(message="Refresh Token不存在")

        user_id = payload.get("sub")
        result = await self.db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise UnauthorizedException(message="用户不存在或已禁用")

        new_access = create_access_token(subject=str(user.id), extra={"plan": user.plan, "role": user.role})
        new_refresh = create_refresh_token(subject=str(user.id))

        await self.db.delete(rt)

        new_hash = sha256(new_refresh.encode()).hexdigest()
        new_rt = RefreshToken(user_id=user.id, token_hash=new_hash, expires_at=datetime.now(timezone.utc) + timedelta(days=7))
        self.db.add(new_rt)

        return TokenResponse(access_token=new_access, refresh_token=new_refresh, expires_in=1800)

    async def get_user_info(self, user_id: uuid.UUID) -> UserInfoResponse:
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundException(message="用户不存在")

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
