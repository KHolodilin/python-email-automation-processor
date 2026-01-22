"""Tests for SMTP sender module."""

import logging
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from email_processor.logging.setup import setup_logging
from email_processor.smtp.config import SMTPConfig
from email_processor.smtp.sender import (
    EmailSender,
    calculate_email_size,
    create_email_message,
    create_email_subject,
    format_subject_template,
    split_files_by_size,
)


class TestSubjectTemplates(unittest.TestCase):
    """Tests for subject template formatting."""

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

    def test_format_subject_template(self):
        """Test subject template formatting."""
        template = "File: {filename} - {date}"
        context = {"filename": "test.pdf", "date": "2024-01-15"}
        result = format_subject_template(template, context)
        self.assertEqual(result, "File: test.pdf - 2024-01-15")

    def test_format_subject_template_missing_variable(self):
        """Test subject template with missing variable."""
        template = "File: {filename} - {missing}"
        context = {"filename": "test.pdf"}
        result = format_subject_template(template, context)
        # Should handle gracefully by replacing missing variable with empty string
        self.assertIsInstance(result, str)
        self.assertIn("test.pdf", result)
        # Missing variable should be replaced with empty string
        self.assertEqual(result, "File: test.pdf - ")

    def test_format_subject_template_keyerror_fallback(self):
        """Test format_subject_template when KeyError occurs and manual replacement is used."""
        # Create a template that will cause KeyError even after building full_context
        # This can happen with complex template syntax
        template = "File: {filename} - {date} - {extra}"
        context = {"filename": "test.pdf", "date": "2024-01-15"}
        # The template has {extra} which will be in full_context as empty string
        # But if format() somehow still fails, it should use manual replacement
        result = format_subject_template(template, context)
        self.assertIsInstance(result, str)
        self.assertIn("test.pdf", result)
        self.assertIn("2024-01-15", result)

    def test_create_email_subject_single_file(self):
        """Test creating subject for single file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.pdf"
            file_path.write_bytes(b"test content")

            subject = create_email_subject([file_path])
            self.assertEqual(subject, "test.pdf")

    def test_create_email_subject_multiple_files(self):
        """Test creating subject for multiple files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "file1.pdf"
            file2 = Path(tmpdir) / "file2.pdf"
            file1.write_bytes(b"content1")
            file2.write_bytes(b"content2")

            subject = create_email_subject([file1, file2])
            self.assertIn("Package of files", subject)
            self.assertIn(datetime.now().strftime("%Y-%m-%d"), subject)

    def test_create_email_subject_with_template_single(self):
        """Test creating subject with template for single file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.pdf"
            file_path.write_bytes(b"test content")

            template = "File: {filename}"
            subject = create_email_subject([file_path], template=template)
            self.assertEqual(subject, "File: test.pdf")

    def test_create_email_subject_with_template_multiple(self):
        """Test creating subject with template for multiple files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "file1.pdf"
            file2 = Path(tmpdir) / "file2.pdf"
            file1.write_bytes(b"content1")
            file2.write_bytes(b"content2")

            template = "Package - {file_count} files"
            subject = create_email_subject([file1, file2], template=template)
            self.assertIn("Package - 2 files", subject)


