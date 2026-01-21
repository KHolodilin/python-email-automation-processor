"""Tests for logging formatters module."""

import json
import logging
import unittest
from datetime import datetime

from email_processor.logging.formatters import StructlogFileFormatter


class TestStructlogFileFormatter(unittest.TestCase):
    """Tests for StructlogFileFormatter class."""

    def setUp(self):
        """Set up test fixtures."""
        self.formatter = StructlogFileFormatter()

    def test_init_default(self):
        """Test formatter initialization with default format."""
        formatter = StructlogFileFormatter()
        self.assertEqual(formatter.file_format, "json")

    def test_init_json_format(self):
        """Test formatter initialization with json format."""
        formatter = StructlogFileFormatter(file_format="json")
        self.assertEqual(formatter.file_format, "json")

    def test_init_console_format(self):
        """Test formatter initialization with console format."""
        formatter = StructlogFileFormatter(file_format="console")
        self.assertEqual(formatter.file_format, "console")

    def test_format_with_structlog_dict_json(self):
        """Test formatting with structlog event dict in JSON format."""
        formatter = StructlogFileFormatter(file_format="json")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg={"event": "test_event", "key": "value"},
            args=(),
            exc_info=None,
        )
        record.created = datetime(2024, 1, 1, 12, 0, 0).timestamp()

        result = formatter.format(record)
        parsed = json.loads(result.strip())

        self.assertEqual(parsed["event"], "test_event")
        self.assertEqual(parsed["key"], "value")
        self.assertEqual(parsed["level"], "INFO")
        self.assertIn("timestamp", parsed)

    def test_format_with_structlog_dict_console(self):
        """Test formatting with structlog event dict in console format."""
        formatter = StructlogFileFormatter(file_format="console")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg={"event": "test_event", "key": "value"},
            args=(),
            exc_info=None,
        )
        record.created = datetime(2024, 1, 1, 12, 0, 0).timestamp()

        result = formatter.format(record)
        # Console format should contain the event information
        self.assertIn("test_event", result)
        self.assertIn("value", result)

    def test_format_without_structlog_dict(self):
        """Test formatting without structlog event dict (fallback to default)."""
        formatter = StructlogFileFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Simple message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        # Should use default formatter
        self.assertIsInstance(result, str)
        self.assertIn("Simple message", result)

    def test_format_with_string_msg(self):
        """Test formatting with string message (not dict)."""
        formatter = StructlogFileFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=1,
            msg="Warning message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        self.assertIn("Warning message", result)

    def test_format_timestamp_in_json(self):
        """Test that timestamp is included in JSON format."""
        formatter = StructlogFileFormatter(file_format="json")
        test_time = datetime(2024, 6, 15, 14, 30, 45).timestamp()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg={"event": "test"},
            args=(),
            exc_info=None,
        )
        record.created = test_time

        result = formatter.format(record)
        parsed = json.loads(result.strip())
        self.assertIn("timestamp", parsed)
        # Check timestamp format (ISO format)
        self.assertIn("2024-06-15T14:30:45", parsed["timestamp"])

    def test_format_level_in_json(self):
        """Test that level is correctly set in JSON format."""
        formatter = StructlogFileFormatter(file_format="json")
        for level_name, level_num in [
            ("DEBUG", logging.DEBUG),
            ("INFO", logging.INFO),
            ("WARNING", logging.WARNING),
            ("ERROR", logging.ERROR),
            ("CRITICAL", logging.CRITICAL),
        ]:
            with self.subTest(level=level_name):
                record = logging.LogRecord(
                    name="test",
                    level=level_num,
                    pathname="test.py",
                    lineno=1,
                    msg={"event": "test"},
                    args=(),
                    exc_info=None,
                )
                result = formatter.format(record)
                parsed = json.loads(result.strip())
                self.assertEqual(parsed["level"], level_name)

    def test_format_ensures_ascii_false(self):
        """Test that JSON formatting preserves non-ASCII characters."""
        formatter = StructlogFileFormatter(file_format="json")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg={"event": "тест", "message": "Привет мир"},
            args=(),
            exc_info=None,
        )
        record.created = datetime.now().timestamp()

        result = formatter.format(record)
        # Should not escape Unicode characters
        self.assertIn("тест", result)
        self.assertIn("Привет мир", result)
        # Should be valid JSON
        parsed = json.loads(result.strip())
        self.assertEqual(parsed["event"], "тест")

    def test_format_with_nested_dict(self):
        """Test formatting with nested dictionary in event dict."""
        formatter = StructlogFileFormatter(file_format="json")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg={"event": "test", "data": {"nested": "value", "number": 42}},
            args=(),
            exc_info=None,
        )
        record.created = datetime.now().timestamp()

        result = formatter.format(record)
        parsed = json.loads(result.strip())
        self.assertEqual(parsed["data"]["nested"], "value")
        self.assertEqual(parsed["data"]["number"], 42)
