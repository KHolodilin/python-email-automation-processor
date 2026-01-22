"""Tests for email filters module."""

import unittest

from email_processor.imap.filters import EmailFilter
from email_processor.logging.setup import setup_logging


class TestEmailFilter(unittest.TestCase):
    """Tests for EmailFilter class."""

    def setUp(self):
        """Setup logging."""
        setup_logging({"level": "INFO", "format": "console"})

    def test_is_allowed_sender(self):
        """Test EmailFilter.is_allowed_sender method."""
        allowed_senders = ["sender1@example.com", "Sender2@Example.com"]
        topic_mapping = {".*": "default"}  # Required: at least one rule
        filter_obj = EmailFilter(allowed_senders, topic_mapping)

        self.assertTrue(filter_obj.is_allowed_sender("sender1@example.com"))
        self.assertTrue(filter_obj.is_allowed_sender("SENDER1@EXAMPLE.COM"))  # Case insensitive
        self.assertFalse(filter_obj.is_allowed_sender("other@example.com"))

    def test_resolve_folder(self):
        """Test EmailFilter.resolve_folder method."""
        allowed_senders = []
        topic_mapping = {
            ".*invoice.*": "invoices",
            ".*report.*": "reports",
            ".*": "default",  # Last rule is used as default
        }
        filter_obj = EmailFilter(allowed_senders, topic_mapping)

        result = filter_obj.resolve_folder("Invoice #123")
        self.assertEqual(result, "invoices")

        result = filter_obj.resolve_folder("Random subject")
        self.assertEqual(result, "default")  # Uses last rule as default

    def test_resolve_folder_empty_mapping(self):
        """Test EmailFilter.resolve_folder with empty mapping raises ValueError."""
        filter_obj = EmailFilter([], {})
        with self.assertRaises(ValueError):
            filter_obj.resolve_folder("Test subject")
