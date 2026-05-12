import json
import logging
import functools
from typing import Any, Callable

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


async def cache_mget(keys: list[str]) -> list[Any | None]:
    if not keys:
        return []
    full_keys = [f"{_CACHE_PREFIX}{k}" for k in keys]
    try:
        raws = await redis_client.mget(*full_keys)
        results = []
        for raw in raws:
            if raw is None:
                results.append(None)
            else:
                try:
                    results.append(json.loads(raw))
                except (json.JSONDecodeError, TypeError):
                    results.append(None)
        return results
    except Exception as e:
        logger.warning(f"Redis cache_mget error: {e}")
        return [None] * len(keys)


async def cache_mset(items: dict[str, tuple[Any, int]]) -> None:
    if not items:
        return
    try:
        pipe = redis_client.pipeline()
        for key, (value, ttl) in items.items():
            full_key = f"{_CACHE_PREFIX}{key}"
            pipe.setex(full_key, ttl, json.dumps(value, default=str))
        await pipe.execute()
    except Exception as e:
        logger.warning(f"Redis cache_mset error: {e}")


async def invalidate_user_cache(user_id: str) -> None:
    patterns = [
        f"dashboard:stats:{user_id}",
        f"dashboard:trend:{user_id}:*",
        f"products:list:{user_id}:*",
        f"features:*:{user_id}:*",
    ]
    for pattern in patterns:
        await cache_delete_pattern(pattern)


def cached(ttl: int = 300, key_builder: Callable | None = None):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = f"{func.__module__}:{func.__name__}:{args}:{kwargs}"

            cached_val = await cache_get(cache_key)
            if cached_val is not None:
                return cached_val

            result = await func(*args, **kwargs)

            if result is not None:
                await cache_set(cache_key, result, ttl_seconds=ttl)

            return result
        return wrapper
    return decorator


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
