"""
Logging configuration and utilities
"""
import logging
import sys
from typing import Any, Dict

import structlog
from structlog.stdlib import LoggerFactory

from app.core.config import settings


def configure_logging() -> None:
    """Configure structured logging for the application."""

    # Configure structlog
    timestamper = structlog.processors.TimeStamper(fmt="ISO")

    shared_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.ENVIRONMENT == "development":
        # Pretty printing for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
        log_level = logging.DEBUG if settings.DEBUG else logging.INFO
    else:
        # JSON logging for production
        processors = shared_processors + [structlog.processors.JSONRenderer()]
        log_level = logging.INFO

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Set uvicorn log level
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin to add logging capability to classes."""

    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Get logger instance for this class."""
        return get_logger(self.__class__.__name__)


def log_database_operation(
    operation: str,
    collection: str,
    document_id: str = None,
    extra_data: Dict[str, Any] = None,
) -> None:
    """Log database operations with structured data."""
    logger = get_logger("database")

    log_data = {
        "operation": operation,
        "collection": collection,
    }

    if document_id:
        log_data["document_id"] = document_id

    if extra_data:
        log_data.update(extra_data)

    logger.info("Database operation", **log_data)


def log_api_request(
    method: str,
    path: str,
    user_id: str = None,
    status_code: int = None,
    duration_ms: float = None,
) -> None:
    """Log API requests with structured data."""
    logger = get_logger("api")

    log_data = {
        "method": method,
        "path": path,
    }

    if user_id:
        log_data["user_id"] = user_id

    if status_code:
        log_data["status_code"] = status_code

    if duration_ms:
        log_data["duration_ms"] = duration_ms

    logger.info("API request", **log_data)


def log_authentication_event(
    event: str,
    user_email: str = None,
    user_id: str = None,
    success: bool = True,
    reason: str = None,
) -> None:
    """Log authentication events."""
    logger = get_logger("auth")

    log_data = {
        "event": event,
        "success": success,
    }

    if user_email:
        log_data["user_email"] = user_email

    if user_id:
        log_data["user_id"] = user_id

    if reason:
        log_data["reason"] = reason

    if success:
        logger.info("Authentication event", **log_data)
    else:
        logger.warning("Authentication failed", **log_data)
