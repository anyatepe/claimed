"""
Tests for chat memory service.
"""

import pytest
import time
import json
from unittest.mock import Mock, patch

import redis
from fakeredis import FakeStrictRedis

from app.services.chat_memory import ChatMemory, Message


@pytest.fixture
def fake_redis():
    """Create a fake Redis instance for testing."""
    return FakeStrictRedis(decode_responses=True)


@pytest.fixture
def chat_memory(fake_redis):
    """Create a ChatMemory instance with fake Redis."""
    return ChatMemory(redis_client=fake_redis, ttl_seconds=60)


@pytest.fixture
def chat_memory_with_limits(fake_redis):
    """Create a ChatMemory instance with size limits."""
    return ChatMemory(
        redis_client=fake_redis,
        ttl_seconds=60,
        max_turns=3,
        max_tokens=100
    )


class TestMessage:
    """Tests for Message class."""
    
    def test_message_creation(self):
        """Test basic message creation."""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp is not None
    
    def test_message_timestamp(self):
        """Test that timestamp is set automatically."""
        before = time.time()
        msg = Message(role="user", content="Hello")
        after = time.time()
        assert before <= msg.timestamp <= after
    
    def test_message_custom_timestamp(self):
        """Test message with custom timestamp."""
        custom_time = 1234567890.0
        msg = Message(role="user", content="Hello", timestamp=custom_time)
        assert msg.timestamp == custom_time
    
    def test_message_serialization(self):
        """Test message serialization to/from dict."""
        msg = Message(role="assistant", content="Hi there")
        msg_dict = msg.to_dict()
        assert msg_dict["role"] == "assistant"
        assert msg_dict["content"] == "Hi there"
        assert "timestamp" in msg_dict
        
        restored = Message.from_dict(msg_dict)
        assert restored.role == msg.role
        assert restored.content == msg.content
        assert restored.timestamp == msg.timestamp


class TestChatMemoryRoundTrip:
    """Tests for round-trip save/load operations."""
    
    def test_save_and_load_single_turn(self, chat_memory):
        """Test saving and loading a single conversation turn."""
        session_id = "test-session-1"
        user_msg = "Hello, how are you?"
        assistant_msg = "I'm doing well, thank you!"
        
        chat_memory.save_turn(session_id, user_msg, assistant_msg)
        history = chat_memory.load_history(session_id)
        
        assert len(history) == 2
        assert history[0].role == "user"
        assert history[0].content == user_msg
        assert history[1].role == "assistant"
        assert history[1].content == assistant_msg
    
    def test_save_and_load_multiple_turns(self, chat_memory):
        """Test saving and loading multiple conversation turns."""
        session_id = "test-session-2"
        
        # Save first turn
        chat_memory.save_turn(session_id, "Hello", "Hi there!")
        
        # Save second turn
        chat_memory.save_turn(session_id, "How are you?", "I'm fine, thanks!")
        
        # Save third turn
        chat_memory.save_turn(session_id, "What's the weather?", "It's sunny!")
        
        history = chat_memory.load_history(session_id)
        
        assert len(history) == 6  # 3 turns = 6 messages
        assert history[0].role == "user"
        assert history[0].content == "Hello"
        assert history[1].role == "assistant"
        assert history[1].content == "Hi there!"
        assert history[2].role == "user"
        assert history[2].content == "How are you?"
        assert history[3].role == "assistant"
        assert history[3].content == "I'm fine, thanks!"
        assert history[4].role == "user"
        assert history[4].content == "What's the weather?"
        assert history[5].role == "assistant"
        assert history[5].content == "It's sunny!"
    
    def test_load_nonexistent_session(self, chat_memory):
        """Test loading a session that doesn't exist."""
        history = chat_memory.load_history("nonexistent-session")
        assert history == []
    
    def test_multiple_sessions_independence(self, chat_memory):
        """Test that different sessions are independent."""
        session1 = "session-1"
        session2 = "session-2"
        
        chat_memory.save_turn(session1, "Hello", "Hi!")
        chat_memory.save_turn(session2, "Goodbye", "Bye!")
        
        history1 = chat_memory.load_history(session1)
        history2 = chat_memory.load_history(session2)
        
        assert len(history1) == 2
        assert len(history2) == 2
        assert history1[0].content == "Hello"
        assert history2[0].content == "Goodbye"
    
    def test_message_ordering(self, chat_memory):
        """Test that messages are returned in chronological order."""
        session_id = "test-ordering"
        
        # Add small delay between messages
        chat_memory.save_turn(session_id, "First", "First response")
        time.sleep(0.01)
        chat_memory.save_turn(session_id, "Second", "Second response")
        
        history = chat_memory.load_history(session_id)
        
        assert len(history) == 4
        # Verify timestamps are in order
        for i in range(len(history) - 1):
            assert history[i].timestamp <= history[i + 1].timestamp


