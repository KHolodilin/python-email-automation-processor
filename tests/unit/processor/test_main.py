"""Tests for __main__ module."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from email_processor.__main__ import create_default_config, main
from email_processor.config.constants import KEYRING_SERVICE_NAME
from email_processor.processor.email_processor import ProcessingMetrics, ProcessingResult


class TestMainEntryPoint(unittest.TestCase):
    """Tests for main entry point."""

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.clear_passwords")
    def test_main_clear_passwords_mode(self, mock_clear_passwords, mock_load_config):
        """Test main function in clear-passwords mode."""
        mock_load_config.return_value = {
            "imap": {
                "user": "test@example.com",
            },
        }

        with patch("sys.argv", ["email_processor", "--clear-passwords"]):
            result = main()
            self.assertEqual(result, 0)
            mock_clear_passwords.assert_called_once_with(KEYRING_SERVICE_NAME, "test@example.com")

    @patch("email_processor.__main__.ConfigLoader.load")
    def test_main_clear_passwords_missing_user(self, mock_load_config):
        """Test main function when user is missing in clear-passwords mode."""
        mock_load_config.return_value = {
            "imap": {},
        }

        with patch("sys.argv", ["email_processor", "--clear-passwords"]):
            result = main()
            self.assertEqual(result, 1)

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.EmailProcessor")
    def test_main_normal_mode(self, mock_processor_class, mock_load_config):
        """Test main function in normal processing mode."""
        mock_load_config.return_value = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "allowed_senders": [],
        }
        mock_processor = MagicMock()
        metrics = ProcessingMetrics(total_time=1.5)
        mock_processor.process.return_value = ProcessingResult(
            processed=5, skipped=3, errors=1, file_stats={}, metrics=metrics
        )
        mock_processor_class.return_value = mock_processor

        with patch("sys.argv", ["email_processor"]):
            result = main()
            self.assertEqual(result, 0)
            mock_processor.process.assert_called_once_with(dry_run=False, mock_mode=False)

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.EmailProcessor")
    def test_main_dry_run_mode(self, mock_processor_class, mock_load_config):
        """Test main function in dry-run mode."""
        mock_load_config.return_value = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "allowed_senders": [],
        }
        mock_processor = MagicMock()
        metrics = ProcessingMetrics(total_time=0.5)
        mock_processor.process.return_value = ProcessingResult(
            processed=0, skipped=0, errors=0, file_stats={}, metrics=metrics
        )
        mock_processor_class.return_value = mock_processor

        with patch("sys.argv", ["email_processor", "--dry-run"]):
            result = main()
            self.assertEqual(result, 0)
            mock_processor.process.assert_called_once_with(dry_run=True, mock_mode=False)

    @patch("email_processor.__main__.ConfigLoader.load")
    def test_main_config_file_not_found(self, mock_load_config):
        """Test main function when config file not found."""
        mock_load_config.side_effect = FileNotFoundError(
            "Configuration file not found: config.yaml"
        )

        with patch("sys.argv", ["email_processor"]):
            result = main()
            self.assertEqual(result, 1)

    @patch("email_processor.__main__.ConfigLoader.load")
    def test_main_config_validation_error(self, mock_load_config):
        """Test main function when config validation fails."""
        mock_load_config.side_effect = ValueError("Configuration validation failed")

        with patch("sys.argv", ["email_processor"]):
            result = main()
            self.assertEqual(result, 1)

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.EmailProcessor")
    def test_main_custom_config_path(self, mock_processor_class, mock_load_config):
        """Test main function with custom config path."""
        mock_load_config.return_value = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "allowed_senders": [],
        }
        mock_processor = MagicMock()
        metrics = ProcessingMetrics(total_time=0.8)
        mock_processor.process.return_value = ProcessingResult(
            processed=2, skipped=1, errors=0, file_stats={}, metrics=metrics
        )
        mock_processor_class.return_value = mock_processor

        with patch("sys.argv", ["email_processor", "--config", "custom_config.yaml"]):
            result = main()
            self.assertEqual(result, 0)
            mock_load_config.assert_called_once_with("custom_config.yaml")
            mock_processor.process.assert_called_once_with(dry_run=False, mock_mode=False)

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.EmailProcessor")
    def test_main_with_mock_metrics(self, mock_processor_class, mock_load_config):
        """Test main function handles ProcessingResult with MagicMock metrics gracefully."""
        mock_load_config.return_value = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "allowed_senders": [],
        }
        mock_processor = MagicMock()
        # Create ProcessingResult with MagicMock metrics to test error handling
        mock_result = ProcessingResult(
            processed=1, skipped=0, errors=0, file_stats={}, metrics=MagicMock()
        )
        mock_processor.process.return_value = mock_result
        mock_processor_class.return_value = mock_processor

        with patch("sys.argv", ["email_processor"]):
            result = main()
            # Should not crash, even with MagicMock metrics
            self.assertEqual(result, 0)
            mock_processor.process.assert_called_once_with(dry_run=False, mock_mode=False)

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.EmailProcessor")
    def test_main_with_none_metrics(self, mock_processor_class, mock_load_config):
        """Test main function handles ProcessingResult with None metrics gracefully."""
        mock_load_config.return_value = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "allowed_senders": [],
        }
        mock_processor = MagicMock()
        # Create ProcessingResult with None metrics
        mock_result = ProcessingResult(
            processed=1, skipped=0, errors=0, file_stats={}, metrics=None
        )
        mock_processor.process.return_value = mock_result
        mock_processor_class.return_value = mock_processor

        with patch("sys.argv", ["email_processor"]):
            result = main()
            # Should not crash, even with None metrics
            self.assertEqual(result, 0)
            mock_processor.process.assert_called_once_with(dry_run=False, mock_mode=False)

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.EmailProcessor")
    def test_main_keyboard_interrupt(self, mock_processor_class, mock_load_config):
        """Test main function handles KeyboardInterrupt."""
        mock_load_config.return_value = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "allowed_senders": [],
        }
        mock_processor = MagicMock()
        mock_processor.process.side_effect = KeyboardInterrupt()
        mock_processor_class.return_value = mock_processor

        with patch("sys.argv", ["email_processor"]):
            result = main()
            self.assertEqual(result, 0)

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.EmailProcessor")
    def test_main_processing_error(self, mock_processor_class, mock_load_config):
        """Test main function handles processing errors."""
        mock_load_config.return_value = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "allowed_senders": [],
        }
        mock_processor = MagicMock()
        mock_processor.process.side_effect = Exception("Processing error")
        mock_processor_class.return_value = mock_processor

        with patch("sys.argv", ["email_processor"]):
            result = main()
            self.assertEqual(result, 1)

    @patch("email_processor.__main__.Path")
    @patch("email_processor.__main__.shutil.copy2")
    def test_create_default_config_success(self, mock_copy, mock_path_class):
        """Test create_default_config successfully creates config file."""
        # Setup mocks
        example_path = MagicMock()
        example_path.exists.return_value = True
        example_path.absolute.return_value = Path("/path/to/config.yaml.example")

        target_path = MagicMock()
        target_path.exists.return_value = False
        target_path.parent = MagicMock()
        target_path.absolute.return_value = Path("/path/to/config.yaml")

        mock_path_class.side_effect = lambda p: example_path if "example" in str(p) else target_path

        result = create_default_config("config.yaml")
        self.assertEqual(result, 0)
        mock_copy.assert_called_once_with(example_path, target_path)
        target_path.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("email_processor.__main__.Path")
    @patch("email_processor.__main__.console", None)
    def test_create_default_config_example_not_found(self, mock_path_class):
        """Test create_default_config when example file not found."""
        example_path = MagicMock()
        example_path.exists.return_value = False
        example_path.absolute.return_value = Path("/path/to/config.yaml.example")

        mock_path_class.return_value = example_path

        with patch("builtins.print") as mock_print:
            result = create_default_config("config.yaml")
            self.assertEqual(result, 1)
            mock_print.assert_any_call("Error: Template file config.yaml.example not found")

    @patch("email_processor.__main__.Path")
    @patch("email_processor.__main__.shutil.copy2")
    @patch("builtins.input")
    def test_create_default_config_file_exists_overwrite(
        self, mock_input, mock_copy, mock_path_class
    ):
        """Test create_default_config when file exists and user confirms overwrite."""
        example_path = MagicMock()
        example_path.exists.return_value = True

        target_path = MagicMock()
        target_path.exists.return_value = True
        target_path.parent = MagicMock()
        target_path.absolute.return_value = Path("/path/to/config.yaml")

        mock_path_class.side_effect = lambda p: example_path if "example" in str(p) else target_path
        mock_input.return_value = "y"

        result = create_default_config("config.yaml")
        self.assertEqual(result, 0)
        mock_copy.assert_called_once_with(example_path, target_path)

    @patch("email_processor.__main__.Path")
    @patch("builtins.input")
    def test_create_default_config_file_exists_cancel(self, mock_input, mock_path_class):
        """Test create_default_config when file exists and user cancels."""
        example_path = MagicMock()
        example_path.exists.return_value = True

        target_path = MagicMock()
        target_path.exists.return_value = True

        mock_path_class.side_effect = lambda p: example_path if "example" in str(p) else target_path
        mock_input.return_value = "n"

        with patch("email_processor.__main__.console", None):
            with patch("builtins.print") as mock_print:
                result = create_default_config("config.yaml")
                self.assertEqual(result, 0)
                mock_print.assert_any_call("Cancelled.")

    @patch("email_processor.__main__.Path")
    @patch("email_processor.__main__.shutil.copy2")
    def test_create_default_config_custom_path(self, mock_copy, mock_path_class):
        """Test create_default_config with custom config path."""
        example_path = MagicMock()
        example_path.exists.return_value = True

        target_path = MagicMock()
        target_path.exists.return_value = False
        target_path.parent = MagicMock()
        target_path.absolute.return_value = Path("/custom/path/config.yaml")

        mock_path_class.side_effect = lambda p: example_path if "example" in str(p) else target_path

        result = create_default_config("custom/path/config.yaml")
        self.assertEqual(result, 0)
        mock_copy.assert_called_once_with(example_path, target_path)

    @patch("email_processor.__main__.create_default_config")
    def test_main_create_config_mode(self, mock_create_config):
        """Test main function in create-config mode."""
        mock_create_config.return_value = 0

        with patch("sys.argv", ["email_processor", "--create-config"]):
            result = main()
            self.assertEqual(result, 0)
            mock_create_config.assert_called_once_with("config.yaml")

    @patch("email_processor.__main__.create_default_config")
    def test_main_create_config_with_custom_path(self, mock_create_config):
        """Test main function in create-config mode with custom path."""
        mock_create_config.return_value = 0

        with patch("sys.argv", ["email_processor", "--create-config", "--config", "custom.yaml"]):
            result = main()
            self.assertEqual(result, 0)
            mock_create_config.assert_called_once_with("custom.yaml")
