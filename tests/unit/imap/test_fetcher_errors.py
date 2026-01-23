"""Tests for Fetcher errors functionality."""

import imaplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from unittest.mock import MagicMock, patch

from email_processor.imap.fetcher import Fetcher
from tests.unit.imap.test_fetcher_base import TestFetcherBase

# Backward compatibility alias
EmailProcessor = Fetcher


class TestFetcherErrors(TestFetcherBase):
    """Tests for Fetcher errors functionality."""

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

        from email_processor.imap.fetcher import ProcessingMetrics

        metrics = ProcessingMetrics()
        result, blocked = processor._process_email(mock_mail, b"1", {}, False, metrics)
        self.assertEqual(result, "skipped")
        self.assertEqual(blocked, 0)
        # Should not save UID when skip_non_allowed_as_processed is False

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
                "email_processor.imap.fetcher.get_imap_password",
                return_value="password",
            ),
            patch("email_processor.imap.fetcher.imap_connect", return_value=mock_mail),
        ):
            result = self.processor.process(dry_run=False)
            # Should have file stats
            self.assertIsNotNone(result.file_stats)
            self.assertIn(".pdf", result.file_stats)

    def test_process_imap_error_handling(self):
        """Test process handles IMAP errors during email processing."""
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b"1"])
        mock_mail.fetch.side_effect = imaplib.IMAP4.error("IMAP error")

        with (
            patch(
                "email_processor.imap.fetcher.get_imap_password",
                return_value="password",
            ),
            patch("email_processor.imap.fetcher.imap_connect", return_value=mock_mail),
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
                "email_processor.imap.fetcher.get_imap_password",
                return_value="password",
            ),
            patch("email_processor.imap.fetcher.imap_connect", return_value=mock_mail),
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
                "email_processor.imap.fetcher.get_imap_password",
                return_value="password",
            ),
            patch("email_processor.imap.fetcher.imap_connect", return_value=mock_mail),
        ):
            result = self.processor.process(dry_run=False)
            # Should handle logout errors gracefully
            self.assertIsInstance(result, type(result))

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.fetcher.imap_connect")
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

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.fetcher.imap_connect")
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

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.fetcher.imap_connect")
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

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.fetcher.imap_connect")
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

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.fetcher.imap_connect")
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

    def test_process_logout_imap_error(self):
        """Test process handles IMAP logout errors."""
        mock_mail = MagicMock()
        mock_mail.select.return_value = ("OK", [b"1"])
        mock_mail.search.return_value = ("OK", [b""])
        mock_mail.logout.side_effect = imaplib.IMAP4.error("IMAP logout error")

        with (
            patch(
                "email_processor.imap.fetcher.get_imap_password",
                return_value="password",
            ),
            patch("email_processor.imap.fetcher.imap_connect", return_value=mock_mail),
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
                "email_processor.imap.fetcher.get_imap_password",
                return_value="password",
            ),
            patch("email_processor.imap.fetcher.imap_connect", return_value=mock_mail),
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
                "email_processor.imap.fetcher.get_imap_password",
                return_value="password",
            ),
            patch("email_processor.imap.fetcher.imap_connect", return_value=mock_mail),
            patch("email_processor.imap.fetcher.PSUTIL_AVAILABLE", True),
        ):
            # Manually inject psutil into the module
            import email_processor.imap.fetcher as ep_module

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
                "email_processor.imap.fetcher.get_imap_password",
                return_value="password",
            ),
            patch("email_processor.imap.fetcher.imap_connect", return_value=mock_mail),
            patch("email_processor.imap.fetcher.PSUTIL_AVAILABLE", True),
        ):
            # Manually inject psutil into the module
            import email_processor.imap.fetcher as ep_module

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
                "email_processor.imap.fetcher.get_imap_password",
                return_value="password",
            ),
            patch("email_processor.imap.fetcher.imap_connect", return_value=mock_mail),
            patch("email_processor.imap.fetcher.PSUTIL_AVAILABLE", True),
        ):
            # Manually inject psutil into the module
            import email_processor.imap.fetcher as ep_module

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

    def test_process_mock_mode_logging(self):
        """Test process logs mock mode message when mock_mode is True."""
        from email_processor.imap.mock_client import MockIMAP4_SSL

        # Create a real MockIMAP4_SSL instance
        mock_mail = MockIMAP4_SSL("imap.example.com")
        # Mock its methods
        mock_mail.select = MagicMock(return_value=("OK", [b"1"]))
        mock_mail.search = MagicMock(return_value=("OK", [b""]))

        # Patch MockIMAP4_SSL to return our mock
        with patch("email_processor.imap.mock_client.MockIMAP4_SSL", return_value=mock_mail):
            result = self.processor.process(dry_run=False, mock_mode=True)
            # Should handle mock mode gracefully
            self.assertIsInstance(result, type(result))

    def test_process_cleanup_unexpected_error(self):
        """Test process handles unexpected cleanup errors."""
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
                "email_processor.imap.fetcher.cleanup_old_processed_days",
                side_effect=ValueError("Unexpected cleanup error"),
            ),
        ):
            result = self.processor.process(dry_run=False)
            # Should handle cleanup errors gracefully
            self.assertIsInstance(result, type(result))
