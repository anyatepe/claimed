"""
Main Flask application for job API.
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
from celery.result import AsyncResult
import os
import uuid
from datetime import datetime
from celery_app import celery
from tasks import summarize_async, classify_async, set_jobs

app = Flask(__name__)
CORS(app)

# In-memory job storage (in production, use a database)
jobs = {}

# Initialize tasks module with jobs dict
set_jobs(jobs)


@app.route('/v1/jobs', methods=['POST'])
def create_job():
    """Create a new job."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Request body is required'}), 400
    
    job_type = data.get('type')
    if job_type not in ['summarize', 'classify']:
        return jsonify({'error': 'Invalid job type. Must be "summarize" or "classify"'}), 400
    
    text = data.get('text')
    if not text:
        return jsonify({'error': 'Text is required'}), 400
    
    webhook_url = data.get('webhook_url')
    
    # Create job ID
    job_id = str(uuid.uuid4())
    
    # Create job record
    job = {
        'id': job_id,
        'type': job_type,
        'status': 'pending',
        'created_at': datetime.utcnow().isoformat(),
        'webhook_url': webhook_url
    }
    jobs[job_id] = job
    
    # Submit task to Celery
    if job_type == 'summarize':
        task = summarize_async.delay(text, job_id, webhook_url)
    else:
        task = classify_async.delay(text, job_id, webhook_url)
    
    job['task_id'] = task.id
    job['status'] = 'processing'
    
    return jsonify({
        'id': job_id,
        'status': job['status'],
        'created_at': job['created_at']
    }), 202


@app.route('/v1/jobs/<job_id>', methods=['GET'])
def get_job(job_id):
    """Get job status and result."""
    if job_id not in jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = jobs[job_id]
    
    # Get task status from Celery
    if 'task_id' in job:
        task_result = AsyncResult(job['task_id'], app=celery)
        
        if task_result.ready():
            if task_result.successful():
                job['status'] = 'completed'
                job['result'] = task_result.result
                job['completed_at'] = datetime.utcnow().isoformat()
            else:
                job['status'] = 'failed'
                job['error'] = str(task_result.info)
                job['failed_at'] = datetime.utcnow().isoformat()
        else:
            job['status'] = 'processing'
    
    response = {
        'id': job['id'],
        'type': job['type'],
        'status': job['status'],
        'created_at': job['created_at']
    }
    
    if 'result' in job:
        response['result'] = job['result']
    if 'error' in job:
        response['error'] = job['error']
    if 'completed_at' in job:
        response['completed_at'] = job['completed_at']
    if 'failed_at' in job:
        response['failed_at'] = job['failed_at']
    
    return jsonify(response), 200


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
