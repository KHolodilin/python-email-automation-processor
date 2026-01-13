"""File manager for safe file operations."""

import os
from pathlib import Path

from email_processor.logging.setup import get_logger


def validate_path(base: Path, target: Path) -> bool:
    """
    Validate that target path is within base directory (protection against path traversal).
    Supports both absolute and relative paths.

    Args:
        base: Base directory path (can be absolute like C:\\downloads or relative)
        target: Target path to validate

    Returns:
        True if target is within base, False otherwise
    """
    try:
        base_resolved = base.resolve()
        target_resolved = target.resolve()
        # Check if target is within base directory using relative_to
        target_resolved.relative_to(base_resolved)
    except ValueError:
        # Path is not within base directory
        return False
    else:
        return True


def safe_save_path(folder: str, filename: str) -> Path:
    """
    Generate a safe save path for a file, avoiding duplicates.
    Supports both absolute and relative folder paths.

    Args:
        folder: Target folder path (string, can be absolute like C:\\downloads or relative like downloads)
        filename: Original filename

    Returns:
        Path object for the safe save location
    """
    folder_path = Path(folder)
    # Resolve to handle both absolute and relative paths
    folder_path_resolved = folder_path.resolve()

    # Sanitize filename to prevent path traversal in filename itself
    # Remove any path separators from filename
    logger = get_logger()
    safe_filename = os.path.basename(filename)
    if safe_filename != filename:
        logger.warning("filename_sanitized", original=filename, sanitized=safe_filename)

    base, ext = os.path.splitext(safe_filename)
    candidate = folder_path_resolved / safe_filename
    counter = 1

    while candidate.exists():
        candidate = folder_path_resolved / f"{base}_{counter:02d}{ext}"
        counter += 1

    # Validate path to prevent path traversal (works with absolute paths)
    if not validate_path(folder_path_resolved, candidate):
        raise ValueError(f"Invalid path detected (path traversal attempt?): {candidate}")

    return candidate


class FileManager:
    """File manager class for safe file operations."""

    @staticmethod
    def safe_save_path(folder: Path, filename: str) -> Path:
        """Generate a safe save path for a file, avoiding duplicates."""
        return safe_save_path(str(folder), filename)

    @staticmethod
    def validate_path(base: Path, target: Path) -> bool:
        """Validate that target path is within base directory."""
        return validate_path(base, target)

    @staticmethod
    def ensure_directory(path: Path) -> None:
        """Ensure directory exists."""
        path.mkdir(parents=True, exist_ok=True)
