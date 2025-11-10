"""Logging utilities."""
import structlog
import sys
import os


def setup_logging():
    """Setup structured logging."""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            log_level=log_level,
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str = None):
    """Get a structured logger."""
    return structlog.get_logger(name)
