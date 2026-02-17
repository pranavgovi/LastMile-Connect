"""Redis async client; set in lifespan, used by location_store and WebSocket."""
import redis.asyncio as aioredis

from backend.config import settings

_redis: aioredis.Redis | None = None


def set_redis(client: aioredis.Redis) -> None:
    global _redis
    _redis = client


async def get_redis() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialized")
    return _redis
