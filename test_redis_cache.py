"""
Unit tests for Redis caching and idempotency functionality.

These tests verify that:
1. Cache functions work correctly
2. Duplicate requests reuse cached results
3. Idempotency is properly enforced
"""

import pytest
import json
import time
from unittest.mock import Mock, patch, MagicMock
import redis

from redis_cache import (
    cache_result,
    get_cached_result,
    ensure_idempotency,
    generate_cache_key,
    cached,
    idempotent,
    get_redis_client,
    DEFAULT_TTL
)
from nlp_service import summarize, classify


class TestRedisCacheUtilities:
    """Test basic Redis cache utility functions."""
    
    @patch('redis_cache.get_redis_client')
    def test_cache_result_success(self, mock_get_client):
        """Test successful caching of a result."""
        mock_client = Mock()
        mock_client.setex.return_value = True
        mock_get_client.return_value = mock_client
        
        result = cache_result("test_key", {"data": "test"}, ttl=60)
        
        assert result is True
        mock_client.setex.assert_called_once()
        call_args = mock_client.setex.call_args
        assert call_args[0][0] == "test_key"
        assert call_args[0][1] == 60
        assert json.loads(call_args[0][2]) == {"data": "test"}
    
    @patch('redis_cache.get_redis_client')
    def test_cache_result_failure(self, mock_get_client):
        """Test caching failure handling."""
        mock_client = Mock()
        mock_client.setex.side_effect = redis.RedisError("Connection failed")
        mock_get_client.return_value = mock_client
        
        result = cache_result("test_key", {"data": "test"}, ttl=60)
        
        assert result is False
    
    @patch('redis_cache.get_redis_client')
    def test_get_cached_result_found(self, mock_get_client):
        """Test retrieving a cached result that exists."""
        mock_client = Mock()
        cached_data = json.dumps({"data": "test"})
        mock_client.get.return_value = cached_data
        mock_get_client.return_value = mock_client
        
        result = get_cached_result("test_key")
        
        assert result == {"data": "test"}
        mock_client.get.assert_called_once_with("test_key")
    
    @patch('redis_cache.get_redis_client')
    def test_get_cached_result_not_found(self, mock_get_client):
        """Test retrieving a cached result that doesn't exist."""
        mock_client = Mock()
        mock_client.get.return_value = None
        mock_get_client.return_value = mock_client
        
        result = get_cached_result("test_key")
        
        assert result is None
        mock_client.get.assert_called_once_with("test_key")
    
    @patch('redis_cache.get_redis_client')
    def test_ensure_idempotency_new_request(self, mock_get_client):
        """Test idempotency check for a new request."""
        mock_client = Mock()
        mock_client.setnx.return_value = True  # Key doesn't exist
        mock_client.expire.return_value = True
        mock_get_client.return_value = mock_client
        
        result = ensure_idempotency("test_idempotency_key", ttl=60)
        
        assert result is True
        mock_client.setnx.assert_called_once_with("test_idempotency_key", "processing")
        mock_client.expire.assert_called_once_with("test_idempotency_key", 60)
    
    @patch('redis_cache.get_redis_client')
    def test_ensure_idempotency_existing_request(self, mock_get_client):
        """Test idempotency check for an already processed request."""
        mock_client = Mock()
        mock_client.setnx.return_value = False  # Key already exists
        mock_get_client.return_value = mock_client
        
        result = ensure_idempotency("test_idempotency_key", ttl=60)
        
        assert result is False
        mock_client.setnx.assert_called_once_with("test_idempotency_key", "processing")
        mock_client.expire.assert_not_called()
    
    @patch('redis_cache.get_redis_client')
    def test_ensure_idempotency_redis_error(self, mock_get_client):
        """Test idempotency check fails open on Redis error."""
        mock_client = Mock()
        mock_client.setnx.side_effect = redis.RedisError("Connection failed")
        mock_get_client.return_value = mock_client
        
        # Should return True (fail open) on Redis error
        result = ensure_idempotency("test_idempotency_key", ttl=60)
        
        assert result is True
    
    def test_generate_cache_key(self):
        """Test cache key generation."""
        key1 = generate_cache_key("test_func", "arg1", "arg2", param1="value1")
        key2 = generate_cache_key("test_func", "arg1", "arg2", param1="value1")
        key3 = generate_cache_key("test_func", "arg1", "arg2", param1="value2")
        
        # Same arguments should generate same key
        assert key1 == key2
        # Different arguments should generate different key
        assert key1 != key3
        # Key should start with prefix
        assert key1.startswith("test_func:")


