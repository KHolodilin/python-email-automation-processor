"""IMAP email fetcher class."""

import email
import imaplib
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from email import message_from_bytes
from email.utils import parseaddr
from pathlib import Path
from typing import Any, Optional, Union

import structlog

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    from tqdm import tqdm

    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

    # Fallback: create a no-op tqdm-like object
    class tqdm:  # type: ignore[no-redef]
        def __init__(self, iterable=None, *args, **kwargs):
            self.iterable = iterable

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def __iter__(self):
            return iter(self.iterable) if self.iterable else iter([])

        def update(self, n=1):
            pass

        def set_postfix(self, **kwargs):
            """No-op method for compatibility."""

        def close(self):
            """No-op method for compatibility."""


from email_processor.config.constants import MAX_ATTACHMENT_SIZE
from email_processor.imap.archive import archive_message
from email_processor.imap.attachments import AttachmentHandler
from email_processor.imap.auth import get_imap_password
from email_processor.imap.client import imap_connect
from email_processor.imap.filters import EmailFilter
from email_processor.imap.mock_client import MockIMAP4_SSL
from email_processor.logging.setup import get_logger, setup_logging
from email_processor.storage.uid_storage import (
    UIDStorage,
    cleanup_old_processed_days,
    load_processed_for_day,
    save_processed_uid_for_day,
)
from email_processor.utils.context import set_correlation_id, set_request_id
from email_processor.utils.email_utils import decode_mime_header_value, parse_email_date
from email_processor.utils.redact import redact_email


def get_start_date(days_back: int) -> str:
    """Get start date string for IMAP search."""
    date_from = datetime.now() - timedelta(days=days_back)
    return date_from.strftime("%d-%b-%Y")


@dataclass
class ProcessingMetrics:
    """Performance metrics for email processing."""

    total_time: float = 0.0  # Total processing time in seconds
    per_email_time: list[float] = field(default_factory=list)  # Time per email in seconds
    total_downloaded_size: int = 0  # Total size of downloaded files in bytes
    imap_operations: int = 0  # Number of IMAP operations
    imap_operation_times: list[float] = field(default_factory=list)  # Time for each IMAP operation
    memory_peak: Optional[int] = None  # Peak memory usage in bytes (if available)
    memory_current: Optional[int] = None  # Current memory usage in bytes (if available)


@dataclass
class ProcessingResult:
    """Result of email processing."""

    processed: int
    skipped: int
    errors: int
    blocked: int = 0  # Number of emails with blocked attachments
    file_stats: Optional[dict[str, int]] = None
    metrics: ProcessingMetrics = field(default_factory=ProcessingMetrics)


