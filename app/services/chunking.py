"""
Text chunking service for splitting text into overlapping token-based chunks.
"""

import tiktoken
from typing import List


class TextChunker:
    """
    Splits text into chunks of approximately 800 tokens with 100-token overlap.
    
    Uses tiktoken library for tokenization with cl100k_base encoding
    (compatible with GPT-3.5/GPT-4 models).
    """
    
    def __init__(
        self,
        chunk_size: int = 800,
        overlap_size: int = 100,
        encoding_name: str = "cl100k_base"
    ):
        """
        Initialize the TextChunker.
        
        Args:
            chunk_size: Target number of tokens per chunk (default: 800)
            overlap_size: Number of tokens to overlap between chunks (default: 100)
            encoding_name: Name of the tiktoken encoding to use (default: "cl100k_base")
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if overlap_size < 0:
            raise ValueError("overlap_size must be non-negative")
        if overlap_size >= chunk_size:
            raise ValueError("overlap_size must be less than chunk_size")
        
        self.chunk_size = chunk_size
        self.overlap_size = overlap_size
        self.encoding = tiktoken.get_encoding(encoding_name)
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks based on token count.
        
        Args:
            text: The input text to chunk
            
        Returns:
            List of text chunks, each containing approximately chunk_size tokens
            with overlap_size tokens overlapping between consecutive chunks.
        """
        if not text:
            return []
        
        # Tokenize the entire text
        tokens = self.encoding.encode(text)
        
        if len(tokens) <= self.chunk_size:
            # Text fits in a single chunk
            return [text]
        
        chunks = []
        start_idx = 0
        
        while start_idx < len(tokens):
            # Calculate end index for this chunk
            end_idx = start_idx + self.chunk_size
            
            # Extract tokens for this chunk
            chunk_tokens = tokens[start_idx:end_idx]
            
            # Decode tokens back to text
            chunk_text = self.encoding.decode(chunk_tokens)
            chunks.append(chunk_text)
            
            # Move start index forward by (chunk_size - overlap_size)
            # to create the overlap
            start_idx += self.chunk_size - self.overlap_size
            
            # If remaining tokens are less than chunk_size, include them
            # in the last chunk (with overlap)
            if end_idx >= len(tokens):
                break
        
        return chunks
