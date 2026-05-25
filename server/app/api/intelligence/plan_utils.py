# AIGC START
"""情报会员有效套餐：按档位优先级取最高，续费从当前到期日顺延。"""
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.intelligence import IntelMembership

PLAN_RANK: dict[str, int] = {
    "free": 0,
    "weekly": 1,
    "monthly": 2,
    "yearly": 3,
    "enterprise": 3,
    "pro": 2,
}


def plan_rank(plan: str) -> int:
    return PLAN_RANK.get(plan, 0)


def pick_effective_membership(memberships: list[IntelMembership]) -> IntelMembership | None:
    if not memberships:
        return None
    return max(
        memberships,
        key=lambda m: (plan_rank(m.plan), m.expires_at or datetime.min.replace(tzinfo=UTC)),
    )


async def list_active_memberships(
    user_id,
    db: AsyncSession,
    *,
    now: datetime | None = None,
) -> list[IntelMembership]:
    now = now or datetime.now(UTC)
    result = await db.execute(
        select(IntelMembership).where(
            IntelMembership.user_id == user_id,
            IntelMembership.status == "active",
            IntelMembership.expires_at > now,
        )
    )
    return list(result.scalars().all())


async def get_effective_membership(user_id, db: AsyncSession) -> IntelMembership | None:
    active = await list_active_memberships(user_id, db)
    return pick_effective_membership(active)


def compute_membership_expires(
    now: datetime,
    active_memberships: list[IntelMembership],
    new_plan: str,
    duration_days: int,
) -> datetime:
    new_rank = plan_rank(new_plan)
    effective = pick_effective_membership(active_memberships)
    eff_rank = plan_rank(effective.plan) if effective else 0

    if new_rank >= eff_rank:
        base = now
        if effective and effective.expires_at and effective.expires_at > now:
            base = effective.expires_at
        return base + timedelta(days=duration_days)

    return now + timedelta(days=duration_days)


async def apply_effective_plan_to_user(user, db: AsyncSession) -> IntelMembership | None:
    effective = await get_effective_membership(user.id, db)
    if effective:
        user.plan = effective.plan
        user.plan_expires_at = effective.expires_at
    return effective
# AIGC END