class TestChatMemoryTTL:
    """Tests for TTL expiry behavior."""
    
    def test_ttl_is_set(self, fake_redis):
        """Test that TTL is set when saving a session."""
        chat_memory = ChatMemory(redis_client=fake_redis, ttl_seconds=120)
        session_id = "ttl-test"
        
        chat_memory.save_turn(session_id, "Hello", "Hi!")
        
        key = chat_memory._get_key(session_id)
        ttl = fake_redis.ttl(key)
        
        # TTL should be approximately 120 seconds (allow small margin)
        assert 115 <= ttl <= 120
    
    def test_session_expires_after_ttl(self, fake_redis):
        """Test that session expires after TTL."""
        chat_memory = ChatMemory(redis_client=fake_redis, ttl_seconds=1)
        session_id = "expiry-test"
        
        chat_memory.save_turn(session_id, "Hello", "Hi!")
        
        # Verify session exists
        history = chat_memory.load_history(session_id)
        assert len(history) == 2
        
        # Manually expire the key (simulating TTL expiry)
        key = chat_memory._get_key(session_id)
        fake_redis.expire(key, 0)
        
        # Verify session is gone
        history = chat_memory.load_history(session_id)
        assert history == []
    
    def test_ttl_refresh_on_save(self, fake_redis):
        """Test that TTL is refreshed when saving a new turn."""
        chat_memory = ChatMemory(redis_client=fake_redis, ttl_seconds=60)
        session_id = "ttl-refresh-test"
        
        chat_memory.save_turn(session_id, "First", "First response")
        key = chat_memory._get_key(session_id)
        initial_ttl = fake_redis.ttl(key)
        
        # Wait a bit
        time.sleep(0.1)
        
        # Save another turn
        chat_memory.save_turn(session_id, "Second", "Second response")
        
        # TTL should be refreshed (close to full duration)
        new_ttl = fake_redis.ttl(key)
        assert new_ttl >= initial_ttl - 1  # Allow small margin
    
    def test_extend_ttl(self, fake_redis):
        """Test extending TTL of existing session."""
        chat_memory = ChatMemory(redis_client=fake_redis, ttl_seconds=60)
        session_id = "extend-ttl-test"
        
        chat_memory.save_turn(session_id, "Hello", "Hi!")
        key = chat_memory._get_key(session_id)
        
        # Set a short TTL
        fake_redis.expire(key, 10)
        assert fake_redis.ttl(key) <= 10
        
        # Extend TTL
        result = chat_memory.extend_ttl(session_id)
        assert result is True
        assert fake_redis.ttl(key) >= 55  # Should be close to 60
    
    def test_extend_ttl_nonexistent_session(self, chat_memory):
        """Test extending TTL of non-existent session."""
        result = chat_memory.extend_ttl("nonexistent")
        assert result is False


