"""
Integration tests for the API service with rate limiting.
Tests concurrent requests to ensure rate limiting works correctly.
"""

import pytest
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from fastapi.testclient import TestClient
import redis
from api import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture(scope="function")
def clean_redis():
    """Clean Redis before and after each test."""
    # Use a separate DB for testing
    test_redis = redis.Redis(
        host="localhost",
        port=6379,
        db=15,
        decode_responses=False
    )
    test_redis.flushdb()
    yield test_redis
    test_redis.flushdb()
    test_redis.close()


class TestAPIRateLimiting:
    """Test API rate limiting functionality."""
    
    def test_health_check_no_rate_limit(self, client):
        """Test that health check endpoint is not rate limited."""
        for _ in range(20):
            response = client.get("/health")
            assert response.status_code == 200
    
    def test_missing_api_key(self, client):
        """Test that requests without API key are rejected."""
        response = client.get("/api/test")
        assert response.status_code == 401
        assert "API key required" in response.json()["error"]
    
    def test_rate_limit_headers_present(self, client):
        """Test that rate limit headers are present in responses."""
        api_key = "test_key_headers"
        headers = {"X-API-Key": api_key}
        
        response = client.get("/api/test", headers=headers)
        assert response.status_code == 200
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        assert "X-RateLimit-Limit" in response.headers
    
    def test_rate_limit_headers_values(self, client):
        """Test that rate limit headers have correct values."""
        api_key = "test_key_values"
        headers = {"X-API-Key": api_key}
        
        # Make a request
        response = client.get("/api/test", headers=headers)
        assert response.status_code == 200
        
        remaining = int(response.headers["X-RateLimit-Remaining"])
        limit = int(response.headers["X-RateLimit-Limit"])
        reset = int(response.headers["X-RateLimit-Reset"])
        
        assert remaining >= 0
        assert remaining < limit
        assert reset > time.time()
    
    def test_rate_limit_exceeded_response(self, client):
        """Test that rate limit exceeded returns 429 status."""
        api_key = "test_key_exceeded"
        headers = {"X-API-Key": api_key}
        
        # Consume all tokens
        for _ in range(10):
            response = client.get("/api/test", headers=headers)
            assert response.status_code == 200
        
        # Next request should be rate limited
        response = client.get("/api/test", headers=headers)
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["error"]
        assert int(response.headers["X-RateLimit-Remaining"]) == 0
    
    def test_different_api_keys_independent(self, client):
        """Test that different API keys have independent rate limits."""
        api_key_1 = "test_key_indep_1"
        api_key_2 = "test_key_indep_2"
        
        # Consume all tokens for key 1
        for _ in range(10):
            response = client.get("/api/test", headers={"X-API-Key": api_key_1})
            assert response.status_code == 200
        
        # Key 2 should still work
        response = client.get("/api/test", headers={"X-API-Key": api_key_2})
        assert response.status_code == 200
        assert int(response.headers["X-RateLimit-Remaining"]) == 9
    
    def test_bearer_token_auth(self, client):
        """Test that Bearer token authentication works."""
        api_key = "test_bearer_token"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        response = client.get("/api/test", headers=headers)
        assert response.status_code == 200
    
    def test_rate_limit_info_endpoint(self, client):
        """Test the rate limit info endpoint."""
        api_key = "test_key_info"
        headers = {"X-API-Key": api_key}
        
        # Make some requests
        for _ in range(3):
            client.get("/api/test", headers=headers)
        
        # Get rate limit info
        response = client.get("/api/rate-limit-info", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "remaining" in data
        assert "limit" in data
        assert "reset_time" in data
        assert data["remaining"] == 7


class TestConcurrentAPIRequests:
    """Test concurrent API requests to ensure rate limiting works correctly."""
    
    def test_concurrent_requests_same_key(self, client):
        """Test concurrent requests for the same API key."""
        api_key = "concurrent_api_key_1"
        headers = {"X-API-Key": api_key}
        num_requests = 20
        
        def make_request():
            return client.get("/api/test", headers=headers)
        
        # Make concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            responses = [future.result() for future in as_completed(futures)]
        
        # Count successful and rate limited responses
        success_count = sum(1 for r in responses if r.status_code == 200)
        rate_limited_count = sum(1 for r in responses if r.status_code == 429)
        
        # Should have exactly 10 successful requests (capacity)
        assert success_count == 10
        assert rate_limited_count == 10
        
        # Verify headers on rate limited responses
        for response in responses:
            if response.status_code == 429:
                assert int(response.headers["X-RateLimit-Remaining"]) == 0
                assert "X-RateLimit-Reset" in response.headers
    
    def test_concurrent_requests_different_keys(self, client):
        """Test concurrent requests for different API keys."""
        num_keys = 5
        requests_per_key = 10
        
        def make_requests_for_key(key_id):
            api_key = f"concurrent_api_key_{key_id}"
            headers = {"X-API-Key": api_key}
            responses = []
            for _ in range(requests_per_key):
                response = client.get("/api/test", headers=headers)
                responses.append(response)
            return responses
        
        # Make concurrent requests for different keys
        with ThreadPoolExecutor(max_workers=num_keys) as executor:
            futures = [
                executor.submit(make_requests_for_key, i)
                for i in range(num_keys)
            ]
            all_responses = [future.result() for future in as_completed(futures)]
        
        # All requests should be successful (each key has its own bucket)
        for key_responses in all_responses:
            assert all(r.status_code == 200 for r in key_responses)
    
    def test_concurrent_requests_with_delays(self, client):
        """Test concurrent requests with delays to test refill."""
        api_key = "concurrent_delayed_key"
        headers = {"X-API-Key": api_key}
        
        # Consume all tokens
        for _ in range(10):
            client.get("/api/test", headers=headers)
        
        # Wait for refill
        time.sleep(1.0)
        
        # Make concurrent requests
        num_requests = 5
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(client.get, "/api/test", headers=headers)
                for _ in range(num_requests)
            ]
            responses = [future.result() for future in as_completed(futures)]
        
        # Some requests should succeed due to refill
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count >= 1
    
    def test_high_concurrency_stress(self, client):
        """Stress test with high concurrency."""
        api_key = "stress_test_api_key"
        headers = {"X-API-Key": api_key}
        num_requests = 50
        
        def make_request():
            return client.get("/api/test", headers=headers)
        
        # Make many concurrent requests
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            responses = [future.result() for future in as_completed(futures)]
        
        # Verify exactly 10 requests succeeded (capacity)
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count == 10
        
        # Verify all rate limited responses have correct headers
        rate_limited = [r for r in responses if r.status_code == 429]
        for response in rate_limited:
            assert int(response.headers["X-RateLimit-Remaining"]) == 0
            reset_time = int(response.headers["X-RateLimit-Reset"])
            assert reset_time > time.time()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
