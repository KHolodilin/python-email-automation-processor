"""Base test class for Fetcher tests with common setup."""

import shutil
import tempfile
import unittest
from pathlib import Path

from email_processor.imap.fetcher import Fetcher
from email_processor.logging.setup import setup_logging

# Backward compatibility alias
EmailProcessor = Fetcher


class TestFetcherBase(unittest.TestCase):
    """Base test class for Fetcher tests with common setup."""

    def setUp(self):
        """Setup test fixtures."""
        setup_logging({"level": "INFO", "format": "console"})
        self.temp_dir = tempfile.mkdtemp()

        self.config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
                "max_retries": 3,
                "retry_delay": 1,
            },
            "processing": {
                "start_days_back": 5,
                "archive_folder": "INBOX/Processed",
                "processed_dir": str(Path(self.temp_dir) / "processed_uids"),
                "keep_processed_days": 0,
                "archive_only_mapped": True,
                "skip_non_allowed_as_processed": True,
                "skip_unmapped_as_processed": True,
            },
            "logging": {
                "level": "INFO",
                "format": "console",
            },
            "allowed_senders": ["sender@example.com"],
            "topic_mapping": {
                ".*invoice.*": str(Path(self.temp_dir) / "downloads" / "invoices"),
                ".*": str(Path(self.temp_dir) / "downloads" / "default"),
            },
        }
        self.processor = EmailProcessor(self.config)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
