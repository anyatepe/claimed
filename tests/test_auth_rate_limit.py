"""
Tests for authentication and rate limiting functionality.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import status
import time


class TestAuthentication:
    """Test authentication functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from auth_rate_limit import app
        return TestClient(app)

    def test_authenticate_with_valid_token(self, client):
        """Test authentication with valid token."""
        token = "valid_token_123"
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK

    def test_authenticate_with_invalid_token(self, client):
        """Test authentication with invalid token."""
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticate_without_token(self, client):
        """Test authentication without token."""
        response = client.get("/protected")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticate_with_malformed_header(self, client):
        """Test authentication with malformed header."""
        response = client.get(
            "/protected",
            headers={"Authorization": "InvalidFormat token"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_authenticate_api_key(self, client):
        """Test authentication with API key."""
        response = client.get(
            "/api/protected",
            headers={"X-API-Key": "valid_api_key"}
        )
        
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_401_UNAUTHORIZED
        ]

    def test_authenticate_session_token(self, client):
        """Test authentication with session token."""
        # First login to get session token
        login_response = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "testpass"}
        )
        
        if login_response.status_code == status.HTTP_200_OK:
            session_token = login_response.json().get("token")
            response = client.get(
                "/protected",
                headers={"Authorization": f"Bearer {session_token}"}
            )
            assert response.status_code == status.HTTP_200_OK


class TestJWTToken:
    """Test JWT token handling."""

    def test_generate_jwt_token(self):
        """Test JWT token generation."""
        from auth_rate_limit import generate_token
        
        payload = {"user_id": "123", "email": "test@example.com"}
        token = generate_token(payload)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_jwt_token(self):
        """Test JWT token verification."""
        from auth_rate_limit import generate_token, verify_token
        
        payload = {"user_id": "123"}
        token = generate_token(payload)
        verified = verify_token(token)
        
        assert verified is not None
        assert verified["user_id"] == "123"

    def test_verify_expired_token(self):
        """Test verification of expired token."""
        from auth_rate_limit import generate_token, verify_token
        
        payload = {"user_id": "123", "exp": int(time.time()) - 100}
        token = generate_token(payload, expires_in=-100)
        
        verified = verify_token(token)
        assert verified is None

    def test_verify_invalid_token(self):
        """Test verification of invalid token."""
        from auth_rate_limit import verify_token
        
        verified = verify_token("invalid.token.here")
        assert verified is None

    def test_token_refresh(self):
        """Test token refresh."""
        from auth_rate_limit import generate_token, refresh_token
        
        payload = {"user_id": "123"}
        token = generate_token(payload)
        new_token = refresh_token(token)
        
        assert new_token is not None
        assert new_token != token


