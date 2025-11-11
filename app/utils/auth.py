"""
Authentication and authorization utilities for API protection.

Supports:
- API key authentication via X-API-Key header with Redis lookup
- Token bucket rate limiting
- Optional JWT authentication with tenant claim
"""

import time
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

import redis
from fastapi import HTTPException, Security, Depends, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel


# Configuration
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
JWT_SECRET_KEY = "your-secret-key-change-in-production"  # Should be from env/config
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Rate limiting defaults
DEFAULT_RATE_LIMIT = 100  # requests per window
DEFAULT_WINDOW_SECONDS = 60  # time window in seconds
DEFAULT_BUCKET_SIZE = 100  # token bucket size

# Redis key prefixes
API_KEY_PREFIX = "api_key:"
RATE_LIMIT_PREFIX = "rate_limit:"
TOKEN_BUCKET_PREFIX = "token_bucket:"


class TokenBucket:
    """Token bucket rate limiter implementation."""
    
    def __init__(self, redis_client: redis.Redis, key: str, capacity: int, refill_rate: float):
        """
        Initialize token bucket.
        
        Args:
            redis_client: Redis client instance
            key: Redis key for this bucket
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.redis = redis_client
        self.key = key
        self.capacity = capacity
        self.refill_rate = refill_rate
    
    def consume(self, tokens: int = 1) -> Tuple[bool, Dict[str, Any]]:
        """
        Try to consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            Tuple of (success, rate_limit_info)
        """
        now = time.time()
        
        # Use Lua script for atomic operations
        lua_script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local tokens_requested = tonumber(ARGV[3])
        local now = tonumber(ARGV[4])
        
        local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
        local current_tokens = tonumber(bucket[1]) or capacity
        local last_refill = tonumber(bucket[2]) or now
        
        -- Refill tokens based on time elapsed
        local elapsed = now - last_refill
        local tokens_to_add = math.floor(elapsed * refill_rate)
        current_tokens = math.min(capacity, current_tokens + tokens_to_add)
        
        -- Check if we can consume tokens
        if current_tokens >= tokens_requested then
            current_tokens = current_tokens - tokens_requested
            redis.call('HMSET', key, 'tokens', current_tokens, 'last_refill', now)
            redis.call('EXPIRE', key, 3600)  -- Expire after 1 hour of inactivity
            return {1, current_tokens, capacity}
        else
            redis.call('HMSET', key, 'tokens', current_tokens, 'last_refill', now)
            redis.call('EXPIRE', key, 3600)
            return {0, current_tokens, capacity}
        end
        """
        
        result = self.redis.eval(
            lua_script,
            1,
            self.key,
            self.capacity,
            self.refill_rate,
            tokens,
            now
        )
        
        success = bool(result[0])
        remaining = int(result[1])
        limit = int(result[2])
        
        # Calculate reset time (when bucket will be full)
        if remaining < limit:
            tokens_needed = limit - remaining
            reset_seconds = int(tokens_needed / self.refill_rate) + 1
        else:
            reset_seconds = 0
        
        return success, {
            "limit": limit,
            "remaining": max(0, remaining),
            "reset": int(now) + reset_seconds
        }


class AuthUser(BaseModel):
    """Authenticated user model."""
    api_key: Optional[str] = None
    tenant: Optional[str] = None
    user_id: Optional[str] = None


