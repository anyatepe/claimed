"""
Chat memory service providing stateless and Redis-backed session memory.

This module provides session-based chat history storage with configurable TTL
and size limits (turn count or token budget).
"""

import json
import time
from dataclasses import dataclass, asdict
from typing import Optional, List

import redis
from redis.exceptions import RedisError


@dataclass
class Message:
    """Represents a single message in the chat history."""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: Optional[float] = None

    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        """Convert message to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'Message':
        """Create message from dictionary."""
        return cls(**data)


class ChatMemory:
    """
    Redis-backed chat memory service for managing session-based conversation history.
    
    Features:
    - Configurable TTL for session expiration
    - Size limits: maximum turn count or token budget
    - Automatic trimming of old messages when limits are exceeded
    """
    
    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        redis_url: Optional[str] = None,
        ttl_seconds: int = 3600,
        max_turns: Optional[int] = None,
        max_tokens: Optional[int] = None,
        key_prefix: str = "chat:session:",
    ):
        """
        Initialize chat memory service.
        
        Args:
            redis_client: Optional Redis client instance. If not provided, will create one.
            redis_url: Redis connection URL (e.g., 'redis://localhost:6379/0').
                      Used only if redis_client is not provided.
            ttl_seconds: Time-to-live for sessions in seconds. Default: 3600 (1 hour).
            max_turns: Maximum number of turns (user+assistant pairs) to keep.
                      If None, no turn limit is enforced.
            max_tokens: Maximum token budget for the session. If None, no token limit.
                       Note: This is a simple character-based estimate (4 chars ≈ 1 token).
            key_prefix: Prefix for Redis keys. Default: "chat:session:".
        """
        if redis_client is not None:
            self.redis = redis_client
        else:
            redis_url = redis_url or "redis://localhost:6379/0"
            self.redis = redis.from_url(redis_url, decode_responses=True)
        
        self.ttl_seconds = ttl_seconds
        self.max_turns = max_turns
        self.max_tokens = max_tokens
        self.key_prefix = key_prefix
    
    def _get_key(self, session_id: str) -> str:
        """Get Redis key for a session."""
        return f"{self.key_prefix}{session_id}"
    
    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count from text.
        Simple heuristic: ~4 characters per token.
        """
        return len(text) // 4
    
    def _count_tokens(self, messages: List[Message]) -> int:
        """Count total tokens in a list of messages."""
        return sum(self._estimate_tokens(msg.content) for msg in messages)
    
    def _trim_messages(
        self,
        messages: List[Message],
        max_turns: Optional[int] = None,
        max_tokens: Optional[int] = None
    ) -> List[Message]:
        """
        Trim messages to fit within size limits.
        Keeps the most recent messages.
        
        Args:
            messages: List of messages to trim.
            max_turns: Maximum number of turns to keep.
            max_tokens: Maximum token budget.
        
        Returns:
            Trimmed list of messages.
        """
        if not messages:
            return messages
        
        # Apply turn limit
        if max_turns is not None:
            # Each turn is a user+assistant pair, so we keep last 2*max_turns messages
            max_messages = max_turns * 2
            if len(messages) > max_messages:
                messages = messages[-max_messages:]
        
        # Apply token limit
        if max_tokens is not None:
            total_tokens = self._count_tokens(messages)
            if total_tokens > max_tokens:
                # Remove oldest messages until we're under the limit
                trimmed = []
                current_tokens = 0
                for msg in reversed(messages):
                    msg_tokens = self._estimate_tokens(msg.content)
                    if current_tokens + msg_tokens <= max_tokens:
                        trimmed.insert(0, msg)
                        current_tokens += msg_tokens
                    else:
                        break
                messages = trimmed
        
        return messages
    
    def load_history(self, session_id: str) -> List[Message]:
        """
        Load chat history for a session.
        
        Args:
            session_id: Unique session identifier.
        
        Returns:
            List of Message objects, ordered chronologically.
            Returns empty list if session doesn't exist or has expired.
        
        Raises:
            RedisError: If Redis operation fails.
        """
        try:
            key = self._get_key(session_id)
            data = self.redis.get(key)
            
            if data is None:
                return []
            
            messages_data = json.loads(data)
            messages = [Message.from_dict(msg_data) for msg_data in messages_data]
            
            # Sort by timestamp to ensure chronological order
            messages.sort(key=lambda m: m.timestamp)
            
            return messages
        
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # If data is corrupted, return empty list
            return []
        except RedisError:
            raise
    
    def save_turn(self, session_id: str, user: str, assistant: str) -> None:
        """
        Save a conversation turn (user message + assistant response) to the session.
        
        Args:
            session_id: Unique session identifier.
            user: User message content.
            assistant: Assistant response content.
        
        Raises:
            RedisError: If Redis operation fails.
        """
        try:
            # Load existing history
            messages = self.load_history(session_id)
            
            # Add new messages
            messages.append(Message(role="user", content=user))
            messages.append(Message(role="assistant", content=assistant))
            
            # Apply size limits
            messages = self._trim_messages(
                messages,
                max_turns=self.max_turns,
                max_tokens=self.max_tokens
            )
            
            # Serialize and save
            key = self._get_key(session_id)
            messages_data = [msg.to_dict() for msg in messages]
            data = json.dumps(messages_data)
            
            # Save with TTL
            self.redis.setex(key, self.ttl_seconds, data)
        
        except RedisError:
            raise
    
    def delete_session(self, session_id: str) -> None:
        """
        Delete a session from Redis.
        
        Args:
            session_id: Unique session identifier.
        
        Raises:
            RedisError: If Redis operation fails.
        """
        try:
            key = self._get_key(session_id)
            self.redis.delete(key)
        except RedisError:
            raise
    
    def extend_ttl(self, session_id: str) -> bool:
        """
        Extend the TTL of an existing session.
        
        Args:
            session_id: Unique session identifier.
        
        Returns:
            True if session exists and TTL was extended, False otherwise.
        
        Raises:
            RedisError: If Redis operation fails.
        """
        try:
            key = self._get_key(session_id)
            return bool(self.redis.expire(key, self.ttl_seconds))
        except RedisError:
            raise