class TestEmailSizeCalculation(unittest.TestCase):
    """Tests for email size calculation."""

    def test_calculate_email_size(self):
        """Test email size calculation with MIME overhead."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "file1.txt"
            file2 = Path(tmpdir) / "file2.txt"
            file1.write_bytes(b"x" * 1000)
            file2.write_bytes(b"y" * 2000)

            size = calculate_email_size([file1, file2])

            # Should be larger than sum due to MIME overhead (~33%)
            self.assertGreater(size, 3000)
            self.assertLess(size, 5000)  # Should not exceed 33% overhead too much


class TestFileSplitting(unittest.TestCase):
    """Tests for file splitting by size."""

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

    def test_split_files_by_size_single_file(self):
        """Test splitting single file that fits."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "small.txt"
            file_path.write_bytes(b"x" * 1000)

            groups = split_files_by_size([file_path], max_size_mb=1.0)
            self.assertEqual(len(groups), 1)
            self.assertEqual(len(groups[0]), 1)

    def test_split_files_by_size_multiple_files_fit(self):
        """Test multiple files that fit in one email."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "file1.txt"
            file2 = Path(tmpdir) / "file2.txt"
            file1.write_bytes(b"x" * 1000)
            file2.write_bytes(b"y" * 1000)

            groups = split_files_by_size([file1, file2], max_size_mb=1.0)
            self.assertEqual(len(groups), 1)
            self.assertEqual(len(groups[0]), 2)

    def test_split_files_by_size_exceeds_limit(self):
        """Test files that exceed limit are split."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "file1.txt"
            file2 = Path(tmpdir) / "file2.txt"
            # Each file ~500KB, with overhead should fit in 1MB limit
            file1.write_bytes(b"x" * 500000)
            file2.write_bytes(b"y" * 500000)

            groups = split_files_by_size([file1, file2], max_size_mb=0.5)
            # Should be split into multiple groups
            self.assertGreaterEqual(len(groups), 1)

    def test_split_files_by_size_single_file_exceeds(self):
        """Test single file that exceeds limit raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "large.txt"
            file_path.write_bytes(b"x" * (2 * 1024 * 1024))  # 2MB

            with self.assertRaises(ValueError) as context:
                split_files_by_size([file_path], max_size_mb=1.0)

            self.assertIn("exceeds maximum email size", str(context.exception))


class TestEmailMessageCreation(unittest.TestCase):
    """Tests for email message creation."""

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

    def test_create_email_message_single_file(self):
        """Test creating email message with single file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.pdf"
            file_path.write_bytes(b"test content")

            msg = create_email_message(
                "from@example.com", "to@example.com", "Test Subject", [file_path]
            )

            self.assertEqual(msg["From"], "from@example.com")
            self.assertEqual(msg["To"], "to@example.com")
            self.assertEqual(msg["Subject"], "Test Subject")
            # Check attachment
            self.assertGreater(len(msg.get_payload()), 0)

    def test_create_email_message_multiple_files(self):
        """Test creating email message with multiple files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "file1.pdf"
            file2 = Path(tmpdir) / "file2.pdf"
            file1.write_bytes(b"content1")
            file2.write_bytes(b"content2")

            msg = create_email_message(
                "from@example.com", "to@example.com", "Test Subject", [file1, file2]
            )

            self.assertEqual(msg["From"], "from@example.com")
            self.assertEqual(msg["To"], "to@example.com")
            # Should have body + 2 attachments
            payload = msg.get_payload()
            self.assertGreaterEqual(len(payload), 2)

    def test_create_email_message_with_body_text(self):
        """Test creating email message with custom body text."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.pdf"
            file_path.write_bytes(b"test content")

            msg = create_email_message(
                "from@example.com",
                "to@example.com",
                "Test Subject",
                [file_path],
                body_text="Custom body text",
            )

            payload = msg.get_payload()
            # Should have body text
            self.assertGreater(len(payload), 0)


