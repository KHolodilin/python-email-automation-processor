"""Tests for path utils module."""

import os
import unittest

from email_processor.utils.path_utils import (
    PathUtils,
    normalize_folder_name,
    sanitize_filename,
)


class TestPathUtils(unittest.TestCase):
    """Tests for path utility functions."""

    def test_normalize_folder_name(self):
        """Test folder name normalization."""
        self.assertEqual(normalize_folder_name("test"), "test")
        self.assertEqual(normalize_folder_name("test/folder"), "test_folder")
        self.assertEqual(normalize_folder_name("test:folder"), "test_folder")
        self.assertEqual(normalize_folder_name("  test  "), "test")
        # Test long name truncation
        long_name = "a" * 300
        result = normalize_folder_name(long_name)
        self.assertEqual(len(result), 200)

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        self.assertEqual(sanitize_filename("test.pdf"), "test.pdf")
        self.assertEqual(sanitize_filename("../test.pdf"), "test.pdf")
        if os.name == "nt":
            self.assertEqual(sanitize_filename("..\\test.pdf"), "test.pdf")

    def test_path_utils_normalize_folder_name(self):
        """Test PathUtils.normalize_folder_name method."""
        result = PathUtils.normalize_folder_name("test/folder")
        self.assertEqual(result, "test_folder")

    def test_path_utils_sanitize_filename(self):
        """Test PathUtils.sanitize_filename method."""
        result = PathUtils.sanitize_filename("../test.pdf")
        self.assertEqual(result, "test.pdf")
