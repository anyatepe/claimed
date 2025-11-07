# Redis Caching and Idempotency Implementation

This implementation provides Redis-based caching and idempotency for summarize and classify functions.

## Files

- `redis_cache.py` - Core Redis caching utilities
- `nlp_service.py` - Summarize and classify functions with caching decorators
- `test_redis_cache.py` - Comprehensive unit tests
- `example_usage.py` - Example usage demonstrations
- `requirements.txt` - Python dependencies

## Features

### 1. Core Utility Functions

#### `cache_result(key, value, ttl)`
Caches a value in Redis with a specified time-to-live (TTL).

```python
from redis_cache import cache_result

cache_result("my_key", {"data": "value"}, ttl=3600)
```

#### `get_cached_result(key)`
Retrieves a cached value from Redis.

```python
from redis_cache import get_cached_result

cached_value = get_cached_result("my_key")
```

#### `ensure_idempotency(idempotency_key, ttl)`
Ensures idempotency by checking if a request has been processed.

```python
from redis_cache import ensure_idempotency

is_new = ensure_idempotency("request_123", ttl=3600)
if is_new:
    # Process request
    pass
```

### 2. Decorators

#### `@cached(ttl=3600, key_prefix=None)`
Decorator to automatically cache function results.

```python
from redis_cache import cached

@cached(ttl=3600)
def expensive_function(x, y):
    return x + y
```

#### `@idempotent(ttl=3600, key_prefix=None)`
Decorator to ensure function idempotency.

```python
from redis_cache import idempotent

@idempotent(ttl=3600)
def process_request(request_id, data):
    # Process request
    return result
```

### 3. NLP Service Functions

#### `summarize(text, max_length=100, min_length=30)`
Summarizes text with automatic caching and idempotency.

```python
from nlp_service import summarize

result = summarize("Long text here...", max_length=100)
# Duplicate calls with same parameters return cached results
```

#### `classify(text, categories=None)`
Classifies text with automatic caching and idempotency.

```python
from nlp_service import classify

result = classify("Text to classify")
# Duplicate calls with same parameters return cached results
```

## Configuration

Set environment variables to configure Redis connection:

```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
export REDIS_DB=0
export REDIS_PASSWORD=  # Optional
export REDIS_CACHE_TTL=3600  # Default TTL in seconds
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start Redis (if not already running):
```bash
docker run -d -p 6379:6379 redis
```

## Running Tests

```bash
pytest test_redis_cache.py -v
```

## Running Examples

```bash
python example_usage.py
```

## How It Works

### Caching Flow

1. Function is called with parameters
2. Cache key is generated from function name and parameters
3. Check Redis for cached result
4. If found (cache hit), return cached result
5. If not found (cache miss), execute function and cache result

### Idempotency Flow

1. Function is called with parameters
2. Idempotency key is generated from function name and parameters
3. Check Redis if idempotency key exists (using SETNX for atomicity)
4. If key doesn't exist (new request):
   - Set idempotency key
   - Execute function
   - Cache result
5. If key exists (duplicate request):
   - Return cached result if available
   - Otherwise process request (shouldn't happen in normal flow)

## Benefits

1. **Performance**: Cached results are returned instantly without recomputation
2. **Idempotency**: Duplicate requests are safely handled without side effects
3. **Cost Reduction**: Reduces computational load and API costs
4. **Reliability**: Fail-open design ensures service continues even if Redis is unavailable

## Error Handling

- Redis connection errors are logged but don't crash the application
- Idempotency checks fail open (allow requests to proceed) on Redis errors
- Serialization errors are caught and logged
- All errors are logged for debugging

## Testing

The test suite includes:
- Unit tests for all utility functions
- Tests for cache hit/miss scenarios
- Tests for idempotency enforcement
- Tests for duplicate request handling
- Integration tests for end-to-end flows

All tests use mocks to avoid requiring a running Redis instance.
