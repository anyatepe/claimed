"""Pytest configuration and fixtures."""
import pytest
import os
import tempfile
import shutil
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings


@pytest.fixture(scope="session")
def test_storage_dir():
    """Create temporary storage directory for tests."""
    temp_dir = tempfile.mkdtemp()
    original_path = settings.result_storage_path
    settings.result_storage_path = temp_dir
    yield temp_dir
    shutil.rmtree(temp_dir)
    settings.result_storage_path = original_path


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_redis(monkeypatch):
    """Mock Redis connection for testing."""
    # In a real test setup, you might use fakeredis or mock Redis
    pass
