"""
Celery tasks for async job processing.
"""
from celery_app import celery
from datetime import datetime
import requests
import os

# Import jobs dict from app (will be set by app initialization)
_jobs = None


def set_jobs(jobs_dict):
    """Set the jobs dictionary from the Flask app."""
    global _jobs
    _jobs = jobs_dict


@celery.task(bind=True, name='summarize_async')
def summarize_async(self, text, job_id, webhook_url=None):
    """Async task to summarize text."""
    try:
        # Simple summarization logic (replace with actual implementation)
        # For now, return first 100 characters as summary
        summary = text[:100] + '...' if len(text) > 100 else text
        
        result = {
            'summary': summary,
            'original_length': len(text),
            'summary_length': len(summary)
        }
        
        # Update job status
        if _jobs and job_id in _jobs:
            _jobs[job_id]['status'] = 'completed'
            _jobs[job_id]['result'] = result
            _jobs[job_id]['completed_at'] = datetime.utcnow().isoformat()
        
        # Call webhook if provided
        if webhook_url:
            try:
                requests.post(webhook_url, json={
                    'job_id': job_id,
                    'status': 'completed',
                    'result': result
                }, timeout=5)
            except Exception as e:
                # Log error but don't fail the task
                print(f"Webhook call failed: {e}")
        
        return result
    except Exception as e:
        # Update job status
        if _jobs and job_id in _jobs:
            _jobs[job_id]['status'] = 'failed'
            _jobs[job_id]['error'] = str(e)
            _jobs[job_id]['failed_at'] = datetime.utcnow().isoformat()
        
        # Call webhook if provided
        if webhook_url:
            try:
                requests.post(webhook_url, json={
                    'job_id': job_id,
                    'status': 'failed',
                    'error': str(e)
                }, timeout=5)
            except Exception:
                pass
        
        raise


@celery.task(bind=True, name='classify_async')
def classify_async(self, text, job_id, webhook_url=None):
    """Async task to classify text."""
    try:
        # Simple classification logic (replace with actual implementation)
        # For now, classify based on keywords
        categories = {
            'technology': ['code', 'programming', 'software', 'computer', 'tech'],
            'science': ['research', 'study', 'experiment', 'scientific', 'data'],
            'business': ['company', 'market', 'sales', 'revenue', 'business'],
            'general': []
        }
        
        text_lower = text.lower()
        classification = 'general'
        confidence = 0.5
        
        for category, keywords in categories.items():
            if category == 'general':
                continue
            matches = sum(1 for keyword in keywords if keyword in text_lower)
            if matches > 0:
                category_confidence = matches / len(keywords)
                if category_confidence > confidence:
                    classification = category
                    confidence = category_confidence
        
        result = {
            'category': classification,
            'confidence': confidence
        }
        
        # Update job status
        if _jobs and job_id in _jobs:
            _jobs[job_id]['status'] = 'completed'
            _jobs[job_id]['result'] = result
            _jobs[job_id]['completed_at'] = datetime.utcnow().isoformat()
        
        # Call webhook if provided
        if webhook_url:
            try:
                requests.post(webhook_url, json={
                    'job_id': job_id,
                    'status': 'completed',
                    'result': result
                }, timeout=5)
            except Exception as e:
                # Log error but don't fail the task
                print(f"Webhook call failed: {e}")
        
        return result
    except Exception as e:
        # Update job status
        if _jobs and job_id in _jobs:
            _jobs[job_id]['status'] = 'failed'
            _jobs[job_id]['error'] = str(e)
            _jobs[job_id]['failed_at'] = datetime.utcnow().isoformat()
        
        # Call webhook if provided
        if webhook_url:
            try:
                requests.post(webhook_url, json={
                    'job_id': job_id,
                    'status': 'failed',
                    'error': str(e)
                }, timeout=5)
            except Exception:
                pass
        
        raise
