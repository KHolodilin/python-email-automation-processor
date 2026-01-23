"""
Email Processor Package

Main package for email attachment processing with IMAP support.
"""

# Export main classes and functions for backward compatibility
# Import version
from email_processor.__version__ import __version__
from email_processor.config.constants import CONFIG_FILE, KEYRING_SERVICE_NAME, MAX_ATTACHMENT_SIZE
from email_processor.config.loader import ConfigLoader, load_config, validate_config
from email_processor.imap.archive import archive_message
from email_processor.imap.auth import IMAPAuth, clear_passwords, get_imap_password
from email_processor.imap.client import imap_connect
from email_processor.imap.fetcher import Fetcher
from email_processor.logging.setup import get_logger, setup_logging
from email_processor.utils.context import (
    clear_context,
    generate_correlation_id,
    generate_request_id,
    get_context_dict,
    get_correlation_id,
    get_request_id,
    set_correlation_id,
    set_request_id,
)

# Backward compatibility alias
EmailProcessor = Fetcher


# Legacy function wrapper for backward compatibility
def download_attachments(config, dry_run=False):
    """Legacy function wrapper for backward compatibility.

    Returns:
        ProcessingResult from processor.process()
    """
    processor = Fetcher(config)
    return processor.process(dry_run=dry_run)


__all__ = [
    "CONFIG_FILE",
    "KEYRING_SERVICE_NAME",
    "MAX_ATTACHMENT_SIZE",
    "ConfigLoader",
    "EmailProcessor",
    "IMAPAuth",
    "__version__",
    "archive_message",
    "clear_context",
    "clear_passwords",
    "download_attachments",  # Legacy
    "generate_correlation_id",
    "generate_request_id",
    "get_context_dict",
    "get_correlation_id",
    "get_imap_password",
    "get_logger",
    "get_request_id",
    "imap_connect",
    "load_config",
    "set_correlation_id",
    "set_request_id",
    "setup_logging",
    "validate_config",
]
