"""Storage for tracking sent files by SHA256 hash."""

import hashlib
from datetime import datetime, timedelta
from pathlib import Path

from email_processor.logging.setup import get_logger
from email_processor.storage.file_manager import validate_path


def ensure_sent_files_dir(root_dir: str) -> None:
    """Ensure sent files directory exists."""
    Path(root_dir).mkdir(parents=True, exist_ok=True)


def get_sent_files_path(root_dir: str, day_str: str) -> Path:
    """Get path to sent files hash file for a specific day."""
    ensure_sent_files_dir(root_dir)
    root_path = Path(root_dir)
    filename = f"{day_str}.txt"
    file_path = root_path / filename

    # Validate path to prevent path traversal
    if not validate_path(root_path, file_path):
        raise ValueError(f"Invalid path detected: {file_path}")

    return file_path


def get_file_hash(file_path: Path) -> str:
    """Calculate SHA256 hash of file contents.

    Args:
        file_path: Path to the file

    Returns:
        SHA256 hash as hexadecimal string (64 characters)
    """
    sha256_hash = hashlib.sha256()
    logger = get_logger()
    try:
        with file_path.open("rb") as f:
            # Read file in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        hash_value = sha256_hash.hexdigest()
        logger.debug("file_hash_calculated", file=str(file_path), hash=hash_value[:16] + "...")
        return hash_value
    except OSError as e:
        logger.error("file_hash_error", file=str(file_path), error=str(e))
        raise


def load_sent_hashes_for_day(root_dir: str, day_str: str, cache: dict[str, set[str]]) -> set[str]:
    """Load sent file hashes for a specific day with error handling."""
    if day_str in cache:
        return cache[day_str]

    path = get_sent_files_path(root_dir, day_str)
    if not path.exists():
        cache[day_str] = set()
        return cache[day_str]

    logger = get_logger()
    try:
        with path.open("r", encoding="utf-8") as f:
            hashes = {line.strip() for line in f if line.strip()}
    except OSError as e:
        logger.error("sent_files_read_io_error", path=str(path), error=str(e))
        cache[day_str] = set()
        return cache[day_str]
    except Exception as e:
        logger.error("sent_files_read_error", path=str(path), error=str(e))
        cache[day_str] = set()
        return cache[day_str]

    cache[day_str] = hashes
    logger.debug("sent_files_loaded", count=len(hashes), path=str(path))
    return cache[day_str]


def save_sent_hash_for_day(
    root_dir: str, day_str: str, file_hash: str, cache: dict[str, set[str]]
) -> None:
    """Save sent file hash for a specific day with error handling."""
    hashes = load_sent_hashes_for_day(root_dir, day_str, cache)
    if file_hash in hashes:
        return

    path = get_sent_files_path(root_dir, day_str)
    logger = get_logger()
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(file_hash + "\n")
        hashes.add(file_hash)
        logger.debug("sent_hash_added", hash=file_hash[:16] + "...", path=str(path))
    except OSError as e:
        logger.error("sent_hash_save_io_error", path=str(path), error=str(e))
        raise
    except Exception as e:
        logger.error("sent_hash_save_error", path=str(path), error=str(e))
        raise


def cleanup_old_sent_files(root_dir: str, keep_days: int) -> None:
    """Clean up old sent file hash files."""
    if keep_days <= 0:
        return

    ensure_sent_files_dir(root_dir)
    root_path = Path(root_dir)
    cutoff = datetime.now().date() - timedelta(days=keep_days)

    for file_path in root_path.iterdir():
        if not file_path.is_file():
            continue
        if file_path.suffix != ".txt":
            continue

        # Validate path to prevent path traversal
        logger = get_logger()
        if not validate_path(root_path, file_path):
            logger.warning("invalid_path_skipped", path=str(file_path))
            continue

        try:
            day = datetime.strptime(file_path.stem, "%Y-%m-%d").date()
        except ValueError:
            continue
        if day < cutoff:
            logger = get_logger()
            try:
                age_days = (datetime.now().date() - day).days
                file_path.unlink()
                logger.info("sent_files_file_deleted", path=str(file_path), age_days=age_days)
            except Exception as e:
                logger.error("sent_files_delete_error", path=str(file_path), error=str(e))


class SentFilesStorage:
    """Storage class for tracking sent files by SHA256 hash."""

    def __init__(self, root_dir: str):
        """
        Initialize sent files storage.

        Args:
            root_dir: Root directory for storing sent file hash files
        """
        self.root_dir = root_dir
        self.cache: dict[str, set[str]] = {}

    def get_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file contents."""
        return get_file_hash(file_path)

    def is_sent(self, file_path: Path, day_str: str) -> bool:
        """Check if file is already sent for a specific day.

        Args:
            file_path: Path to the file to check
            day_str: Date string in format YYYY-MM-DD

        Returns:
            True if file hash is found in storage, False otherwise
        """
        logger = get_logger()
        logger.debug("checking_if_file_sent", file=str(file_path), day=day_str)
        file_hash = self.get_file_hash(file_path)
        hashes = load_sent_hashes_for_day(self.root_dir, day_str, self.cache)
        is_sent = file_hash in hashes
        logger.debug(
            "file_sent_check_result",
            file=str(file_path),
            hash=file_hash[:16] + "...",
            is_sent=is_sent,
            total_hashes_in_storage=len(hashes),
        )
        if is_sent:
            logger.warning("file_already_sent", file=str(file_path), hash=file_hash[:16] + "...")
        return is_sent

    def mark_as_sent(self, file_path: Path, day_str: str) -> None:
        """Mark file as sent for a specific day.

        Args:
            file_path: Path to the file to mark as sent
            day_str: Date string in format YYYY-MM-DD
        """
        logger = get_logger()
        logger.debug("marking_file_as_sent", file=str(file_path), day=day_str)
        file_hash = self.get_file_hash(file_path)
        hashes_before = load_sent_hashes_for_day(self.root_dir, day_str, self.cache)
        save_sent_hash_for_day(self.root_dir, day_str, file_hash, self.cache)
        hashes_after = load_sent_hashes_for_day(self.root_dir, day_str, self.cache)
        logger.debug(
            "file_marked_as_sent_debug",
            file=str(file_path),
            hash=file_hash[:16] + "...",
            hashes_before_count=len(hashes_before),
            hashes_after_count=len(hashes_after),
            was_new=file_hash not in hashes_before,
        )
        logger.info("file_marked_as_sent", file=str(file_path), hash=file_hash[:16] + "...")

    def cleanup_old(self, keep_days: int) -> None:
        """Clean up old sent file hash files."""
        cleanup_old_sent_files(self.root_dir, keep_days)
