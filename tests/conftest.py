"""Pytest configuration and fixtures."""

import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_config():
    """Sample configuration for tests."""
    return {
        "imap": {
            "server": "imap.example.com",
            "user": "test@example.com",
            "max_retries": 3,
            "retry_delay": 1,
        },
        "processing": {
            "start_days_back": 5,
            "download_dir": "downloads",
            "archive_folder": "INBOX/Processed",
            "processed_dir": "processed_uids",
            "keep_processed_days": 0,
            "archive_only_mapped": True,
            "skip_non_allowed_as_processed": True,
            "skip_unmapped_as_processed": True,
        },
        "logging": {
            "level": "INFO",
            "format": "console",
            "format_file": "json",
        },
        "allowed_senders": ["sender@example.com"],
        "topic_mapping": {
            ".*invoice.*": "invoices",
        },
    }
