import functools
import json
import logging
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any

from app.core.redis import is_redis_available, redis_client

logger = logging.getLogger(__name__)

_CACHE_PREFIX = "cache:"
_RATE_LIMIT_PREFIX = "ratelimit:"
_NULL_SENTINEL = "__NULL__"
_NULL_CACHE_TTL = 60

_MEMORY_CACHE_MAX_SIZE = 1000
_MEMORY_RATE_LIMIT_MAX_ENTRIES = 5000

_memory_cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
_memory_rate_limits: dict[str, list[float]] = {}


def _memory_cache_get(key: str) -> Any | None:
    if key in _memory_cache:
        value, expires_at = _memory_cache[key]
        if time.time() < expires_at:
            _memory_cache.move_to_end(key)
            return value
        del _memory_cache[key]
    return None


def _memory_cache_set(key: str, value: Any, ttl_seconds: int) -> None:
    if len(_memory_cache) >= _MEMORY_CACHE_MAX_SIZE:
        _memory_cache.popitem(last=False)
    _memory_cache[key] = (value, time.time() + ttl_seconds)


def _memory_cache_delete(key: str) -> None:
    _memory_cache.pop(key, None)


def _memory_rate_limit_check(identifier: str, max_requests: int, window_seconds: int) -> tuple[bool, int]:
    now = time.time()
    attempts = _memory_rate_limits.get(identifier, [])
    attempts = [t for t in attempts if now - t < window_seconds]
    if len(attempts) >= max_requests:
        _memory_rate_limits[identifier] = attempts
        return False, 0
    attempts.append(now)
    _memory_rate_limits[identifier] = attempts
    if len(_memory_rate_limits) > _MEMORY_RATE_LIMIT_MAX_ENTRIES:
        oldest_keys = sorted(_memory_rate_limits.keys(),
                             key=lambda k: min(_memory_rate_limits[k]))[:len(_memory_rate_limits) // 2]
        for k in oldest_keys:
            del _memory_rate_limits[k]
    remaining = max(0, max_requests - len(attempts))
    return True, remaining


async def cache_get(key: str) -> Any | None:
    full_key = f"{_CACHE_PREFIX}{key}"
    if is_redis_available():
        try:
            raw = await redis_client.get(full_key)
            if raw is None:
                return None
            decoded = json.loads(raw)
            if decoded == _NULL_SENTINEL:
                return None
            return decoded
        except Exception as e:
            logger.warning(f"Redis cache_get error for {key}: {e}, falling back to memory")
    result = _memory_cache_get(full_key)
    if result == _NULL_SENTINEL:
        return None
    return result


async def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> None:
    full_key = f"{_CACHE_PREFIX}{key}"
    _memory_cache_set(full_key, value, ttl_seconds)
    if is_redis_available():
        try:
            await redis_client.setex(full_key, ttl_seconds, json.dumps(value, default=str))
        except Exception as e:
            logger.warning(f"Redis cache_set error for {key}: {e}")


async def cache_delete(key: str) -> None:
    full_key = f"{_CACHE_PREFIX}{key}"
    _memory_cache_delete(full_key)
    if is_redis_available():
        try:
            await redis_client.delete(full_key)
        except Exception as e:
            logger.warning(f"Redis cache_delete error for {key}: {e}")


async def cache_set_null(key: str, ttl_seconds: int = _NULL_CACHE_TTL) -> None:
    full_key = f"{_CACHE_PREFIX}{key}"
    _memory_cache_set(full_key, _NULL_SENTINEL, ttl_seconds)
    if is_redis_available():
        try:
            await redis_client.setex(full_key, ttl_seconds, json.dumps(_NULL_SENTINEL))
        except Exception as e:
            logger.warning(f"Redis cache_set_null error for {key}: {e}")


async def cache_get_with_loader(
    key: str,
    loader: Callable,
    ttl_seconds: int = 300,
    null_ttl_seconds: int = _NULL_CACHE_TTL,
) -> Any | None:
    cached = await cache_get(key)
    if cached is not None:
        return cached
    full_key = f"{_CACHE_PREFIX}{key}"
    if full_key in _memory_cache:
        return None
    if is_redis_available():
        try:
            raw = await redis_client.get(full_key)
            if raw is not None:
                return None
        except Exception as e:
            logger.debug("Redis get failed for key %s: %s", full_key, e)

    result = await loader()
    if result is not None:
        await cache_set(key, result, ttl_seconds=ttl_seconds)
    else:
        await cache_set_null(key, ttl_seconds=null_ttl_seconds)
    return result


async def cache_delete_pattern(pattern: str) -> None:
    full_pattern = f"{_CACHE_PREFIX}{pattern}"
    keys_to_delete = [k for k in _memory_cache if k.startswith(full_pattern.replace("*", ""))]
    for k in keys_to_delete:
        del _memory_cache[k]
    if is_redis_available():
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
    if is_redis_available():
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
            logger.warning(f"Redis cache_mget error: {e}, falling back to memory")
    return [_memory_cache_get(k) for k in full_keys]


async def cache_mset(items: dict[str, tuple[Any, int]]) -> None:
    if not items:
        return
    for key, (value, ttl) in items.items():
        full_key = f"{_CACHE_PREFIX}{key}"
        _memory_cache_set(full_key, value, ttl)
    if is_redis_available():
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
    if is_redis_available():
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
            logger.warning(f"Redis rate_limit_check error for {identifier}: {e}, falling back to memory")
    return _memory_rate_limit_check(identifier, max_requests, window_seconds)


async def rate_limit_sliding_window(
    identifier: str,
    max_requests: int,
    window_seconds: int,
) -> tuple[bool, int]:
    key = f"{_RATE_LIMIT_PREFIX}{identifier}"
    if is_redis_available():
        try:
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
            logger.warning(f"Redis rate_limit_sliding_window error for {identifier}: {e}, falling back to memory")
    return _memory_rate_limit_check(identifier, max_requests, window_seconds)


def _current_window(window_seconds: int) -> str:
    return str(int(time.time() // window_seconds))
