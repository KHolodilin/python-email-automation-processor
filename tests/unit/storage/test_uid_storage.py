"""Tests for UID storage module."""

import logging
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from email_processor.logging.setup import setup_logging
from email_processor.storage.uid_storage import (
    UIDStorage,
    cleanup_old_processed_days,
    ensure_processed_dir,
    get_processed_file_path,
    load_processed_for_day,
    save_processed_uid_for_day,
)


class TestUIDStorage(unittest.TestCase):
    """Tests for UID storage functions."""

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

    def test_ensure_processed_dir(self):
        """Test processed directory creation."""
        test_dir = os.path.join(self.temp_dir, "processed")
        ensure_processed_dir(test_dir)
        self.assertTrue(os.path.exists(test_dir))
        self.assertTrue(os.path.isdir(test_dir))

    def test_get_processed_file_path(self):
        """Test processed file path generation."""
        day_str = "2024-01-01"
        path = get_processed_file_path(self.temp_dir, day_str)
        expected = Path(self.temp_dir) / "2024-01-01.txt"
        self.assertEqual(path, expected)
        # Directory should be created
        self.assertTrue(Path(self.temp_dir).exists())

    @patch("email_processor.storage.uid_storage.validate_path")
    def test_get_processed_file_path_invalid(self, mock_validate):
        """Test get_processed_file_path raises error when path traversal detected."""
        mock_validate.return_value = False
        with self.assertRaises(ValueError) as context:
            get_processed_file_path(self.temp_dir, "2024-01-01")
        self.assertIn("Invalid path detected", str(context.exception))

    def test_load_processed_for_day_empty(self):
        """Test loading processed UIDs for day with no file."""
        cache = {}
        result = load_processed_for_day(self.temp_dir, "2024-01-01", cache)
        self.assertEqual(result, set())
        self.assertIn("2024-01-01", cache)

    def test_load_processed_for_day_existing(self):
        """Test loading processed UIDs from existing file."""
        day_str = "2024-01-01"
        path = get_processed_file_path(self.temp_dir, day_str)
        path.write_text("123\n456\n789\n")

        cache = {}
        result = load_processed_for_day(self.temp_dir, day_str, cache)
        self.assertEqual(result, {"123", "456", "789"})
        # Test cache
        result2 = load_processed_for_day(self.temp_dir, day_str, cache)
        self.assertEqual(result2, result)

    def test_load_processed_for_day_io_error(self):
        """Test loading processed UIDs with IO error."""
        day_str = "2024-01-01"
        path = get_processed_file_path(self.temp_dir, day_str)
        path.write_text("123\n")

        cache = {}

        # Create a mock that raises IOError when opening the specific path
        def mock_open(self, *args, **kwargs):
            if str(self) == str(path):
                raise OSError("Permission denied")
            # For other paths, use real open
            return Path.open(self, *args, **kwargs)

        with patch.object(Path, "open", mock_open):
            result = load_processed_for_day(self.temp_dir, day_str, cache)
            self.assertEqual(result, set())
            self.assertIn(day_str, cache)

    def test_load_processed_for_day_unexpected_error(self):
        """Test loading processed UIDs with unexpected error."""
        day_str = "2024-01-01"
        path = get_processed_file_path(self.temp_dir, day_str)
        path.write_text("123\n")

        cache = {}

        # Create a mock that raises Exception when opening the specific path
        def mock_open(self, *args, **kwargs):
            if str(self) == str(path):
                raise Exception("Unexpected error")
            # For other paths, use real open
            return Path.open(self, *args, **kwargs)

        with patch.object(Path, "open", mock_open):
            result = load_processed_for_day(self.temp_dir, day_str, cache)
            self.assertEqual(result, set())
            self.assertIn(day_str, cache)

    def test_save_processed_uid_for_day(self):
        """Test saving processed UID."""
        day_str = "2024-01-01"
        cache = {}
        save_processed_uid_for_day(self.temp_dir, day_str, "123", cache)

        path = get_processed_file_path(self.temp_dir, day_str)
        self.assertTrue(path.exists())
        content = path.read_text()
        self.assertIn("123", content)

        # Should not duplicate
        save_processed_uid_for_day(self.temp_dir, day_str, "123", cache)
        lines = path.read_text().splitlines()
        self.assertEqual(len([l for l in lines if l.strip() == "123"]), 1)

    def test_save_processed_uid_for_day_io_error(self):
        """Test saving processed UID with IO error."""
        day_str = "2024-01-01"
        cache = {}
        path = get_processed_file_path(self.temp_dir, day_str)

        # Create a mock that raises IOError when opening in append mode
        def mock_open(self, mode="r", *args, **kwargs):
            if mode == "a" and str(self) == str(path):
                raise OSError("Permission denied")
            # For other cases, use real open
            return Path.open(self, mode, *args, **kwargs)

        with patch.object(Path, "open", mock_open), self.assertRaises(IOError):
            save_processed_uid_for_day(self.temp_dir, day_str, "123", cache)

    def test_save_processed_uid_for_day_unexpected_error(self):
        """Test saving processed UID with unexpected error."""
        day_str = "2024-01-01"
        cache = {}
        path = get_processed_file_path(self.temp_dir, day_str)

        # Create a mock that raises Exception when opening in append mode
        def mock_open(self, mode="r", *args, **kwargs):
            if mode == "a" and str(self) == str(path):
                raise Exception("Unexpected error")
            # For other cases, use real open
            return Path.open(self, mode, *args, **kwargs)

        with patch.object(Path, "open", mock_open), self.assertRaises(Exception):
            save_processed_uid_for_day(self.temp_dir, day_str, "123", cache)

    def test_cleanup_old_processed_days(self):
        """Test cleanup of old processed UID files."""
        # Create old file
        old_date = (datetime.now() - timedelta(days=200)).strftime("%Y-%m-%d")
        old_path = get_processed_file_path(self.temp_dir, old_date)
        old_path.write_text("123\n")

        # Create recent file
        recent_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        recent_path = get_processed_file_path(self.temp_dir, recent_date)
        recent_path.write_text("456\n")

        # Cleanup with keep_days=180
        cleanup_old_processed_days(self.temp_dir, 180)

        # Old file should be deleted
        self.assertFalse(old_path.exists())
        # Recent file should remain
        self.assertTrue(recent_path.exists())

    def test_cleanup_keep_forever(self):
        """Test cleanup with keep_days=0 (keep forever)."""
        old_date = (datetime.now() - timedelta(days=200)).strftime("%Y-%m-%d")
        old_path = get_processed_file_path(self.temp_dir, old_date)
        old_path.write_text("123\n")

        cleanup_old_processed_days(self.temp_dir, 0)

        # File should remain
        self.assertTrue(old_path.exists())

    def test_cleanup_old_processed_days_skips_non_txt(self):
        """Test cleanup skips non-.txt files."""
        # Create a non-.txt file
        other_file = Path(self.temp_dir) / "2024-01-01.dat"
        other_file.write_text("data")

        cleanup_old_processed_days(self.temp_dir, 1)

        # Non-.txt file should remain
        self.assertTrue(other_file.exists())

    def test_cleanup_old_processed_days_skips_invalid_date(self):
        """Test cleanup skips files with invalid date format."""
        invalid_file = Path(self.temp_dir) / "invalid-date.txt"
        invalid_file.write_text("123\n")

        cleanup_old_processed_days(self.temp_dir, 1)

        # Invalid date file should remain
        self.assertTrue(invalid_file.exists())

    def test_cleanup_old_processed_days_skips_directories(self):
        """Test cleanup skips directories."""
        # Create a directory with date-like name
        dir_path = Path(self.temp_dir) / "2024-01-01.txt"
        dir_path.mkdir(parents=True, exist_ok=True)

        cleanup_old_processed_days(self.temp_dir, 1)

        # Directory should remain
        self.assertTrue(dir_path.exists())
        self.assertTrue(dir_path.is_dir())

    def test_cleanup_old_processed_days_handles_delete_error(self):
        """Test cleanup handles errors during file deletion."""
        old_date = (datetime.now() - timedelta(days=200)).strftime("%Y-%m-%d")
        old_path = get_processed_file_path(self.temp_dir, old_date)
        old_path.write_text("123\n")

        with patch.object(Path, "unlink", side_effect=Exception("Permission denied")):
            # Should not raise, just log error
            cleanup_old_processed_days(self.temp_dir, 180)

        # File should still exist due to error
        self.assertTrue(old_path.exists())

    @patch("email_processor.storage.uid_storage.validate_path")
    def test_cleanup_old_processed_days_invalid_path(self, mock_validate):
        """Test cleanup skips files with invalid paths."""
        # Create a file
        test_file = Path(self.temp_dir) / "2024-01-01.txt"
        test_file.write_text("123\n")

        # Mock validate_path to return False for this file
        def validate_side_effect(base, target):
            return str(target) != str(test_file)

        mock_validate.side_effect = validate_side_effect

        # Should not raise, should skip the file
        cleanup_old_processed_days(self.temp_dir, 1)

        # File should still exist (skipped due to invalid path)
        self.assertTrue(test_file.exists())


