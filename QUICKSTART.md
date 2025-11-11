# Quick Start Guide

## Prerequisites

- Python 3.11+
- Redis server running

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis (if not already running)
# Using Docker:
docker run -d -p 6379:6379 redis:7-alpine

# Or using system package:
# Ubuntu/Debian: sudo systemctl start redis
# macOS: brew services start redis
```

## Running the Application

### Terminal 1: Start Celery Worker
```bash
celery -A app.celery_app worker --loglevel=info
```

### Terminal 2: Start Celery Beat (Optional - for scheduled tasks)
```bash
celery -A app.celery_app beat --loglevel=info
```

### Terminal 3: Start API Server
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## Using Docker Compose (Easiest)

```bash
docker-compose up
```

This starts all services:
- Redis on port 6379
- API on port 8000
- Celery worker
- Celery beat

## Testing the API

### Create an Upsert Job

```bash
curl -X POST http://localhost:8000/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "upsert",
    "payload": {
      "document_id": "test-1",
      "content": "Test document content",
      "metadata": {"source": "api"}
    }
  }'
```

### Create a Chat Job

```bash
curl -X POST http://localhost:8000/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "type": "chat",
    "payload": {
      "query": "What is machine learning?",
      "max_hops": 3
    }
  }'
```

### Check Job Status

```bash
curl http://localhost:8000/v1/jobs/{job_id}
```

### Get Job Result

```bash
curl http://localhost:8000/v1/jobs/{job_id}/result
```

## Running Tests

```bash
# Install test dependencies (if not already installed)
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

## Example Python Script

See `example_usage.py` for a complete example:

```bash
python example_usage.py
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Troubleshooting

### Redis Connection Error
- Ensure Redis is running: `redis-cli ping` should return `PONG`
- Check Redis URL in environment variables or `.env` file

### Celery Worker Not Processing Tasks
- Check worker logs for errors
- Verify Redis connection
- Ensure tasks are properly registered: `celery -A app.celery_app inspect registered`

### Jobs Stuck in PENDING
- Check if Celery worker is running
- Verify Redis is accessible
- Check worker logs for errors
