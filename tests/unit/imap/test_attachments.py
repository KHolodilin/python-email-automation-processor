"""Tests for attachment handler module."""

import email.message
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from email_processor.config.constants import MAX_ATTACHMENT_SIZE
from email_processor.imap.attachments import AttachmentHandler
from email_processor.logging.setup import setup_logging


class TestAttachmentHandler(unittest.TestCase):
    """Tests for AttachmentHandler class."""

    def setUp(self):
        """Setup logging."""
        setup_logging({"level": "INFO", "format": "console"})
        self.temp_dir = tempfile.mkdtemp()
        self.download_dir = Path(self.temp_dir)

    def tearDown(self):
        """Clean up."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_size(self):
        """Test AttachmentHandler.validate_size method."""
        handler = AttachmentHandler()

        self.assertTrue(handler.validate_size(1024))
        self.assertTrue(handler.validate_size(MAX_ATTACHMENT_SIZE))
        self.assertFalse(handler.validate_size(MAX_ATTACHMENT_SIZE + 1))

    def test_save_attachment_success(self):
        """Test successful attachment saving."""
        handler = AttachmentHandler()
        target_folder = self.download_dir / "test_folder"
        target_folder.mkdir()

        # Create mock email part
        part = email.message.Message()
        part.set_payload(b"test content")
        part.add_header("Content-Disposition", "attachment", filename="test.pdf")

        result = handler.save_attachment(part, target_folder, "123", dry_run=False)
        self.assertTrue(result[0])
        # File size should match payload size (b"test content" = 12 bytes)
        self.assertEqual(result[1], 12)

        # Check file was created
        saved_file = list(target_folder.glob("test*.pdf"))[0]
        self.assertTrue(saved_file.exists())

    def test_save_attachment_dry_run(self):
        """Test attachment saving in dry-run mode."""
        handler = AttachmentHandler()
        target_folder = self.download_dir / "test_folder"
        target_folder.mkdir()

        part = email.message.Message()
        part.set_payload(b"test content")
        part.add_header("Content-Disposition", "attachment", filename="test.pdf")

        result = handler.save_attachment(part, target_folder, "123", dry_run=True)
        self.assertTrue(result[0])
        self.assertEqual(result[1], 0)  # Size is 0 in dry_run mode

        # File should not be created in dry-run
        self.assertEqual(len(list(target_folder.glob("test*.pdf"))), 0)

    def test_save_attachment_empty_filename(self):
        """Test attachment saving with empty filename."""
        handler = AttachmentHandler()
        target_folder = self.download_dir / "test_folder"
        target_folder.mkdir()

        part = email.message.Message()
        part.set_payload(b"test content")
        part.add_header("Content-Disposition", "attachment", filename="")

        result = handler.save_attachment(part, target_folder, "123", dry_run=False)
        self.assertFalse(result[0])
        self.assertEqual(result[1], 0)

    def test_save_attachment_no_payload(self):
        """Test attachment saving with no payload."""
        handler = AttachmentHandler()
        target_folder = self.download_dir / "test_folder"
        target_folder.mkdir()

        part = email.message.Message()
        part.add_header("Content-Disposition", "attachment", filename="test.pdf")
        # No payload set

        result = handler.save_attachment(part, target_folder, "123", dry_run=False)
        self.assertFalse(result[0])
        self.assertEqual(result[1], 0)

    def test_save_attachment_too_large(self):
        """Test attachment saving with file too large."""
        handler = AttachmentHandler(max_size=1024)
        target_folder = self.download_dir / "test_folder"
        target_folder.mkdir()

        part = email.message.Message()
        part.set_payload(b"x" * 2048)  # 2KB, larger than max_size
        part.add_header("Content-Disposition", "attachment", filename="test.pdf")

        result = handler.save_attachment(part, target_folder, "123", dry_run=False)
        self.assertFalse(result[0])
        self.assertEqual(result[1], 0)

    def test_save_attachment_io_error(self):
        """Test attachment saving with IO error."""
        handler = AttachmentHandler()
        target_folder = self.download_dir / "test_folder"
        target_folder.mkdir()

        part = email.message.Message()
        part.set_payload(b"test content")
        part.add_header("Content-Disposition", "attachment", filename="test.pdf")

        with patch("pathlib.Path.open", side_effect=OSError("Permission denied")):
            result = handler.save_attachment(part, target_folder, "123", dry_run=False)
            self.assertFalse(result[0])
            self.assertEqual(result[1], 0)

    def test_save_attachment_unexpected_error(self):
        """Test attachment saving with unexpected error."""
        handler = AttachmentHandler()
        target_folder = self.download_dir / "test_folder"
        target_folder.mkdir()

        part = email.message.Message()
        part.set_payload(b"test content")
        part.add_header("Content-Disposition", "attachment", filename="test.pdf")

        with patch("pathlib.Path.open", side_effect=Exception("Unexpected error")):
            result = handler.save_attachment(part, target_folder, "123", dry_run=False)
            self.assertFalse(result[0])
            self.assertEqual(result[1], 0)

    def test_is_allowed_extension_no_filter(self):
        """Test extension filtering with no restrictions."""
        handler = AttachmentHandler()

        self.assertTrue(handler.is_allowed_extension("test.pdf"))
        self.assertTrue(handler.is_allowed_extension("test.exe"))
        self.assertTrue(handler.is_allowed_extension("test.doc"))

    def test_is_allowed_extension_allowed_list(self):
        """Test extension filtering with allowed list."""
        handler = AttachmentHandler(allowed_extensions=[".pdf", ".doc", ".docx"])

        self.assertTrue(handler.is_allowed_extension("test.pdf"))
        self.assertTrue(handler.is_allowed_extension("test.PDF"))  # Case insensitive
        self.assertTrue(handler.is_allowed_extension("test.doc"))
        self.assertFalse(handler.is_allowed_extension("test.exe"))
        self.assertFalse(handler.is_allowed_extension("test.txt"))
        self.assertFalse(handler.is_allowed_extension("test"))  # No extension

    def test_is_allowed_extension_blocked_list(self):
        """Test extension filtering with blocked list."""
        handler = AttachmentHandler(blocked_extensions=[".exe", ".bat", ".sh"])

        self.assertTrue(handler.is_allowed_extension("test.pdf"))
        self.assertTrue(handler.is_allowed_extension("test.doc"))
        self.assertFalse(handler.is_allowed_extension("test.exe"))
        self.assertFalse(handler.is_allowed_extension("test.EXE"))  # Case insensitive
        self.assertFalse(handler.is_allowed_extension("test.bat"))

    def test_is_allowed_extension_both_lists(self):
        """Test extension filtering with both allowed and blocked lists."""
        handler = AttachmentHandler(
            allowed_extensions=[".pdf", ".doc", ".exe", ".bat"],
            blocked_extensions=[".exe", ".bat"],
        )

        # Blocked takes priority
        self.assertFalse(handler.is_allowed_extension("test.exe"))
        self.assertFalse(handler.is_allowed_extension("test.bat"))
        # Allowed but not blocked
        self.assertTrue(handler.is_allowed_extension("test.pdf"))
        self.assertTrue(handler.is_allowed_extension("test.doc"))
        # Not in allowed list
        self.assertFalse(handler.is_allowed_extension("test.txt"))

    def test_is_allowed_extension_without_dot(self):
        """Test extension filtering handles extensions without dot prefix."""
        handler = AttachmentHandler(
            allowed_extensions=["pdf", "doc", ".docx"],  # Mix of with and without dot
        )

        self.assertTrue(handler.is_allowed_extension("test.pdf"))
        self.assertTrue(handler.is_allowed_extension("test.doc"))
        self.assertTrue(handler.is_allowed_extension("test.docx"))
        self.assertFalse(handler.is_allowed_extension("test.txt"))

    def test_save_attachment_blocked_extension(self):
        """Test attachment saving with blocked extension."""
        handler = AttachmentHandler(blocked_extensions=[".exe", ".bat"])
        target_folder = self.download_dir / "test_folder"
        target_folder.mkdir()

        part = email.message.Message()
        part.set_payload(b"test content")
        part.add_header("Content-Disposition", "attachment", filename="malware.exe")

        result = handler.save_attachment(part, target_folder, "123", dry_run=False)
        self.assertFalse(result[0])
        self.assertEqual(result[1], 0)

        # File should not be created
        self.assertEqual(len(list(target_folder.glob("malware*.exe"))), 0)

    def test_save_attachment_allowed_extension_only(self):
        """Test attachment saving with only allowed extensions."""
        handler = AttachmentHandler(allowed_extensions=[".pdf", ".doc"])
        target_folder = self.download_dir / "test_folder"
        target_folder.mkdir()

        # Allowed extension
        part1 = email.message.Message()
        part1.set_payload(b"test content")
        part1.add_header("Content-Disposition", "attachment", filename="document.pdf")

        result1 = handler.save_attachment(part1, target_folder, "123", dry_run=False)
        self.assertTrue(result1[0])

        # Not allowed extension
        part2 = email.message.Message()
        part2.set_payload(b"test content")
        part2.add_header("Content-Disposition", "attachment", filename="script.txt")

        result2 = handler.save_attachment(part2, target_folder, "123", dry_run=False)
        self.assertFalse(result2[0])

    @patch("email_processor.imap.attachments.check_disk_space")
    def test_save_attachment_insufficient_disk_space(self, mock_check_disk):
        """Test attachment saving when disk space is insufficient."""
        handler = AttachmentHandler()
        target_folder = self.download_dir / "test_folder"
        target_folder.mkdir()

        part = email.message.Message()
        part.set_payload(b"test content")
        part.add_header("Content-Disposition", "attachment", filename="test.pdf")

        # Mock check_disk_space to return False (insufficient space)
        mock_check_disk.return_value = False

        result = handler.save_attachment(part, target_folder, "123", dry_run=False)
        self.assertFalse(result[0])
        self.assertEqual(result[1], 0)

        # File should not be created
        self.assertEqual(len(list(target_folder.glob("test*.pdf"))), 0)
        # check_disk_space should be called with required_bytes (file_size + 10MB buffer)
        mock_check_disk.assert_called_once()
        call_args = mock_check_disk.call_args
        # Normalize paths for comparison (macOS uses /private/var symlink)
        actual_path = Path(call_args[0][0]).resolve()
        expected_path = target_folder.resolve()
        self.assertEqual(actual_path, expected_path)
        # required_bytes should be file_size (12) + 10MB buffer
        self.assertEqual(call_args[0][1], 12 + 10 * 1024 * 1024)
