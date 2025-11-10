"""Langflow client adapter."""
import httpx
import os
from typing import Optional


class LangflowClient:
    """Client for Langflow API."""
    
    def __init__(self):
        self.base_url = os.getenv("LANGFLOW_URL", "http://localhost:7860")
        self.api_key = os.getenv("LANGFLOW_API_KEY", "")
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def generate(self, prompt: str) -> str:
        """Generate a response using Langflow."""
        url = f"{self.base_url}/api/v1/run"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "input_value": prompt,
            "output_type": "chat",
            "input_type": "chat",
        }
        
        response = await self.client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        
        # Extract the generated text from response
        if isinstance(result, dict) and "outputs" in result:
            outputs = result["outputs"]
            if outputs and len(outputs) > 0:
                return outputs[0].get("outputs", [{}])[0].get("results", {}).get("message", {}).get("content", "")
        
        return str(result)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
