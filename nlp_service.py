"""
NLP service functions with Redis caching and idempotency support.

This module provides summarize and classify functions that are wrapped
with caching decorators to improve performance and ensure idempotency.
"""

import logging
from typing import Dict, Any, Optional
from redis_cache import cached, idempotent

logger = logging.getLogger(__name__)


@cached(ttl=3600, key_prefix="summarize")
@idempotent(ttl=3600, key_prefix="summarize")
def summarize(text: str, max_length: int = 100, min_length: int = 30) -> Dict[str, Any]:
    """
    Summarize a text using a simple extractive summarization approach.
    
    This function is cached and idempotent - duplicate requests with the same
    parameters will return cached results.
    
    Args:
        text: The text to summarize
        max_length: Maximum length of the summary
        min_length: Minimum length of the summary
    
    Returns:
        dict: A dictionary containing:
            - summary: The summarized text
            - original_length: Length of original text
            - summary_length: Length of summary
            - compression_ratio: Ratio of summary to original length
    """
    logger.info(f"Summarizing text (length: {len(text)}, max_length: {max_length}, min_length: {min_length})")
    
    if not text or not text.strip():
        return {
            "summary": "",
            "original_length": 0,
            "summary_length": 0,
            "compression_ratio": 0.0
        }
    
    # Simple extractive summarization: take first sentences up to max_length
    sentences = text.split('.')
    summary_sentences = []
    current_length = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        sentence_length = len(sentence) + 1  # +1 for period
        if current_length + sentence_length <= max_length:
            summary_sentences.append(sentence)
            current_length += sentence_length
        else:
            # Try to fit partial sentence if we haven't reached min_length
            if current_length < min_length:
                remaining = max_length - current_length
                if remaining > 20:  # Only add if meaningful
                    summary_sentences.append(sentence[:remaining] + "...")
            break
    
    summary = '. '.join(summary_sentences)
    if summary and not summary.endswith('.'):
        summary += '.'
    
    # Ensure minimum length
    if len(summary) < min_length and len(text) >= min_length:
        summary = text[:min_length] + "..."
    
    result = {
        "summary": summary,
        "original_length": len(text),
        "summary_length": len(summary),
        "compression_ratio": len(summary) / len(text) if len(text) > 0 else 0.0
    }
    
    logger.info(f"Summary generated: {len(summary)} characters (compression: {result['compression_ratio']:.2%})")
    return result


@cached(ttl=3600, key_prefix="classify")
@idempotent(ttl=3600, key_prefix="classify")
def classify(text: str, categories: Optional[list] = None) -> Dict[str, Any]:
    """
    Classify text into predefined categories using a simple keyword-based approach.
    
    This function is cached and idempotent - duplicate requests with the same
    parameters will return cached results.
    
    Args:
        text: The text to classify
        categories: Optional list of categories. If None, uses default categories:
            ['technology', 'science', 'business', 'health', 'entertainment', 'sports']
    
    Returns:
        dict: A dictionary containing:
            - category: The predicted category
            - confidence: Confidence score (0.0 to 1.0)
            - scores: Dictionary of scores for each category
    """
    if categories is None:
        categories = ['technology', 'science', 'business', 'health', 'entertainment', 'sports']
    
    logger.info(f"Classifying text (length: {len(text)}, categories: {categories})")
    
    if not text or not text.strip():
        return {
            "category": categories[0] if categories else "unknown",
            "confidence": 0.0,
            "scores": {cat: 0.0 for cat in categories}
        }
    
    text_lower = text.lower()
    
    # Simple keyword-based classification
    category_keywords = {
        'technology': ['computer', 'software', 'hardware', 'digital', 'internet', 'ai', 'machine learning', 'data', 'code', 'programming', 'tech', 'algorithm'],
        'science': ['research', 'study', 'experiment', 'discovery', 'scientific', 'theory', 'hypothesis', 'laboratory', 'molecule', 'atom', 'physics', 'chemistry'],
        'business': ['company', 'market', 'revenue', 'profit', 'investment', 'financial', 'economy', 'trade', 'commerce', 'corporate', 'business'],
        'health': ['health', 'medical', 'doctor', 'patient', 'treatment', 'disease', 'medicine', 'hospital', 'clinic', 'wellness', 'therapy'],
        'entertainment': ['movie', 'film', 'music', 'celebrity', 'actor', 'entertainment', 'show', 'concert', 'theater', 'performance', 'art'],
        'sports': ['sport', 'game', 'player', 'team', 'match', 'championship', 'athlete', 'football', 'basketball', 'soccer', 'olympics']
    }
    
    scores = {}
    for category in categories:
        keywords = category_keywords.get(category, [])
        score = sum(1 for keyword in keywords if keyword in text_lower)
        scores[category] = score
    
    # Normalize scores to 0-1 range
    max_score = max(scores.values()) if scores.values() else 1
    if max_score > 0:
        scores = {cat: score / max_score for cat, score in scores.items()}
    else:
        scores = {cat: 1.0 / len(categories) for cat in categories}
    
    # Get category with highest score
    predicted_category = max(scores.items(), key=lambda x: x[1])[0]
    confidence = scores[predicted_category]
    
    result = {
        "category": predicted_category,
        "confidence": confidence,
        "scores": scores
    }
    
    logger.info(f"Text classified as '{predicted_category}' with confidence {confidence:.2%}")
    return result
