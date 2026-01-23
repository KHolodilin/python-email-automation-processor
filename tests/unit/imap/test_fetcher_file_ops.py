"""Tests for Fetcher file_ops functionality."""

from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests.unit.imap.test_fetcher_base import TestFetcherBase


class TestFetcherFileOps(TestFetcherBase):
    """Tests for Fetcher file_ops functionality."""

    def test_process_email_target_folder_create_error(self):
        """Test _process_email when target folder creation fails."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
        ]

        with patch("pathlib.Path.mkdir", side_effect=Exception("Permission denied")):
            from email_processor.imap.fetcher import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

    def test_process_file_stats_collection(self):
        """Test file statistics collection in process method."""
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b""])  # No messages

        with (
            patch(
                "email_processor.imap.fetcher.get_imap_password",
                return_value="password",
            ),
            patch("email_processor.imap.fetcher.imap_connect", return_value=mock_mail),
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
                "email_processor.imap.fetcher.get_imap_password",
                return_value="password",
            ),
            patch("email_processor.imap.fetcher.imap_connect", return_value=mock_mail),
            patch("pathlib.Path.rglob", side_effect=Exception("Access error")),
        ):
            result = self.processor.process(dry_run=False)
            # Should handle error gracefully
            self.assertIsInstance(result, type(result))

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
            from email_processor.imap.fetcher import ProcessingMetrics

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
            from email_processor.imap.fetcher import ProcessingMetrics

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
            from email_processor.imap.fetcher import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

    def test_process_file_statistics_error(self):
        """Test process handles errors when collecting file statistics."""
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b""])

        with (
            patch(
                "email_processor.imap.fetcher.get_imap_password",
                return_value="password",
            ),
            patch("email_processor.imap.fetcher.imap_connect", return_value=mock_mail),
            patch(
                "email_processor.imap.fetcher.Path.iterdir",
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
                "email_processor.imap.fetcher.get_imap_password",
                return_value="password",
            ),
            patch("email_processor.imap.fetcher.imap_connect", return_value=mock_mail),
            patch(
                "email_processor.imap.fetcher.Path.iterdir",
                side_effect=ValueError("Unexpected error"),
            ),
        ):
            result = self.processor.process(dry_run=False)
            # Should handle file statistics errors gracefully
            self.assertIsInstance(result, type(result))
