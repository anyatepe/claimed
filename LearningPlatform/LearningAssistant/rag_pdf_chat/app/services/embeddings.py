"""Embeddings service."""
from sentence_transformers import SentenceTransformer
from typing import List


class EmbeddingsService:
    """Service for generating text embeddings."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
    
    def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a query."""
        return self.model.encode(text).tolist()
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple documents."""
        return self.model.encode(texts).tolist()
