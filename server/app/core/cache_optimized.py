import functools
import hashlib
import json
import logging
from collections.abc import Callable
from typing import Any

from app.core.redis import redis_client

logger = logging.getLogger(__name__)

_CACHE_PREFIX = "cache:"
_RATE_LIMIT_PREFIX = "ratelimit:"
_LOCK_PREFIX = "lock:"


class CacheStrategy:
    TTL_SHORT = 60
    TTL_MEDIUM = 300
    TTL_LONG = 3600
    TTL_EXTENDED = 86400

    @staticmethod
    def for_user_stats() -> int:
        return CacheStrategy.TTL_MEDIUM

    @staticmethod
    def for_product_list() -> int:
        return CacheStrategy.TTL_SHORT

    @staticmethod
    def for_dashboard() -> int:
        return CacheStrategy.TTL_MEDIUM

    @staticmethod
    def for_ai_analysis() -> int:
        return CacheStrategy.TTL_LONG

    @staticmethod
    def for_feature_flags() -> int:
        return CacheStrategy.TTL_EXTENDED

    @staticmethod
    def for_category_stats() -> int:
        return CacheStrategy.TTL_LONG


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


async def cache_set(
    key: str,
    value: Any,
    ttl_seconds: int = 300,
    strategy: Callable[[], int] | None = None
) -> None:
    full_key = f"{_CACHE_PREFIX}{key}"

    if strategy:
        ttl_seconds = strategy()

    try:
        await redis_client.setex(full_key, ttl_seconds, json.dumps(value, default=str))
    except Exception as e:
        logger.warning(f"Redis cache_set error for {key}: {e}")


async def cache_set_async(key: str, value: Any, ttl_seconds: int = 300) -> None:
    full_key = f"{_CACHE_PREFIX}{key}"
    try:
        await redis_client.setex(full_key, ttl_seconds, json.dumps(value, default=str))
    except Exception as e:
        logger.warning(f"Redis cache_set_async error for {key}: {e}")


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


async def invalidate_product_cache(product_id: str) -> None:
    patterns = [
        f"product:{product_id}:*",
        f"features:{product_id}:*",
    ]
    for pattern in patterns:
        await cache_delete_pattern(pattern)


async def cache_warm_user_data(user_id: str, db_session) -> None:
    try:
        from sqlalchemy import select

        from app.models.product import Product, ProductFeature

        recent_products = await db_session.execute(
            select(Product.id)
            .where(Product.user_id == user_id)
            .where(Product.is_active.is_(True))
            .limit(100)
        )
        product_ids = [str(row[0]) for row in recent_products.fetchall()]

        if product_ids:
            cache_items = {}
            for pid in product_ids:
                latest_feature = await db_session.execute(
                    select(ProductFeature)
                    .where(ProductFeature.product_id == pid)
                    .order_by(ProductFeature.collected_at.desc())
                    .limit(1)
                )
                feature = latest_feature.scalar_one_or_none()
                if feature:
                    cache_items[f"product:latest:{pid}"] = (
                        {
                            "price": float(feature.price) if feature.price else None,
                            "sales_count": feature.sales_count,
                        },
                        CacheStrategy.TTL_MEDIUM
                    )

            if cache_items:
                await cache_mset(cache_items)

        logger.info(f"Cache warmed for user {user_id}, {len(cache_items)} items")
    except Exception as e:
        logger.warning(f"Cache warming error for user {user_id}: {e}")


def cached(
    ttl: int = 300,
    key_builder: Callable | None = None,
    strategy: Callable[[], int] | None = None
):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                cache_key = f"{func.__module__}:{func.__name__}"

            cached_val = await cache_get(cache_key)
            if cached_val is not None:
                return cached_val

            result = await func(*args, **kwargs)

            if result is not None:
                await cache_set(cache_key, result, ttl_seconds=ttl, strategy=strategy)

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


async def acquire_lock(
    key: str,
    timeout_seconds: int = 10,
    lock_ttl_seconds: int = 30,
) -> bool:
    lock_key = f"{_LOCK_PREFIX}{key}"
    try:
        import time
        lock_value = f"{time.time()}"
        acquired = await redis_client.set(lock_key, lock_value, nx=True, ex=lock_ttl_seconds)
        return bool(acquired)
    except Exception as e:
        logger.warning(f"Redis acquire_lock error for {key}: {e}")
        return False


async def release_lock(key: str) -> None:
    lock_key = f"{_LOCK_PREFIX}{key}"
    try:
        await redis_client.delete(lock_key)
    except Exception as e:
        logger.warning(f"Redis release_lock error for {key}: {e}")


def _current_window(window_seconds: int) -> str:
    import time
    return str(int(time.time() // window_seconds))


def generate_cache_key(*args, **kwargs) -> str:
    key_parts = [str(arg) for arg in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    key_str = ":".join(key_parts)
    return hashlib.md5(key_str.encode()).hexdigest()
