"""Tests for email utils module."""

import unittest
from datetime import datetime
from unittest.mock import patch

from email_processor.logging.setup import setup_logging
from email_processor.utils.email_utils import (
    EmailUtils,
    decode_mime_header_value,
    parse_email_date,
)


class TestEmailUtils(unittest.TestCase):
    """Tests for email utility functions."""

    def setUp(self):
        """Setup logging."""
        setup_logging({"level": "INFO", "format": "console"})

    def test_decode_mime_header_value_simple(self):
        """Test MIME header decoding with simple ASCII."""
        self.assertEqual(decode_mime_header_value("test"), "test")

    def test_decode_mime_header_value_empty(self):
        """Test MIME header decoding with empty/None values."""
        self.assertEqual(decode_mime_header_value(""), "")
        self.assertEqual(decode_mime_header_value(None), "")

    def test_decode_mime_header_value_with_charset(self):
        """Test MIME header decoding with charset."""
        test_header = "=?UTF-8?Q?Test_Subject?="
        result = decode_mime_header_value(test_header)
        self.assertIsInstance(result, str)
        self.assertIn("Test", result)

    def test_decode_mime_header_value_encoded_utf8(self):
        """Test MIME header decoding with UTF-8 encoded value."""
        test_header = "=?UTF-8?Q?Test_=D0=A2=D0=B5=D1=81=D1=82?="
        result = decode_mime_header_value(test_header)
        self.assertIsInstance(result, str)
        self.assertIn("Test", result)

    def test_decode_mime_header_value_multiple_parts(self):
        """Test MIME header decoding with multiple encoded parts."""
        test_header = "=?UTF-8?Q?Part1?= =?UTF-8?Q?Part2?="
        result = decode_mime_header_value(test_header)
        self.assertIsInstance(result, str)
        self.assertIn("Part", result)

    def test_parse_email_date_valid(self):
        """Test email date parsing with valid date."""
        date_str = "Mon, 1 Jan 2024 12:00:00 +0000"
        result = parse_email_date(date_str)
        self.assertIsInstance(result, datetime)

    def test_parse_email_date_invalid(self):
        """Test email date parsing with invalid date."""
        result = parse_email_date("invalid date")
        self.assertIsNone(result)

    def test_parse_email_date_empty(self):
        """Test email date parsing with empty string."""
        result = parse_email_date("")
        self.assertIsNone(result)
        result = parse_email_date(None)
        self.assertIsNone(result)

    def test_parse_email_date_with_timezone(self):
        """Test email date parsing with timezone."""
        date_str = "Mon, 1 Jan 2024 12:00:00 +0500"
        result = parse_email_date(date_str)
        self.assertIsInstance(result, datetime)
        # Should be converted to naive datetime
        self.assertIsNone(result.tzinfo)

    def test_parse_email_date_none_return(self):
        """Test email date parsing when parsedate_to_datetime returns None."""
        with patch("email_processor.utils.email_utils.parsedate_to_datetime", return_value=None):
            result = parse_email_date("Mon, 1 Jan 2024 12:00:00 +0000")
            self.assertIsNone(result)

    def test_parse_email_date_value_error(self):
        """Test email date parsing with ValueError."""
        with patch(
            "email_processor.utils.email_utils.parsedate_to_datetime",
            side_effect=ValueError("Invalid date"),
        ):
            result = parse_email_date("invalid")
            self.assertIsNone(result)

    def test_parse_email_date_type_error(self):
        """Test email date parsing with TypeError."""
        with patch(
            "email_processor.utils.email_utils.parsedate_to_datetime",
            side_effect=TypeError("Invalid type"),
        ):
            result = parse_email_date("invalid")
            self.assertIsNone(result)

    def test_parse_email_date_unexpected_error(self):
        """Test email date parsing with unexpected error."""
        with patch(
            "email_processor.utils.email_utils.parsedate_to_datetime",
            side_effect=Exception("Unexpected"),
        ):
            result = parse_email_date("invalid")
            self.assertIsNone(result)

    def test_email_utils_decode_mime_header(self):
        """Test EmailUtils.decode_mime_header method."""
        result = EmailUtils.decode_mime_header("test")
        self.assertEqual(result, "test")

    def test_email_utils_parse_date(self):
        """Test EmailUtils.parse_date method."""
        date_str = "Mon, 1 Jan 2024 12:00:00 +0000"
        result = EmailUtils.parse_date(date_str)
        self.assertIsInstance(result, datetime)

    def test_email_utils_extract_sender(self):
        """Test EmailUtils.extract_sender method."""
        import email.message

        msg = email.message.Message()
        msg["From"] = "Test User <test@example.com>"
        result = EmailUtils.extract_sender(msg)
        self.assertEqual(result, "test@example.com")

    def test_email_utils_extract_subject(self):
        """Test EmailUtils.extract_subject method."""
        import email.message

        msg = email.message.Message()
        msg["Subject"] = "Test Subject"
        result = EmailUtils.extract_subject(msg)
        self.assertEqual(result, "Test Subject")
