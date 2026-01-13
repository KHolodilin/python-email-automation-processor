"""Custom formatters for structlog file logging."""

import json
import logging
from datetime import datetime

import structlog


class StructlogFileFormatter(logging.Formatter):
    """Custom formatter for structlog file output."""

    def __init__(self, file_format: str = "json"):
        """
        Initialize formatter.

        Args:
            file_format: Format for file output ("json" or "console")
        """
        super().__init__()
        self.file_format = file_format

    def format(self, record: logging.LogRecord) -> str:
        """Format log record for file output."""
        # Extract structlog event dict if present
        if hasattr(record, "msg") and isinstance(record.msg, dict):
            event_dict = record.msg.copy()
            event_dict["timestamp"] = datetime.fromtimestamp(record.created).isoformat()
            event_dict["level"] = record.levelname
            if self.file_format == "json":
                return json.dumps(event_dict, ensure_ascii=False) + "\n"
            else:
                return structlog.dev.ConsoleRenderer()(None, None, event_dict) + "\n"
        return super().format(record)
