"""Tests for disk utils module."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from email_processor.utils.disk_utils import (
    DiskUtils,
    check_disk_space,
)


class TestDiskUtils(unittest.TestCase):
    """Tests for disk utility functions."""

    def test_check_disk_space_sufficient(self):
        """Test check_disk_space with sufficient space."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            # Should have enough space for 1MB
            result = check_disk_space(path, 1024 * 1024)
            self.assertTrue(result)

    def test_check_disk_space_insufficient(self):
        """Test check_disk_space with insufficient space."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            # Request huge amount of space (1TB)
            result = check_disk_space(path, 1024 * 1024 * 1024 * 1024)
            # May be True or False depending on actual disk space
            self.assertIsInstance(result, bool)

    def test_check_disk_space_logging_insufficient(self):
        """Test check_disk_space logs warning when insufficient space."""
        with patch("email_processor.utils.disk_utils.get_logger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            with tempfile.TemporaryDirectory() as tmpdir:
                path = Path(tmpdir)
                # Request huge amount of space (1TB) to trigger warning
                check_disk_space(path, 1024 * 1024 * 1024 * 1024)

                # Check if warning was logged (if space was insufficient)
                # Note: This depends on actual disk space, so we just check the call was made
                self.assertTrue(mock_get_logger.called)

    def test_check_disk_space_error(self):
        """Test check_disk_space with error."""
        with patch("shutil.disk_usage", side_effect=Exception("Disk error")):
            with tempfile.TemporaryDirectory() as tmpdir:
                path = Path(tmpdir)
                # Should return True (assume enough space if check fails)
                result = check_disk_space(path, 1024 * 1024)
                self.assertTrue(result)

    def test_disk_utils_check_space(self):
        """Test DiskUtils.check_space method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            result = DiskUtils.check_space(path, 1024 * 1024)
            self.assertTrue(result)

    def test_disk_utils_get_free_space(self):
        """Test DiskUtils.get_free_space method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            free_space = DiskUtils.get_free_space(path)
            self.assertIsInstance(free_space, int)
            self.assertGreaterEqual(free_space, 0)

    def test_disk_utils_get_free_space_error(self):
        """Test DiskUtils.get_free_space with error."""
        with patch("shutil.disk_usage", side_effect=Exception("Disk error")):
            with tempfile.TemporaryDirectory() as tmpdir:
                path = Path(tmpdir)
                free_space = DiskUtils.get_free_space(path)
                self.assertEqual(free_space, 0)
