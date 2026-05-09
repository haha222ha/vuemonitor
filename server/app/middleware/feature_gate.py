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

from shared.constants.feature_gates import PLAN_HIERARCHY, is_plan_sufficient


class FeatureGateMiddleware:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_gate(self, user: User, gate_key: str) -> None:
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
