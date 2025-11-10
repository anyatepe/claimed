"""Chat memory service."""
from typing import List, Optional
from app.utils.cache import CacheService


class ChatMemoryService:
    """Service for managing chat memory/history."""
    
    def __init__(self):
        self.cache = CacheService()
    
    async def get_history(
        self,
        session_id: str,
        limit: int = 10,
    ) -> List[dict]:
        """Get chat history for a session."""
        key = f"chat_history:{session_id}"
        history = await self.cache.get(key)
        if history is None:
            return []
        return history[-limit:]
    
    async def save_interaction(
        self,
        session_id: str,
        query: str,
        response: str,
    ):
        """Save an interaction to chat history."""
        key = f"chat_history:{session_id}"
        history = await self.get_history(session_id, limit=1000)
        history.append({"query": query, "response": response})
        await self.cache.set(key, history, ttl=3600)  # 1 hour TTL
