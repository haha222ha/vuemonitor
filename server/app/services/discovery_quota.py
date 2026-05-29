"""云端发现库额度：按账号 + IP 合计，仅限制搜索/从发现库加入监控。"""
from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import Request

from app.core.exceptions import ForbiddenException
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

# 每日「搜索 + 从发现库加入监控」合计次数（同一账号 + 同一 IP）
DISCOVERY_DAILY_LIMITS: dict[str, int] = {
    "free": 20,
    "pro": 200,
    "premium": 200,
    "enterprise": -1,
}

DISCOVERY_QUOTA_HINT = (
    "「搜索添加」使用云端商品发现库，按账号与当前 IP 合计计次，每日 0 点重置。"
    "免费版每日 20 次，Pro 每日 200 次。"
    "「粘贴链接」自行填写商品链接或 ID，不占用发现库额度，数量不限。"
)

DISCOVERY_QUOTA_EXCEEDED_MESSAGE = (
    "今日云端「搜索添加」次数已用完，请明日再试，或使用「粘贴链接」添加您自己的商品。"
)

STORE_ADD_MAX_PER_REQUEST = 5


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _day_key() -> str:
    return datetime.now(UTC).strftime("%Y%m%d")


def _quota_redis_key(user_id: str, client_ip: str) -> str:
    ip_part = hashlib.sha256(client_ip.encode()).hexdigest()[:12]
    return f"discovery:quota:{_day_key()}:{user_id}:{ip_part}"


def daily_limit_for_plan(plan: str | None) -> int:
    return DISCOVERY_DAILY_LIMITS.get(plan or "free", DISCOVERY_DAILY_LIMITS["free"])


async def get_discovery_quota(user_id: str, client_ip: str, plan: str | None) -> dict[str, Any]:
    limit = daily_limit_for_plan(plan)
    if limit < 0:
        return {
            "plan": plan or "free",
            "daily_limit": -1,
            "used_today": 0,
            "remaining": -1,
            "quota_hint": DISCOVERY_QUOTA_HINT,
        }

    key = _quota_redis_key(str(user_id), client_ip)
    used = 0
    try:
        redis = await get_redis()
        raw = await redis.get(key)
        used = int(raw or 0)
    except Exception as e:
        logger.warning("discovery quota read failed: %s", e)

    remaining = max(0, limit - used)
    return {
        "plan": plan or "free",
        "daily_limit": limit,
        "used_today": used,
        "remaining": remaining,
        "quota_hint": DISCOVERY_QUOTA_HINT,
    }


async def consume_discovery_quota(
    user_id: str,
    client_ip: str,
    plan: str | None,
    *,
    amount: int = 1,
    action: str = "search",
) -> dict[str, Any]:
    if amount < 1:
        amount = 1

    limit = daily_limit_for_plan(plan)
    status = await get_discovery_quota(user_id, client_ip, plan)
    if limit < 0:
        status["action"] = action
        return status

    if status["remaining"] < amount:
        raise ForbiddenException(
            code=42021,
            message=(
                f"{DISCOVERY_QUOTA_EXCEEDED_MESSAGE} "
                f"（已用 {status['used_today']}/{limit}，本次需 {amount} 次）"
            ),
            detail={
                "quota_hint": DISCOVERY_QUOTA_HINT,
                "used_today": status["used_today"],
                "daily_limit": limit,
                "remaining": status["remaining"],
                "action": action,
            },
        )

    key = _quota_redis_key(str(user_id), client_ip)
    try:
        redis = await get_redis()
        new_used = await redis.incrby(key, amount)
        if new_used == amount:
            await redis.expire(key, 86400 * 2)
        if new_used > limit:
            await redis.decrby(key, amount)
            raise ForbiddenException(
                code=42021,
                message=DISCOVERY_QUOTA_EXCEEDED_MESSAGE,
                detail={"quota_hint": DISCOVERY_QUOTA_HINT, "used_today": limit, "daily_limit": limit},
            )
    except ForbiddenException:
        raise
    except Exception as e:
        logger.warning("discovery quota consume failed: %s", e)

    return await get_discovery_quota(user_id, client_ip, plan)


async def bind_ref_to_user(ref: str, user_id: str) -> None:
    try:
        redis = await get_redis()
        await redis.set(f"discovery:ref_owner:{ref}", str(user_id), ex=7 * 24 * 3600)
    except Exception as e:
        logger.warning("discovery ref owner bind failed: %s", e)


async def assert_ref_owner(ref: str, user_id: str) -> None:
    try:
        redis = await get_redis()
        owner = await redis.get(f"discovery:ref_owner:{ref}")
        if owner and owner != str(user_id):
            raise ForbiddenException(
                code=42022,
                message="该商品引用无效或已过期，请重新搜索后再添加",
            )
    except ForbiddenException:
        raise
    except Exception as e:
        logger.warning("discovery ref owner check failed: %s", e)
