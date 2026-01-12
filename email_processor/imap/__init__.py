"""IMAP module for email processor."""

from email_processor.imap.client import IMAPClient
from email_processor.imap.auth import IMAPAuth, get_imap_password, clear_passwords
from email_processor.imap.archive import ArchiveManager, archive_message

__all__ = [
    "IMAPClient",
    "IMAPAuth",
    "get_imap_password",
    "clear_passwords",
    "ArchiveManager",
    "archive_message",
]
