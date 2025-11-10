"""Pinecone vector store adapter."""
import logging
from typing import Any, Dict, List, Optional

try:
    import pinecone
    from pinecone import Pinecone, ServerlessSpec
except ImportError:
    raise ImportError(
        "pinecone-client is required. Install it with: pip install pinecone-client"
    )

from .base import VectorStore

logger = logging.getLogger(__name__)


class PineconeStore(VectorStore):
    """Pinecone vector store implementation."""
    
    def __init__(
        self,
        api_key: str,
        index_name: str,
        embedding_model: Any,
        environment: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ):
        """Initialize PineconeStore.
        
        Args:
            api_key: Pinecone API key
            index_name: Name of the Pinecone index
            embedding_model: Embedding model instance with a dimension attribute
            environment: Optional Pinecone environment (for legacy API)
            tenant_id: Optional tenant ID for namespace isolation
        """
        self.api_key = api_key
        self.index_name = index_name
        self.embedding_model = embedding_model
        self.tenant_id = tenant_id
        self.namespace = tenant_id if tenant_id else "default"
        
        # Initialize Pinecone client
        self.pc = Pinecone(api_key=api_key)
        
        # Get or create index
        self._ensure_index_exists()
        
        # Get index instance
        self.index = self.pc.Index(index_name)
    
    def _get_embedding_dimension(self) -> int:
        """Get the dimension from the embedding model."""
        if hasattr(self.embedding_model, 'dimension'):
            return self.embedding_model.dimension
        elif hasattr(self.embedding_model, 'get_dimension'):
            return self.embedding_model.get_dimension()
        elif hasattr(self.embedding_model, 'model_dimension'):
            return self.embedding_model.model_dimension
        else:
            # Try to infer from a sample embedding
            try:
                sample_embedding = self.embedding_model.embed_query("sample")
                return len(sample_embedding)
            except Exception as e:
                raise ValueError(
                    f"Could not determine embedding dimension from model: {e}. "
                    "Please ensure the model has a 'dimension' attribute or can generate embeddings."
                )
    
    def _ensure_index_exists(self) -> None:
        """Create index if it doesn't exist."""
        dimension = self._get_embedding_dimension()
        
        # Check if index exists
        existing_indexes = [idx.name for idx in self.pc.list_indexes()]
        
        if self.index_name not in existing_indexes:
            logger.info(
                f"Creating Pinecone index '{self.index_name}' with dimension {dimension}"
            )
            self.pc.create_index(
                name=self.index_name,
                dimension=dimension,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
            logger.info(f"Index '{self.index_name}' created successfully")
        else:
            logger.debug(f"Index '{self.index_name}' already exists")
    
    def upsert(
        self,
        vectors: List[List[float]],
        ids: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Upsert vectors into Pinecone with batch support.
        
        Args:
            vectors: List of embedding vectors
            ids: List of unique identifiers for each vector
            metadata: Optional list of metadata dictionaries for each vector
        """
        if len(vectors) != len(ids):
            raise ValueError("Number of vectors must match number of ids")
        
        if metadata is not None and len(metadata) != len(vectors):
            raise ValueError("Number of metadata entries must match number of vectors")
        
        # Prepare vectors for upsert
        vectors_to_upsert = []
        for i, (vector, vector_id) in enumerate(zip(vectors, ids)):
            vector_data = {
                "id": vector_id,
                "values": vector,
            }
            
            if metadata is not None:
                vector_data["metadata"] = metadata[i]
            
            vectors_to_upsert.append(vector_data)
        
        # Batch upsert
        batch_size = 100  # Pinecone recommended batch size
        for i in range(0, len(vectors_to_upsert), batch_size):
            batch = vectors_to_upsert[i:i + batch_size]
            self.index.upsert(
                vectors=batch,
                namespace=self.namespace
            )
        
        logger.debug(
            f"Upserted {len(vectors_to_upsert)} vectors to namespace '{self.namespace}'"
        )
    
    def similarity_search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors with optional metadata filtering.
        
        Args:
            query_vector: The query embedding vector
            top_k: Number of results to return
            filter: Optional metadata filter dictionary
            
        Returns:
            List of dictionaries containing 'id', 'score', and 'metadata' keys
        """
        query_kwargs = {
            "vector": query_vector,
            "top_k": top_k,
            "namespace": self.namespace,
            "include_metadata": True,
        }
        
        if filter is not None:
            query_kwargs["filter"] = filter
        
        results = self.index.query(**query_kwargs)
        
        # Format results
        formatted_results = []
        for match in results.matches:
            formatted_results.append({
                "id": match.id,
                "score": match.score,
                "metadata": match.metadata or {},
            })
        
        return formatted_results
