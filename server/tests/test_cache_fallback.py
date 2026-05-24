import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.cache import (
    _memory_cache_get,
    _memory_cache_set,
    _memory_rate_limit_check,
    cache_delete,
    cache_get,
    cache_set,
    rate_limit_check,
    rate_limit_sliding_window,
)


class TestMemoryCacheFallback:
    def test_memory_cache_set_and_get(self):
        _memory_cache_set("test:key", {"value": 42}, ttl_seconds=60)
        result = _memory_cache_get("test:key")
        assert result == {"value": 42}

    def test_memory_cache_get_expired(self):
        _memory_cache_set("test:expired", "data", ttl_seconds=-1)
        result = _memory_cache_get("test:expired")
        assert result is None

    def test_memory_cache_get_missing(self):
        result = _memory_cache_get("test:nonexistent")
        assert result is None

    def test_memory_rate_limit_allows_under_limit(self):
        allowed, remaining = _memory_rate_limit_check("ip:1.2.3.4", 5, 60)
        assert allowed is True
        assert remaining == 4

    def test_memory_rate_limit_blocks_over_limit(self):
        for _ in range(5):
            _memory_rate_limit_check("ip:blocked", 5, 60)
        allowed, remaining = _memory_rate_limit_check("ip:blocked", 5, 60)
        assert allowed is False
        assert remaining == 0


class TestCacheWithRedisDown:
    @pytest.mark.asyncio
    async def test_cache_get_falls_back_to_memory(self):
        with patch("app.core.cache.is_redis_available", return_value=False):
            await cache_set("fb_key", "fb_value", ttl_seconds=60)
            result = await cache_get("fb_key")
            assert result == "fb_value"

    @pytest.mark.asyncio
    async def test_cache_get_returns_none_when_both_miss(self):
        with patch("app.core.cache.is_redis_available", return_value=False):
            result = await cache_get("nonexistent_key_xyz")
            assert result is None


class TestRateLimitWithRedisDown:
    @pytest.mark.asyncio
    async def test_rate_limit_falls_back_to_memory(self):
        with patch("app.core.cache.is_redis_available", return_value=False):
            allowed, remaining = await rate_limit_check("test:fallback", 10, 60)
            assert allowed is True
            assert remaining == 9

    @pytest.mark.asyncio
    async def test_sliding_window_falls_back_to_memory(self):
        with patch("app.core.cache.is_redis_available", return_value=False):
            allowed, remaining = await rate_limit_sliding_window("test:sw_fallback", 10, 60)
            assert allowed is True


class TestRateLimitWithRedisUp:
    @pytest.mark.asyncio
    async def test_rate_limit_check_with_redis(self):
        mock_pipe = MagicMock()
        mock_pipe.incr = MagicMock(return_value=mock_pipe)
        mock_pipe.expire = MagicMock(return_value=mock_pipe)
        mock_pipe.execute = AsyncMock(return_value=[1])

        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)

        with patch("app.core.cache.is_redis_available", return_value=True), \
             patch("app.core.cache.redis_client", mock_redis):
            allowed, remaining = await rate_limit_check("test:redis_up", 10, 60)
            assert allowed is True
            assert remaining == 9

    @pytest.mark.asyncio
    async def test_rate_limit_sliding_window_with_redis(self):
        mock_pipe = MagicMock()
        mock_pipe.zremrangebyscore = MagicMock(return_value=mock_pipe)
        mock_pipe.zadd = MagicMock(return_value=mock_pipe)
        mock_pipe.zcard = MagicMock(return_value=mock_pipe)
        mock_pipe.expire = MagicMock(return_value=mock_pipe)
        mock_pipe.execute = AsyncMock(return_value=[None, None, 1, True])

        mock_redis = AsyncMock()
        mock_redis.pipeline = MagicMock(return_value=mock_pipe)

        with patch("app.core.cache.is_redis_available", return_value=True), \
             patch("app.core.cache.redis_client", mock_redis):
            allowed, remaining = await rate_limit_sliding_window("test:sw_redis", 10, 60)
            assert allowed is True
