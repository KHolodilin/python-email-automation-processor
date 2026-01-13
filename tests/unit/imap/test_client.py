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
