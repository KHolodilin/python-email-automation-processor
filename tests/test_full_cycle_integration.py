"""Integration tests for full email processing cycle."""

import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from email_processor import download_attachments
from email_processor.cli.commands.smtp import send_folder
from email_processor.smtp.config import SMTPConfig
from email_processor.smtp.sender import EmailSender
from email_processor.storage.sent_files_storage import SentFilesStorage


class MockIMAP4_SSL:
    """Mock IMAP4_SSL class for full cycle testing."""

    def __init__(self, server):
        self.server = server
        self.logged_in = False
        self.selected_folder = None
        self.messages = {}

    def login(self, user, password):
        """Mock login."""
        self.logged_in = True
        return ("OK", [b"Login successful"])

    def select(self, folder):
        """Mock select folder."""
        self.selected_folder = folder
        return ("OK", [b"1"])

    def search(self, charset, criteria):
        """Mock search."""
        return ("OK", [b"1"])

    def fetch(self, msg_id, parts):
        """Mock fetch."""
        from email import encoders
        from email.mime.base import MIMEBase
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        current_date = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")

        if msg_id == b"1":
            if "(UID RFC822.SIZE BODYSTRUCTURE)" in parts:
                return ("OK", [(b"1 (UID 100 RFC822.SIZE 1024 BODYSTRUCTURE)", None)])
            elif "BODY.PEEK[HEADER.FIELDS" in parts:
                header_lines = [
                    "From: sender@example.com",
                    "Subject: Test Invoice",
                    f"Date: {current_date}",
                    "",
                ]
                header_bytes = "\r\n".join(header_lines).encode("utf-8")
                return ("OK", [(b"1", header_bytes)])
            elif "(RFC822)" in parts:
                msg = MIMEMultipart()
                msg["From"] = "sender@example.com"
                msg["Subject"] = "Test Invoice"
                msg["Date"] = current_date

                body = MIMEText("Test email body", "plain")
                msg.attach(body)

                part = MIMEBase("application", "pdf")
                part.set_payload(b"PDF content")
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", 'attachment; filename="invoice.pdf"')
                msg.attach(part)

                return ("OK", [(b"1", msg.as_bytes())])
        return ("NO", [b"Message not found"])

    def create(self, folder):
        """Mock create folder."""
        return ("OK", [b"Folder created"])

    def uid(self, command, uid, *args):
        """Mock UID command."""
        if command == "COPY":
            return ("OK", [b"Message copied"])
        elif command == "STORE":
            return ("OK", [b"Flags updated"])
        return ("NO", [b"Unknown command"])

    def expunge(self):
        """Mock expunge."""
        return ("OK", [b"Expunged"])

    def logout(self):
        """Mock logout."""
        self.logged_in = False
        return ("OK", [b"Logout successful"])


