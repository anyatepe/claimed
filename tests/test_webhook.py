"""Tests for webhook functionality."""
import pytest
import hmac
import hashlib
import json
from app.utils.webhook import generate_hmac_signature, send_webhook_notification
from app.config import settings


def test_generate_hmac_signature():
    """Test HMAC signature generation."""
    payload = json.dumps({"test": "data"}, sort_keys=True)
    secret = "test-secret"
    
    signature = generate_hmac_signature(payload, secret)
    
    assert isinstance(signature, str)
    assert len(signature) == 64  # SHA256 hex digest length
    
    # Verify signature is deterministic
    signature2 = generate_hmac_signature(payload, secret)
    assert signature == signature2
    
    # Verify different secrets produce different signatures
    signature3 = generate_hmac_signature(payload, "different-secret")
    assert signature != signature3


@pytest.mark.asyncio
async def test_send_webhook_notification_invalid_url():
    """Test webhook notification with invalid URL."""
    # This should fail gracefully
    result = await send_webhook_notification(
        webhook_url="https://invalid-url-that-does-not-exist.example.com/webhook",
        job_id="test-job",
        status="success",
    )
    
    # Should return False for invalid URL
    assert result is False


def test_webhook_payload_format():
    """Test webhook payload format."""
    payload = {
        "job_id": "test-123",
        "status": "success",
        "result": {"data": "test"},
        "error": None,
    }
    
    payload_json = json.dumps(payload, sort_keys=True)
    signature = generate_hmac_signature(payload_json, settings.webhook_secret_key)
    
    # Verify signature format (function returns hex, header adds "sha256=" prefix)
    assert isinstance(signature, str)
    assert len(signature) == 64  # SHA256 hex digest length
    assert signature.startswith("sha256=") is False  # Function returns just the hex
