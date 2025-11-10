"""Cache utility."""
import json
import os
from typing import Optional, Any
import redis.asyncio as redis


class CacheService:
    """Service for caching operations."""
    
    def __init__(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        value = await self.redis_client.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set a value in cache."""
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await self.redis_client.set(key, value, ex=ttl)
    
    async def delete(self, key: str):
        """Delete a key from cache."""
        await self.redis_client.delete(key)
    
    async def close(self):
        """Close the Redis connection."""
        await self.redis_client.close()
