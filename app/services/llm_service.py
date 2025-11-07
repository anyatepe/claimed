"""LLM Service for text summarization and classification.

Supports multiple backends:
- OpenAI: Uses OpenAI ChatCompletion API
- Local: Uses vLLM endpoint via HTTP
"""

import json
import logging
import os
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

import openai
import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """Base exception for LLM service errors."""

    pass


class LLMService:
    """Service for LLM operations with multiple backend support."""

    def __init__(
        self,
        backend: Optional[str] = None,
        openai_api_key: Optional[str] = None,
        openai_model: str = "gpt-3.5-turbo",
        vllm_endpoint: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """Initialize LLM service.

        Args:
            backend: Backend to use ("openai" or "local"). If None, reads from
                LLM_BACKEND env var or defaults to "openai".
            openai_api_key: OpenAI API key. If None, reads from OPENAI_API_KEY env var.
            openai_model: OpenAI model to use. Defaults to "gpt-3.5-turbo".
            vllm_endpoint: vLLM endpoint URL. If None, reads from VLLM_ENDPOINT env var.
            max_retries: Maximum number of retry attempts. Defaults to 3.
            retry_delay: Initial delay between retries in seconds. Defaults to 1.0.
        """
        self.backend = backend or os.getenv("LLM_BACKEND", "openai")
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        if self.backend == "openai":
            self._init_openai(openai_api_key, openai_model)
        elif self.backend == "local":
            self._init_local(vllm_endpoint)
        else:
            raise ValueError(
                f"Unsupported backend: {self.backend}. Must be 'openai' or 'local'."
            )

    def _init_openai(self, api_key: Optional[str], model: str):
        """Initialize OpenAI backend."""
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY env var or pass openai_api_key."
            )
        self.openai_client = openai.OpenAI(api_key=api_key)
        self.openai_model = model
        logger.info(f"Initialized OpenAI backend with model: {model}")

    def _init_local(self, endpoint: Optional[str]):
        """Initialize local vLLM backend."""
        endpoint = endpoint or os.getenv("VLLM_ENDPOINT", "http://localhost:8000")
        if not endpoint.endswith("/"):
            endpoint += "/"
        self.vllm_endpoint = endpoint
        self.vllm_completions_url = urljoin(endpoint, "v1/completions")
        self.vllm_chat_url = urljoin(endpoint, "v1/chat/completions")
        logger.info(f"Initialized local vLLM backend with endpoint: {endpoint}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((requests.RequestException, openai.APIError)),
        reraise=True,
    )
    def summarize(self, text: str, context: Optional[str] = None) -> str:
        """Summarize the given text.

        Args:
            text: Text to summarize.
            context: Optional context to include in the prompt.

        Returns:
            Summarized text.

        Raises:
            LLMServiceError: If summarization fails.
        """
        prompt = self._build_summarize_prompt(text, context)

        try:
            if self.backend == "openai":
                response = self._summarize_openai(prompt)
            else:  # local
                response = self._summarize_local(prompt)

            return response.strip()
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            raise LLMServiceError(f"Failed to summarize text: {e}") from e

    def _build_summarize_prompt(self, text: str, context: Optional[str]) -> str:
        """Build the summarization prompt."""
        prompt_parts = ["Please provide a concise summary of the following text:"]
        if context:
            prompt_parts.append(f"\nContext: {context}")
        prompt_parts.append(f"\n\nText:\n{text}")
        return "\n".join(prompt_parts)

    def _summarize_openai(self, prompt: str) -> str:
        """Summarize using OpenAI backend."""
        response = self.openai_client.chat.completions.create(
            model=self.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500,
        )
        return response.choices[0].message.content

    def _summarize_local(self, prompt: str) -> str:
        """Summarize using local vLLM backend."""
        payload = {
            "model": "default",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 500,
        }
        response = requests.post(
            self.vllm_chat_url,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((requests.RequestException, openai.APIError)),
        reraise=True,
    )
    def classify(
        self,
        text: str,
        labels: List[str],
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Classify text into one of the given labels.

        Args:
            text: Text to classify.
            labels: List of possible classification labels.
            context: Optional context to include in the prompt.

        Returns:
            Dictionary with 'label' (selected label) and 'confidence' (optional).

        Raises:
            LLMServiceError: If classification fails or JSON parsing fails.
        """
        prompt = self._build_classify_prompt(text, labels, context)

        try:
            if self.backend == "openai":
                response_text = self._classify_openai(prompt)
            else:  # local
                response_text = self._classify_local(prompt)

            return self._parse_classification_response(response_text, labels)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse classification JSON: {e}")
            raise LLMServiceError(f"Failed to parse classification response: {e}") from e
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            raise LLMServiceError(f"Failed to classify text: {e}") from e

    def _build_classify_prompt(self, text: str, labels: List[str], context: Optional[str]) -> str:
        """Build the classification prompt with JSON format instruction."""
        prompt_parts = [
            "Classify the following text into one of the given labels.",
            "Respond with a JSON object containing 'label' and optionally 'confidence'.",
        ]
        if context:
            prompt_parts.append(f"\nContext: {context}")
        prompt_parts.append(f"\n\nLabels: {', '.join(labels)}")
        prompt_parts.append(f"\n\nText:\n{text}")
        prompt_parts.append("\n\nRespond with JSON only, no additional text.")
        return "\n".join(prompt_parts)

    def _classify_openai(self, prompt: str) -> str:
        """Classify using OpenAI backend."""
        response = self.openai_client.chat.completions.create(
            model=self.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200,
        )
        return response.choices[0].message.content

    def _classify_local(self, prompt: str) -> str:
        """Classify using local vLLM backend."""
        payload = {
            "model": "default",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 200,
        }
        response = requests.post(
            self.vllm_chat_url,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]

    def _parse_classification_response(
        self, response_text: str, labels: List[str]
    ) -> Dict[str, Any]:
        """Parse classification response and validate label.

        Args:
            response_text: Raw response text from LLM.
            labels: Valid labels to check against.

        Returns:
            Parsed classification dictionary.

        Raises:
            LLMServiceError: If JSON parsing fails or label is invalid.
        """
        # Try to extract JSON from response (might have markdown code blocks)
        original_text = response_text.strip()
        response_text = original_text
        
        if response_text.startswith("```"):
            # Remove markdown code blocks
            lines = response_text.split("\n")
            json_lines = [l for l in lines if not l.strip().startswith("```")]
            response_text = "\n".join(json_lines)

        # Try to find JSON object in the response
        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}")
        if start_idx != -1 and end_idx != -1:
            extracted_json = response_text[start_idx : end_idx + 1]
        else:
            extracted_json = response_text

        # Try parsing extracted JSON first
        try:
            result = json.loads(extracted_json)
        except json.JSONDecodeError:
            # If extraction failed, try parsing the original text
            try:
                result = json.loads(original_text)
            except json.JSONDecodeError as e:
                raise LLMServiceError(f"Failed to parse JSON response: {e}") from e

        # Validate label
        if "label" not in result:
            raise LLMServiceError("Response missing 'label' field")
        if result["label"] not in labels:
            raise LLMServiceError(
                f"Invalid label '{result['label']}'. Must be one of: {labels}"
            )

        return result
