"""Retriever service for semantic search with optional reranking."""
from typing import List, Optional, Any
import logging

try:
    from sentence_transformers import CrossEncoder
except ImportError:
    CrossEncoder = None

from app.models import ContextChunk

logger = logging.getLogger(__name__)


class Retriever:
    """Retriever service that performs semantic search with optional reranking."""
    
    def __init__(
        self,
        embedding_service: Any,
        vector_store: Any,
        rerank: bool = True,
        rerank_model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    ):
        """
        Initialize the Retriever.
        
        Args:
            embedding_service: Service that provides embed() method for text embedding
            vector_store: Vector store that provides similarity_search() method
            rerank: Whether to use reranking (default: True)
            rerank_model_name: Name of the cross-encoder model for reranking
        """
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.rerank = rerank
        self.rerank_model_name = rerank_model_name
        self._cross_encoder = None
        
        if self.rerank:
            if CrossEncoder is None:
                logger.warning(
                    "sentence_transformers not available. Reranking will be disabled. "
                    "Install with: pip install sentence-transformers"
                )
                self.rerank = False
            else:
                try:
                    self._cross_encoder = CrossEncoder(rerank_model_name)
                    logger.info(f"Loaded reranking model: {rerank_model_name}")
                except Exception as e:
                    logger.warning(f"Failed to load reranking model: {e}. Reranking disabled.")
                    self.rerank = False
    
    def retrieve(
        self,
        query_text: str,
        k: int = 6,
        filters: Optional[dict] = None
    ) -> List[ContextChunk]:
        """
        Retrieve relevant context chunks for a query.
        
        Args:
            query_text: The query text to search for
            k: Number of chunks to retrieve (default: 6)
            filters: Optional filters to apply to the search
            
        Returns:
            List of ContextChunk objects sorted by relevance (highest score first)
        """
        # Step 1: Embed the query
        query_embedding = self.embedding_service.embed(query_text)
        
        # Step 2: Perform similarity search
        # Fetch more results if reranking is enabled to improve reranking quality
        search_k = k * 3 if self.rerank else k
        results = self.vector_store.similarity_search(
            query_embedding,
            k=search_k,
            filters=filters
        )
        
        # Convert results to ContextChunk objects
        chunks = self._results_to_chunks(results)
        
        # Step 3: Optional reranking using cross-encoder
        if self.rerank and self._cross_encoder and len(chunks) > 0:
            chunks = self._rerank(query_text, chunks, k)
        
        # Return top k chunks
        return chunks[:k]
    
    def _results_to_chunks(self, results: List[Any]) -> List[ContextChunk]:
        """
        Convert vector store results to ContextChunk objects.
        
        Assumes results have attributes/metadata: text, doc_id, page, score, citation_id
        """
        chunks = []
        for result in results:
            # Handle different result formats
            if hasattr(result, 'text'):
                text = result.text
            elif isinstance(result, dict):
                text = result.get('text', result.get('content', ''))
            else:
                text = str(result)
            
            # Extract metadata
            if hasattr(result, 'metadata'):
                metadata = result.metadata
            elif isinstance(result, dict):
                metadata = result
            else:
                metadata = {}
            
            # Extract score
            if hasattr(result, 'score'):
                score = result.score
            elif hasattr(result, 'distance'):
                # Convert distance to score (assuming cosine similarity)
                score = 1.0 - result.distance
            elif isinstance(result, dict) and 'score' in result:
                score = result['score']
            else:
                score = metadata.get('score', 0.0)
            
            chunk = ContextChunk(
                text=text,
                doc_id=metadata.get('doc_id', metadata.get('document_id', '')),
                page=metadata.get('page'),
                score=float(score),
                citation_id=metadata.get('citation_id', metadata.get('citation', None))
            )
            chunks.append(chunk)
        
        return chunks
    
    def _rerank(
        self,
        query_text: str,
        chunks: List[ContextChunk],
        k: int
    ) -> List[ContextChunk]:
        """
        Rerank chunks using a cross-encoder model.
        
        Args:
            query_text: The original query text
            chunks: List of chunks to rerank
            k: Number of top chunks to return
            
        Returns:
            Reranked list of chunks
        """
        if not chunks:
            return chunks
        
        # Prepare pairs for cross-encoder: (query, chunk_text)
        pairs = [(query_text, chunk.text) for chunk in chunks]
        
        # Get reranking scores
        try:
            rerank_scores = self._cross_encoder.predict(pairs)
        except Exception as e:
            logger.error(f"Error during reranking: {e}. Returning original order.")
            return chunks
        
        # Update scores and sort by rerank score
        for chunk, rerank_score in zip(chunks, rerank_scores):
            chunk.score = float(rerank_score)
        
        # Sort by score (descending)
        reranked_chunks = sorted(chunks, key=lambda x: x.score, reverse=True)
        
        return reranked_chunks
