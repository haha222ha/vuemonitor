import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import decode_access_token
from app.models.user import User
from app.services.token_blacklist import is_token_blacklisted

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException(message="Token无效")
    except Exception:
        raise UnauthorizedException(message="Token无效或已过期")

    token_jti = payload.get("jti")
    if token_jti and await is_token_blacklisted(token_jti):
        raise UnauthorizedException(message="Token已失效，请重新登录")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedException(message="用户不存在")
    if not user.is_active:
        raise UnauthorizedException(message="账户已禁用")

    now = datetime.now(UTC)
    if user.plan != "free" and user.plan_expires_at and user.plan_expires_at < now:
        user.plan = "free"
        user.plan_expires_at = None
        await db.flush()

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: str):
    async def _check(user: CurrentUser) -> User:
        if user.role not in roles:
            raise ForbiddenException(message="权限不足")
        return user

    return _check


AdminUser = Annotated[User, Depends(require_role("super_admin", "admin"))]
