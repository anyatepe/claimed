"""FastAPI application main entry point."""
from fastapi import FastAPI
from app.api.jobs import router as jobs_router

app = FastAPI(
    title="CLAIMED Job API",
    description="Background job processing API with Celery",
    version="1.0.0",
)

app.include_router(jobs_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    from app.config import settings
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
