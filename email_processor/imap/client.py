"""IMAP client for email operations."""

import contextlib
import email.message
import imaplib
import re
import time
from email import message_from_bytes
from typing import Optional

from email_processor.logging.setup import get_logger


def imap_connect(
    server: str, user: str, password: str, max_retries: int, retry_delay: int
) -> imaplib.IMAP4_SSL:
    """Connect to IMAP server with retry logic."""
    attempts = 0
    while attempts < max_retries:
        try:
            attempts += 1
            logger = get_logger()
            logger.info("imap_connecting", server=server, attempt=attempts, max_retries=max_retries)
            mail = imaplib.IMAP4_SSL(server)
            mail.login(user, password)
            logger.info("imap_connected", server=server)
            return mail
        except imaplib.IMAP4.error as e:
            # Authentication errors should not be retried
            # Handle both string and bytes error messages (including Russian characters)
            try:
                error_str = str(e).upper()
            except (UnicodeEncodeError, UnicodeDecodeError):
                # If error contains non-ASCII characters, try to decode as bytes
                try:
                    if isinstance(e.args[0], bytes):
                        error_str = e.args[0].decode("utf-8", errors="ignore").upper()
                    else:
                        error_str = repr(e).upper()
                except Exception:
                    error_str = repr(e).upper()

            # Check for authentication failures (including Russian error messages)
            auth_keywords = [
                "AUTHENTICATIONFAILED",
                "INVALID CREDENTIALS",
                "INVALID CREDENTIAL",
                "НЕВЕРНЫЕ УЧЕТНЫЕ ДАННЫЕ",
                "ОШИБКА АУТЕНТИФИКАЦИИ",
                "АУТЕНТИФИКАЦИЯ",
                "НЕВЕРНЫЙ ПАРОЛЬ",
                "ОШИБКА ВХОДА",
            ]
            if any(keyword in error_str for keyword in auth_keywords):
                logger = get_logger()
                try:
                    error_msg = str(e)
                except (UnicodeEncodeError, UnicodeDecodeError):
                    error_msg = repr(e)
                logger.error("imap_authentication_failed", server=server, error=error_msg)
                raise ConnectionError(f"IMAP authentication failed: {error_msg}") from e

            # Other IMAP errors can be retried
            logger = get_logger()
            try:
                error_msg = str(e)
            except (UnicodeEncodeError, UnicodeDecodeError):
                error_msg = repr(e)
            logger.error("imap_connection_error", server=server, error=error_msg, attempt=attempts)
            if attempts < max_retries:
                logger.info("imap_retry", delay=retry_delay)
                time.sleep(retry_delay)
        except (UnicodeEncodeError, UnicodeDecodeError) as e:
            # Encoding errors should not be retried (e.g., Russian characters in error message)
            logger = get_logger()
            logger.error("imap_encoding_error", server=server, error=repr(e), attempt=attempts)
            raise ConnectionError(
                f"IMAP encoding error (likely authentication failure with non-ASCII characters): {e!r}"
            ) from e
        except Exception as e:
            logger = get_logger()
            try:
                error_msg = str(e)
            except (UnicodeEncodeError, UnicodeDecodeError):
                error_msg = repr(e)
            logger.error("imap_connection_error", server=server, error=error_msg, attempt=attempts)
            if attempts < max_retries:
                logger.info("imap_retry", delay=retry_delay)
                time.sleep(retry_delay)
    raise ConnectionError("IMAP: failed to connect after all attempts.")


class IMAPClient:
    """IMAP client class for email operations."""

    def __init__(self, server: str, user: str, password: str, max_retries: int, retry_delay: int):
        """
        Initialize IMAP client.

        Args:
            server: IMAP server address
            user: IMAP username
            password: IMAP password
            max_retries: Maximum connection retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.server = server
        self.user = user
        self.password = password
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._mail: Optional[imaplib.IMAP4_SSL] = None

    def connect(self) -> imaplib.IMAP4_SSL:
        """Connect to IMAP server with retry logic."""
        self._mail = imap_connect(
            self.server, self.user, self.password, self.max_retries, self.retry_delay
        )
        return self._mail

    def select_folder(self, folder: str) -> None:
        """Select IMAP folder."""
        if not self._mail:
            raise ConnectionError("Not connected to IMAP server")
        status, _ = self._mail.select(folder)
        if status != "OK":
            raise ConnectionError(f"Failed to select folder {folder}: {status}")

    def search_emails(self, since_date: str) -> list[bytes]:
        """Search emails since given date."""
        if not self._mail:
            raise ConnectionError("Not connected to IMAP server")
        status, messages = self._mail.search(None, f'(SINCE "{since_date}")')
        if status != "OK":
            raise ConnectionError(f"Email search failed: {status}")
        return messages[0].split() if messages and messages[0] else []  # type: ignore[no-any-return]

    def fetch_uid(self, msg_id: bytes) -> Optional[str]:
        """Fetch UID for message ID."""
        if not self._mail:
            raise ConnectionError("Not connected to IMAP server")

        status, meta = self._mail.fetch(msg_id, "(UID RFC822.SIZE BODYSTRUCTURE)")  # type: ignore[arg-type]
        if status != "OK" or not meta or not meta[0]:
            return None
        try:
            raw = (
                meta[0][0].decode("utf-8", errors="ignore")
                if isinstance(meta[0], tuple)
                else meta[0].decode("utf-8", errors="ignore")
            )
            uid_match = re.search(r"UID (\d+)", raw)
            return uid_match.group(1) if uid_match else None
        except Exception:
            return None

    def fetch_headers(self, msg_id: bytes) -> Optional[email.message.Message]:
        """Fetch headers for message ID."""
        if not self._mail:
            raise ConnectionError("Not connected to IMAP server")
        status, header_data = self._mail.fetch(
            msg_id,  # type: ignore[arg-type]
            "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE)])",
        )
        if status != "OK" or not header_data or not header_data[0]:
            return None
        try:
            header_bytes = (
                header_data[0][1] if isinstance(header_data[0], tuple) else header_data[0]
            )
            if not header_bytes:
                return None
            return message_from_bytes(header_bytes)
        except Exception:
            return None

    def fetch_message(self, msg_id: bytes) -> Optional[email.message.Message]:
        """Fetch full message for message ID."""
        if not self._mail:
            raise ConnectionError("Not connected to IMAP server")
        status, full_data = self._mail.fetch(msg_id, "(RFC822)")  # type: ignore[arg-type]
        if status != "OK" or not full_data or not full_data[0]:
            return None
        try:
            msg_bytes = full_data[0][1] if isinstance(full_data[0], tuple) else full_data[0]
            if not msg_bytes:
                return None
            return message_from_bytes(msg_bytes)
        except Exception:
            return None

    def close(self) -> None:
        """Close IMAP connection."""
        if self._mail:
            with contextlib.suppress(Exception):
                self._mail.logout()
            self._mail = None
