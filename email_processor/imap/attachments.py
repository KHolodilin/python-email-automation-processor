"""Attachment handler for processing email attachments."""

import email.message
from pathlib import Path
from typing import Optional

from email_processor.config.constants import MAX_ATTACHMENT_SIZE
from email_processor.logging.setup import get_logger
from email_processor.storage.file_manager import safe_save_path
from email_processor.utils.disk_utils import check_disk_space
from email_processor.utils.email_utils import decode_mime_header_value


class AttachmentHandler:
    """Attachment handler class for processing email attachments."""

    def __init__(
        self,
        max_size: int = MAX_ATTACHMENT_SIZE,
        allowed_extensions: Optional[list[str]] = None,
        blocked_extensions: Optional[list[str]] = None,
    ):
        """
        Initialize attachment handler.

        Args:
            max_size: Maximum attachment size in bytes
            allowed_extensions: List of allowed file extensions (e.g., [".pdf", ".doc"]).
                               If None or empty, all extensions are allowed (unless blocked).
            blocked_extensions: List of blocked file extensions (e.g., [".exe", ".bat"]).
                               If None or empty, no extensions are blocked.
        """
        self.max_size = max_size
        # Normalize extensions to lowercase with dot prefix
        self.allowed_extensions: Optional[set[str]] = None
        if allowed_extensions:
            self.allowed_extensions = {
                ext.lower() if ext.startswith(".") else f".{ext.lower()}"
                for ext in allowed_extensions
            }
        self.blocked_extensions: Optional[set[str]] = None
        if blocked_extensions:
            self.blocked_extensions = {
                ext.lower() if ext.startswith(".") else f".{ext.lower()}"
                for ext in blocked_extensions
            }

    def is_allowed_extension(self, filename: str) -> bool:
        """
        Check if attachment extension is allowed.

        Args:
            filename: Attachment filename

        Returns:
            True if extension is allowed, False otherwise
        """
        ext = Path(filename).suffix.lower()

        # Check blocked extensions first (highest priority)
        if self.blocked_extensions and ext in self.blocked_extensions:
            return False

        # Check allowed extensions (if specified)
        if self.allowed_extensions:
            return ext in self.allowed_extensions

        # If no restrictions, allow all
        return True

    def save_attachment(
        self, part: email.message.Message, target_folder: Path, uid: str, dry_run: bool
    ) -> tuple[bool, int]:
        """
        Save attachment to target folder.

        Args:
            part: Email message part containing attachment
            target_folder: Target folder path
            uid: Email UID for logging
            dry_run: If True, simulate saving without actual file write

        Returns:
            Tuple of (success: bool, file_size: int). file_size is 0 if not saved or in dry_run mode.
        """
        uid_logger = get_logger(uid=uid)

        try:
            filename_raw = part.get_filename()
            filename = decode_mime_header_value(filename_raw)
            if not filename:
                uid_logger.debug("attachment_empty_filename")
                return (False, 0)

            # Check extension filter
            if not self.is_allowed_extension(filename):
                ext = Path(filename).suffix.lower()
                uid_logger.debug("attachment_extension_blocked", filename=filename, extension=ext)
                return (False, 0)

            save_path = safe_save_path(str(target_folder), filename)
            payload = part.get_payload(decode=True)
            if payload is None:
                uid_logger.warning("attachment_no_payload", filename=filename)
                return (False, 0)

            file_size = len(payload)

            # Validate attachment size
            if file_size > self.max_size:
                uid_logger.warning(
                    "attachment_too_large",
                    filename=filename,
                    size=file_size,
                    max_size=self.max_size,
                )
                return (False, 0)

            # Check disk space (with 10MB buffer)
            required_bytes = file_size + 10 * 1024 * 1024
            if not check_disk_space(save_path.parent, required_bytes):
                uid_logger.error(
                    "insufficient_disk_space",
                    filename=filename,
                    required=file_size,
                    required_with_buffer=required_bytes,
                )
                return (False, 0)

            if dry_run:
                uid_logger.info("dry_run_save_file", path=str(save_path), size=file_size)
                return (True, 0)  # Return 0 size in dry_run mode
            else:
                with save_path.open("wb") as f:
                    f.write(payload)
            uid_logger.info("file_saved", path=str(save_path))
            return (True, file_size)
        except OSError as e:
            uid_logger.error(
                "attachment_save_io_error",
                filename=filename if "filename" in locals() else "unknown",
                error=str(e),
            )
            return (False, 0)
        except Exception as e:
            uid_logger.error(
                "attachment_process_error",
                filename=filename if "filename" in locals() else "unknown",
                error=str(e),
                exc_info=True,
            )
            return (False, 0)

    def validate_size(self, size: int) -> bool:
        """Validate attachment size."""
        return size <= self.max_size
