"""
Example usage of Redis caching and idempotency for summarize and classify functions.

This script demonstrates how the caching and idempotency features work.
"""

import logging
from redis_cache import cache_result, get_cached_result, ensure_idempotency
from nlp_service import summarize, classify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_basic_caching():
    """Example of basic caching functions."""
    print("\n=== Basic Caching Example ===")
    
    # Cache a result
    key = "example:test_key"
    value = {"result": "test_data", "number": 42}
    ttl = 60
    
    print(f"Caching value: {value}")
    success = cache_result(key, value, ttl)
    print(f"Cache result: {success}")
    
    # Retrieve cached result
    cached_value = get_cached_result(key)
    print(f"Retrieved cached value: {cached_value}")
    
    # Verify they match
    assert cached_value == value
    print("✓ Cached and retrieved values match!")


def example_idempotency():
    """Example of idempotency checking."""
    print("\n=== Idempotency Example ===")
    
    idempotency_key = "example:idempotency_key_123"
    
    # First request - should be new
    is_new = ensure_idempotency(idempotency_key, ttl=60)
    print(f"First request (idempotency_key: {idempotency_key}): {'NEW' if is_new else 'DUPLICATE'}")
    
    # Second request with same key - should be duplicate
    is_new2 = ensure_idempotency(idempotency_key, ttl=60)
    print(f"Second request (same key): {'NEW' if is_new2 else 'DUPLICATE'}")
    
    assert is_new is True
    assert is_new2 is False
    print("✓ Idempotency check working correctly!")


def example_summarize_caching():
    """Example of summarize function with caching."""
    print("\n=== Summarize with Caching Example ===")
    
    text = """
    Machine learning is a subset of artificial intelligence that focuses on the development
    of algorithms and statistical models that enable computer systems to improve their
    performance on a specific task through experience. Unlike traditional programming,
    where explicit instructions are provided, machine learning systems learn patterns
    from data. This approach has revolutionized many fields including computer vision,
    natural language processing, and predictive analytics. Deep learning, a subset of
    machine learning, uses neural networks with multiple layers to model and understand
    complex patterns in data.
    """
    
    print(f"Original text length: {len(text)} characters")
    
    # First call - will compute and cache
    print("\nFirst call (cache miss - will compute):")
    result1 = summarize(text, max_length=100, min_length=30)
    print(f"Summary: {result1['summary']}")
    print(f"Summary length: {result1['summary_length']} characters")
    print(f"Compression ratio: {result1['compression_ratio']:.2%}")
    
    # Second call with same parameters - should use cache
    print("\nSecond call (cache hit - will reuse cached result):")
    result2 = summarize(text, max_length=100, min_length=30)
    print(f"Summary: {result2['summary']}")
    
    # Results should be identical
    assert result1 == result2
    print("\n✓ Duplicate requests return identical cached results!")


def example_classify_caching():
    """Example of classify function with caching."""
    print("\n=== Classify with Caching Example ===")
    
    text1 = "The new software update includes advanced machine learning algorithms for data analysis."
    text2 = "Scientists discovered a new molecule that could revolutionize cancer treatment."
    
    print(f"Text 1: {text1}")
    print(f"Text 2: {text2}\n")
    
    # Classify first text
    print("Classifying text 1 (first call):")
    result1a = classify(text1)
    print(f"Category: {result1a['category']}")
    print(f"Confidence: {result1a['confidence']:.2%}")
    print(f"Scores: {result1a['scores']}")
    
    # Classify same text again - should use cache
    print("\nClassifying text 1 (second call - should use cache):")
    result1b = classify(text1)
    print(f"Category: {result1b['category']}")
    assert result1a == result1b
    print("✓ Duplicate classification requests return cached results!")
    
    # Classify different text
    print("\nClassifying text 2:")
    result2 = classify(text2)
    print(f"Category: {result2['category']}")
    print(f"Confidence: {result2['confidence']:.2%}")
    print(f"Scores: {result2['scores']}")


def example_custom_categories():
    """Example of classify with custom categories."""
    print("\n=== Classify with Custom Categories ===")
    
    text = "The company announced record profits and increased market share."
    custom_categories = ["business", "technology", "finance"]
    
    print(f"Text: {text}")
    print(f"Custom categories: {custom_categories}\n")
    
    result = classify(text, categories=custom_categories)
    print(f"Category: {result['category']}")
    print(f"Confidence: {result['confidence']:.2%}")
    print(f"Scores: {result['scores']}")
    
    assert result["category"] in custom_categories
    print("\n✓ Custom categories working correctly!")


if __name__ == "__main__":
    print("Redis Caching and Idempotency Examples")
    print("=" * 50)
    
    try:
        example_basic_caching()
        example_idempotency()
        example_summarize_caching()
        example_classify_caching()
        example_custom_categories()
        
        print("\n" + "=" * 50)
        print("All examples completed successfully!")
        print("\nNote: Make sure Redis is running and accessible.")
        print("You can start Redis with: docker run -d -p 6379:6379 redis")
        
    except Exception as e:
        logger.error(f"Error running examples: {e}")
        print(f"\nError: {e}")
        print("Make sure Redis is running and accessible.")
        raise
