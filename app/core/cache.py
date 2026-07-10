from redis.asyncio import Redis

from app.common.retry import CACHE_RETRY
from app.core.config import get_settings

settings = get_settings()

redis: Redis | None = None


@CACHE_RETRY
async def get_redis() -> Redis:
    global redis
    if redis is None:
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return redis


async def close_redis():
    global redis
    if redis:
        await redis.close()
        redis = None
