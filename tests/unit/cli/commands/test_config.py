"""Tests for config commands."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from email_processor.cli import CLIUI
from email_processor.cli.commands.config import (
    _find_config_example,
    create_default_config,
    validate_config_file,
)
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


class TestFindConfigExample(unittest.TestCase):
    """Tests for _find_config_example function."""

    @patch("email_processor.cli.commands.config.Path")
    def test_find_config_example_in_current_directory(self, mock_path_class):
        """Test _find_config_example finds file in current directory."""
        example_path = MagicMock()
        example_path.exists.return_value = True

        mock_path_class.return_value = example_path

        result = _find_config_example()
        self.assertEqual(result, example_path)
        example_path.exists.assert_called_once()

    @patch("email_processor.cli.commands.config.resources")
    @patch("email_processor.cli.commands.config.Path")
    def test_find_config_example_in_package(self, mock_path_class, mock_resources):
        """Test _find_config_example finds file in package via importlib.resources."""
        # Current directory path doesn't exist
        current_dir_path = MagicMock()
        current_dir_path.exists.return_value = False

        # Package path exists
        pkg_path = Path("/package/path/config.yaml.example")
        pkg_path_mock = MagicMock()
        pkg_path_mock.exists.return_value = True

        # Mock context manager for resources.path()
        context_manager = MagicMock()
        context_manager.__enter__.return_value = pkg_path_mock
        context_manager.__exit__.return_value = None
        mock_resources.path.return_value = context_manager

        mock_path_class.side_effect = lambda p: (
            current_dir_path if p == "config.yaml.example" else Path(pkg_path_mock)
        )

        result = _find_config_example()
        # Result should be Path(pkg_path_mock)
        self.assertIsInstance(result, Path)
        mock_resources.path.assert_called_once_with("email_processor", "config.yaml.example")

    @patch("email_processor.cli.commands.config.resources")
    @patch("email_processor.cli.commands.config.Path")
    def test_find_config_example_fallback_when_package_not_found(
        self, mock_path_class, mock_resources
    ):
        """Test _find_config_example falls back to current directory when package resource not found."""
        # Current directory path doesn't exist initially
        current_dir_path = MagicMock()
        current_dir_path.exists.return_value = False

        mock_path_class.return_value = current_dir_path
        # Simulate exception when accessing package resource
        mock_resources.path.side_effect = FileNotFoundError("Package resource not found")

        result = _find_config_example()
        self.assertEqual(result, current_dir_path)
        mock_resources.path.assert_called_once_with("email_processor", "config.yaml.example")


class TestCreateConfigMissingExample(unittest.TestCase):
    """Tests for create_default_config when example file is missing."""

    @patch("email_processor.cli.commands.config.Path")
    def test_create_config_example_not_found(self, mock_path_class):
        """Test create_default_config when config.yaml.example is not found."""
        example_path = MagicMock()
        example_path.exists.return_value = False
        example_path.absolute.return_value = Path("/path/to/config.yaml.example")

        target_path = MagicMock()
        target_path.exists.return_value = False

        mock_path_class.side_effect = lambda p: example_path if "example" in str(p) else target_path

        ui = CLIUI()
        with patch.object(ui, "error") as mock_error, patch.object(ui, "info") as mock_info:
            result = create_default_config("config.yaml", ui)
            self.assertEqual(result, ExitCode.FILE_NOT_FOUND)
            mock_error.assert_called_once()
            mock_info.assert_called_once()


class TestCreateConfigOverwrite(unittest.TestCase):
    """Tests for create_default_config file overwrite confirmation."""

    @patch("email_processor.cli.commands.config.Path")
    @patch("email_processor.cli.commands.config.shutil.copy2")
    def test_create_config_overwrite_cancelled(self, mock_copy, mock_path_class):
        """Test create_default_config when user cancels overwrite."""
        example_path = MagicMock()
        example_path.exists.return_value = True

        target_path = MagicMock()
        target_path.exists.return_value = True  # File already exists
        target_path.parent = MagicMock()
        target_path.absolute.return_value = Path("/path/to/config.yaml")

        mock_path_class.side_effect = lambda p: example_path if "example" in str(p) else target_path

        ui = CLIUI()
        with patch.object(ui, "input", return_value="n"), patch.object(ui, "warn") as mock_warn:
            result = create_default_config("config.yaml", ui)
            self.assertEqual(result, ExitCode.SUCCESS)
            mock_warn.assert_called_once_with("Cancelled.")
            mock_copy.assert_not_called()

    @patch("email_processor.cli.commands.config.Path")
    @patch("email_processor.cli.commands.config.shutil.copy2")
    def test_create_config_overwrite_confirmed(self, mock_copy, mock_path_class):
        """Test create_default_config when user confirms overwrite."""
        example_path = MagicMock()
        example_path.exists.return_value = True

        target_path = MagicMock()
        target_path.exists.return_value = True  # File already exists
        target_path.parent = MagicMock()
        target_path.absolute.return_value = Path("/path/to/config.yaml")

        mock_path_class.side_effect = lambda p: example_path if "example" in str(p) else target_path

        ui = CLIUI()
        with (
            patch.object(ui, "input", return_value="y"),
            patch.object(ui, "success") as mock_success,
        ):
            result = create_default_config("config.yaml", ui)
            self.assertEqual(result, ExitCode.SUCCESS)
            mock_copy.assert_called_once_with(example_path, target_path)
            mock_success.assert_called_once()


class TestCreateConfigWithoutRich(unittest.TestCase):
    """Tests for create_default_config without rich console."""

    @patch("email_processor.cli.commands.config.Path")
    @patch("email_processor.cli.commands.config.shutil.copy2")
    @patch("email_processor.cli.ui.RICH_AVAILABLE", False)
    def test_create_config_without_rich_console(self, mock_copy, mock_path_class):
        """Test create_default_config without rich console (fallback to info)."""
        example_path = MagicMock()
        example_path.exists.return_value = True

        target_path = MagicMock()
        target_path.exists.return_value = False
        target_path.parent = MagicMock()
        target_path.absolute.return_value = Path("/path/to/config.yaml")

        mock_path_class.side_effect = lambda p: example_path if "example" in str(p) else target_path

        ui = CLIUI()
        with patch.object(ui, "info") as mock_info, patch.object(ui, "success") as mock_success:
            result = create_default_config("config.yaml", ui)
            self.assertEqual(result, ExitCode.SUCCESS)
            mock_success.assert_called_once()
            # Should use info instead of print when rich is not available
            mock_info.assert_called()
            # Check that info was called with the edit message
            info_calls = [call[0][0] for call in mock_info.call_args_list]
            self.assertTrue(any("edit" in str(call).lower() for call in info_calls))
