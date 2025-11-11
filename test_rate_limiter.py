"""
Tests for Redis token bucket rate limiter.
Includes tests for concurrent requests.
"""

import pytest
import redis
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from rate_limiter import TokenBucketRateLimiter, RateLimitResult


@pytest.fixture
def redis_client():
    """Create a Redis client for testing."""
    client = redis.Redis(
        host="localhost",
        port=6379,
        db=15,  # Use a separate DB for testing
        decode_responses=False
    )
    
    # Clear test database
    client.flushdb()
    
    yield client
    
    # Cleanup
    client.flushdb()
    client.close()


@pytest.fixture
def rate_limiter(redis_client):
    """Create a rate limiter instance for testing."""
    return TokenBucketRateLimiter(
        redis_client=redis_client,
        capacity=10,
        refill_rate=2.0,  # 2 tokens per second
        key_prefix="test:ratelimit:"
    )


class TestTokenBucketRateLimiter:
    """Test cases for TokenBucketRateLimiter."""
    
    def test_initial_request_allowed(self, rate_limiter):
        """Test that initial request is allowed."""
        result = rate_limiter.check_rate_limit("test_key_1")
        assert result.allowed is True
        assert result.remaining == 9  # 10 - 1
        assert result.capacity == 10
    
    def test_multiple_requests_consume_tokens(self, rate_limiter):
        """Test that multiple requests consume tokens correctly."""
        api_key = "test_key_2"
        
        # Make 5 requests
        for i in range(5):
            result = rate_limiter.check_rate_limit(api_key)
            assert result.allowed is True
            assert result.remaining == 10 - (i + 1)
    
    def test_rate_limit_exceeded(self, rate_limiter):
        """Test that rate limit is exceeded when capacity is reached."""
        api_key = "test_key_3"
        
        # Consume all tokens
        for i in range(10):
            result = rate_limiter.check_rate_limit(api_key)
            assert result.allowed is True
        
        # Next request should be denied
        result = rate_limiter.check_rate_limit(api_key)
        assert result.allowed is False
        assert result.remaining == 0
    
    def test_token_refill(self, rate_limiter):
        """Test that tokens are refilled over time."""
        api_key = "test_key_4"
        
        # Consume all tokens
        for _ in range(10):
            rate_limiter.check_rate_limit(api_key)
        
        # Wait for refill (0.6 seconds should add ~1.2 tokens, so 1 token)
        time.sleep(0.6)
        
        result = rate_limiter.check_rate_limit(api_key)
        assert result.allowed is True
        assert result.remaining >= 0  # Should have at least 1 token
    
    def test_different_api_keys_independent(self, rate_limiter):
        """Test that different API keys have independent rate limits."""
        api_key_1 = "test_key_5"
        api_key_2 = "test_key_6"
        
        # Consume all tokens for key 1
        for _ in range(10):
            result = rate_limiter.check_rate_limit(api_key_1)
            assert result.allowed is True
        
        # Key 2 should still have all tokens
        result = rate_limiter.check_rate_limit(api_key_2)
        assert result.allowed is True
        assert result.remaining == 9
    
    def test_reset_time_calculation(self, rate_limiter):
        """Test that reset time is calculated correctly."""
        api_key = "test_key_7"
        
        # Consume all tokens
        for _ in range(10):
            rate_limiter.check_rate_limit(api_key)
        
        result = rate_limiter.check_rate_limit(api_key)
        assert result.allowed is False
        
        # Reset time should be approximately capacity / refill_rate seconds in the future
        expected_reset = time.time() + (10 / 2.0)  # 5 seconds
        assert abs(result.reset_time - expected_reset) < 1.0  # Allow 1 second tolerance
    
    def test_get_rate_limit_info(self, rate_limiter):
        """Test getting rate limit info without consuming tokens."""
        api_key = "test_key_8"
        
        # Make some requests
        for _ in range(3):
            rate_limiter.check_rate_limit(api_key)
        
        # Get info without consuming
        info = rate_limiter.get_rate_limit_info(api_key)
        assert info is not None
        assert info.remaining == 7
        assert info.allowed is True
        
        # Make another request and verify info updates
        rate_limiter.check_rate_limit(api_key)
        info = rate_limiter.get_rate_limit_info(api_key)
        assert info.remaining == 6


