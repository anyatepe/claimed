"""Document ingestion API endpoints."""
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models.ingestion import IngestionResponse
from app.services.ingestion import IngestionService

router = APIRouter()


@router.post("/pdf", response_model=IngestionResponse)
async def ingest_pdf(file: UploadFile = File(...)):
    """Ingest a PDF document."""
    try:
        ingestion_service = IngestionService()
        result = await ingestion_service.ingest_pdf(file)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """Delete a document from the vector store."""
    try:
        ingestion_service = IngestionService()
        await ingestion_service.delete_document(document_id)
        return {"status": "deleted", "document_id": document_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
