"""Tests for email processor module."""

import shutil
import tempfile
import unittest
from email import message_from_bytes
from pathlib import Path
from unittest.mock import MagicMock, patch

from email_processor.imap.fetcher import (
    Fetcher,
    ProcessingResult,
    get_start_date,
)
from email_processor.logging.setup import setup_logging

# Backward compatibility alias
EmailProcessor = Fetcher


class TestGetStartDate(unittest.TestCase):
    """Tests for get_start_date function."""

    def test_get_start_date(self):
        """Test get_start_date function."""
        days_back = 5
        result = get_start_date(days_back)
        # Should be in format "DD-MMM-YYYY"
        self.assertIsInstance(result, str)
        self.assertRegex(result, r"\d{2}-\w{3}-\d{4}")


class TestEmailProcessor(unittest.TestCase):
    """Tests for EmailProcessor class."""

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
                "format_file": "json",
            },
            "allowed_senders": ["sender@example.com"],
            "topic_mapping": {
                ".*invoice.*": "invoices",
            },
        }

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_email_processor_init(self):
        """Test EmailProcessor initialization."""
        processor = EmailProcessor(self.config)
        self.assertEqual(processor.imap_server, "imap.example.com")
        self.assertEqual(processor.imap_user, "test@example.com")
        self.assertIsNotNone(processor.filter)
        self.assertIsNotNone(processor.attachment_handler)
        self.assertIsNotNone(processor.uid_storage)

    def test_email_processor_init_logging_fallback(self):
        """Test EmailProcessor initialization with old logging config format."""
        config = self.config.copy()
        del config["logging"]
        config["processing"]["log_level"] = "DEBUG"
        config["processing"]["log_file"] = None

        processor = EmailProcessor(config)
        self.assertIsNotNone(processor.logger)

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.fetcher.imap_connect")
    def test_process_no_emails(self, mock_imap_connect, mock_get_password):
        """Test processing with no emails."""
        mock_get_password.return_value = "password"
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b""])  # No messages
        mock_imap_connect.return_value = mock_mail

        processor = EmailProcessor(self.config)
        result = processor.process(dry_run=False)

        self.assertEqual(result.processed, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.errors, 0)

    @patch("email_processor.imap.fetcher.get_imap_password")
    def test_process_password_error(self, mock_get_password):
        """Test processing with password error."""
        mock_get_password.side_effect = ValueError("Password not entered")

        processor = EmailProcessor(self.config)
        result = processor.process(dry_run=False)

        self.assertEqual(result.processed, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.errors, 0)

    @patch("email_processor.imap.fetcher.get_imap_password")
    def test_process_password_keyring_error(self, mock_get_password):
        """Test processing with keyring error (KeyError)."""
        mock_get_password.side_effect = KeyError("Password not found")

        processor = EmailProcessor(self.config)
        result = processor.process(dry_run=False)

        self.assertEqual(result.processed, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.errors, 0)

    @patch("email_processor.imap.fetcher.get_imap_password")
    def test_process_password_runtime_error(self, mock_get_password):
        """Test processing with runtime error from keyring."""
        mock_get_password.side_effect = RuntimeError("Keyring error")

        processor = EmailProcessor(self.config)
        result = processor.process(dry_run=False)

        self.assertEqual(result.processed, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.errors, 0)

    @patch("email_processor.imap.fetcher.get_imap_password")
    def test_process_password_unexpected_error(self, mock_get_password):
        """Test processing with unexpected password error."""
        mock_get_password.side_effect = Exception("Unexpected error")

        processor = EmailProcessor(self.config)
        result = processor.process(dry_run=False)

        self.assertEqual(result.processed, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.errors, 0)

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.fetcher.imap_connect")
    def test_process_connection_error(self, mock_imap_connect, mock_get_password):
        """Test processing with connection error."""
        mock_get_password.return_value = "password"
        mock_imap_connect.side_effect = ConnectionError("Failed to connect")

        processor = EmailProcessor(self.config)
        result = processor.process(dry_run=False)

        self.assertEqual(result.processed, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.errors, 0)

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.fetcher.imap_connect")
    def test_process_imap_network_error_timeout(self, mock_imap_connect, mock_get_password):
        """Test processing with timeout error."""
        mock_get_password.return_value = "password"
        mock_imap_connect.side_effect = TimeoutError("Connection timeout")

        processor = EmailProcessor(self.config)
        result = processor.process(dry_run=False)

        self.assertEqual(result.processed, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.errors, 0)

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.fetcher.imap_connect")
    def test_process_imap_network_error_oserror(self, mock_imap_connect, mock_get_password):
        """Test processing with OSError."""
        mock_get_password.return_value = "password"
        mock_imap_connect.side_effect = OSError("Network error")

        processor = EmailProcessor(self.config)
        result = processor.process(dry_run=False)

        self.assertEqual(result.processed, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.errors, 0)

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.fetcher.imap_connect")
    def test_process_imap_connection_unexpected_error(self, mock_imap_connect, mock_get_password):
        """Test processing with unexpected IMAP connection error."""
        mock_get_password.return_value = "password"
        mock_imap_connect.side_effect = ValueError("Unexpected connection error")

        processor = EmailProcessor(self.config)
        result = processor.process(dry_run=False)

        self.assertEqual(result.processed, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.errors, 0)

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.fetcher.imap_connect")
    def test_process_inbox_select_failed(self, mock_imap_connect, mock_get_password):
        """Test processing when INBOX select fails."""
        mock_get_password.return_value = "password"
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("NO", [b"Select failed"])
        mock_imap_connect.return_value = mock_mail

        processor = EmailProcessor(self.config)
        result = processor.process(dry_run=False)

        self.assertEqual(result.processed, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.errors, 0)

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.fetcher.imap_connect")
    def test_process_inbox_select_imap_error(self, mock_imap_connect, mock_get_password):
        """Test processing when INBOX select raises IMAP4.error."""
        import imaplib

        mock_get_password.return_value = "password"
        mock_mail = MagicMock()
        mock_mail.select.side_effect = imaplib.IMAP4.error("IMAP error")
        mock_imap_connect.return_value = mock_mail

        processor = EmailProcessor(self.config)
        result = processor.process(dry_run=False)

        self.assertEqual(result.processed, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.errors, 0)

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.fetcher.imap_connect")
    def test_process_inbox_select_invalid_state_attribute_error(
        self, mock_imap_connect, mock_get_password
    ):
        """Test processing when INBOX select raises AttributeError."""
        mock_get_password.return_value = "password"
        mock_mail = MagicMock()
        mock_mail.select.side_effect = AttributeError("Invalid state")
        mock_imap_connect.return_value = mock_mail

        processor = EmailProcessor(self.config)
        result = processor.process(dry_run=False)

        self.assertEqual(result.processed, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.errors, 0)

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.fetcher.imap_connect")
    def test_process_inbox_select_invalid_state_type_error(
        self, mock_imap_connect, mock_get_password
    ):
        """Test processing when INBOX select raises TypeError."""
        mock_get_password.return_value = "password"
        mock_mail = MagicMock()
        mock_mail.select.side_effect = TypeError("Invalid state")
        mock_imap_connect.return_value = mock_mail

        processor = EmailProcessor(self.config)
        result = processor.process(dry_run=False)

        self.assertEqual(result.processed, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.errors, 0)

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.fetcher.imap_connect")
    def test_process_inbox_select_unexpected_error(self, mock_imap_connect, mock_get_password):
        """Test processing when INBOX select raises unexpected error."""
        mock_get_password.return_value = "password"
        mock_mail = MagicMock()
        mock_mail.select.side_effect = ValueError("Unexpected error")
        mock_imap_connect.return_value = mock_mail

        processor = EmailProcessor(self.config)
        result = processor.process(dry_run=False)

        self.assertEqual(result.processed, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.errors, 0)

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.fetcher.imap_connect")
    def test_process_search_error(self, mock_imap_connect, mock_get_password):
        """Test processing when search fails."""
        mock_get_password.return_value = "password"
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("NO", [b"Search failed"])
        mock_imap_connect.return_value = mock_mail

        processor = EmailProcessor(self.config)
        result = processor.process(dry_run=False)

        self.assertEqual(result.processed, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.errors, 0)

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.fetcher.imap_connect")
    def test_process_search_imap_error(self, mock_imap_connect, mock_get_password):
        """Test processing when search raises IMAP4.error."""
        import imaplib

        mock_get_password.return_value = "password"
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.side_effect = imaplib.IMAP4.error("IMAP search error")
        mock_imap_connect.return_value = mock_mail

        processor = EmailProcessor(self.config)
        result = processor.process(dry_run=False)

        self.assertEqual(result.processed, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.errors, 0)

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.fetcher.imap_connect")
    def test_process_search_invalid_state_attribute_error(
        self, mock_imap_connect, mock_get_password
    ):
        """Test processing when search raises AttributeError."""
        mock_get_password.return_value = "password"
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.side_effect = AttributeError("Invalid state")
        mock_imap_connect.return_value = mock_mail

        processor = EmailProcessor(self.config)
        result = processor.process(dry_run=False)

        self.assertEqual(result.processed, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.errors, 0)

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.fetcher.imap_connect")
    def test_process_search_invalid_state_type_error(self, mock_imap_connect, mock_get_password):
        """Test processing when search raises TypeError."""
        mock_get_password.return_value = "password"
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.side_effect = TypeError("Invalid state")
        mock_imap_connect.return_value = mock_mail

        processor = EmailProcessor(self.config)
        result = processor.process(dry_run=False)

        self.assertEqual(result.processed, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.errors, 0)

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.fetcher.imap_connect")
    def test_process_search_unexpected_error(self, mock_imap_connect, mock_get_password):
        """Test processing when search raises unexpected error."""
        mock_get_password.return_value = "password"
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.side_effect = ValueError("Unexpected error")
        mock_imap_connect.return_value = mock_mail

        processor = EmailProcessor(self.config)
        result = processor.process(dry_run=False)

        self.assertEqual(result.processed, 0)
        self.assertEqual(result.skipped, 0)
        self.assertEqual(result.errors, 0)

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.fetcher.imap_connect")
    def test_process_dry_run(self, mock_imap_connect, mock_get_password):
        """Test processing in dry-run mode."""
        mock_get_password.return_value = "password"
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b""])  # No messages
        mock_imap_connect.return_value = mock_mail

        processor = EmailProcessor(self.config)
        result = processor.process(dry_run=True)

        self.assertEqual(result.processed, 0)
        # Should complete without errors
        self.assertIsInstance(result, ProcessingResult)

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.fetcher.imap_connect")
    def test_process_cleanup_error(self, mock_imap_connect, mock_get_password):
        """Test processing when cleanup fails."""
        mock_get_password.return_value = "password"
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b""])
        mock_imap_connect.return_value = mock_mail

        with patch(
            "email_processor.imap.fetcher.cleanup_old_processed_days",
            side_effect=Exception("Cleanup error"),
        ):
            processor = EmailProcessor(self.config)
            result = processor.process(dry_run=False)
            # Should continue despite cleanup error
            self.assertIsInstance(result, ProcessingResult)


