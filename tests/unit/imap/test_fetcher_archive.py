"""Tests for Fetcher archive functionality."""

import imaplib
from unittest.mock import MagicMock, patch

from email_processor.imap.fetcher import Fetcher
from tests.unit.imap.test_fetcher_base import TestFetcherBase

# Backward compatibility alias
EmailProcessor = Fetcher


class TestFetcherArchive(TestFetcherBase):
    """Tests for Fetcher archive functionality."""

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
            "email_processor.imap.fetcher.archive_message",
            side_effect=Exception("Archive error"),
        ):
            from email_processor.imap.fetcher import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should still return "skipped" (no attachments)
            self.assertEqual(result, "skipped")
            self.assertEqual(blocked, 0)

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

        from email_processor.imap.fetcher import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = processor._process_email(mock_mail, b"1", {}, False, metrics)
        # Should not archive when archive_only_mapped is False and no mapped folder
        self.assertEqual(result, "skipped")
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

        from email_processor.imap.fetcher import ProcessingMetrics

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

        from email_processor.imap.fetcher import ProcessingMetrics

        # Mock archive_message to raise ConnectionError
        with patch(
            "email_processor.imap.fetcher.archive_message",
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

        from email_processor.imap.fetcher import ProcessingMetrics

        # Mock archive_message to raise OSError
        with patch(
            "email_processor.imap.fetcher.archive_message",
            side_effect=OSError("File system error"),
        ):
            metrics = ProcessingMetrics()
            self.processor.archive_only_mapped = True
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should handle archive error gracefully
            self.assertEqual(result, "skipped")
            self.assertEqual(blocked, 0)

    def test_process_email_archive_imap_error(self):
        """Test _process_email when archive raises IMAP4.error."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        msg_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\n\r\nBody text"

        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, msg_bytes)]),
        ]

        from email_processor.imap.fetcher import ProcessingMetrics

        # Mock archive_message to raise imaplib.IMAP4.error
        with patch(
            "email_processor.imap.fetcher.archive_message",
            side_effect=imaplib.IMAP4.error("IMAP archive error"),
        ):
            metrics = ProcessingMetrics()
            self.processor.archive_only_mapped = True
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should handle archive error gracefully
            self.assertEqual(result, "skipped")
            self.assertEqual(blocked, 0)
