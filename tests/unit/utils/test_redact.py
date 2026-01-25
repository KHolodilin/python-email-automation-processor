"""Tests for redact utils module."""

import unittest

from email_processor.utils.redact import redact_email


class TestRedactEmail(unittest.TestCase):
    """Tests for redact_email."""

    def test_redact_email_normal(self):
        """Redact typical email."""
        self.assertEqual(redact_email("user@example.com"), "u***@***")
        self.assertEqual(redact_email("test@domain.org"), "t***@***")

    def test_redact_email_single_char_local(self):
        """Local part with one character."""
        self.assertEqual(redact_email("a@b.co"), "a***@***")

    def test_redact_email_empty(self):
        """Empty or falsy input."""
        self.assertEqual(redact_email(""), "")
        self.assertEqual(redact_email(None), "")
        self.assertEqual(redact_email("   "), "")

    def test_redact_email_no_at(self):
        """String without @."""
        self.assertEqual(redact_email("notanemail"), "***")

    def test_redact_email_empty_local(self):
        """@ only or empty local part."""
        self.assertEqual(redact_email("@domain.com"), "***@***")

    def test_redact_email_strips(self):
        """Whitespace is stripped."""
        self.assertEqual(redact_email("  user@example.com  "), "u***@***")
