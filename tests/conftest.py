"""Pytest configuration and fixtures."""
import os
import pytest


@pytest.fixture(autouse=True)
def reset_env():
    """Reset environment variables after each test."""
    # Store original env vars
    original_env = dict(os.environ)
    
    yield
    
    # Restore original env vars
    os.environ.clear()
    os.environ.update(original_env)
