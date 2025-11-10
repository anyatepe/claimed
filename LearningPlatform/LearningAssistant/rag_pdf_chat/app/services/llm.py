"""LLM service."""
from typing import List, Optional
from app.adapters.langflow_client import LangflowClient


class LLMService:
    """Service for LLM interactions."""
    
    def __init__(self):
        self.client = LangflowClient()
    
    async def generate(
        self,
        query: str,
        context: List[str],
        history: Optional[List[dict]] = None,
    ) -> str:
        """Generate a response using LLM."""
        # Format context
        context_str = "\n\n".join([doc.page_content for doc in context])
        
        # Format history
        history_str = ""
        if history:
            history_str = "\n".join([
                f"Human: {h['query']}\nAssistant: {h['response']}"
                for h in history[-5:]  # Last 5 exchanges
            ])
        
        # Build prompt
        prompt = f"""Context from documents:
{context_str}

{history_str}

Human: {query}
Assistant:"""
        
        # Generate response
        response = await self.client.generate(prompt)
        return response
