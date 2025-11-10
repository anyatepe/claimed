"""Tests for configuration loading."""
import os
import pytest
from pydantic import ValidationError

from app.utils.config import Settings


def test_config_loads_with_defaults():
    """Test that config loads with default values."""
    # Clear any existing env vars for this test
    env_vars_to_clear = [
        "ENV", "API_KEYS", "JWT_SECRET", "VECTOR_BACKEND",
        "PINECONE_ENV", "PINECONE_INDEX", "CHROMA_COLLECTION",
        "EMBED_MODEL_NAME", "REDIS_URL", "LANGFLOW_BASE_URL",
        "STORAGE_BUCKET", "MAX_CHUNK_TOKENS", "CHUNK_OVERLAP",
    ]
    
    original_values = {}
    for var in env_vars_to_clear:
        original_values[var] = os.environ.get(var)
        if var in os.environ:
            del os.environ[var]
    
    try:
        # Create a new settings instance
        settings = Settings()
        
        # Check defaults
        assert settings.ENV == "development"
        assert settings.API_KEYS == ""
        assert settings.JWT_SECRET == ""
        assert settings.VECTOR_BACKEND == "chroma"
        assert settings.CHROMA_COLLECTION == "default"
        assert settings.EMBED_MODEL_NAME == "sentence-transformers/all-MiniLM-L6-v2"
        assert settings.REDIS_URL == "redis://localhost:6379/0"
        assert settings.LANGFLOW_BASE_URL == "http://localhost:7860"
        assert settings.MAX_CHUNK_TOKENS == 512
        assert settings.CHUNK_OVERLAP == 50
    finally:
        # Restore original values
        for var, value in original_values.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]


def test_config_loads_from_env():
    """Test that config loads from environment variables."""
    # Set test environment variables
    test_env = {
        "ENV": "production",
        "API_KEYS": "key1,key2,key3",
        "JWT_SECRET": "test-secret-key",
        "VECTOR_BACKEND": "pinecone",
        "PINECONE_ENV": "us-east-1",
        "PINECONE_INDEX": "test-index",
        "EMBED_MODEL_NAME": "test-model",
        "REDIS_URL": "redis://test:6379/0",
        "LANGFLOW_BASE_URL": "http://test:7860",
        "STORAGE_BUCKET": "s3://test-bucket/path",
        "MAX_CHUNK_TOKENS": "1024",
        "CHUNK_OVERLAP": "100",
    }
    
    original_values = {}
    for key, value in test_env.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value
    
    try:
        settings = Settings()
        
        assert settings.ENV == "production"
        assert settings.API_KEYS == "key1,key2,key3"
        assert settings.JWT_SECRET == "test-secret-key"
        assert settings.VECTOR_BACKEND == "pinecone"
        assert settings.PINECONE_ENV == "us-east-1"
        assert settings.PINECONE_INDEX == "test-index"
        assert settings.EMBED_MODEL_NAME == "test-model"
        assert settings.REDIS_URL == "redis://test:6379/0"
        assert settings.LANGFLOW_BASE_URL == "http://test:7860"
        assert settings.STORAGE_BUCKET == "s3://test-bucket/path"
        assert settings.MAX_CHUNK_TOKENS == 1024
        assert settings.CHUNK_OVERLAP == 100
    finally:
        # Restore original values
        for key, value in original_values.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]


def test_config_validates_pinecone_backend():
    """Test that config validates Pinecone backend requirements."""
    test_env = {
        "VECTOR_BACKEND": "pinecone",
    }
    
    original_values = {}
    for key, value in test_env.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value
    
    # Clear Pinecone-specific vars
    for var in ["PINECONE_ENV", "PINECONE_INDEX"]:
        original_values[var] = os.environ.get(var)
        if var in os.environ:
            del os.environ[var]
    
    try:
        with pytest.raises(ValidationError):
            Settings()
    finally:
        # Restore original values
        for key, value in original_values.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]


def test_config_loads_chroma_backend_with_default():
    """Test that config loads Chroma backend with default collection."""
    test_env = {
        "VECTOR_BACKEND": "chroma",
    }
    
    original_values = {}
    for key, value in test_env.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value
    
    # Clear Chroma-specific var to test default
    original_values["CHROMA_COLLECTION"] = os.environ.get("CHROMA_COLLECTION")
    if "CHROMA_COLLECTION" in os.environ:
        del os.environ["CHROMA_COLLECTION"]
    
    try:
        settings = Settings()
        assert settings.VECTOR_BACKEND == "chroma"
        assert settings.CHROMA_COLLECTION == "default"
    finally:
        # Restore original values
        for key, value in original_values.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]


def test_config_validates_chunk_tokens():
    """Test that config validates chunk token constraints."""
    test_env = {
        "MAX_CHUNK_TOKENS": "0",
    }
    
    original_values = {}
    for key, value in test_env.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value
    
    try:
        with pytest.raises(ValidationError):
            Settings()
    finally:
        # Restore original values
        for key, value in original_values.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]
