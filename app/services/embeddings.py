"""
Embedding service using sentence-transformers with Redis caching.
"""
import hashlib
import json
from typing import List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer
import aioredis


class EmbeddingService:
    """Service for generating text embeddings with Redis caching."""
    
    def __init__(
        self,
        model_name: str = "BAAI/bge-large-en-v1.5",
        redis_url: Optional[str] = None,
        redis_client: Optional[aioredis.Redis] = None,
    ):
        """
        Initialize the EmbeddingService.
        
        Args:
            model_name: Name of the sentence-transformers model to use.
            redis_url: Redis connection URL (e.g., "redis://localhost:6379").
                      If None, caching will be disabled.
            redis_client: Optional pre-configured Redis client. If provided,
                         redis_url will be ignored.
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self._redis_client = redis_client
        self._redis_url = redis_url
        self._redis_initialized = False
    
    async def _get_redis_client(self) -> Optional[aioredis.Redis]:
        """Get or create Redis client."""
        if self._redis_client is not None:
            return self._redis_client
        
        if self._redis_url is None:
            return None
        
        if not self._redis_initialized:
            self._redis_client = await aioredis.from_url(self._redis_url)
            self._redis_initialized = True
        
        return self._redis_client
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text and model name."""
        cache_string = f"{text}{self.model_name}"
        return hashlib.sha256(cache_string.encode()).hexdigest()
    
    async def _get_from_cache(self, cache_key: str) -> Optional[np.ndarray]:
        """Retrieve embedding from Redis cache."""
        redis_client = await self._get_redis_client()
        if redis_client is None:
            return None
        
        try:
            cached_data = await redis_client.get(cache_key)
            if cached_data is not None:
                if isinstance(cached_data, bytes):
                    cached_data = cached_data.decode('utf-8')
                embedding_list = json.loads(cached_data)
                return np.array(embedding_list, dtype=np.float32)
        except Exception:
            # If cache read fails, continue without cache
            pass
        
        return None
    
    async def _set_to_cache(self, cache_key: str, embedding: np.ndarray) -> None:
        """Store embedding in Redis cache."""
        redis_client = await self._get_redis_client()
        if redis_client is None:
            return
        
        try:
            embedding_list = embedding.tolist()
            await redis_client.set(cache_key, json.dumps(embedding_list))
        except Exception:
            # If cache write fails, continue without cache
            pass
    
    async def get_embedding(self, text: str) -> np.ndarray:
        """
        Get embedding for a single text.
        
        Args:
            text: Input text to embed.
            
        Returns:
            numpy array containing the embedding vector.
        """
        cache_key = self._get_cache_key(text)
        
        # Try to get from cache
        cached_embedding = await self._get_from_cache(cache_key)
        if cached_embedding is not None:
            return cached_embedding
        
        # Generate embedding
        embedding = self.model.encode(text, convert_to_numpy=True)
        
        # Store in cache
        await self._set_to_cache(cache_key, embedding)
        
        return embedding
    
    async def batch_embed(self, texts: List[str]) -> np.ndarray:
        """
        Get embeddings for multiple texts efficiently.
        
        Args:
            texts: List of input texts to embed.
            
        Returns:
            numpy array of shape (len(texts), embedding_dim) containing embeddings.
        """
        if not texts:
            return np.array([])
        
        cache_keys = [self._get_cache_key(text) for text in texts]
        embeddings = [None] * len(texts)
        texts_to_embed = []
        indices_to_embed = []
        
        # Check cache for all texts
        redis_client = await self._get_redis_client()
        if redis_client is not None:
            try:
                # Batch get from Redis
                cached_data_list = await redis_client.mget(cache_keys)
                for idx, cached_data in enumerate(cached_data_list):
                    if cached_data is not None:
                        if isinstance(cached_data, bytes):
                            cached_data = cached_data.decode('utf-8')
                        embedding_list = json.loads(cached_data)
                        embeddings[idx] = np.array(embedding_list, dtype=np.float32)
                    else:
                        texts_to_embed.append(texts[idx])
                        indices_to_embed.append(idx)
            except Exception:
                # If batch cache read fails, embed all texts
                texts_to_embed = texts
                indices_to_embed = list(range(len(texts)))
                embeddings = [None] * len(texts)
        else:
            # No Redis client, embed all texts
            texts_to_embed = texts
            indices_to_embed = list(range(len(texts)))
        
        # Generate embeddings for texts not in cache
        if texts_to_embed:
            new_embeddings = self.model.encode(
                texts_to_embed,
                convert_to_numpy=True,
                batch_size=32,
            )
            
            # Store new embeddings in cache and update results
            if redis_client is not None:
                try:
                    cache_pairs = {}
                    for i, idx in enumerate(indices_to_embed):
                        embeddings[idx] = new_embeddings[i]
                        cache_pairs[cache_keys[idx]] = json.dumps(new_embeddings[i].tolist())
                    
                    # Batch set to Redis
                    if cache_pairs:
                        await redis_client.mset(cache_pairs)
                except Exception:
                    # If batch cache write fails, continue without cache
                    for i, idx in enumerate(indices_to_embed):
                        embeddings[idx] = new_embeddings[i]
            else:
                for i, idx in enumerate(indices_to_embed):
                    embeddings[idx] = new_embeddings[i]
        
        return np.array(embeddings)
    
    async def close(self) -> None:
        """Close Redis connection if it was created by this service."""
        if self._redis_client is not None and self._redis_initialized:
            await self._redis_client.close()
            self._redis_client = None
            self._redis_initialized = False
