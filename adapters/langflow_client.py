"""
Langflow client adapter for running flows via HTTP API.

This module provides a client interface to interact with Langflow server,
allowing execution of configured flows with input data.
"""

import os
import requests
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class LangflowClient:
    """Client for interacting with Langflow server API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize Langflow client.

        Args:
            base_url: Base URL of Langflow server (defaults to LANGFLOW_BASE_URL env var)
            api_key: API key for authentication (defaults to LANGFLOW_API_KEY env var)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or os.getenv("LANGFLOW_BASE_URL", "http://localhost:7860")
        self.api_key = api_key or os.getenv("LANGFLOW_API_KEY")
        self.timeout = timeout

        # Ensure base_url doesn't end with a slash
        self.base_url = self.base_url.rstrip("/")

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for API requests."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def run_flow(self, flow_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a Langflow flow with the given inputs.

        Args:
            flow_id: The ID of the flow to run
            inputs: Dictionary of input data to pass to the flow

        Returns:
            Dictionary containing the flow execution results

        Raises:
            requests.RequestException: If the HTTP request fails
            ValueError: If the response indicates an error
        """
        url = f"{self.base_url}/api/v1/run/{flow_id}"

        logger.info(f"Running flow {flow_id} with inputs: {list(inputs.keys())}")

        try:
            response = requests.post(
                url,
                json={"inputs": inputs},
                headers=self._get_headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()

            result = response.json()
            logger.info(f"Flow {flow_id} completed successfully")
            return result

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to run flow {flow_id}: {e}")
            raise
        except ValueError as e:
            logger.error(f"Invalid response from flow {flow_id}: {e}")
            raise


def run_flow(flow_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to run a Langflow flow.

    Args:
        flow_id: The ID of the flow to run
        inputs: Dictionary of input data to pass to the flow

    Returns:
        Dictionary containing the flow execution results
    """
    client = LangflowClient()
    return client.run_flow(flow_id, inputs)
