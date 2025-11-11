"""Celery application configuration."""
from celery import Celery
from app.config import settings

# Create Celery instance
celery_app = Celery(
    "claimed",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.upsert", "app.tasks.chat"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    beat_schedule={
        "periodic-health-check": {
            "task": "app.tasks.upsert.health_check",
            "schedule": 60.0,  # Every minute
        },
    },
)
