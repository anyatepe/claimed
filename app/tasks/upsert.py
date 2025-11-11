"""Document upsert tasks."""
from typing import Dict, Any
from app.celery_app import celery_app
from app.tasks.base import update_task_state, handle_task_completion, run_async
from app.models.job import JobStatus


@celery_app.task(bind=True, name="app.tasks.upsert.async_upsert_document")
def async_upsert_document(self, job_id: str, payload: Dict[str, Any], webhook_url: str = None):
    """Asynchronously upsert a document.
    
    Args:
        job_id: Job ID
        payload: Document payload containing document data
        webhook_url: Optional webhook URL for completion notification
        
    Returns:
        Result dictionary
    """
    try:
        # Update task state to STARTED
        update_task_state(job_id, JobStatus.STARTED.value)
        
        # Extract document data from payload
        document_id = payload.get("document_id")
        content = payload.get("content")
        metadata = payload.get("metadata", {})
        
        # Simulate document upsert operation
        # In a real implementation, this would interact with a document store
        # (e.g., Elasticsearch, Pinecone, Weaviate, etc.)
        import time
        time.sleep(2)  # Simulate processing time
        
        result = {
            "document_id": document_id,
            "status": "upserted",
            "metadata": metadata,
            "processed_at": "2024-01-01T00:00:00Z",
        }
        
        # Handle completion (save result, send webhook)
        run_async(handle_task_completion(
            task_id=job_id,
            webhook_url=webhook_url,
            result=result,
        ))
        
        update_task_state(job_id, JobStatus.SUCCESS.value, {"result": result})
        return result
        
    except Exception as e:
        error_msg = str(e)
        update_task_state(job_id, JobStatus.FAILURE.value, {"error": error_msg})
        
        # Send webhook notification for failure
        if webhook_url:
            run_async(handle_task_completion(
                task_id=job_id,
                webhook_url=webhook_url,
                error=error_msg,
            ))
        
        raise


@celery_app.task(name="app.tasks.upsert.health_check")
def health_check():
    """Periodic health check task."""
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}
