# Metrics and Tracing Setup

This application includes comprehensive metrics and tracing instrumentation.

## Metrics

The `/metrics` endpoint exposes Prometheus-compatible metrics:

- **request_count{route, code}**: Counter tracking HTTP requests by route and status code
- **latency_seconds{route}**: Histogram tracking request latency by route
- **llm_tokens{type}**: Counter tracking LLM token usage (prompt, completion, total)
- **retrieval_ms**: Histogram tracking document retrieval latency in milliseconds
- **cache_hits**: Counter for cache hits
- **cache_misses**: Counter for cache misses

## Tracing

OpenTelemetry tracing spans are created for:

- `ingest.extract`: Document extraction
- `chunk`: Document chunking
- `embed`: Embedding generation
- `upsert`: Vector database upsert
- `retrieve`: Document retrieval
- `rerank`: Result reranking
- `llm.chat`: LLM chat completion

Tracing is configured via environment variables:
- `OTEL_EXPORTER_OTLP_ENDPOINT`: OTLP endpoint (default: http://localhost:4317)

## Running the Application

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python app.py
# or
uvicorn app:app --host 0.0.0.0 --port 8000
```

3. Access metrics:
```bash
curl http://localhost:8000/metrics
```

## Grafana Dashboard

Import `grafana_dashboard.json` into Grafana to visualize:
- Request latency (p95)
- Request rate
- Error rate
- LLM tokens usage
- Retrieval latency (p50, p95)
- Cache hit rate

## Testing

Run smoke tests to verify metrics are present:
```bash
# Start the application first
python app.py

# In another terminal, run tests
pytest test_metrics.py -v
```
