# Job API with Celery and Redis

This API provides asynchronous job processing using Celery with Redis as the message broker.

## Setup

### Prerequisites

- Python 3.8+
- Redis server running (default: localhost:6379)

### Installation

```bash
pip install -r requirements.txt
```

### Running Redis

```bash
# Using Docker
docker run -d -p 6379:6379 redis:latest

# Or using local Redis installation
redis-server
```

## Running the Application

### Start Flask API Server

```bash
python app.py
```

The API will be available at `http://localhost:5000`

### Start Celery Worker

In a separate terminal:

```bash
celery -A celery_app.celery worker --loglevel=info
```

## API Endpoints

### POST /v1/jobs

Create a new job.

**Request Body:**
```json
{
  "type": "summarize" | "classify",
  "text": "Text to process",
  "webhook_url": "https://example.com/webhook" // optional
}
```

**Response (202 Accepted):**
```json
{
  "id": "job-uuid",
  "status": "processing",
  "created_at": "2024-01-01T00:00:00"
}
```

### GET /v1/jobs/{id}

Get job status and result.

**Response (200 OK):**
```json
{
  "id": "job-uuid",
  "type": "summarize",
  "status": "completed",
  "created_at": "2024-01-01T00:00:00",
  "completed_at": "2024-01-01T00:00:01",
  "result": {
    "summary": "...",
    "original_length": 1000,
    "summary_length": 100
  }
}
```

**Status values:**
- `pending`: Job created but not yet processing
- `processing`: Job is being processed
- `completed`: Job completed successfully
- `failed`: Job failed

### GET /health

Health check endpoint.

**Response (200 OK):**
```json
{
  "status": "healthy"
}
```

## Webhook Callbacks

When a job completes (successfully or with failure), if a `webhook_url` was provided, the API will POST a callback to that URL:

**Success callback:**
```json
{
  "job_id": "job-uuid",
  "status": "completed",
  "result": {
    "summary": "...",
    ...
  }
}
```

**Failure callback:**
```json
{
  "job_id": "job-uuid",
  "status": "failed",
  "error": "Error message"
}
```

## Environment Variables

- `REDIS_URL`: Redis connection URL (default: `redis://localhost:6379/0`)
- `CELERY_BROKER_URL`: Celery broker URL (default: same as REDIS_URL)
- `CELERY_RESULT_BACKEND`: Celery result backend URL (default: same as REDIS_URL)

## Running Tests

```bash
# Install test dependencies
pip install pytest requests

# Run tests
pytest tests/test_job_lifecycle.py -v

# Or run all tests
pytest
```

## Example Usage

### Create a summarize job:

```bash
curl -X POST http://localhost:5000/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "summarize",
    "text": "This is a very long text that needs to be summarized..."
  }'
```

### Check job status:

```bash
curl http://localhost:5000/v1/jobs/{job-id}
```

### Create a job with webhook:

```bash
curl -X POST http://localhost:5000/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "classify",
    "text": "This is about programming and software development.",
    "webhook_url": "https://your-webhook-url.com/callback"
  }'
```
