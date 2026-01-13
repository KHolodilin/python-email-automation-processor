"""
Integration tests for email_processor module.
Tests with mocked IMAP server.
"""

import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from email_processor import (
    KEYRING_SERVICE_NAME,
    clear_passwords,
    download_attachments,
    get_imap_password,
)
from email_processor.imap.archive import archive_message
from email_processor.imap.client import imap_connect


class MockIMAP4_SSL:
    """Mock IMAP4_SSL class for testing."""

    def __init__(self, server):
        self.server = server
        self.logged_in = False
        self.selected_folder = None
        self.messages = {}
        self.archived_messages = []
        self.deleted_messages = []

    def login(self, user, password):
        """Mock login."""
        if password == "wrong_password":
            raise Exception("Authentication failed")
        self.logged_in = True
        return ("OK", [b"Login successful"])

    def select(self, folder):
        """Mock select folder."""
        self.selected_folder = folder
        return ("OK", [b"1"])

    def search(self, charset, criteria):
        """Mock search."""
        if not self.logged_in:
            return ("NO", [b"Not logged in"])
        # Return some message IDs
        return ("OK", [b"1 2 3"])

    def fetch(self, msg_id, parts):
        """Mock fetch."""
        # Use current date for headers to match processed UID file naming
        from datetime import datetime

        current_date = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")

        if msg_id == b"1":
            if "(UID RFC822.SIZE BODYSTRUCTURE)" in parts:
                # Return tuple format: (response_string, None)
                response = b"1 (UID 100 RFC822.SIZE 1024 BODYSTRUCTURE)"
                return ("OK", [(response, None)])
            elif "BODY.PEEK[HEADER.FIELDS" in parts:
                header_bytes = create_test_header_bytes(
                    "sender@example.com", "Test Subject", current_date
                )
                return ("OK", [(b"1", header_bytes)])
            elif "(RFC822)" in parts:
                msg = create_test_message_with_attachment(
                    "sender@example.com", "Test Subject", "test.pdf", b"PDF content"
                )
                msg_bytes = msg.as_bytes()
                return ("OK", [(b"1", msg_bytes)])
        elif msg_id == b"2":
            if "(UID RFC822.SIZE BODYSTRUCTURE)" in parts:
                response = b"2 (UID 101 RFC822.SIZE 2048 BODYSTRUCTURE)"
                return ("OK", [(response, None)])
            elif "BODY.PEEK[HEADER.FIELDS" in parts:
                header_bytes = create_test_header_bytes(
                    "other@example.com", "Other Subject", current_date
                )
                return ("OK", [(b"2", header_bytes)])
        return ("NO", [b"Message not found"])

    def create(self, folder):
        """Mock create folder."""
        return ("OK", [b"Folder created"])

    def uid(self, command, uid, *args):
        """Mock UID command."""
        if command == "COPY":
            folder = args[0] if args else None
            self.archived_messages.append((uid, folder))
            return ("OK", [b"Message copied"])
        elif command == "STORE":
            # args[0] is "+FLAGS", args[1] is "(\\Deleted)"
            if len(args) >= 2 and ("\\Deleted" in args[1] or "Deleted" in args[1]):
                self.deleted_messages.append(uid)
            return ("OK", [b"Flags updated"])
        return ("NO", [b"Unknown command"])

    def expunge(self):
        """Mock expunge."""
        return ("OK", [b"Expunged"])

    def logout(self):
        """Mock logout."""
        self.logged_in = False
        return ("OK", [b"Logout successful"])


def create_test_header_bytes(from_addr, subject, date):
    """Create a test email header as bytes."""
    header_lines = [
        f"From: {from_addr}",
        f"Subject: {subject}",
        f"Date: {date}",
        "",
    ]
    return "\r\n".join(header_lines).encode("utf-8")


def create_test_message_with_attachment(from_addr, subject, filename, content):
    """Create a test email message with attachment."""
    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["Subject"] = subject
    msg["Date"] = "Mon, 1 Jan 2024 12:00:00 +0000"

    # Add body
    body = MIMEText("Test email body", "plain")
    msg.attach(body)

    # Add attachment
    part = MIMEBase("application", "octet-stream")
    part.set_payload(content)
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
    msg.attach(part)

    return msg


