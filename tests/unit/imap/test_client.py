"""Tests for IMAP client module."""

import logging
import unittest
from unittest.mock import MagicMock, patch

from email_processor.imap.client import IMAPClient, imap_connect
from email_processor.logging.setup import setup_logging


class TestIMAPConnection(unittest.TestCase):
    """Tests for IMAP connection."""

    def setUp(self):
        """Close any file handlers from previous tests."""
        for handler in logging.root.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                try:
                    handler.close()
                except Exception:
                    pass
                logging.root.removeHandler(handler)
        setup_logging({"level": "INFO", "format": "console"})

    @patch("email_processor.imap.client.imaplib.IMAP4_SSL")
    def test_imap_connect_success(self, mock_imap_class):
        """Test successful IMAP connection."""
        mock_imap = MagicMock()
        mock_imap.login.return_value = ("OK", [b"Login successful"])
        mock_imap_class.return_value = mock_imap

        result = imap_connect("imap.example.com", "user", "password", 3, 1)

        self.assertEqual(result, mock_imap)
        mock_imap_class.assert_called_once_with("imap.example.com")
        mock_imap.login.assert_called_once_with("user", "password")

    @patch("email_processor.imap.client.imaplib.IMAP4_SSL")
    @patch("time.sleep")
    def test_imap_connect_retry(self, mock_sleep, mock_imap_class):
        """Test IMAP connection with retries."""
        mock_imap = MagicMock()
        mock_imap.login.side_effect = [
            Exception("Connection failed"),
            Exception("Connection failed"),
            ("OK", [b"Login successful"]),
        ]
        mock_imap_class.return_value = mock_imap

        result = imap_connect("imap.example.com", "user", "password", 3, 1)

        self.assertEqual(result, mock_imap)
        self.assertEqual(mock_imap.login.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("email_processor.imap.client.imaplib.IMAP4_SSL")
    @patch("time.sleep")
    def test_imap_connect_failure(self, mock_sleep, mock_imap_class):
        """Test IMAP connection failure after all retries."""
        mock_imap = MagicMock()
        mock_imap.login.side_effect = Exception("Connection failed")
        mock_imap_class.return_value = mock_imap

        with self.assertRaises(ConnectionError):
            imap_connect("imap.example.com", "user", "password", 2, 1)

        self.assertEqual(mock_imap.login.call_count, 2)


class TestIMAPClient(unittest.TestCase):
    """Tests for IMAPClient class."""

    def setUp(self):
        """Setup logging."""
        setup_logging({"level": "INFO", "format": "console"})

    @patch("email_processor.imap.client.imaplib.IMAP4_SSL")
    def test_imap_client_connect(self, mock_imap_class):
        """Test IMAPClient.connect method."""
        mock_imap = MagicMock()
        mock_imap.login.return_value = ("OK", [b"Login successful"])
        mock_imap_class.return_value = mock_imap

        client = IMAPClient("imap.example.com", "user", "password", 3, 1)
        result = client.connect()

        self.assertEqual(result, mock_imap)
        self.assertEqual(client._mail, mock_imap)

    def test_imap_client_select_folder(self):
        """Test IMAPClient.select_folder method."""
        client = IMAPClient("imap.example.com", "user", "password", 3, 1)
        client._mail = MagicMock()
        client._mail.select.return_value = ("OK", [b"1"])

        client.select_folder("INBOX")
        client._mail.select.assert_called_once_with("INBOX")

    def test_imap_client_select_folder_not_connected(self):
        """Test IMAPClient.select_folder raises when not connected."""
        client = IMAPClient("imap.example.com", "user", "password", 3, 1)

        with self.assertRaises(ConnectionError):
            client.select_folder("INBOX")

    def test_imap_client_search_emails(self):
        """Test IMAPClient.search_emails method."""
        client = IMAPClient("imap.example.com", "user", "password", 3, 1)
        client._mail = MagicMock()
        client._mail.search.return_value = ("OK", [b"1 2 3"])

        result = client.search_emails("01-Jan-2024")
        self.assertEqual(result, [b"1", b"2", b"3"])

    def test_imap_client_search_emails_not_connected(self):
        """Test IMAPClient.search_emails raises when not connected."""
        client = IMAPClient("imap.example.com", "user", "password", 3, 1)

        with self.assertRaises(ConnectionError):
            client.search_emails("01-Jan-2024")

    def test_imap_client_fetch_uid(self):
        """Test IMAPClient.fetch_uid method."""
        client = IMAPClient("imap.example.com", "user", "password", 3, 1)
        client._mail = MagicMock()
        client._mail.fetch.return_value = ("OK", [(b"UID 123 SIZE 1000", None)])

        result = client.fetch_uid(b"1")
        self.assertEqual(result, "123")

    def test_imap_client_fetch_uid_not_found(self):
        """Test IMAPClient.fetch_uid returns None when UID not found."""
        client = IMAPClient("imap.example.com", "user", "password", 3, 1)
        client._mail = MagicMock()
        client._mail.fetch.return_value = ("OK", [(b"No UID here", None)])

        result = client.fetch_uid(b"1")
        self.assertIsNone(result)

    def test_imap_client_fetch_headers(self):
        """Test IMAPClient.fetch_headers method."""
        import email.message

        client = IMAPClient("imap.example.com", "user", "password", 3, 1)
        client._mail = MagicMock()
        header_bytes = b"From: test@example.com\r\nSubject: Test\r\n"
        client._mail.fetch.return_value = ("OK", [(None, header_bytes)])

        result = client.fetch_headers(b"1")
        self.assertIsInstance(result, email.message.Message)

    def test_imap_client_fetch_message(self):
        """Test IMAPClient.fetch_message method."""
        import email.message

        client = IMAPClient("imap.example.com", "user", "password", 3, 1)
        client._mail = MagicMock()
        msg_bytes = b"From: test@example.com\r\n\r\nBody"
        client._mail.fetch.return_value = ("OK", [(None, msg_bytes)])

        result = client.fetch_message(b"1")
        self.assertIsInstance(result, email.message.Message)

    def test_imap_client_close(self):
        """Test IMAPClient.close method."""
        client = IMAPClient("imap.example.com", "user", "password", 3, 1)
        mock_mail = MagicMock()
        client._mail = mock_mail

        client.close()

        mock_mail.logout.assert_called_once()
        self.assertIsNone(client._mail)

    def test_imap_client_close_no_connection(self):
        """Test IMAPClient.close when not connected."""
        client = IMAPClient("imap.example.com", "user", "password", 3, 1)
        # Should not raise
        client.close()

    @patch("email_processor.imap.client.imaplib.IMAP4_SSL")
    def test_imap_connect_authentication_failed(self, mock_imap_class):
        """Test IMAP connection with authentication failure."""
        import imaplib

        mock_imap = MagicMock()
        auth_error = imaplib.IMAP4.error("AUTHENTICATIONFAILED")
        mock_imap.login.side_effect = auth_error
        mock_imap_class.return_value = mock_imap

        with self.assertRaises(ConnectionError) as context:
            imap_connect("imap.example.com", "user", "password", 3, 1)
        self.assertIn("IMAP authentication failed", str(context.exception))

    @patch("email_processor.imap.client.imaplib.IMAP4_SSL")
    def test_imap_connect_authentication_failed_russian(self, mock_imap_class):
        """Test IMAP connection with Russian authentication error."""
        import imaplib

        mock_imap = MagicMock()
        auth_error = imaplib.IMAP4.error("НЕВЕРНЫЕ УЧЕТНЫЕ ДАННЫЕ")
        mock_imap.login.side_effect = auth_error
        mock_imap_class.return_value = mock_imap

        with self.assertRaises(ConnectionError) as context:
            imap_connect("imap.example.com", "user", "password", 3, 1)
        self.assertIn("IMAP authentication failed", str(context.exception))

    @patch("email_processor.imap.client.imaplib.IMAP4_SSL")
    def test_imap_connect_authentication_failed_bytes(self, mock_imap_class):
        """Test IMAP connection with bytes authentication error."""
        import imaplib

        mock_imap = MagicMock()
        auth_error = imaplib.IMAP4.error(b"AUTHENTICATIONFAILED")
        mock_imap.login.side_effect = auth_error
        mock_imap_class.return_value = mock_imap

        with self.assertRaises(ConnectionError) as context:
            imap_connect("imap.example.com", "user", "password", 3, 1)
        self.assertIn("IMAP authentication failed", str(context.exception))

    @patch("email_processor.imap.client.imaplib.IMAP4_SSL")
    @patch("time.sleep")
    def test_imap_connect_imap_error_retry(self, mock_sleep, mock_imap_class):
        """Test IMAP connection retries on non-auth IMAP errors."""
        import imaplib

        mock_imap = MagicMock()
        imap_error = imaplib.IMAP4.error("Temporary error")
        mock_imap.login.side_effect = [imap_error, ("OK", [b"Login successful"])]
        mock_imap_class.return_value = mock_imap

        result = imap_connect("imap.example.com", "user", "password", 3, 1)
        self.assertEqual(result, mock_imap)
        self.assertEqual(mock_imap.login.call_count, 2)
        mock_sleep.assert_called_once()

    @patch("email_processor.imap.client.imaplib.IMAP4_SSL")
    def test_imap_connect_unicode_error(self, mock_imap_class):
        """Test IMAP connection with Unicode encoding error."""
        mock_imap = MagicMock()
        mock_imap.login.side_effect = UnicodeEncodeError("utf-8", "test", 0, 1, "error")
        mock_imap_class.return_value = mock_imap

        with self.assertRaises(ConnectionError) as context:
            imap_connect("imap.example.com", "user", "password", 3, 1)
        self.assertIn("IMAP encoding error", str(context.exception))

    @patch("email_processor.imap.client.imaplib.IMAP4_SSL")
    @patch("time.sleep")
    def test_imap_connect_general_exception_retry(self, mock_sleep, mock_imap_class):
        """Test IMAP connection retries on general exceptions."""
        mock_imap = MagicMock()
        mock_imap.login.side_effect = [ValueError("Some error"), ("OK", [b"Login successful"])]
        mock_imap_class.return_value = mock_imap

        result = imap_connect("imap.example.com", "user", "password", 3, 1)
        self.assertEqual(result, mock_imap)

    @patch("email_processor.imap.client.imaplib.IMAP4_SSL")
    def test_imap_connect_unicode_error_in_auth(self, mock_imap_class):
        """Test IMAP connection with Unicode error in authentication error handling."""
        mock_imap = MagicMock()

        # Create an exception that will raise UnicodeDecodeError when str() is called
        class UnicodeException(Exception):
            def __str__(self):
                raise UnicodeDecodeError("utf-8", b"\xff\xfe", 0, 2, "error")

        auth_error = UnicodeException()
        mock_imap.login.side_effect = auth_error
        mock_imap_class.return_value = mock_imap

        with self.assertRaises(ConnectionError):
            imap_connect("imap.example.com", "user", "password", 1, 1)

    @patch("email_processor.imap.client.imaplib.IMAP4_SSL")
    @patch("time.sleep")
    def test_imap_connect_unicode_error_in_retry(self, mock_sleep, mock_imap_class):
        """Test IMAP connection with Unicode error in retry error handling."""
        mock_imap = MagicMock()

        # Create an exception that will raise UnicodeDecodeError when str() is called
        class UnicodeException(Exception):
            def __str__(self):
                raise UnicodeDecodeError("utf-8", b"\xff\xfe", 0, 2, "error")

        retry_error = UnicodeException()
        mock_imap.login.side_effect = retry_error
        mock_imap_class.return_value = mock_imap

        with self.assertRaises(ConnectionError):
            imap_connect("imap.example.com", "user", "password", 2, 1)

    @patch("email_processor.imap.client.imaplib.IMAP4_SSL")
    @patch("time.sleep")
    def test_imap_connect_unicode_error_in_general_exception(self, mock_sleep, mock_imap_class):
        """Test IMAP connection with Unicode error in general exception handling."""

        # Create an exception that will raise UnicodeDecodeError when str() is called
        class UnicodeException(Exception):
            def __str__(self):
                raise UnicodeDecodeError("utf-8", b"\xff\xfe", 0, 2, "error")

        general_error = UnicodeException()
        mock_imap_class.side_effect = general_error

        with self.assertRaises(ConnectionError):
            imap_connect("imap.example.com", "user", "password", 2, 1)
        mock_sleep.assert_called_once()

    @patch("email_processor.imap.client.imaplib.IMAP4_SSL")
    def test_imap_connect_unicode_error_in_imap_error_str(self, mock_imap_class):
        """Test IMAP connection with Unicode error when converting IMAPError to string."""
        import imaplib

        mock_imap = MagicMock()

        # Create an IMAPError that raises UnicodeDecodeError when str() is called
        class UnicodeIMAPError(imaplib.IMAP4.error):
            def __init__(self):
                super().__init__()
                self.args = (b"\xff\xfe\x00\x01",)  # Invalid UTF-8 bytes

            def __str__(self):
                # First call raises UnicodeDecodeError
                raise UnicodeDecodeError("utf-8", b"\xff\xfe", 0, 2, "error")

        imap_error = UnicodeIMAPError()
        mock_imap.login.side_effect = imap_error
        mock_imap_class.return_value = mock_imap

        with self.assertRaises(ConnectionError):
            imap_connect("imap.example.com", "user", "password", 1, 1)

    @patch("email_processor.imap.client.imaplib.IMAP4_SSL")
    def test_imap_connect_unicode_error_in_imap_error_decode(self, mock_imap_class):
        """Test IMAP connection with Unicode error when decoding bytes in IMAPError."""
        import imaplib

        mock_imap = MagicMock()

        # Create an IMAPError with bytes that cause decode error, and str() raises UnicodeEncodeError
        class UnicodeIMAPError(imaplib.IMAP4.error):
            def __init__(self):
                super().__init__()
                self.args = (b"\xff\xfe\x00\x01",)  # Invalid UTF-8 bytes

            def __str__(self):
                # First call raises UnicodeEncodeError
                raise UnicodeEncodeError("utf-8", "test", 0, 1, "error")

        imap_error = UnicodeIMAPError()
        mock_imap.login.side_effect = imap_error
        mock_imap_class.return_value = mock_imap

        with self.assertRaises(ConnectionError):
            imap_connect("imap.example.com", "user", "password", 1, 1)

    @patch("email_processor.imap.client.imaplib.IMAP4_SSL")
    def test_imap_connect_unicode_error_in_auth_logging(self, mock_imap_class):
        """Test IMAP connection with Unicode error in authentication error logging."""
        import imaplib

        mock_imap = MagicMock()

        # Create an IMAPError that is detected as auth error and raises Unicode error in logging
        class UnicodeAuthError(imaplib.IMAP4.error):
            def __str__(self):
                # First call succeeds (for error_str check)
                if not hasattr(self, "_str_called"):
                    self._str_called = True
                    return "AUTHENTICATIONFAILED"
                # Second call (in logging) raises UnicodeDecodeError
                raise UnicodeDecodeError("utf-8", b"\xff\xfe", 0, 2, "error")

        auth_error = UnicodeAuthError()
        mock_imap.login.side_effect = auth_error
        mock_imap_class.return_value = mock_imap

        with self.assertRaises(ConnectionError):
            imap_connect("imap.example.com", "user", "password", 1, 1)

    @patch("email_processor.imap.client.imaplib.IMAP4_SSL")
    @patch("time.sleep")
    def test_imap_connect_unicode_error_in_retry_logging(self, mock_sleep, mock_imap_class):
        """Test IMAP connection with Unicode error in retry error logging."""
        import imaplib

        mock_imap = MagicMock()

        # Create an IMAPError that is NOT auth error and raises Unicode error in logging
        class UnicodeRetryError(imaplib.IMAP4.error):
            def __str__(self):
                # First call succeeds (for error_str check)
                if not hasattr(self, "_str_called"):
                    self._str_called = True
                    return "Temporary failure"
                # Second call (in logging) raises UnicodeDecodeError
                raise UnicodeDecodeError("utf-8", b"\xff\xfe", 0, 2, "error")

        retry_error = UnicodeRetryError()
        mock_imap.login.side_effect = retry_error
        mock_imap_class.return_value = mock_imap

        with self.assertRaises(ConnectionError):
            imap_connect("imap.example.com", "user", "password", 2, 1)

    def test_imap_client_select_folder_failure(self):
        """Test IMAPClient.select_folder raises on failure."""
        client = IMAPClient("imap.example.com", "user", "password", 3, 1)
        client._mail = MagicMock()
        client._mail.select.return_value = ("NO", [b"Error"])

        with self.assertRaises(ConnectionError) as context:
            client.select_folder("INBOX")
        self.assertIn("Failed to select folder", str(context.exception))

    def test_imap_client_search_emails_failure(self):
        """Test IMAPClient.search_emails raises on failure."""
        client = IMAPClient("imap.example.com", "user", "password", 3, 1)
        client._mail = MagicMock()
        client._mail.search.return_value = ("NO", [b"Error"])

        with self.assertRaises(ConnectionError) as context:
            client.search_emails("01-Jan-2024")
        self.assertIn("Email search failed", str(context.exception))

    def test_imap_client_search_emails_empty(self):
        """Test IMAPClient.search_emails with empty result."""
        client = IMAPClient("imap.example.com", "user", "password", 3, 1)
        client._mail = MagicMock()
        client._mail.search.return_value = ("OK", [b""])

        result = client.search_emails("01-Jan-2024")
        self.assertEqual(result, [])

    def test_imap_client_fetch_uid_not_connected(self):
        """Test IMAPClient.fetch_uid raises when not connected."""
        client = IMAPClient("imap.example.com", "user", "password", 3, 1)

        with self.assertRaises(ConnectionError):
            client.fetch_uid(b"1")

    def test_imap_client_fetch_uid_fetch_failure(self):
        """Test IMAPClient.fetch_uid returns None on fetch failure."""
        client = IMAPClient("imap.example.com", "user", "password", 3, 1)
        client._mail = MagicMock()
        client._mail.fetch.return_value = ("NO", None)

        result = client.fetch_uid(b"1")
        self.assertIsNone(result)

    def test_imap_client_fetch_uid_exception(self):
        """Test IMAPClient.fetch_uid handles exceptions in parsing."""
        client = IMAPClient("imap.example.com", "user", "password", 3, 1)
        client._mail = MagicMock()
        # Return OK status but with data that will cause exception in parsing
        client._mail.fetch.return_value = ("OK", [object()])  # Invalid data type

        result = client.fetch_uid(b"1")
        self.assertIsNone(result)

    def test_imap_client_fetch_uid_string_response(self):
        """Test IMAPClient.fetch_uid with string response."""
        client = IMAPClient("imap.example.com", "user", "password", 3, 1)
        client._mail = MagicMock()
        client._mail.fetch.return_value = ("OK", [b"UID 456 SIZE 2000"])

        result = client.fetch_uid(b"1")
        self.assertEqual(result, "456")

    def test_imap_client_fetch_headers_not_connected(self):
        """Test IMAPClient.fetch_headers raises when not connected."""
        client = IMAPClient("imap.example.com", "user", "password", 3, 1)

        with self.assertRaises(ConnectionError):
            client.fetch_headers(b"1")

    def test_imap_client_fetch_headers_fetch_failure(self):
        """Test IMAPClient.fetch_headers returns None on fetch failure."""
        client = IMAPClient("imap.example.com", "user", "password", 3, 1)
        client._mail = MagicMock()
        client._mail.fetch.return_value = ("NO", None)

        result = client.fetch_headers(b"1")
        self.assertIsNone(result)

    def test_imap_client_fetch_headers_empty(self):
        """Test IMAPClient.fetch_headers with empty header bytes."""
        client = IMAPClient("imap.example.com", "user", "password", 3, 1)
        client._mail = MagicMock()
        client._mail.fetch.return_value = ("OK", [(None, b"")])

        result = client.fetch_headers(b"1")
        self.assertIsNone(result)

    def test_imap_client_fetch_headers_string_response(self):
        """Test IMAPClient.fetch_headers with string response."""
        client = IMAPClient("imap.example.com", "user", "password", 3, 1)
        client._mail = MagicMock()
        header_bytes = b"From: test@example.com\r\nSubject: Test\r\n"
        client._mail.fetch.return_value = ("OK", [header_bytes])

        result = client.fetch_headers(b"1")
        self.assertIsNotNone(result)

    def test_imap_client_fetch_headers_exception(self):
        """Test IMAPClient.fetch_headers handles exceptions in parsing."""
        client = IMAPClient("imap.example.com", "user", "password", 3, 1)
        client._mail = MagicMock()
        # Return OK status but with data that will cause exception in parsing
        client._mail.fetch.return_value = ("OK", [object()])  # Invalid data type

        result = client.fetch_headers(b"1")
        self.assertIsNone(result)

    def test_imap_client_fetch_message_not_connected(self):
        """Test IMAPClient.fetch_message raises when not connected."""
        client = IMAPClient("imap.example.com", "user", "password", 3, 1)

        with self.assertRaises(ConnectionError):
            client.fetch_message(b"1")

    def test_imap_client_fetch_message_fetch_failure(self):
        """Test IMAPClient.fetch_message returns None on fetch failure."""
        client = IMAPClient("imap.example.com", "user", "password", 3, 1)
        client._mail = MagicMock()
        client._mail.fetch.return_value = ("NO", None)

        result = client.fetch_message(b"1")
        self.assertIsNone(result)

    def test_imap_client_fetch_message_empty(self):
        """Test IMAPClient.fetch_message with empty message bytes."""
        client = IMAPClient("imap.example.com", "user", "password", 3, 1)
        client._mail = MagicMock()
        client._mail.fetch.return_value = ("OK", [(None, b"")])

        result = client.fetch_message(b"1")
        self.assertIsNone(result)

    def test_imap_client_fetch_message_string_response(self):
        """Test IMAPClient.fetch_message with string response."""
        client = IMAPClient("imap.example.com", "user", "password", 3, 1)
        client._mail = MagicMock()
        msg_bytes = b"From: test@example.com\r\n\r\nBody"
        client._mail.fetch.return_value = ("OK", [msg_bytes])

        result = client.fetch_message(b"1")
        self.assertIsNotNone(result)

    def test_imap_client_fetch_message_exception(self):
        """Test IMAPClient.fetch_message handles exceptions in parsing."""
        client = IMAPClient("imap.example.com", "user", "password", 3, 1)
        client._mail = MagicMock()
        # Return OK status but with data that will cause exception in parsing
        client._mail.fetch.return_value = ("OK", [object()])  # Invalid data type

        result = client.fetch_message(b"1")
        self.assertIsNone(result)