class TestConcurrentRequests:
    """Test concurrent requests to ensure thread-safety."""
    
    def test_concurrent_requests_same_key(self, rate_limiter):
        """Test that concurrent requests for the same key are handled correctly."""
        api_key = "concurrent_key_1"
        capacity = 10
        num_requests = 20  # More than capacity
        
        def make_request():
            return rate_limiter.check_rate_limit(api_key)
        
        # Make concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            results = [future.result() for future in as_completed(futures)]
        
        # Count allowed and denied requests
        allowed_count = sum(1 for r in results if r.allowed)
        denied_count = sum(1 for r in results if r.allowed is False)
        
        # Should have exactly capacity allowed requests
        assert allowed_count == capacity
        assert denied_count == num_requests - capacity
        
        # Verify remaining tokens
        final_result = rate_limiter.check_rate_limit(api_key)
        assert final_result.allowed is False
        assert final_result.remaining == 0
    
    def test_concurrent_requests_different_keys(self, rate_limiter):
        """Test that concurrent requests for different keys work independently."""
        num_keys = 5
        requests_per_key = 10
        capacity = 10
        
        def make_requests_for_key(key_id):
            api_key = f"concurrent_key_{key_id}"
            results = []
            for _ in range(requests_per_key):
                result = rate_limiter.check_rate_limit(api_key)
                results.append(result)
            return results
        
        # Make concurrent requests for different keys
        with ThreadPoolExecutor(max_workers=num_keys) as executor:
            futures = [
                executor.submit(make_requests_for_key, i)
                for i in range(num_keys)
            ]
            all_results = [future.result() for future in as_completed(futures)]
        
        # All requests should be allowed (each key has its own bucket)
        for key_results in all_results:
            assert all(r.allowed for r in key_results)
            # Each key should have consumed all its tokens
            final_key = f"concurrent_key_{all_results.index(key_results)}"
            final_result = rate_limiter.check_rate_limit(final_key)
            assert final_result.allowed is False
    
    def test_concurrent_requests_with_refill(self, rate_limiter):
        """Test concurrent requests with token refill over time."""
        api_key = "concurrent_refill_key"
        capacity = 10
        
        # Consume all tokens
        for _ in range(capacity):
            rate_limiter.check_rate_limit(api_key)
        
        # Wait for some refill
        time.sleep(1.0)  # Should refill ~2 tokens
        
        # Make concurrent requests
        num_requests = 5
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(rate_limiter.check_rate_limit, api_key)
                for _ in range(num_requests)
            ]
            results = [future.result() for future in as_completed(futures)]
        
        # Some requests should be allowed due to refill
        allowed_count = sum(1 for r in results if r.allowed)
        assert allowed_count >= 1  # At least some tokens should have refilled
    
    def test_high_concurrency_stress_test(self, rate_limiter):
        """Stress test with high concurrency."""
        api_key = "stress_test_key"
        capacity = 100
        num_requests = 200
        
        # Create a new rate limiter with higher capacity for stress test
        stress_limiter = TokenBucketRateLimiter(
            redis_client=rate_limiter.redis_client,
            capacity=capacity,
            refill_rate=10.0,
            key_prefix="test:ratelimit:"
        )
        
        def make_request():
            return stress_limiter.check_rate_limit(api_key)
        
        # Make many concurrent requests
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            results = [future.result() for future in as_completed(futures)]
        
        # Verify exactly capacity requests were allowed
        allowed_count = sum(1 for r in results if r.allowed)
        assert allowed_count == capacity
        
        # Verify remaining is 0
        final_result = stress_limiter.check_rate_limit(api_key)
        assert final_result.allowed is False
        assert final_result.remaining == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
