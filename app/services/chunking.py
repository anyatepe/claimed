"""Text chunking service for splitting documents into token-limited chunks with overlap."""

import re
from dataclasses import dataclass
from typing import List, Optional

try:
    import tiktoken
except ImportError:
    tiktoken = None

try:
    from transformers import AutoTokenizer
except ImportError:
    AutoTokenizer = None


# Default constants
MAX_CHUNK_TOKENS = 700
CHUNK_OVERLAP = 100


@dataclass
class Chunk:
    """Represents a text chunk with metadata."""
    chunk_id: str
    doc_id: str
    page: int
    text: str
    token_count: int


class TextChunker:
    """Chunks text into token-limited segments with overlap, preserving page information."""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo", use_hf_tokenizer: bool = False):
        """
        Initialize the TextChunker with a tokenizer.
        
        Args:
            model_name: Model name for tiktoken (default: "gpt-3.5-turbo") or 
                       HuggingFace model name if use_hf_tokenizer=True
            use_hf_tokenizer: If True, use HuggingFace tokenizer instead of tiktoken
        """
        self.use_hf_tokenizer = use_hf_tokenizer
        self.model_name = model_name
        
        if use_hf_tokenizer:
            if AutoTokenizer is None:
                raise ImportError(
                    "transformers library is required for HuggingFace tokenizer. "
                    "Install with: pip install transformers"
                )
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        else:
            if tiktoken is None:
                raise ImportError(
                    "tiktoken library is required. Install with: pip install tiktoken"
                )
            self.encoding = tiktoken.encoding_for_model(model_name)
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text using the configured tokenizer."""
        if self.use_hf_tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            return len(self.encoding.encode(text))
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs (double newlines or single newline followed by whitespace)."""
        # Split on double newlines first
        paragraphs = re.split(r'\n\s*\n', text)
        
        # If no double newlines, try splitting on single newlines that start new lines
        if len(paragraphs) == 1:
            paragraphs = re.split(r'\n(?=\S)', text)
        
        # Filter out empty paragraphs
        return [p.strip() for p in paragraphs if p.strip()]
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences using regex."""
        # Pattern to match sentence endings followed by whitespace or end of string
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z])|(?<=[.!?])\s*$'
        sentences = re.split(sentence_pattern, text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _extract_overlap_text(self, text: str, overlap_tokens: int) -> str:
        """
        Extract the last N tokens from text for overlap.
        
        Args:
            text: Source text
            overlap_tokens: Target number of tokens for overlap
        
        Returns:
            Text containing approximately overlap_tokens from the end
        """
        if overlap_tokens <= 0:
            return ""
        
        # Try to extract by sentences first (preserves sentence boundaries)
        sentences = self._split_into_sentences(text)
        overlap_sentences = []
        overlap_count = 0
        
        for sent in reversed(sentences):
            sent_tokens = self._count_tokens(sent)
            if overlap_count + sent_tokens <= overlap_tokens:
                overlap_sentences.insert(0, sent)
                overlap_count += sent_tokens
            else:
                break
        
        if overlap_sentences:
            return " ".join(overlap_sentences)
        
        # Fallback: extract by words if sentences don't work
        words = text.split()
        if not words:
            return ""
        
        # Binary search for the right number of words
        overlap_words = []
        overlap_count = 0
        
        for word in reversed(words):
            word_tokens = self._count_tokens(word)
            if overlap_count + word_tokens <= overlap_tokens:
                overlap_words.insert(0, word)
                overlap_count += word_tokens
            else:
                break
        
        return " ".join(overlap_words) if overlap_words else ""
    
    def _create_chunk(
        self, 
        text: str, 
        doc_id: str, 
        page: int, 
        chunk_index: int
    ) -> Chunk:
        """Create a Chunk object with generated chunk_id."""
        chunk_id = f"{doc_id}_page{page}_chunk{chunk_index}"
        token_count = self._count_tokens(text)
        return Chunk(
            chunk_id=chunk_id,
            doc_id=doc_id,
            page=page,
            text=text,
            token_count=token_count
        )
    
    def chunk(
        self,
        text: str,
        page: int,
        doc_id: str,
        target_tokens: int = MAX_CHUNK_TOKENS,
        overlap: int = CHUNK_OVERLAP
    ) -> List[Chunk]:
        """
        Chunk text into segments with token limits and overlap.
        
        Args:
            text: The text to chunk
            page: Page number for this text
            doc_id: Document identifier
            target_tokens: Maximum tokens per chunk (default: MAX_CHUNK_TOKENS)
            overlap: Number of tokens to overlap between chunks (default: CHUNK_OVERLAP)
        
        Returns:
            List of Chunk objects
        """
        if not text.strip():
            return []
        
        chunks = []
        chunk_index = 0
        
        # First, try to split by paragraphs
        paragraphs = self._split_into_paragraphs(text)
        
        current_chunk = []
        current_tokens = 0
        use_paragraph_separator = True  # Track if we're at paragraph level
        
        for paragraph in paragraphs:
            para_tokens = self._count_tokens(paragraph)
            
            # If paragraph alone exceeds target, split by sentences
            if para_tokens > target_tokens:
                # Flush current chunk if it has content
                if current_chunk:
                    separator = "\n\n" if use_paragraph_separator else " "
                    chunk_text = separator.join(current_chunk)
                    chunks.append(self._create_chunk(chunk_text, doc_id, page, chunk_index))
                    chunk_index += 1
                    current_chunk = []
                    current_tokens = 0
                    use_paragraph_separator = False  # Now we're at sentence level
                
                # Split paragraph into sentences
                sentences = self._split_into_sentences(paragraph)
                for sentence in sentences:
                    sent_tokens = self._count_tokens(sentence)
                    
                    # If sentence alone exceeds target, split it further
                    if sent_tokens > target_tokens:
                        # Flush current chunk if it has content
                        if current_chunk:
                            chunk_text = " ".join(current_chunk)
                            chunks.append(self._create_chunk(chunk_text, doc_id, page, chunk_index))
                            chunk_index += 1
                            current_chunk = []
                            current_tokens = 0
                        
                        # Split long sentence by words (fallback)
                        words = sentence.split()
                        for word in words:
                            word_tokens = self._count_tokens(word)
                            if current_tokens + word_tokens > target_tokens:
                                if current_chunk:
                                    chunk_text = " ".join(current_chunk)
                                    chunks.append(self._create_chunk(chunk_text, doc_id, page, chunk_index))
                                    chunk_index += 1
                                    
                                    # Apply overlap: take last N tokens from previous chunk
                                    if overlap > 0 and chunks:
                                        prev_chunk = chunks[-1]
                                        overlap_text = self._extract_overlap_text(prev_chunk.text, overlap)
                                        if overlap_text:
                                            current_chunk = [overlap_text]
                                            current_tokens = self._count_tokens(overlap_text)
                                        else:
                                            current_chunk = []
                                            current_tokens = 0
                                    else:
                                        current_chunk = []
                                        current_tokens = 0
                            
                            current_chunk.append(word)
                            current_tokens += word_tokens
                    else:
                        # Sentence fits, check if adding it would exceed limit
                        if current_tokens + sent_tokens > target_tokens:
                            if current_chunk:
                                chunk_text = " ".join(current_chunk)
                                chunks.append(self._create_chunk(chunk_text, doc_id, page, chunk_index))
                                chunk_index += 1
                                
                                # Apply overlap
                                if overlap > 0 and chunks:
                                    prev_chunk = chunks[-1]
                                    overlap_text = self._extract_overlap_text(prev_chunk.text, overlap)
                                    if overlap_text:
                                        current_chunk = [overlap_text]
                                        current_tokens = self._count_tokens(overlap_text)
                                    else:
                                        current_chunk = []
                                        current_tokens = 0
                                else:
                                    current_chunk = []
                                    current_tokens = 0
                        
                        current_chunk.append(sentence)
                        current_tokens += sent_tokens
            else:
                # Paragraph fits, check if adding it would exceed limit
                if current_tokens + para_tokens > target_tokens:
                    if current_chunk:
                        separator = "\n\n" if use_paragraph_separator else " "
                        chunk_text = separator.join(current_chunk)
                        chunks.append(self._create_chunk(chunk_text, doc_id, page, chunk_index))
                        chunk_index += 1
                        
                        # Apply overlap
                        if overlap > 0 and chunks:
                            prev_chunk = chunks[-1]
                            overlap_text = self._extract_overlap_text(prev_chunk.text, overlap)
                            if overlap_text:
                                current_chunk = [overlap_text]
                                current_tokens = self._count_tokens(overlap_text)
                                use_paragraph_separator = False  # Overlap might be sentences
                            else:
                                current_chunk = []
                                current_tokens = 0
                        else:
                            current_chunk = []
                            current_tokens = 0
                
                current_chunk.append(paragraph)
                current_tokens += para_tokens
        
        # Add remaining chunk
        if current_chunk:
            separator = "\n\n" if use_paragraph_separator else " "
            chunk_text = separator.join(current_chunk)
            chunks.append(self._create_chunk(chunk_text, doc_id, page, chunk_index))
        
        return chunks
