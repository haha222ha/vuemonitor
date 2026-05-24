import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import rate_limit_sliding_window
from app.core.database import get_db
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException, UnauthorizedException
from app.core.redis import get_redis
from app.core.security import decode_access_token
from app.middleware.auth import CurrentUser
from app.models.license import LicenseActivation, LicenseCode
from app.schemas.auth import LoginRequest, RefreshTokenRequest, RegisterRequest, TokenResponse, UserInfoResponse
from app.services.auth_service import AuthService
from app.services.operation_audit import record_operation
from app.services.token_blacklist import blacklist_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

_LOGIN_MAX_ATTEMPTS = 5
_LOGIN_LOCKOUT_SECONDS = 900


@router.post("/register", response_model=UserInfoResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    try:
        svc = AuthService(db)
        result = await svc.register(req)
        user_id = result.data.id if hasattr(result, "data") and result.data else None
        await record_operation(
            user_id=str(user_id) if user_id else "unknown",
            action="auth:register",
            resource_type="user",
            resource_id=user_id,
            ip_address="unknown",
        )
        return result
    except (BadRequestException, UnauthorizedException, ForbiddenException):
        raise
    except Exception as e:
        logger.error(f"Register error: {e}", exc_info=True)
        raise BadRequestException(message=f"注册失败: {str(e)[:100]}")


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    login_rate_key = f"login_attempts:{client_ip}"
    allowed, remaining = await rate_limit_sliding_window(
        login_rate_key, _LOGIN_MAX_ATTEMPTS, _LOGIN_LOCKOUT_SECONDS
    )
    if not allowed:
        raise ForbiddenException(message=f"登录尝试过多，请{_LOGIN_LOCKOUT_SECONDS}秒后重试")

    try:
        svc = AuthService(db)
        result = await svc.login(req)
        redis = await get_redis()
        await redis.delete(f"ratelimit:{login_rate_key}")
        user_id = result.data.user_id if hasattr(result, "data") and result.data else None
        await record_operation(
            user_id=str(user_id) if user_id else "unknown",
            action="auth:login",
            resource_type="session",
            ip_address=client_ip,
        )
        return result
    except (UnauthorizedException, ForbiddenException):
        raise
    except Exception as e:
        logger.error(f"Login error for account={req.account}: {e}", exc_info=True)
        raise UnauthorizedException(message=f"登录失败: {str(e)[:100]}")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    svc = AuthService(db)
    return await svc.refresh_access_token(req.refresh_token)


@router.post("/logout")
async def logout(user: CurrentUser, request: Request):
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            payload = decode_access_token(auth_header[7:])
            token_jti = payload.get("jti")
            token_exp = datetime.fromtimestamp(payload.get("exp", 0), tz=UTC)
            if token_jti:
                await blacklist_token(token_jti, token_exp)
        except Exception:
            logging.getLogger("auth").debug("Logout token cleanup failed, ignoring")

    await record_operation(
        user_id=str(user.id),
        action="auth:logout",
        resource_type="session",
        ip_address=request.client.host if request.client else "unknown",
    )

    return {"code": 0, "message": "已成功登出"}


@router.get("/me", response_model=UserInfoResponse)
async def get_me(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    svc = AuthService(db)
    return await svc.get_user_info(user.id)


class LicenseActivateRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)


@router.post("/license/activate")
async def activate_license(
    req: LicenseActivateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    clean_code = req.code.strip().upper()
    result = await db.execute(
        select(LicenseCode).where(LicenseCode.code == clean_code)
    )
    license_obj = result.scalar_one_or_none()

    if not license_obj:
        raise NotFoundException(message="授权码不存在")

    if license_obj.status == "revoked":
        raise BadRequestException(message="授权码已被吊销")

    now = datetime.now(UTC)

    if license_obj.expires_at and license_obj.expires_at < now:
        raise BadRequestException(message="授权码已过期")

    existing = await db.execute(
        select(LicenseActivation).where(
            LicenseActivation.license_id == license_obj.id,
            LicenseActivation.user_id == user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise BadRequestException(message="您已激活过此授权码")

    if license_obj.current_activations >= license_obj.max_activations:
        raise BadRequestException(message="授权码激活次数已达上限")

    activation = LicenseActivation(
        license_id=license_obj.id,
        user_id=user.id,
        activated_at=now,
    )
    db.add(activation)

    license_obj.current_activations += 1
    if license_obj.status == "unused":
        license_obj.status = "active"
        license_obj.activated_at = now
        if not license_obj.expires_at:
            license_obj.expires_at = now + timedelta(days=license_obj.duration_days)

    plan_order = {"free": 0, "pro": 1, "premium": 2, "enterprise": 3}
    current_plan_level = plan_order.get(user.plan, 0)
    new_plan_level = plan_order.get(license_obj.plan, 0)

    if new_plan_level > current_plan_level:
        user.plan = license_obj.plan
        user.plan_expires_at = license_obj.expires_at
    elif new_plan_level == current_plan_level and user.plan_expires_at:
        if user.plan_expires_at > now:
            user.plan_expires_at = user.plan_expires_at + timedelta(days=license_obj.duration_days)
        else:
            user.plan_expires_at = license_obj.expires_at

    await db.flush()

    await record_operation(
        user_id=str(user.id),
        action="settings:license_update",
        resource_type="license",
        resource_id=str(license_obj.id),
        detail=f"code={clean_code[:4]}***, plan={license_obj.plan}",
        ip_address="unknown",
    )

    return {
        "code": 0,
        "data": {
            "plan": user.plan,
            "plan_expires_at": user.plan_expires_at.isoformat() if user.plan_expires_at else None,
            "duration_days": license_obj.duration_days,
        },
    }


@router.get("/license/status")
async def license_status(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    activations = await db.execute(
        select(LicenseActivation)
        .where(LicenseActivation.user_id == user.id)
        .order_by(LicenseActivation.activated_at.desc())
    )
    items = activations.scalars().all()

    license_ids = [a.license_id for a in items]
    licenses = []
    if license_ids:
        lic_result = await db.execute(
            select(LicenseCode).where(LicenseCode.id.in_(license_ids))
        )
        lic_map = {l.id: l for l in lic_result.scalars().all()}
        for a in items:
            lic = lic_map.get(a.license_id)
            if lic:
                licenses.append({
                    "code": lic.code,
                    "plan": lic.plan,
                    "status": lic.status,
                    "expires_at": lic.expires_at.isoformat() if lic.expires_at else None,
                    "activated_at": a.activated_at.isoformat() if a.activated_at else None,
                })

    return {
        "code": 0,
        "data": {
            "current_plan": user.plan,
            "plan_expires_at": user.plan_expires_at.isoformat() if user.plan_expires_at else None,
            "licenses": licenses,
        },
    }
