"""Path utility functions."""

import os
import re
from pathlib import Path

from email_processor.storage.file_manager import validate_path
from email_processor.logging.setup import get_logger


def normalize_folder_name(name: str) -> str:
    """Normalize folder name by removing invalid characters."""
    name = name.strip()
    name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name)
    return name[:200]


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal."""
    return os.path.basename(filename)


class PathUtils:
    """Path utility class."""
    
    @staticmethod
    def normalize_folder_name(name: str) -> str:
        """Normalize folder name by removing invalid characters."""
        return normalize_folder_name(name)
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename to prevent path traversal."""
        return os.path.basename(filename)
