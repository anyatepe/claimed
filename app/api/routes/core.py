from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


@router.get("/version")
async def version():
    """Version endpoint."""
    return {"version": "1.0.0"}
