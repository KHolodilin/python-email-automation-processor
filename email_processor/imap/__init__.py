"""IMAP module for email processor."""

from email_processor.imap.archive import ArchiveManager, archive_message
from email_processor.imap.auth import IMAPAuth, clear_passwords, get_imap_password
from email_processor.imap.client import IMAPClient

__all__ = [
    "ArchiveManager",
    "IMAPAuth",
    "IMAPClient",
    "archive_message",
    "clear_passwords",
    "get_imap_password",
]
