"""Storage utilities for job results."""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from app.config import settings


def ensure_storage_path():
    """Ensure storage directory exists."""
    Path(settings.result_storage_path).mkdir(parents=True, exist_ok=True)


def save_job_result(job_id: str, result: Dict[str, Any]) -> str:
    """Save job result to storage.
    
    Args:
        job_id: Job ID
        result: Result data to save
        
    Returns:
        Path to saved result file
    """
    ensure_storage_path()
    result_path = Path(settings.result_storage_path) / f"{job_id}.json"
    
    with open(result_path, "w") as f:
        json.dump(result, f, indent=2)
    
    return str(result_path)


def load_job_result(job_id: str) -> Optional[Dict[str, Any]]:
    """Load job result from storage.
    
    Args:
        job_id: Job ID
        
    Returns:
        Result data or None if not found
    """
    result_path = Path(settings.result_storage_path) / f"{job_id}.json"
    
    if not result_path.exists():
        return None
    
    with open(result_path, "r") as f:
        return json.load(f)


def delete_job_result(job_id: str) -> bool:
    """Delete job result from storage.
    
    Args:
        job_id: Job ID
        
    Returns:
        True if deleted, False if not found
    """
    result_path = Path(settings.result_storage_path) / f"{job_id}.json"
    
    if result_path.exists():
        result_path.unlink()
        return True
    
    return False
