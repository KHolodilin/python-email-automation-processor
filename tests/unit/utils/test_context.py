"""Tests for context management module."""

import unittest

from email_processor.utils.context import (
    clear_context,
    generate_correlation_id,
    generate_request_id,
    get_context_dict,
    get_correlation_id,
    get_request_id,
    set_correlation_id,
    set_request_id,
)


class TestContext(unittest.TestCase):
    """Tests for context management functions."""

    def setUp(self):
        """Clear context before each test."""
        clear_context()

    def tearDown(self):
        """Clear context after each test."""
        clear_context()

    def test_generate_request_id(self):
        """Test request ID generation."""
        id1 = generate_request_id()
        id2 = generate_request_id()
        self.assertIsInstance(id1, str)
        self.assertIsInstance(id2, str)
        self.assertNotEqual(id1, id2)
        self.assertGreater(len(id1), 0)

    def test_generate_correlation_id(self):
        """Test correlation ID generation."""
        id1 = generate_correlation_id()
        id2 = generate_correlation_id()
        self.assertIsInstance(id1, str)
        self.assertIsInstance(id2, str)
        self.assertNotEqual(id1, id2)
        self.assertGreater(len(id1), 0)

    def test_set_request_id_with_value(self):
        """Test setting request ID with provided value."""
        result = set_request_id("test-request-id")
        self.assertEqual(result, "test-request-id")
        self.assertEqual(get_request_id(), "test-request-id")

    def test_set_request_id_generated(self):
        """Test setting request ID with auto-generation."""
        result = set_request_id()
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        self.assertEqual(get_request_id(), result)

    def test_get_request_id_none(self):
        """Test getting request ID when not set."""
        self.assertIsNone(get_request_id())

    def test_set_correlation_id_with_value(self):
        """Test setting correlation ID with provided value."""
        result = set_correlation_id("test-correlation-id")
        self.assertEqual(result, "test-correlation-id")
        self.assertEqual(get_correlation_id(), "test-correlation-id")

    def test_set_correlation_id_generated(self):
        """Test setting correlation ID with auto-generation."""
        result = set_correlation_id()
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)
        self.assertEqual(get_correlation_id(), result)

    def test_get_correlation_id_none(self):
        """Test getting correlation ID when not set."""
        self.assertIsNone(get_correlation_id())

    def test_clear_context(self):
        """Test clearing context variables."""
        set_request_id("test-request")
        set_correlation_id("test-correlation")
        self.assertIsNotNone(get_request_id())
        self.assertIsNotNone(get_correlation_id())

        clear_context()

        self.assertIsNone(get_request_id())
        self.assertIsNone(get_correlation_id())

    def test_get_context_dict_empty(self):
        """Test getting context dict when nothing is set."""
        ctx = get_context_dict()
        self.assertIsInstance(ctx, dict)
        self.assertEqual(len(ctx), 0)

    def test_get_context_dict_with_request_id(self):
        """Test getting context dict with request ID."""
        set_request_id("test-request")
        ctx = get_context_dict()
        self.assertIn("request_id", ctx)
        self.assertEqual(ctx["request_id"], "test-request")
        self.assertNotIn("correlation_id", ctx)

    def test_get_context_dict_with_correlation_id(self):
        """Test getting context dict with correlation ID."""
        set_correlation_id("test-correlation")
        ctx = get_context_dict()
        self.assertIn("correlation_id", ctx)
        self.assertEqual(ctx["correlation_id"], "test-correlation")
        self.assertNotIn("request_id", ctx)

    def test_get_context_dict_with_both(self):
        """Test getting context dict with both IDs."""
        set_request_id("test-request")
        set_correlation_id("test-correlation")
        ctx = get_context_dict()
        self.assertIn("request_id", ctx)
        self.assertIn("correlation_id", ctx)
        self.assertEqual(ctx["request_id"], "test-request")
        self.assertEqual(ctx["correlation_id"], "test-correlation")
