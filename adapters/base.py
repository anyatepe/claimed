"""Base classes for vector store adapters."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class VectorStore(ABC):
    """Abstract base class for vector store implementations."""
    
    @abstractmethod
    def upsert(
        self,
        vectors: List[List[float]],
        ids: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Upsert vectors into the store.
        
        Args:
            vectors: List of embedding vectors
            ids: List of unique identifiers for each vector
            metadata: Optional list of metadata dictionaries for each vector
        """
        pass
    
    @abstractmethod
    def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors.
        
        Args:
            query_vector: The query embedding vector
            top_k: Number of results to return
            filter: Optional metadata filter dictionary
            
        Returns:
            List of dictionaries containing 'id', 'score', and 'metadata' keys
        """
        pass
