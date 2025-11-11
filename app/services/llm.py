"""LLM Service supporting multiple providers with retry logic and timeouts."""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Union

import httpx
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from openai import OpenAI
from openai._exceptions import APIError, APITimeoutError

logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """Base exception for LLM service errors."""

    pass


class LLMService:
    """Service for interacting with LLM providers (OpenAI and local vLLM)."""

    def __init__(
        self,
        provider: str = "openai",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """
        Initialize LLM service.

        Args:
            provider: Provider name ("openai" or "local")
            api_key: API key for OpenAI (defaults to OPENAI_API_KEY env var)
            base_url: Base URL for local provider (defaults to http://localhost:8000/v1)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.provider = provider.lower()
        self.timeout = timeout
        self.max_retries = max_retries

        if self.provider == "openai":
            self.client = OpenAI(
                api_key=api_key or os.getenv("OPENAI_API_KEY"),
                timeout=timeout,
            )
        elif self.provider == "local":
            self.base_url = base_url or os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1")
            self.api_key = api_key or os.getenv("VLLM_API_KEY")
        else:
            raise ValueError(f"Unsupported provider: {provider}. Must be 'openai' or 'local'")

    def chat(
        self,
        prompt_messages: List[Dict[str, str]],
        json_mode: bool = False,
        max_tokens: int = 512,
        temperature: float = 0.2,
    ) -> Union[str, Dict[str, Any]]:
        """
        Send chat completion request to LLM provider.

        Args:
            prompt_messages: List of message dicts with 'role' and 'content' keys
            json_mode: If True, parse response as JSON and return dict
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 2.0)

        Returns:
            Response text as string, or parsed JSON dict if json_mode=True

        Raises:
            LLMServiceError: If request fails or JSON parsing fails
        """
        # Use tenacity Retrying with instance-specific max_retries
        retry_strategy = Retrying(
            retry=retry_if_exception_type((APIError, APITimeoutError, httpx.HTTPError, httpx.TimeoutException)),
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            reraise=True,
        )

        try:
            return retry_strategy(self._execute_chat)(
                prompt_messages=prompt_messages,
                json_mode=json_mode,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except (APIError, APITimeoutError, httpx.HTTPError, httpx.TimeoutException) as e:
            logger.error(f"LLM request failed after {self.max_retries} retries: {e}")
            raise LLMServiceError(f"LLM request failed: {e}") from e
        except LLMServiceError:
            # Re-raise LLMServiceError (e.g., from JSON parsing)
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise LLMServiceError(f"Unexpected error: {e}") from e

    def _execute_chat(
        self,
        prompt_messages: List[Dict[str, str]],
        json_mode: bool,
        max_tokens: int,
        temperature: float,
    ) -> Union[str, Dict[str, Any]]:
        """Execute chat request (called by retry logic)."""
        if self.provider == "openai":
            response = self._chat_openai(
                prompt_messages=prompt_messages,
                json_mode=json_mode,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        elif self.provider == "local":
            response = self._chat_local(
                prompt_messages=prompt_messages,
                json_mode=json_mode,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

        if json_mode:
            try:
                return self._parse_json_safe(response)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed: {e}")
                raise LLMServiceError(f"Failed to parse JSON response: {e}") from e
        return response

    def _chat_openai(
        self,
        prompt_messages: List[Dict[str, str]],
        json_mode: bool,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Send chat completion request to OpenAI."""
        extra_kwargs = {}
        if json_mode:
            extra_kwargs["response_format"] = {"type": "json_object"}

        completion = self.client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
            messages=prompt_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            **extra_kwargs,
        )

        content = completion.choices[0].message.content
        if content is None:
            raise LLMServiceError("Empty response from OpenAI")
        return content

    def _chat_local(
        self,
        prompt_messages: List[Dict[str, str]],
        json_mode: bool,
        max_tokens: int,
        temperature: float,
    ) -> str:
        """Send chat completion request to local vLLM server."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": os.getenv("VLLM_MODEL", "default"),
            "messages": prompt_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            result = response.json()

        if "choices" not in result or not result["choices"]:
            raise LLMServiceError("Invalid response format from local provider")

        content = result["choices"][0].get("message", {}).get("content")
        if content is None:
            raise LLMServiceError("Empty response from local provider")
        return content

    def _parse_json_safe(self, text: str) -> Dict[str, Any]:
        """
        Safely parse JSON from text, handling common issues.

        Args:
            text: Text that should contain JSON

        Returns:
            Parsed JSON as dict

        Raises:
            LLMServiceError: If JSON parsing fails
        """
        text = text.strip()

        # Try to extract JSON from markdown code blocks if present
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end != -1:
                text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end != -1:
                text = text[start:end].strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON, attempting to fix common issues: {e}")
            # Try to fix common JSON issues
            # Remove trailing commas
            text = text.replace(",}", "}").replace(",]", "]")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                raise LLMServiceError(f"Failed to parse JSON: {e}") from e