class Fetcher:
    """IMAP email fetcher class."""

    def __init__(self, config: dict[str, Any]):
        """
        Initialize email fetcher.

        Args:
            config: Configuration dictionary with IMAP and processing settings
        """
        self.config = config

        # Setup logging
        log_config = config.get("logging", {})
        if not log_config:
            # Fallback to old format for backward compatibility
            proc_cfg = config.get("processing", {})
            log_config = {
                "level": proc_cfg.get("log_level", "INFO"),
                "format": "console",
                "format_file": "json",
                "file": proc_cfg.get("log_file") if proc_cfg.get("log_file") else None,
            }
        setup_logging(log_config)
        self.logger = structlog.get_logger()

        # Extract config
        imap_cfg = config.get("imap", {})
        self.allowed_senders = config.get("allowed_senders", [])
        self.topic_mapping = config.get("topic_mapping", {})

        self.imap_server = imap_cfg.get("server")
        self.imap_user = imap_cfg.get("user")
        self.max_retries = int(imap_cfg.get("max_retries", 5))
        self.retry_delay = int(imap_cfg.get("retry_delay", 3))

        proc_cfg = config.get("processing", {})
        self.start_days_back = int(proc_cfg.get("start_days_back", 5))
        self.archive_folder = proc_cfg.get("archive_folder", "INBOX/Processed")
        self.processed_dir = proc_cfg.get("processed_dir", "processed_uids")
        self.keep_processed_days = int(proc_cfg.get("keep_processed_days", 0))

        self.archive_only_mapped = bool(proc_cfg.get("archive_only_mapped", True))
        self.skip_non_allowed_as_processed = bool(
            proc_cfg.get("skip_non_allowed_as_processed", True)
        )
        self.skip_unmapped_as_processed = bool(proc_cfg.get("skip_unmapped_as_processed", True))

        # Progress bar setting (default: True if tqdm is available)
        self.show_progress = bool(proc_cfg.get("show_progress", TQDM_AVAILABLE))

        # Extension filtering
        allowed_extensions = proc_cfg.get("allowed_extensions")
        blocked_extensions = proc_cfg.get("blocked_extensions")

        # Initialize components
        self.filter = EmailFilter(self.allowed_senders, self.topic_mapping)
        self.attachment_handler = AttachmentHandler(
            MAX_ATTACHMENT_SIZE,
            allowed_extensions=allowed_extensions,
            blocked_extensions=blocked_extensions,
        )
        self.uid_storage = UIDStorage(self.processed_dir)

    def process(
        self, dry_run: bool = False, mock_mode: bool = False, config_path: Optional[str] = None
    ) -> ProcessingResult:
        """
        Process emails and download attachments.

        Args:
            dry_run: If True, simulate processing without downloading or archiving
            mock_mode: If True, use mock IMAP client instead of real connection
            config_path: Optional path to config file for encryption key generation

        Returns:
            ProcessingResult with statistics and performance metrics
        """
        # Initialize metrics
        metrics = ProcessingMetrics()
        process_start_time = time.time()

        # Get initial memory usage if available
        if PSUTIL_AVAILABLE:
            try:
                process = psutil.Process()
                metrics.memory_current = process.memory_info().rss
            except Exception:
                pass

        # Set up context IDs for this processing session
        request_id = set_request_id()
        correlation_id = set_correlation_id()
        self.logger = self.logger.bind(request_id=request_id, correlation_id=correlation_id)

        if dry_run:
            self.logger.info(
                "dry_run_mode", message="DRY-RUN MODE: No files will be downloaded or archived"
            )

        if mock_mode:
            self.logger.info(
                "mock_mode", message="MOCK MODE: Using simulated IMAP server (no real connection)"
            )

        # Cleanup old processed days
        try:
            cleanup_old_processed_days(self.processed_dir, self.keep_processed_days)
        except (OSError, PermissionError) as e:
            self.logger.error("cleanup_error", error=str(e), error_type=type(e).__name__)
        except Exception as e:
            self.logger.error(
                "cleanup_unexpected_error", error=str(e), error_type=type(e).__name__, exc_info=True
            )

        processed_cache: dict[str, set[str]] = {}

        mail: Union[imaplib.IMAP4_SSL, MockIMAP4_SSL, None] = None
        if mock_mode:
            # Use mock IMAP client
            mail = MockIMAP4_SSL(self.imap_server)
            self.logger.info("mock_imap_connected", server=self.imap_server)
        else:
            # Get IMAP password for real connection
            try:
                imap_password = get_imap_password(self.imap_user, config_path=config_path)
            except ValueError as e:
                self.logger.error("password_error", error=str(e), error_type=type(e).__name__)
                metrics.total_time = time.time() - process_start_time
                return ProcessingResult(
                    processed=0, skipped=0, errors=0, blocked=0, metrics=metrics
                )
            except (KeyError, RuntimeError) as e:
                self.logger.error(
                    "password_keyring_error", error=str(e), error_type=type(e).__name__
                )
                metrics.total_time = time.time() - process_start_time
                return ProcessingResult(
                    processed=0, skipped=0, errors=0, blocked=0, metrics=metrics
                )
            except Exception as e:
                self.logger.error(
                    "password_unexpected_error",
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )
                metrics.total_time = time.time() - process_start_time
                return ProcessingResult(
                    processed=0, skipped=0, errors=0, blocked=0, metrics=metrics
                )

            # Connect to real IMAP server
            try:
                mail = imap_connect(
                    self.imap_server,
                    self.imap_user,
                    imap_password,
                    self.max_retries,
                    self.retry_delay,
                )
            except ConnectionError as e:
                self.logger.error(
                    "imap_connection_failed", error=str(e), error_type=type(e).__name__
                )
                metrics.total_time = time.time() - process_start_time
                return ProcessingResult(
                    processed=0, skipped=0, errors=0, blocked=0, metrics=metrics
                )
            except (TimeoutError, OSError) as e:
                self.logger.error("imap_network_error", error=str(e), error_type=type(e).__name__)
                metrics.total_time = time.time() - process_start_time
                return ProcessingResult(
                    processed=0, skipped=0, errors=0, blocked=0, metrics=metrics
                )
            except Exception as e:
                self.logger.error(
                    "imap_connection_unexpected_error",
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )
                metrics.total_time = time.time() - process_start_time
                return ProcessingResult(
                    processed=0, skipped=0, errors=0, blocked=0, metrics=metrics
                )

        start_date = get_start_date(self.start_days_back)
        self.logger.info("processing_started", start_date=start_date)

        try:
            # Select INBOX
            try:
                imap_start = time.time()
                status, _ = mail.select("INBOX")
                metrics.imap_operations += 1
                metrics.imap_operation_times.append(time.time() - imap_start)
                if status != "OK":
                    self.logger.error("inbox_select_failed", status=status)
                    metrics.total_time = time.time() - process_start_time
                    return ProcessingResult(
                        processed=0, skipped=0, errors=0, blocked=0, metrics=metrics
                    )
            except imaplib.IMAP4.error as e:
                self.logger.error(
                    "inbox_select_imap_error", error=str(e), error_type=type(e).__name__
                )
                metrics.total_time = time.time() - process_start_time
                return ProcessingResult(
                    processed=0, skipped=0, errors=0, blocked=0, metrics=metrics
                )
            except (AttributeError, TypeError) as e:
                self.logger.error(
                    "inbox_select_invalid_state", error=str(e), error_type=type(e).__name__
                )
                metrics.total_time = time.time() - process_start_time
                return ProcessingResult(
                    processed=0, skipped=0, errors=0, blocked=0, metrics=metrics
                )
            except Exception as e:
                self.logger.error(
                    "inbox_select_unexpected_error",
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )
                metrics.total_time = time.time() - process_start_time
                return ProcessingResult(
                    processed=0, skipped=0, errors=0, blocked=0, metrics=metrics
                )

            # Search emails
            try:
                imap_start = time.time()
                status, messages = mail.search(None, f'(SINCE "{start_date}")')
                metrics.imap_operations += 1
                metrics.imap_operation_times.append(time.time() - imap_start)
                if status != "OK":
                    self.logger.error("email_search_error", status=status)
                    metrics.total_time = time.time() - process_start_time
                    return ProcessingResult(
                        processed=0, skipped=0, errors=0, blocked=0, metrics=metrics
                    )
            except imaplib.IMAP4.error as e:
                self.logger.error(
                    "email_search_imap_error", error=str(e), error_type=type(e).__name__
                )
                metrics.total_time = time.time() - process_start_time
                return ProcessingResult(
                    processed=0, skipped=0, errors=0, blocked=0, metrics=metrics
                )
            except (AttributeError, TypeError) as e:
                self.logger.error(
                    "email_search_invalid_state", error=str(e), error_type=type(e).__name__
                )
                metrics.total_time = time.time() - process_start_time
                return ProcessingResult(
                    processed=0, skipped=0, errors=0, blocked=0, metrics=metrics
                )
            except Exception as e:
                self.logger.error(
                    "email_search_unexpected_error",
                    error=str(e),
                    error_type=type(e).__name__,
                    exc_info=True,
                )
                metrics.total_time = time.time() - process_start_time
                return ProcessingResult(
                    processed=0, skipped=0, errors=0, blocked=0, metrics=metrics
                )

            email_ids = messages[0].split() if messages and messages[0] else []
            self.logger.info("emails_found", count=len(email_ids))

            processed_count = 0
            skipped_count = 0
            error_count = 0

            # Create progress bar if enabled
            email_iter = reversed(email_ids)
            if self.show_progress and len(email_ids) > 0:
                pbar = tqdm(
                    email_iter,
                    total=len(email_ids),
                    desc="Processing emails",
                    unit="email",
                    disable=False,
                )
            else:
                pbar = email_iter

            blocked_count = 0
            for msg_id in pbar:
                try:
                    email_start = time.time()
                    result, blocked_in_email = self._process_email(
                        mail, msg_id, processed_cache, dry_run, metrics
                    )
                    email_time = time.time() - email_start
                    metrics.per_email_time.append(email_time)
                    if result == "processed":
                        processed_count += 1
                    elif result == "skipped":
                        skipped_count += 1
                        blocked_count += blocked_in_email
                    elif result == "error":
                        error_count += 1

                    # Update progress bar description with current stats
                    if self.show_progress and hasattr(pbar, "set_postfix"):
                        pbar.set_postfix(
                            processed=processed_count,
                            skipped=skipped_count,
                            errors=error_count,
                            blocked=blocked_count,
                        )
                except imaplib.IMAP4.error as e:
                    msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
                    self.logger.error(
                        "imap_error_processing",
                        msg_id=msg_id_str,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    error_count += 1
                    if self.show_progress and hasattr(pbar, "set_postfix"):
                        pbar.set_postfix(
                            processed=processed_count, skipped=skipped_count, errors=error_count
                        )
                except (ValueError, TypeError, AttributeError) as e:
                    msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
                    self.logger.error(
                        "processing_data_error",
                        msg_id=msg_id_str,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    error_count += 1
                    if self.show_progress and hasattr(pbar, "set_postfix"):
                        pbar.set_postfix(
                            processed=processed_count, skipped=skipped_count, errors=error_count
                        )
                except Exception as e:
                    msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
                    self.logger.exception(
                        "unexpected_error_processing",
                        msg_id=msg_id_str,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    error_count += 1
                    if self.show_progress and hasattr(pbar, "set_postfix"):
                        pbar.set_postfix(
                            processed=processed_count, skipped=skipped_count, errors=error_count
                        )

            # Close progress bar if it was created
            if self.show_progress and len(email_ids) > 0 and hasattr(pbar, "close"):
                pbar.close()

            self.logger.info(
                "processing_complete",
                processed=processed_count,
                skipped=skipped_count,
                errors=error_count,
                blocked=blocked_count,
            )

            # Collect file statistics from all folders in topic_mapping
            file_stats: Optional[dict[str, int]] = None
            if processed_count > 0 and not dry_run:
                try:
                    file_stats = {}
                    for folder_path_str in self.topic_mapping.values():
                        folder_path = Path(folder_path_str)
                        if folder_path.exists() and folder_path.is_dir():
                            for file_path in folder_path.rglob("*"):
                                if file_path.is_file():
                                    ext = file_path.suffix.lower() or "(no extension)"
                                    file_stats[ext] = file_stats.get(ext, 0) + 1
                    if file_stats:
                        sorted_stats = dict(
                            sorted(file_stats.items(), key=lambda x: x[1], reverse=True)
                        )
                        logging.info("File statistics by extension: %s", sorted_stats)
                        file_stats = sorted_stats
                except (OSError, PermissionError) as e:
                    logging.debug("Could not collect file statistics: %s", e)
                except Exception as e:
                    logging.debug("Unexpected error collecting file statistics: %s", e)

            # Calculate final metrics
            metrics.total_time = time.time() - process_start_time
            if PSUTIL_AVAILABLE:
                try:
                    process = psutil.Process()
                    metrics.memory_current = process.memory_info().rss
                    if metrics.memory_peak is None or metrics.memory_current > metrics.memory_peak:
                        metrics.memory_peak = metrics.memory_current
                except Exception:
                    pass

            return ProcessingResult(
                processed=processed_count,
                skipped=skipped_count,
                errors=error_count,
                blocked=blocked_count,
                file_stats=file_stats,
                metrics=metrics,
            )

        finally:
            if mail:
                try:
                    mail.logout()
                except (imaplib.IMAP4.error, AttributeError) as e:
                    logging.debug("Error during IMAP logout (non-critical): %s", e)
                except Exception as e:
                    logging.debug("Unexpected error during IMAP logout (non-critical): %s", e)
            logging.info("Script finished.")

    def _process_email(
        self,
        mail: Union[imaplib.IMAP4_SSL, Any],
        msg_id: bytes,
        processed_cache: dict[str, set[str]],
        dry_run: bool,
        metrics: ProcessingMetrics,
    ) -> tuple[str, int]:
        """
        Process a single email message.

        Args:
            mail: IMAP connection
            msg_id: Message ID
            processed_cache: Cache of processed UIDs
            dry_run: If True, simulate processing
            metrics: Performance metrics to update

        Returns:
            Tuple of (result: str, blocked_count: int) where:
            - result is "processed", "skipped", or "error"
            - blocked_count is number of blocked attachments in this email
        """
        # Fetch UID
        try:
            imap_start = time.time()
            status, meta = mail.fetch(msg_id, "(UID RFC822.SIZE BODYSTRUCTURE)")  # type: ignore[arg-type]
            metrics.imap_operations += 1
            metrics.imap_operation_times.append(time.time() - imap_start)
            if status != "OK" or not meta or not meta[0]:
                self.logger.debug(
                    "uid_fetch_failed",
                    msg_id=msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id),
                    status=status,
                )
                return ("skipped", 0)
        except imaplib.IMAP4.error as e:
            msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
            self.logger.warning(
                "uid_fetch_imap_error", msg_id=msg_id_str, error=str(e), error_type=type(e).__name__
            )
            return ("error", 0)
        except (AttributeError, IndexError, TypeError) as e:
            msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
            self.logger.warning(
                "uid_fetch_data_error", msg_id=msg_id_str, error=str(e), error_type=type(e).__name__
            )
            return ("error", 0)
        except Exception as e:
            msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
            self.logger.warning(
                "uid_fetch_unexpected_error",
                msg_id=msg_id_str,
                error=str(e),
                error_type=type(e).__name__,
            )
            return ("error", 0)

        try:
            raw = (
                meta[0][0].decode("utf-8", errors="ignore")
                if isinstance(meta[0], tuple)
                else meta[0].decode("utf-8", errors="ignore")
            )
            uid_match = re.search(r"UID (\d+)", raw)
            uid = uid_match.group(1) if uid_match else None
            if not uid:
                self.logger.debug(
                    "uid_extraction_failed",
                    msg_id=msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id),
                )
                return ("skipped", 0)
        except (AttributeError, IndexError, UnicodeDecodeError) as e:
            msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
            self.logger.warning(
                "uid_parse_error", msg_id=msg_id_str, error=str(e), error_type=type(e).__name__
            )
            return ("error", 0)
        except Exception as e:
            msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
            self.logger.warning(
                "uid_parse_unexpected_error",
                msg_id=msg_id_str,
                error=str(e),
                error_type=type(e).__name__,
            )
            return ("error", 0)

        uid_logger = get_logger(uid=uid)

        # Fetch headers
        try:
            imap_start = time.time()
            status, header_data = mail.fetch(
                msg_id,  # type: ignore[arg-type]
                "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])",
            )
            metrics.imap_operations += 1
            metrics.imap_operation_times.append(time.time() - imap_start)
            if status != "OK" or not header_data or not header_data[0]:
                uid_logger.debug("header_fetch_failed", status=status)
                return ("skipped", 0)
        except imaplib.IMAP4.error as e:
            uid_logger.warning("header_fetch_imap_error", error=str(e), error_type=type(e).__name__)
            return ("error", 0)
        except (AttributeError, IndexError, TypeError) as e:
            uid_logger.warning("header_fetch_data_error", error=str(e), error_type=type(e).__name__)
            return ("error", 0)
        except Exception as e:
            uid_logger.warning(
                "header_fetch_unexpected_error", error=str(e), error_type=type(e).__name__
            )
            return ("error", 0)

        try:
            header_bytes = (
                header_data[0][1] if isinstance(header_data[0], tuple) else header_data[0]
            )
            if not header_bytes:
                uid_logger.debug("header_empty")
                return ("skipped", 0)
            header_msg = message_from_bytes(header_bytes)
        except (email.errors.MessageParseError, UnicodeDecodeError) as e:
            uid_logger.warning("header_parse_error", error=str(e), error_type=type(e).__name__)
            return ("error", 0)
        except (AttributeError, IndexError, TypeError) as e:
            uid_logger.warning("header_parse_data_error", error=str(e), error_type=type(e).__name__)
            return ("error", 0)
        except Exception as e:
            uid_logger.warning(
                "header_parse_unexpected_error", error=str(e), error_type=type(e).__name__
            )
            return ("error", 0)

        sender = parseaddr(header_msg.get("From", ""))[1]
        subject = decode_mime_header_value(header_msg.get("Subject", "(no subject)"))
        date_raw = header_msg.get("Date", "")
        dt = parse_email_date(date_raw)
        day_str = dt.strftime("%Y-%m-%d") if dt else "nodate"

        # Check if already processed
        try:
            processed_for_day = load_processed_for_day(self.processed_dir, day_str, processed_cache)
            if uid in processed_for_day:
                uid_logger.debug("already_processed")
                return ("skipped", 0)
        except (OSError, PermissionError) as e:
            uid_logger.error(
                "processed_uids_load_io_error",
                day=day_str,
                error=str(e),
                error_type=type(e).__name__,
            )
            return ("error", 0)
        except Exception as e:
            uid_logger.error(
                "processed_uids_load_unexpected_error",
                day=day_str,
                error=str(e),
                error_type=type(e).__name__,
            )
            return ("error", 0)

        # Sender filter
        if not self.filter.is_allowed_sender(sender):
            uid_logger.debug("sender_not_allowed", sender=redact_email(sender))
            if self.skip_non_allowed_as_processed:
                try:
                    save_processed_uid_for_day(self.processed_dir, day_str, uid, processed_cache)
                except (OSError, PermissionError) as e:
                    uid_logger.error(
                        "processed_uid_save_io_error_non_allowed",
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                except Exception as e:
                    uid_logger.error(
                        "processed_uid_save_unexpected_error_non_allowed",
                        error=str(e),
                        error_type=type(e).__name__,
                    )
            return ("skipped", 0)

        # Folder determination
        mapped_folder = None
        try:
            mapped_folder = self.filter.resolve_folder(subject)
            target_folder = Path(mapped_folder)
            target_folder_resolved = target_folder.resolve()

            target_folder_resolved.mkdir(parents=True, exist_ok=True)
            target_folder = target_folder_resolved
        except (OSError, PermissionError) as e:
            uid_logger.error(
                "target_folder_create_io_error", error=str(e), error_type=type(e).__name__
            )
            return ("error", 0)
        except Exception as e:
            uid_logger.error(
                "target_folder_create_unexpected_error", error=str(e), error_type=type(e).__name__
            )
            return ("error", 0)

        # Fetch full message
        try:
            imap_start = time.time()
            status, full_data = mail.fetch(msg_id, "(RFC822)")  # type: ignore[arg-type]
            metrics.imap_operations += 1
            metrics.imap_operation_times.append(time.time() - imap_start)
            if status != "OK" or not full_data or not full_data[0]:
                uid_logger.warning("message_fetch_failed", status=status)
                try:
                    save_processed_uid_for_day(self.processed_dir, day_str, uid, processed_cache)
                except (OSError, PermissionError) as e:
                    uid_logger.error(
                        "processed_uid_save_io_error_after_fetch",
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                except Exception as e:
                    uid_logger.error(
                        "processed_uid_save_unexpected_error_after_fetch",
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                return ("skipped", 0)
        except imaplib.IMAP4.error as e:
            uid_logger.error("message_fetch_imap_error", error=str(e), error_type=type(e).__name__)
            return ("error", 0)
        except (AttributeError, IndexError, TypeError) as e:
            uid_logger.error("message_fetch_data_error", error=str(e), error_type=type(e).__name__)
            return ("error", 0)
        except Exception as e:
            uid_logger.error(
                "message_fetch_unexpected_error", error=str(e), error_type=type(e).__name__
            )
            return ("error", 0)

        try:
            msg_bytes = full_data[0][1] if isinstance(full_data[0], tuple) else full_data[0]
            if not msg_bytes:
                uid_logger.warning("message_body_empty")
                return ("skipped", 0)
            msg = message_from_bytes(msg_bytes)
        except (email.errors.MessageParseError, UnicodeDecodeError) as e:
            uid_logger.error("message_parse_error", error=str(e), error_type=type(e).__name__)
            return ("error", 0)
        except (AttributeError, IndexError, TypeError) as e:
            uid_logger.error("message_parse_data_error", error=str(e), error_type=type(e).__name__)
            return ("error", 0)
        except Exception as e:
            uid_logger.error(
                "message_parse_unexpected_error", error=str(e), error_type=type(e).__name__
            )
            return ("error", 0)

        # Process attachments
        attachments_found = False
        attachment_errors = []
        blocked_attachments = 0
        try:
            for part in msg.walk():
                if part.get_content_disposition() == "attachment":
                    result = self.attachment_handler.save_attachment(
                        part, target_folder, uid, dry_run
                    )
                    if isinstance(result, tuple):
                        success, file_size = result
                        if success:
                            attachments_found = True
                            if file_size:
                                metrics.total_downloaded_size += file_size
                        else:
                            # Check if it was blocked by extension filter (not a real error)
                            filename_raw = part.get_filename()
                            if filename_raw:
                                filename = decode_mime_header_value(filename_raw)
                                if filename and not self.attachment_handler.is_allowed_extension(
                                    filename
                                ):
                                    blocked_attachments += 1
                                else:
                                    attachment_errors.append("Failed to save attachment")
                            else:
                                attachment_errors.append("Failed to save attachment")
                    elif result:
                        attachments_found = True
                    else:
                        attachment_errors.append("Failed to save attachment")
        except (AttributeError, TypeError) as e:
            uid_logger.error("message_walk_data_error", error=str(e), error_type=type(e).__name__)
            return ("error", 0)
        except Exception as e:
            uid_logger.error(
                "message_walk_unexpected_error",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            return ("error", 0)

        # Save processed UID
        try:
            save_processed_uid_for_day(self.processed_dir, day_str, uid, processed_cache)
        except (OSError, PermissionError) as e:
            uid_logger.error(
                "processed_uid_save_io_error", error=str(e), error_type=type(e).__name__
            )
            return ("error", 0)
        except Exception as e:
            uid_logger.error(
                "processed_uid_save_unexpected_error", error=str(e), error_type=type(e).__name__
            )
            return ("error", 0)

        # Archive
        if mapped_folder and self.archive_only_mapped:
            if dry_run:
                uid_logger.info("dry_run_archive", archive_folder=self.archive_folder)
            else:
                try:
                    archive_message(mail, uid, self.archive_folder)
                except imaplib.IMAP4.error as e:
                    uid_logger.error(
                        "archive_imap_error", error=str(e), error_type=type(e).__name__
                    )
                except (ConnectionError, OSError) as e:
                    uid_logger.error(
                        "archive_connection_error", error=str(e), error_type=type(e).__name__
                    )
                except Exception as e:
                    uid_logger.error(
                        "archive_unexpected_error", error=str(e), error_type=type(e).__name__
                    )

        if attachments_found:
            return ("processed", 0)
        elif attachment_errors:
            # Only return error if there were actual errors (not just blocked extensions)
            return ("error", 0)
        elif blocked_attachments > 0:
            # If only blocked attachments (no real errors), treat as skipped
            uid_logger.debug("attachments_blocked", count=blocked_attachments)
            return ("skipped", blocked_attachments)
        else:
            uid_logger.debug("no_attachments")
            return ("skipped", 0)
