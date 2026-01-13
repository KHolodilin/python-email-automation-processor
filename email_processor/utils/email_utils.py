"""Email utility functions."""

import email.message
import email.utils
from datetime import datetime
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import Optional

from email_processor.logging.setup import get_logger


def decode_mime_header_value(value: Optional[str]) -> str:
    """Decode MIME header value."""
    if not value:
        return ""
    decoded = decode_header(value)
    result = ""
    for part, charset in decoded:
        if charset:
            result += part.decode(charset, errors="replace")
        else:
            result += part if isinstance(part, str) else part.decode(errors="replace")
    return result


def parse_email_date(date_raw: str) -> Optional[datetime]:
    """Parse email date header with improved error handling."""
    logger = get_logger()
    if not date_raw:
        return None
    try:
        dt = parsedate_to_datetime(date_raw)
        if dt is None:
            logger.debug(
                "date_parse_failed", date_raw=date_raw, reason="parsedate_to_datetime returned None"
            )
            return None
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
    except (ValueError, TypeError) as e:
        logger.debug("date_parse_error", date_raw=date_raw, error=str(e))
        return None
    except Exception as e:
        logger.debug("date_parse_unexpected_error", date_raw=date_raw, error=str(e))
        return None
    else:
        return dt


class EmailUtils:
    """Email utility class."""

    @staticmethod
    def decode_mime_header(value: Optional[str]) -> str:
        """Decode MIME header value."""
        return decode_mime_header_value(value)

    @staticmethod
    def parse_date(date_raw: str) -> Optional[datetime]:
        """Parse email date header with improved error handling."""
        return parse_email_date(date_raw)

    @staticmethod
    def extract_sender(msg: email.message.Message) -> str:
        """Extract sender email from message."""
        return email.utils.parseaddr(msg.get("From", ""))[1]

    @staticmethod
    def extract_subject(msg: email.message.Message) -> str:
        """Extract subject from message."""
        return decode_mime_header_value(msg.get("Subject", "(no subject)"))
