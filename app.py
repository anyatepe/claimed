"""
FastAPI application with metrics and tracing instrumentation.
"""
import asyncio
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware

from metrics import (
    request_count,
    latency_seconds,
    llm_tokens,
    retrieval_ms,
    cache_hits,
    cache_misses,
)
from tracing import setup_tracing, get_tracer

# Setup tracing
setup_tracing()
tracer = get_tracer(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    yield


app = FastAPI(title="RAG Application", lifespan=lifespan)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to track request metrics."""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        route = request.url.path
        status_code = 200

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except HTTPException as e:
            status_code = e.status_code
            raise
        finally:
            duration = time.time() - start_time
            request_count.labels(route=route, code=str(status_code)).inc()
            latency_seconds.labels(route=route).observe(duration)


app.add_middleware(MetricsMiddleware)


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/ingest")
async def ingest(request: Request):
    """Ingest documents."""
    with tracer.start_as_current_span("ingest.extract") as span:
        span.set_attribute("operation", "extract")
        # Simulate extraction
        await asyncio.sleep(0.1)
        data = await request.json()
        documents = data.get("documents", [])

    with tracer.start_as_current_span("chunk") as span:
        span.set_attribute("operation", "chunk")
        # Simulate chunking
        await asyncio.sleep(0.05)
        chunks = [doc[:100] for doc in documents]

    with tracer.start_as_current_span("embed") as span:
        span.set_attribute("operation", "embed")
        # Simulate embedding
        await asyncio.sleep(0.2)
        embeddings = [[0.1] * 768 for _ in chunks]

    with tracer.start_as_current_span("upsert") as span:
        span.set_attribute("operation", "upsert")
        # Simulate upsert to vector DB
        await asyncio.sleep(0.15)

    return JSONResponse({"status": "ingested", "chunks": len(chunks)})


@app.post("/retrieve")
async def retrieve(request: Request):
    """Retrieve relevant documents."""
    start_time = time.time()
    
    with tracer.start_as_current_span("retrieve") as span:
        span.set_attribute("operation", "retrieve")
        data = await request.json()
        query = data.get("query", "")
        
        # Simulate retrieval
        await asyncio.sleep(0.1)
        results = [{"id": i, "score": 0.9 - i * 0.1} for i in range(5)]
        
        span.set_attribute("results_count", len(results))

    with tracer.start_as_current_span("rerank") as span:
        span.set_attribute("operation", "rerank")
        # Simulate reranking
        await asyncio.sleep(0.05)
        reranked = sorted(results, key=lambda x: x["score"], reverse=True)
        span.set_attribute("reranked_count", len(reranked))

    retrieval_duration = (time.time() - start_time) * 1000  # Convert to ms
    retrieval_ms.observe(retrieval_duration)

    return JSONResponse({"results": reranked})


@app.post("/chat")
async def chat(request: Request):
    """Chat with LLM."""
    with tracer.start_as_current_span("llm.chat") as span:
        span.set_attribute("operation", "chat")
        data = await request.json()
        message = data.get("message", "")
        
        # Simulate LLM call
        await asyncio.sleep(0.3)
        
        # Simulate token usage
        prompt_tokens = len(message.split()) * 1.3
        completion_tokens = 50
        total_tokens = int(prompt_tokens + completion_tokens)
        
        llm_tokens.labels(type="prompt").inc(int(prompt_tokens))
        llm_tokens.labels(type="completion").inc(completion_tokens)
        llm_tokens.labels(type="total").inc(total_tokens)
        
        span.set_attribute("prompt_tokens", int(prompt_tokens))
        span.set_attribute("completion_tokens", completion_tokens)
        span.set_attribute("total_tokens", total_tokens)

        response_text = f"Response to: {message[:50]}..."
        
        return JSONResponse({
            "response": response_text,
            "tokens": {
                "prompt": int(prompt_tokens),
                "completion": completion_tokens,
                "total": total_tokens,
            }
        })


@app.get("/health")
async def health():
    """Health check endpoint."""
    return JSONResponse({"status": "healthy"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
