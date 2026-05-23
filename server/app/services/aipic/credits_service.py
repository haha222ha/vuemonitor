import logging
import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aipic import AipicCreditsLog, AipicUserCredits

logger = logging.getLogger(__name__)

PLAN_DAILY_LIMITS = {
    "free": 3,
    "pro": 50,
    "premium": 200,
    "enterprise": -1,
}

PLAN_FREE_CREDITS = {
    "free": 3,
    "pro": 0,
    "premium": 0,
    "enterprise": 0,
}


async def get_or_create_credits(db: AsyncSession, user_id: uuid.UUID, plan: str = "free") -> AipicUserCredits:
    result = await db.execute(
        select(AipicUserCredits).where(AipicUserCredits.user_id == user_id)
    )
    credits = result.scalar_one_or_none()
    if credits:
        await _reset_daily_if_needed(db, credits, plan)
        return credits

    daily_limit = PLAN_DAILY_LIMITS.get(plan, 3)
    initial = PLAN_FREE_CREDITS.get(plan, 3)

    credits = AipicUserCredits(
        user_id=user_id,
        credits=initial,
        total_purchased=initial,
        total_used=0,
        daily_generate_limit=daily_limit if daily_limit > 0 else 999,
        today_generated_count=0,
        last_reset_date=date.today(),
    )
    db.add(credits)

    if initial > 0:
        log = AipicCreditsLog(
            user_id=user_id,
            change_amount=initial,
            change_type="daily_reset",
            description=f"{plan}套餐每日积分重置",
            balance_after=initial,
        )
        db.add(log)

    await db.flush()
    return credits


async def _reset_daily_if_needed(db: AsyncSession, credits: AipicUserCredits, plan: str) -> None:
    today = date.today()
    if credits.last_reset_date == today:
        return

    daily_limit = PLAN_DAILY_LIMITS.get(plan, 3)
    free_credits = PLAN_FREE_CREDITS.get(plan, 3)

    old_credits = credits.credits
    credits.credits = free_credits
    credits.today_generated_count = 0
    credits.last_reset_date = today
    credits.daily_generate_limit = daily_limit if daily_limit > 0 else 999

    if free_credits > 0:
        log = AipicCreditsLog(
            user_id=credits.user_id,
            change_amount=free_credits - old_credits,
            change_type="daily_reset",
            description=f"{plan}套餐每日积分重置",
            balance_after=free_credits,
        )
        db.add(log)

    await db.flush()


async def deduct_credits(
    db: AsyncSession, user_id: uuid.UUID, amount: int, description: str
) -> tuple[bool, int]:
    result = await db.execute(
        select(AipicUserCredits)
        .where(AipicUserCredits.user_id == user_id)
        .with_for_update()
    )
    credits = result.scalar_one_or_none()
    if not credits:
        return False, 0

    if credits.credits < amount:
        return False, credits.credits

    credits.credits -= amount
    credits.total_used += amount
    credits.today_generated_count += 1

    log = AipicCreditsLog(
        user_id=user_id,
        change_amount=-amount,
        change_type="consume",
        description=description,
        balance_after=credits.credits,
    )
    db.add(log)
    await db.flush()
    return True, credits.credits


async def refund_credits(
    db: AsyncSession, user_id: uuid.UUID, amount: int, description: str
) -> tuple[bool, int]:
    result = await db.execute(
        select(AipicUserCredits)
        .where(AipicUserCredits.user_id == user_id)
        .with_for_update()
    )
    credits = result.scalar_one_or_none()
    if not credits:
        return False, 0

    credits.credits += amount
    credits.total_used = max(0, credits.total_used - amount)

    log = AipicCreditsLog(
        user_id=user_id,
        change_amount=amount,
        change_type="refund",
        description=description,
        balance_after=credits.credits,
    )
    db.add(log)
    await db.flush()
    return True, credits.credits


async def add_credits(
    db: AsyncSession, user_id: uuid.UUID, amount: int, change_type: str, description: str
) -> int:
    result = await db.execute(
        select(AipicUserCredits)
        .where(AipicUserCredits.user_id == user_id)
        .with_for_update()
    )
    credits = result.scalar_one_or_none()
    if not credits:
        return -1

    credits.credits += amount
    if change_type == "purchase":
        credits.total_purchased += amount

    log = AipicCreditsLog(
        user_id=user_id,
        change_amount=amount,
        change_type=change_type,
        description=description,
        balance_after=credits.credits,
    )
    db.add(log)
    await db.flush()
    return credits.credits


async def check_daily_quota(db: AsyncSession, user_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(AipicUserCredits).where(AipicUserCredits.user_id == user_id)
    )
    credits = result.scalar_one_or_none()
    if not credits:
        return False
    if credits.daily_generate_limit == -1:
        return True
    return credits.today_generated_count < credits.daily_generate_limit


async def get_credits_log(
    db: AsyncSession, user_id: uuid.UUID, page: int = 1, page_size: int = 20
) -> dict:
    count_result = await db.execute(
        select(func.count()).where(AipicCreditsLog.user_id == user_id)
    )
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    result = await db.execute(
        select(AipicCreditsLog)
        .where(AipicCreditsLog.user_id == user_id)
        .order_by(AipicCreditsLog.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    logs = result.scalars().all()

    return {
        "total": total,
        "items": [
            {
                "id": str(log.id),
                "change_amount": log.change_amount,
                "change_type": log.change_type,
                "description": log.description,
                "balance_after": log.balance_after,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
        "page": page,
        "page_size": page_size,
    }