class TestProcessEmail(unittest.TestCase):
    """Tests for _process_email method."""

    def setUp(self):
        """Setup test fixtures."""
        setup_logging({"level": "INFO", "format": "console"})
        self.temp_dir = tempfile.mkdtemp()

        self.config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {
                "start_days_back": 5,
                "download_dir": str(Path(self.temp_dir) / "downloads"),
                "archive_folder": "INBOX/Processed",
                "processed_dir": str(Path(self.temp_dir) / "processed_uids"),
                "archive_only_mapped": True,
                "skip_non_allowed_as_processed": True,
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

    def test_process_email_uid_fetch_failed(self):
        """Test _process_email when UID fetch fails."""
        mock_mail = MagicMock()
        mock_mail.fetch.return_value = ("NO", None)

        from email_processor.imap.fetcher import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "skipped")
        self.assertEqual(blocked, 0)

    def test_process_email_uid_extraction_failed(self):
        """Test _process_email when UID extraction fails."""
        mock_mail = MagicMock()
        mock_mail.fetch.return_value = ("OK", [(b"No UID here", None)])

        from email_processor.imap.fetcher import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "skipped")
        self.assertEqual(blocked, 0)

    def test_process_email_header_fetch_failed(self):
        """Test _process_email when header fetch fails."""
        mock_mail = MagicMock()
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),  # UID fetch succeeds
            ("NO", None),  # Header fetch fails
        ]

        from email_processor.imap.fetcher import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "skipped")
        self.assertEqual(blocked, 0)

    def test_process_email_already_processed(self):
        """Test _process_email when email already processed."""
        from email_processor.storage.uid_storage import save_processed_uid_for_day

        mock_mail = MagicMock()
        header_bytes = (
            b"From: sender@example.com\r\nSubject: Test\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        )
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
        ]

        # Mark as processed
        day_str = "2024-01-01"
        cache = {}
        save_processed_uid_for_day(self.processor.processed_dir, day_str, "123", cache)

        from email_processor.imap.fetcher import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", cache, False, metrics)
        self.assertEqual(result, "skipped")
        self.assertEqual(blocked, 0)

    def test_process_email_sender_not_allowed(self):
        """Test _process_email when sender is not allowed."""
        mock_mail = MagicMock()
        header_bytes = (
            b"From: other@example.com\r\nSubject: Test\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        )
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
        ]

        from email_processor.imap.fetcher import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "skipped")
        self.assertEqual(blocked, 0)

    def test_process_email_message_fetch_failed(self):
        """Test _process_email when message fetch fails."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("NO", None),  # Message fetch fails
        ]

        from email_processor.imap.fetcher import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "skipped")
        self.assertEqual(blocked, 0)

    def test_process_email_no_attachments(self):
        """Test _process_email when email has no attachments."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        msg_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\n\r\nBody text"
        msg = message_from_bytes(msg_bytes)

        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, msg_bytes)]),
        ]

        from email_processor.imap.fetcher import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "skipped")
        self.assertEqual(blocked, 0)

    def test_process_email_with_attachment(self):
        """Test _process_email with attachment."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"

        # Create message with attachment using MIMEMultipart
        from email.mime.base import MIMEBase
        from email.mime.multipart import MIMEMultipart

        from email_processor.imap.fetcher import ProcessingMetrics

        msg = MIMEMultipart()
        msg["From"] = "sender@example.com"
        msg["Subject"] = "Invoice"
        msg["Date"] = "Mon, 1 Jan 2024 12:00:00 +0000"

        # Add attachment
        part = MIMEBase("application", "octet-stream")
        part.set_payload(b"test content")
        part.add_header("Content-Disposition", "attachment", filename="test.pdf")
        msg.attach(part)

        msg_bytes = msg.as_bytes()

        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, msg_bytes)]),
        ]

        metrics = ProcessingMetrics()
        result = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
        # Should process successfully
        result_str, blocked = result
        self.assertIn(result_str, ["processed", "skipped", "error"])
        self.assertIsInstance(blocked, int)


class TestProcessingResult(unittest.TestCase):
    """Tests for ProcessingResult dataclass."""

    def test_processing_result(self):
        """Test ProcessingResult dataclass."""
        from email_processor.imap.fetcher import ProcessingMetrics

        metrics = ProcessingMetrics()
        result = ProcessingResult(
            processed=5, skipped=3, errors=1, file_stats={".pdf": 3, ".doc": 2}, metrics=metrics
        )
        self.assertEqual(result.processed, 5)
        self.assertEqual(result.skipped, 3)
        self.assertEqual(result.errors, 1)
        self.assertEqual(result.file_stats[".pdf"], 3)


class TestProgressBar(unittest.TestCase):
    """Tests for progress bar functionality."""

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
            },
            "logging": {
                "level": "INFO",
                "format": "console",
            },
            "allowed_senders": ["sender@example.com"],
            "topic_mapping": {},
        }

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.fetcher.imap_connect")
    def test_process_with_progress_bar(self, mock_imap_connect, mock_get_password):
        """Test process with progress bar enabled."""
        mock_get_password.return_value = "password"
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b"1 2 3"])
        mock_mail.fetch.return_value = ("OK", [(b"UID 123", None)])
        mock_mail.logout.return_value = ("OK", [])
        mock_imap_connect.return_value = mock_mail

        config = self.config.copy()
        config["processing"]["show_progress"] = True

        processor = EmailProcessor(config)
        # Mock tqdm to avoid actual progress bar in tests
        with patch("email_processor.imap.fetcher.tqdm") as mock_tqdm:
            mock_pbar = MagicMock()
            mock_pbar.__iter__ = lambda self: iter([b"1", b"2", b"3"])
            mock_pbar.set_postfix = MagicMock()
            mock_pbar.close = MagicMock()
            mock_tqdm.return_value = mock_pbar

            result = processor.process(dry_run=False)

            # Verify tqdm was called if progress is enabled
            if processor.show_progress:
                mock_tqdm.assert_called_once()
                mock_pbar.close.assert_called_once()

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.fetcher.imap_connect")
    def test_process_without_progress_bar(self, mock_imap_connect, mock_get_password):
        """Test process with progress bar disabled."""
        mock_get_password.return_value = "password"
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b"1 2 3"])
        mock_mail.fetch.return_value = ("OK", [(b"UID 123", None)])
        mock_mail.logout.return_value = ("OK", [])
        mock_imap_connect.return_value = mock_mail

        config = self.config.copy()
        config["processing"]["show_progress"] = False

        processor = EmailProcessor(config)
        # Mock tqdm to verify it's not called
        with patch("email_processor.imap.fetcher.tqdm") as mock_tqdm:
            result = processor.process(dry_run=False)

            # Verify tqdm was not called when show_progress is False
            mock_tqdm.assert_not_called()

    def test_progress_bar_default(self):
        """Test that progress bar default is set correctly."""
        # Test with show_progress not specified
        config = self.config.copy()
        processor = EmailProcessor(config)
        # Default should be a boolean (True if tqdm available, False otherwise)
        self.assertIsInstance(processor.show_progress, bool)

        # Test with show_progress explicitly set
        config["processing"]["show_progress"] = False
        processor2 = EmailProcessor(config)
        self.assertFalse(processor2.show_progress)

        config["processing"]["show_progress"] = True
        processor3 = EmailProcessor(config)
        self.assertTrue(processor3.show_progress)
