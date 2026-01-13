"""Disk utility functions."""

import shutil
from pathlib import Path

from email_processor.logging.setup import get_logger


def check_disk_space(path: Path, required_bytes: int) -> bool:
    """
    Check if enough disk space is available.

    Args:
        path: Path to check disk space for
        required_bytes: Required bytes (including buffer)

    Returns:
        True if enough space is available, False otherwise
    """
    logger = get_logger()
    try:
        stat = shutil.disk_usage(path)
        free_space = stat.free
        has_space = free_space >= required_bytes

        if not has_space:
            logger.warning(
                "insufficient_disk_space_check",
                path=str(path),
                free_space=free_space,
                required=required_bytes,
                free_space_mb=round(free_space / (1024 * 1024), 2),
                required_mb=round(required_bytes / (1024 * 1024), 2),
            )
    except Exception as e:
        logger.warning("disk_space_check_error", path=str(path), error=str(e))
        return True  # Assume enough space if check fails
    else:
        return has_space


class DiskUtils:
    """Disk utility class."""

    @staticmethod
    def check_space(path: Path, required_bytes: int) -> bool:
        """Check if enough disk space is available."""
        return check_disk_space(path, required_bytes)

    @staticmethod
    def get_free_space(path: Path) -> int:
        """Get free disk space in bytes."""
        try:
            stat = shutil.disk_usage(path)
        except Exception as e:
            logger = get_logger()
            logger.warning("disk_space_check_error", path=str(path), error=str(e))
            return 0
        else:
            return stat.free
