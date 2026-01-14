"""Tests for folder resolver module."""

import unittest
from unittest.mock import MagicMock, patch

from email_processor.logging.setup import setup_logging
from email_processor.utils.folder_resolver import (
    FolderResolver,
    resolve_custom_folder,
)


class TestFolderResolver(unittest.TestCase):
    """Tests for folder resolver functions."""

    def setUp(self):
        """Setup logging."""
        setup_logging({"level": "INFO", "format": "console"})

    def test_resolve_custom_folder(self):
        """Test custom folder resolution."""
        topic_mapping = {
            ".*invoice.*": "invoices",
            ".*report.*": "reports",
            ".*": "default",  # Last rule is used as default
        }
        # Matching pattern
        result = resolve_custom_folder("Invoice #123", topic_mapping)
        self.assertEqual(result, "invoices")
        # Non-matching - uses last rule as default
        result = resolve_custom_folder("Random subject", topic_mapping)
        self.assertEqual(result, "default")

    def test_resolve_custom_folder_empty_mapping(self):
        """Test custom folder resolution with empty mapping raises ValueError."""
        with self.assertRaises(ValueError):
            resolve_custom_folder("Test subject", {})

    def test_resolve_custom_folder_with_logging(self):
        """Test custom folder resolution logs match."""
        topic_mapping = {
            ".*invoice.*": "invoices",
            ".*": "default",
        }
        # Setup logging for structlog
        setup_logging({"level": "INFO", "format": "console"})
        # Patch get_logger in the module where it's used
        with patch("email_processor.utils.folder_resolver.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            result = resolve_custom_folder("Invoice #123", topic_mapping)
            self.assertEqual(result, "invoices")
            # Verify logger was called (either info for match or debug for default)
            mock_logger.info.assert_called()
            call_args = mock_logger.info.call_args
            self.assertIn("subject_matched", str(call_args))

    def test_resolve_custom_folder_regex_caching(self):
        """Test that regex patterns are cached for performance."""
        topic_mapping = {
            ".*test.*": "test_folder",
        }
        # First call
        result1 = resolve_custom_folder("Test Subject", topic_mapping)
        # Second call with same pattern should use cached regex
        result2 = resolve_custom_folder("Another Test", topic_mapping)
        self.assertEqual(result1, "test_folder")
        self.assertEqual(result2, "test_folder")

    def test_folder_resolver_class(self):
        """Test FolderResolver class."""
        topic_mapping = {
            ".*invoice.*": "invoices",
            ".*": "default",  # Last rule is used as default
        }
        resolver = FolderResolver(topic_mapping)
        result = resolver.resolve("Invoice #123")
        self.assertEqual(result, "invoices")

        result = resolver.resolve("Random subject")
        self.assertEqual(result, "default")  # Uses last rule as default

    def test_folder_resolver_compile_pattern(self):
        """Test FolderResolver._compile_pattern method."""
        topic_mapping = {
            ".*test.*": "test_folder",
        }
        resolver = FolderResolver(topic_mapping)
        pattern = resolver._compile_pattern(".*test.*")
        self.assertIsNotNone(pattern)
        self.assertTrue(pattern.search("Test Subject"))
