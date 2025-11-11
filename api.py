"""
API service with Redis token bucket rate limiting per API key.
"""

import os
import time
from typing import Optional
from fastapi import FastAPI, Request, Response, HTTPException, Header
from fastapi.responses import JSONResponse
import redis
from rate_limiter import TokenBucketRateLimiter, RateLimitResult

app = FastAPI(title="Rate Limited API")

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# Rate limit configuration
RATE_LIMIT_CAPACITY = int(os.getenv("RATE_LIMIT_CAPACITY", "10"))
RATE_LIMIT_REFILL_RATE = float(os.getenv("RATE_LIMIT_REFILL_RATE", "2.0"))  # tokens per second

# Initialize Redis client
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=False  # We need binary for Lua scripts
)

# Initialize rate limiter
rate_limiter = TokenBucketRateLimiter(
    redis_client=redis_client,
    capacity=RATE_LIMIT_CAPACITY,
    refill_rate=RATE_LIMIT_REFILL_RATE
)


def get_api_key(request: Request) -> Optional[str]:
    """
    Extract API key from request headers.
    Checks for 'X-API-Key' or 'Authorization' header.
    """
    # Check X-API-Key header first
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return api_key
    
    # Check Authorization header (Bearer token)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]  # Remove "Bearer " prefix
    
    return None


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """
    Middleware to apply rate limiting per API key.
    Adds X-RateLimit-Remaining and X-RateLimit-Reset headers.
    """
    # Skip rate limiting for health check endpoints
    if request.url.path in ["/health", "/docs", "/openapi.json", "/redoc"]:
        response = await call_next(request)
        return response
    
    # Get API key from request
    api_key = get_api_key(request)
    
    if not api_key:
        return JSONResponse(
            status_code=401,
            content={"error": "API key required. Provide X-API-Key header or Authorization: Bearer <token>"}
        )
    
    # Check rate limit
    rate_limit_result = rate_limiter.check_rate_limit(api_key, tokens_requested=1)
    
    # Add rate limit headers
    response = await call_next(request) if rate_limit_result.allowed else None
    
    if not rate_limit_result.allowed:
        # Rate limit exceeded
        response = JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded",
                "message": f"Rate limit exceeded. Try again after {int(rate_limit_result.reset_time - time.time())} seconds."
            }
        )
    
    # Add rate limit headers to response
    response.headers["X-RateLimit-Remaining"] = str(max(0, rate_limit_result.remaining))
    response.headers["X-RateLimit-Reset"] = str(int(rate_limit_result.reset_time))
    response.headers["X-RateLimit-Limit"] = str(rate_limit_result.capacity)
    
    return response


@app.get("/health")
async def health_check():
    """Health check endpoint (not rate limited)."""
    try:
        # Check Redis connection
        redis_client.ping()
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "redis": "disconnected", "error": str(e)}
        )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Rate Limited API",
        "docs": "/docs",
        "rate_limit": {
            "capacity": RATE_LIMIT_CAPACITY,
            "refill_rate_per_sec": RATE_LIMIT_REFILL_RATE
        }
    }


@app.get("/api/test")
async def test_endpoint(request: Request):
    """Test endpoint that requires API key and is rate limited."""
    api_key = get_api_key(request)
    return {
        "message": "Success",
        "api_key": api_key[:8] + "..." if api_key else None,
        "timestamp": time.time()
    }


@app.get("/api/rate-limit-info")
async def rate_limit_info(request: Request):
    """Get current rate limit information for the API key."""
    api_key = get_api_key(request)
    
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required"
        )
    
    info = rate_limiter.get_rate_limit_info(api_key)
    
    if info is None:
        # No rate limit data yet, return defaults
        return {
            "remaining": RATE_LIMIT_CAPACITY,
            "limit": RATE_LIMIT_CAPACITY,
            "reset_time": int(time.time() + (RATE_LIMIT_CAPACITY / RATE_LIMIT_REFILL_RATE))
        }
    
    return {
        "remaining": info.remaining,
        "limit": info.capacity,
        "reset_time": int(info.reset_time)
    }
