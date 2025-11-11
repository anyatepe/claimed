"""
Prometheus metrics definitions.
"""
from prometheus_client import Counter, Histogram

# Request counter with route and status code labels
request_count = Counter(
    "request_count",
    "Total number of HTTP requests",
    ["route", "code"],
)

# Request latency histogram
latency_seconds = Histogram(
    "latency_seconds",
    "HTTP request latency in seconds",
    ["route"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# LLM token usage counter
llm_tokens = Counter(
    "llm_tokens",
    "Total number of LLM tokens used",
    ["type"],  # type: prompt, completion, total
)

# Retrieval latency histogram in milliseconds
retrieval_ms = Histogram(
    "retrieval_ms",
    "Document retrieval latency in milliseconds",
    buckets=[10, 25, 50, 100, 250, 500, 1000, 2500, 5000],
)

# Cache metrics for cache hit rate calculation
cache_hits = Counter(
    "cache_hits",
    "Total number of cache hits",
)

cache_misses = Counter(
    "cache_misses",
    "Total number of cache misses",
)
