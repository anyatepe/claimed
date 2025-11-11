"""
Example FastAPI application using the ingest routes.

To run:
    uvicorn example_main:app --reload

To test:
    # With API key
    curl -X POST "http://localhost:8000/v1/documents" \
         -H "X-API-Key: test-api-key-123" \
         -F "file=@tests/sample.pdf"
    
    # With JWT
    curl -X POST "http://localhost:8000/v1/documents" \
         -H "Authorization: Bearer test-jwt-token" \
         -F "file=@tests/sample.pdf" \
         -F "doc_id=my-doc-123" \
         -F 'metadata={"author":"John Doe"}' \
         -F "tenant=acme-corp"
    
    # Delete document
    curl -X DELETE "http://localhost:8000/v1/documents/my-doc-123?tenant=acme-corp" \
         -H "X-API-Key: test-api-key-123"
"""

import os
from fastapi import FastAPI

from app.api.routes.ingest import router

# Set up test credentials (in production, use proper secret management)
os.environ.setdefault("API_KEY", "test-api-key-123")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")

app = FastAPI(
    title="Document Ingestion API",
    description="API for ingesting and deleting documents",
    version="1.0.0",
)

app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Document Ingestion API",
        "endpoints": {
            "POST /v1/documents": "Ingest a document",
            "DELETE /v1/documents/{doc_id}": "Delete a document",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
