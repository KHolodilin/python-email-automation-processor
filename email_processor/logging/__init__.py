"""Logging module for email processor."""

from email_processor.logging.setup import LoggingManager, setup_logging, get_logger

__all__ = [
    "LoggingManager",
    "setup_logging",
    "get_logger",
]