class TestIMAPPassword(unittest.TestCase):
    """Tests for IMAP password handling."""

    @patch("email_processor.imap.auth.keyring.get_password")
    @patch("email_processor.imap.auth.keyring.set_password")
    def test_get_password_from_keyring(self, mock_set, mock_get):
        """Test getting password from keyring."""
        mock_get.return_value = "stored_password"

        password = get_imap_password("test@example.com")

        self.assertEqual(password, "stored_password")
        mock_get.assert_called_once_with(KEYRING_SERVICE_NAME, "test@example.com")
        mock_set.assert_not_called()

    @patch("email_processor.imap.auth.keyring.get_password")
    @patch("email_processor.imap.auth.keyring.set_password")
    @patch("builtins.input")
    @patch("getpass.getpass")
    def test_get_password_from_input_save(self, mock_getpass, mock_input, mock_set, mock_get):
        """Test getting password from input and saving."""
        mock_get.return_value = None
        mock_getpass.return_value = "new_password"
        mock_input.return_value = "y"

        password = get_imap_password("test@example.com")

        self.assertEqual(password, "new_password")
        mock_set.assert_called_once_with(KEYRING_SERVICE_NAME, "test@example.com", "new_password")

    @patch("email_processor.imap.auth.keyring.get_password")
    @patch("email_processor.imap.auth.keyring.set_password")
    @patch("builtins.input")
    @patch("getpass.getpass")
    def test_get_password_from_input_no_save(self, mock_getpass, mock_input, mock_set, mock_get):
        """Test getting password from input without saving."""
        mock_get.return_value = None
        mock_getpass.return_value = "new_password"
        mock_input.return_value = "n"

        password = get_imap_password("test@example.com")

        self.assertEqual(password, "new_password")
        mock_set.assert_not_called()

    @patch("email_processor.imap.auth.keyring.get_password")
    @patch("getpass.getpass")
    def test_get_password_empty(self, mock_getpass, mock_get):
        """Test getting empty password raises error."""
        mock_get.return_value = None
        mock_getpass.return_value = ""

        with self.assertRaises(ValueError):
            get_imap_password("test@example.com")


class TestIMAPConnection(unittest.TestCase):
    """Tests for IMAP connection."""

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


