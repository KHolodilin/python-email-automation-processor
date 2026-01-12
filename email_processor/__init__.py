"""
Email Processor Package

Main package for email attachment processing with IMAP support.
"""

__version__ = "7.1.0"

# Export main classes and functions for backward compatibility
from email_processor.processor.email_processor import EmailProcessor
from email_processor.config.loader import ConfigLoader, load_config, validate_config
from email_processor.imap.auth import IMAPAuth, get_imap_password, clear_passwords
from email_processor.imap.client import imap_connect
from email_processor.imap.archive import archive_message
from email_processor.logging.setup import setup_logging, get_logger
from email_processor.config.constants import KEYRING_SERVICE_NAME, CONFIG_FILE, MAX_ATTACHMENT_SIZE

# Import version
from email_processor.__version__ import __version__

# Legacy function wrapper for backward compatibility
def download_attachments(config, dry_run=False):
    """Legacy function wrapper for backward compatibility."""
    processor = EmailProcessor(config)
    processor.process(dry_run=dry_run)

__all__ = [
    "EmailProcessor",
    "ConfigLoader",
    "load_config",
    "validate_config",
    "IMAPAuth",
    "get_imap_password",
    "clear_passwords",
    "imap_connect",
    "archive_message",
    "setup_logging",
    "get_logger",
    "KEYRING_SERVICE_NAME",
    "CONFIG_FILE",
    "MAX_ATTACHMENT_SIZE",
    "download_attachments",  # Legacy
    "__version__",
]
