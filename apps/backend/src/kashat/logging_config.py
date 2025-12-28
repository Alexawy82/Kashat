"""
Structured logging configuration for LedgerLoop API.

Provides JSON-formatted logs for production use with support for:
- Structured log data (request IDs, user IDs, etc.)
- Log levels from environment variable
- Console and file output options
"""

import logging
import json
import sys
from datetime import datetime, UTC
from typing import Any, Dict, Optional
import os


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "exc_info", "exc_text", "thread", "threadName",
                "message", "taskName"
            ):
                log_entry[key] = value

        return json.dumps(log_entry)


class ConsoleFormatter(logging.Formatter):
    """Human-readable formatter for development console output."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        base = f"{color}{timestamp} [{record.levelname:8}]{self.RESET} {record.name}: {record.getMessage()}"

        # Add extra context if present
        extras = []
        for key in ("request_id", "user_id", "path", "method", "status_code", "duration_ms"):
            if hasattr(record, key):
                extras.append(f"{key}={getattr(record, key)}")

        if extras:
            base += f" [{', '.join(extras)}]"

        if record.exc_info:
            base += f"\n{self.formatException(record.exc_info)}"

        return base


def setup_logging(
    level: Optional[str] = None,
    json_format: bool = False,
    log_file: Optional[str] = None,
) -> None:
    """Configure logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Defaults to KASHAT_LOG_LEVEL env var or INFO.
        json_format: If True, use JSON formatter. Defaults to KASHAT_LOG_JSON env var.
        log_file: Optional file path to write logs to.
    """
    # Determine log level
    if level is None:
        level = os.getenv("KASHAT_LOG_LEVEL", "INFO").upper()

    # Determine format
    if json_format is False:
        json_format = os.getenv("KASHAT_LOG_JSON", "false").lower() == "true"

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level, logging.INFO))

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level, logging.INFO))

    if json_format:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(ConsoleFormatter())

    root_logger.addHandler(console_handler)

    # Optional file handler
    if log_file or os.getenv("KASHAT_LOG_FILE"):
        file_path = log_file or os.getenv("KASHAT_LOG_FILE")
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(getattr(logging, level, logging.INFO))
        file_handler.setFormatter(JSONFormatter())  # Always JSON for files
        root_logger.addHandler(file_handler)

    # Set levels for noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name.

    Usage:
        from kashat.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("Processing transaction", extra={"tx_id": "123"})
    """
    return logging.getLogger(name)


class LogContext:
    """Context manager for adding extra fields to all log messages in scope.

    Usage:
        with LogContext(request_id="abc123", user_id="user1"):
            logger.info("Processing request")  # Will include request_id and user_id
    """

    def __init__(self, **kwargs):
        self.extras = kwargs
        self._old_factory = None

    def __enter__(self):
        self._old_factory = logging.getLogRecordFactory()
        extras = self.extras

        def record_factory(*args, **kwargs):
            record = self._old_factory(*args, **kwargs)
            for key, value in extras.items():
                setattr(record, key, value)
            return record

        logging.setLogRecordFactory(record_factory)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logging.setLogRecordFactory(self._old_factory)
        return False
