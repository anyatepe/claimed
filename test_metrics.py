"""
Smoke tests for metrics presence.
"""
import pytest
import requests
from prometheus_client.parser import text_string_to_metric_families


def test_metrics_endpoint_exists():
    """Test that /metrics endpoint exists and returns 200."""
    response = requests.get("http://localhost:8000/metrics")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/plain; version=0.0.4; charset=utf-8"


def test_metrics_contains_request_count():
    """Test that request_count metric is present."""
    response = requests.get("http://localhost:8000/metrics")
    metrics = list(text_string_to_metric_families(response.text))
    
    metric_names = [m.name for m in metrics]
    assert "request_count" in metric_names
    
    # Find the request_count metric
    request_count_metric = next(m for m in metrics if m.name == "request_count")
    assert request_count_metric.type == "counter"
    
    # Check for route and code labels
    samples = list(request_count_metric.samples)
    if samples:
        sample = samples[0]
        assert "route" in sample.labels or "code" in sample.labels


def test_metrics_contains_latency_seconds():
    """Test that latency_seconds metric is present."""
    response = requests.get("http://localhost:8000/metrics")
    metrics = list(text_string_to_metric_families(response.text))
    
    metric_names = [m.name for m in metrics]
    assert "latency_seconds" in metric_names
    
    # Find the latency_seconds metric
    latency_metric = next(m for m in metrics if m.name == "latency_seconds")
    assert latency_metric.type == "histogram"


def test_metrics_contains_llm_tokens():
    """Test that llm_tokens metric is present."""
    response = requests.get("http://localhost:8000/metrics")
    metrics = list(text_string_to_metric_families(response.text))
    
    metric_names = [m.name for m in metrics]
    assert "llm_tokens" in metric_names
    
    # Find the llm_tokens metric
    llm_tokens_metric = next(m for m in metrics if m.name == "llm_tokens")
    assert llm_tokens_metric.type == "counter"


def test_metrics_contains_retrieval_ms():
    """Test that retrieval_ms metric is present."""
    response = requests.get("http://localhost:8000/metrics")
    metrics = list(text_string_to_metric_families(response.text))
    
    metric_names = [m.name for m in metrics]
    assert "retrieval_ms" in metric_names
    
    # Find the retrieval_ms metric
    retrieval_metric = next(m for m in metrics if m.name == "retrieval_ms")
    assert retrieval_metric.type == "histogram"


def test_metrics_contains_cache_metrics():
    """Test that cache metrics are present."""
    response = requests.get("http://localhost:8000/metrics")
    metrics = list(text_string_to_metric_families(response.text))
    
    metric_names = [m.name for m in metrics]
    assert "cache_hits" in metric_names
    assert "cache_misses" in metric_names


def test_metrics_after_request():
    """Test that metrics are updated after making a request."""
    # Make a request to generate metrics
    requests.get("http://localhost:8000/health")
    
    response = requests.get("http://localhost:8000/metrics")
    metrics = list(text_string_to_metric_families(response.text))
    
    # Find request_count metric
    request_count_metric = next(m for m in metrics if m.name == "request_count")
    samples = list(request_count_metric.samples)
    
    # Should have at least one sample
    assert len(samples) > 0
    
    # Check that we have a sample for /health endpoint
    health_samples = [s for s in samples if s.labels.get("route") == "/health"]
    assert len(health_samples) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
