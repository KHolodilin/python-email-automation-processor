"""Storage module for email processor."""

from email_processor.storage.file_manager import FileManager, safe_save_path, validate_path
from email_processor.storage.uid_storage import UIDStorage

__all__ = [
    "FileManager",
    "UIDStorage",
    "safe_save_path",
    "validate_path",
]
