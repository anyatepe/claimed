# Redis Token Bucket Rate Limiter

A Redis-based token bucket rate limiting implementation with per-API-key rate limiting support.

## Features

- **Token Bucket Algorithm**: Implements a token bucket algorithm using Redis for distributed rate limiting
- **Per-API-Key Rate Limiting**: Each API key has its own independent rate limit bucket
- **Configurable Parameters**: 
  - `capacity`: Maximum number of tokens in the bucket
  - `refill_rate`: Tokens added per second
- **Rate Limit Headers**: Returns standard rate limit headers:
  - `X-RateLimit-Remaining`: Number of tokens remaining
  - `X-RateLimit-Reset`: Unix timestamp when the bucket will be full again
  - `X-RateLimit-Limit`: Maximum capacity of the bucket
- **Thread-Safe**: Uses Redis Lua scripts for atomic operations, ensuring correct behavior under concurrent load
- **Concurrent Request Support**: Tested with high concurrency to ensure thread-safety

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure Redis is running:
```bash
redis-server
```

Or use Docker:
```bash
docker run -d -p 6379:6379 redis:latest
```

## Usage

### Basic Rate Limiter

```python
import redis
from rate_limiter import TokenBucketRateLimiter

# Create Redis client
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=False)

# Create rate limiter with capacity=10, refill_rate=2 tokens/second
rate_limiter = TokenBucketRateLimiter(
    redis_client=redis_client,
    capacity=10,
    refill_rate=2.0
)

# Check rate limit for an API key
result = rate_limiter.check_rate_limit("api_key_123")

if result.allowed:
    print(f"Request allowed. {result.remaining} tokens remaining.")
    print(f"Bucket will be full at: {result.reset_time}")
else:
    print("Rate limit exceeded!")
```

### API Service

Run the FastAPI service:

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

Or with custom Redis settings:

```bash
REDIS_HOST=localhost REDIS_PORT=6379 RATE_LIMIT_CAPACITY=10 RATE_LIMIT_REFILL_RATE=2.0 uvicorn api:app --host 0.0.0.0 --port 8000
```

#### API Endpoints

- `GET /`: Root endpoint with API information
- `GET /health`: Health check (not rate limited)
- `GET /api/test`: Test endpoint (rate limited)
- `GET /api/rate-limit-info`: Get current rate limit information for your API key

#### Authentication

Provide API key via one of these methods:

1. `X-API-Key` header:
```bash
curl -H "X-API-Key: your_api_key" http://localhost:8000/api/test
```

2. `Authorization: Bearer <token>` header:
```bash
curl -H "Authorization: Bearer your_api_key" http://localhost:8000/api/test
```

#### Example Requests

```bash
# Make a request
curl -H "X-API-Key: test_key" http://localhost:8000/api/test

# Check rate limit info
curl -H "X-API-Key: test_key" http://localhost:8000/api/rate-limit-info

# Health check (no API key needed)
curl http://localhost:8000/health
```

## Configuration

### Environment Variables

- `REDIS_HOST`: Redis host (default: `localhost`)
- `REDIS_PORT`: Redis port (default: `6379`)
- `REDIS_DB`: Redis database number (default: `0`)
- `RATE_LIMIT_CAPACITY`: Maximum tokens per bucket (default: `10`)
- `RATE_LIMIT_REFILL_RATE`: Tokens per second refill rate (default: `2.0`)

## Testing

Run the rate limiter unit tests:

```bash
pytest test_rate_limiter.py -v
```

Run the API integration tests:

```bash
pytest test_api.py -v
```

Run all tests:

```bash
pytest -v
```

### Test Coverage

The tests include:

1. **Basic Functionality**:
   - Initial request allowed
   - Multiple requests consume tokens
   - Rate limit exceeded when capacity reached
   - Token refill over time
   - Different API keys are independent

2. **Concurrent Requests**:
   - Concurrent requests for the same API key
   - Concurrent requests for different API keys
   - Concurrent requests with token refill
   - High concurrency stress tests

## How It Works

The token bucket algorithm works as follows:

1. Each API key has a bucket with a maximum capacity of tokens
2. Each request consumes one token (configurable)
3. Tokens are refilled at a constant rate (tokens per second)
4. If tokens are available, the request is allowed
5. If no tokens are available, the request is denied (HTTP 429)

The implementation uses Redis Lua scripts to ensure atomic operations, making it safe for concurrent requests across multiple processes or servers.

## Rate Limit Headers

The API returns the following headers:

- `X-RateLimit-Remaining`: Number of tokens remaining in the bucket
- `X-RateLimit-Reset`: Unix timestamp (seconds) when the bucket will be full again
- `X-RateLimit-Limit`: Maximum capacity of the bucket

## Architecture

- `rate_limiter.py`: Core token bucket rate limiter implementation
- `api.py`: FastAPI service with rate limiting middleware
- `test_rate_limiter.py`: Unit tests for the rate limiter
- `test_api.py`: Integration tests for the API service

## License

See LICENSE file for details.
