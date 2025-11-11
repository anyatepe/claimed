"""Tests for LLMService."""

import json
import os
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest
from openai import OpenAI
from openai._exceptions import APIError, APITimeoutError

from app.services.llm import LLMService, LLMServiceError


class TestLLMService:
    """Test suite for LLMService."""

    def test_init_openai(self):
        """Test initialization with OpenAI provider."""
        service = LLMService(provider="openai", api_key="test-key")
        assert service.provider == "openai"
        assert isinstance(service.client, OpenAI)

    def test_init_local(self):
        """Test initialization with local provider."""
        service = LLMService(provider="local", base_url="http://localhost:8000/v1")
        assert service.provider == "local"
        assert service.base_url == "http://localhost:8000/v1"

    def test_init_invalid_provider(self):
        """Test initialization with invalid provider raises error."""
        with pytest.raises(ValueError, match="Unsupported provider"):
            LLMService(provider="invalid")

    @patch("app.services.llm.OpenAI")
    def test_chat_openai_success(self, mock_openai_class):
        """Test successful OpenAI chat completion."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello, world!"
        mock_client.chat.completions.create.return_value = mock_response

        service = LLMService(provider="openai", api_key="test-key")
        result = service.chat(
            prompt_messages=[{"role": "user", "content": "Hello"}],
            json_mode=False,
        )

        assert result == "Hello, world!"
        mock_client.chat.completions.create.assert_called_once()

    @patch("app.services.llm.OpenAI")
    def test_chat_openai_json_mode(self, mock_openai_class):
        """Test OpenAI chat completion with JSON mode."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"key": "value"}'
        mock_client.chat.completions.create.return_value = mock_response

        service = LLMService(provider="openai", api_key="test-key")
        result = service.chat(
            prompt_messages=[{"role": "user", "content": "Return JSON"}],
            json_mode=True,
        )

        assert isinstance(result, dict)
        assert result == {"key": "value"}
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["response_format"] == {"type": "json_object"}

    @patch("app.services.llm.httpx.Client")
    def test_chat_local_success(self, mock_client_class):
        """Test successful local vLLM chat completion."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Local response"}}]
        }
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client

        service = LLMService(provider="local", base_url="http://localhost:8000/v1")
        result = service.chat(
            prompt_messages=[{"role": "user", "content": "Hello"}],
            json_mode=False,
        )

        assert result == "Local response"
        mock_client.post.assert_called_once()

    @patch("app.services.llm.httpx.Client")
    def test_chat_local_json_mode(self, mock_client_class):
        """Test local vLLM chat completion with JSON mode."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"status": "ok"}'}}]
        }
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client

        service = LLMService(provider="local", base_url="http://localhost:8000/v1")
        result = service.chat(
            prompt_messages=[{"role": "user", "content": "Return JSON"}],
            json_mode=True,
        )

        assert isinstance(result, dict)
        assert result == {"status": "ok"}
        call_kwargs = mock_client.post.call_args[1]
        assert call_kwargs["json"]["response_format"] == {"type": "json_object"}

    @patch("app.services.llm.OpenAI")
    def test_chat_openai_retry_on_api_error(self, mock_openai_class):
        """Test retry logic on OpenAI API errors."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # First two calls fail, third succeeds
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Success after retry"

        mock_client.chat.completions.create.side_effect = [
            APIError("Rate limit", response=Mock(), body=None),
            APIError("Rate limit", response=Mock(), body=None),
            mock_response,
        ]

        service = LLMService(provider="openai", api_key="test-key", max_retries=3)
        result = service.chat(prompt_messages=[{"role": "user", "content": "Hello"}])

        assert result == "Success after retry"
        assert mock_client.chat.completions.create.call_count == 3

    @patch("app.services.llm.httpx.Client")
    def test_chat_local_retry_on_timeout(self, mock_client_class):
        """Test retry logic on local provider timeout."""
        mock_client = MagicMock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client

        # First call times out, second succeeds
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Success after timeout"}}]
        }
        mock_response.raise_for_status = Mock()

        mock_client.post.side_effect = [
            httpx.TimeoutException("Request timeout"),
            mock_response,
        ]

        service = LLMService(provider="local", base_url="http://localhost:8000/v1", max_retries=3)
        result = service.chat(prompt_messages=[{"role": "user", "content": "Hello"}])

        assert result == "Success after timeout"
        assert mock_client.post.call_count == 2

    @patch("app.services.llm.OpenAI")
    def test_chat_openai_max_retries_exceeded(self, mock_openai_class):
        """Test that max retries are respected."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_client.chat.completions.create.side_effect = APIError(
            "Rate limit", response=Mock(), body=None
        )

        service = LLMService(provider="openai", api_key="test-key", max_retries=2)
        with pytest.raises(LLMServiceError):
            service.chat(prompt_messages=[{"role": "user", "content": "Hello"}])

        assert mock_client.chat.completions.create.call_count == 2

    def test_parse_json_safe_valid_json(self):
        """Test safe JSON parsing with valid JSON."""
        service = LLMService(provider="openai", api_key="test-key")
        result = service._parse_json_safe('{"key": "value", "number": 42}')
        assert result == {"key": "value", "number": 42}

    def test_parse_json_safe_json_in_markdown(self):
        """Test safe JSON parsing with JSON in markdown code blocks."""
        service = LLMService(provider="openai", api_key="test-key")
        result = service._parse_json_safe('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_parse_json_safe_json_in_code_block(self):
        """Test safe JSON parsing with JSON in generic code blocks."""
        service = LLMService(provider="openai", api_key="test-key")
        result = service._parse_json_safe('```\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_parse_json_safe_trailing_comma(self):
        """Test safe JSON parsing fixes trailing commas."""
        service = LLMService(provider="openai", api_key="test-key")
        result = service._parse_json_safe('{"key": "value",}')
        assert result == {"key": "value"}

    def test_parse_json_safe_invalid_json(self):
        """Test safe JSON parsing raises error on invalid JSON."""
        service = LLMService(provider="openai", api_key="test-key")
        with pytest.raises(LLMServiceError, match="Failed to parse JSON"):
            service._parse_json_safe("not valid json")

    @patch("app.services.llm.OpenAI")
    def test_chat_openai_empty_response(self, mock_openai_class):
        """Test handling of empty response from OpenAI."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_client.chat.completions.create.return_value = mock_response

        service = LLMService(provider="openai", api_key="test-key")
        with pytest.raises(LLMServiceError, match="Empty response"):
            service.chat(prompt_messages=[{"role": "user", "content": "Hello"}])

    @patch("app.services.llm.httpx.Client")
    def test_chat_local_invalid_response_format(self, mock_client_class):
        """Test handling of invalid response format from local provider."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"invalid": "format"}
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client

        service = LLMService(provider="local", base_url="http://localhost:8000/v1")
        with pytest.raises(LLMServiceError, match="Invalid response format"):
            service.chat(prompt_messages=[{"role": "user", "content": "Hello"}])

    @patch("app.services.llm.OpenAI")
    def test_chat_parameters_passed_correctly(self, mock_openai_class):
        """Test that chat parameters are passed correctly to provider."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_client.chat.completions.create.return_value = mock_response

        service = LLMService(provider="openai", api_key="test-key")
        service.chat(
            prompt_messages=[{"role": "user", "content": "Test"}],
            max_tokens=1024,
            temperature=0.7,
        )

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["max_tokens"] == 1024
        assert call_kwargs["temperature"] == 0.7

    @patch("app.services.llm.httpx.Client")
    def test_chat_local_with_api_key(self, mock_client_class):
        """Test local provider includes API key in headers when provided."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}}]
        }
        mock_response.raise_for_status = Mock()
        mock_client.post.return_value = mock_response
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client_class.return_value = mock_client

        service = LLMService(
            provider="local",
            base_url="http://localhost:8000/v1",
            api_key="test-api-key",
        )
        service.chat(prompt_messages=[{"role": "user", "content": "Hello"}])

        call_kwargs = mock_client.post.call_args
        headers = call_kwargs[1]["headers"]
        assert headers["Authorization"] == "Bearer test-api-key"
