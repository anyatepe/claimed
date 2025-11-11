"""
Redis cache utilities for retrieval and response caching.
"""
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

import aioredis

logger = logging.getLogger(__name__)


class CacheService:
    """Service for Redis-based caching operations."""
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        redis_client: Optional[aioredis.Redis] = None,
    ):
        """
        Initialize the CacheService.
        
        Args:
            redis_url: Redis connection URL (e.g., "redis://localhost:6379").
                      If None, caching will be disabled.
            redis_client: Optional pre-configured Redis client. If provided,
                         redis_url will be ignored.
        """
        self._redis_client = redis_client
        self._redis_url = redis_url
        self._redis_initialized = False
    
    async def _get_redis_client(self) -> Optional[aioredis.Redis]:
        """Get or create Redis client."""
        if self._redis_client is not None:
            return self._redis_client
        
        if self._redis_url is None:
            return None
        
        if not self._redis_initialized:
            self._redis_client = await aioredis.from_url(self._redis_url)
            self._redis_initialized = True
        
        return self._redis_client
    
    def _hash_key(self, *parts: str) -> str:
        """Generate a hash key from multiple parts."""
        combined = ":".join(str(part) for part in parts)
        return hashlib.sha256(combined.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        redis_client = await self._get_redis_client()
        if redis_client is None:
            return None
        
        try:
            cached_data = await redis_client.get(key)
            if cached_data is not None:
                if isinstance(cached_data, bytes):
                    cached_data = cached_data.decode('utf-8')
                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"Cache read failed for key '{key}': {e}")
        
        return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Store a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time to live in seconds. If None, no expiration.
            
        Returns:
            True if successful, False otherwise
        """
        redis_client = await self._get_redis_client()
        if redis_client is None:
            return False
        
        try:
            serialized = json.dumps(value)
            if ttl is not None:
                await redis_client.setex(key, ttl, serialized)
            else:
                await redis_client.set(key, serialized)
            return True
        except Exception as e:
            logger.warning(f"Cache write failed for key '{key}': {e}")
            return False
    
    async def get_retrieval_cache(
        self, 
        query_hash: str, 
        filters: Optional[Dict[str, Any]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached chunks for a query and filters.
        
        Args:
            query_hash: Hash of the query
            filters: Optional filters dictionary
            
        Returns:
            List of chunk dictionaries or None if not cached
        """
        filters_str = json.dumps(filters, sort_keys=True) if filters else ""
        cache_key = f"retrieval:{query_hash}:{self._hash_key(filters_str)}"
        return await self.get(cache_key)
    
    async def set_retrieval_cache(
        self,
        query_hash: str,
        chunks: List[Dict[str, Any]],
        filters: Optional[Dict[str, Any]] = None,
        ttl: int = 300,  # 5 minutes default TTL for retrieval cache
    ) -> bool:
        """
        Cache chunks for a query and filters.
        
        Args:
            query_hash: Hash of the query
            chunks: List of chunk dictionaries to cache
            filters: Optional filters dictionary
            ttl: Time to live in seconds (default: 300)
            
        Returns:
            True if successful, False otherwise
        """
        filters_str = json.dumps(filters, sort_keys=True) if filters else ""
        cache_key = f"retrieval:{query_hash}:{self._hash_key(filters_str)}"
        return await self.set(cache_key, chunks, ttl=ttl)
    
    async def get_response_cache(
        self,
        session_id: str,
        query_hash: str,
        model_version: str,
    ) -> Optional[Any]:
        """
        Get cached response for a session, query, and model version.
        
        Args:
            session_id: Session identifier
            query_hash: Hash of the query
            model_version: Model version string
            
        Returns:
            Cached response or None if not cached
        """
        cache_key = f"response:{session_id}:{query_hash}:{model_version}"
        return await self.get(cache_key)
    
    async def set_response_cache(
        self,
        session_id: str,
        query_hash: str,
        model_version: str,
        response: Any,
        ttl: Optional[int] = None,  # No default TTL for response cache
    ) -> bool:
        """
        Cache response for a session, query, and model version.
        
        Args:
            session_id: Session identifier
            query_hash: Hash of the query
            model_version: Model version string
            response: Response to cache (must be JSON serializable)
            ttl: Time to live in seconds. If None, no expiration.
            
        Returns:
            True if successful, False otherwise
        """
        cache_key = f"response:{session_id}:{query_hash}:{model_version}"
        return await self.set(cache_key, response, ttl=ttl)
    
    async def close(self) -> None:
        """Close Redis connection if it was created by this service."""
        if self._redis_client is not None and self._redis_initialized:
            await self._redis_client.close()
            self._redis_client = None
            self._redis_initialized = False
