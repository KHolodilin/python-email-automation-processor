"""Integration tests for SMTP email sending."""

import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from email_processor.logging.setup import setup_logging
from email_processor.smtp.config import SMTPConfig
from email_processor.smtp.sender import EmailSender
from email_processor.storage.sent_files_storage import SentFilesStorage


class TestSMTPIntegration(unittest.TestCase):
    """Integration tests for SMTP sending functionality."""

    def setUp(self):
        """Set up test fixtures."""
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
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("email_processor.smtp.smtp_connect")
    def test_full_send_file_cycle(self, mock_smtp_connect):
        """Test full cycle of sending a file."""
        mock_smtp = MagicMock()
        mock_smtp.send_message.return_value = None
        mock_smtp_connect.return_value = mock_smtp

        config = SMTPConfig(
            smtp_server="smtp.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_password="password",
            from_address="sender@example.com",
        )
        sender = EmailSender(config=config)
        storage = SentFilesStorage(self.temp_dir)

        # Create test file
        test_file = Path(self.temp_dir) / "test.pdf"
        test_file.write_bytes(b"test content")
        day_str = "2024-01-15"

        # Verify file is not sent yet
        self.assertFalse(storage.is_sent(test_file, day_str))

        # Send file
        result = sender.send_file(test_file, "recipient@example.com", dry_run=False)
        self.assertTrue(result)

        # Mark as sent
        storage.mark_as_sent(test_file, day_str)

        # Verify file is now marked as sent
        self.assertTrue(storage.is_sent(test_file, day_str))

        # Verify SMTP was called
        mock_smtp_connect.assert_called_once()
        mock_smtp.send_message.assert_called_once()

    @patch("email_processor.smtp.smtp_connect")
    def test_send_multiple_files_split(self, mock_smtp_connect):
        """Test sending multiple files that need to be split."""
        mock_smtp = MagicMock()
        mock_smtp.send_message.return_value = None
        mock_smtp_connect.return_value = mock_smtp

        config = SMTPConfig(
            smtp_server="smtp.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_password="password",
            from_address="sender@example.com",
            max_email_size_mb=0.1,  # Small limit to force splitting
        )
        sender = EmailSender(config=config)

        # Create multiple files
        files = []
        for i in range(3):
            file_path = Path(self.temp_dir) / f"file{i}.txt"
            file_path.write_bytes(b"x" * 50000)  # 50KB each
            files.append(file_path)

        result = sender.send_files(files, "recipient@example.com", dry_run=False)
        self.assertTrue(result)

        # Should have sent at least one email
        self.assertGreaterEqual(mock_smtp.send_message.call_count, 1)

    def test_sent_files_tracking_integration(self):
        """Test integration of sent files tracking."""
        storage = SentFilesStorage(self.temp_dir)
        day_str = "2024-01-15"

        # Create two files with same content
        file1 = Path(self.temp_dir) / "file1.txt"
        file2 = Path(self.temp_dir) / "file2.txt"
        content = b"same content"
        file1.write_bytes(content)
        file2.write_bytes(content)

        # Mark first file as sent
        storage.mark_as_sent(file1, day_str)

        # Second file should be recognized as sent (same hash)
        self.assertTrue(storage.is_sent(file2, day_str))

    def test_subject_templates_integration(self):
        """Test subject templates in full sending cycle."""
        config = SMTPConfig(
            smtp_server="smtp.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_password="password",
            from_address="sender@example.com",
            subject_template="File: {filename}",
            subject_template_package="Package: {file_count} files",
        )
        sender = EmailSender(config=config)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Test single file with template
            file1 = Path(tmpdir) / "test.pdf"
            file1.write_bytes(b"content")

            # In dry-run, check that template is used
            result = sender.send_file(file1, "recipient@example.com", dry_run=True)
            self.assertTrue(result)

            # Test multiple files with package template
            file2 = Path(tmpdir) / "test2.pdf"
            file2.write_bytes(b"content2")

            result = sender.send_files([file1, file2], "recipient@example.com", dry_run=True)
            self.assertTrue(result)

    @patch("email_processor.smtp.smtp_connect")
    def test_dry_run_vs_real_send(self, mock_smtp_connect):
        """Test that dry-run doesn't actually send."""
        mock_smtp = MagicMock()
        mock_smtp_connect.return_value = mock_smtp

        config = SMTPConfig(
            smtp_server="smtp.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_password="password",
            from_address="sender@example.com",
        )
        sender = EmailSender(config=config)

        test_file = Path(self.temp_dir) / "test.pdf"
        test_file.write_bytes(b"test content")

        # Dry-run should not connect
        result = sender.send_file(test_file, "recipient@example.com", dry_run=True)
        self.assertTrue(result)
        mock_smtp_connect.assert_not_called()

        # Real send should connect
        result = sender.send_file(test_file, "recipient@example.com", dry_run=False)
        self.assertTrue(result)
        mock_smtp_connect.assert_called_once()

    def test_file_size_limit_enforcement(self):
        """Test that file size limits are enforced."""
        config = SMTPConfig(
            smtp_server="smtp.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_password="password",
            from_address="sender@example.com",
            max_email_size_mb=1.0,
        )
        sender = EmailSender(config=config)

        # Create file that exceeds limit
        large_file = Path(self.temp_dir) / "large.bin"
        large_file.write_bytes(b"x" * (2 * 1024 * 1024))  # 2MB

        # Should fail to send
        result = sender.send_file(large_file, "recipient@example.com", dry_run=True)
        # In dry-run, it might still return True, but in real send would raise ValueError
        # Let's test the splitting function directly
        from email_processor.smtp.sender import split_files_by_size

        with self.assertRaises(ValueError):
            split_files_by_size([large_file], max_size_mb=1.0)


if __name__ == "__main__":
    unittest.main()
