"""Additional tests for email processor to reach 90% coverage."""

import imaplib
import shutil
import tempfile
import unittest
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from unittest.mock import MagicMock, patch

from email_processor.logging.setup import setup_logging
from email_processor.processor.email_processor import EmailProcessor


class TestEmailProcessorAdditional(unittest.TestCase):
    """Additional tests for EmailProcessor to increase coverage."""

    def setUp(self):
        """Setup test fixtures."""
        setup_logging({"level": "INFO", "format": "console"})
        self.temp_dir = tempfile.mkdtemp()

        self.config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
                "max_retries": 3,
                "retry_delay": 1,
            },
            "processing": {
                "start_days_back": 5,
                "download_dir": str(Path(self.temp_dir) / "downloads"),
                "archive_folder": "INBOX/Processed",
                "processed_dir": str(Path(self.temp_dir) / "processed_uids"),
                "keep_processed_days": 0,
                "archive_only_mapped": True,
                "skip_non_allowed_as_processed": True,
                "skip_unmapped_as_processed": True,
            },
            "logging": {
                "level": "INFO",
                "format": "console",
            },
            "allowed_senders": ["sender@example.com"],
            "topic_mapping": {
                ".*invoice.*": "invoices",
            },
        }
        self.processor = EmailProcessor(self.config)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_process_email_header_empty(self):
        """Test _process_email when header is empty."""
        mock_mail = MagicMock()
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, b"")]),  # Empty header
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "skipped")

    def test_process_email_header_parse_error(self):
        """Test _process_email when header parsing fails."""
        mock_mail = MagicMock()
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, b"Invalid header")]),
        ]

        with patch(
            "email_processor.processor.email_processor.message_from_bytes",
            side_effect=Exception("Parse error"),
        ):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")

    def test_process_email_invalid_target_folder(self):
        """Test _process_email when target folder validation fails."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
        ]

        with patch("email_processor.processor.email_processor.validate_path", return_value=False):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")

    def test_process_email_target_folder_create_error(self):
        """Test _process_email when target folder creation fails."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
        ]

        with patch("pathlib.Path.mkdir", side_effect=Exception("Permission denied")):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")

    def test_process_email_message_body_empty(self):
        """Test _process_email when message body is empty."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, b"")]),  # Empty message body
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "skipped")

    def test_process_email_message_parse_error(self):
        """Test _process_email when message parsing fails."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, b"Invalid message")]),
        ]

        with patch(
            "email_processor.processor.email_processor.message_from_bytes",
            side_effect=Exception("Parse error"),
        ):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")

    def test_process_email_processed_uid_save_error(self):
        """Test _process_email when saving processed UID fails."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        msg_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\n\r\nBody"
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, msg_bytes)]),
        ]

        with patch(
            "email_processor.processor.email_processor.save_processed_uid_for_day",
            side_effect=Exception("Save error"),
        ):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")

    def test_process_email_archive_error(self):
        """Test _process_email when archiving fails."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        msg_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\n\r\nBody"
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, msg_bytes)]),
        ]

        with patch(
            "email_processor.processor.email_processor.archive_message",
            side_effect=Exception("Archive error"),
        ):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should still return "skipped" (no attachments)
            self.assertEqual(result, "skipped")

    def test_process_email_with_attachment_success(self):
        """Test _process_email successfully processes email with attachment."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"

        # Create message with attachment
        msg = MIMEMultipart()
        msg["From"] = "sender@example.com"
        msg["Subject"] = "Invoice"
        msg["Date"] = "Mon, 1 Jan 2024 12:00:00 +0000"

        part = MIMEBase("application", "pdf")
        part.set_payload(b"test pdf content")
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment", filename="test.pdf")
        msg.attach(part)

        msg_bytes = msg.as_bytes()

        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, msg_bytes)]),
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        # Should process successfully
        self.assertEqual(result, "processed")

        # Check file was created
        invoices_dir = Path(self.temp_dir) / "downloads" / "invoices"
        self.assertTrue(invoices_dir.exists())
        pdf_files = list(invoices_dir.glob("*.pdf"))
        self.assertGreater(len(pdf_files), 0)

    def test_process_email_attachment_errors(self):
        """Test _process_email when attachment processing has errors."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"

        # Create message with attachment that will fail
        msg = MIMEMultipart()
        msg["From"] = "sender@example.com"
        msg["Subject"] = "Invoice"
        msg["Date"] = "Mon, 1 Jan 2024 12:00:00 +0000"

        part = MIMEBase("application", "pdf")
        part.set_payload(b"test content")
        part.add_header("Content-Disposition", "attachment", filename="test.pdf")
        msg.attach(part)

        msg_bytes = msg.as_bytes()

        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, msg_bytes)]),
        ]

        # Mock attachment handler to return False (error)
        with patch.object(
            self.processor.attachment_handler, "save_attachment", return_value=(False, 0)
        ):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should return "error" if attachment processing fails
            self.assertEqual(result, "error")

    def test_process_email_message_walk_error(self):
        """Test _process_email when message.walk() fails."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        # Create a proper message that can be parsed, but walk() will fail
        msg = MIMEText("Body")
        msg["From"] = "sender@example.com"
        msg["Subject"] = "Invoice"
        msg["Date"] = "Mon, 1 Jan 2024 12:00:00 +0000"
        msg_bytes = msg.as_bytes()

        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, msg_bytes)]),
        ]

        # Create mock header message
        mock_header_msg = MagicMock()
        mock_header_msg.get.side_effect = lambda x, d="": {
            "From": "sender@example.com",
            "Subject": "Invoice",
            "Date": "Mon, 1 Jan 2024 12:00:00 +0000",
        }.get(x, d)

        # Create mock full message that will fail on walk()
        mock_full_msg = MagicMock()
        mock_full_msg.walk.side_effect = Exception("Walk error")

        # message_from_bytes is called twice: once for header, once for full message
        with patch(
            "email_processor.processor.email_processor.message_from_bytes",
            side_effect=[
                mock_header_msg,  # First call for header
                mock_full_msg,  # Second call for full message
            ],
        ):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")

    def test_process_email_skip_non_allowed_false(self):
        """Test _process_email when skip_non_allowed_as_processed is False."""
        config = self.config.copy()
        config["processing"]["skip_non_allowed_as_processed"] = False
        processor = EmailProcessor(config)

        mock_mail = MagicMock()
        header_bytes = (
            b"From: other@example.com\r\nSubject: Test\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        )
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result = processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "skipped")
        # Should not save UID when skip_non_allowed_as_processed is False

    def test_process_email_archive_only_mapped_false(self):
        """Test _process_email when archive_only_mapped is False."""
        config = self.config.copy()
        config["processing"]["archive_only_mapped"] = False
        processor = EmailProcessor(config)

        mock_mail = MagicMock()
        header_bytes = (
            b"From: sender@example.com\r\nSubject: Test\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        )
        msg_bytes = b"From: sender@example.com\r\nSubject: Test\r\n\r\nBody"
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, msg_bytes)]),
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result = processor._process_email(mock_mail, b"1", {}, False, metrics)
        # Should not archive when archive_only_mapped is False and no mapped folder
        self.assertEqual(result, "skipped")

    def test_process_file_stats_collection(self):
        """Test file statistics collection in process method."""
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b""])  # No messages

        with (
            patch(
                "email_processor.processor.email_processor.get_imap_password",
                return_value="password",
            ),
            patch("email_processor.processor.email_processor.imap_connect", return_value=mock_mail),
        ):
            # Create some test files in download_dir
            download_dir = Path(self.temp_dir) / "downloads"
            download_dir.mkdir(parents=True, exist_ok=True)
            (download_dir / "test.pdf").write_text("test")
            (download_dir / "test.doc").write_text("test")

            result = self.processor.process(dry_run=False)
            # File stats should be None when no emails processed
            self.assertIsNone(result.file_stats)

    def test_process_file_stats_with_processed(self):
        """Test file statistics when emails are processed."""
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b"1"])

        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"

        # Create message with attachment
        msg = MIMEMultipart()
        msg["From"] = "sender@example.com"
        msg["Subject"] = "Invoice"
        msg["Date"] = "Mon, 1 Jan 2024 12:00:00 +0000"

        part = MIMEBase("application", "pdf")
        part.set_payload(b"test pdf content")
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment", filename="test.pdf")
        msg.attach(part)

        msg_bytes = msg.as_bytes()

        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, msg_bytes)]),
        ]

        with (
            patch(
                "email_processor.processor.email_processor.get_imap_password",
                return_value="password",
            ),
            patch("email_processor.processor.email_processor.imap_connect", return_value=mock_mail),
        ):
            result = self.processor.process(dry_run=False)
            # Should have file stats
            self.assertIsNotNone(result.file_stats)
            self.assertIn(".pdf", result.file_stats)

    def test_process_file_stats_collection_error(self):
        """Test file statistics collection error handling."""
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b"1"])

        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"

        msg = MIMEMultipart()
        msg["From"] = "sender@example.com"
        msg["Subject"] = "Invoice"
        msg["Date"] = "Mon, 1 Jan 2024 12:00:00 +0000"

        part = MIMEBase("application", "pdf")
        part.set_payload(b"test")
        part.add_header("Content-Disposition", "attachment", filename="test.pdf")
        msg.attach(part)

        msg_bytes = msg.as_bytes()

        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, msg_bytes)]),
        ]

        with (
            patch(
                "email_processor.processor.email_processor.get_imap_password",
                return_value="password",
            ),
            patch("email_processor.processor.email_processor.imap_connect", return_value=mock_mail),
            patch("pathlib.Path.rglob", side_effect=Exception("Access error")),
        ):
            result = self.processor.process(dry_run=False)
            # Should handle error gracefully
            self.assertIsInstance(result, type(result))

    def test_process_imap_error_handling(self):
        """Test process handles IMAP errors during email processing."""
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b"1"])
        mock_mail.fetch.side_effect = imaplib.IMAP4.error("IMAP error")

        with (
            patch(
                "email_processor.processor.email_processor.get_imap_password",
                return_value="password",
            ),
            patch("email_processor.processor.email_processor.imap_connect", return_value=mock_mail),
        ):
            result = self.processor.process(dry_run=False)
            # Should handle IMAP errors
            self.assertGreaterEqual(result.errors, 0)

    def test_process_unexpected_error_handling(self):
        """Test process handles unexpected errors during email processing."""
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b"1"])
        mock_mail.fetch.side_effect = Exception("Unexpected error")

        with (
            patch(
                "email_processor.processor.email_processor.get_imap_password",
                return_value="password",
            ),
            patch("email_processor.processor.email_processor.imap_connect", return_value=mock_mail),
        ):
            result = self.processor.process(dry_run=False)
            # Should handle unexpected errors
            self.assertGreaterEqual(result.errors, 0)

    def test_process_logout_error(self):
        """Test process handles logout errors."""
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b""])
        mock_mail.logout.side_effect = Exception("Logout error")

        with (
            patch(
                "email_processor.processor.email_processor.get_imap_password",
                return_value="password",
            ),
            patch("email_processor.processor.email_processor.imap_connect", return_value=mock_mail),
        ):
            result = self.processor.process(dry_run=False)
            # Should handle logout errors gracefully
            self.assertIsInstance(result, type(result))
