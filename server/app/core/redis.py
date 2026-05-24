import redis.asyncio as aioredis

from app.config import get_settings

settings = get_settings()

redis_client = aioredis.from_url(
    settings.REDIS_URL_RESOLVED,
    encoding="utf-8",
    decode_responses=True,
    max_connections=20,
    socket_timeout=5,
    socket_connect_timeout=3,
    retry_on_timeout=True,
    socket_keepalive=True,
    health_check_interval=30,
)

_redis_available: bool = True


async def get_redis() -> aioredis.Redis:
    return redis_client


async def close_redis() -> None:
    await redis_client.close()


async def check_redis_health() -> bool:
    global _redis_available
    try:
        await redis_client.ping()
        if not _redis_available:
            _redis_available = True
        return True
    except Exception:
        _redis_available = False
        return False


def is_redis_available() -> bool:
    return _redis_available
