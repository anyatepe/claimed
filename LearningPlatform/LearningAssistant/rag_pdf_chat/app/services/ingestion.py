"""Document ingestion service."""
from fastapi import UploadFile
import aiofiles
from app.services.embeddings import EmbeddingsService
from app.services.vector_store import VectorStoreService
from app.utils.cache import CacheService
from app.models.ingestion import IngestionResponse


class IngestionService:
    """Service for ingesting documents."""
    
    def __init__(self):
        self.embeddings_service = EmbeddingsService()
        self.vector_store = VectorStoreService()
        self.cache = CacheService()
    
    async def ingest_pdf(self, file: UploadFile) -> IngestionResponse:
        """Ingest a PDF file."""
        # Save file temporarily
        file_path = f"/tmp/{file.filename}"
        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)
        
        # Extract text from PDF
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        texts = []
        for page in reader.pages:
            texts.append(page.extract_text())
        
        # Generate embeddings
        embeddings = self.embeddings_service.embed_documents(texts)
        
        # Add to vector store
        metadatas = [
            {"source": file.filename, "page": i} for i in range(len(texts))
        ]
        ids = [f"{file.filename}_page_{i}" for i in range(len(texts))]
        
        await self.vector_store.add_documents(
            texts=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )
        
        return IngestionResponse(
            document_id=file.filename,
            pages_ingested=len(texts),
            status="success",
        )
    
    async def delete_document(self, document_id: str):
        """Delete a document from the vector store."""
        # Implementation would need to track all IDs for a document
        pass
