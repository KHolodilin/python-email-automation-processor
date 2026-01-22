"""Tests for Fetcher attachment functionality."""

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from unittest.mock import MagicMock, patch

from tests.unit.imap.test_fetcher_base import TestFetcherBase


class TestFetcherAttachment(TestFetcherBase):
    """Tests for Fetcher attachment functionality."""

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

        from email_processor.imap.fetcher import ProcessingMetrics

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
            from email_processor.imap.fetcher import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should return "error" if attachment processing fails
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
        with (
            patch.object(
                self.processor.attachment_handler, "is_allowed_extension", return_value=False
            ),
            patch.object(
                self.processor.attachment_handler, "save_attachment", return_value=(False, 0)
            ),
        ):
            from email_processor.imap.fetcher import ProcessingMetrics

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
            from email_processor.imap.fetcher import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should return "error" if attachment processing fails
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

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
            from email_processor.imap.fetcher import ProcessingMetrics

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
            from email_processor.imap.fetcher import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should return "error" if attachment processing fails
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)
