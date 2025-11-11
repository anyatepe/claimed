"""
Example usage of the Redis token bucket rate limiter.
"""

import redis
from rate_limiter import TokenBucketRateLimiter
import time

# Create Redis client
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=False
)

# Create rate limiter with capacity=10, refill_rate=2 tokens/second
rate_limiter = TokenBucketRateLimiter(
    redis_client=redis_client,
    capacity=10,
    refill_rate=2.0
)

# Example 1: Basic usage
print("Example 1: Basic usage")
api_key = "example_api_key_1"

for i in range(12):
    result = rate_limiter.check_rate_limit(api_key)
    if result.allowed:
        print(f"Request {i+1}: Allowed - {result.remaining} tokens remaining")
    else:
        print(f"Request {i+1}: Rate limited - Reset at {result.reset_time}")

print("\n" + "="*50 + "\n")

# Example 2: Different API keys are independent
print("Example 2: Different API keys are independent")
api_key_1 = "example_api_key_2"
api_key_2 = "example_api_key_3"

# Consume all tokens for key 1
for i in range(10):
    result = rate_limiter.check_rate_limit(api_key_1)
    print(f"Key 1, Request {i+1}: {'Allowed' if result.allowed else 'Denied'}")

# Key 2 should still have all tokens
result = rate_limiter.check_rate_limit(api_key_2)
print(f"\nKey 2, Request 1: {'Allowed' if result.allowed else 'Denied'} - {result.remaining} tokens remaining")

print("\n" + "="*50 + "\n")

# Example 3: Token refill over time
print("Example 3: Token refill over time")
api_key_3 = "example_api_key_4"

# Consume all tokens
for i in range(10):
    rate_limiter.check_rate_limit(api_key_3)

print("All tokens consumed. Waiting for refill...")
time.sleep(1.0)  # Wait 1 second (should refill ~2 tokens)

result = rate_limiter.check_rate_limit(api_key_3)
if result.allowed:
    print(f"After 1 second: {result.remaining} tokens available")
else:
    print("Still rate limited")

print("\n" + "="*50 + "\n")

# Example 4: Get rate limit info without consuming tokens
print("Example 4: Get rate limit info without consuming")
api_key_4 = "example_api_key_5"

# Make some requests
for i in range(3):
    rate_limiter.check_rate_limit(api_key_4)

# Get info without consuming
info = rate_limiter.get_rate_limit_info(api_key_4)
if info:
    print(f"Current tokens: {info.remaining}")
    print(f"Capacity: {info.capacity}")
    print(f"Reset time: {info.reset_time}")
