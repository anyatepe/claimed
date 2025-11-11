"""Job models."""
from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    STARTED = "started"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRY = "retry"
    REVOKED = "revoked"


class JobType(str, Enum):
    """Job type enumeration."""
    UPSERT = "upsert"
    CHAT = "chat"


class JobCreate(BaseModel):
    """Request model for creating a job."""
    type: JobType = Field(..., description="Job type: 'upsert' or 'chat'")
    payload: Dict[str, Any] = Field(..., description="Job payload")
    webhook_url: Optional[str] = Field(None, description="Optional webhook URL for completion notification")


class JobResponse(BaseModel):
    """Response model for job status."""
    id: str = Field(..., description="Job ID")
    type: JobType = Field(..., description="Job type")
    status: JobStatus = Field(..., description="Current job status")
    created_at: datetime = Field(..., description="Job creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Job completion timestamp")
    result_url: Optional[str] = Field(None, description="URL to retrieve job result")
    error: Optional[str] = Field(None, description="Error message if job failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "abc123",
                "type": "upsert",
                "status": "success",
                "created_at": "2024-01-01T00:00:00Z",
                "started_at": "2024-01-01T00:00:01Z",
                "completed_at": "2024-01-01T00:00:05Z",
                "result_url": "/v1/jobs/abc123/result",
                "error": None,
            }
        }
