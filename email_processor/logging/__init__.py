"""Logging module for email processor."""

from email_processor.logging.setup import LoggingManager, get_logger, setup_logging

__all__ = [
    "LoggingManager",
    "get_logger",
    "setup_logging",
]
