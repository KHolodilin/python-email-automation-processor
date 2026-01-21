"""Tests for logging setup module."""

import logging
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from email_processor.logging.setup import LoggingManager, get_logger, setup_logging


# Reset logging before each test to avoid conflicts
def setUpModule():
    """Reset logging before tests."""
    # Close all existing handlers
    for handler in logging.root.handlers[:]:
        try:
            handler.close()
        except Exception:
            pass
        logging.root.removeHandler(handler)
    logging.shutdown()


class TestSetupLogging(unittest.TestCase):
    """Tests for logging setup with structlog."""

    def setUp(self):
        """Close any file handlers from previous tests."""
        for handler in logging.root.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                try:
                    handler.close()
                except Exception:
                    pass
                logging.root.removeHandler(handler)

    def test_setup_logging_debug(self):
        """Test setting up logging with DEBUG level."""
        setup_logging({"level": "DEBUG", "format": "console"})
        self.assertEqual(logging.getLogger().level, logging.DEBUG)

    def test_setup_logging_info(self):
        """Test setting up logging with INFO level."""
        setup_logging({"level": "INFO", "format": "console"})
        self.assertEqual(logging.getLogger().level, logging.INFO)

    def test_setup_logging_warning(self):
        """Test setting up logging with WARNING level."""
        setup_logging({"level": "WARNING", "format": "console"})
        self.assertEqual(logging.getLogger().level, logging.WARNING)

    def test_setup_logging_error(self):
        """Test setting up logging with ERROR level."""
        setup_logging({"level": "ERROR", "format": "console"})
        self.assertEqual(logging.getLogger().level, logging.ERROR)

    def test_setup_logging_critical(self):
        """Test setting up logging with CRITICAL level."""
        setup_logging({"level": "CRITICAL", "format": "console"})
        self.assertEqual(logging.getLogger().level, logging.CRITICAL)

    def test_setup_logging_invalid_defaults_to_info(self):
        """Test that invalid log level defaults to INFO."""
        setup_logging({"level": "INVALID", "format": "console"})
        self.assertEqual(logging.getLogger().level, logging.INFO)

    def test_setup_logging_with_file(self):
        """Test setting up logging with file output."""
        import structlog

        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs"
            setup_logging(
                {"level": "INFO", "format": "console", "format_file": "json", "file": str(log_dir)}
            )
            logger = structlog.get_logger()
            logger.info("test_message", message="Test message")
            # Force flush and close handlers
            for handler in logging.root.handlers[:]:
                if isinstance(handler, logging.FileHandler):
                    handler.flush()
                    handler.close()
            # Check that log directory was created
            self.assertTrue(log_dir.exists())
            # Check that log file was created (format: yyyy-mm-dd.log)
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = log_dir / f"{today}.log"
            self.assertTrue(log_file.exists())

    def test_setup_logging_file_creates_directory(self):
        """Test that log file directory is created if needed."""
        import structlog

        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "nested" / "logs"
            setup_logging(
                {"level": "INFO", "format": "console", "format_file": "json", "file": str(log_dir)}
            )
            logger = structlog.get_logger()
            logger.info("test_message", message="Test message")
            # Force flush and close handlers
            for handler in logging.root.handlers[:]:
                if isinstance(handler, logging.FileHandler):
                    handler.flush()
                    handler.close()
            # Directory should be created
            self.assertTrue(log_dir.exists())

    def test_setup_logging_json_format(self):
        """Test setting up logging with JSON format."""
        setup_logging({"level": "INFO", "format": "json"})
        self.assertEqual(logging.getLogger().level, logging.INFO)

    def test_setup_logging_file_json_format(self):
        """Test setting up logging with file JSON format."""
        import structlog

        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs"
            setup_logging(
                {"level": "INFO", "format": "console", "format_file": "json", "file": str(log_dir)}
            )
            logger = structlog.get_logger()
            logger.info("test_message", message="Test")
            # Force flush and close handlers
            for handler in logging.root.handlers[:]:
                if isinstance(handler, logging.FileHandler):
                    handler.flush()
                    handler.close()
            self.assertTrue(log_dir.exists())


class TestGetLogger(unittest.TestCase):
    """Tests for get_logger function."""

    def setUp(self):
        """Setup logging."""
        setup_logging({"level": "INFO", "format": "console"})

    def test_get_logger_without_uid(self):
        """Test get_logger without UID."""
        logger = get_logger()
        self.assertIsNotNone(logger)

    def test_get_logger_with_uid(self):
        """Test get_logger with UID."""
        logger = get_logger(uid="12345")
        self.assertIsNotNone(logger)


class TestLoggingManager(unittest.TestCase):
    """Tests for LoggingManager class."""

    def setUp(self):
        """Close any file handlers from previous tests."""
        for handler in logging.root.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                try:
                    handler.close()
                except Exception:
                    pass
                logging.root.removeHandler(handler)

    def test_logging_manager_setup(self):
        """Test LoggingManager.setup method."""
        LoggingManager.setup({"level": "INFO", "format": "console"})
        self.assertEqual(logging.getLogger().level, logging.INFO)

    def test_logging_manager_get_logger(self):
        """Test LoggingManager.get_logger method."""
        setup_logging({"level": "INFO", "format": "console"})
        logger = LoggingManager.get_logger()
        self.assertIsNotNone(logger)

        logger_with_uid = LoggingManager.get_logger(uid="12345")
        self.assertIsNotNone(logger_with_uid)

    def test_setup_logging_file_permission_error(self):
        """Test setup_logging handles PermissionError when creating log file."""
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs"
            # Mock Path.mkdir to raise PermissionError
            with patch(
                "email_processor.logging.setup.Path.mkdir",
                side_effect=PermissionError("Access denied"),
            ):
                # Should not raise, should print warning
                with patch("builtins.print") as mock_print:
                    setup_logging(
                        {
                            "level": "INFO",
                            "format": "console",
                            "format_file": "json",
                            "file": str(log_dir),
                        }
                    )
                    # Check that warning was printed
                    mock_print.assert_called()
                    call_args = str(mock_print.call_args)
                    self.assertIn("Warning", call_args)
                    self.assertIn("file logging", call_args)

    def test_setup_logging_file_os_error(self):
        """Test setup_logging handles OSError when creating log file."""
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs"
            # Mock Path.mkdir to raise OSError
            with patch(
                "email_processor.logging.setup.Path.mkdir", side_effect=OSError("Disk full")
            ):
                # Should not raise, should print warning
                with patch("builtins.print") as mock_print:
                    setup_logging(
                        {
                            "level": "INFO",
                            "format": "console",
                            "format_file": "json",
                            "file": str(log_dir),
                        }
                    )
                    # Check that warning was printed
                    mock_print.assert_called()
                    call_args = str(mock_print.call_args)
                    self.assertIn("Warning", call_args)

    def test_setup_logging_file_unexpected_error(self):
        """Test setup_logging handles unexpected errors when creating log file."""
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir) / "logs"
            # Mock Path.mkdir to raise unexpected exception
            with patch(
                "email_processor.logging.setup.Path.mkdir",
                side_effect=ValueError("Unexpected error"),
            ):
                # Should not raise, should print warning
                with patch("builtins.print") as mock_print:
                    setup_logging(
                        {
                            "level": "INFO",
                            "format": "console",
                            "format_file": "json",
                            "file": str(log_dir),
                        }
                    )
                    # Check that warning was printed
                    mock_print.assert_called()
                    call_args = str(mock_print.call_args)
                    self.assertIn("Warning", call_args)
                    self.assertIn("Unexpected error", call_args)
