"""
FastAPI application with OpenTelemetry tracing and Prometheus metrics.
"""
import os
import time
from contextlib import asynccontextmanager
from typing import Optional

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, Histogram, generate_latest, REGISTRY
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint']
)

ERROR_COUNT = Counter(
    'http_errors_total',
    'Total number of HTTP errors',
    ['method', 'endpoint', 'status']
)

# Database and Redis configuration
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+asyncpg://postgres:postgres@localhost:5432/testdb'
)
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Initialize database engine
async_engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)

# Initialize Redis connection pool
redis_pool: Optional[aioredis.ConnectionPool] = None
redis_client: Optional[aioredis.Redis] = None


def setup_opentelemetry(app: FastAPI):
    """Configure OpenTelemetry tracing."""
    resource = Resource.create({
        "service.name": "fastapi-app",
        "service.version": "1.0.0",
    })
    
    trace.set_tracer_provider(TracerProvider(resource=resource))
    
    # OTLP exporter (can be configured via env vars)
    otlp_exporter = OTLPSpanExporter(
        endpoint=os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://localhost:4317'),
        insecure=os.getenv('OTEL_EXPORTER_OTLP_INSECURE', 'true').lower() == 'true',
    )
    
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
    
    # Instrument FastAPI (must be called after app creation)
    FastAPIInstrumentor.instrument_app(app)
    
    # Instrument Redis
    RedisInstrumentor().instrument()
    
    # Instrument SQLAlchemy (for async, we'll use manual tracing in routes)
    # SQLAlchemy async instrumentation is limited, so we use manual spans


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan."""
    global redis_pool, redis_client
    
    # Initialize Redis connection (optional, fails gracefully)
    try:
        redis_pool = aioredis.ConnectionPool.from_url(REDIS_URL)
        redis_client = aioredis.Redis(connection_pool=redis_pool)
    except Exception:
        # Redis not available, continue without it
        redis_pool = None
        redis_client = None
    
    yield
    
    # Cleanup
    if redis_client:
        await redis_client.close()
    if redis_pool:
        await redis_pool.disconnect()
    await async_engine.dispose()


app = FastAPI(title="FastAPI with OpenTelemetry and Prometheus", lifespan=lifespan)

# Setup OpenTelemetry (must be after app creation)
setup_opentelemetry(app)

# Setup Prometheus instrumentation
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)


@app.middleware("http")
async def metrics_middleware(request, call_next):
    """Middleware to collect Prometheus metrics."""
    start_time = time.time()
    method = request.method
    endpoint = request.url.path
    
    try:
        response = await call_next(request)
        status_code = response.status_code
        
        # Record metrics
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status_code).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(
            time.time() - start_time
        )
        
        if status_code >= 400:
            ERROR_COUNT.labels(method=method, endpoint=endpoint, status=status_code).inc()
        
        return response
    except Exception as e:
        status_code = 500
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status_code).inc()
        ERROR_COUNT.labels(method=method, endpoint=endpoint, status=status_code).inc()
        raise


@app.get("/")
async def root():
    """Root endpoint."""
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("root_handler"):
        return {"message": "Hello World"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("health_check"):
        return {"status": "healthy"}


@app.get("/users/{user_id}")
async def get_user(user_id: int):
    """Get user by ID with database query."""
    tracer = trace.get_tracer(__name__)
    
    with tracer.start_as_current_span("get_user") as span:
        span.set_attribute("user.id", user_id)
        
        # Query PostgreSQL
        async with AsyncSessionLocal() as session:
            with tracer.start_as_current_span("postgres_query"):
                try:
                    result = await session.execute(
                        text("SELECT id, name FROM users WHERE id = :id"),
                        {"id": user_id}
                    )
                    user = result.fetchone()
                    if not user:
                        raise HTTPException(status_code=404, detail="User not found")
                    return {"id": user[0], "name": user[1]}
                except Exception as e:
                    span.record_exception(e)
                    raise HTTPException(status_code=500, detail=str(e))


@app.get("/cache/{key}")
async def get_cache(key: str):
    """Get value from Redis cache."""
    tracer = trace.get_tracer(__name__)
    
    with tracer.start_as_current_span("get_cache") as span:
        span.set_attribute("cache.key", key)
        
        if not redis_client:
            raise HTTPException(status_code=503, detail="Redis not available")
        
        # Query Redis
        with tracer.start_as_current_span("redis_get"):
            try:
                value = await redis_client.get(key)
                if value is None:
                    raise HTTPException(status_code=404, detail="Key not found")
                return {"key": key, "value": value.decode() if isinstance(value, bytes) else value}
            except Exception as e:
                span.record_exception(e)
                raise HTTPException(status_code=500, detail=str(e))


@app.post("/cache/{key}")
async def set_cache(key: str, value: str):
    """Set value in Redis cache."""
    tracer = trace.get_tracer(__name__)
    
    with tracer.start_as_current_span("set_cache") as span:
        span.set_attribute("cache.key", key)
        
        if not redis_client:
            raise HTTPException(status_code=503, detail="Redis not available")
        
        # Set in Redis
        with tracer.start_as_current_span("redis_set"):
            try:
                await redis_client.set(key, value)
                return {"key": key, "value": value, "status": "set"}
            except Exception as e:
                span.record_exception(e)
                raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest(REGISTRY)
