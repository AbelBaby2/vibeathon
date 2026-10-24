"""Structured logging setup for Bid2Work AI."""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict

request_id_ctx_var: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    """Return the active request ID from contextvars."""
    return request_id_ctx_var.get()


def set_request_id(request_id: str) -> None:
    """Set the active request ID in contextvars."""
    request_id_ctx_var.set(request_id)


class StructuredLogFormatter(logging.Formatter):
    """JSON structured log formatter suitable for local debugging and Render logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": get_request_id(),
            "message": record.getMessage(),
        }
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            payload.update(record.extra_fields)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(log_level: str = "INFO") -> None:
    """Configure root application logging with structured output."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredLogFormatter())

    # Replace existing handlers to avoid duplicate output
    root_logger.handlers = [handler]

    # Quiet noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Retrieve a named logger."""
    return logging.getLogger(name)
