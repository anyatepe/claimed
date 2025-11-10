"""Embedding service with Redis caching and async batch processing."""

import asyncio
import hashlib
import os
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

import redis
from sentence_transformers import SentenceTransformer


class EmbeddingService:
    """Service for generating text embeddings with Redis caching and async batch support."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        redis_client: Optional[redis.Redis] = None,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        max_workers: int = 4,
    ):
        """
        Initialize the EmbeddingService.

        Args:
            model_name: Name of the sentence-transformers model to use.
                       Defaults to "BAAI/bge-large-en-v1.5" or EMBED_MODEL_NAME env var.
            redis_client: Optional Redis client instance. If not provided, creates one.
            redis_host: Redis host (used if redis_client not provided).
            redis_port: Redis port (used if redis_client not provided).
            redis_db: Redis database number (used if redis_client not provided).
            max_workers: Maximum number of worker threads for async batch processing.
        """
        self.model_name = model_name or os.getenv("EMBED_MODEL_NAME", "BAAI/bge-large-en-v1.5")
        self.model: Optional[SentenceTransformer] = None

        # Initialize Redis client
        if redis_client is not None:
            self.redis_client = redis_client
        else:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=False,  # We'll handle encoding/decoding ourselves
            )

        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def _get_model(self) -> SentenceTransformer:
        """Lazy load the model (thread-safe)."""
        if self.model is None:
            self.model = SentenceTransformer(self.model_name)
        return self.model

    def _get_cache_key(self, text: str) -> str:
        """
        Generate a cache key from model name and text.

        Args:
            text: Input text to embed.

        Returns:
            SHA256 hash of (model_name + text) as hex string.
        """
        cache_input = f"{self.model_name}{text}"
        return hashlib.sha256(cache_input.encode("utf-8")).hexdigest()

    def _serialize_embedding(self, embedding: List[float]) -> bytes:
        """Serialize embedding list to bytes for Redis storage."""
        import pickle
        return pickle.dumps(embedding)

    def _deserialize_embedding(self, data: bytes) -> List[float]:
        """Deserialize embedding bytes from Redis to list."""
        import pickle
        return pickle.loads(data)

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text to embed.

        Returns:
            List of floats representing the embedding vector.
        """
        cache_key = self._get_cache_key(text)

        # Try to get from cache
        cached = self.redis_client.get(cache_key)
        if cached is not None:
            return self._deserialize_embedding(cached)

        # Generate embedding
        model = self._get_model()
        embedding = model.encode(text, convert_to_numpy=False)

        # Store in cache
        self.redis_client.set(cache_key, self._serialize_embedding(embedding))

        return embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts (synchronous).

        Args:
            texts: List of input texts to embed.

        Returns:
            List of embedding vectors (each is a list of floats).
        """
        if not texts:
            return []

        # Check cache for all texts
        cache_keys = [self._get_cache_key(text) for text in texts]
        cached_results = self.redis_client.mget(cache_keys)

        # Process texts that weren't cached
        uncached_indices = []
        uncached_texts = []
        results = [None] * len(texts)

        for i, (cached, text) in enumerate(zip(cached_results, texts)):
            if cached is not None:
                results[i] = self._deserialize_embedding(cached)
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)

        # Generate embeddings for uncached texts
        if uncached_texts:
            model = self._get_model()
            embeddings = model.encode(uncached_texts, convert_to_numpy=False)

            # Store in cache and update results
            pipeline = self.redis_client.pipeline()
            for idx, text, embedding in zip(uncached_indices, uncached_texts, embeddings):
                cache_key = cache_keys[idx]
                results[idx] = embedding
                pipeline.set(cache_key, self._serialize_embedding(embedding))
            pipeline.execute()

        return results

    async def embed_batch_async(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts asynchronously using ThreadPool.

        Args:
            texts: List of input texts to embed.

        Returns:
            List of embedding vectors (each is a list of floats).
        """
        if not texts:
            return []

        # Check cache for all texts
        cache_keys = [self._get_cache_key(text) for text in texts]
        loop = asyncio.get_event_loop()
        cached_results = await loop.run_in_executor(
            self.executor, lambda: self.redis_client.mget(cache_keys)
        )

        # Process texts that weren't cached
        uncached_indices = []
        uncached_texts = []
        results = [None] * len(texts)

        for i, (cached, text) in enumerate(zip(cached_results, texts)):
            if cached is not None:
                results[i] = self._deserialize_embedding(cached)
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)

        # Generate embeddings for uncached texts asynchronously
        if uncached_texts:
            model = self._get_model()

            # Run model encoding in thread pool
            embeddings = await loop.run_in_executor(
                self.executor,
                lambda: model.encode(uncached_texts, convert_to_numpy=False),
            )

            # Store in cache and update results (also async)
            def store_in_cache():
                pipeline = self.redis_client.pipeline()
                for idx, embedding in zip(uncached_indices, embeddings):
                    cache_key = cache_keys[idx]
                    results[idx] = embedding
                    pipeline.set(cache_key, self._serialize_embedding(embedding))
                pipeline.execute()

            await loop.run_in_executor(self.executor, store_in_cache)

        return results

    async def embed_batch_async_parallel(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts using asyncio.gather for parallel processing.

        This method processes texts in parallel using asyncio.gather, which can be more
        efficient for large batches.

        Args:
            texts: List of input texts to embed.

        Returns:
            List of embedding vectors (each is a list of floats).
        """
        if not texts:
            return []

        # Create async tasks for each text
        tasks = [self._embed_text_async(text) for text in texts]
        results = await asyncio.gather(*tasks)
        return results

    async def _embed_text_async(self, text: str) -> List[float]:
        """
        Async wrapper for embed_text to use with asyncio.gather.

        Args:
            text: Input text to embed.

        Returns:
            List of floats representing the embedding vector.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, self.embed_text, text)

    def close(self):
        """Clean up resources."""
        if self.executor:
            self.executor.shutdown(wait=True)
