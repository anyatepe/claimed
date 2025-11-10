"""
FastAPI application entry point for RAG PDF Chat service.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat, ingestion, health
from app.utils.logging import setup_logging

# Setup structured logging
setup_logging()

app = FastAPI(
    title="RAG PDF Chat API",
    description="Retrieval-Augmented Generation service for PDF document chat",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(ingestion.router, prefix="/api/v1/ingestion", tags=["ingestion"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "RAG PDF Chat API", "version": "0.1.0"}
