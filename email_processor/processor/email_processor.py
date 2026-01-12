"""Main email processor class."""

import re
import imaplib
import email
from email import message_from_bytes
from email.utils import parseaddr
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Set, Optional, Union
from dataclasses import dataclass
import structlog
import logging

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    # Fallback: create a no-op tqdm-like object
    class tqdm:
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
            pass
        
        def close(self):
            """No-op method for compatibility."""
            pass

from email_processor.logging.setup import setup_logging, get_logger
from email_processor.imap.client import imap_connect
from email_processor.imap.archive import archive_message
from email_processor.imap.auth import get_imap_password
from email_processor.imap.mock_client import MockIMAP4_SSL
from email_processor.storage.uid_storage import (
    UIDStorage,
    cleanup_old_processed_days,
    load_processed_for_day,
    save_processed_uid_for_day,
)
from email_processor.storage.file_manager import validate_path, safe_save_path
from email_processor.utils.email_utils import decode_mime_header_value, parse_email_date
from email_processor.utils.path_utils import normalize_folder_name
from email_processor.utils.folder_resolver import resolve_custom_folder
from email_processor.utils.disk_utils import check_disk_space
from email_processor.processor.filters import EmailFilter
from email_processor.processor.attachments import AttachmentHandler
from email_processor.config.constants import MAX_ATTACHMENT_SIZE


def get_start_date(days_back: int) -> str:
    """Get start date string for IMAP search."""
    date_from = datetime.now() - timedelta(days=days_back)
    return date_from.strftime("%d-%b-%Y")


@dataclass
class ProcessingResult:
    """Result of email processing."""
    processed: int
    skipped: int
    errors: int
    file_stats: Optional[Dict[str, int]] = None


