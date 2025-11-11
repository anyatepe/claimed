# Celery Background Job Processing

This project implements background job processing using Celery with Redis as the message broker.

## Features

- **Background Tasks**: Asynchronous processing of long-running operations
- **Job API**: RESTful API for creating and monitoring jobs
- **Webhook Support**: Optional webhook notifications with HMAC signatures
- **Multi-hop Retrieval**: Long-form chat with multi-hop document retrieval
- **Job Status Tracking**: Real-time job status and result retrieval

## Architecture

```
┌─────────┐      ┌─────────┐      ┌──────────────┐
│   API   │─────▶│  Redis  │◀─────│ Celery Worker│
│ (FastAPI)│     │ (Broker)│      │              │
└─────────┘      └─────────┘      └──────────────┘
                       │
                       ▼
                ┌──────────────┐
                │ Celery Beat  │
                │  (Scheduler) │
                └──────────────┘
```

## Setup

### Prerequisites

- Python 3.11+
- Redis server
- Docker and Docker Compose (optional)

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start Redis:
```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or using system package manager
# Ubuntu/Debian: sudo apt-get install redis-server
# macOS: brew install redis
```

3. Configure environment variables (optional):
```bash
cp .env.example .env
# Edit .env with your settings
```

### Running the Application

#### Option 1: Using Docker Compose (Recommended)

```bash
docker-compose up
```

This will start:
- Redis on port 6379
- API server on port 8000
- Celery worker
- Celery beat scheduler

#### Option 2: Manual Setup

1. Start Redis:
```bash
redis-server
```

2. Start Celery worker (in separate terminal):
```bash
celery -A app.celery_app worker --loglevel=info
```

3. Start Celery beat (in separate terminal):
```bash
celery -A app.celery_app beat --loglevel=info
```

4. Start API server:
```bash
python -m app.main
# Or
uvicorn app.main:app --reload
```

## API Endpoints

### Create Job

```bash
POST /v1/jobs
Content-Type: application/json

{
  "type": "upsert|chat",
  "payload": {
    // Job-specific payload
  },
  "webhook_url": "https://example.com/webhook" // Optional
}
```

**Response:**
```json
{
  "id": "job-uuid",
  "type": "upsert",
  "status": "pending",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Get Job Status

```bash
GET /v1/jobs/{job_id}
```

**Response:**
```json
{
  "id": "job-uuid",
  "type": "upsert",
  "status": "success|pending|started|failure",
  "created_at": "2024-01-01T00:00:00Z",
  "started_at": "2024-01-01T00:00:01Z",
  "completed_at": "2024-01-01T00:00:05Z",
  "result_url": "/v1/jobs/{job_id}/result",
  "error": null
}
```

### Get Job Result

```bash
GET /v1/jobs/{job_id}/result
```

## Job Types

### Upsert Document

```json
{
  "type": "upsert",
  "payload": {
    "document_id": "doc-123",
    "content": "Document content...",
    "metadata": {
      "source": "api",
      "tags": ["tag1", "tag2"]
    }
  }
}
```

### Long-form Chat

```json
{
  "type": "chat",
  "payload": {
    "query": "What is machine learning?",
    "max_hops": 3,
    "temperature": 0.7
  }
}
```

## Webhook Notifications

When a job completes, if a `webhook_url` is provided, a POST request will be sent to that URL with:

**Headers:**
```
Content-Type: application/json
X-Webhook-Signature: sha256={hmac_signature}
```

**Body:**
```json
{
  "job_id": "job-uuid",
  "status": "success|failure",
  "result": { /* job result */ },
  "error": null
}
```

### Verifying Webhook Signatures

```python
import hmac
import hashlib
import json

def verify_webhook_signature(payload: str, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

## Testing

Run integration tests:

```bash
pytest tests/ -v
```

Run with coverage:

```bash
pytest tests/ --cov=app --cov-report=html
```

## Monitoring

### Celery Flower (Optional)

Monitor Celery tasks with Flower:

```bash
pip install flower
celery -A app.celery_app flower
```

Access at http://localhost:5555

### Health Check

```bash
curl http://localhost:8000/health
```

## Configuration

Environment variables:

- `REDIS_URL`: Redis connection URL
- `CELERY_BROKER_URL`: Celery broker URL
- `CELERY_RESULT_BACKEND`: Celery result backend URL
- `WEBHOOK_SECRET_KEY`: Secret key for HMAC signatures
- `RESULT_STORAGE_PATH`: Path for storing job results
- `API_HOST`: API server host
- `API_PORT`: API server port

## Production Considerations

1. **Security**: Change `WEBHOOK_SECRET_KEY` to a strong random value
2. **Redis Persistence**: Enable Redis persistence (AOF/RDB)
3. **Scaling**: Run multiple Celery workers for horizontal scaling
4. **Monitoring**: Set up monitoring for Redis, Celery, and API
5. **Error Handling**: Implement retry logic and dead letter queues
6. **Result Storage**: Use object storage (S3, etc.) instead of local filesystem
7. **Database**: Replace in-memory job registry with persistent storage (PostgreSQL, etc.)
