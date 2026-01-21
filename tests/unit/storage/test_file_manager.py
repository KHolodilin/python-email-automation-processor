"""Tests for file manager module."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from email_processor.logging.setup import setup_logging
from email_processor.storage.file_manager import (
    FileManager,
    safe_save_path,
    validate_path,
)


class TestFileManager(unittest.TestCase):
    """Tests for file manager functions."""

    def setUp(self):
        """Setup logging."""
        setup_logging({"level": "INFO", "format": "console"})

    def test_validate_path_valid(self):
        """Test validate_path with valid paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir) / "base"
            base_path.mkdir()
            target_path = base_path / "file.txt"
            self.assertTrue(validate_path(base_path, target_path))

    def test_validate_path_invalid(self):
        """Test validate_path with invalid paths (path traversal)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir) / "base"
            base_path.mkdir()
            # Try to access parent directory
            target_path = Path(tmpdir) / ".." / "file.txt"
            self.assertFalse(validate_path(base_path, target_path))

            # Try to access completely different directory
            other_path = Path(tmpdir) / "other" / "file.txt"
            self.assertFalse(validate_path(base_path, other_path))

    def test_validate_path_absolute_paths(self):
        """Test validate_path works with absolute paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir).resolve() / "downloads"
            base.mkdir(parents=True, exist_ok=True)

            # Valid absolute paths within base
            valid1 = base / "subdir" / "file.txt"
            self.assertTrue(validate_path(base, valid1))

            valid2 = base / "file.txt"
            self.assertTrue(validate_path(base, valid2))

            # Invalid: path outside base
            invalid1 = Path(tmpdir).resolve() / "other" / "file.txt"
            self.assertFalse(validate_path(base, invalid1))

    def test_safe_save_path(self):
        """Test safe save path generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_resolved = Path(tmpdir).resolve()
            # First file
            path1 = safe_save_path(tmpdir, "test.pdf")
            # Use resolve() for comparison to handle symlinks (e.g., /var -> /private/var on macOS)
            self.assertEqual(path1.resolve(), tmpdir_resolved / "test.pdf")
            # Create the file
            path1.write_text("test")
            # Second file with same name should get numbered
            path2 = safe_save_path(tmpdir, "test.pdf")
            self.assertEqual(path2.resolve(), tmpdir_resolved / "test_01.pdf")

    def test_safe_save_path_absolute_path(self):
        """Test safe_save_path works with absolute paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            abs_path = Path(tmpdir).resolve() / "downloads"
            abs_path.mkdir()

            # Should work with absolute path
            path1 = safe_save_path(str(abs_path), "test.pdf")
            # Use resolve() for comparison to handle symlinks (e.g., /var -> /private/var on macOS)
            self.assertEqual(path1.parent.resolve(), abs_path.resolve())
            self.assertEqual(path1.name, "test.pdf")

            # Create file and test duplicate handling
            path1.write_text("test")
            path2 = safe_save_path(str(abs_path), "test.pdf")
            self.assertEqual(path2.name, "test_01.pdf")

    def test_safe_save_path_filename_sanitization(self):
        """Test safe_save_path sanitizes filenames with path separators."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_resolved = Path(tmpdir).resolve()
            # Filename with path separators should be sanitized
            path1 = safe_save_path(tmpdir, "../test.pdf")
            self.assertEqual(path1.name, "test.pdf")
            # Use resolve() for comparison to handle symlinks (e.g., /var -> /private/var on macOS)
            self.assertEqual(path1.parent.resolve(), tmpdir_resolved)

            # Filename with backslashes (Windows)
            if os.name == "nt":
                path2 = safe_save_path(tmpdir, "..\\test.pdf")
                self.assertEqual(path2.name, "test.pdf")
                self.assertEqual(path2.parent.resolve(), tmpdir_resolved)

    def test_file_manager_safe_save_path(self):
        """Test FileManager.safe_save_path method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            path = FileManager.safe_save_path(folder, "test.pdf")
            self.assertEqual(path.name, "test.pdf")

    def test_file_manager_validate_path(self):
        """Test FileManager.validate_path method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "base"
            base.mkdir()
            target = base / "file.txt"
            self.assertTrue(FileManager.validate_path(base, target))

    def test_file_manager_ensure_directory(self):
        """Test FileManager.ensure_directory method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            new_dir = Path(tmpdir) / "new" / "nested" / "dir"
            FileManager.ensure_directory(new_dir)
            self.assertTrue(new_dir.exists())
            self.assertTrue(new_dir.is_dir())

    @patch("email_processor.storage.file_manager.validate_path")
    def test_safe_save_path_path_traversal_detected(self, mock_validate):
        """Test safe_save_path raises error when path traversal is detected."""
        mock_validate.return_value = False
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(ValueError) as context:
                safe_save_path(tmpdir, "test.pdf")
            self.assertIn("Invalid path detected", str(context.exception))
            self.assertIn("path traversal", str(context.exception))
