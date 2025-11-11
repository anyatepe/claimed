"""Job API endpoints."""
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
from datetime import datetime
from app.models.job import JobCreate, JobResponse, JobStatus, JobType
from app.tasks.upsert import async_upsert_document
from app.tasks.chat import long_form_chat
from app.celery_app import celery_app
from app.utils.storage import load_job_result
import uuid

router = APIRouter(prefix="/v1/jobs", tags=["jobs"])


# In-memory job registry (in production, use Redis or database)
_job_registry: Dict[str, Dict[str, Any]] = {}


def get_job_info(job_id: str) -> Dict[str, Any]:
    """Get job information from registry and Celery.
    
    Args:
        job_id: Job ID
        
    Returns:
        Job information dictionary
    """
    # Check registry
    if job_id in _job_registry:
        return _job_registry[job_id]
    
    # Check Celery backend
    result = celery_app.AsyncResult(job_id)
    
    if result.state:
        return {
            "id": job_id,
            "status": result.state.lower(),
            "result": result.result if result.successful() else None,
            "error": str(result.info) if result.failed() else None,
        }
    
    return None


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(job_request: JobCreate) -> JobResponse:
    """Create a new background job.
    
    Args:
        job_request: Job creation request
        
    Returns:
        Job response with ID and status
    """
    job_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Register job
    _job_registry[job_id] = {
        "id": job_id,
        "type": job_request.type.value,
        "status": JobStatus.PENDING.value,
        "created_at": now,
        "webhook_url": job_request.webhook_url,
    }
    
    # Dispatch task based on type
    if job_request.type == JobType.UPSERT:
        task = async_upsert_document.delay(
            job_id=job_id,
            payload=job_request.payload,
            webhook_url=job_request.webhook_url,
        )
    elif job_request.type == JobType.CHAT:
        task = long_form_chat.delay(
            job_id=job_id,
            payload=job_request.payload,
            webhook_url=job_request.webhook_url,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported job type: {job_request.type}",
        )
    
    # Update registry with task ID
    _job_registry[job_id]["task_id"] = task.id
    
    return JobResponse(
        id=job_id,
        type=job_request.type,
        status=JobStatus.PENDING,
        created_at=now,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    """Get job status and information.
    
    Args:
        job_id: Job ID
        
    Returns:
        Job response with current status
    """
    job_info = get_job_info(job_id)
    
    if not job_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found",
        )
    
    # Get task result from Celery
    task_id = job_info.get("task_id", job_id)
    result = celery_app.AsyncResult(task_id)
    
    # Determine status
    celery_state = result.state or job_info.get("status", JobStatus.PENDING.value)
    
    # Map Celery states to our JobStatus
    status_map = {
        "PENDING": JobStatus.PENDING,
        "STARTED": JobStatus.STARTED,
        "SUCCESS": JobStatus.SUCCESS,
        "FAILURE": JobStatus.FAILURE,
        "RETRY": JobStatus.RETRY,
        "REVOKED": JobStatus.REVOKED,
    }
    
    job_status = status_map.get(celery_state.upper(), JobStatus.PENDING)
    
    # Get result URL if successful
    result_url = None
    if job_status == JobStatus.SUCCESS:
        result_url = f"/v1/jobs/{job_id}/result"
    
    # Get timestamps
    created_at = job_info.get("created_at", datetime.utcnow())
    started_at = job_info.get("started_at")
    completed_at = job_info.get("completed_at")
    
    # Get error if failed
    error = None
    if job_status == JobStatus.FAILURE:
        error = str(result.info) if result.failed() else job_info.get("error")
    
    return JobResponse(
        id=job_id,
        type=JobType(job_info.get("type", "upsert")),
        status=job_status,
        created_at=created_at,
        started_at=started_at,
        completed_at=completed_at,
        result_url=result_url,
        error=error,
    )


@router.get("/{job_id}/result")
async def get_job_result(job_id: str) -> Dict[str, Any]:
    """Get job result.
    
    Args:
        job_id: Job ID
        
    Returns:
        Job result data
    """
    result = load_job_result(job_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Result for job {job_id} not found",
        )
    
    return result