class TestCachedDecorator:
    """Test the @cached decorator."""
    
    @patch('redis_cache.get_cached_result')
    @patch('redis_cache.cache_result')
    def test_cached_decorator_cache_hit(self, mock_cache_result, mock_get_cached):
        """Test cached decorator returns cached result on cache hit."""
        mock_get_cached.return_value = {"cached": "result"}
        
        @cached(ttl=60)
        def test_function(x, y):
            return {"result": x + y}
        
        result = test_function(1, 2)
        
        assert result == {"cached": "result"}
        mock_get_cached.assert_called_once()
        mock_cache_result.assert_not_called()
    
    @patch('redis_cache.get_cached_result')
    @patch('redis_cache.cache_result')
    def test_cached_decorator_cache_miss(self, mock_cache_result, mock_get_cached):
        """Test cached decorator executes function and caches result on cache miss."""
        mock_get_cached.return_value = None
        mock_cache_result.return_value = True
        
        @cached(ttl=60)
        def test_function(x, y):
            return {"result": x + y}
        
        result = test_function(1, 2)
        
        assert result == {"result": 3}
        mock_get_cached.assert_called_once()
        mock_cache_result.assert_called_once()


class TestIdempotentDecorator:
    """Test the @idempotent decorator."""
    
    @patch('redis_cache.ensure_idempotency')
    @patch('redis_cache.get_cached_result')
    @patch('redis_cache.cache_result')
    def test_idempotent_decorator_new_request(self, mock_cache_result, mock_get_cached, mock_ensure_idempotency):
        """Test idempotent decorator processes new request."""
        mock_ensure_idempotency.return_value = True  # New request
        mock_get_cached.return_value = None
        mock_cache_result.return_value = True
        
        @idempotent(ttl=60)
        def test_function(x, y):
            return {"result": x + y}
        
        result = test_function(1, 2)
        
        assert result == {"result": 3}
        mock_ensure_idempotency.assert_called_once()
        mock_cache_result.assert_called_once()
    
    @patch('redis_cache.ensure_idempotency')
    @patch('redis_cache.get_cached_result')
    @patch('redis_cache.cache_result')
    def test_idempotent_decorator_duplicate_request(self, mock_cache_result, mock_get_cached, mock_ensure_idempotency):
        """Test idempotent decorator returns cached result for duplicate request."""
        mock_ensure_idempotency.return_value = False  # Duplicate request
        mock_get_cached.return_value = {"cached": "result"}
        
        @idempotent(ttl=60)
        def test_function(x, y):
            return {"result": x + y}
        
        result = test_function(1, 2)
        
        assert result == {"cached": "result"}
        mock_ensure_idempotency.assert_called_once()
        mock_get_cached.assert_called_once()
        # Should not cache again for duplicate request
        assert mock_cache_result.call_count == 0


class TestSummarizeFunction:
    """Test the summarize function with caching."""
    
    @patch('redis_cache.get_cached_result')
    @patch('redis_cache.cache_result')
    @patch('redis_cache.ensure_idempotency')
    def test_summarize_cache_hit(self, mock_ensure_idempotency, mock_cache_result, mock_get_cached):
        """Test summarize returns cached result on cache hit."""
        cached_summary = {
            "summary": "This is a cached summary.",
            "original_length": 100,
            "summary_length": 25,
            "compression_ratio": 0.25
        }
        mock_get_cached.return_value = cached_summary
        mock_ensure_idempotency.return_value = False
        
        text = "This is a long text that should be summarized. " * 10
        result = summarize(text, max_length=50)
        
        assert result == cached_summary
        mock_get_cached.assert_called()
    
    @patch('redis_cache.get_cached_result')
    @patch('redis_cache.cache_result')
    @patch('redis_cache.ensure_idempotency')
    def test_summarize_cache_miss(self, mock_ensure_idempotency, mock_cache_result, mock_get_cached):
        """Test summarize generates new summary on cache miss."""
        mock_get_cached.return_value = None
        mock_ensure_idempotency.return_value = True
        mock_cache_result.return_value = True
        
        text = "This is sentence one. This is sentence two. This is sentence three."
        result = summarize(text, max_length=50, min_length=10)
        
        assert "summary" in result
        assert "original_length" in result
        assert "summary_length" in result
        assert "compression_ratio" in result
        assert result["original_length"] == len(text)
        assert len(result["summary"]) > 0
        mock_cache_result.assert_called()
    
    @patch('redis_cache.get_cached_result')
    @patch('redis_cache.cache_result')
    @patch('redis_cache.ensure_idempotency')
    def test_summarize_duplicate_request(self, mock_ensure_idempotency, mock_cache_result, mock_get_cached):
        """Test duplicate summarize requests reuse cached results."""
        cached_summary = {
            "summary": "Cached summary.",
            "original_length": 100,
            "summary_length": 15,
            "compression_ratio": 0.15
        }
        mock_get_cached.return_value = cached_summary
        mock_ensure_idempotency.return_value = False  # Duplicate request
        
        text = "Some text to summarize."
        
        # First call
        result1 = summarize(text, max_length=50)
        # Second call with same parameters
        result2 = summarize(text, max_length=50)
        
        assert result1 == cached_summary
        assert result2 == cached_summary
        assert result1 == result2
        # Should have checked cache multiple times
        assert mock_get_cached.call_count >= 2


class TestClassifyFunction:
    """Test the classify function with caching."""
    
    @patch('redis_cache.get_cached_result')
    @patch('redis_cache.cache_result')
    @patch('redis_cache.ensure_idempotency')
    def test_classify_cache_hit(self, mock_ensure_idempotency, mock_cache_result, mock_get_cached):
        """Test classify returns cached result on cache hit."""
        cached_classification = {
            "category": "technology",
            "confidence": 0.85,
            "scores": {"technology": 0.85, "science": 0.2, "business": 0.1}
        }
        mock_get_cached.return_value = cached_classification
        mock_ensure_idempotency.return_value = False
        
        text = "This is about computers and software."
        result = classify(text)
        
        assert result == cached_classification
        mock_get_cached.assert_called()
    
    @patch('redis_cache.get_cached_result')
    @patch('redis_cache.cache_result')
    @patch('redis_cache.ensure_idempotency')
    def test_classify_cache_miss(self, mock_ensure_idempotency, mock_cache_result, mock_get_cached):
        """Test classify generates new classification on cache miss."""
        mock_get_cached.return_value = None
        mock_ensure_idempotency.return_value = True
        mock_cache_result.return_value = True
        
        text = "This is about computers and software development."
        result = classify(text)
        
        assert "category" in result
        assert "confidence" in result
        assert "scores" in result
        assert result["confidence"] >= 0.0
        assert result["confidence"] <= 1.0
        mock_cache_result.assert_called()
    
    @patch('redis_cache.get_cached_result')
    @patch('redis_cache.cache_result')
    @patch('redis_cache.ensure_idempotency')
    def test_classify_duplicate_request(self, mock_ensure_idempotency, mock_cache_result, mock_get_cached):
        """Test duplicate classify requests reuse cached results."""
        cached_classification = {
            "category": "science",
            "confidence": 0.9,
            "scores": {"science": 0.9, "technology": 0.3}
        }
        mock_get_cached.return_value = cached_classification
        mock_ensure_idempotency.return_value = False  # Duplicate request
        
        text = "This is about scientific research and experiments."
        
        # First call
        result1 = classify(text)
        # Second call with same parameters
        result2 = classify(text)
        
        assert result1 == cached_classification
        assert result2 == cached_classification
        assert result1 == result2
        # Should have checked cache multiple times
        assert mock_get_cached.call_count >= 2
    
    @patch('redis_cache.get_cached_result')
    @patch('redis_cache.cache_result')
    @patch('redis_cache.ensure_idempotency')
    def test_classify_with_custom_categories(self, mock_ensure_idempotency, mock_cache_result, mock_get_cached):
        """Test classify with custom categories."""
        mock_get_cached.return_value = None
        mock_ensure_idempotency.return_value = True
        mock_cache_result.return_value = True
        
        text = "This is about medical treatment and health."
        custom_categories = ["health", "technology"]
        result = classify(text, categories=custom_categories)
        
        assert result["category"] in custom_categories
        assert set(result["scores"].keys()) == set(custom_categories)


class TestIntegration:
    """Integration tests for caching and idempotency."""
    
    @patch('redis_cache.get_redis_client')
    def test_end_to_end_caching_flow(self, mock_get_client):
        """Test end-to-end caching flow with Redis mock."""
        # Setup Redis mock
        mock_client = Mock()
        mock_client.get.return_value = None  # Cache miss initially
        mock_client.setex.return_value = True
        mock_client.setnx.return_value = True  # New request
        mock_client.expire.return_value = True
        mock_get_client.return_value = mock_client
        
        # First call - should cache result
        text = "This is a test text for summarization."
        result1 = summarize(text, max_length=30)
        
        # Verify caching was attempted
        assert mock_client.setex.called
        
        # Second call - simulate cache hit
        cached_data = json.dumps(result1)
        mock_client.get.return_value = cached_data
        mock_client.setnx.return_value = False  # Duplicate request
        
        result2 = summarize(text, max_length=30)
        
        # Results should be identical
        assert result1 == result2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