class TestChatMemorySizeLimits:
    """Tests for size limit enforcement."""
    
    def test_max_turns_limit(self, fake_redis):
        """Test that max_turns limit is enforced."""
        chat_memory = ChatMemory(
            redis_client=fake_redis,
            ttl_seconds=60,
            max_turns=2
        )
        session_id = "turns-limit-test"
        
        # Save 3 turns (should only keep last 2)
        chat_memory.save_turn(session_id, "Turn 1 user", "Turn 1 assistant")
        chat_memory.save_turn(session_id, "Turn 2 user", "Turn 2 assistant")
        chat_memory.save_turn(session_id, "Turn 3 user", "Turn 3 assistant")
        
        history = chat_memory.load_history(session_id)
        
        # Should only have 2 turns = 4 messages
        assert len(history) == 4
        assert history[0].content == "Turn 2 user"
        assert history[1].content == "Turn 2 assistant"
        assert history[2].content == "Turn 3 user"
        assert history[3].content == "Turn 3 assistant"
    
    def test_max_tokens_limit(self, fake_redis):
        """Test that max_tokens limit is enforced."""
        # Set a small token limit (approximately 20 tokens = 80 chars)
        chat_memory = ChatMemory(
            redis_client=fake_redis,
            ttl_seconds=60,
            max_tokens=20
        )
        session_id = "tokens-limit-test"
        
        # Save messages that exceed the limit
        chat_memory.save_turn(session_id, "A" * 30, "B" * 30)  # ~15 tokens each
        chat_memory.save_turn(session_id, "C" * 30, "D" * 30)  # ~15 tokens each
        
        history = chat_memory.load_history(session_id)
        
        # Should trim to fit within token budget
        total_tokens = sum(len(msg.content) // 4 for msg in history)
        assert total_tokens <= 20
    
    def test_max_turns_and_tokens_combined(self, fake_redis):
        """Test that both limits work together."""
        chat_memory = ChatMemory(
            redis_client=fake_redis,
            ttl_seconds=60,
            max_turns=5,
            max_tokens=50
        )
        session_id = "combined-limits-test"
        
        # Add many small turns
        for i in range(10):
            chat_memory.save_turn(session_id, f"User {i}", f"Assistant {i}")
        
        history = chat_memory.load_history(session_id)
        
        # Should respect both limits
        assert len(history) <= 10  # max_turns * 2
        total_tokens = sum(len(msg.content) // 4 for msg in history)
        assert total_tokens <= 50
    
    def test_no_limits(self, chat_memory):
        """Test that messages are saved without limits."""
        session_id = "no-limits-test"
        
        # Save many turns
        for i in range(20):
            chat_memory.save_turn(session_id, f"User {i}", f"Assistant {i}")
        
        history = chat_memory.load_history(session_id)
        assert len(history) == 40  # All messages should be present


class TestChatMemoryEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_messages(self, chat_memory):
        """Test handling of empty messages."""
        session_id = "empty-messages-test"
        
        chat_memory.save_turn(session_id, "", "")
        history = chat_memory.load_history(session_id)
        
        assert len(history) == 2
        assert history[0].content == ""
        assert history[1].content == ""
    
    def test_very_long_messages(self, chat_memory):
        """Test handling of very long messages."""
        session_id = "long-messages-test"
        long_text = "A" * 10000
        
        chat_memory.save_turn(session_id, long_text, long_text)
        history = chat_memory.load_history(session_id)
        
        assert len(history) == 2
        assert len(history[0].content) == 10000
        assert len(history[1].content) == 10000
    
    def test_special_characters(self, chat_memory):
        """Test handling of special characters and unicode."""
        session_id = "special-chars-test"
        
        special_text = "Hello! 🎉 你好 مرحبا\n\t\"quotes\" 'apostrophes'"
        chat_memory.save_turn(session_id, special_text, special_text)
        history = chat_memory.load_history(session_id)
        
        assert len(history) == 2
        assert history[0].content == special_text
        assert history[1].content == special_text
    
    def test_delete_session(self, chat_memory):
        """Test deleting a session."""
        session_id = "delete-test"
        
        chat_memory.save_turn(session_id, "Hello", "Hi!")
        history = chat_memory.load_history(session_id)
        assert len(history) == 2
        
        chat_memory.delete_session(session_id)
        history = chat_memory.load_history(session_id)
        assert history == []
    
    def test_corrupted_data_handling(self, fake_redis):
        """Test handling of corrupted Redis data."""
        chat_memory = ChatMemory(redis_client=fake_redis, ttl_seconds=60)
        session_id = "corrupted-test"
        key = chat_memory._get_key(session_id)
        
        # Store invalid JSON
        fake_redis.set(key, "not valid json")
        
        # Should return empty list instead of crashing
        history = chat_memory.load_history(session_id)
        assert history == []
    
    def test_redis_error_propagation(self):
        """Test that Redis errors are properly propagated."""
        mock_redis = Mock()
        mock_redis.get.side_effect = redis.RedisError("Connection failed")
        
        chat_memory = ChatMemory(redis_client=mock_redis, ttl_seconds=60)
        
        with pytest.raises(redis.RedisError):
            chat_memory.load_history("test-session")


class TestChatMemoryInitialization:
    """Tests for ChatMemory initialization."""
    
    def test_init_with_redis_client(self, fake_redis):
        """Test initialization with provided Redis client."""
        chat_memory = ChatMemory(redis_client=fake_redis)
        assert chat_memory.redis == fake_redis
    
    def test_init_with_redis_url(self):
        """Test initialization with Redis URL."""
        with patch('app.services.chat_memory.redis.from_url') as mock_from_url:
            mock_client = Mock()
            mock_from_url.return_value = mock_client
            
            chat_memory = ChatMemory(redis_url="redis://localhost:6379/0")
            
            mock_from_url.assert_called_once()
            assert chat_memory.redis == mock_client
    
    def test_init_defaults(self, fake_redis):
        """Test default initialization values."""
        chat_memory = ChatMemory(redis_client=fake_redis)
        assert chat_memory.ttl_seconds == 3600
        assert chat_memory.max_turns is None
        assert chat_memory.max_tokens is None
        assert chat_memory.key_prefix == "chat:session:"
    
    def test_init_custom_config(self, fake_redis):
        """Test initialization with custom configuration."""
        chat_memory = ChatMemory(
            redis_client=fake_redis,
            ttl_seconds=7200,
            max_turns=10,
            max_tokens=1000,
            key_prefix="custom:prefix:"
        )
        assert chat_memory.ttl_seconds == 7200
        assert chat_memory.max_turns == 10
        assert chat_memory.max_tokens == 1000
        assert chat_memory.key_prefix == "custom:prefix:"
