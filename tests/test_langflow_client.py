"""Tests for Langflow client adapter."""

import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
import os

from adapters.langflow_client import LangflowClient, run_flow


class TestLangflowClient:
    """Test cases for LangflowClient."""

    def test_init_with_defaults(self):
        """Test client initialization with default values."""
        with patch.dict(os.environ, {}, clear=True):
            client = LangflowClient()
            assert client.base_url == "http://localhost:7860"
            assert client.api_key is None
            assert client.timeout == 30

    def test_init_with_env_vars(self):
        """Test client initialization with environment variables."""
        with patch.dict(
            os.environ,
            {
                "LANGFLOW_BASE_URL": "http://test-server:8080",
                "LANGFLOW_API_KEY": "test-api-key",
            },
            clear=False,
        ):
            client = LangflowClient()
            assert client.base_url == "http://test-server:8080"
            assert client.api_key == "test-api-key"

    def test_init_with_parameters(self):
        """Test client initialization with explicit parameters."""
        client = LangflowClient(
            base_url="http://custom:9000",
            api_key="custom-key",
            timeout=60,
        )
        assert client.base_url == "http://custom:9000"
        assert client.api_key == "custom-key"
        assert client.timeout == 60

    def test_init_strips_trailing_slash(self):
        """Test that base_url trailing slash is stripped."""
        client = LangflowClient(base_url="http://test.com/")
        assert client.base_url == "http://test.com"

    def test_get_headers_without_api_key(self):
        """Test headers generation without API key."""
        client = LangflowClient()
        headers = client._get_headers()
        assert headers == {"Content-Type": "application/json"}

    def test_get_headers_with_api_key(self):
        """Test headers generation with API key."""
        client = LangflowClient(api_key="test-key")
        headers = client._get_headers()
        assert headers == {
            "Content-Type": "application/json",
            "Authorization": "Bearer test-key",
        }

    @patch("adapters.langflow_client.requests.post")
    def test_run_flow_success(self, mock_post):
        """Test successful flow execution."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "outputs": {"result": "test output"},
            "status": "success",
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Execute
        client = LangflowClient(base_url="http://test.com")
        result = client.run_flow("test-flow-id", {"input": "test data"})

        # Verify
        assert result == {"outputs": {"result": "test output"}, "status": "success"}
        mock_post.assert_called_once_with(
            "http://test.com/api/v1/run/test-flow-id",
            json={"inputs": {"input": "test data"}},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        mock_response.raise_for_status.assert_called_once()

    @patch("adapters.langflow_client.requests.post")
    def test_run_flow_with_api_key(self, mock_post):
        """Test flow execution with API key authentication."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = LangflowClient(
            base_url="http://test.com", api_key="secret-key"
        )
        client.run_flow("flow-123", {"data": "test"})

        mock_post.assert_called_once_with(
            "http://test.com/api/v1/run/flow-123",
            json={"inputs": {"data": "test"}},
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer secret-key",
            },
            timeout=30,
        )

    @patch("adapters.langflow_client.requests.post")
    def test_run_flow_http_error(self, mock_post):
        """Test handling of HTTP errors."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError(
            "400 Bad Request"
        )
        mock_post.return_value = mock_response

        client = LangflowClient()
        with pytest.raises(requests.RequestException):
            client.run_flow("flow-id", {"input": "data"})

    @patch("adapters.langflow_client.requests.post")
    def test_run_flow_connection_error(self, mock_post):
        """Test handling of connection errors."""
        mock_post.side_effect = requests.ConnectionError("Connection failed")

        client = LangflowClient()
        with pytest.raises(requests.RequestException):
            client.run_flow("flow-id", {"input": "data"})

    @patch("adapters.langflow_client.requests.post")
    def test_run_flow_timeout(self, mock_post):
        """Test handling of timeout errors."""
        mock_post.side_effect = requests.Timeout("Request timed out")

        client = LangflowClient(timeout=10)
        with pytest.raises(requests.RequestException):
            client.run_flow("flow-id", {"input": "data"})

    @patch("adapters.langflow_client.requests.post")
    def test_run_flow_invalid_json(self, mock_post):
        """Test handling of invalid JSON response."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = LangflowClient()
        with pytest.raises(ValueError):
            client.run_flow("flow-id", {"input": "data"})


class TestRunFlowFunction:
    """Test cases for the convenience run_flow function."""

    @patch("adapters.langflow_client.LangflowClient")
    def test_run_flow_function(self, mock_client_class):
        """Test the convenience run_flow function."""
        mock_client = Mock()
        mock_client.run_flow.return_value = {"result": "success"}
        mock_client_class.return_value = mock_client

        result = run_flow("test-flow", {"input": "data"})

        assert result == {"result": "success"}
        mock_client.run_flow.assert_called_once_with("test-flow", {"input": "data"})
