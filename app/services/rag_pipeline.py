"""
RAG Pipeline service for retrieval-augmented generation.

This module provides the RAGPipeline class for performing retrieval-augmented
summarization and classification using LangChain patterns.
"""

import hashlib
import json
from typing import List, Dict, Any, Optional, Protocol
from langchain.prompts import PromptTemplate

from app.services.cache import CacheService


class VectorStore(Protocol):
    """
    Protocol/interface for VectorStore.
    
    VectorStore should be imported from the appropriate module.
    This Protocol defines the expected interface: a search(query, k) method
    that returns a list of dictionaries containing retrieved chunks.
    """
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for relevant chunks given a query.
        
        Args:
            query: The search query
            k: Number of results to return
            
        Returns:
            List of dictionaries containing retrieved chunks with metadata
        """
        ...


class RAGPipeline:
    """
    Retrieval-Augmented Generation Pipeline.
    
    Provides methods for retrieval, summarization, and classification
    using retrieval-augmented generation patterns with LangChain.
    """
    
    def __init__(
        self, 
        vector_store: VectorStore, 
        llm: Optional[Any] = None,
        cache_service: Optional[CacheService] = None,
    ):
        """
        Initialize the RAG Pipeline.
        
        Args:
            vector_store: Instance of VectorStore for document retrieval
            llm: Optional LLM instance (stubbed out for now)
            cache_service: Optional CacheService for caching retrieval results
        """
        self.vector_store = vector_store
        self.llm = llm
        self.cache_service = cache_service
        
        # Initialize LangChain prompt templates
        self._initialize_prompts()
    
    def _get_query_hash(self, query: str) -> str:
        """Generate hash for a query."""
        return hashlib.sha256(query.encode()).hexdigest()
    
    def _initialize_prompts(self):
        """Initialize LangChain prompt templates for RAG operations."""
        
        # Summarization prompt template
        self.summarize_prompt = PromptTemplate(
            input_variables=["query", "context"],
            template="""Given the following context documents, provide a comprehensive summary that answers the query.

Query: {query}

Context Documents:
{context}

Please provide a detailed summary that addresses the query using information from the context documents above."""
        )
        
        # Classification prompt template
        self.classify_prompt = PromptTemplate(
            input_variables=["query", "labels", "context"],
            template="""Given the following context documents, classify the query into one of the provided labels.

Query: {query}

Available Labels: {labels}

Context Documents:
{context}

Please classify the query into one of the available labels based on the context provided. Return only the label name."""
        )
    
    async def retrieve(
        self, 
        query: str, 
        k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks from the vector store with caching.
        
        Args:
            query: The search query
            k: Number of chunks to retrieve (default: 5)
            filters: Optional filters dictionary for filtering results
            
        Returns:
            List of dictionaries containing retrieved chunks with metadata
        """
        query_hash = self._get_query_hash(query)
        
        # Try to get cached chunks
        if self.cache_service:
            cached_chunks = await self.cache_service.get_retrieval_cache(
                query_hash, filters
            )
            if cached_chunks is not None:
                return cached_chunks
        
        # Perform actual retrieval
        chunks = self.vector_store.search(query, k=k)
        
        # Cache the retrieved chunks
        if self.cache_service and chunks:
            await self.cache_service.set_retrieval_cache(
                query_hash, chunks, filters, ttl=300
            )
        
        return chunks
    
    def summarize_with_context(
        self, 
        query: str, 
        retrieved_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate a summary using retrieval-augmented generation.
        
        Uses LangChain patterns to compose a prompt with the query and
        retrieved context chunks. LLM calls are stubbed out and return
        the composed prompt for testing.
        
        Args:
            query: The query to summarize
            retrieved_chunks: List of retrieved document chunks with metadata
            
        Returns:
            Dictionary containing:
                - prompt: The composed prompt (for testing)
                - summary: Stubbed summary response
        """
        # Format context from retrieved chunks
        context_parts = []
        for i, chunk in enumerate(retrieved_chunks, 1):
            chunk_text = chunk.get('text', chunk.get('content', str(chunk)))
            chunk_metadata = chunk.get('metadata', {})
            
            context_part = f"[Document {i}]"
            if chunk_metadata:
                metadata_str = ", ".join([f"{k}: {v}" for k, v in chunk_metadata.items()])
                context_part += f" ({metadata_str})"
            context_part += f"\n{chunk_text}\n"
            context_parts.append(context_part)
        
        context = "\n".join(context_parts)
        
        # Compose prompt using LangChain template
        prompt = self.summarize_prompt.format(query=query, context=context)
        
        # Stub LLM call - return composed prompt for testing
        # In production, this would call: self.llm(prompt) or use LLMChain
        return {
            "prompt": prompt,
            "summary": f"[STUBBED] Summary for query: {query}",
            "retrieved_chunks_count": len(retrieved_chunks)
        }
    
    def classify_with_context(
        self,
        query: str,
        labels: List[str],
        retrieved_chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Classify a query using retrieval-augmented generation.
        
        Uses LangChain patterns to compose a classification prompt with the query,
        available labels, and retrieved context chunks. LLM calls are stubbed out
        and return the composed prompt for testing.
        
        Args:
            query: The query to classify
            labels: List of available classification labels
            retrieved_chunks: List of retrieved document chunks with metadata
            
        Returns:
            Dictionary containing:
                - prompt: The composed prompt (for testing)
                - classification: Stubbed classification result
                - confidence: Stubbed confidence score
        """
        # Format context from retrieved chunks
        context_parts = []
        for i, chunk in enumerate(retrieved_chunks, 1):
            chunk_text = chunk.get('text', chunk.get('content', str(chunk)))
            chunk_metadata = chunk.get('metadata', {})
            
            context_part = f"[Document {i}]"
            if chunk_metadata:
                metadata_str = ", ".join([f"{k}: {v}" for k, v in chunk_metadata.items()])
                context_part += f" ({metadata_str})"
            context_part += f"\n{chunk_text}\n"
            context_parts.append(context_part)
        
        context = "\n".join(context_parts)
        
        # Format labels as comma-separated string
        labels_str = ", ".join(labels)
        
        # Compose prompt using LangChain template
        prompt = self.classify_prompt.format(
            query=query,
            labels=labels_str,
            context=context
        )
        
        # Stub LLM call - return composed prompt for testing
        # In production, this would call: self.llm(prompt) or use LLMChain
        return {
            "prompt": prompt,
            "classification": labels[0] if labels else "[STUBBED] Unknown",
            "confidence": 0.85,  # Stubbed confidence score
            "retrieved_chunks_count": len(retrieved_chunks)
        }