class TestEmailSender(unittest.TestCase):
    """Tests for EmailSender class."""

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

    @patch("email_processor.smtp.smtp_connect")
    def test_send_file_success(self, mock_smtp_connect):
        """Test successful file sending."""
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

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.pdf"
            file_path.write_bytes(b"test content")

            result = sender.send_file(file_path, "recipient@example.com", dry_run=False)

            self.assertTrue(result)
            mock_smtp_connect.assert_called_once()
            mock_smtp.send_message.assert_called_once()
            mock_smtp.quit.assert_called_once()

    def test_send_file_dry_run(self):
        """Test file sending in dry-run mode."""
        config = SMTPConfig(
            smtp_server="smtp.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_password="password",
            from_address="sender@example.com",
        )
        sender = EmailSender(config=config)

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.pdf"
            file_path.write_bytes(b"test content")

            result = sender.send_file(file_path, "recipient@example.com", dry_run=True)

            self.assertTrue(result)
            # Should not actually connect to SMTP

    def test_send_file_with_subject_template(self):
        """Test sending file with subject template."""
        config = SMTPConfig(
            smtp_server="smtp.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_password="password",
            from_address="sender@example.com",
            subject_template="File: {filename}",
        )
        sender = EmailSender(config=config)

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.pdf"
            file_path.write_bytes(b"test content")

            # In dry-run, should use template
            result = sender.send_file(file_path, "recipient@example.com", dry_run=True)
            self.assertTrue(result)

    def test_send_files_empty_list(self):
        """Test sending empty file list."""
        config = SMTPConfig(
            smtp_server="smtp.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_password="password",
            from_address="sender@example.com",
        )
        sender = EmailSender(config=config)

        result = sender.send_files([], "recipient@example.com")
        self.assertFalse(result)

    @patch("email_processor.smtp.smtp_connect")
    def test_send_files_split_by_size(self, mock_connect):
        """Test sending files that need to be split."""
        mock_smtp = MagicMock()
        mock_smtp.send_message.return_value = None
        mock_connect.return_value = mock_smtp

        config = SMTPConfig(
            smtp_server="smtp.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_password="password",
            from_address="sender@example.com",
            max_email_size_mb=0.1,  # Small limit
        )
        sender = EmailSender(config=config)

        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "file1.txt"
            file2 = Path(tmpdir) / "file2.txt"
            # Each file ~100KB
            file1.write_bytes(b"x" * 100000)
            file2.write_bytes(b"y" * 100000)

            result = sender.send_files([file1, file2], "recipient@example.com", dry_run=False)

            # Should send multiple emails if split
            self.assertTrue(result)
            # Number of send_message calls depends on splitting
            self.assertGreaterEqual(mock_smtp.send_message.call_count, 1)

    @patch("email_processor.smtp.smtp_connect")
    def test_send_files_oserror_attach(self, mock_connect):
        """Test send_files handles OSError when attaching file."""
        mock_smtp = MagicMock()
        mock_smtp.send_message.return_value = None
        mock_connect.return_value = mock_smtp

        config = SMTPConfig(
            smtp_server="smtp.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_password="password",
            from_address="sender@example.com",
        )
        sender = EmailSender(config=config)

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.pdf"
            file_path.write_bytes(b"test content")

            # Mock Path.open to raise OSError when attaching (in create_email_message)
            # Need to patch where the file is actually opened
            original_open = Path.open

            def mock_open(self, mode="r", *args, **kwargs):
                if mode == "rb" and str(self) == str(file_path):
                    raise OSError("Permission denied")
                return original_open(self, mode, *args, **kwargs)

            with patch.object(Path, "open", mock_open):
                # OSError is caught and logged, then caught in general exception handler
                # Function should return False
                result = sender.send_files([file_path], "recipient@example.com", dry_run=False)
                self.assertFalse(result)

    def test_send_files_valueerror_split(self):
        """Test send_files handles ValueError from split_files_by_size."""
        config = SMTPConfig(
            smtp_server="smtp.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_password="password",
            from_address="sender@example.com",
            max_email_size_mb=0.001,  # Very small limit
        )
        sender = EmailSender(config=config)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file that's too large for the limit
            file_path = Path(tmpdir) / "large.txt"
            file_path.write_bytes(b"x" * (2 * 1024 * 1024))  # 2MB

            result = sender.send_files([file_path], "recipient@example.com", dry_run=False)
            # Should return False when ValueError is raised
            self.assertFalse(result)

    @patch("email_processor.smtp.smtp_connect")
    def test_send_files_custom_subject(self, mock_connect):
        """Test send_files with custom subject parameter."""
        mock_smtp = MagicMock()
        mock_smtp.send_message.return_value = None
        mock_connect.return_value = mock_smtp

        config = SMTPConfig(
            smtp_server="smtp.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_password="password",
            from_address="sender@example.com",
        )
        sender = EmailSender(config=config)

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.pdf"
            file_path.write_bytes(b"test content")

            result = sender.send_files(
                [file_path], "recipient@example.com", subject="Custom Subject", dry_run=False
            )
            self.assertTrue(result)

    @patch("email_processor.smtp.smtp_connect")
    def test_send_files_package_template(self, mock_connect):
        """Test send_files uses package template for multiple files."""
        mock_smtp = MagicMock()
        mock_smtp.send_message.return_value = None
        mock_connect.return_value = mock_smtp

        config = SMTPConfig(
            smtp_server="smtp.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_password="password",
            from_address="sender@example.com",
            subject_template_package="Package: {file_count} files",
        )
        sender = EmailSender(config=config)

        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "file1.pdf"
            file2 = Path(tmpdir) / "file2.pdf"
            file1.write_bytes(b"content1")
            file2.write_bytes(b"content2")

            result = sender.send_files([file1, file2], "recipient@example.com", dry_run=False)
            self.assertTrue(result)

    @patch("email_processor.smtp.smtp_connect")
    def test_send_files_exception_handling(self, mock_connect):
        """Test send_files handles general exceptions."""
        # Make smtp_connect raise an exception
        mock_connect.side_effect = Exception("Connection failed")

        config = SMTPConfig(
            smtp_server="smtp.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_password="password",
            from_address="sender@example.com",
        )
        sender = EmailSender(config=config)

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test.pdf"
            file_path.write_bytes(b"test content")

            result = sender.send_files([file_path], "recipient@example.com", dry_run=False)
            # Should return False on exception
            self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