class EmailProcessor:
    """Main email processor class."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize email processor.
        
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
        download_dir_str = proc_cfg.get("download_dir", "downloads")
        self.download_dir = Path(download_dir_str).resolve()
        self.archive_folder = proc_cfg.get("archive_folder", "INBOX/Processed")
        self.processed_dir = proc_cfg.get("processed_dir", "processed_uids")
        self.keep_processed_days = int(proc_cfg.get("keep_processed_days", 0))
        
        self.archive_only_mapped = bool(proc_cfg.get("archive_only_mapped", True))
        self.skip_non_allowed_as_processed = bool(proc_cfg.get("skip_non_allowed_as_processed", True))
        self.skip_unmapped_as_processed = bool(proc_cfg.get("skip_unmapped_as_processed", True))
        
        # Progress bar setting (default: True if tqdm is available)
        self.show_progress = bool(proc_cfg.get("show_progress", TQDM_AVAILABLE))
        
        # Extension filtering
        allowed_extensions = proc_cfg.get("allowed_extensions")
        blocked_extensions = proc_cfg.get("blocked_extensions")
        
        # Initialize components
        self.filter = EmailFilter(self.allowed_senders, self.topic_mapping)
        self.attachment_handler = AttachmentHandler(
            self.download_dir,
            MAX_ATTACHMENT_SIZE,
            allowed_extensions=allowed_extensions,
            blocked_extensions=blocked_extensions,
        )
        self.uid_storage = UIDStorage(self.processed_dir)
    
    def process(self, dry_run: bool = False, mock_mode: bool = False) -> ProcessingResult:
        """
        Process emails and download attachments.
        
        Args:
            dry_run: If True, simulate processing without downloading or archiving
            mock_mode: If True, use mock IMAP client instead of real connection
        
        Returns:
            ProcessingResult with statistics
        """
        if dry_run:
            self.logger.info("dry_run_mode", message="DRY-RUN MODE: No files will be downloaded or archived")
        
        if mock_mode:
            self.logger.info("mock_mode", message="MOCK MODE: Using simulated IMAP server (no real connection)")
        
        # Cleanup old processed days
        try:
            cleanup_old_processed_days(self.processed_dir, self.keep_processed_days)
        except Exception as e:
            self.logger.error("cleanup_error", error=str(e))
        
        processed_cache: Dict[str, Set[str]] = {}
        
        mail = None
        if mock_mode:
            # Use mock IMAP client
            mail = MockIMAP4_SSL(self.imap_server)
            self.logger.info("mock_imap_connected", server=self.imap_server)
        else:
            # Get IMAP password for real connection
            try:
                imap_password = get_imap_password(self.imap_user)
            except ValueError as e:
                self.logger.error("password_error", error=str(e))
                return ProcessingResult(processed=0, skipped=0, errors=0)
            except Exception as e:
                self.logger.error("password_unexpected_error", error=str(e), exc_info=True)
                return ProcessingResult(processed=0, skipped=0, errors=0)
            
            # Connect to real IMAP server
            try:
                mail = imap_connect(self.imap_server, self.imap_user, imap_password, self.max_retries, self.retry_delay)
            except ConnectionError as e:
                self.logger.error("imap_connection_failed", error=str(e))
                return ProcessingResult(processed=0, skipped=0, errors=0)
            except Exception as e:
                self.logger.error("imap_connection_unexpected_error", error=str(e), exc_info=True)
                return ProcessingResult(processed=0, skipped=0, errors=0)
        
        start_date = get_start_date(self.start_days_back)
        self.logger.info("processing_started", start_date=start_date)
        
        try:
            # Select INBOX
            try:
                status, _ = mail.select("INBOX")
                if status != "OK":
                    self.logger.error("inbox_select_failed", status=status)
                    return ProcessingResult(processed=0, skipped=0, errors=0)
            except Exception as e:
                self.logger.error("inbox_select_error", error=str(e), exc_info=True)
                return ProcessingResult(processed=0, skipped=0, errors=0)
            
            # Search emails
            try:
                status, messages = mail.search(None, f'(SINCE "{start_date}")')
                if status != "OK":
                    self.logger.error("email_search_error", status=status)
                    return ProcessingResult(processed=0, skipped=0, errors=0)
            except Exception as e:
                self.logger.error("email_search_exception", error=str(e), exc_info=True)
                return ProcessingResult(processed=0, skipped=0, errors=0)
            
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
            
            for msg_id in pbar:
                try:
                    result = self._process_email(mail, msg_id, processed_cache, dry_run)
                    if result == "processed":
                        processed_count += 1
                    elif result == "skipped":
                        skipped_count += 1
                    elif result == "error":
                        error_count += 1
                    
                    # Update progress bar description with current stats
                    if self.show_progress and hasattr(pbar, 'set_postfix'):
                        pbar.set_postfix(
                            processed=processed_count,
                            skipped=skipped_count,
                            errors=error_count
                        )
                except imaplib.IMAP4.error as e:
                    self.logger.error("imap_error_processing", msg_id=msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id), error=str(e))
                    error_count += 1
                    if self.show_progress and hasattr(pbar, 'set_postfix'):
                        pbar.set_postfix(
                            processed=processed_count,
                            skipped=skipped_count,
                            errors=error_count
                        )
                except Exception as e:
                    self.logger.exception("unexpected_error_processing", msg_id=msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id), error=str(e))
                    error_count += 1
                    if self.show_progress and hasattr(pbar, 'set_postfix'):
                        pbar.set_postfix(
                            processed=processed_count,
                            skipped=skipped_count,
                            errors=error_count
                        )
            
            # Close progress bar if it was created
            if self.show_progress and len(email_ids) > 0 and hasattr(pbar, 'close'):
                pbar.close()
            
            self.logger.info("processing_complete", processed=processed_count, skipped=skipped_count, errors=error_count)
            
            # Collect file statistics
            file_stats = None
            if processed_count > 0 and not dry_run:
                try:
                    file_stats = {}
                    for file_path in self.download_dir.rglob("*"):
                        if file_path.is_file():
                            ext = file_path.suffix.lower() or "(no extension)"
                            file_stats[ext] = file_stats.get(ext, 0) + 1
                    if file_stats:
                        sorted_stats = dict(sorted(file_stats.items(), key=lambda x: x[1], reverse=True))
                        logging.info("File statistics by extension: %s", sorted_stats)
                        file_stats = sorted_stats
                except Exception as e:
                    logging.debug("Could not collect file statistics: %s", e)
            
            return ProcessingResult(
                processed=processed_count,
                skipped=skipped_count,
                errors=error_count,
                file_stats=file_stats,
            )
        
        finally:
            if mail:
                try:
                    mail.logout()
                except Exception as e:
                    logging.debug("Error during IMAP logout (non-critical): %s", e)
            logging.info("Script finished.")
    
    def _process_email(self, mail: Union[imaplib.IMAP4_SSL, Any], msg_id: bytes, processed_cache: Dict[str, Set[str]], dry_run: bool) -> str:
        """
        Process a single email message.
        
        Returns:
            "processed", "skipped", or "error"
        """
        # Fetch UID
        try:
            status, meta = mail.fetch(msg_id, "(UID RFC822.SIZE BODYSTRUCTURE)")
            if status != "OK" or not meta or not meta[0]:
                self.logger.debug("uid_fetch_failed", msg_id=msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id), status=status)
                return "skipped"
        except Exception as e:
            self.logger.warning("uid_fetch_exception", msg_id=msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id), error=str(e))
            return "error"
        
        try:
            raw = meta[0][0].decode("utf-8", errors="ignore") if isinstance(meta[0], tuple) else meta[0].decode("utf-8", errors="ignore")
            uid_match = re.search(r"UID (\d+)", raw)
            uid = uid_match.group(1) if uid_match else None
            if not uid:
                self.logger.debug("uid_extraction_failed", msg_id=msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id))
                return "skipped"
        except Exception as e:
            self.logger.warning("uid_parse_error", msg_id=msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id), error=str(e))
            return "error"
        
        uid_logger = get_logger(uid=uid)
        
        # Fetch headers
        try:
            status, header_data = mail.fetch(msg_id, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])")
            if status != "OK" or not header_data or not header_data[0]:
                uid_logger.debug("header_fetch_failed", status=status)
                return "skipped"
        except Exception as e:
            uid_logger.warning("header_fetch_exception", error=str(e))
            return "error"
        
        try:
            header_bytes = header_data[0][1] if isinstance(header_data[0], tuple) else header_data[0]
            if not header_bytes:
                uid_logger.debug("header_empty")
                return "skipped"
            header_msg = message_from_bytes(header_bytes)
        except Exception as e:
            uid_logger.warning("header_parse_error", error=str(e))
            return "error"
        
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
                return "skipped"
        except Exception as e:
            uid_logger.error("processed_uids_load_error", day=day_str, error=str(e))
            return "error"
        
        # Sender filter
        if not self.filter.is_allowed_sender(sender):
            uid_logger.debug("sender_not_allowed", sender=sender)
            if self.skip_non_allowed_as_processed:
                try:
                    save_processed_uid_for_day(self.processed_dir, day_str, uid, processed_cache)
                except Exception as e:
                    uid_logger.error("processed_uid_save_error_non_allowed", error=str(e))
            return "skipped"
        
        # Folder determination
        try:
            mapped_folder = self.filter.resolve_folder(subject)
            if mapped_folder:
                target_folder = self.download_dir / mapped_folder
            else:
                target_folder = self.download_dir / normalize_folder_name(subject)
            
            download_dir_resolved = self.download_dir.resolve()
            target_folder_resolved = target_folder.resolve()
            
            if not validate_path(download_dir_resolved, target_folder_resolved):
                uid_logger.error("invalid_target_folder", target_folder=str(target_folder))
                return "error"
            
            target_folder_resolved.mkdir(parents=True, exist_ok=True)
            target_folder = target_folder_resolved
        except Exception as e:
            uid_logger.error("target_folder_create_error", error=str(e))
            return "error"
        
        # Fetch full message
        try:
            status, full_data = mail.fetch(msg_id, "(RFC822)")
            if status != "OK" or not full_data or not full_data[0]:
                uid_logger.warning("message_fetch_failed", status=status)
                try:
                    save_processed_uid_for_day(self.processed_dir, day_str, uid, processed_cache)
                except Exception as e:
                    uid_logger.error("processed_uid_save_error_after_fetch", error=str(e))
                return "skipped"
        except Exception as e:
            uid_logger.error("message_fetch_exception", error=str(e))
            return "error"
        
        try:
            msg_bytes = full_data[0][1] if isinstance(full_data[0], tuple) else full_data[0]
            if not msg_bytes:
                uid_logger.warning("message_body_empty")
                return "skipped"
            msg = message_from_bytes(msg_bytes)
        except Exception as e:
            uid_logger.error("message_parse_error", error=str(e))
            return "error"
        
        # Process attachments
        attachments_found = False
        attachment_errors = []
        try:
            for part in msg.walk():
                if part.get_content_disposition() == "attachment":
                    if self.attachment_handler.save_attachment(part, target_folder, uid, dry_run):
                        attachments_found = True
                    else:
                        attachment_errors.append(f"Failed to save attachment")
        except Exception as e:
            uid_logger.error("message_walk_error", error=str(e), exc_info=True)
            return "error"
        
        # Save processed UID
        try:
            save_processed_uid_for_day(self.processed_dir, day_str, uid, processed_cache)
        except Exception as e:
            uid_logger.error("processed_uid_save_error", error=str(e))
            return "error"
        
        # Archive
        if mapped_folder and self.archive_only_mapped:
            if dry_run:
                uid_logger.info("dry_run_archive", archive_folder=self.archive_folder)
            else:
                try:
                    archive_message(mail, uid, self.archive_folder)
                except Exception as e:
                    uid_logger.error("archive_error", error=str(e))
        
        if attachments_found:
            return "processed"
        elif attachment_errors:
            return "error"
        else:
            uid_logger.debug("no_attachments")
            return "skipped"
