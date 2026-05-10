import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import BadRequestException, NotFoundException, UnauthorizedException
from app.middleware.auth import CurrentUser
from app.models.license import LicenseCode, LicenseActivation
from app.models.user import User
from shared.constants.feature_gates import PLAN_FEATURES_MAP

router = APIRouter(prefix="/license", tags=["license"])


class LicenseVerifyRequest(BaseModel):
    license_key: str = Field(..., min_length=1, max_length=64)
    device_id: str = Field(..., min_length=1, max_length=64)
    machine_fingerprint: str = Field(..., min_length=1, max_length=255)
    app_version: str = Field("1.0.0", max_length=20)


class LicenseHeartbeatRequest(BaseModel):
    license_key: str = Field(..., min_length=1, max_length=64)
    device_id: str = Field(..., min_length=1, max_length=64)
    machine_fingerprint: str = Field(..., min_length=1, max_length=255)


@router.post("/verify")
async def verify_license(
    req: LicenseVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LicenseCode).where(LicenseCode.code == req.license_key.strip())
    )
    license_obj = result.scalar_one_or_none()

    if not license_obj:
        return {"valid": False, "message": "授权码不存在"}

    if license_obj.status == "revoked":
        return {"valid": False, "message": "授权码已被吊销"}

    now = datetime.now(timezone.utc)

    if license_obj.expires_at and license_obj.expires_at < now:
        license_obj.status = "expired"
        await db.flush()
        return {"valid": False, "message": "授权码已过期"}

    if license_obj.status not in ("active", "unused"):
        return {"valid": False, "message": f"授权码状态异常: {license_obj.status}"}

    activation_result = await db.execute(
        select(LicenseActivation).where(
            LicenseActivation.license_id == license_obj.id,
            LicenseActivation.device_fingerprint == req.machine_fingerprint,
        )
    )
    existing_activation = activation_result.scalar_one_or_none()

    if existing_activation:
        return {
            "valid": True,
            "plan": license_obj.plan,
            "expires_at": license_obj.expires_at.isoformat() if license_obj.expires_at else None,
            "features": PLAN_FEATURES_MAP.get(license_obj.plan, []),
            "activated_at": existing_activation.activated_at.isoformat() if existing_activation.activated_at else None,
        }

    if license_obj.current_activations >= license_obj.max_activations:
        return {"valid": False, "message": f"授权码激活设备数已达上限({license_obj.max_activations}台)"}

    user_result = await db.execute(
        select(LicenseActivation).where(
            LicenseActivation.license_id == license_obj.id,
        )
    )
    first_activation = user_result.scalars().first()

    user_id = first_activation.user_id if first_activation else None

    activation = LicenseActivation(
        license_id=license_obj.id,
        user_id=user_id or uuid.uuid4(),
        device_fingerprint=req.machine_fingerprint,
        activated_at=now,
    )
    db.add(activation)

    license_obj.current_activations += 1
    if license_obj.status == "unused":
        license_obj.status = "active"
        license_obj.activated_at = now

    await db.flush()

    return {
        "valid": True,
        "plan": license_obj.plan,
        "expires_at": license_obj.expires_at.isoformat() if license_obj.expires_at else None,
        "features": PLAN_FEATURES_MAP.get(license_obj.plan, []),
        "activated_at": now.isoformat(),
    }


@router.post("/heartbeat")
async def license_heartbeat(
    req: LicenseHeartbeatRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(LicenseCode).where(LicenseCode.code == req.license_key.strip())
    )
    license_obj = result.scalar_one_or_none()

    if not license_obj:
        return {"valid": False, "message": "授权码不存在"}

    if license_obj.status == "revoked":
        return {"valid": False, "message": "授权码已被吊销"}

    now = datetime.now(timezone.utc)
    if license_obj.expires_at and license_obj.expires_at < now:
        return {"valid": False, "message": "授权码已过期"}

    activation_result = await db.execute(
        select(LicenseActivation).where(
            LicenseActivation.license_id == license_obj.id,
            LicenseActivation.device_fingerprint == req.machine_fingerprint,
        )
    )
    activation = activation_result.scalar_one_or_none()

    if not activation:
        return {"valid": False, "message": "设备未激活"}

    return {
        "valid": True,
        "plan": license_obj.plan,
        "expires_at": license_obj.expires_at.isoformat() if license_obj.expires_at else None,
        "features": PLAN_FEATURES_MAP.get(license_obj.plan, []),
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
                })

    return {
        "code": 0,
        "data": {
            "current_plan": user.plan,
            "plan_expires_at": user.plan_expires_at.isoformat() if user.plan_expires_at else None,
            "features": PLAN_FEATURES_MAP.get(user.plan, []),
            "licenses": licenses,
        },
    }


@router.post("/deactivate")
async def deactivate_device(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    machine_fingerprint: str = Body(..., min_length=1, max_length=255),
):
    activation_result = await db.execute(
        select(LicenseActivation).where(
            LicenseActivation.user_id == user.id,
            LicenseActivation.device_fingerprint == machine_fingerprint,
        )
    )
    activation = activation_result.scalar_one_or_none()

    if not activation:
        raise NotFoundException(message="未找到该设备的激活记录")

    license_result = await db.execute(
        select(LicenseCode).where(LicenseCode.id == activation.license_id)
    )
    license_obj = license_result.scalar_one_or_none()

    await db.delete(activation)

    if license_obj and license_obj.current_activations > 0:
        license_obj.current_activations -= 1
        if license_obj.current_activations == 0:
            license_obj.status = "unused"

    await db.flush()

    return {"code": 0, "message": "设备已解绑"}
