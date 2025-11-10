"""Main application entry point with OpenTelemetry tracing and Prometheus metrics."""
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.config import settings
from app.utils.logging import (
    get_logger,
    set_request_id,
    set_trace_id,
    configure_logging,
)

# Configure logging
configure_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))

logger = get_logger(__name__)

# Prometheus metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

# OpenTelemetry setup
try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.trace import Status, StatusCode
    
    # Initialize OpenTelemetry
    resource = Resource.create({"service.name": "app", "service.version": "1.0.0"})
    trace.set_tracer_provider(TracerProvider(resource=resource))
    
    # Configure OTLP exporter (can be configured via OTEL_EXPORTER_OTLP_ENDPOINT env var)
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        span_processor = BatchSpanProcessor(otlp_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)
    
    tracer = trace.get_tracer(__name__)
    OTEL_AVAILABLE = True
    OTEL_STATUS = Status
    OTEL_STATUS_CODE = StatusCode
except ImportError:
    logger.warning("OpenTelemetry packages not installed. Tracing will be disabled.")
    OTEL_AVAILABLE = False
    tracer = None
    OTEL_STATUS = None
    OTEL_STATUS_CODE = None


class TracingMiddleware(BaseHTTPMiddleware):
    """Middleware to add OpenTelemetry tracing and request/trace IDs."""
    
    async def dispatch(self, request: Request, call_next):
        # Generate request and trace IDs
        request_id = set_request_id()
        trace_id = set_trace_id()
        
        # Add IDs to request state
        request.state.request_id = request_id
        request.state.trace_id = trace_id
        
        # Create OpenTelemetry span if available
        if OTEL_AVAILABLE and tracer:
            with tracer.start_as_current_span(
                f"{request.method} {request.url.path}",
                attributes={
                    "http.method": request.method,
                    "http.url": str(request.url),
                    "http.route": request.url.path,
                    "request_id": request_id,
                    "trace_id": trace_id,
                },
            ) as span:
                try:
                    response = await call_next(request)
                    span.set_attribute("http.status_code", response.status_code)
                    span.set_status(OTEL_STATUS(OTEL_STATUS_CODE.OK))
                    return response
                except Exception as e:
                    span.set_status(OTEL_STATUS(OTEL_STATUS_CODE.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        else:
            response = await call_next(request)
            return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics."""
    
    async def dispatch(self, request: Request, call_next):
        # Skip metrics endpoint
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Record request start time
        import time
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Record metrics
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
        ).inc()
        
        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(duration)
        
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger.info("Application starting up", env=settings.ENV)
    
    # Initialize OpenTelemetry instrumentation if available
    if OTEL_AVAILABLE:
        try:
            FastAPIInstrumentor.instrument_app(app)
            RequestsInstrumentor().instrument()
            logger.info("OpenTelemetry instrumentation enabled")
        except Exception as e:
            logger.warning("Failed to initialize OpenTelemetry instrumentation", error=str(e))
    
    yield
    
    logger.info("Application shutting down")


# Create FastAPI app
app = FastAPI(
    title="App",
    description="Application with OpenTelemetry tracing and Prometheus metrics",
    version="1.0.0",
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(TracingMiddleware)
app.add_middleware(MetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    logger.info("Root endpoint accessed")
    return {"message": "Hello World", "env": settings.ENV}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENV == "development",
    )
