"""Logging setup with structlog."""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import structlog

from email_processor.logging.formatters import StructlogFileFormatter


def get_logger(uid: Optional[str] = None) -> structlog.BoundLogger:
    """
    Get structlog logger with optional UID context.
    
    Args:
        uid: Optional email UID to add to context
    
    Returns:
        Bound logger with UID context if provided
    """
    logger = structlog.get_logger()
    if uid:
        return logger.bind(uid=uid)
    return logger


def setup_logging(log_config: Dict[str, Any]) -> None:
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
    
    # Configure processors for structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    # Add format processor based on output type
    if console_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Setup file logging if configured
    if log_dir:
        try:
            log_dir_path = Path(log_dir).resolve()
            log_dir_path.mkdir(parents=True, exist_ok=True)
            
            # Create daily rotating file handler
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = log_dir_path / f"{today}.log"
            
            file_handler = logging.FileHandler(str(log_file), encoding="utf-8", mode='a')
            file_handler.setLevel(level)
            
            file_handler.setFormatter(StructlogFileFormatter(file_format))
            logging.root.addHandler(file_handler)
        except (OSError, IOError, PermissionError) as e:
            import sys
            print(f"Warning: Could not setup file logging to {log_dir}: {e}", file=sys.stderr)
        except Exception as e:
            import sys
            print(f"Warning: Unexpected error setting up file logging: {e}", file=sys.stderr)


class LoggingManager:
    """Logging manager class."""
    
    @staticmethod
    def setup(log_config: Dict[str, Any]) -> None:
        """Setup structlog with configurable level, format, and file output."""
        setup_logging(log_config)
    
    @staticmethod
    def get_logger(uid: Optional[str] = None) -> structlog.BoundLogger:
        """Get structlog logger with optional UID context."""
        return get_logger(uid)
