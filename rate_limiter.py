"""
Redis Token Bucket Rate Limiter

Implements a token bucket algorithm using Redis for distributed rate limiting.
Supports per-API-key rate limiting with configurable capacity and refill rate.
"""

import time
import redis
from typing import Optional
from dataclasses import dataclass


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    reset_time: float
    capacity: int


class TokenBucketRateLimiter:
    """
    Redis-based token bucket rate limiter.
    
    Uses a Lua script for atomic operations to ensure thread-safety
    and handle concurrent requests correctly.
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        capacity: int,
        refill_rate: float,
        key_prefix: str = "ratelimit:"
    ):
        """
        Initialize the rate limiter.
        
        Args:
            redis_client: Redis client instance
            capacity: Maximum number of tokens in the bucket
            refill_rate: Tokens added per second
            key_prefix: Prefix for Redis keys
        """
        self.redis_client = redis_client
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.key_prefix = key_prefix
        
        # Lua script for atomic token bucket operations
        self.lua_script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local requested = tonumber(ARGV[3])
        local now = tonumber(ARGV[4])
        
        -- Get current bucket state
        local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
        local tokens = tonumber(bucket[1]) or capacity
        local last_refill = tonumber(bucket[2]) or now
        
        -- Calculate time elapsed since last refill
        local elapsed = now - last_refill
        
        -- Refill tokens based on elapsed time
        if elapsed > 0 then
            local tokens_to_add = elapsed * refill_rate
            tokens = math.min(capacity, tokens + tokens_to_add)
        end
        
        -- Check if we have enough tokens
        local allowed = false
        local remaining = tokens
        if tokens >= requested then
            tokens = tokens - requested
            allowed = true
            remaining = tokens
        end
        
        -- Update bucket state
        redis.call('HMSET', key, 'tokens', tokens, 'last_refill', now)
        
        -- Set expiration to clean up old keys (expire after 2x time to fill bucket)
        local ttl = math.ceil((capacity / refill_rate) * 2)
        redis.call('EXPIRE', key, ttl)
        
        -- Calculate reset time (when bucket will be full again)
        local tokens_needed = capacity - tokens
        local reset_time = now
        if tokens_needed > 0 then
            reset_time = now + (tokens_needed / refill_rate)
        end
        
        return {allowed, remaining, reset_time}
        """
        
        # Compile Lua script
        self.script_sha = None
        try:
            self.script_sha = self.redis_client.script_load(self.lua_script)
        except Exception:
            # If script loading fails, we'll use EVAL instead of EVALSHA
            pass
    
    def _get_key(self, api_key: str) -> str:
        """Generate Redis key for the API key."""
        return f"{self.key_prefix}{api_key}"
    
    def check_rate_limit(
        self,
        api_key: str,
        tokens_requested: int = 1
    ) -> RateLimitResult:
        """
        Check if a request should be allowed based on rate limits.
        
        Args:
            api_key: The API key to check rate limits for
            tokens_requested: Number of tokens to consume (default: 1)
            
        Returns:
            RateLimitResult with allowed status, remaining tokens, and reset time
        """
        key = self._get_key(api_key)
        now = time.time()
        
        # Execute Lua script atomically
        try:
            if self.script_sha:
                result = self.redis_client.evalsha(
                    self.script_sha,
                    1,  # numkeys
                    key,
                    self.capacity,
                    self.refill_rate,
                    tokens_requested,
                    now
                )
            else:
                result = self.redis_client.eval(
                    self.lua_script,
                    1,  # numkeys
                    key,
                    self.capacity,
                    self.refill_rate,
                    tokens_requested,
                    now
                )
        except redis.exceptions.NoScriptError:
            # Script not loaded, reload and retry
            self.script_sha = self.redis_client.script_load(self.lua_script)
            result = self.redis_client.evalsha(
                self.script_sha,
                1,
                key,
                self.capacity,
                self.refill_rate,
                tokens_requested,
                now
            )
        
        allowed, remaining, reset_time = result
        
        return RateLimitResult(
            allowed=bool(allowed),
            remaining=int(remaining),
            reset_time=float(reset_time),
            capacity=self.capacity
        )
    
    def get_rate_limit_info(self, api_key: str) -> Optional[RateLimitResult]:
        """
        Get current rate limit information without consuming tokens.
        
        Args:
            api_key: The API key to check
            
        Returns:
            RateLimitResult or None if key doesn't exist
        """
        key = self._get_key(api_key)
        
        bucket = self.redis_client.hmget(key, 'tokens', 'last_refill')
        if bucket[0] is None:
            return None
        
        tokens = float(bucket[0])
        last_refill = float(bucket[1])
        now = time.time()
        
        # Calculate current tokens after refill
        elapsed = now - last_refill
        if elapsed > 0:
            tokens_to_add = elapsed * self.refill_rate
            tokens = min(self.capacity, tokens + tokens_to_add)
        
        # Calculate reset time
        tokens_needed = self.capacity - tokens
        reset_time = now
        if tokens_needed > 0:
            reset_time = now + (tokens_needed / self.refill_rate)
        
        return RateLimitResult(
            allowed=True,  # Info only, doesn't block
            remaining=int(tokens),
            reset_time=reset_time,
            capacity=self.capacity
        )
