"""Tests for sent files storage module."""

import logging
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from email_processor.logging.setup import setup_logging
from email_processor.storage.sent_files_storage import (
    SentFilesStorage,
    cleanup_old_sent_files,
    ensure_sent_files_dir,
    get_file_hash,
    get_sent_files_path,
    load_sent_hashes_for_day,
    save_sent_hash_for_day,
)


class TestSentFilesStorage(unittest.TestCase):
    """Tests for sent files storage functions."""

    def setUp(self):
        """Set up test fixtures."""
        # Close any file handlers from previous tests
        for handler in logging.root.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                try:
                    handler.close()
                except Exception:
                    pass
                logging.root.removeHandler(handler)
        setup_logging({"level": "INFO", "format": "console"})
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_ensure_sent_files_dir(self):
        """Test sent files directory creation."""
        test_dir = os.path.join(self.temp_dir, "sent_files")
        ensure_sent_files_dir(test_dir)
        self.assertTrue(os.path.exists(test_dir))
        self.assertTrue(os.path.isdir(test_dir))

    def test_get_sent_files_path(self):
        """Test getting sent files path for a day."""
        day_str = "2024-01-15"
        path = get_sent_files_path(self.temp_dir, day_str)
        expected = Path(self.temp_dir) / "2024-01-15.txt"
        self.assertEqual(path, expected)
        self.assertTrue(path.parent.exists())

    def test_get_file_hash(self):
        """Test file hash calculation."""
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("test content", encoding="utf-8")

        hash_value = get_file_hash(test_file)

        # Verify it's a valid SHA256 hash (64 hex characters)
        self.assertEqual(len(hash_value), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in hash_value))

        # Verify hash is consistent
        hash_value2 = get_file_hash(test_file)
        self.assertEqual(hash_value, hash_value2)

        # Verify hash changes with content
        test_file.write_text("different content", encoding="utf-8")
        hash_value3 = get_file_hash(test_file)
        self.assertNotEqual(hash_value, hash_value3)

    def test_load_sent_hashes_for_day_empty(self):
        """Test loading sent hashes for day when file doesn't exist."""
        cache = {}
        hashes = load_sent_hashes_for_day(self.temp_dir, "2024-01-15", cache)
        self.assertEqual(hashes, set())
        self.assertEqual(cache["2024-01-15"], set())

    def test_save_and_load_sent_hash(self):
        """Test saving and loading sent hash."""
        day_str = "2024-01-15"
        cache = {}
        test_hash = "a" * 64

        save_sent_hash_for_day(self.temp_dir, day_str, test_hash, cache)
        hashes = load_sent_hashes_for_day(self.temp_dir, day_str, cache)

        self.assertIn(test_hash, hashes)
        self.assertIn(test_hash, cache[day_str])

    def test_save_sent_hash_duplicate(self):
        """Test saving duplicate hash doesn't create duplicates."""
        day_str = "2024-01-15"
        cache = {}
        test_hash = "a" * 64

        save_sent_hash_for_day(self.temp_dir, day_str, test_hash, cache)
        save_sent_hash_for_day(self.temp_dir, day_str, test_hash, cache)

        path = get_sent_files_path(self.temp_dir, day_str)
        with path.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], test_hash)

    def test_sent_files_storage_class(self):
        """Test SentFilesStorage class."""
        storage = SentFilesStorage(self.temp_dir)
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("test content", encoding="utf-8")
        day_str = "2024-01-15"

        # Test hash calculation
        hash_value = storage.get_file_hash(test_file)
        self.assertEqual(len(hash_value), 64)

        # Test is_sent (should be False initially)
        self.assertFalse(storage.is_sent(test_file, day_str))

        # Test mark_as_sent
        storage.mark_as_sent(test_file, day_str)

        # Test is_sent (should be True now)
        self.assertTrue(storage.is_sent(test_file, day_str))

    def test_sent_files_storage_same_content_different_name(self):
        """Test that files with same content but different names are recognized as sent."""
        storage = SentFilesStorage(self.temp_dir)
        test_file1 = Path(self.temp_dir) / "file1.txt"
        test_file2 = Path(self.temp_dir) / "file2.txt"
        content = "same content"
        test_file1.write_text(content, encoding="utf-8")
        test_file2.write_text(content, encoding="utf-8")
        day_str = "2024-01-15"

        # Mark first file as sent
        storage.mark_as_sent(test_file1, day_str)

        # Second file with same content should be recognized as sent
        self.assertTrue(storage.is_sent(test_file2, day_str))

    def test_cleanup_old_sent_files(self):
        """Test cleanup of old sent files."""
        # Create old file
        old_date = (datetime.now() - timedelta(days=200)).strftime("%Y-%m-%d")
        old_path = get_sent_files_path(self.temp_dir, old_date)
        old_path.write_text("old_hash\n", encoding="utf-8")

        # Create recent file
        recent_date = datetime.now().strftime("%Y-%m-%d")
        recent_path = get_sent_files_path(self.temp_dir, recent_date)
        recent_path.write_text("recent_hash\n", encoding="utf-8")

        cleanup_old_sent_files(self.temp_dir, keep_days=180)

        # Old file should be deleted
        self.assertFalse(old_path.exists())
        # Recent file should still exist
        self.assertTrue(recent_path.exists())

    def test_cleanup_old_sent_files_zero_days(self):
        """Test cleanup with zero keep_days doesn't delete anything."""
        day_str = datetime.now().strftime("%Y-%m-%d")
        path = get_sent_files_path(self.temp_dir, day_str)
        path.write_text("hash\n", encoding="utf-8")

        cleanup_old_sent_files(self.temp_dir, keep_days=0)

        # File should still exist
        self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
