import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException, ForbiddenException
from app.models.license import LicenseCode, LicenseActivation, LicenseChangeLog
from app.models.user import User
from shared.constants.feature_gates import PLAN_FEATURES_MAP, PLAN_LIMITS

_PLAN_CODES = {"F": "free", "P": "pro", "M": "premium", "E": "enterprise"}
_PLAN_REVERSE = {v: k for k, v in _PLAN_CODES.items()}
_CHECKSUM_SECRET = "xhs365_license_checksum_v2"


class LicenseService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def generate_code(self, plan: str, duration_days: int) -> str:
        plan_code = _PLAN_REVERSE.get(plan, "F")
        random_part = secrets.token_hex(6).upper()
        duration_code = f"{duration_days:04X}"
        payload = f"{plan_code}{random_part}{duration_code}"
        checksum = hashlib.sha256(f"{payload}{_CHECKSUM_SECRET}".encode()).hexdigest()[:4].upper()
        return f"VM-{plan_code}{random_part[:2]}-{random_part[2:4]}-{random_part[4:6]}-{duration_code[:2]}{checksum[:2]}-{checksum[2:]}{plan_code}"

    def validate_code_format(self, code: str) -> bool:
        clean = code.strip().upper()
        if clean.startswith("VM-"):
            parts = clean.split("-")
            if len(parts) != 6:
                return False
            if len(parts[1]) != 3 or parts[1][0] not in _PLAN_CODES:
                return False
            return True
        return bool(clean and 16 <= len(clean) <= 32 and clean.isalnum())

    async def batch_generate(
        self,
        plan: str,
        duration_days: int,
        count: int,
        max_activations: int = 1,
        note: str | None = None,
        created_by: uuid.UUID | None = None,
    ) -> list[LicenseCode]:
        if plan not in _PLAN_REVERSE:
            raise BadRequestException(message=f"无效的套餐类型: {plan}")
        if count < 1 or count > 500:
            raise BadRequestException(message="批量生成数量需在1-500之间")

        batch_id = secrets.token_hex(8)
        licenses = []
        for _ in range(count):
            code = self.generate_code(plan, duration_days)
            lic = LicenseCode(
                code=code,
                plan=plan,
                duration_days=duration_days,
                max_activations=max_activations,
                status="unused",
                batch_id=batch_id,
                note=note,
                created_by=created_by,
            )
            self.db.add(lic)
            licenses.append(lic)

        await self.db.flush()
        return licenses

    async def verify(self, code: str, device_fingerprint: str, ip_address: str | None = None) -> dict:
        clean_code = code.strip().upper()
        result = await self.db.execute(
            select(LicenseCode).where(LicenseCode.code == clean_code)
        )
        lic = result.scalar_one_or_none()

        if not lic:
            return {"valid": False, "message": "授权码不存在"}

        if lic.status == "revoked":
            return {"valid": False, "message": "授权码已被吊销"}

        now = datetime.now(timezone.utc)

        if lic.expires_at and lic.expires_at < now:
            if lic.status != "expired":
                lic.status = "expired"
                await self.db.flush()
            return {"valid": False, "message": "授权码已过期"}

        if lic.status not in ("active", "unused"):
            return {"valid": False, "message": f"授权码状态异常: {lic.status}"}

        activation_result = await self.db.execute(
            select(LicenseActivation).where(
                LicenseActivation.license_id == lic.id,
                LicenseActivation.device_fingerprint == device_fingerprint,
            )
        )
        existing = activation_result.scalar_one_or_none()

        if existing:
            existing.last_heartbeat = now
            if ip_address:
                existing.ip_address = ip_address
            await self.db.flush()
            return {
                "valid": True,
                "plan": lic.plan,
                "expires_at": lic.expires_at.isoformat() if lic.expires_at else None,
                "features": PLAN_FEATURES_MAP.get(lic.plan, []),
                "quotas": PLAN_LIMITS.get(lic.plan, PLAN_LIMITS["free"]),
                "activated_at": existing.activated_at.isoformat() if existing.activated_at else None,
            }

        if lic.current_activations >= lic.max_activations:
            return {"valid": False, "message": f"授权码激活设备数已达上限({lic.max_activations}台)"}

        return {
            "valid": True,
            "plan": lic.plan,
            "expires_at": lic.expires_at.isoformat() if lic.expires_at else None,
            "features": PLAN_FEATURES_MAP.get(lic.plan, []),
            "quotas": PLAN_LIMITS.get(lic.plan, PLAN_LIMITS["free"]),
            "needs_activation": True,
            "license_id": str(lic.id),
        }

    async def activate(
        self,
        code: str,
        user_id: uuid.UUID,
        device_fingerprint: str,
        device_name: str | None = None,
        ip_address: str | None = None,
    ) -> dict:
        clean_code = code.strip().upper()
        result = await self.db.execute(
            select(LicenseCode).where(LicenseCode.code == clean_code)
        )
        lic = result.scalar_one_or_none()

        if not lic:
            raise BadRequestException(message="授权码不存在")
        if lic.status == "revoked":
            raise BadRequestException(message="授权码已被吊销")

        now = datetime.now(timezone.utc)
        if lic.expires_at and lic.expires_at < now:
            raise BadRequestException(message="授权码已过期")

        activation_result = await self.db.execute(
            select(LicenseActivation).where(
                LicenseActivation.license_id == lic.id,
                LicenseActivation.device_fingerprint == device_fingerprint,
            )
        )
        existing = activation_result.scalar_one_or_none()

        if existing:
            existing.last_heartbeat = now
            if ip_address:
                existing.ip_address = ip_address
            await self.db.flush()
            return {
                "plan": lic.plan,
                "expires_at": lic.expires_at.isoformat() if lic.expires_at else None,
                "features": PLAN_FEATURES_MAP.get(lic.plan, []),
                "already_activated": True,
            }

        if lic.current_activations >= lic.max_activations:
            raise BadRequestException(message=f"授权码激活设备数已达上限({lic.max_activations}台)")

        activation = LicenseActivation(
            license_id=lic.id,
            user_id=user_id,
            device_fingerprint=device_fingerprint,
            device_name=device_name,
            ip_address=ip_address,
            activated_at=now,
            last_heartbeat=now,
        )
        self.db.add(activation)

        lic.current_activations += 1
        if lic.status == "unused":
            lic.status = "active"
            lic.activated_at = now
            if not lic.expires_at:
                lic.expires_at = now + timedelta(days=lic.duration_days)

        user_result = await self.db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user:
            from shared.constants.feature_gates import PLAN_HIERARCHY
            if PLAN_HIERARCHY.get(lic.plan, 0) > PLAN_HIERARCHY.get(user.plan, 0):
                user.plan = lic.plan
                user.plan_expires_at = lic.expires_at

        change_log = LicenseChangeLog(
            license_id=lic.id,
            action="activate",
            new_value=f"device={device_fingerprint[:8]}",
            operator_id=user_id,
            detail=f"设备激活, plan={lic.plan}",
        )
        self.db.add(change_log)

        await self.db.flush()

        return {
            "plan": lic.plan,
            "expires_at": lic.expires_at.isoformat() if lic.expires_at else None,
            "features": PLAN_FEATURES_MAP.get(lic.plan, []),
            "activated_at": now.isoformat(),
        }

    async def revoke(self, license_id: uuid.UUID, revoked_by: uuid.UUID, reason: str | None = None) -> dict:
        result = await self.db.execute(
            select(LicenseCode).where(LicenseCode.id == license_id)
        )
        lic = result.scalar_one_or_none()
        if not lic:
            raise NotFoundException(message="授权码不存在")
        if lic.status == "revoked":
            raise BadRequestException(message="授权码已被吊销")

        old_status = lic.status
        lic.status = "revoked"
        lic.revoked_at = datetime.now(timezone.utc)
        lic.revoked_by = revoked_by
        lic.revoke_reason = reason

        activations_result = await self.db.execute(
            select(LicenseActivation).where(LicenseActivation.license_id == lic.id)
        )
        for activation in activations_result.scalars().all():
            user_result = await self.db.execute(select(User).where(User.id == activation.user_id))
            user = user_result.scalar_one_or_none()
            if user and user.plan == lic.plan:
                user.plan = "free"
                user.plan_expires_at = None

        change_log = LicenseChangeLog(
            license_id=lic.id,
            action="revoke",
            old_value=old_status,
            new_value="revoked",
            operator_id=revoked_by,
            detail=reason or "管理员吊销",
        )
        self.db.add(change_log)

        await self.db.flush()
        return {"code": 0, "message": "授权码已吊销"}

    async def renew(self, license_id: uuid.UUID, extra_days: int, operator_id: uuid.UUID | None = None) -> dict:
        result = await self.db.execute(
            select(LicenseCode).where(LicenseCode.id == license_id)
        )
        lic = result.scalar_one_or_none()
        if not lic:
            raise NotFoundException(message="授权码不存在")
        if lic.status == "revoked":
            raise BadRequestException(message="已吊销的授权码无法续期")

        now = datetime.now(timezone.utc)
        old_expires = lic.expires_at.isoformat() if lic.expires_at else None
        base = lic.expires_at if lic.expires_at and lic.expires_at > now else now
        lic.expires_at = base + timedelta(days=extra_days)
        lic.duration_days += extra_days

        if lic.status == "expired":
            lic.status = "active"

        user_result = await self.db.execute(select(User).where(User.id == operator_id))
        user = user_result.scalar_one_or_none()
        if user and user.plan == lic.plan:
            user.plan_expires_at = lic.expires_at

        change_log = LicenseChangeLog(
            license_id=lic.id,
            action="renew",
            old_value=old_expires,
            new_value=lic.expires_at.isoformat(),
            operator_id=operator_id,
            detail=f"续期{extra_days}天",
        )
        self.db.add(change_log)

        await self.db.flush()
        return {
            "code": 0,
            "data": {
                "expires_at": lic.expires_at.isoformat(),
                "duration_days": lic.duration_days,
                "status": lic.status,
            },
        }

    async def upgrade(self, license_id: uuid.UUID, new_plan: str, operator_id: uuid.UUID | None = None) -> dict:
        from shared.constants.feature_gates import PLAN_HIERARCHY

        result = await self.db.execute(
            select(LicenseCode).where(LicenseCode.id == license_id)
        )
        lic = result.scalar_one_or_none()
        if not lic:
            raise NotFoundException(message="授权码不存在")
        if lic.status == "revoked":
            raise BadRequestException(message="已吊销的授权码无法升级")
        if PLAN_HIERARCHY.get(new_plan, 0) <= PLAN_HIERARCHY.get(lic.plan, 0):
            raise BadRequestException(message="只能升级到更高级别的套餐")

        old_plan = lic.plan
        lic.plan = new_plan

        activations_result = await self.db.execute(
            select(LicenseActivation).where(LicenseActivation.license_id == lic.id)
        )
        for activation in activations_result.scalars().all():
            user_result = await self.db.execute(select(User).where(User.id == activation.user_id))
            user = user_result.scalar_one_or_none()
            if user and PLAN_HIERARCHY.get(new_plan, 0) > PLAN_HIERARCHY.get(user.plan, 0):
                user.plan = new_plan

        change_log = LicenseChangeLog(
            license_id=lic.id,
            action="upgrade",
            old_value=old_plan,
            new_value=new_plan,
            operator_id=operator_id,
            detail=f"套餐升级: {old_plan} → {new_plan}",
        )
        self.db.add(change_log)

        await self.db.flush()
        return {
            "code": 0,
            "data": {
                "old_plan": old_plan,
                "new_plan": new_plan,
                "features": PLAN_FEATURES_MAP.get(new_plan, []),
            },
        }

    async def deactivate_device(
        self,
        user_id: uuid.UUID,
        device_fingerprint: str,
    ) -> dict:
        activation_result = await self.db.execute(
            select(LicenseActivation).where(
                LicenseActivation.user_id == user_id,
                LicenseActivation.device_fingerprint == device_fingerprint,
            )
        )
        activation = activation_result.scalar_one_or_none()
        if not activation:
            raise NotFoundException(message="未找到该设备的激活记录")

        license_result = await self.db.execute(
            select(LicenseCode).where(LicenseCode.id == activation.license_id)
        )
        lic = license_result.scalar_one_or_none()

        change_log = LicenseChangeLog(
            license_id=activation.license_id,
            action="deactivate_device",
            old_value=f"device={device_fingerprint[:8]}",
            operator_id=user_id,
            detail="设备解绑",
        )
        self.db.add(change_log)

        await self.db.delete(activation)

        if lic and lic.current_activations > 0:
            lic.current_activations -= 1
            if lic.current_activations == 0 and lic.status == "active":
                lic.status = "unused"

        await self.db.flush()
        return {"code": 0, "message": "设备已解绑"}

    async def list_licenses(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        plan: str | None = None,
        batch_id: str | None = None,
        search: str | None = None,
    ) -> dict:
        query = select(LicenseCode)

        if status:
            query = query.where(LicenseCode.status == status)
        if plan:
            query = query.where(LicenseCode.plan == plan)
        if batch_id:
            query = query.where(LicenseCode.batch_id == batch_id)
        if search:
            query = query.where(LicenseCode.code.ilike(f"%{search}%"))

        total_result = await self.db.execute(select(func.count()).select_from(query.subquery()))
        total = total_result.scalar() or 0

        query = query.order_by(LicenseCode.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        licenses = result.scalars().all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "id": str(l.id),
                    "code": l.code,
                    "plan": l.plan,
                    "duration_days": l.duration_days,
                    "status": l.status,
                    "current_activations": l.current_activations,
                    "max_activations": l.max_activations,
                    "batch_id": l.batch_id,
                    "note": l.note,
                    "created_at": l.created_at.isoformat() if l.created_at else None,
                    "activated_at": l.activated_at.isoformat() if l.activated_at else None,
                    "expires_at": l.expires_at.isoformat() if l.expires_at else None,
                    "revoked_at": l.revoked_at.isoformat() if l.revoked_at else None,
                }
                for l in licenses
            ],
        }

    async def get_change_logs(self, license_id: uuid.UUID) -> list[dict]:
        result = await self.db.execute(
            select(LicenseChangeLog)
            .where(LicenseChangeLog.license_id == license_id)
            .order_by(LicenseChangeLog.created_at.desc())
        )
        logs = result.scalars().all()
        return [
            {
                "id": str(log.id),
                "action": log.action,
                "old_value": log.old_value,
                "new_value": log.new_value,
                "operator_id": str(log.operator_id) if log.operator_id else None,
                "detail": log.detail,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]
