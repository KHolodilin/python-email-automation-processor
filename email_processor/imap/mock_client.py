"""Mock IMAP client for dry-run mode without real connection."""

import email
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional


class MockIMAP4_SSL:
    """Mock IMAP4_SSL class for dry-run mode without connection."""

    def __init__(self, server: str):
        """Initialize mock IMAP client."""
        self.server = server
        self.logged_in = True  # Auto-login for mock
        self.selected_folder = None
        self.archived_messages: list[tuple[str, str]] = []
        self.deleted_messages: list[str] = []
        self._message_counter = 0

    def login(self, user: str, password: str) -> tuple[str, list[bytes]]:
        """Mock login - always succeeds."""
        self.logged_in = True
        return ("OK", [b"Login successful"])

    def select(self, folder: str) -> tuple[str, list[bytes]]:
        """Mock select folder."""
        self.selected_folder = folder
        return ("OK", [b"1"])

    def search(self, charset: Optional[str], criteria: str) -> tuple[str, list[bytes]]:
        """Mock search - returns test message IDs."""
        if not self.logged_in:
            return ("NO", [b"Not logged in"])
        # Return 3 test message IDs
        return ("OK", [b"1 2 3"])

    def fetch(self, msg_id: bytes, parts: str) -> tuple[str, list]:
        """Mock fetch - returns test email data."""
        msg_id_str = msg_id.decode() if isinstance(msg_id, bytes) else str(msg_id)
        current_date = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")

        # Generate test data based on message ID
        if msg_id_str == "1":
            # First message: allowed sender with attachment
            if "(UID RFC822.SIZE BODYSTRUCTURE)" in parts:
                response = b"1 (UID 100 RFC822.SIZE 1024 BODYSTRUCTURE)"
                return ("OK", [(response, None)])
            elif "BODY.PEEK[HEADER.FIELDS" in parts:
                header_bytes = self._create_header_bytes(
                    "client1@example.com", "Roadmap Q1 2024", current_date
                )
                return ("OK", [(b"1", header_bytes)])
            elif "(RFC822)" in parts:
                msg = self._create_message_with_attachment(
                    "client1@example.com",
                    "Roadmap Q1 2024",
                    "roadmap.pdf",
                    b"PDF content for roadmap",
                )
                msg_bytes = msg.as_bytes()
                return ("OK", [(b"1", msg_bytes)])

        elif msg_id_str == "2":
            # Second message: allowed sender, different topic
            if "(UID RFC822.SIZE BODYSTRUCTURE)" in parts:
                response = b"2 (UID 101 RFC822.SIZE 2048 BODYSTRUCTURE)"
                return ("OK", [(response, None)])
            elif "BODY.PEEK[HEADER.FIELDS" in parts:
                header_bytes = self._create_header_bytes(
                    "finance@example.com", "Invoice #12345", current_date
                )
                return ("OK", [(b"2", header_bytes)])
            elif "(RFC822)" in parts:
                msg = self._create_message_with_attachment(
                    "finance@example.com",
                    "Invoice #12345",
                    "invoice.pdf",
                    b"PDF content for invoice",
                )
                msg_bytes = msg.as_bytes()
                return ("OK", [(b"2", msg_bytes)])

        elif msg_id_str == "3":
            # Third message: non-allowed sender (should be skipped)
            if "(UID RFC822.SIZE BODYSTRUCTURE)" in parts:
                response = b"3 (UID 102 RFC822.SIZE 512 BODYSTRUCTURE)"
                return ("OK", [(response, None)])
            elif "BODY.PEEK[HEADER.FIELDS" in parts:
                header_bytes = self._create_header_bytes(
                    "spam@example.com", "Spam Subject", current_date
                )
                return ("OK", [(b"3", header_bytes)])
            elif "(RFC822)" in parts:
                msg = self._create_message_with_attachment(
                    "spam@example.com", "Spam Subject", "spam.exe", b"Executable content"
                )
                msg_bytes = msg.as_bytes()
                return ("OK", [(b"3", msg_bytes)])

        return ("NO", [b"Message not found"])

    def create(self, folder: str) -> tuple[str, list[bytes]]:
        """Mock create folder."""
        return ("OK", [b"Folder created"])

    def uid(self, command: str, uid: str, *args) -> tuple[str, list[bytes]]:
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

    def expunge(self) -> tuple[str, list[bytes]]:
        """Mock expunge."""
        return ("OK", [b"Expunged"])

    def logout(self) -> tuple[str, list[bytes]]:
        """Mock logout."""
        self.logged_in = False
        return ("OK", [b"Logout successful"])

    def _create_header_bytes(self, from_addr: str, subject: str, date: str) -> bytes:
        """Create test email header as bytes."""
        header_lines = [
            f"From: {from_addr}",
            f"Subject: {subject}",
            f"Date: {date}",
            "",
        ]
        return "\r\n".join(header_lines).encode("utf-8")

    def _create_message_with_attachment(
        self, from_addr: str, subject: str, filename: str, content: bytes
    ) -> email.message.Message:
        """Create a test email message with attachment."""
        msg = MIMEMultipart()
        msg["From"] = from_addr
        msg["Subject"] = subject
        msg["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")

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
