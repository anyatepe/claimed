"""
FastAPI application with health checks for liveness and readiness probes.
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
import os
import psycopg2
from psycopg2 import pool
import redis
from contextlib import contextmanager
from typing import Optional

app = FastAPI(title="FastAPI Application", version="1.0.0")

# Database connection pool
db_pool: Optional[pool.ThreadedConnectionPool] = None
redis_client: Optional[redis.Redis] = None


def get_db_pool():
    """Initialize database connection pool."""
    global db_pool
    if db_pool is None:
        db_pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            database=os.getenv("POSTGRES_DB", "appdb"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        )
    return db_pool


def get_redis_client():
    """Initialize Redis client."""
    global redis_client
    if redis_client is None:
        redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=0,
            decode_responses=True,
        )
    return redis_client


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    pool = get_db_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)


@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup."""
    try:
        get_db_pool()
        get_redis_client()
    except Exception as e:
        print(f"Warning: Could not initialize connections: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Close connections on shutdown."""
    global db_pool, redis_client
    if db_pool:
        db_pool.closeall()
    if redis_client:
        redis_client.close()


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "FastAPI Application", "status": "running"}


@app.get("/health")
async def health():
    """Health check endpoint for liveness probe."""
    return {"status": "healthy"}


@app.get("/ready")
async def readiness():
    """Readiness probe endpoint - checks database and Redis connectivity."""
    checks = {
        "database": False,
        "redis": False,
    }
    
    # Check database
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                checks["database"] = True
    except Exception as e:
        print(f"Database check failed: {e}")
    
    # Check Redis
    try:
        r = get_redis_client()
        r.ping()
        checks["redis"] = True
    except Exception as e:
        print(f"Redis check failed: {e}")
    
    if all(checks.values()):
        return JSONResponse(
            status_code=200,
            content={"status": "ready", "checks": checks}
        )
    else:
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "checks": checks}
        )


@app.get("/api/v1/info")
async def info():
    """API info endpoint."""
    return {
        "app": "FastAPI Application",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
    }
