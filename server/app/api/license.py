import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BadRequestException, NotFoundException
from app.middleware.auth import CurrentUser, AdminUser
from app.models.license import LicenseCode, LicenseActivation
from app.models.user import User
from app.services.license_service import LicenseService
from shared.constants.feature_gates import PLAN_FEATURES_MAP, PLAN_LIMITS

router = APIRouter(prefix="/license", tags=["license"])


class LicenseVerifyRequest(BaseModel):
    license_key: str = Field(..., min_length=1, max_length=64)
    device_id: str = Field(..., min_length=1, max_length=64)
    machine_fingerprint: str = Field(..., min_length=1, max_length=255)
    app_version: str = Field("1.0.0", max_length=20)


class LicenseActivateRequest(BaseModel):
    license_key: str = Field(..., min_length=1, max_length=64)
    device_name: str | None = Field(None, max_length=128)


class LicenseHeartbeatRequest(BaseModel):
    license_key: str = Field(..., min_length=1, max_length=64)
    device_id: str = Field(..., min_length=1, max_length=64)
    machine_fingerprint: str = Field(..., min_length=1, max_length=255)


class LicenseRenewRequest(BaseModel):
    extra_days: int = Field(..., ge=1, le=3650)


class LicenseUpgradeRequest(BaseModel):
    new_plan: str = Field(..., pattern="^(pro|premium|enterprise)$")


@router.post("/verify")
async def verify_license(
    req: LicenseVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    svc = LicenseService(db)
    ip_address = request.client.host if request.client else None
    result = await svc.verify(req.license_key, req.machine_fingerprint, ip_address)
    return result


@router.post("/activate")
async def activate_license(
    req: LicenseActivateRequest,
    user: CurrentUser,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    svc = LicenseService(db)
    from app.main import licenseManager

    fingerprint = licenseManager.getMachineFingerprint() if licenseManager else req.license_key
    ip_address = request.client.host if request.client else None

    result = await svc.activate(
        code=req.license_key,
        user_id=user.id,
        device_fingerprint=fingerprint,
        device_name=req.device_name,
        ip_address=ip_address,
    )
    return {"code": 0, "data": result}


@router.post("/heartbeat")
async def license_heartbeat(
    req: LicenseHeartbeatRequest,
    db: AsyncSession = Depends(get_db),
):
    svc = LicenseService(db)
    result = await svc.verify(req.license_key, req.machine_fingerprint)
    if not result.get("valid"):
        return result

    lic_result = await db.execute(
        select(LicenseCode).where(LicenseCode.code == req.license_key.strip().upper())
    )
    lic = lic_result.scalar_one_or_none()
    if not lic:
        return {"valid": False, "message": "授权码不存在"}

    activation_result = await db.execute(
        select(LicenseActivation).where(
            LicenseActivation.license_id == lic.id,
            LicenseActivation.device_fingerprint == req.machine_fingerprint,
        )
    )
    activation = activation_result.scalar_one_or_none()
    if not activation:
        return {"valid": False, "message": "设备未激活"}

    return {
        "valid": True,
        "plan": lic.plan,
        "expires_at": lic.expires_at.isoformat() if lic.expires_at else None,
        "features": PLAN_FEATURES_MAP.get(lic.plan, []),
        "quotas": PLAN_LIMITS.get(lic.plan, PLAN_LIMITS["free"]),
    }


@router.get("/status")
async def get_license_status(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)

    if user.plan_expires_at and user.plan_expires_at < now and user.plan != "free":
        user.plan = "free"
        user.plan_expires_at = None
        await db.flush()

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
                is_expired = lic.expires_at and lic.expires_at < now
                licenses.append({
                    "code": lic.code[:8] + "****",
                    "plan": lic.plan,
                    "status": "expired" if is_expired else lic.status,
                    "expires_at": lic.expires_at.isoformat() if lic.expires_at else None,
                    "activated_at": a.activated_at.isoformat() if a.activated_at else None,
                    "device_fingerprint": a.device_fingerprint[:8] + "****" if a.device_fingerprint else None,
                    "device_name": a.device_name,
                })

    return {
        "code": 0,
        "data": {
            "current_plan": user.plan,
            "plan_expires_at": user.plan_expires_at.isoformat() if user.plan_expires_at else None,
            "features": PLAN_FEATURES_MAP.get(user.plan, []),
            "quotas": PLAN_LIMITS.get(user.plan, PLAN_LIMITS["free"]),
            "licenses": licenses,
        },
    }


@router.post("/deactivate")
async def deactivate_device(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    machine_fingerprint: str = Body(..., min_length=1, max_length=255),
):
    svc = LicenseService(db)
    return await svc.deactivate_device(user.id, machine_fingerprint)


@router.post("/{license_id}/renew")
async def renew_license(
    license_id: uuid.UUID,
    req: LicenseRenewRequest,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    svc = LicenseService(db)
    return await svc.renew(license_id, req.extra_days, admin.id)


@router.post("/{license_id}/upgrade")
async def upgrade_license(
    license_id: uuid.UUID,
    req: LicenseUpgradeRequest,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    svc = LicenseService(db)
    return await svc.upgrade(license_id, req.new_plan, admin.id)


@router.post("/{license_id}/revoke")
async def revoke_license(
    license_id: uuid.UUID,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
    reason: str = Body(None, max_length=500),
):
    svc = LicenseService(db)
    return await svc.revoke(license_id, admin.id, reason)


@router.get("/{license_id}/logs")
async def get_license_logs(
    license_id: uuid.UUID,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    svc = LicenseService(db)
    logs = await svc.get_change_logs(license_id)
    return {"code": 0, "data": {"items": logs}}


@router.get("/quotas")
async def get_plan_quotas(
    user: CurrentUser,
):
    return {
        "code": 0,
        "data": {
            "current_plan": user.plan,
            "quotas": PLAN_LIMITS.get(user.plan, PLAN_LIMITS["free"]),
            "features": PLAN_FEATURES_MAP.get(user.plan, []),
        },
    }
