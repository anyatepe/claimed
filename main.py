"""
Main FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os

app = FastAPI(
    title="CLAIMED Component Library API",
    description="API for the CLAIMED component library",
    version="1.0.0"
)


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker healthchecks."""
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "claimed-api"
        },
        status_code=200
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "CLAIMED Component Library API",
        "version": "1.0.0"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
