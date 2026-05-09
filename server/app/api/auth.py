import time

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenException
from app.middleware.auth import CurrentUser
from app.schemas.auth import LoginRequest, RefreshTokenRequest, RegisterRequest, TokenResponse, UserInfoResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

_login_attempts: dict[str, list[float]] = {}
_MAX_ATTEMPTS = 10
_LOCKOUT_SECONDS = 300


@router.post("/register", response_model=UserInfoResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    svc = AuthService(db)
    return await svc.register(req)


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    attempts = _login_attempts.get(client_ip, [])
    attempts = [t for t in attempts if now - t < _LOCKOUT_SECONDS]
    if len(attempts) >= _MAX_ATTEMPTS:
        raise ForbiddenException(message=f"登录尝试过多，请{_LOCKOUT_SECONDS}秒后重试")
    _login_attempts[client_ip] = attempts

    svc = AuthService(db)
    result = await svc.login(req)
    _login_attempts.pop(client_ip, None)
    return result


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    svc = AuthService(db)
    return await svc.refresh_access_token(req.refresh_token)


@router.get("/me", response_model=UserInfoResponse)
async def get_me(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    svc = AuthService(db)
    return await svc.get_user_info(user.id)