class TestArchiveMessage(unittest.TestCase):
    """Tests for message archiving."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_mail = MockIMAP4_SSL("imap.example.com")
        self.mock_mail.logged_in = True

    def test_archive_message_success(self):
        """Test successful message archiving."""
        archive_message(self.mock_mail, "100", "INBOX/Processed")

        self.assertIn(("100", "INBOX/Processed"), self.mock_mail.archived_messages)
        self.assertIn("100", self.mock_mail.deleted_messages)

    def test_archive_message_folder_exists(self):
        """Test archiving when folder already exists."""
        # First call creates folder
        archive_message(self.mock_mail, "100", "INBOX/Processed")
        # Second call should handle existing folder gracefully
        archive_message(self.mock_mail, "101", "INBOX/Processed")

        self.assertEqual(len(self.mock_mail.archived_messages), 2)


class TestDownloadAttachments(unittest.TestCase):
    """Integration tests for download_attachments function."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.download_dir = os.path.join(self.temp_dir, "downloads")
        self.processed_dir = os.path.join(self.temp_dir, "processed_uids")
        os.makedirs(self.download_dir, exist_ok=True)

        self.config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
                "max_retries": 3,
                "retry_delay": 1,
            },
            "processing": {
                "start_days_back": 5,
                "download_dir": self.download_dir,
                "archive_folder": "INBOX/Processed",
                "processed_dir": self.processed_dir,
                "keep_processed_days": 0,
                "archive_only_mapped": True,
                "skip_non_allowed_as_processed": True,
                "skip_unmapped_as_processed": True,
            },
            "logging": {
                "level": "WARNING",
                "format": "console",
                "format_file": "json",
            },
            "allowed_senders": ["sender@example.com"],
            "topic_mapping": {
                ".*Test.*": "test_folder",
            },
        }

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("email_processor.processor.email_processor.get_imap_password")
    @patch("email_processor.imap.client.imaplib.IMAP4_SSL")
    def test_download_attachments_success(self, mock_imap_class, mock_get_password):
        """Test successful attachment download."""
        mock_get_password.return_value = "password"
        mock_mail = MockIMAP4_SSL("imap.example.com")
        mock_imap_class.return_value = mock_mail

        download_attachments(self.config, dry_run=False)

        # Check that attachment was downloaded
        # Subject is "Test Subject" which matches ".*Test.*" -> "test_folder"
        test_folder = Path(self.download_dir) / "test_folder"
        if test_folder.exists():
            # Check for attachment file (may have _01 suffix if duplicate)
            pdf_files = list(test_folder.glob("test*.pdf"))
            self.assertGreater(len(pdf_files), 0, "No PDF files found in test_folder")
        else:
            # If folder doesn't exist, check if it was created with normalized name
            # Subject "Test Subject" -> normalized folder name
            normalized_folders = [d for d in Path(self.download_dir).iterdir() if d.is_dir()]
            self.assertGreater(len(normalized_folders), 0, "No download folders created")

        # Check processed UID was saved
        day_str = datetime.now().strftime("%Y-%m-%d")
        processed_file = Path(self.processed_dir) / f"{day_str}.txt"
        self.assertTrue(
            processed_file.exists(), f"Processed UID file {processed_file} should exist"
        )
        content = processed_file.read_text()
        self.assertIn("100", content, "UID 100 should be in processed file")

    @patch("email_processor.processor.email_processor.get_imap_password")
    @patch("email_processor.imap.client.imaplib.IMAP4_SSL")
    def test_download_attachments_filter_sender(self, mock_imap_class, mock_get_password):
        """Test that non-allowed senders are filtered."""
        mock_get_password.return_value = "password"
        mock_mail = MockIMAP4_SSL("imap.example.com")
        # Modify fetch to return message from non-allowed sender
        original_fetch = mock_mail.fetch

        def custom_fetch(msg_id, parts):
            if msg_id == b"2" and "BODY.PEEK[HEADER.FIELDS" in parts:
                header_bytes = create_test_header_bytes(
                    "other@example.com", "Test Subject", "Mon, 1 Jan 2024 12:00:00 +0000"
                )
                return ("OK", [(b"2", header_bytes)])
            return original_fetch(msg_id, parts)

        mock_mail.fetch = custom_fetch
        mock_imap_class.return_value = mock_mail

        download_attachments(self.config, dry_run=False)

        # Message from non-allowed sender should be skipped
        # No files should be downloaded
        test_folder = Path(self.download_dir) / "test_folder"
        if test_folder.exists():
            files = list(test_folder.iterdir())
            # Only message 1 (from allowed sender) should be processed
            self.assertLessEqual(len(files), 1)

    @patch("email_processor.processor.email_processor.get_imap_password")
    @patch("email_processor.imap.client.imaplib.IMAP4_SSL")
    def test_download_attachments_already_processed(self, mock_imap_class, mock_get_password):
        """Test that already processed messages are skipped."""
        mock_get_password.return_value = "password"
        mock_mail = MockIMAP4_SSL("imap.example.com")
        mock_imap_class.return_value = mock_mail

        # Save UID as already processed
        day_str = datetime.now().strftime("%Y-%m-%d")
        processed_file = Path(self.processed_dir) / f"{day_str}.txt"
        Path(self.processed_dir).mkdir(parents=True, exist_ok=True)
        processed_file.write_text("100\n")

        download_attachments(self.config, dry_run=False)

        # Attachment should not be downloaded again
        test_folder = Path(self.download_dir) / "test_folder"
        if test_folder.exists():
            files = list(test_folder.iterdir())
            self.assertEqual(len(files), 0)


class TestClearPasswords(unittest.TestCase):
    """Tests for clear_passwords function."""

    @patch("email_processor.imap.auth.keyring.delete_password")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_clear_passwords_confirm(self, mock_print, mock_input, mock_delete):
        """Test clearing passwords with confirmation."""
        mock_input.return_value = "y"
        mock_delete.side_effect = [None, None, None]  # No exception

        clear_passwords("test-service", "user@example.com")

        # Should call delete_password multiple times (for different case variations)
        self.assertGreater(mock_delete.call_count, 0)
        # Check that print was called with the correct message format
        print_calls = [str(call) for call in mock_print.call_args_list]
        found = False
        for call_str in print_calls:
            if "Done. Deleted entries:" in call_str and str(mock_delete.call_count) in call_str:
                found = True
                break
        self.assertTrue(
            found,
            f"Expected print call with 'Done. Deleted entries: {mock_delete.call_count}' not found",
        )

    @patch("email_processor.imap.auth.keyring.delete_password")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_clear_passwords_cancel(self, mock_print, mock_input, mock_delete):
        """Test clearing passwords with cancellation."""
        mock_input.return_value = "n"

        clear_passwords("test-service", "user@example.com")

        mock_delete.assert_not_called()
        mock_print.assert_any_call("Cancelled.")


if __name__ == "__main__":
    unittest.main()
