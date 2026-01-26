"""Logging setup with structlog."""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import structlog

from email_processor import __version__


def get_logger(uid: Optional[str] = None) -> structlog.BoundLogger:
    """
    Get structlog logger with optional UID context and request/correlation IDs.

    Args:
        uid: Optional email UID to add to context

    Returns:
        Bound logger with UID, request_id, and correlation_id context if provided
    """
    logger = structlog.get_logger()

    # Import here to avoid circular import
    from email_processor.utils.context import get_context_dict

    # Get context IDs (request_id, correlation_id)
    context = get_context_dict()

    # Add UID if provided
    if uid:
        context["uid"] = uid

    # Bind all context to logger
    if context:
        return logger.bind(**context)
    return logger


def setup_logging(log_config: dict[str, Any]) -> None:
    """
    Setup structlog with configurable level, format, and file output.

    Args:
        log_config: Dictionary with logging configuration:
            - level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            - format: Console format ("console" or "json")
            - format_file: File format ("console" or "json"), default "json"
            - file: Optional directory for log files (format: yyyy-mm-dd.log)
    """
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    level = level_map.get(log_config.get("level", "INFO").upper(), logging.INFO)
    console_format = log_config.get("format", "console")
    file_format = log_config.get("format_file", "json")
    log_dir = log_config.get("file")

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        level=level,
        force=True,
    )

    # Configure processors for structlog (without final renderer - will be handled by ProcessorFormatter)
    # merge_contextvars will automatically include request_id and correlation_id from context
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]

    # Configure structlog
    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Setup console formatter
    console_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer()
        if console_format == "json"
        else structlog.dev.ConsoleRenderer(),
    )

    # Setup console handler with formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(level)
    logging.root.handlers = []  # Clear existing handlers
    logging.root.addHandler(console_handler)

    # Setup file logging if configured
    if log_dir:
        try:
            log_dir_path = Path(log_dir).resolve()
            log_dir_path.mkdir(parents=True, exist_ok=True)

            # Create daily rotating file handler
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = log_dir_path / f"{today}.log"

            file_handler = logging.FileHandler(str(log_file), encoding="utf-8", mode="a")
            file_handler.setLevel(level)

            # Setup file formatter based on file_format setting
            file_formatter = structlog.stdlib.ProcessorFormatter(
                processor=structlog.processors.JSONRenderer()
                if file_format == "json"
                else structlog.dev.ConsoleRenderer(),
            )
            file_handler.setFormatter(file_formatter)
            logging.root.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            print(f"Warning: Could not setup file logging to {log_dir}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Unexpected error setting up file logging: {e}", file=sys.stderr)

    # Log version information after logging is set up
    logger = get_logger()
    logger.info("application_started", version=__version__)


class LoggingManager:
    """Logging manager class."""

    @staticmethod
    def setup(log_config: dict[str, Any]) -> None:
        """Setup structlog with configurable level, format, and file output."""
        setup_logging(log_config)

    @staticmethod
    def get_logger(uid: Optional[str] = None) -> structlog.BoundLogger:
        """Get structlog logger with optional UID context."""
        return get_logger(uid)
