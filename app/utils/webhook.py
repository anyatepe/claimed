"""Webhook utilities."""
import hmac
import hashlib
import json
import httpx
from typing import Dict, Any, Optional
from app.config import settings


def generate_hmac_signature(payload: str, secret: str) -> str:
    """Generate HMAC signature for webhook payload.
    
    Args:
        payload: JSON string payload
        secret: Secret key for signing
        
    Returns:
        HMAC signature as hex string
    """
    return hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


async def send_webhook_notification(
    webhook_url: str,
    job_id: str,
    status: str,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
) -> bool:
    """Send webhook notification with HMAC signature.
    
    Args:
        webhook_url: Webhook URL to POST to
        job_id: Job ID
        status: Job status
        result: Optional result data
        error: Optional error message
        
    Returns:
        True if successful, False otherwise
    """
    payload = {
        "job_id": job_id,
        "status": status,
        "result": result,
        "error": error,
    }
    
    payload_json = json.dumps(payload, sort_keys=True)
    signature_hex = generate_hmac_signature(payload_json, settings.webhook_secret_key)
    
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": f"sha256={signature_hex}",
    }
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                webhook_url,
                content=payload_json,
                headers=headers,
            )
            response.raise_for_status()
            return True
    except Exception as e:
        # Log error in production
        print(f"Webhook notification failed: {e}")
        return False
