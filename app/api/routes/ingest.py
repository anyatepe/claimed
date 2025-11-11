"""
Document ingestion and deletion API routes.

Provides endpoints for:
- POST /v1/documents: Upload and ingest documents
- DELETE /v1/documents/{doc_id}: Delete documents from vector store
"""

import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse

from app.api.dependencies.auth import get_current_user
from app.services.upsert_service import upsert_document, delete_document

router = APIRouter(prefix="/v1/documents", tags=["documents"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def ingest_document(
    file: UploadFile = File(..., description="Document file to ingest"),
    doc_id: Optional[str] = Form(None, description="Optional document ID"),
    metadata: Optional[str] = Form(None, description="Optional metadata as JSON string"),
    tenant: Optional[str] = Form(None, description="Optional tenant identifier"),
    _: dict = Depends(get_current_user),  # Authentication dependency
):
    """
    Ingest a document into the vector store.
    
    Accepts multipart/form-data with:
    - file: Required document file
    - doc_id: Optional document ID (generated if not provided)
    - metadata: Optional JSON string with metadata
    - tenant: Optional tenant identifier
    
    Returns:
        JSON with doc_id and summary
    """
    # Generate doc_id if not provided
    if not doc_id:
        doc_id = str(uuid.uuid4())
    
    # Parse metadata if provided
    metadata_dict = {}
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON format for metadata"
            )
    
    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is required"
        )
    
    # Store file temporarily
    temp_file_path = None
    try:
        # Create temporary file
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            temp_file_path = tmp_file.name
            
            # Read and write file content
            content = await file.read()
            tmp_file.write(content)
        
        # Call upsert service
        try:
            summary = await upsert_document(
                file_path=temp_file_path,
                doc_id=doc_id,
                metadata=metadata_dict,
                tenant=tenant
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upsert document: {str(e)}"
            )
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "doc_id": doc_id,
                "summary": summary,
                "filename": file.filename,
                "tenant": tenant
            }
        )
    
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass  # Ignore cleanup errors


@router.delete("/{doc_id}", status_code=status.HTTP_200_OK)
async def delete_document_by_id(
    doc_id: str,
    tenant: Optional[str] = Query(None, description="Optional tenant identifier"),
    _: dict = Depends(get_current_user),  # Authentication dependency
):
    """
    Delete a document from the vector store.
    
    Args:
        doc_id: Document ID to delete
        tenant: Optional tenant identifier
        
    Returns:
        JSON confirmation message
    """
    if not doc_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="doc_id is required"
        )
    
    try:
        success = await delete_document(doc_id=doc_id, tenant=tenant)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with doc_id '{doc_id}' not found"
            )
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": f"Document '{doc_id}' deleted successfully",
                "doc_id": doc_id
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )
