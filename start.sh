#!/bin/bash
# Helper script to start Redis, Flask app, and Celery worker

set -e

echo "Starting Redis..."
if ! pgrep -x "redis-server" > /dev/null; then
    if command -v docker > /dev/null; then
        echo "Starting Redis with Docker..."
        docker run -d -p 6379:6379 --name redis-job-api redis:latest || docker start redis-job-api
    else
        echo "Please start Redis manually: redis-server"
        exit 1
    fi
else
    echo "Redis is already running"
fi

echo ""
echo "To start the Flask API:"
echo "  python app.py"
echo ""
echo "To start the Celery worker (in another terminal):"
echo "  celery -A celery_app.celery worker --loglevel=info"
echo ""
echo "To run tests:"
echo "  pytest tests/test_job_lifecycle.py -v"
