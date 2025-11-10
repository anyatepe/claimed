"""Idempotency utilities."""
import hashlib
import json
from typing import Any, Optional
from app.utils.cache import CacheService


class IdempotencyService:
    """Service for handling idempotent requests."""
    
    def __init__(self):
        self.cache = CacheService()
    
    def generate_key(self, method: str, path: str, body: Any, headers: dict) -> str:
        """Generate an idempotency key from request details."""
        key_data = {
            "method": method,
            "path": path,
            "body": body,
            "headers": headers.get("idempotency-key", ""),
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    async def get_response(self, idempotency_key: str) -> Optional[dict]:
        """Get cached response for an idempotency key."""
        key = f"idempotency:{idempotency_key}"
        return await self.cache.get(key)
    
    async def save_response(
        self,
        idempotency_key: str,
        response: dict,
        ttl: int = 3600,
    ):
        """Save a response for an idempotency key."""
        key = f"idempotency:{idempotency_key}"
        await self.cache.set(key, response, ttl=ttl)
