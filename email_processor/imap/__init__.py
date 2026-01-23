"""IMAP module for email processor."""

from email_processor.imap.archive import ArchiveManager, archive_message
from email_processor.imap.attachments import AttachmentHandler
from email_processor.imap.auth import IMAPAuth, clear_passwords, get_imap_password
from email_processor.imap.client import IMAPClient
from email_processor.imap.fetcher import Fetcher, ProcessingMetrics, ProcessingResult
from email_processor.imap.filters import EmailFilter

__all__ = [
    "ArchiveManager",
    "AttachmentHandler",
    "EmailFilter",
    "Fetcher",
    "IMAPAuth",
    "IMAPClient",
    "ProcessingMetrics",
    "ProcessingResult",
    "archive_message",
    "clear_passwords",
    "get_imap_password",
]