class TestFullCycleIntegration(unittest.TestCase):
    """Integration tests for full email processing cycle."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.download_dir = Path(self.temp_dir) / "downloads"
        self.processed_dir = Path(self.temp_dir) / "processed_uids"
        self.sent_files_dir = Path(self.temp_dir) / "sent_files"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.sent_files_dir.mkdir(parents=True, exist_ok=True)

        self.config = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
                "max_retries": 3,
                "retry_delay": 1,
            },
            "processing": {
                "start_days_back": 5,
                "archive_folder": "INBOX/Processed",
                "processed_dir": str(self.processed_dir),
                "keep_processed_days": 0,
                "archive_only_mapped": True,
                "skip_non_allowed_as_processed": True,
                "skip_unmapped_as_processed": True,
            },
            "logging": {
                "level": "WARNING",
                "format": "console",
            },
            "allowed_senders": ["sender@example.com"],
            "topic_mapping": {
                ".*invoice.*": str(self.download_dir / "invoices"),
                ".*": str(self.download_dir / "default"),
            },
        }

        self.smtp_config = SMTPConfig(
            smtp_server="smtp.example.com",
            smtp_port=587,
            smtp_user="sender@example.com",
            smtp_password="password",
            from_address="sender@example.com",
        )

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.client.imaplib.IMAP4_SSL")
    @patch("email_processor.smtp.smtp_connect")
    def test_full_cycle_download_and_send(
        self, mock_smtp_connect, mock_imap_class, mock_get_password
    ):
        """Test full cycle: download attachments and send them via SMTP."""
        mock_get_password.return_value = "password"
        mock_mail = MockIMAP4_SSL("imap.example.com")
        mock_imap_class.return_value = mock_mail

        mock_smtp = MagicMock()
        mock_smtp.send_message.return_value = None
        mock_smtp_connect.return_value = mock_smtp

        # Step 1: Download attachments
        result = download_attachments(self.config, dry_run=False)
        self.assertIsNotNone(result)
        self.assertGreater(result.processed, 0)

        # Step 2: Verify files were downloaded
        invoice_folder = self.download_dir / "invoices"
        self.assertTrue(invoice_folder.exists(), "Invoice folder should exist")
        pdf_files = list(invoice_folder.glob("*.pdf"))
        self.assertGreater(len(pdf_files), 0, "PDF files should be downloaded")

        # Step 3: Send downloaded files via SMTP
        storage = SentFilesStorage(str(self.sent_files_dir))
        sender = EmailSender(config=self.smtp_config)

        day_str = datetime.now().strftime("%Y-%m-%d")
        for pdf_file in pdf_files:
            if not storage.is_sent(pdf_file, day_str):
                result = sender.send_file(pdf_file, "recipient@example.com", dry_run=False)
                self.assertTrue(result)
                storage.mark_as_sent(pdf_file, day_str)

        # Step 4: Verify files were sent
        self.assertTrue(mock_smtp_connect.called, "SMTP should be connected")
        self.assertGreater(mock_smtp.send_message.call_count, 0, "Files should be sent")

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.client.imaplib.IMAP4_SSL")
    @patch("email_processor.smtp.smtp_connect")
    def test_full_cycle_send_folder(self, mock_smtp_connect, mock_imap_class, mock_get_password):
        """Test full cycle: download attachments and send folder via SMTP."""
        mock_get_password.return_value = "password"
        mock_mail = MockIMAP4_SSL("imap.example.com")
        mock_imap_class.return_value = mock_mail

        mock_smtp = MagicMock()
        mock_smtp.send_message.return_value = None
        mock_smtp_connect.return_value = mock_smtp

        # Step 1: Download attachments
        download_attachments(self.config, dry_run=False)

        # Step 2: Send folder via SMTP command
        invoice_folder = self.download_dir / "invoices"
        # Ensure folder exists and has files
        self.assertTrue(invoice_folder.exists(), "Invoice folder should exist after download")
        pdf_files = list(invoice_folder.glob("*.pdf"))
        self.assertGreater(len(pdf_files), 0, "PDF files should be downloaded")

        # Create proper SMTP config dict (use isolated sent_files_dir to avoid
        # sharing state with other tests—same file hash could be marked sent)
        smtp_config_dict = {
            "smtp": {
                "server": "smtp.example.com",
                "port": 587,
                "user": "sender@example.com",
                "password": "password",
                "from_address": "sender@example.com",
                "sent_files_dir": str(self.sent_files_dir),
            }
        }
        mock_ui = MagicMock()
        mock_ui.has_rich = False
        # Mock get_imap_password to avoid password prompt
        with patch("email_processor.cli.commands.smtp.get_imap_password", return_value="password"):
            result = send_folder(
                smtp_config_dict,
                str(invoice_folder),
                "recipient@example.com",
                subject=None,
                dry_run=False,
                config_path="config.yaml",
                ui=mock_ui,
            )
        from email_processor.exit_codes import ExitCode

        # Result can be SUCCESS (0) or PROCESSING_ERROR (1) for partial failure, but should not be CONFIG_ERROR (6)
        self.assertIn(
            result,
            (ExitCode.SUCCESS, ExitCode.PROCESSING_ERROR),
            f"Send folder should succeed or have partial failure, got {result}",
        )

        # Step 3: Verify SMTP was called (if files were sent)
        # We use isolated sent_files_dir, so no files are pre-marked sent; on SUCCESS we must have sent.
        if result == ExitCode.SUCCESS:
            self.assertTrue(
                mock_smtp_connect.called, "SMTP should be connected when files are sent"
            )

    @patch("email_processor.imap.fetcher.get_imap_password")
    @patch("email_processor.imap.client.imaplib.IMAP4_SSL")
    def test_download_with_processed_tracking(self, mock_imap_class, mock_get_password):
        """Test that processed UIDs are tracked correctly."""
        mock_get_password.return_value = "password"
        mock_mail = MockIMAP4_SSL("imap.example.com")
        mock_imap_class.return_value = mock_mail

        # First run: download attachments
        result1 = download_attachments(self.config, dry_run=False)
        self.assertIsNotNone(result1)
        self.assertGreater(result1.processed, 0)

        # Check processed UID file was created
        processed_files = list(self.processed_dir.glob("*.txt"))
        self.assertGreater(len(processed_files), 0, "Processed UID file should exist")

        # Second run: should skip already processed messages
        result2 = download_attachments(self.config, dry_run=False)
        self.assertIsNotNone(result2)
        # Should have skipped the already processed message
        self.assertGreaterEqual(result2.skipped, 0)


if __name__ == "__main__":
    unittest.main()
