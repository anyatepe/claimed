"""Application configuration."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # Redis/Celery
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    # Webhook
    webhook_secret_key: str = "your-secret-key-change-in-production"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Storage
    result_storage_path: str = "/tmp/job_results"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