class TestUIDStorageClass(unittest.TestCase):
    """Tests for UIDStorage class."""

    def setUp(self):
        """Set up test fixtures."""
        setup_logging({"level": "INFO", "format": "console"})
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_uid_storage_load_for_day(self):
        """Test UIDStorage.load_for_day method."""
        storage = UIDStorage(self.temp_dir)
        result = storage.load_for_day("2024-01-01")
        self.assertEqual(result, set())

        # Save a UID and load again
        storage.save_uid("2024-01-01", "123")
        result = storage.load_for_day("2024-01-01")
        self.assertIn("123", result)

    def test_uid_storage_save_uid(self):
        """Test UIDStorage.save_uid method."""
        storage = UIDStorage(self.temp_dir)
        storage.save_uid("2024-01-01", "123")

        path = Path(self.temp_dir) / "2024-01-01.txt"
        self.assertTrue(path.exists())
        self.assertIn("123", path.read_text())

    def test_uid_storage_is_processed(self):
        """Test UIDStorage.is_processed method."""
        storage = UIDStorage(self.temp_dir)
        self.assertFalse(storage.is_processed("2024-01-01", "123"))

        storage.save_uid("2024-01-01", "123")
        self.assertTrue(storage.is_processed("2024-01-01", "123"))

    def test_uid_storage_cleanup_old(self):
        """Test UIDStorage.cleanup_old method."""
        storage = UIDStorage(self.temp_dir)

        # Create old file
        old_date = (datetime.now() - timedelta(days=200)).strftime("%Y-%m-%d")
        old_path = Path(self.temp_dir) / f"{old_date}.txt"
        old_path.write_text("123\n")

        storage.cleanup_old(180)
        self.assertFalse(old_path.exists())
