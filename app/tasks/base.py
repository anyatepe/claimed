"""Base task utilities."""
from typing import Dict, Any, Optional
from datetime import datetime
from app.celery_app import celery_app
from app.models.job import JobStatus
from app.utils.storage import save_job_result
from app.utils.webhook import send_webhook_notification
import asyncio


def update_task_state(task_id: str, status: str, meta: Optional[Dict[str, Any]] = None):
    """Update task state in Celery."""
    celery_app.backend.store_result(
        task_id,
        {"status": status, "meta": meta or {}},
        state=status.upper(),
    )


async def handle_task_completion(
    task_id: str,
    webhook_url: Optional[str],
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
):
    """Handle task completion: save result and send webhook if configured.
    
    Args:
        task_id: Task ID
        webhook_url: Optional webhook URL
        result: Task result
        error: Error message if failed
    """
    status = JobStatus.SUCCESS if error is None else JobStatus.FAILURE
    
    # Save result if successful
    result_to_send = result
    if result:
        save_job_result(task_id, result)
        # Create a copy with result_url for webhook
        result_to_send = {**result, "result_url": f"/v1/jobs/{task_id}/result"}
    
    # Send webhook notification if configured
    if webhook_url:
        await send_webhook_notification(
            webhook_url=webhook_url,
            job_id=task_id,
            status=status.value,
            result=result_to_send,
            error=error,
        )


def run_async(coro):
    """Run async coroutine in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)
