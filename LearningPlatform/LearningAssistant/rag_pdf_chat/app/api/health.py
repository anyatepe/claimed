"""Health check endpoints."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    return {"status": "ready"}


@router.get("/live")
async def liveness_check():
    """Liveness check endpoint."""
    return {"status": "alive"}
