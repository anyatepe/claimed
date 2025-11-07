"""
Redis caching and idempotency utilities.

This module provides utilities for caching function results and ensuring
idempotency using Redis.
"""

import json
import hashlib
import logging
import os
from functools import wraps
from typing import Any, Optional, Callable
import redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis connection configuration
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_DB = int(os.environ.get('REDIS_DB', 0))
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', None)

# Default TTL for cached results (in seconds)
DEFAULT_TTL = int(os.environ.get('REDIS_CACHE_TTL', 3600))

# Redis client instance (lazy initialization)
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """
    Get or create a Redis client instance.
    
    Returns:
        redis.Redis: Redis client instance
    """
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            _redis_client.ping()
            logger.info(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis: {e}")
            raise
    return _redis_client


def cache_result(key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
    """
    Cache a value in Redis with a specified TTL.
    
    Args:
        key: The cache key
        value: The value to cache (will be JSON serialized)
        ttl: Time to live in seconds (default: DEFAULT_TTL)
    
    Returns:
        bool: True if caching was successful, False otherwise
    """
    try:
        client = get_redis_client()
        # Serialize value to JSON
        serialized_value = json.dumps(value)
        # Store in Redis with TTL
        result = client.setex(key, ttl, serialized_value)
        logger.debug(f"Cached result for key '{key}' with TTL {ttl}s")
        return result
    except redis.RedisError as e:
        logger.error(f"Redis error caching result for key '{key}': {e}")
        return False
    except (TypeError, ValueError) as e:
        logger.error(f"Serialization error caching result for key '{key}': {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error caching result for key '{key}': {e}")
        return False


def get_cached_result(key: str) -> Optional[Any]:
    """
    Retrieve a cached value from Redis.
    
    Args:
        key: The cache key
    
    Returns:
        The cached value (deserialized from JSON) or None if not found
    """
    try:
        client = get_redis_client()
        cached_value = client.get(key)
        if cached_value is None:
            logger.debug(f"No cached result found for key '{key}'")
            return None
        # Deserialize from JSON
        value = json.loads(cached_value)
        logger.debug(f"Retrieved cached result for key '{key}'")
        return value
    except redis.RedisError as e:
        logger.error(f"Redis error retrieving cached result for key '{key}': {e}")
        return None
    except (TypeError, ValueError) as e:
        logger.error(f"Deserialization error retrieving cached result for key '{key}': {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error retrieving cached result for key '{key}': {e}")
        return None


def ensure_idempotency(idempotency_key: str, ttl: int = DEFAULT_TTL) -> bool:
    """
    Ensure idempotency by checking if a request with the given key has been processed.
    If the key doesn't exist, it will be set to indicate the request is being processed.
    
    Args:
        idempotency_key: Unique key identifying the request
        ttl: Time to live in seconds for the idempotency key (default: DEFAULT_TTL)
    
    Returns:
        bool: True if this is a new request (idempotency key didn't exist),
              False if the request was already processed (idempotency key exists)
    """
    try:
        client = get_redis_client()
        # Use SETNX (SET if Not eXists) to atomically check and set
        # This ensures thread-safe idempotency checking
        result = client.setnx(idempotency_key, "processing")
        if result:
            # Set TTL on the key
            client.expire(idempotency_key, ttl)
            logger.info(f"New idempotency key '{idempotency_key}' - request will be processed")
            return True
        else:
            logger.info(f"Idempotency key '{idempotency_key}' already exists - request already processed")
            return False
    except redis.RedisError as e:
        logger.error(f"Redis error checking idempotency for key '{idempotency_key}': {e}")
        # On Redis error, allow the request to proceed (fail open)
        return True
    except Exception as e:
        logger.error(f"Unexpected error checking idempotency for key '{idempotency_key}': {e}")
        # On unexpected error, allow the request to proceed (fail open)
        return True


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate a cache key from function arguments.
    
    Args:
        prefix: Prefix for the cache key (e.g., function name)
        *args: Positional arguments
        **kwargs: Keyword arguments
    
    Returns:
        str: A unique cache key
    """
    # Create a string representation of arguments
    key_parts = [prefix]
    if args:
        key_parts.append(str(args))
    if kwargs:
        # Sort kwargs for consistent key generation
        sorted_kwargs = sorted(kwargs.items())
        key_parts.append(str(sorted_kwargs))
    
    # Create a hash of the key parts for shorter keys
    key_string = ":".join(key_parts)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()
    return f"{prefix}:{key_hash}"


def cached(ttl: int = DEFAULT_TTL, key_prefix: Optional[str] = None):
    """
    Decorator to cache function results using Redis.
    
    Args:
        ttl: Time to live in seconds for cached results
        key_prefix: Optional prefix for cache keys (defaults to function name)
    
    Example:
        @cached(ttl=3600)
        def expensive_function(arg1, arg2):
            # ... expensive computation ...
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            prefix = key_prefix or func.__name__
            cache_key = generate_cache_key(prefix, *args, **kwargs)
            
            # Try to get cached result
            cached_result = get_cached_result(cache_key)
            if cached_result is not None:
                logger.info(f"Cache hit for function '{func.__name__}' with key '{cache_key}'")
                return cached_result
            
            # Cache miss - execute function
            logger.info(f"Cache miss for function '{func.__name__}' with key '{cache_key}'")
            result = func(*args, **kwargs)
            
            # Cache the result
            cache_result(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator


def idempotent(ttl: int = DEFAULT_TTL, key_prefix: Optional[str] = None):
    """
    Decorator to ensure function idempotency using Redis.
    
    Args:
        ttl: Time to live in seconds for idempotency keys
        key_prefix: Optional prefix for idempotency keys (defaults to function name)
    
    Example:
        @idempotent(ttl=3600)
        def process_request(request_id, data):
            # ... process request ...
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate idempotency key
            prefix = key_prefix or func.__name__
            idempotency_key = generate_cache_key(f"idempotent:{prefix}", *args, **kwargs)
            
            # Check if request was already processed
            is_new_request = ensure_idempotency(idempotency_key, ttl)
            if not is_new_request:
                # Request already processed - return cached result if available
                cache_key = generate_cache_key(prefix, *args, **kwargs)
                cached_result = get_cached_result(cache_key)
                if cached_result is not None:
                    logger.info(f"Idempotent request detected for '{func.__name__}' - returning cached result")
                    return cached_result
                else:
                    # Idempotency key exists but no cached result - this shouldn't happen
                    # but we'll process the request anyway
                    logger.warning(f"Idempotency key exists but no cached result for '{func.__name__}'")
            
            # Process the request
            result = func(*args, **kwargs)
            
            # Cache the result for future idempotent requests
            cache_key = generate_cache_key(prefix, *args, **kwargs)
            cache_result(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator
