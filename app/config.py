"""
Application configuration and structured logging setup.

This module provides:
- Configuration management using Pydantic BaseSettings for environment variables
- Structured logging with request ID context support
"""
import logging
import sys
from contextvars import ContextVar
from typing import Optional

from pydantic import Field

# Support both Pydantic v1 and v2
try:
    from pydantic_settings import BaseSettings
except ImportError:
    # Fallback for Pydantic v1
    from pydantic import BaseSettings


# Context variable for storing request ID
request_id_context: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database configuration
    database_url: str = Field(
        default="",
        alias="DATABASE_URL",
        description="Database connection URL"
    )
    
    # Redis configuration
    redis_url: str = Field(
        default="",
        alias="REDIS_URL",
        description="Redis connection URL"
    )
    
    # OpenAI API configuration
    openai_api_key: str = Field(
        default="",
        alias="OPENAI_API_KEY",
        description="OpenAI API key"
    )
    
    # Logging configuration
    log_level: str = Field(
        default="INFO",
        alias="LOG_LEVEL",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    # Application configuration
    app_name: str = Field(
        default="app",
        alias="APP_NAME",
        description="Application name"
    )
    
    # Environment
    environment: str = Field(
        default="development",
        alias="ENVIRONMENT",
        description="Application environment (development, staging, production)"
    )
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


class RequestIDFormatter(logging.Formatter):
    """Custom formatter that includes request ID in log records."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with request ID."""
        # Get request ID from context
        request_id = request_id_context.get()
        
        # Add request_id to record if available
        if request_id:
            record.request_id = request_id
        else:
            record.request_id = "-"
        
        return super().format(record)


def setup_logging(log_level: Optional[str] = None) -> None:
    """
    Configure structured logging with request ID support.
    
    Args:
        log_level: Optional log level override. If not provided, uses settings.log_level.
    """
    level = log_level or settings.log_level
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatter with structured format including request ID
    formatter = RequestIDFormatter(
        fmt='%(asctime)s [%(levelname)s] [%(name)s] [request_id=%(request_id)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    
    root_logger.addHandler(console_handler)
    
    # Set levels for common third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def set_request_id(request_id: str) -> None:
    """
    Set the request ID in the current context.
    
    Args:
        request_id: Unique request identifier
    """
    request_id_context.set(request_id)


def get_request_id() -> Optional[str]:
    """
    Get the current request ID from context.
    
    Returns:
        Current request ID or None if not set
    """
    return request_id_context.get()


def clear_request_id() -> None:
    """Clear the request ID from the current context."""
    request_id_context.set(None)


# Initialize logging on module import
setup_logging()
