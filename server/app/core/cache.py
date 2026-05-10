import json
import logging
from typing import Any

from app.core.redis import redis_client

logger = logging.getLogger(__name__)

_CACHE_PREFIX = "cache:"
_RATE_LIMIT_PREFIX = "ratelimit:"


async def cache_get(key: str) -> Any | None:
    full_key = f"{_CACHE_PREFIX}{key}"
    try:
        raw = await redis_client.get(full_key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.warning(f"Redis cache_get error for {key}: {e}")
        return None


async def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> None:
    full_key = f"{_CACHE_PREFIX}{key}"
    try:
        await redis_client.setex(full_key, ttl_seconds, json.dumps(value, default=str))
    except Exception as e:
        logger.warning(f"Redis cache_set error for {key}: {e}")


async def cache_delete(key: str) -> None:
    full_key = f"{_CACHE_PREFIX}{key}"
    try:
        await redis_client.delete(full_key)
    except Exception as e:
        logger.warning(f"Redis cache_delete error for {key}: {e}")


async def cache_delete_pattern(pattern: str) -> None:
    full_pattern = f"{_CACHE_PREFIX}{pattern}"
    try:
        keys = []
        async for key in redis_client.scan_iter(match=full_pattern):
            keys.append(key)
        if keys:
            await redis_client.delete(*keys)
    except Exception as e:
        logger.warning(f"Redis cache_delete_pattern error for {pattern}: {e}")


async def rate_limit_check(
    identifier: str,
    max_requests: int,
    window_seconds: int,
) -> tuple[bool, int]:
    key = f"{_RATE_LIMIT_PREFIX}{identifier}"
    try:
        pipe = redis_client.pipeline()
        now_key = f"{key}:{_current_window(window_seconds)}"
        pipe.incr(now_key)
        pipe.expire(now_key, window_seconds * 2)
        results = await pipe.execute()
        current_count = results[0]
        remaining = max(0, max_requests - current_count)
        allowed = current_count <= max_requests
        return allowed, remaining
    except Exception as e:
        logger.warning(f"Redis rate_limit_check error for {identifier}: {e}")
        return True, max_requests


async def rate_limit_sliding_window(
    identifier: str,
    max_requests: int,
    window_seconds: int,
) -> tuple[bool, int]:
    key = f"{_RATE_LIMIT_PREFIX}{identifier}"
    try:
        import time
        now = time.time()
        window_start = now - window_seconds

        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window_seconds + 1)
        results = await pipe.execute()
        current_count = results[2]
        remaining = max(0, max_requests - current_count)
        allowed = current_count <= max_requests
        return allowed, remaining
    except Exception as e:
        logger.warning(f"Redis rate_limit_sliding_window error for {identifier}: {e}")
        return True, max_requests


def _current_window(window_seconds: int) -> str:
    import time
    return str(int(time.time() // window_seconds))
