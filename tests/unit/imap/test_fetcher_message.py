"""Tests for Fetcher message functionality."""

from email.mime.text import MIMEText
from unittest.mock import MagicMock, patch

from tests.unit.imap.test_fetcher_base import TestFetcherBase


class TestFetcherMessage(TestFetcherBase):
    """Tests for Fetcher message functionality."""

    def test_process_email_message_body_empty(self):
        """Test _process_email when message body is empty."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, b"")]),  # Empty message body
        ]

        from email_processor.imap.fetcher import ProcessingMetrics

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
            "email_processor.imap.fetcher.message_from_bytes",
            side_effect=Exception("Parse error"),
        ):
            from email_processor.imap.fetcher import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
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
            "email_processor.imap.fetcher.message_from_bytes",
            side_effect=[
                mock_header_msg,  # First call for header
                mock_full_msg,  # Second call for full message
            ],
        ):
            from email_processor.imap.fetcher import ProcessingMetrics

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

        from email_processor.imap.fetcher import ProcessingMetrics

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

        from email_processor.imap.fetcher import ProcessingMetrics

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

        from email_processor.imap.fetcher import ProcessingMetrics

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

        from email_processor.imap.fetcher import ProcessingMetrics

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

        from email_processor.imap.fetcher import ProcessingMetrics

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
            "email_processor.imap.fetcher.message_from_bytes",
            side_effect=[
                header_msg,  # First call for header (succeeds)
                email.errors.MessageParseError("Parse error"),  # Second call for message (fails)
            ],
        ):
            from email_processor.imap.fetcher import ProcessingMetrics

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
            "email_processor.imap.fetcher.message_from_bytes",
            side_effect=[
                header_msg,  # First call for header (succeeds)
                UnicodeDecodeError(
                    "utf-8", b"", 0, 1, "invalid"
                ),  # Second call for message (fails)
            ],
        ):
            from email_processor.imap.fetcher import ProcessingMetrics

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

        from email_processor.imap.fetcher import ProcessingMetrics

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

        from email_processor.imap.fetcher import ProcessingMetrics

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

        from email_processor.imap.fetcher import ProcessingMetrics

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
            "email_processor.imap.fetcher.message_from_bytes",
            side_effect=[
                header_msg,  # First call for header (succeeds)
                RuntimeError("Unexpected error"),  # Second call for message (fails)
            ],
        ):
            from email_processor.imap.fetcher import ProcessingMetrics

            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

    def test_process_email_message_walk_attribute_error(self):
        """Test _process_email when message.walk() raises AttributeError."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        msg_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\n\r\nBody text"

        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, msg_bytes)]),
        ]

        from email.message import Message

        from email_processor.imap.fetcher import ProcessingMetrics

        # Create a message that will raise AttributeError when walk() is called
        msg = Message()
        msg["From"] = "sender@example.com"
        msg["Subject"] = "Invoice"
        msg["Date"] = "Mon, 1 Jan 2024 12:00:00 +0000"

        with (
            patch("email_processor.imap.fetcher.message_from_bytes", return_value=msg),
            patch.object(msg, "walk", side_effect=AttributeError("No walk method")),
        ):
            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should return "error" if message walk fails
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)

    def test_process_email_message_walk_type_error(self):
        """Test _process_email when message.walk() raises TypeError."""
        mock_mail = MagicMock()
        header_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\nDate: Mon, 1 Jan 2024 12:00:00 +0000\r\n"
        msg_bytes = b"From: sender@example.com\r\nSubject: Invoice\r\n\r\nBody text"

        mock_mail.fetch.side_effect = [
            ("OK", [(b"UID 123 SIZE 1000", None)]),
            ("OK", [(None, header_bytes)]),
            ("OK", [(None, msg_bytes)]),
        ]

        from email.message import Message

        from email_processor.imap.fetcher import ProcessingMetrics

        # Create a message that will raise TypeError when walk() is called
        msg = Message()
        msg["From"] = "sender@example.com"
        msg["Subject"] = "Invoice"
        msg["Date"] = "Mon, 1 Jan 2024 12:00:00 +0000"

        with (
            patch("email_processor.imap.fetcher.message_from_bytes", return_value=msg),
            patch.object(msg, "walk", side_effect=TypeError("Invalid type")),
        ):
            metrics = ProcessingMetrics()
            result, blocked = self.processor._process_email(mock_mail, b"1", {}, False, metrics)
            # Should return "error" if message walk fails
            self.assertEqual(result, "error")
            self.assertEqual(blocked, 0)
