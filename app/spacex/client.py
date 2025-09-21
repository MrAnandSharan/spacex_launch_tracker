from typing import Dict, Any
from app.connection import redis_cache
import httpx
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class SpaceXClient:
    """
    SpaceXCient fetches data from the SpaceX REST API and caches responses in Redis to avoid repeatative external API calls.
    """
    def __init__(self, base_url: str = settings.BASE_URL):
        self.base_url = base_url

    async def fetch(self, endpoint: str) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint}"
        try:
            cached_value = redis_cache.get(url)
            if cached_value:
                logger.info("Returning Cached Value")
                return cached_value
            async with httpx.AsyncClient(timeout=30) as client:
                logger.info("Returning External API Call response")
                response = await client.get(url)
                response.raise_for_status()
                redis_cache.set(url, response.json(), ex=settings.CACHE_TTL_SECONDS)
                return response.json()
        except Exception as e:
            logger.exception(f"Error while fetching {url}: {str(e)}")
            raise

    async def get_launches(self) -> Dict[str, Any]:
        return await self.fetch("launches")

    async def get_rockets(self) -> Dict[str, Any]:
        return await self.fetch("rockets")

    async def get_launchpads(self) -> Dict[str, Any]:
        return await self.fetch("launchpads")
