from app.cache import RedisCache
from app.config import settings

# Shared connection instances
redis_cache = RedisCache(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT
)
