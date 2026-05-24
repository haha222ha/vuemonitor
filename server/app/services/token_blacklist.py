import logging
import uuid
from datetime import UTC, datetime

from app.core.redis import get_redis, is_redis_available

logger = logging.getLogger(__name__)

_BLACKLIST_PREFIX = "token_blacklist:"
_MEMORY_BLACKLIST: dict[str, float] = {}
_MEMORY_BLACKLIST_MAX = 10000


async def blacklist_token(token_jti: str, expires_at: datetime) -> None:
    ttl_seconds = max(1, int((expires_at - datetime.now(UTC)).total_seconds()))
    key = f"{_BLACKLIST_PREFIX}{token_jti}"

    if is_redis_available():
        try:
            redis = await get_redis()
            await redis.setex(key, ttl_seconds, "1")
            return
        except Exception as e:
            logger.warning(f"Redis blacklist_token error: {e}")

    if len(_MEMORY_BLACKLIST) >= _MEMORY_BLACKLIST_MAX:
        _evict_memory_blacklist()
    _MEMORY_BLACKLIST[token_jti] = expires_at.timestamp()


async def is_token_blacklisted(token_jti: str) -> bool:
    key = f"{_BLACKLIST_PREFIX}{token_jti}"

    if is_redis_available():
        try:
            redis = await get_redis()
            return await redis.exists(key) > 0
        except Exception as e:
            logger.warning(f"Redis is_token_blacklisted error: {e}")

    expires_at = _MEMORY_BLACKLIST.get(token_jti)
    if expires_at is None:
        return False
    if datetime.now(UTC).timestamp() > expires_at:
        del _MEMORY_BLACKLIST[token_jti]
        return False
    return True


async def blacklist_all_user_tokens(user_id: uuid.UUID) -> int:
    prefix = f"{_BLACKLIST_PREFIX}user:{str(user_id)}:"
    count = 0

    if is_redis_available():
        try:
            redis = await get_redis()
            async for key in redis.scan_iter(match=f"{prefix}*"):
                await redis.delete(key)
                count += 1
        except Exception as e:
            logger.warning(f"Redis blacklist_all_user_tokens error: {e}")

    keys_to_delete = [k for k in _MEMORY_BLACKLIST if k.startswith(prefix)]
    for k in keys_to_delete:
        del _MEMORY_BLACKLIST[k]
        count += 1

    return count


def _evict_memory_blacklist() -> None:
    now = datetime.now(UTC).timestamp()
    expired_keys = [k for k, v in _MEMORY_BLACKLIST.items() if now > v]
    for k in expired_keys:
        del _MEMORY_BLACKLIST[k]
    if len(_MEMORY_BLACKLIST) >= _MEMORY_BLACKLIST_MAX:
        sorted_keys = sorted(_MEMORY_BLACKLIST.items(), key=lambda x: x[1])
        for k, _ in sorted_keys[: len(sorted_keys) // 2]:
            del _MEMORY_BLACKLIST[k]
