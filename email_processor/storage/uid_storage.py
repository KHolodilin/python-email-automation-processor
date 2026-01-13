"""UID storage for tracking processed emails."""

from datetime import datetime, timedelta
from pathlib import Path

from email_processor.logging.setup import get_logger
from email_processor.storage.file_manager import validate_path


def ensure_processed_dir(root_dir: str) -> None:
    """Ensure processed directory exists."""
    Path(root_dir).mkdir(parents=True, exist_ok=True)


def get_processed_file_path(root_dir: str, day_str: str) -> Path:
    """Get path to processed UID file for a specific day."""
    ensure_processed_dir(root_dir)
    root_path = Path(root_dir)
    filename = f"{day_str}.txt"
    file_path = root_path / filename

    # Validate path to prevent path traversal
    if not validate_path(root_path, file_path):
        raise ValueError(f"Invalid path detected: {file_path}")

    return file_path


def load_processed_for_day(root_dir: str, day_str: str, cache: dict[str, set[str]]) -> set[str]:
    """Load processed UIDs for a specific day with error handling."""
    if day_str in cache:
        return cache[day_str]

    path = get_processed_file_path(root_dir, day_str)
    if not path.exists():
        cache[day_str] = set()
        return cache[day_str]

    logger = get_logger()
    try:
        with path.open("r", encoding="utf-8") as f:
            uids = {line.strip() for line in f if line.strip()}
    except OSError as e:
        logger.error("processed_uids_read_io_error", path=str(path), error=str(e))
        cache[day_str] = set()
        return cache[day_str]
    except Exception as e:
        logger.error("processed_uids_read_error", path=str(path), error=str(e))
        cache[day_str] = set()
        return cache[day_str]

    cache[day_str] = uids
    logger.debug("processed_uids_loaded", count=len(uids), path=str(path))
    return cache[day_str]


def save_processed_uid_for_day(
    root_dir: str, day_str: str, uid: str, cache: dict[str, set[str]]
) -> None:
    """Save processed UID for a specific day with error handling."""
    uids = load_processed_for_day(root_dir, day_str, cache)
    if uid in uids:
        return

    path = get_processed_file_path(root_dir, day_str)
    logger = get_logger(uid=uid)
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(uid + "\n")
        uids.add(uid)
        logger.debug("processed_uid_added", path=str(path))
    except OSError as e:
        logger.error("processed_uid_save_io_error", path=str(path), error=str(e))
        raise
    except Exception as e:
        logger.error("processed_uid_save_error", path=str(path), error=str(e))
        raise


def cleanup_old_processed_days(root_dir: str, keep_days: int) -> None:
    """Clean up old processed UID files."""
    if keep_days <= 0:
        return

    ensure_processed_dir(root_dir)
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
                logger.info("processed_uids_file_deleted", path=str(file_path), age_days=age_days)
            except Exception as e:
                logger.error("processed_uids_delete_error", path=str(file_path), error=str(e))


class UIDStorage:
    """UID storage class for tracking processed emails."""

    def __init__(self, root_dir: str):
        """
        Initialize UID storage.

        Args:
            root_dir: Root directory for storing processed UID files
        """
        self.root_dir = root_dir
        self.cache: dict[str, set[str]] = {}

    def load_for_day(self, day_str: str) -> set[str]:
        """Load processed UIDs for a specific day."""
        return load_processed_for_day(self.root_dir, day_str, self.cache)

    def save_uid(self, day_str: str, uid: str) -> None:
        """Save processed UID for a specific day."""
        save_processed_uid_for_day(self.root_dir, day_str, uid, self.cache)

    def cleanup_old(self, keep_days: int) -> None:
        """Clean up old processed UID files."""
        cleanup_old_processed_days(self.root_dir, keep_days)

    def is_processed(self, day_str: str, uid: str) -> bool:
        """Check if UID is already processed for a specific day."""
        uids = self.load_for_day(day_str)
        return uid in uids
