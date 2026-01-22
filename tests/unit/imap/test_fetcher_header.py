"""Tests for Fetcher header functionality."""

from unittest.mock import MagicMock, patch

from tests.unit.imap.test_fetcher_base import TestFetcherBase


class TestFetcherHeader(TestFetcherBase):
    """Tests for Fetcher header functionality."""

    def test_process_email_header_empty(self):
        """Test _process_email when header is empty."""
        mock_mail = MagicMock()
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, b"")]),  # Empty header
        ]

        from email_processor.imap.fetcher import ProcessingMetrics

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
            "email_processor.imap.fetcher.message_from_bytes",
            side_effect=Exception("Parse error"),
        ):
            from email_processor.imap.fetcher import ProcessingMetrics

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

        from email_processor.imap.fetcher import ProcessingMetrics

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

        from email_processor.imap.fetcher import ProcessingMetrics

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

        from email_processor.imap.fetcher import ProcessingMetrics

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

        from email_processor.imap.fetcher import ProcessingMetrics

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

        from email_processor.imap.fetcher import ProcessingMetrics

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
            "email_processor.imap.fetcher.message_from_bytes",
            side_effect=email.errors.MessageParseError("Parse error"),
        ):
            from email_processor.imap.fetcher import ProcessingMetrics

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
            "email_processor.imap.fetcher.message_from_bytes",
            side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "invalid"),
        ):
            from email_processor.imap.fetcher import ProcessingMetrics

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

        from email_processor.imap.fetcher import ProcessingMetrics

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

        from email_processor.imap.fetcher import ProcessingMetrics

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

        from email_processor.imap.fetcher import ProcessingMetrics

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
            "email_processor.imap.fetcher.message_from_bytes",
            side_effect=RuntimeError("Unexpected error"),
        ):
            from email_processor.imap.fetcher import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)
