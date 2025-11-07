"""Tests for LLM service."""

import json
import os
from unittest.mock import Mock, patch, MagicMock

import pytest
import requests
from openai import OpenAI

from app.services.llm_service import LLMService, LLMServiceError


class TestLLMService:
    """Test suite for LLMService."""

    @pytest.fixture
    def mock_openai_api_key(self):
        """Mock OpenAI API key."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            yield

    @pytest.fixture
    def mock_vllm_endpoint(self):
        """Mock vLLM endpoint."""
        with patch.dict(os.environ, {"VLLM_ENDPOINT": "http://localhost:8000"}):
            yield

    def test_init_openai_backend(self, mock_openai_api_key):
        """Test initialization with OpenAI backend."""
        service = LLMService(backend="openai")
        assert service.backend == "openai"
        assert service.openai_client is not None
        assert service.openai_model == "gpt-3.5-turbo"

    def test_init_openai_backend_custom_model(self, mock_openai_api_key):
        """Test initialization with custom OpenAI model."""
        service = LLMService(backend="openai", openai_model="gpt-4")
        assert service.openai_model == "gpt-4"

    def test_init_local_backend(self, mock_vllm_endpoint):
        """Test initialization with local backend."""
        service = LLMService(backend="local")
        assert service.backend == "local"
        assert service.vllm_endpoint == "http://localhost:8000/"

    def test_init_local_backend_custom_endpoint(self):
        """Test initialization with custom vLLM endpoint."""
        service = LLMService(backend="local", vllm_endpoint="http://custom:9000")
        assert service.vllm_endpoint == "http://custom:9000/"

    def test_init_backend_from_env(self, mock_openai_api_key):
        """Test backend selection from environment variable."""
        with patch.dict(os.environ, {"LLM_BACKEND": "openai"}):
            service = LLMService()
            assert service.backend == "openai"

    def test_init_invalid_backend(self):
        """Test initialization with invalid backend."""
        with pytest.raises(ValueError, match="Unsupported backend"):
            LLMService(backend="invalid")

    def test_init_openai_missing_key(self):
        """Test initialization without OpenAI API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key is required"):
                LLMService(backend="openai")

    @patch("app.services.llm_service.OpenAI")
    def test_summarize_openai(self, mock_openai_class, mock_openai_api_key):
        """Test summarization with OpenAI backend."""
        # Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is a summary."
        mock_client.chat.completions.create.return_value = mock_response

        service = LLMService(backend="openai")
        result = service.summarize("This is a long text to summarize.")

        assert result == "This is a summary."
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-3.5-turbo"
        assert "messages" in call_args[1]

    @patch("app.services.llm_service.requests.post")
    def test_summarize_local(self, mock_post, mock_vllm_endpoint):
        """Test summarization with local vLLM backend."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Local summary."}}]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        service = LLMService(backend="local")
        result = service.summarize("This is a long text to summarize.")

        assert result == "Local summary."
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "json" in call_args[1]
        assert "messages" in call_args[1]["json"]

    @patch("app.services.llm_service.OpenAI")
    def test_summarize_with_context(self, mock_openai_class, mock_openai_api_key):
        """Test summarization with context."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Summary with context."
        mock_client.chat.completions.create.return_value = mock_response

        service = LLMService(backend="openai")
        result = service.summarize("Text", context="Some context")

        assert result == "Summary with context."
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        assert "context" in messages[0]["content"].lower()

    @patch("app.services.llm_service.OpenAI")
    def test_classify_openai(self, mock_openai_class, mock_openai_api_key):
        """Test classification with OpenAI backend."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"label": "positive", "confidence": 0.95}'
        mock_client.chat.completions.create.return_value = mock_response

        service = LLMService(backend="openai")
        result = service.classify("This is positive text.", labels=["positive", "negative"])

        assert result["label"] == "positive"
        assert result["confidence"] == 0.95
        mock_client.chat.completions.create.assert_called_once()

    @patch("app.services.llm_service.requests.post")
    def test_classify_local(self, mock_post, mock_vllm_endpoint):
        """Test classification with local vLLM backend."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"label": "negative"}'}}]
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        service = LLMService(backend="local")
        result = service.classify("This is negative text.", labels=["positive", "negative"])

        assert result["label"] == "negative"
        mock_post.assert_called_once()

    @patch("app.services.llm_service.OpenAI")
    def test_classify_with_json_markdown(self, mock_openai_class, mock_openai_api_key):
        """Test classification with JSON wrapped in markdown code blocks."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '```json\n{"label": "neutral"}\n```'
        mock_client.chat.completions.create.return_value = mock_response

        service = LLMService(backend="openai")
        result = service.classify("Text", labels=["positive", "negative", "neutral"])

        assert result["label"] == "neutral"

    @patch("app.services.llm_service.OpenAI")
    def test_classify_with_extra_text(self, mock_openai_class, mock_openai_api_key):
        """Test classification with extra text before/after JSON."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            'Here is the classification: {"label": "positive"} That is the result.'
        )
        mock_client.chat.completions.create.return_value = mock_response

        service = LLMService(backend="openai")
        result = service.classify("Text", labels=["positive", "negative"])

        assert result["label"] == "positive"

    @patch("app.services.llm_service.OpenAI")
    def test_classify_invalid_label(self, mock_openai_class, mock_openai_api_key):
        """Test classification with invalid label."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"label": "invalid"}'
        mock_client.chat.completions.create.return_value = mock_response

        service = LLMService(backend="openai")
        with pytest.raises(LLMServiceError, match="Invalid label"):
            service.classify("Text", labels=["positive", "negative"])

    @patch("app.services.llm_service.OpenAI")
    def test_classify_missing_label(self, mock_openai_class, mock_openai_api_key):
        """Test classification response missing label field."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"confidence": 0.9}'
        mock_client.chat.completions.create.return_value = mock_response

        service = LLMService(backend="openai")
        with pytest.raises(LLMServiceError, match="missing 'label' field"):
            service.classify("Text", labels=["positive", "negative"])

    @patch("app.services.llm_service.OpenAI")
    def test_classify_invalid_json(self, mock_openai_class, mock_openai_api_key):
        """Test classification with invalid JSON response."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Not valid JSON"
        mock_client.chat.completions.create.return_value = mock_response

        service = LLMService(backend="openai")
        with pytest.raises(LLMServiceError, match="Failed to parse classification response"):
            service.classify("Text", labels=["positive", "negative"])

    @patch("app.services.llm_service.OpenAI")
    def test_summarize_retry_on_error(self, mock_openai_class, mock_openai_api_key):
        """Test retry logic on OpenAI API error."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # First call fails, second succeeds
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Retried summary."
        mock_client.chat.completions.create.side_effect = [
            openai.APIError("Temporary error", request=None),
            mock_response,
        ]

        service = LLMService(backend="openai")
        result = service.summarize("Text")

        assert result == "Retried summary."
        assert mock_client.chat.completions.create.call_count == 2

    @patch("app.services.llm_service.requests.post")
    def test_summarize_retry_on_http_error(self, mock_post, mock_vllm_endpoint):
        """Test retry logic on HTTP error."""
        mock_response_success = MagicMock()
        mock_response_success.json.return_value = {
            "choices": [{"message": {"content": "Retried summary."}}]
        }
        mock_response_success.raise_for_status = Mock()

        # First call fails, second succeeds
        mock_post.side_effect = [
            requests.RequestException("Connection error"),
            mock_response_success,
        ]

        service = LLMService(backend="local")
        result = service.summarize("Text")

        assert result == "Retried summary."
        assert mock_post.call_count == 2

    @patch("app.services.llm_service.OpenAI")
    def test_summarize_max_retries_exceeded(self, mock_openai_class, mock_openai_api_key):
        """Test that max retries are respected."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = openai.APIError(
            "Persistent error", request=None
        )

        service = LLMService(backend="openai", max_retries=2)
        with pytest.raises(LLMServiceError):
            service.summarize("Text")

        # Should retry 2 times (initial + 2 retries = 3 total attempts)
        assert mock_client.chat.completions.create.call_count == 3

    @patch("app.services.llm_service.OpenAI")
    def test_classify_with_context(self, mock_openai_class, mock_openai_api_key):
        """Test classification with context."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"label": "positive"}'
        mock_client.chat.completions.create.return_value = mock_response

        service = LLMService(backend="openai")
        result = service.classify(
            "Text", labels=["positive", "negative"], context="Review context"
        )

        assert result["label"] == "positive"
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        assert "context" in messages[0]["content"].lower()

    def test_parse_classification_response_valid(self):
        """Test parsing valid classification response."""
        service = LLMService(backend="openai", openai_api_key="test")
        result = service._parse_classification_response(
            '{"label": "positive", "confidence": 0.9}', ["positive", "negative"]
        )
        assert result["label"] == "positive"
        assert result["confidence"] == 0.9

    def test_parse_classification_response_invalid_label(self):
        """Test parsing with invalid label."""
        service = LLMService(backend="openai", openai_api_key="test")
        with pytest.raises(LLMServiceError, match="Invalid label"):
            service._parse_classification_response(
                '{"label": "invalid"}', ["positive", "negative"]
            )
