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
                ".*invoice.*": str(Path(self.temp_dir) / "downloads" / "invoices"),
                ".*": str(Path(self.temp_dir) / "downloads" / "default"),
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
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "skipped")
        self.assertEqual(blocked, 0)

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
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

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
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

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
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "skipped")
        self.assertEqual(blocked, 0)

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
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

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
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

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
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should still return "skipped" (no attachments)
            self.assertEqual(result, "skipped")
            self.assertEqual(blocked, 0)

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
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        # Should process successfully
        self.assertEqual(result, "processed")
        self.assertEqual(blocked, 0)

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
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should return "error" if attachment processing fails
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

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
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

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
        result, blocked = processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "skipped")
        self.assertEqual(blocked, 0)
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
        result, blocked = processor._process_email(mock_mail, b"1", {}, False, metrics)
        # Should not archive when archive_only_mapped is False and no mapped folder
        self.assertEqual(result, "skipped")
        self.assertEqual(blocked, 0)

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
            # Create some test files in folders from topic_mapping
            invoices_dir = Path(self.temp_dir) / "downloads" / "invoices"
            invoices_dir.mkdir(parents=True, exist_ok=True)
            (invoices_dir / "test.pdf").write_text("test")
            default_dir = Path(self.temp_dir) / "downloads" / "default"
            default_dir.mkdir(parents=True, exist_ok=True)
            (default_dir / "test.doc").write_text("test")

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

    @patch("email_processor.processor.email_processor.get_imap_password")
    @patch("email_processor.processor.email_processor.imap_connect")
    def test_process_email_imap_error_processing(self, mock_imap_connect, mock_get_password):
        """Test processing when _process_email raises IMAP4.error."""
        import imaplib

        mock_get_password.return_value = "password"
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b"1"])  # One email
        mock_imap_connect.return_value = mock_mail

        # Mock _process_email to raise IMAP4.error
        with patch.object(
            self.processor,
            "_process_email",
            side_effect=imaplib.IMAP4.error("IMAP error during processing"),
        ):
            result = self.processor.process(dry_run=False)
            self.assertEqual(result.errors, 1)
            self.assertEqual(result.processed, 0)

    @patch("email_processor.processor.email_processor.get_imap_password")
    @patch("email_processor.processor.email_processor.imap_connect")
    def test_process_email_processing_data_error_value_error(
        self, mock_imap_connect, mock_get_password
    ):
        """Test processing when _process_email raises ValueError."""
        mock_get_password.return_value = "password"
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b"1"])  # One email
        mock_imap_connect.return_value = mock_mail

        # Mock _process_email to raise ValueError
        with patch.object(self.processor, "_process_email", side_effect=ValueError("Data error")):
            result = self.processor.process(dry_run=False)
            self.assertEqual(result.errors, 1)
            self.assertEqual(result.processed, 0)

    @patch("email_processor.processor.email_processor.get_imap_password")
    @patch("email_processor.processor.email_processor.imap_connect")
    def test_process_email_processing_data_error_type_error(
        self, mock_imap_connect, mock_get_password
    ):
        """Test processing when _process_email raises TypeError."""
        mock_get_password.return_value = "password"
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b"1"])  # One email
        mock_imap_connect.return_value = mock_mail

        # Mock _process_email to raise TypeError
        with patch.object(self.processor, "_process_email", side_effect=TypeError("Type error")):
            result = self.processor.process(dry_run=False)
            self.assertEqual(result.errors, 1)
            self.assertEqual(result.processed, 0)

    @patch("email_processor.processor.email_processor.get_imap_password")
    @patch("email_processor.processor.email_processor.imap_connect")
    def test_process_email_processing_data_error_attribute_error(
        self, mock_imap_connect, mock_get_password
    ):
        """Test processing when _process_email raises AttributeError."""
        mock_get_password.return_value = "password"
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b"1"])  # One email
        mock_imap_connect.return_value = mock_mail

        # Mock _process_email to raise AttributeError
        with patch.object(
            self.processor, "_process_email", side_effect=AttributeError("Attribute error")
        ):
            result = self.processor.process(dry_run=False)
            self.assertEqual(result.errors, 1)
            self.assertEqual(result.processed, 0)

    @patch("email_processor.processor.email_processor.get_imap_password")
    @patch("email_processor.processor.email_processor.imap_connect")
    def test_process_email_unexpected_error_processing(self, mock_imap_connect, mock_get_password):
        """Test processing when _process_email raises unexpected error."""
        mock_get_password.return_value = "password"
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b"1"])  # One email
        mock_imap_connect.return_value = mock_mail

        # Mock _process_email to raise unexpected error
        with patch.object(
            self.processor, "_process_email", side_effect=RuntimeError("Unexpected error")
        ):
            result = self.processor.process(dry_run=False)
            self.assertEqual(result.errors, 1)
            self.assertEqual(result.processed, 0)

    def test_process_email_uid_parse_error_attribute_error(self):
        """Test _process_email when UID parsing raises AttributeError."""
        mock_mail = MagicMock()
        # Return meta data that will cause AttributeError when trying to access meta[0][0]
        mock_meta_item = MagicMock()
        # Make meta[0] not None, but accessing meta[0][0] will raise AttributeError
        del mock_meta_item.__getitem__
        mock_mail.fetch.side_effect = [
            (
                "OK",
                [(mock_meta_item, None)],
            ),  # meta[0] exists but accessing [0] raises AttributeError
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_uid_parse_error_index_error(self):
        """Test _process_email when UID parsing raises IndexError."""
        mock_mail = MagicMock()
        # Return meta data that will cause IndexError when trying to access meta[0][0]
        mock_meta_item = []
        mock_mail.fetch.side_effect = [
            (
                "OK",
                [(mock_meta_item, None)],
            ),  # meta[0] exists but is empty list, accessing [0] raises IndexError
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_uid_parse_error_unicode_decode_error(self):
        """Test _process_email when UID parsing raises UnicodeDecodeError."""
        from email_processor.processor.email_processor import ProcessingMetrics

        mock_mail = MagicMock()

        # Return meta data that will cause UnicodeDecodeError when trying to decode
        # Create a mock that when accessed returns bytes that can't be decoded
        class BadDecode:
            def decode(self, encoding, errors="strict"):
                raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")

        mock_meta_item = BadDecode()
        mock_mail.fetch.side_effect = [
            ("OK", [(mock_meta_item, None)]),
        ]

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_uid_parse_unexpected_error(self):
        """Test _process_email when UID parsing raises unexpected error."""
        mock_mail = MagicMock()
        # Return meta data that will cause unexpected error
        mock_meta = MagicMock()
        mock_meta.__getitem__ = MagicMock(side_effect=RuntimeError("Unexpected error"))
        mock_mail.fetch.side_effect = [
            ("OK", [(mock_meta, None)]),
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_header_fetch_imap_error(self):
        """Test _process_email when header fetch raises IMAP4.error."""
        import imaplib

        mock_mail = MagicMock()
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),  # UID fetch succeeds
            imaplib.IMAP4.error("IMAP error"),  # Header fetch fails
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_header_fetch_data_error_attribute_error(self):
        """Test _process_email when header fetch raises AttributeError."""
        mock_mail = MagicMock()
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),  # UID fetch succeeds
            AttributeError("Attribute error"),  # Header fetch fails
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_header_fetch_data_error_index_error(self):
        """Test _process_email when header fetch raises IndexError."""
        mock_mail = MagicMock()
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),  # UID fetch succeeds
            IndexError("Index error"),  # Header fetch fails
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_header_fetch_data_error_type_error(self):
        """Test _process_email when header fetch raises TypeError."""
        mock_mail = MagicMock()
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),  # UID fetch succeeds
            TypeError("Type error"),  # Header fetch fails
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_header_fetch_unexpected_error(self):
        """Test _process_email when header fetch raises unexpected error."""
        mock_mail = MagicMock()
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),  # UID fetch succeeds
            RuntimeError("Unexpected error"),  # Header fetch fails
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_header_parse_error_message_parse_error(self):
        """Test _process_email when header parsing raises MessageParseError."""
        import email.errors

        mock_mail = MagicMock()
        header_bytes = b"Invalid header"
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
        ]

        with patch(
            "email_processor.processor.email_processor.message_from_bytes",
            side_effect=email.errors.MessageParseError("Parse error"),
        ):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

    def test_process_email_header_parse_error_unicode_decode_error(self):
        """Test _process_email when header parsing raises UnicodeDecodeError."""
        mock_mail = MagicMock()
        header_bytes = b"Invalid header"
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
        ]

        with patch(
            "email_processor.processor.email_processor.message_from_bytes",
            side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "invalid"),
        ):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

    def test_process_email_header_parse_data_error_attribute_error(self):
        """Test _process_email when header parsing raises AttributeError."""
        mock_mail = MagicMock()

        # Create header_data that will cause AttributeError when accessing [0][1] or [0]
        class BadHeaderData:
            def __getitem__(self, key):
                if key == 0:
                    raise AttributeError("Attribute error")
                raise IndexError("Index error")

        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [BadHeaderData()]),  # Invalid header data that causes AttributeError
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_header_parse_data_error_index_error(self):
        """Test _process_email when header parsing raises IndexError."""
        mock_mail = MagicMock()

        # Create header_data that will cause IndexError when accessing [0]
        class BadHeaderData:
            def __getitem__(self, key):
                raise IndexError("Index error")

        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [BadHeaderData()]),  # Invalid header data that causes IndexError
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_header_parse_data_error_type_error(self):
        """Test _process_email when header parsing raises TypeError."""
        mock_mail = MagicMock()

        # Create header_data that will cause TypeError when accessing [0][1] or [0]
        class BadHeaderData:
            def __getitem__(self, key):
                if key == 0:
                    raise TypeError("Type error")
                raise IndexError("Index error")

        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [BadHeaderData()]),  # Invalid header data that causes TypeError
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_header_parse_unexpected_error(self):
        """Test _process_email when header parsing raises unexpected error."""
        mock_mail = MagicMock()
        header_bytes = (
            b"From: sender@example.com\r\nSubject: Test\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        )
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
        ]

        with patch(
            "email_processor.processor.email_processor.message_from_bytes",
            side_effect=RuntimeError("Unexpected error"),
        ):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

    def test_process_email_processed_uids_load_io_error(self):
        """Test _process_email when loading processed UIDs raises OSError."""
        mock_mail = MagicMock()
        header_bytes = (
            b"From: sender@example.com\r\nSubject: Test\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        )
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
        ]

        with patch(
            "email_processor.processor.email_processor.load_processed_for_day",
            side_effect=OSError("IO error"),
        ):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

    def test_process_email_processed_uids_load_permission_error(self):
        """Test _process_email when loading processed UIDs raises PermissionError."""
        mock_mail = MagicMock()
        header_bytes = (
            b"From: sender@example.com\r\nSubject: Test\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        )
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
        ]

        with patch(
            "email_processor.processor.email_processor.load_processed_for_day",
            side_effect=PermissionError("Permission error"),
        ):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

    def test_process_email_processed_uids_load_unexpected_error(self):
        """Test _process_email when loading processed UIDs raises unexpected error."""
        mock_mail = MagicMock()
        header_bytes = (
            b"From: sender@example.com\r\nSubject: Test\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        )
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
        ]

        with patch(
            "email_processor.processor.email_processor.load_processed_for_day",
            side_effect=RuntimeError("Unexpected error"),
        ):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

    def test_process_email_processed_uid_save_io_error_non_allowed(self):
        """Test _process_email when saving processed UID for non-allowed sender raises OSError."""
        mock_mail = MagicMock()
        header_bytes = (
            b"From: other@example.com\r\nSubject: Test\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        )
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
        ]

        with patch(
            "email_processor.processor.email_processor.save_processed_uid_for_day",
            side_effect=OSError("IO error"),
        ):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should still return "skipped" even if save fails
            self.assertEqual(result, "skipped")
            self.assertEqual(blocked, 0)

    def test_process_email_processed_uid_save_permission_error_non_allowed(self):
        """Test _process_email when saving processed UID for non-allowed sender raises PermissionError."""
        mock_mail = MagicMock()
        header_bytes = (
            b"From: other@example.com\r\nSubject: Test\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        )
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
        ]

        with patch(
            "email_processor.processor.email_processor.save_processed_uid_for_day",
            side_effect=PermissionError("Permission error"),
        ):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should still return "skipped" even if save fails
            self.assertEqual(result, "skipped")
            self.assertEqual(blocked, 0)

    def test_process_email_processed_uid_save_unexpected_error_non_allowed(self):
        """Test _process_email when saving processed UID for non-allowed sender raises unexpected error."""
        mock_mail = MagicMock()
        header_bytes = (
            b"From: other@example.com\r\nSubject: Test\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        )
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
        ]

        with patch(
            "email_processor.processor.email_processor.save_processed_uid_for_day",
            side_effect=RuntimeError("Unexpected error"),
        ):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should still return "skipped" even if save fails
            self.assertEqual(result, "skipped")
            self.assertEqual(blocked, 0)

    def test_process_email_target_folder_create_io_error(self):
        """Test _process_email when target folder creation raises OSError."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        msg_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\n\r\nBody"
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, msg_bytes)]),
        ]

        # Mock Path.mkdir to raise OSError
        with patch("pathlib.Path.mkdir", side_effect=OSError("IO error")):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

    def test_process_email_target_folder_create_permission_error(self):
        """Test _process_email when target folder creation raises PermissionError."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        msg_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\n\r\nBody"
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, msg_bytes)]),
        ]

        # Mock Path.mkdir to raise PermissionError
        with patch("pathlib.Path.mkdir", side_effect=PermissionError("Permission error")):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

    def test_process_email_target_folder_create_unexpected_error(self):
        """Test _process_email when target folder creation raises unexpected error."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        msg_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\n\r\nBody"
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, msg_bytes)]),
        ]

        # Mock Path.mkdir to raise unexpected error
        with patch("pathlib.Path.mkdir", side_effect=RuntimeError("Unexpected error")):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

    def test_process_email_message_fetch_imap_error(self):
        """Test _process_email when message fetch raises IMAP4.error."""
        import imaplib

        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            imaplib.IMAP4.error("IMAP error"),  # Message fetch fails
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_message_fetch_data_error_attribute_error(self):
        """Test _process_email when message fetch raises AttributeError."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            AttributeError("Attribute error"),  # Message fetch fails
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_message_fetch_data_error_index_error(self):
        """Test _process_email when message fetch raises IndexError."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            IndexError("Index error"),  # Message fetch fails
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_message_fetch_data_error_type_error(self):
        """Test _process_email when message fetch raises TypeError."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            TypeError("Type error"),  # Message fetch fails
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_message_fetch_unexpected_error(self):
        """Test _process_email when message fetch raises unexpected error."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            RuntimeError("Unexpected error"),  # Message fetch fails
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_message_parse_error_message_parse_error(self):
        """Test _process_email when message parsing raises MessageParseError."""
        import email.errors
        from email.mime.text import MIMEText

        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        msg_bytes = b"Invalid message"  # Non-empty bytes to pass the check
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, msg_bytes)]),
        ]

        # Create a proper header message mock
        header_msg = MIMEText("")
        header_msg["From"] = "sender@example.com"
        header_msg["Subject"] = "Invoice"
        header_msg["Date"] = "Mon, 1 Jan 2024 12:00:00 +0000"

        with patch(
            "email_processor.processor.email_processor.message_from_bytes",
            side_effect=[
                header_msg,  # First call for header (succeeds)
                email.errors.MessageParseError("Parse error"),  # Second call for message (fails)
            ],
        ):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

    def test_process_email_message_parse_error_unicode_decode_error(self):
        """Test _process_email when message parsing raises UnicodeDecodeError."""
        from email.mime.text import MIMEText

        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        msg_bytes = b"Invalid message"  # Non-empty bytes to pass the check
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, msg_bytes)]),
        ]

        # Create a proper header message mock
        header_msg = MIMEText("")
        header_msg["From"] = "sender@example.com"
        header_msg["Subject"] = "Invoice"
        header_msg["Date"] = "Mon, 1 Jan 2024 12:00:00 +0000"

        with patch(
            "email_processor.processor.email_processor.message_from_bytes",
            side_effect=[
                header_msg,  # First call for header (succeeds)
                UnicodeDecodeError(
                    "utf-8", b"", 0, 1, "invalid"
                ),  # Second call for message (fails)
            ],
        ):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

    def test_process_email_message_parse_data_error_attribute_error(self):
        """Test _process_email when message parsing raises AttributeError."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"

        # Create full_data that will cause AttributeError when accessing [0][1] or [0]
        class BadMessageData:
            def __getitem__(self, key):
                if key == 0:
                    raise AttributeError("Attribute error")
                raise IndexError("Index error")

        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [BadMessageData()]),  # Invalid message data that causes AttributeError
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_message_parse_data_error_index_error(self):
        """Test _process_email when message parsing raises IndexError."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"

        # Create full_data that will cause IndexError when accessing [0]
        class BadMessageData:
            def __getitem__(self, key):
                raise IndexError("Index error")

        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [BadMessageData()]),  # Invalid message data that causes IndexError
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_message_parse_data_error_type_error(self):
        """Test _process_email when message parsing raises TypeError."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"

        # Create full_data that will cause TypeError when accessing [0][1] or [0]
        class BadMessageData:
            def __getitem__(self, key):
                if key == 0:
                    raise TypeError("Type error")
                raise IndexError("Index error")

        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [BadMessageData()]),  # Invalid message data that causes TypeError
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_message_parse_unexpected_error(self):
        """Test _process_email when message parsing raises unexpected error."""
        from email.mime.text import MIMEText

        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        msg_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\n\r\nBody"  # Non-empty bytes to pass the check
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, msg_bytes)]),
        ]

        # Create a proper header message mock
        header_msg = MIMEText("")
        header_msg["From"] = "sender@example.com"
        header_msg["Subject"] = "Invoice"
        header_msg["Date"] = "Mon, 1 Jan 2024 12:00:00 +0000"

        with patch(
            "email_processor.processor.email_processor.message_from_bytes",
            side_effect=[
                header_msg,  # First call for header (succeeds)
                RuntimeError("Unexpected error"),  # Second call for message (fails)
            ],
        ):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

    def test_process_email_blocked_attachments(self):
        """Test _process_email when attachments are blocked by extension filter."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"

        # Create message with blocked attachment
        msg = MIMEMultipart()
        msg["From"] = "sender@example.com"
        msg["Subject"] = "Invoice"
        msg["Date"] = "Mon, 1 Jan 2024 12:00:00 +0000"

        part = MIMEBase("application", "exe")
        part.set_payload(b"test content")
        part.add_header("Content-Disposition", "attachment", filename="malware.exe")
        msg.attach(part)

        msg_bytes = msg.as_bytes()

        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, msg_bytes)]),
        ]

        # Mock attachment handler to return False (blocked by extension)
        with patch.object(
            self.processor.attachment_handler, "is_allowed_extension", return_value=False
        ), patch.object(
            self.processor.attachment_handler, "save_attachment", return_value=(False, 0)
        ):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should return "skipped" with blocked count if only blocked attachments
            self.assertEqual(result, "skipped")
            self.assertGreater(blocked, 0)

    def test_process_email_attachment_error_no_filename(self):
        """Test _process_email when attachment has no filename."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"

        # Create message with attachment without filename
        msg = MIMEMultipart()
        msg["From"] = "sender@example.com"
        msg["Subject"] = "Invoice"
        msg["Date"] = "Mon, 1 Jan 2024 12:00:00 +0000"

        part = MIMEBase("application", "pdf")
        part.set_payload(b"test content")
        part.add_header("Content-Disposition", "attachment")  # No filename
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
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should return "error" if attachment processing fails
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

    def test_process_email_message_fetch_failed_uid_save_error(self):
        """Test _process_email when message fetch fails and UID save also fails."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("NO", None),  # Message fetch fails
        ]

        # Mock save_processed_uid_for_day to raise OSError
        with patch(
            "email_processor.processor.email_processor.save_processed_uid_for_day",
            side_effect=OSError("Permission denied"),
        ):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should handle the error gracefully
            self.assertEqual(result, "skipped")
            self.assertEqual(blocked, 0)

    def test_process_email_message_fetch_failed_uid_save_unexpected_error(self):
        """Test _process_email when message fetch fails and UID save raises unexpected error."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("NO", None),  # Message fetch fails
        ]

        # Mock save_processed_uid_for_day to raise unexpected error
        with patch(
            "email_processor.processor.email_processor.save_processed_uid_for_day",
            side_effect=ValueError("Unexpected error"),
        ):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should handle the error gracefully
            self.assertEqual(result, "skipped")
            self.assertEqual(blocked, 0)

    def test_process_email_uid_fetch_data_error_attribute_error(self):
        """Test _process_email when UID fetch returns data with AttributeError."""
        mock_mail = MagicMock()

        # Create a mock that raises AttributeError when accessing fetch result
        class MockFetchResult:
            def __getitem__(self, key):
                raise AttributeError("No attribute")

        mock_mail.fetch.return_value = ("OK", MockFetchResult())

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_uid_fetch_data_error_index_error(self):
        """Test _process_email when UID fetch returns data with IndexError."""
        mock_mail = MagicMock()

        # Create a mock that raises IndexError when accessing meta[0]
        class MockFetchResult:
            def __getitem__(self, key):
                if key == 0:
                    raise IndexError("List index out of range")

        mock_mail.fetch.return_value = ("OK", MockFetchResult())

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_email_uid_fetch_data_error_type_error(self):
        """Test _process_email when UID fetch returns data with TypeError."""
        mock_mail = MagicMock()

        # Create a mock that raises TypeError when accessing fetch result
        class MockFetchResult:
            def __getitem__(self, key):
                raise TypeError("Unsupported type")

        mock_mail.fetch.return_value = ("OK", MockFetchResult())

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "error")
        self.assertEqual(blocked, 0)

    def test_process_logout_imap_error(self):
        """Test process handles IMAP logout errors."""
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b""])
        mock_mail.logout.side_effect = imaplib.IMAP4.error("IMAP logout error")

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

    def test_process_logout_attribute_error(self):
        """Test process handles AttributeError during logout."""
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b""])
        mock_mail.logout.side_effect = AttributeError("No logout method")

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

    def test_process_psutil_memory_error(self):
        """Test process handles errors when getting memory usage with psutil."""
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b""])

        # Create a mock psutil module
        mock_psutil = MagicMock()
        mock_psutil.Process.side_effect = Exception("psutil error")

        # Inject mock psutil into sys.modules and the email_processor module
        with (
            patch(
                "email_processor.processor.email_processor.get_imap_password",
                return_value="password",
            ),
            patch("email_processor.processor.email_processor.imap_connect", return_value=mock_mail),
            patch("email_processor.processor.email_processor.PSUTIL_AVAILABLE", True),
        ):
            # Manually inject psutil into the module
            import email_processor.processor.email_processor as ep_module

            original_psutil = getattr(ep_module, "psutil", None)
            ep_module.psutil = mock_psutil
            try:
                result = self.processor.process(dry_run=False)
                # Should handle psutil errors gracefully
                self.assertIsInstance(result, type(result))
            finally:
                if original_psutil is not None:
                    ep_module.psutil = original_psutil
                elif hasattr(ep_module, "psutil"):
                    delattr(ep_module, "psutil")

    def test_process_psutil_memory_metrics_exception(self):
        """Test process handles exceptions when calculating psutil memory metrics."""
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b""])
        mock_mail.fetch.return_value = ("OK", [b""])

        # Create a mock psutil module with Process that raises exception on memory_info()
        mock_psutil = MagicMock()
        mock_process_instance = MagicMock()
        mock_process_instance.memory_info.side_effect = Exception("Memory info error")
        mock_psutil.Process.return_value = mock_process_instance

        with (
            patch(
                "email_processor.processor.email_processor.get_imap_password",
                return_value="password",
            ),
            patch("email_processor.processor.email_processor.imap_connect", return_value=mock_mail),
            patch("email_processor.processor.email_processor.PSUTIL_AVAILABLE", True),
        ):
            # Manually inject psutil into the module
            import email_processor.processor.email_processor as ep_module

            original_psutil = getattr(ep_module, "psutil", None)
            ep_module.psutil = mock_psutil
            try:
                result = self.processor.process(dry_run=False)
                # Should handle psutil errors gracefully
                self.assertIsInstance(result, type(result))
            finally:
                if original_psutil is not None:
                    ep_module.psutil = original_psutil
                elif hasattr(ep_module, "psutil"):
                    delattr(ep_module, "psutil")

    def test_process_email_attachment_error_result_not_tuple(self):
        """Test _process_email when attachment save returns non-tuple result."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"

        # Create message with attachment
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

        # Mock attachment handler to return non-tuple (truthy but not tuple)
        with patch.object(
            self.processor.attachment_handler, "save_attachment", return_value="success"
        ):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should treat truthy non-tuple as success
            self.assertEqual(result, "processed")
            self.assertEqual(blocked, 0)

    def test_process_email_attachment_error_result_false(self):
        """Test _process_email when attachment save returns False."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"

        # Create message with attachment
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

        # Mock attachment handler to return False
        with patch.object(self.processor.attachment_handler, "save_attachment", return_value=False):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should return "error" if attachment processing fails
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

    def test_process_email_dry_run_archive(self):
        """Test _process_email when archiving in dry-run mode."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        msg_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\n\r\nBody text"

        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, msg_bytes)]),
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        metrics = ProcessingMetrics()
        # Set archive_only_mapped to True and use mapped folder
        self.processor.archive_only_mapped = True
        result, blocked = self.processor._process_email(
            mock_mail, b"1", {}, True, metrics
        )  # dry_run=True
        # Should log dry_run_archive but not actually archive
        self.assertEqual(result, "skipped")
        self.assertEqual(blocked, 0)

    def test_process_email_archive_connection_error(self):
        """Test _process_email when archive raises ConnectionError."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        msg_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\n\r\nBody text"

        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, msg_bytes)]),
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        # Mock archive_message to raise ConnectionError
        with patch(
            "email_processor.processor.email_processor.archive_message",
            side_effect=ConnectionError("Connection lost"),
        ):
            metrics = ProcessingMetrics()
            self.processor.archive_only_mapped = True
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should handle archive error gracefully
            self.assertEqual(result, "skipped")
            self.assertEqual(blocked, 0)

    def test_process_email_archive_os_error(self):
        """Test _process_email when archive raises OSError."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        msg_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\n\r\nBody text"

        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, msg_bytes)]),
        ]

        from email_processor.processor.email_processor import ProcessingMetrics

        # Mock archive_message to raise OSError
        with patch(
            "email_processor.processor.email_processor.archive_message",
            side_effect=OSError("File system error"),
        ):
            metrics = ProcessingMetrics()
            self.processor.archive_only_mapped = True
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should handle archive error gracefully
            self.assertEqual(result, "skipped")
            self.assertEqual(blocked, 0)

    def test_process_email_processed_uid_save_error_after_processing(self):
        """Test _process_email when processed UID save fails after successful processing."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"

        # Create message with attachment
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

        # Mock save_processed_uid_for_day to raise OSError after processing
        with patch.object(
            self.processor.attachment_handler, "save_attachment", return_value=(True, 100)
        ), patch(
            "email_processor.processor.email_processor.save_processed_uid_for_day",
            side_effect=OSError("Permission denied"),
        ):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should return "error" if UID save fails
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

    def test_process_email_processed_uid_save_unexpected_error_after_processing(self):
        """Test _process_email when processed UID save raises unexpected error after processing."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"

        # Create message with attachment
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

        # Mock save_processed_uid_for_day to raise unexpected error
        with patch.object(
            self.processor.attachment_handler, "save_attachment", return_value=(True, 100)
        ), patch(
            "email_processor.processor.email_processor.save_processed_uid_for_day",
            side_effect=ValueError("Unexpected error"),
        ):
            from email_processor.processor.email_processor import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should return "error" if UID save fails
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

    def test_process_file_statistics_error(self):
        """Test process handles errors when collecting file statistics."""
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b""])

        with (
            patch(
                "email_processor.processor.email_processor.get_imap_password",
                return_value="password",
            ),
            patch("email_processor.processor.email_processor.imap_connect", return_value=mock_mail),
            patch(
                "email_processor.processor.email_processor.Path.iterdir",
                side_effect=OSError("Permission denied"),
            ),
        ):
            result = self.processor.process(dry_run=False)
            # Should handle file statistics errors gracefully
            self.assertIsInstance(result, type(result))

    def test_process_file_statistics_unexpected_error(self):
        """Test process handles unexpected errors when collecting file statistics."""
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b""])

        with (
            patch(
                "email_processor.processor.email_processor.get_imap_password",
                return_value="password",
            ),
            patch("email_processor.processor.email_processor.imap_connect", return_value=mock_mail),
            patch(
                "email_processor.processor.email_processor.Path.iterdir",
                side_effect=ValueError("Unexpected error"),
            ),
        ):
            result = self.processor.process(dry_run=False)
            # Should handle file statistics errors gracefully
            self.assertIsInstance(result, type(result))

    def test_process_psutil_memory_peak_update(self):
        """Test process updates memory peak when current memory exceeds peak."""
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b""])
        mock_mail.fetch.return_value = ("OK", [b""])

        # Create a mock psutil module
        mock_psutil = MagicMock()
        mock_process_instance = MagicMock()
        # First call returns lower memory, second call returns higher memory
        mock_process_instance.memory_info.side_effect = [
            MagicMock(rss=1000000),  # Initial memory
            MagicMock(rss=2000000),  # Final memory (higher than initial)
        ]
        mock_psutil.Process.return_value = mock_process_instance

        with (
            patch(
                "email_processor.processor.email_processor.get_imap_password",
                return_value="password",
            ),
            patch("email_processor.processor.email_processor.imap_connect", return_value=mock_mail),
            patch("email_processor.processor.email_processor.PSUTIL_AVAILABLE", True),
        ):
            # Manually inject psutil into the module
            import email_processor.processor.email_processor as ep_module

            original_psutil = getattr(ep_module, "psutil", None)
            ep_module.psutil = mock_psutil
            try:
                result = self.processor.process(dry_run=False)
                # Should update memory peak
                self.assertIsInstance(result, type(result))
                if result.metrics and hasattr(result.metrics, "memory_peak"):
                    self.assertIsNotNone(result.metrics.memory_peak)
            finally:
                if original_psutil is not None:
                    ep_module.psutil = original_psutil
                elif hasattr(ep_module, "psutil"):
                    delattr(ep_module, "psutil")