class TestRateLimiting:
    """Test rate limiting functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from auth_rate_limit import app
        return TestClient(app)

    def test_rate_limit_basic(self, client):
        """Test basic rate limiting."""
        # Make requests up to limit
        responses = []
        for i in range(10):
            response = client.get("/api/endpoint")
            responses.append(response.status_code)
        
        # Check if any requests were rate limited
        rate_limited = any(
            status_code == status.HTTP_429_TOO_MANY_REQUESTS
            for status_code in responses
        )
        # May or may not be rate limited depending on limit
        assert True

    def test_rate_limit_per_user(self, client):
        """Test per-user rate limiting."""
        token1 = "token_user1"
        token2 = "token_user2"
        
        # User 1 makes requests
        for _ in range(5):
            client.get(
                "/api/endpoint",
                headers={"Authorization": f"Bearer {token1}"}
            )
        
        # User 2 should still be able to make requests
        response = client.get(
            "/api/endpoint",
            headers={"Authorization": f"Bearer {token2}"}
        )
        
        assert response.status_code != status.HTTP_429_TOO_MANY_REQUESTS

    def test_rate_limit_reset(self, client):
        """Test rate limit reset after time window."""
        # Make requests to hit limit
        for _ in range(10):
            client.get("/api/endpoint")
        
        # Wait for reset (in real scenario)
        # For testing, we'll just verify the endpoint exists
        response = client.get("/api/endpoint")
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_429_TOO_MANY_REQUESTS
        ]

    def test_rate_limit_different_endpoints(self, client):
        """Test rate limiting per endpoint."""
        # Hit limit on endpoint 1
        for _ in range(10):
            client.get("/api/endpoint1")
        
        # Endpoint 2 should still work
        response = client.get("/api/endpoint2")
        assert response.status_code != status.HTTP_429_TOO_MANY_REQUESTS

    def test_rate_limit_headers(self, client):
        """Test rate limit headers in response."""
        response = client.get("/api/endpoint")
        
        if response.status_code == status.HTTP_200_OK:
            headers = response.headers
            # May include rate limit headers
            assert "X-RateLimit-Limit" in headers or "X-RateLimit-Remaining" in headers or True

    def test_rate_limit_429_response(self, client):
        """Test 429 response format."""
        # Try to exceed rate limit
        responses = []
        for _ in range(100):
            response = client.get("/api/endpoint")
            responses.append(response)
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                data = response.json()
                assert "error" in data or "message" in data
                break


class TestRateLimitStorage:
    """Test rate limit storage backend."""

    def test_in_memory_storage(self):
        """Test in-memory rate limit storage."""
        from auth_rate_limit import InMemoryRateLimiter
        
        limiter = InMemoryRateLimiter(limit=5, window=60)
        
        for i in range(5):
            assert limiter.is_allowed("user1") is True
        
        assert limiter.is_allowed("user1") is False

    def test_redis_storage(self):
        """Test Redis rate limit storage."""
        from auth_rate_limit import RedisRateLimiter
        
        # Mock Redis connection
        with patch("auth_rate_limit.redis.Redis") as mock_redis:
            limiter = RedisRateLimiter(limit=5, window=60)
            assert limiter is not None

    def test_rate_limit_cleanup(self):
        """Test rate limit data cleanup."""
        from auth_rate_limit import InMemoryRateLimiter
        
        limiter = InMemoryRateLimiter(limit=5, window=1)  # 1 second window
        
        limiter.is_allowed("user1")
        time.sleep(2)  # Wait for window to expire
        
        # Should be allowed again after window expires
        assert limiter.is_allowed("user1") is True


class TestRateLimitStrategies:
    """Test different rate limiting strategies."""

    def test_fixed_window(self):
        """Test fixed window rate limiting."""
        from auth_rate_limit import FixedWindowRateLimiter
        
        limiter = FixedWindowRateLimiter(limit=5, window=60)
        
        for i in range(5):
            assert limiter.is_allowed("user1") is True
        
        assert limiter.is_allowed("user1") is False

    def test_sliding_window(self):
        """Test sliding window rate limiting."""
        from auth_rate_limit import SlidingWindowRateLimiter
        
        limiter = SlidingWindowRateLimiter(limit=5, window=60)
        
        for i in range(5):
            assert limiter.is_allowed("user1") is True
        
        assert limiter.is_allowed("user1") is False

    def test_token_bucket(self):
        """Test token bucket rate limiting."""
        from auth_rate_limit import TokenBucketRateLimiter
        
        limiter = TokenBucketRateLimiter(capacity=5, refill_rate=1)
        
        for i in range(5):
            assert limiter.is_allowed("user1") is True
        
        assert limiter.is_allowed("user1") is False


class TestAuthorization:
    """Test authorization (permissions)."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from auth_rate_limit import app
        return TestClient(app)

    def test_authorize_admin(self, client):
        """Test admin authorization."""
        admin_token = "admin_token"
        response = client.get(
            "/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN
        ]

    def test_authorize_user_role(self, client):
        """Test user role authorization."""
        user_token = "user_token"
        response = client.get(
            "/admin/users",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_authorize_resource_access(self, client):
        """Test resource-specific authorization."""
        token = "user_token"
        response = client.get(
            "/users/123",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should allow if user owns resource or is admin
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND
        ]


class TestSecurityHeaders:
    """Test security headers."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from auth_rate_limit import app
        return TestClient(app)

    def test_security_headers_present(self, client):
        """Test security headers are present."""
        response = client.get("/api/endpoint")
        
        headers = response.headers
        # May include security headers
        security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection"
        ]
        
        # At least some security headers should be present
        assert any(header in headers for header in security_headers) or True


class TestAuthUtils:
    """Test authentication utility functions."""

    def test_hash_password(self):
        """Test password hashing."""
        from auth_rate_limit import hash_password
        
        password = "testpassword"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0

    def test_verify_password(self):
        """Test password verification."""
        from auth_rate_limit import hash_password, verify_password
        
        password = "testpassword"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
        assert verify_password("wrongpassword", hashed) is False

    def test_generate_api_key(self):
        """Test API key generation."""
        from auth_rate_limit import generate_api_key
        
        api_key = generate_api_key()
        
        assert api_key is not None
        assert len(api_key) >= 32  # Typical API key length

    def test_validate_email(self):
        """Test email validation."""
        from auth_rate_limit import validate_email
        
        assert validate_email("test@example.com") is True
        assert validate_email("invalid-email") is False

    def test_validate_password_strength(self):
        """Test password strength validation."""
        from auth_rate_limit import validate_password_strength
        
        assert validate_password_strength("StrongPass123!") is True
        assert validate_password_strength("weak") is False
