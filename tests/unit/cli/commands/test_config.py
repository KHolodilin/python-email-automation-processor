"""Tests for config commands."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from email_processor.cli import CLIUI
from email_processor.cli.commands.config import create_default_config, validate_config_file
from email_processor.exit_codes import ExitCode


class TestCreateConfigErrors(unittest.TestCase):
    """Tests for create_config error handling."""

    @patch("email_processor.cli.commands.config.Path")
    @patch("email_processor.cli.commands.config.shutil.copy2")
    def test_create_config_os_error(self, mock_copy, mock_path_class):
        """Test error handling when creating config file fails."""
        example_path = MagicMock()
        example_path.exists.return_value = True
        example_path.absolute.return_value = Path("/path/to/config.yaml.example")

        target_path = MagicMock()
        target_path.exists.return_value = False
        target_path.parent = MagicMock()
        target_path.absolute.return_value = Path("/path/to/config.yaml")

        mock_path_class.side_effect = lambda p: example_path if "example" in str(p) else target_path
        mock_copy.side_effect = OSError("Permission denied")

        ui = CLIUI()
        with patch.object(ui, "error") as mock_error:
            result = create_default_config("config.yaml", ui)
            self.assertEqual(result, ExitCode.PROCESSING_ERROR)
            mock_error.assert_called_once()

    @patch("email_processor.cli.commands.config.Path")
    @patch("email_processor.cli.commands.config.shutil.copy2")
    def test_create_config_os_error_with_rich(self, mock_copy, mock_path_class):
        """Test error handling when creating config file fails with rich console."""
        example_path = MagicMock()
        example_path.exists.return_value = True
        example_path.absolute.return_value = Path("/path/to/config.yaml.example")

        target_path = MagicMock()
        target_path.exists.return_value = False
        target_path.parent = MagicMock()
        target_path.absolute.return_value = Path("/path/to/config.yaml")

        mock_path_class.side_effect = lambda p: example_path if "example" in str(p) else target_path
        mock_copy.side_effect = OSError("Permission denied")

        ui = CLIUI()
        with patch.object(ui, "error") as mock_error:
            result = create_default_config("config.yaml", ui)
            self.assertEqual(result, ExitCode.PROCESSING_ERROR)
            mock_error.assert_called_once()


class TestValidateConfigFile(unittest.TestCase):
    """Tests for validate_config_file function."""

    @patch("email_processor.cli.commands.config.ConfigLoader.load")
    @patch("email_processor.cli.commands.config.validate_config")
    def test_validate_config_file_success(self, mock_validate, mock_load):
        """Test validate_config_file with valid config."""
        mock_load.return_value = {"imap": {"server": "imap.example.com"}}
        mock_validate.return_value = None  # No exception means valid

        ui = CLIUI()
        with patch.object(ui, "success") as mock_success:
            result = validate_config_file("config.yaml", ui)
            self.assertEqual(result, ExitCode.SUCCESS)
            mock_load.assert_called_once_with("config.yaml", ui=ui)
            mock_validate.assert_called_once_with({"imap": {"server": "imap.example.com"}}, ui=ui)
            mock_success.assert_called_once()

    @patch("email_processor.cli.commands.config.ConfigLoader.load")
    def test_validate_config_file_not_found(self, mock_load):
        """Test validate_config_file when file not found."""
        mock_load.side_effect = FileNotFoundError("Config file not found")

        ui = CLIUI()
        with patch.object(ui, "error") as mock_error:
            result = validate_config_file("nonexistent.yaml", ui)
            self.assertEqual(result, ExitCode.FILE_NOT_FOUND)
            mock_error.assert_called_once()

    @patch("email_processor.cli.commands.config.ConfigLoader.load")
    @patch("email_processor.cli.commands.config.validate_config")
    def test_validate_config_file_validation_error(self, mock_validate, mock_load):
        """Test validate_config_file with validation error."""
        mock_load.return_value = {"imap": {}}
        mock_validate.side_effect = ValueError("Missing required field: imap.server")

        ui = CLIUI()
        with patch.object(ui, "error") as mock_error:
            result = validate_config_file("config.yaml", ui)
            self.assertEqual(result, ExitCode.CONFIG_ERROR)
            mock_load.assert_called_once_with("config.yaml", ui=ui)
            mock_validate.assert_called_once_with({"imap": {}}, ui=ui)
            mock_error.assert_called_once()

    @patch("email_processor.cli.commands.config.ConfigLoader.load")
    def test_validate_config_file_unexpected_error(self, mock_load):
        """Test validate_config_file with unexpected error."""
        mock_load.side_effect = Exception("Unexpected error")

        ui = CLIUI()
        with patch.object(ui, "error") as mock_error:
            result = validate_config_file("config.yaml", ui)
            self.assertEqual(result, ExitCode.PROCESSING_ERROR)
            mock_error.assert_called_once()


class TestCreateConfigRichOutput(unittest.TestCase):
    """Tests for create_default_config rich console output."""

    @patch("email_processor.cli.commands.config.Path")
    @patch("email_processor.cli.commands.config.shutil.copy2")
    @patch("email_processor.cli.ui.RICH_AVAILABLE", True)
    @patch("email_processor.cli.ui.Console", create=True)
    def test_create_config_with_rich_console(self, mock_console_class, mock_copy, mock_path_class):
        """Test create_default_config with rich console output."""
        example_path = MagicMock()
        example_path.exists.return_value = True

        target_path = MagicMock()
        target_path.exists.return_value = False
        target_path.parent = MagicMock()
        target_path.absolute.return_value = Path("/path/to/config.yaml")

        mock_path_class.side_effect = lambda p: example_path if "example" in str(p) else target_path

        ui = CLIUI()
        with patch.object(ui, "print") as mock_print:
            result = create_default_config("config.yaml", ui)
            self.assertEqual(result, ExitCode.SUCCESS)
            # Check that print was called with rich formatting
            mock_print.assert_called_once()