def get_redis_client() -> redis.Redis:
    """Get Redis client instance."""
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        decode_responses=True
    )


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    redis_client: redis.Redis = Depends(get_redis_client)
) -> Dict[str, Any]:
    """
    Verify API key from X-API-Key header.
    
    Args:
        x_api_key: API key from header
        redis_client: Redis client
        
    Returns:
        API key metadata from Redis
        
    Raises:
        HTTPException: 401 if API key is invalid or missing
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header"
        )
    
    # Lookup API key in Redis
    api_key_data = redis_client.hgetall(f"{API_KEY_PREFIX}{x_api_key}")
    
    if not api_key_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    # Check if API key is active
    if api_key_data.get("active", "true").lower() != "true":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key is inactive"
        )
    
    return {
        "api_key": x_api_key,
        "tenant": api_key_data.get("tenant"),
        "user_id": api_key_data.get("user_id"),
        "rate_limit": int(api_key_data.get("rate_limit", DEFAULT_RATE_LIMIT)),
        "window_seconds": int(api_key_data.get("window_seconds", DEFAULT_WINDOW_SECONDS)),
    }


async def verify_jwt_token(
    credentials: HTTPAuthorizationCredentials = Security(HTTPBearer(auto_error=False))
) -> Optional[Dict[str, Any]]:
    """
    Verify JWT token from Authorization header.
    
    Args:
        credentials: Bearer token credentials
        
    Returns:
        Decoded JWT payload or None if not provided
        
    Raises:
        HTTPException: 401 if JWT is invalid
    """
    if not credentials:
        return None
    
    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired JWT token"
        )


async def check_rate_limit(
    api_key_data: Dict[str, Any] = Depends(verify_api_key),
    redis_client: redis.Redis = Depends(get_redis_client)
) -> AuthUser:
    """
    Check rate limit using token bucket algorithm.
    
    Args:
        api_key_data: API key metadata
        redis_client: Redis client
        
    Returns:
        AuthUser instance
        
    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    api_key = api_key_data["api_key"]
    rate_limit = api_key_data["rate_limit"]
    window_seconds = api_key_data["window_seconds"]
    
    # Calculate refill rate (tokens per second)
    refill_rate = rate_limit / window_seconds
    
    # Create token bucket
    bucket_key = f"{TOKEN_BUCKET_PREFIX}{api_key}"
    bucket = TokenBucket(
        redis_client=redis_client,
        key=bucket_key,
        capacity=rate_limit,
        refill_rate=refill_rate
    )
    
    # Try to consume a token
    success, rate_limit_info = bucket.consume(1)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(rate_limit_info["limit"]),
                "X-RateLimit-Remaining": str(rate_limit_info["remaining"]),
                "X-RateLimit-Reset": str(rate_limit_info["reset"])
            }
        )
    
    return AuthUser(
        api_key=api_key,
        tenant=api_key_data.get("tenant"),
        user_id=api_key_data.get("user_id")
    )


async def authenticate_user(
    api_key_user: Optional[AuthUser] = Depends(check_rate_limit),
    jwt_payload: Optional[Dict[str, Any]] = Depends(verify_jwt_token)
) -> AuthUser:
    """
    Authenticate user via API key (required) or JWT (optional).
    
    API key is required and provides base authentication.
    JWT is optional and can override tenant claim.
    
    Args:
        api_key_user: User authenticated via API key
        jwt_payload: Optional JWT payload
        
    Returns:
        AuthUser with tenant from JWT if provided, otherwise from API key
    """
    if not api_key_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # If JWT is provided, use tenant from JWT (JWT takes precedence)
    if jwt_payload and "tenant" in jwt_payload:
        api_key_user.tenant = jwt_payload["tenant"]
    
    return api_key_user


async def get_current_user(
    user: AuthUser = Depends(authenticate_user)
) -> AuthUser:
    """
    Dependency for getting current authenticated user.
    
    This is the main dependency to use in route handlers.
    """
    return user


def require_tenant(tenant: str):
    """
    Create a dependency that requires a specific tenant.
    
    Usage:
        @router.get("/tenant/{tenant_name}")
        async def endpoint(
            tenant_name: str,
            user: AuthUser = Depends(require_tenant(tenant_name))
        ):
            ...
    
    Args:
        tenant: Required tenant name
        
    Returns:
        Dependency function
    """
    async def check_tenant(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.tenant != tenant:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied for tenant: {tenant}"
            )
        return user
    
    return check_tenant


def create_jwt_token(tenant: str, user_id: Optional[str] = None, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT token with tenant claim.
    
    Args:
        tenant: Tenant identifier
        user_id: Optional user ID
        expires_delta: Optional expiration time delta
        
    Returns:
        Encoded JWT token
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    
    payload = {
        "tenant": tenant,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    if user_id:
        payload["sub"] = user_id
    
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
