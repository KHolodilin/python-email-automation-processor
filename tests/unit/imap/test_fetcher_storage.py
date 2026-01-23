"""Tests for Fetcher storage functionality."""

from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from unittest.mock import MagicMock, patch

from tests.unit.imap.test_fetcher_base import TestFetcherBase


class TestFetcherStorage(TestFetcherBase):
    """Tests for Fetcher storage functionality."""

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
            "email_processor.imap.fetcher.save_processed_uid_for_day",
            side_effect=Exception("Save error"),
        ):
            from email_processor.imap.fetcher import ProcessingMetrics

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
            "email_processor.imap.fetcher.load_processed_for_day",
            side_effect=OSError("IO error"),
        ):
            from email_processor.imap.fetcher import ProcessingMetrics

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
            "email_processor.imap.fetcher.load_processed_for_day",
            side_effect=PermissionError("Permission error"),
        ):
            from email_processor.imap.fetcher import ProcessingMetrics

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
            "email_processor.imap.fetcher.load_processed_for_day",
            side_effect=RuntimeError("Unexpected error"),
        ):
            from email_processor.imap.fetcher import ProcessingMetrics

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
            "email_processor.imap.fetcher.save_processed_uid_for_day",
            side_effect=OSError("IO error"),
        ):
            from email_processor.imap.fetcher import ProcessingMetrics

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
            "email_processor.imap.fetcher.save_processed_uid_for_day",
            side_effect=PermissionError("Permission error"),
        ):
            from email_processor.imap.fetcher import ProcessingMetrics

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
            "email_processor.imap.fetcher.save_processed_uid_for_day",
            side_effect=RuntimeError("Unexpected error"),
        ):
            from email_processor.imap.fetcher import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should still return "skipped" even if save fails
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
        with (
            patch.object(
                self.processor.attachment_handler, "save_attachment", return_value=(True, 100)
            ),
            patch(
                "email_processor.imap.fetcher.save_processed_uid_for_day",
                side_effect=OSError("Permission denied"),
            ),
        ):
            from email_processor.imap.fetcher import ProcessingMetrics

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
        with (
            patch.object(
                self.processor.attachment_handler, "save_attachment", return_value=(True, 100)
            ),
            patch(
                "email_processor.imap.fetcher.save_processed_uid_for_day",
                side_effect=ValueError("Unexpected error"),
            ),
        ):
            from email_processor.imap.fetcher import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should return "error" if UID save fails
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)
