"""Base classes for vector stores."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class VectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    def add_embeddings(
        self,
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Add embeddings to the vector store.

        Args:
            embeddings: List of embedding vectors
            metadatas: Optional list of metadata dictionaries
            ids: Optional list of IDs for the embeddings

        Returns:
            List of IDs that were added
        """
        pass

    @abstractmethod
    def similarity_search(
        self,
        query_embedding: List[float],
        k: int = 4,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar embeddings.

        Args:
            query_embedding: Query embedding vector
            k: Number of results to return
            where: Optional metadata filter dictionary

        Returns:
            List of dictionaries containing 'id', 'embedding', 'metadata', and 'distance'
        """
        pass

    @abstractmethod
    def delete(self, ids: Optional[List[str]] = None, where: Optional[Dict[str, Any]] = None) -> None:
        """
        Delete embeddings from the vector store.

        Args:
            ids: Optional list of IDs to delete
            where: Optional metadata filter dictionary
        """
        pass
