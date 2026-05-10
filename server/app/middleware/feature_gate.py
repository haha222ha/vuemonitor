import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenException
from app.middleware.auth import CurrentUser
from app.models.user import User
from app.models.feature_gate import FeatureGate, FeatureGateUsage

from shared.constants.feature_gates import PLAN_HIERARCHY, PLAN_LIMITS, is_plan_sufficient


class FeatureGateMiddleware:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_and_downgrade_expired_plan(self, user: User) -> bool:
        if user.plan == "free":
            return False

        now = datetime.now(timezone.utc)

        if user.plan_expires_at and user.plan_expires_at < now:
            old_plan = user.plan
            user.plan = "free"
            user.plan_expires_at = None
            await self.db.flush()
            return True

        return False

    async def check_gate(self, user: User, gate_key: str) -> None:
        await self.check_and_downgrade_expired_plan(user)

        result = await self.db.execute(
            select(FeatureGate).where(FeatureGate.gate_key == gate_key, FeatureGate.is_active == True)
        )
        gate = result.scalar_one_or_none()

        if not gate:
            return

        if not is_plan_sufficient(user.plan, gate.required_plan):
            raise ForbiddenException(
                code=42010,
                message=f"当前套餐不支持「{gate.gate_name}」，需要{gate.required_plan}及以上",
            )

        if gate.gate_type == "quota":
            config = gate.config or {}
            quota_limit = config.get(user.plan, config.get("default", 0))
            if quota_limit > 0:
                today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                count_result = await self.db.execute(
                    select(func.count()).where(
                        FeatureGateUsage.user_id == user.id,
                        FeatureGateUsage.gate_key == gate_key,
                        FeatureGateUsage.used_at >= today_start,
                    )
                )
                used_count = count_result.scalar() or 0
                if used_count >= quota_limit:
                    raise ForbiddenException(
                        code=42011,
                        message=f"「{gate.gate_name}」今日配额已用尽（{used_count}/{quota_limit}）",
                    )

        if gate.gate_type == "limit":
            limits = PLAN_LIMITS.get(user.plan, PLAN_LIMITS["free"])
            gate_key_mapping = {
                "gate:monitor:add": "maxProducts",
                "gate:ai:basic_analysis": "aiCallsPerDay",
                "gate:ai:trend_score": "aiCallsPerDay",
                "gate:ai:prediction": "aiCallsPerDay",
                "gate:ai:risk_warning": "aiCallsPerDay",
                "gate:ai:batch_analysis": "aiCallsPerDay",
                "gate:ai:report": "aiCallsPerDay",
            }

            limit_key = gate_key_mapping.get(gate_key)
            if limit_key:
                limit_value = limits.get(limit_key, 0)
                if limit_value == 0:
                    raise ForbiddenException(
                        code=42012,
                        message=f"当前套餐不支持「{gate.gate_name}」",
                    )
                if limit_value > 0 and limit_key == "maxProducts":
                    from app.models.product import Product
                    count_result = await self.db.execute(
                        select(func.count()).select_from(Product).where(
                            Product.user_id == user.id,
                            Product.is_active == True,
                        )
                    )
                    current_count = count_result.scalar() or 0
                    if current_count >= limit_value:
                        raise ForbiddenException(
                            code=42013,
                            message=f"商品数量已达上限（{current_count}/{limit_value}），请升级套餐",
                        )
                elif limit_key == "aiCallsPerDay" and limit_value > 0:
                    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                    ai_gates = [k for k, v in gate_key_mapping.items() if v == "aiCallsPerDay"]
                    count_result = await self.db.execute(
                        select(func.count()).where(
                            FeatureGateUsage.user_id == user.id,
                            FeatureGateUsage.gate_key.in_(ai_gates),
                            FeatureGateUsage.used_at >= today_start,
                        )
                    )
                    used_count = count_result.scalar() or 0
                    if used_count >= limit_value:
                        raise ForbiddenException(
                            code=42014,
                            message=f"今日AI分析次数已达上限（{used_count}/{limit_value}），请升级套餐",
                        )

    async def record_usage(self, user_id: uuid.UUID, gate_key: str, detail: dict | None = None) -> None:
        usage = FeatureGateUsage(
            user_id=user_id,
            gate_key=gate_key,
            detail=detail or {},
        )
        self.db.add(usage)


async def require_feature(gate_key: str):
    async def _check(user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]) -> User:
        middleware = FeatureGateMiddleware(db)
        await middleware.check_gate(user, gate_key)
        return user

    return _check
