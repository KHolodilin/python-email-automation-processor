"""Tests for IMAP archive module."""

import imaplib
import logging
import unittest
from unittest.mock import MagicMock

from email_processor.imap.archive import ArchiveManager, archive_message
from email_processor.logging.setup import setup_logging


class TestArchiveMessage(unittest.TestCase):
    """Tests for message archiving."""

    def setUp(self):
        """Set up test fixtures."""
        # Close any file handlers from previous tests
        for handler in logging.root.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                try:
                    handler.close()
                except Exception:
                    pass
                logging.root.removeHandler(handler)
        setup_logging({"level": "INFO", "format": "console"})
        self.mock_mail = MagicMock()
        self.mock_mail.create.return_value = ("OK", [b"Folder created"])
        self.mock_mail.uid.return_value = ("OK", [b"Message copied"])
        self.mock_mail.expunge.return_value = ("OK", [b"Expunged"])

    def test_archive_message_success(self):
        """Test successful message archiving."""
        archive_message(self.mock_mail, "100", "INBOX/Processed")

        self.mock_mail.create.assert_called_once_with("INBOX/Processed")
        self.assertEqual(self.mock_mail.uid.call_count, 2)  # COPY and STORE
        self.mock_mail.expunge.assert_called_once()

    def test_archive_message_folder_exists(self):
        """Test archiving when folder already exists."""
        self.mock_mail.create.side_effect = imaplib.IMAP4.error("Folder exists")

        archive_message(self.mock_mail, "100", "INBOX/Processed")

        # Should still proceed with archiving
        self.assertEqual(self.mock_mail.uid.call_count, 2)

    def test_archive_message_create_unexpected_error(self):
        """Test archiving handles unexpected error creating folder."""
        self.mock_mail.create.side_effect = Exception("Unexpected error")

        archive_message(self.mock_mail, "100", "INBOX/Processed")

        # Should still proceed with archiving
        self.assertEqual(self.mock_mail.uid.call_count, 2)

    def test_archive_message_copy_fails(self):
        """Test archiving when COPY fails."""
        self.mock_mail.uid.side_effect = [
            ("NO", [b"Copy failed"]),  # COPY fails
        ]

        archive_message(self.mock_mail, "100", "INBOX/Processed")

        # Should not proceed to STORE if COPY fails
        self.assertEqual(self.mock_mail.uid.call_count, 1)
        self.mock_mail.expunge.assert_not_called()

    def test_archive_message_copy_imap_error(self):
        """Test archiving when COPY raises IMAP error."""
        self.mock_mail.uid.side_effect = [
            imaplib.IMAP4.error("IMAP error"),
        ]

        archive_message(self.mock_mail, "100", "INBOX/Processed")

        # Should not proceed to STORE if COPY fails
        self.assertEqual(self.mock_mail.uid.call_count, 1)

    def test_archive_message_copy_unexpected_error(self):
        """Test archiving when COPY raises unexpected error."""
        self.mock_mail.uid.side_effect = [
            Exception("Unexpected error"),
        ]

        archive_message(self.mock_mail, "100", "INBOX/Processed")

        # Should not proceed to STORE if COPY fails
        self.assertEqual(self.mock_mail.uid.call_count, 1)

    def test_archive_message_store_imap_error(self):
        """Test archiving when STORE raises IMAP error."""
        self.mock_mail.uid.side_effect = [
            ("OK", [b"Message copied"]),  # COPY succeeds
            imaplib.IMAP4.error("IMAP error"),  # STORE fails
        ]

        archive_message(self.mock_mail, "100", "INBOX/Processed")

        # Should still try to expunge
        self.assertEqual(self.mock_mail.uid.call_count, 2)

    def test_archive_message_store_unexpected_error(self):
        """Test archiving when STORE raises unexpected error."""
        self.mock_mail.uid.side_effect = [
            ("OK", [b"Message copied"]),  # COPY succeeds
            Exception("Unexpected error"),  # STORE fails
        ]

        archive_message(self.mock_mail, "100", "INBOX/Processed")

        # Should still try to expunge
        self.assertEqual(self.mock_mail.uid.call_count, 2)

    def test_archive_message_copy_none_result(self):
        """Test archiving when COPY returns None."""
        self.mock_mail.uid.return_value = None

        archive_message(self.mock_mail, "100", "INBOX/Processed")

        # Should not proceed to STORE if COPY fails
        self.assertEqual(self.mock_mail.uid.call_count, 1)
        self.mock_mail.expunge.assert_not_called()


class TestArchiveManager(unittest.TestCase):
    """Tests for ArchiveManager class."""

    def setUp(self):
        """Setup logging."""
        setup_logging({"level": "INFO", "format": "console"})

    def test_archive_manager_archive_message_with_client(self):
        """Test ArchiveManager.archive_message with IMAPClient."""
        mock_client = MagicMock()
        mock_client._mail = MagicMock()
        mock_client._mail.create.return_value = ("OK", [b"Folder created"])
        mock_client._mail.uid.return_value = ("OK", [b"Message copied"])
        mock_client._mail.expunge.return_value = ("OK", [b"Expunged"])

        ArchiveManager.archive_message(mock_client, "100", "INBOX/Processed")

        mock_client._mail.create.assert_called_once()
        self.assertEqual(mock_client._mail.uid.call_count, 2)

    def test_archive_manager_archive_message_with_mail(self):
        """Test ArchiveManager.archive_message with direct mail object."""
        import imaplib

        # Create a mock that doesn't have _mail attribute
        # MagicMock has all attributes by default, so we need to use spec or delattr
        mock_mail = MagicMock(spec=["create", "uid", "expunge"])
        # create might fail if folder exists (IMAP4.error), but code continues
        mock_mail.create.side_effect = imaplib.IMAP4.error("Folder exists")
        # uid should return OK for COPY and STORE
        mock_mail.uid.side_effect = [
            ("OK", [b"Message copied"]),  # COPY - first call
            ("OK", [b"Message stored"]),  # STORE - second call
        ]
        mock_mail.expunge.return_value = ("OK", [b"Expunged"])

        # ArchiveManager.archive_message checks if object has _mail attribute
        # Since mock_mail doesn't have _mail (we used spec), it calls archive_message(mock_mail, ...)
        ArchiveManager.archive_message(mock_mail, "100", "INBOX/Processed")

        # create should be called (even if it fails with IMAP4.error, the call still happens)
        mock_mail.create.assert_called_once_with("INBOX/Processed")
        # uid should be called twice (COPY and STORE)
        self.assertEqual(mock_mail.uid.call_count, 2)
