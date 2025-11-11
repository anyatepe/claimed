#!/bin/bash
# Start Celery worker

celery -A app.celery_app worker --loglevel=info
