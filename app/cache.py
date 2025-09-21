from redis import Redis, RedisError
import json
from app.config import settings
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class RedisCache:
    """
    This redis client provides helper methods to interact with a Redis database and JSON encoding/decoding and error handling. 
    """
     
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.host = host
        self.port = port
        self.db = db
        try:
            self.client = Redis(host=self.host, port=self.port, db=self.db)
            if self.client.ping():
                logger.info("Connected to Redis at %s:%s", self.host, self.port)
            else:
                logger.warning("Cannot connect to Redis at %s:%s", self.host, self.port)
        except RedisError as e:
            logger.exception("Could not connect to Redis at %s:%s - %s", self.host, self.port, str(e))
            self.client = None

    def set(self, key: str, value: Dict[str, Any], ex: int = 60) -> bool:
        try:
            self.client.set(key, json.dumps(value), ex=ex)
            logger.debug(f"Set key {key} in Redis (expires in {ex} seconds)")
            return True
        except RedisError as e: 
            logger.exception(f"Redis set error for key {key}: {str(e)}")
            return False
        
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        try: 
            value = self.client.get(key)
            if value:
                try:
                    return json.loads(value.decode("utf-8"))
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode JSON for key {key}: {str(e)}")
                    return None
            return None
        except RedisError as e:
            logger.exception(f"Redis get error for key {key}: {str(e)}")
            return None
        
    def delete(self, key: str) -> bool:
        try:
            if self.client.delete(key):
                return True
            else:
                return False
        except RedisError as e:
            logger.exception(f"Redis delete error for key {key}: {str(e)}")
            return False

    def clear_all(self) -> bool:
        try:
            self.client.flushdb()
            logger.info("Redis cache flushed.")
            return True
        except RedisError as e:
            logger.exception(f"Redis flush error: {str(e)}")
            return False