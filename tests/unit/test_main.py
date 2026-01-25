"""Tests for __main__ module entry point."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from email_processor.__main__ import _parse_duration, _validate_email, main
from email_processor.cli import CLIUI
from email_processor.cli.commands.config import create_default_config
from email_processor.exit_codes import ExitCode
from email_processor.imap.fetcher import ProcessingMetrics, ProcessingResult


class TestMainEntryPoint(unittest.TestCase):
    """Tests for main entry point."""

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.passwords.clear_passwords")
    def test_main_clear_passwords_mode(self, mock_clear_passwords, mock_config_loader_class):
        """Test main function in password clear mode."""
        mock_config_loader_class.load.return_value = {"imap": {}}
        mock_clear_passwords.return_value = 0

        with patch(
            "sys.argv", ["email_processor", "password", "clear", "--user", "test@example.com"]
        ):
            result = main()
            self.assertEqual(result, ExitCode.SUCCESS)
            mock_clear_passwords.assert_called_once_with("test@example.com", unittest.mock.ANY)

    @patch("email_processor.__main__.ConfigLoader")
    def test_main_clear_passwords_missing_user(self, mock_loader_class):
        """Test main when --user is missing and imap.user not in config (password clear)."""
        mock_loader_class.load.return_value = {"imap": {}}
        with patch("sys.argv", ["email_processor", "password", "clear"]):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui_class.return_value = mock_ui
                result = main()
                self.assertEqual(result, ExitCode.VALIDATION_FAILED)
                mock_ui.error.assert_called_once()
                self.assertIn("imap.user", mock_ui.error.call_args[0][0])

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.passwords.clear_passwords")
    def test_main_clear_passwords_uses_imap_user_from_config(
        self, mock_clear_passwords, mock_loader_class
    ):
        """Test password clear without --user uses imap.user from config."""
        mock_loader_class.load.return_value = {
            "imap": {"user": "from_config@example.com"},
            "processing": {},
        }
        mock_clear_passwords.return_value = 0
        with patch("sys.argv", ["email_processor", "password", "clear"]):
            result = main()
            self.assertEqual(result, ExitCode.SUCCESS)
            mock_clear_passwords.assert_called_once_with(
                "from_config@example.com", unittest.mock.ANY
            )

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.passwords.set_password")
    def test_main_password_set_uses_imap_user_from_config(
        self, mock_set_password, mock_loader_class
    ):
        """Test password set without --user uses imap.user from config."""
        mock_loader_class.load.return_value = {
            "imap": {"user": "from_config@example.com"},
            "processing": {},
        }
        mock_set_password.return_value = 0
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("secret\n")
            pwd_file = f.name
        try:
            with patch(
                "sys.argv",
                [
                    "email_processor",
                    "password",
                    "set",
                    "--password-file",
                    pwd_file,
                ],
            ):
                result = main()
                self.assertEqual(result, ExitCode.SUCCESS)
                mock_set_password.assert_called_once()
                self.assertEqual(mock_set_password.call_args[0][0], "from_config@example.com")
        finally:
            Path(pwd_file).unlink(missing_ok=True)

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("email_processor.imap.auth.get_imap_password")
    @patch("email_processor.imap.client.imap_connect")
    @patch("email_processor.cli.commands.imap.EmailProcessor")
    def test_main_normal_mode(
        self, mock_processor_class, mock_imap_connect, mock_get_password, mock_load_config
    ):
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
        mock_get_password.return_value = "password"
        mock_processor_class.return_value = mock_processor

        with patch("sys.argv", ["email_processor", "run"]):
            result = main()
            self.assertEqual(result, ExitCode.SUCCESS)
            mock_processor.process.assert_called_once_with(
                dry_run=False, mock_mode=False, config_path="config.yaml"
            )

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("email_processor.imap.auth.get_imap_password")
    @patch("email_processor.imap.client.imap_connect")
    @patch("email_processor.cli.commands.imap.EmailProcessor")
    def test_main_dry_run_mode(
        self, mock_processor_class, mock_imap_connect, mock_get_password, mock_load_config
    ):
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
        mock_get_password.return_value = "password"
        mock_processor_class.return_value = mock_processor

        with patch("sys.argv", ["email_processor", "run", "--dry-run"]):
            result = main()
            self.assertEqual(result, ExitCode.SUCCESS)
            mock_processor.process.assert_called_once_with(
                dry_run=True, mock_mode=False, config_path="config.yaml"
            )

    @patch("email_processor.config.loader.ConfigLoader.load")
    def test_main_config_file_not_found(self, mock_load_config):
        """Test main function when config file not found."""
        mock_load_config.side_effect = FileNotFoundError(
            "Configuration file not found: config.yaml"
        )

        with patch("sys.argv", ["email_processor", "run"]):
            result = main()
            self.assertEqual(result, ExitCode.CONFIG_ERROR)

    @patch("email_processor.config.loader.ConfigLoader.load")
    def test_main_config_validation_error(self, mock_load_config):
        """Test main function when config validation fails."""
        mock_load_config.side_effect = ValueError("Configuration validation failed")

        with patch("sys.argv", ["email_processor", "run"]):
            result = main()
            self.assertEqual(result, ExitCode.CONFIG_ERROR)

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("email_processor.imap.auth.get_imap_password")
    @patch("email_processor.imap.client.imap_connect")
    @patch("email_processor.cli.commands.imap.EmailProcessor")
    def test_main_custom_config_path(
        self, mock_processor_class, mock_imap_connect, mock_get_password, mock_load_config
    ):
        """Test main function with custom config path."""
        mock_load_config.return_value = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "allowed_senders": [],
        }
        mock_get_password.return_value = "password"
        mock_processor = MagicMock()
        metrics = ProcessingMetrics(total_time=0.8)
        mock_processor.process.return_value = ProcessingResult(
            processed=2, skipped=1, errors=0, file_stats={}, metrics=metrics
        )
        mock_processor_class.return_value = mock_processor

        with patch("sys.argv", ["email_processor", "--config", "custom_config.yaml"]):
            result = main()
            self.assertEqual(result, ExitCode.SUCCESS)
            # ConfigLoader.load is called with ui parameter
            mock_load_config.assert_called_once()
            call_args = mock_load_config.call_args
            self.assertEqual(call_args[0][0], "custom_config.yaml")
            self.assertIn("ui", call_args[1])
            mock_processor.process.assert_called_once_with(
                dry_run=False, mock_mode=False, config_path="custom_config.yaml"
            )

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("email_processor.imap.auth.get_imap_password")
    @patch("email_processor.imap.client.imap_connect")
    @patch("email_processor.cli.commands.imap.EmailProcessor")
    def test_main_with_mock_metrics(
        self, mock_processor_class, mock_imap_connect, mock_get_password, mock_load_config
    ):
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
        mock_get_password.return_value = "password"
        mock_processor_class.return_value = mock_processor

        with patch("sys.argv", ["email_processor"]):
            result = main()
            # Should not crash, even with MagicMock metrics
            self.assertEqual(result, ExitCode.SUCCESS)
            mock_processor.process.assert_called_once_with(
                dry_run=False, mock_mode=False, config_path="config.yaml"
            )

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("email_processor.imap.auth.get_imap_password")
    @patch("email_processor.imap.client.imap_connect")
    @patch("email_processor.cli.commands.imap.EmailProcessor")
    def test_main_with_none_metrics(
        self, mock_processor_class, mock_imap_connect, mock_get_password, mock_load_config
    ):
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
        mock_get_password.return_value = "password"
        mock_processor_class.return_value = mock_processor

        with patch("sys.argv", ["email_processor"]):
            result = main()
            # Should not crash, even with None metrics
            self.assertEqual(result, ExitCode.SUCCESS)
            mock_processor.process.assert_called_once_with(
                dry_run=False, mock_mode=False, config_path="config.yaml"
            )

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("email_processor.imap.auth.get_imap_password")
    @patch("email_processor.imap.client.imap_connect")
    @patch("email_processor.cli.commands.imap.EmailProcessor")
    def test_main_keyboard_interrupt(
        self, mock_processor_class, mock_imap_connect, mock_get_password, mock_load_config
    ):
        """Test main function handles KeyboardInterrupt."""
        mock_load_config.return_value = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "allowed_senders": [],
        }
        mock_get_password.return_value = "password"
        mock_processor = MagicMock()
        mock_processor.process.side_effect = KeyboardInterrupt()
        mock_processor_class.return_value = mock_processor

        with patch("sys.argv", ["email_processor"]):
            result = main()
            self.assertEqual(result, ExitCode.SUCCESS)

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("email_processor.imap.auth.get_imap_password")
    @patch("email_processor.imap.client.imap_connect")
    @patch("email_processor.cli.commands.imap.EmailProcessor")
    def test_main_processing_error(
        self, mock_processor_class, mock_imap_connect, mock_get_password, mock_load_config
    ):
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

        with patch("sys.argv", ["email_processor", "run"]):
            result = main()
            from email_processor.exit_codes import ExitCode

            self.assertEqual(result, ExitCode.PROCESSING_ERROR)

    @patch("email_processor.cli.commands.config.Path")
    @patch("email_processor.cli.commands.config.shutil.copy2")
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

        ui = CLIUI()
        result = create_default_config("config.yaml", ui)
        self.assertEqual(result, 0)
        mock_copy.assert_called_once_with(example_path, target_path)
        target_path.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("email_processor.cli.commands.config.Path")
    def test_create_default_config_example_not_found(self, mock_path_class):
        """Test create_default_config when example file not found."""
        example_path = MagicMock()
        example_path.exists.return_value = False
        example_path.absolute.return_value = Path("/path/to/config.yaml.example")

        mock_path_class.return_value = example_path

        ui = CLIUI()
        with patch.object(ui, "error") as mock_error:
            result = create_default_config("config.yaml", ui)
            self.assertEqual(result, ExitCode.FILE_NOT_FOUND)
            mock_error.assert_called_once()

    @patch("email_processor.cli.commands.config.Path")
    @patch("email_processor.cli.commands.config.shutil.copy2")
    def test_create_default_config_file_exists_overwrite(self, mock_copy, mock_path_class):
        """Test create_default_config when file exists and user confirms overwrite."""
        example_path = MagicMock()
        example_path.exists.return_value = True

        target_path = MagicMock()
        target_path.exists.return_value = True
        target_path.parent = MagicMock()
        target_path.absolute.return_value = Path("/path/to/config.yaml")

        mock_path_class.side_effect = lambda p: example_path if "example" in str(p) else target_path

        ui = CLIUI()
        with patch.object(ui, "input", return_value="y"):
            result = create_default_config("config.yaml", ui)
        self.assertEqual(result, 0)
        mock_copy.assert_called_once_with(example_path, target_path)

    @patch("email_processor.cli.commands.config.Path")
    def test_create_default_config_file_exists_cancel(self, mock_path_class):
        """Test create_default_config when file exists and user cancels."""
        example_path = MagicMock()
        example_path.exists.return_value = True

        target_path = MagicMock()
        target_path.exists.return_value = True

        mock_path_class.side_effect = lambda p: example_path if "example" in str(p) else target_path

        ui = CLIUI()
        with patch.object(ui, "input", return_value="n"):
            with patch.object(ui, "warn") as mock_warn:
                result = create_default_config("config.yaml", ui)
                self.assertEqual(result, ExitCode.SUCCESS)
                mock_warn.assert_called_once_with("Cancelled.")

    @patch("email_processor.cli.commands.config.Path")
    @patch("email_processor.cli.commands.config.shutil.copy2")
    def test_create_default_config_custom_path(self, mock_copy, mock_path_class):
        """Test create_default_config with custom config path."""
        example_path = MagicMock()
        example_path.exists.return_value = True

        target_path = MagicMock()
        target_path.exists.return_value = False
        target_path.parent = MagicMock()
        target_path.absolute.return_value = Path("/custom/path/config.yaml")

        mock_path_class.side_effect = lambda p: example_path if "example" in str(p) else target_path

        ui = CLIUI()
        result = create_default_config("custom/path/config.yaml", ui)
        self.assertEqual(result, 0)
        mock_copy.assert_called_once_with(example_path, target_path)

    @patch("email_processor.cli.commands.config.create_default_config")
    def test_main_create_config_mode(self, mock_create_config):
        """Test main function in create-config mode."""
        mock_create_config.return_value = 0

        with patch("sys.argv", ["email_processor", "config", "init"]):
            result = main()
            self.assertEqual(result, ExitCode.SUCCESS)
            mock_create_config.assert_called_once()
            # Check that config_path was passed
            call_args = mock_create_config.call_args[0]
            self.assertEqual(call_args[0], "config.yaml")

    @patch("email_processor.cli.commands.config.create_default_config")
    def test_main_create_config_with_custom_path(self, mock_create_config):
        """Test main function in create-config mode with custom path."""
        mock_create_config.return_value = 0

        with patch("sys.argv", ["email_processor", "config", "init", "--path", "custom.yaml"]):
            result = main()
            self.assertEqual(result, ExitCode.SUCCESS)
            mock_create_config.assert_called_once()
            # Check that custom path was passed
            call_args = mock_create_config.call_args[0]
            self.assertEqual(call_args[0], "custom.yaml")


class TestDryRunNoConnect(unittest.TestCase):
    """Tests for --dry-run-no-connect mode."""

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("email_processor.imap.auth.get_imap_password")
    @patch("email_processor.imap.client.imap_connect")
    @patch("email_processor.cli.commands.imap.EmailProcessor")
    def test_dry_run_no_connect_mode(
        self, mock_processor_class, mock_imap_connect, mock_get_password, mock_load_config
    ):
        """Test main function in dry-run-no-connect mode."""
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
        mock_get_password.return_value = "password"
        mock_processor_class.return_value = mock_processor

        with patch("sys.argv", ["email_processor", "run", "--dry-run-no-connect"]):
            result = main()
            self.assertEqual(result, ExitCode.SUCCESS)
            mock_processor.process.assert_called_once_with(
                dry_run=True, mock_mode=True, config_path="config.yaml"
            )


class TestSMTPWarning(unittest.TestCase):
    """Tests for SMTP section missing warning."""

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("email_processor.imap.auth.get_imap_password")
    @patch("email_processor.imap.client.imap_connect")
    @patch("email_processor.cli.commands.imap.EmailProcessor")
    def test_smtp_section_missing_warning(
        self, mock_processor_class, mock_imap_connect, mock_get_password, mock_load_config
    ):
        """Test warning when SMTP section is missing and not using SMTP commands."""
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
        mock_get_password.return_value = "password"
        mock_processor_class.return_value = mock_processor

        with patch("sys.argv", ["email_processor"]):
            with patch("email_processor.__main__.get_logger") as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger
                result = main()
                self.assertEqual(result, ExitCode.SUCCESS)
                # Warning is logged via structlog, check that logger.warning was called
                # The warning is logged through get_logger().warning() which is a structlog bound logger
                # mock_logger is the return value of get_logger(), so we check mock_logger.warning
                mock_logger.warning.assert_called()


# Additional tests for send, fetch, run commands and validation
class TestValidateEmail(unittest.TestCase):
    """Tests for _validate_email function."""

    def test_validate_email_valid(self):
        """Test _validate_email with valid email addresses."""
        self.assertTrue(_validate_email("test@example.com"))
        self.assertTrue(_validate_email("user.name@example.com"))
        self.assertTrue(_validate_email("user+tag@example.co.uk"))

    def test_validate_email_invalid(self):
        """Test _validate_email with invalid email addresses."""
        # Note: parseaddr is very permissive, so some "invalid" emails may pass
        # We test cases that should definitely fail
        self.assertFalse(_validate_email("@example.com"))
        self.assertFalse(_validate_email("user@"))

    def test_validate_email_empty(self):
        """Test _validate_email with empty string."""
        self.assertFalse(_validate_email(""))
        self.assertFalse(_validate_email(None))


class TestParseDuration(unittest.TestCase):
    """Tests for _parse_duration function."""

    def test_parse_duration_days(self):
        """Test _parse_duration with days."""
        self.assertEqual(_parse_duration("7d"), 7)
        self.assertEqual(_parse_duration("30d"), 30)
        self.assertEqual(_parse_duration("1d"), 1)

    def test_parse_duration_hours(self):
        """Test _parse_duration with hours."""
        self.assertEqual(_parse_duration("24h"), 1)  # 24 hours = 1 day
        self.assertEqual(_parse_duration("48h"), 2)  # 48 hours = 2 days
        self.assertEqual(_parse_duration("12h"), 0)  # 12 hours < 1 day, rounds to 0

    def test_parse_duration_invalid(self):
        """Test _parse_duration with invalid formats."""
        self.assertEqual(_parse_duration(""), 0)
        self.assertEqual(_parse_duration("invalid"), 0)
        self.assertEqual(_parse_duration("7"), 0)
        self.assertEqual(_parse_duration("7x"), 0)


class TestSendFileCommand(unittest.TestCase):
    """Tests for send file command."""

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("email_processor.cli.commands.smtp.send_file")
    def test_send_file_command(self, mock_send_file, mock_load_config):
        """Test send file command."""
        mock_load_config.return_value = {"smtp": {}}
        mock_send_file.return_value = 0

        with patch(
            "sys.argv", ["email_processor", "send", "file", "test.txt", "--to", "test@example.com"]
        ):
            result = main()
            self.assertEqual(result, ExitCode.SUCCESS)
            mock_send_file.assert_called_once()

    @patch("email_processor.config.loader.ConfigLoader.load")
    def test_send_file_missing_path(self, mock_load_config):
        """Test send file command without path."""
        mock_load_config.return_value = {"smtp": {}}

        with patch("sys.argv", ["email_processor", "send", "file", "--to", "test@example.com"]):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, ExitCode.VALIDATION_FAILED)  # from argparse

    @patch("email_processor.config.loader.ConfigLoader.load")
    def test_send_file_missing_to(self, mock_load_config):
        """Test send file command without --to."""
        mock_load_config.return_value = {"smtp": {}}

        with patch("sys.argv", ["email_processor", "send", "file", "test.txt"]):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, ExitCode.VALIDATION_FAILED)  # from argparse

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("email_processor.cli.commands.smtp.send_file")
    def test_send_file_invalid_email(self, mock_send_file, mock_load_config):
        """Test send file command with invalid email."""
        mock_load_config.return_value = {"smtp": {}}

        with patch("sys.argv", ["email_processor", "send", "file", "test.txt", "--to", "invalid"]):
            result = main()
            self.assertEqual(result, ExitCode.VALIDATION_FAILED)
            mock_send_file.assert_not_called()

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("email_processor.cli.commands.smtp.send_file")
    def test_send_file_with_cc_bcc(self, mock_send_file, mock_load_config):
        """Test send file command with CC and BCC."""
        mock_load_config.return_value = {"smtp": {}}
        mock_send_file.return_value = 0

        with patch(
            "sys.argv",
            [
                "email_processor",
                "send",
                "file",
                "test.txt",
                "--to",
                "test@example.com",
                "--cc",
                "cc@example.com",
                "--bcc",
                "bcc@example.com",
            ],
        ):
            result = main()
            self.assertEqual(result, ExitCode.SUCCESS)
            mock_send_file.assert_called_once()

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("email_processor.cli.commands.smtp.send_file")
    def test_send_file_invalid_cc(self, mock_send_file, mock_load_config):
        """Test send file command with invalid CC."""
        mock_load_config.return_value = {"smtp": {}}

        with patch(
            "sys.argv",
            [
                "email_processor",
                "send",
                "file",
                "test.txt",
                "--to",
                "test@example.com",
                "--cc",
                "invalid",
            ],
        ):
            result = main()
            self.assertEqual(result, ExitCode.VALIDATION_FAILED)
            mock_send_file.assert_not_called()

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("email_processor.cli.commands.smtp.send_file")
    def test_send_file_invalid_bcc(self, mock_send_file, mock_load_config):
        """Test send file command with invalid BCC."""
        mock_load_config.return_value = {"smtp": {}}

        with patch(
            "sys.argv",
            [
                "email_processor",
                "send",
                "file",
                "test.txt",
                "--to",
                "test@example.com",
                "--bcc",
                "invalid",
            ],
        ):
            result = main()
            self.assertEqual(result, ExitCode.VALIDATION_FAILED)
            mock_send_file.assert_not_called()


class TestSendFolderCommand(unittest.TestCase):
    """Tests for send folder command."""

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("email_processor.cli.commands.smtp.send_folder")
    def test_send_folder_command(self, mock_send_folder, mock_load_config):
        """Test send folder command."""
        mock_load_config.return_value = {"smtp": {}}
        mock_send_folder.return_value = 0

        with patch(
            "sys.argv",
            ["email_processor", "send", "folder", "test_dir", "--to", "test@example.com"],
        ):
            result = main()
            self.assertEqual(result, ExitCode.SUCCESS)
            mock_send_folder.assert_called_once()

    @patch("email_processor.__main__.ConfigLoader")
    def test_send_folder_missing_dir(self, mock_loader_class):
        """Test send folder without dir and no smtp.send_folder in config."""
        mock_loader_class.load.return_value = {"smtp": {}}
        with patch("sys.argv", ["email_processor", "send", "folder", "--to", "test@example.com"]):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui_class.return_value = mock_ui
                result = main()
                self.assertEqual(result, ExitCode.VALIDATION_FAILED)
                mock_ui.error.assert_called_once()
                self.assertIn("send_folder", mock_ui.error.call_args[0][0])

    @patch("email_processor.__main__.ConfigLoader")
    def test_send_folder_missing_to(self, mock_loader_class):
        """Test send folder without --to and no smtp.default_recipient in config."""
        mock_loader_class.load.return_value = {"smtp": {}}
        with patch("sys.argv", ["email_processor", "send", "folder", "test_dir"]):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui_class.return_value = mock_ui
                result = main()
                self.assertEqual(result, ExitCode.VALIDATION_FAILED)
                mock_ui.error.assert_called_once()
                self.assertIn("default_recipient", mock_ui.error.call_args[0][0])

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("email_processor.cli.commands.smtp.send_folder")
    def test_send_folder_invalid_email(self, mock_send_folder, mock_load_config):
        """Test send folder command with invalid email."""
        mock_load_config.return_value = {"smtp": {}}

        with patch(
            "sys.argv", ["email_processor", "send", "folder", "test_dir", "--to", "invalid"]
        ):
            result = main()
            self.assertEqual(result, ExitCode.VALIDATION_FAILED)
            mock_send_folder.assert_not_called()


class TestFetchCommand(unittest.TestCase):
    """Tests for fetch command."""

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("email_processor.cli.commands.imap.run_processor")
    def test_fetch_command(self, mock_run_processor, mock_load_config):
        """Test fetch command."""
        mock_load_config.return_value = {"imap": {}, "processing": {}}
        mock_run_processor.return_value = 0

        with patch("sys.argv", ["email_processor", "fetch"]):
            result = main()
            self.assertEqual(result, ExitCode.SUCCESS)
            mock_run_processor.assert_called_once()

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("email_processor.cli.commands.imap.run_processor")
    def test_fetch_with_since_duration(self, mock_run_processor, mock_load_config):
        """Test fetch command with --since duration."""
        mock_load_config.return_value = {"imap": {}, "processing": {}}
        mock_run_processor.return_value = 0

        with patch("sys.argv", ["email_processor", "fetch", "--since", "7d"]):
            result = main()
            self.assertEqual(result, ExitCode.SUCCESS)
            mock_run_processor.assert_called_once()
            # Check that start_days_back was set to 7
            call_kwargs = mock_run_processor.call_args[0]
            config = call_kwargs[0]
            self.assertEqual(config.get("processing", {}).get("start_days_back"), 7)

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("email_processor.cli.commands.imap.run_processor")
    def test_fetch_with_folder(self, mock_run_processor, mock_load_config):
        """Test fetch command with --folder."""
        mock_load_config.return_value = {"imap": {}, "processing": {}}
        mock_run_processor.return_value = 0

        with patch("sys.argv", ["email_processor", "fetch", "--folder", "INBOX"]):
            result = main()
            self.assertEqual(result, ExitCode.SUCCESS)
            mock_run_processor.assert_called_once()

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("email_processor.cli.commands.imap.run_processor")
    def test_fetch_with_max_emails(self, mock_run_processor, mock_load_config):
        """Test fetch command with --max-emails."""
        mock_load_config.return_value = {"imap": {}, "processing": {}}
        mock_run_processor.return_value = 0

        with patch("sys.argv", ["email_processor", "fetch", "--max-emails", "10"]):
            result = main()
            self.assertEqual(result, ExitCode.SUCCESS)
            mock_run_processor.assert_called_once()

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("email_processor.cli.commands.imap.run_processor")
    def test_fetch_with_dry_run_no_connect(self, mock_run_processor, mock_load_config):
        """Test fetch command with --dry-run-no-connect."""
        mock_load_config.return_value = {"imap": {}, "processing": {}}
        mock_run_processor.return_value = 0

        with patch("sys.argv", ["email_processor", "fetch", "--dry-run-no-connect"]):
            result = main()
            self.assertEqual(result, ExitCode.SUCCESS)
            mock_run_processor.assert_called_once()
            # Check that mock_mode is True
            call_args = mock_run_processor.call_args[0]
            self.assertTrue(call_args[2])  # mock_mode should be True


class TestRunCommand(unittest.TestCase):
    """Tests for run command."""

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("email_processor.cli.commands.imap.run_processor")
    def test_run_with_since_duration(self, mock_run_processor, mock_load_config):
        """Test run command with --since duration."""
        mock_load_config.return_value = {"imap": {}, "processing": {}}
        mock_run_processor.return_value = 0

        with patch("sys.argv", ["email_processor", "run", "--since", "14d"]):
            result = main()
            self.assertEqual(result, ExitCode.SUCCESS)
            mock_run_processor.assert_called_once()
            # Check that start_days_back was set to 14
            call_kwargs = mock_run_processor.call_args[0]
            config = call_kwargs[0]
            self.assertEqual(config.get("processing", {}).get("start_days_back"), 14)

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("email_processor.cli.commands.imap.run_processor")
    def test_run_with_folder(self, mock_run_processor, mock_load_config):
        """Test run command with --folder."""
        mock_load_config.return_value = {"imap": {}, "processing": {}}
        mock_run_processor.return_value = 0

        with patch("sys.argv", ["email_processor", "run", "--folder", "INBOX"]):
            result = main()
            self.assertEqual(result, ExitCode.SUCCESS)
            mock_run_processor.assert_called_once()

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("email_processor.cli.commands.imap.run_processor")
    def test_run_with_max_emails(self, mock_run_processor, mock_load_config):
        """Test run command with --max-emails."""
        mock_load_config.return_value = {"imap": {}, "processing": {}}
        mock_run_processor.return_value = 0

        with patch("sys.argv", ["email_processor", "run", "--max-emails", "20"]):
            result = main()
            self.assertEqual(result, ExitCode.SUCCESS)
            mock_run_processor.assert_called_once()

    def test_parse_duration_invalid_unit(self):
        """Test _parse_duration with invalid unit."""
        result = _parse_duration("5x")
        self.assertEqual(result, 0)

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.config.validate_config_file")
    def test_config_validate_command(self, mock_validate, mock_loader_class):
        """Test config validate command."""
        mock_loader = MagicMock()
        mock_loader.load.return_value = {"imap": {}, "processing": {}}
        mock_loader_class.return_value = mock_loader
        mock_validate.return_value = 0

        with patch("sys.argv", ["email_processor", "config", "validate"]):
            result = main()
            self.assertEqual(result, ExitCode.SUCCESS)
            mock_validate.assert_called_once()

    @patch("email_processor.__main__.ConfigLoader")
    def test_config_validate_command_config_error(self, mock_loader_class):
        """Test config validate command with config error."""
        # ConfigLoader.load is a class method, so we need to patch it differently
        mock_loader_class.load.side_effect = ValueError("Invalid config")

        with patch("sys.argv", ["email_processor", "config", "validate"]):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui_class.return_value = mock_ui
                result = main()
                self.assertEqual(result, ExitCode.CONFIG_ERROR)

    def test_password_set_missing_user(self):
        """Test password set command with missing user."""
        with patch("sys.argv", ["email_processor", "password", "set"]):
            with patch("email_processor.__main__.parse_arguments") as mock_parse:
                mock_args = MagicMock()
                mock_args.command = "password"
                mock_args.password_command = "set"
                mock_args.user = None  # Missing user
                mock_args.config = "config.yaml"
                mock_parse.return_value = mock_args
                with patch("email_processor.__main__.ConfigLoader") as mock_loader_class:
                    mock_loader_class.load.return_value = {"imap": {}}
                    with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                        mock_ui = MagicMock()
                        mock_ui_class.return_value = mock_ui
                        result = main()
                        self.assertEqual(result, ExitCode.VALIDATION_FAILED)
                        mock_ui.error.assert_called()

    def test_password_clear_missing_user(self):
        """Test password clear command with missing user."""
        with patch("sys.argv", ["email_processor", "password", "clear"]):
            with patch("email_processor.__main__.parse_arguments") as mock_parse:
                mock_args = MagicMock()
                mock_args.command = "password"
                mock_args.password_command = "clear"
                mock_args.user = None  # Missing user
                mock_args.config = "config.yaml"
                mock_parse.return_value = mock_args
                with patch("email_processor.__main__.ConfigLoader") as mock_loader_class:
                    mock_loader_class.load.return_value = {"imap": {}}
                    with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                        mock_ui = MagicMock()
                        mock_ui_class.return_value = mock_ui
                        result = main()
                        self.assertEqual(result, ExitCode.VALIDATION_FAILED)
                        mock_ui.error.assert_called()

    @patch("email_processor.cli.commands.smtp.send_file")
    @patch("email_processor.__main__.ConfigLoader")
    def test_send_file_missing_path_attribute(self, mock_loader_class, mock_send_file):
        """Test send file command when path attribute is missing."""
        mock_loader = MagicMock()
        mock_loader.load.return_value = {"smtp": {}}
        mock_loader_class.return_value = mock_loader

        # Create args without path attribute
        with patch("sys.argv", ["email_processor", "send", "file", "--to", "test@example.com"]):
            with patch("email_processor.__main__.parse_arguments") as mock_parse:
                mock_args = MagicMock()
                mock_args.command = "send"
                mock_args.send_command = "file"
                mock_args.to = "test@example.com"
                mock_args.dry_run = False
                mock_args.config = "config.yaml"
                # Don't set path attribute
                mock_parse.return_value = mock_args
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui_class.return_value = mock_ui
                    result = main()
                    self.assertEqual(result, ExitCode.VALIDATION_FAILED)
                    mock_ui.error.assert_called()

    @patch("email_processor.cli.commands.smtp.send_file")
    @patch("email_processor.__main__.ConfigLoader")
    def test_send_file_missing_to_attribute(self, mock_loader_class, mock_send_file):
        """Test send file command when to attribute is missing."""
        mock_loader = MagicMock()
        mock_loader.load.return_value = {"smtp": {}}
        mock_loader_class.return_value = mock_loader

        with patch("sys.argv", ["email_processor", "send", "file", "test.txt"]):
            with patch("email_processor.__main__.parse_arguments") as mock_parse:
                mock_args = MagicMock()
                mock_args.command = "send"
                mock_args.send_command = "file"
                mock_args.path = "test.txt"
                mock_args.dry_run = False
                mock_args.config = "config.yaml"
                # Don't set to attribute
                mock_parse.return_value = mock_args
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui_class.return_value = mock_ui
                    result = main()
                    self.assertEqual(result, ExitCode.VALIDATION_FAILED)
                    mock_ui.error.assert_called()

    @patch("email_processor.cli.commands.smtp.send_folder")
    @patch("email_processor.__main__.ConfigLoader")
    def test_send_folder_missing_dir_attribute(self, mock_loader_class, mock_send_folder):
        """Test send folder command when dir attribute is missing."""
        mock_loader = MagicMock()
        mock_loader.load.return_value = {"smtp": {}}
        mock_loader_class.return_value = mock_loader

        with patch("sys.argv", ["email_processor", "send", "folder", "--to", "test@example.com"]):
            with patch("email_processor.__main__.parse_arguments") as mock_parse:
                mock_args = MagicMock()
                mock_args.command = "send"
                mock_args.send_command = "folder"
                mock_args.to = "test@example.com"
                mock_args.dry_run = False
                mock_args.config = "config.yaml"
                # Don't set dir attribute
                mock_parse.return_value = mock_args
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui_class.return_value = mock_ui
                    result = main()
                    self.assertEqual(result, ExitCode.VALIDATION_FAILED)
                    mock_ui.error.assert_called()

    @patch("email_processor.cli.commands.smtp.send_folder")
    @patch("email_processor.__main__.ConfigLoader")
    def test_send_folder_missing_to_attribute(self, mock_loader_class, mock_send_folder):
        """Test send folder command when to attribute is missing."""
        mock_loader = MagicMock()
        mock_loader.load.return_value = {"smtp": {}}
        mock_loader_class.return_value = mock_loader

        with patch("sys.argv", ["email_processor", "send", "folder", "test_dir"]):
            with patch("email_processor.__main__.parse_arguments") as mock_parse:
                mock_args = MagicMock()
                mock_args.command = "send"
                mock_args.send_command = "folder"
                mock_args.dir = "test_dir"
                mock_args.dry_run = False
                mock_args.config = "config.yaml"
                # Don't set to attribute
                mock_parse.return_value = mock_args
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui_class.return_value = mock_ui
                    result = main()
                    self.assertEqual(result, ExitCode.VALIDATION_FAILED)
                    mock_ui.error.assert_called()

    @patch("email_processor.cli.commands.smtp.send_folder")
    @patch("email_processor.__main__.ConfigLoader")
    def test_send_folder_invalid_cc(self, mock_loader_class, mock_send_folder):
        """Test send folder command with invalid CC email."""
        mock_loader = MagicMock()
        mock_loader.load.return_value = {"smtp": {}}
        mock_loader_class.return_value = mock_loader

        with patch(
            "sys.argv",
            [
                "email_processor",
                "send",
                "folder",
                "test_dir",
                "--to",
                "test@example.com",
                "--cc",
                "invalid",
            ],
        ):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui_class.return_value = mock_ui
                result = main()
                self.assertEqual(result, ExitCode.VALIDATION_FAILED)
                mock_ui.error.assert_called()

    @patch("email_processor.cli.commands.smtp.send_folder")
    @patch("email_processor.__main__.ConfigLoader")
    def test_send_folder_invalid_bcc(self, mock_loader_class, mock_send_folder):
        """Test send folder command with invalid BCC email."""
        mock_loader = MagicMock()
        mock_loader.load.return_value = {"smtp": {}}
        mock_loader_class.return_value = mock_loader

        with patch(
            "sys.argv",
            [
                "email_processor",
                "send",
                "folder",
                "test_dir",
                "--to",
                "test@example.com",
                "--bcc",
                "invalid",
            ],
        ):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui_class.return_value = mock_ui
                result = main()
                self.assertEqual(result, ExitCode.VALIDATION_FAILED)
                mock_ui.error.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    def test_unknown_command(self, mock_config_loader_class):
        """Test unknown command handling."""
        mock_config_loader_class.load.return_value = {"imap": {}}
        with patch("sys.argv", ["email_processor", "unknown_command"]):
            with patch("email_processor.__main__.parse_arguments") as mock_parse:
                mock_args = MagicMock()
                mock_args.command = "unknown_command"
                mock_args.config = "config.yaml"
                mock_args.verbose = False
                mock_args.quiet = False
                mock_parse.return_value = mock_args
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui_class.return_value = mock_ui
                    result = main()
                    self.assertEqual(result, ExitCode.VALIDATION_FAILED)
                    mock_ui.error.assert_called()

    @patch("email_processor.__main__.setup_logging")
    @patch("email_processor.__main__.ConfigLoader")
    def test_setup_logging_with_log_level(self, mock_loader_class, mock_setup_logging):
        """Test _setup_logging_from_args with --log-level."""
        from email_processor.__main__ import _setup_logging_from_args

        mock_loader = MagicMock()
        mock_loader.load.return_value = {"logging": {"level": "INFO"}}
        mock_loader_class.return_value = mock_loader

        cfg = {"logging": {"level": "INFO"}}
        args = MagicMock()
        args.log_level = "DEBUG"
        args.verbose = False
        args.quiet = False
        args.log_file = None
        args.json_logs = False

        _setup_logging_from_args(cfg, args)
        mock_setup_logging.assert_called_once()
        call_args = mock_setup_logging.call_args[0][0]
        self.assertEqual(call_args["level"], "DEBUG")

    @patch("email_processor.__main__.setup_logging")
    @patch("email_processor.__main__.ConfigLoader")
    def test_setup_logging_with_verbose(self, mock_loader_class, mock_setup_logging):
        """Test _setup_logging_from_args with --verbose."""
        from email_processor.__main__ import _setup_logging_from_args

        mock_loader = MagicMock()
        mock_loader.load.return_value = {"logging": {"level": "INFO"}}
        mock_loader_class.return_value = mock_loader

        cfg = {"logging": {"level": "INFO"}}
        args = MagicMock()
        args.log_level = None
        args.verbose = True
        args.quiet = False
        args.log_file = None
        args.json_logs = False

        _setup_logging_from_args(cfg, args)
        mock_setup_logging.assert_called_once()
        call_args = mock_setup_logging.call_args[0][0]
        self.assertEqual(call_args["level"], "DEBUG")

    @patch("email_processor.__main__.setup_logging")
    @patch("email_processor.__main__.ConfigLoader")
    def test_setup_logging_with_quiet(self, mock_loader_class, mock_setup_logging):
        """Test _setup_logging_from_args with --quiet."""
        from email_processor.__main__ import _setup_logging_from_args

        mock_loader = MagicMock()
        mock_loader.load.return_value = {"logging": {"level": "INFO"}}
        mock_loader_class.return_value = mock_loader

        cfg = {"logging": {"level": "INFO"}}
        args = MagicMock()
        args.log_level = None
        args.verbose = False
        args.quiet = True
        args.log_file = None
        args.json_logs = False

        _setup_logging_from_args(cfg, args)
        mock_setup_logging.assert_called_once()
        call_args = mock_setup_logging.call_args[0][0]
        self.assertEqual(call_args["level"], "ERROR")

    @patch("email_processor.__main__.setup_logging")
    @patch("email_processor.__main__.ConfigLoader")
    def test_setup_logging_with_log_file(self, mock_loader_class, mock_setup_logging):
        """Test _setup_logging_from_args with --log-file."""
        from email_processor.__main__ import _setup_logging_from_args

        mock_loader = MagicMock()
        mock_loader.load.return_value = {"logging": {"level": "INFO"}}
        mock_loader_class.return_value = mock_loader

        cfg = {"logging": {"level": "INFO"}}
        args = MagicMock()
        args.log_level = None
        args.verbose = False
        args.quiet = False
        args.log_file = "test.log"
        args.json_logs = False

        _setup_logging_from_args(cfg, args)
        mock_setup_logging.assert_called_once()
        call_args = mock_setup_logging.call_args[0][0]
        self.assertEqual(call_args["file"], "test.log")

    @patch("email_processor.__main__.setup_logging")
    @patch("email_processor.__main__.ConfigLoader")
    def test_setup_logging_with_json_logs(self, mock_loader_class, mock_setup_logging):
        """Test _setup_logging_from_args with --json-logs."""
        from email_processor.__main__ import _setup_logging_from_args

        mock_loader = MagicMock()
        mock_loader.load.return_value = {"logging": {"level": "INFO"}}
        mock_loader_class.return_value = mock_loader

        cfg = {"logging": {"level": "INFO"}}
        args = MagicMock()
        args.log_level = None
        args.verbose = False
        args.quiet = False
        args.log_file = None
        args.json_logs = True

        _setup_logging_from_args(cfg, args)
        mock_setup_logging.assert_called_once()
        call_args = mock_setup_logging.call_args[0][0]
        self.assertEqual(call_args["format"], "json")
        self.assertEqual(call_args["format_file"], "json")

    @patch("email_processor.cli.commands.status.show_status")
    def test_status_command(self, mock_show_status):
        """Test status command."""
        mock_show_status.return_value = 0

        with patch("sys.argv", ["email_processor", "status"]):
            with patch("email_processor.__main__.parse_arguments") as mock_parse:
                mock_args = MagicMock()
                mock_args.command = "status"
                mock_args.config = "config.yaml"
                mock_args.verbose = False
                mock_args.quiet = False
                mock_parse.return_value = mock_args
                result = main()
                self.assertEqual(result, ExitCode.SUCCESS)
                mock_show_status.assert_called_once()

    @patch("email_processor.cli.commands.smtp.send_file")
    @patch("email_processor.__main__.ConfigLoader")
    def test_send_file_path_none(self, mock_loader_class, mock_send_file):
        """Test send file command when path is None."""
        mock_loader_class.load.return_value = {"smtp": {}}

        with patch("sys.argv", ["email_processor", "send", "file", "--to", "test@example.com"]):
            with patch("email_processor.__main__.parse_arguments") as mock_parse:
                mock_args = MagicMock()
                mock_args.command = "send"
                mock_args.send_command = "file"
                mock_args.path = None  # path is None
                mock_args.to = "test@example.com"
                mock_args.dry_run = False
                mock_args.config = "config.yaml"
                mock_args.verbose = False
                mock_args.quiet = False
                mock_parse.return_value = mock_args
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui_class.return_value = mock_ui
                    result = main()
                    self.assertEqual(result, ExitCode.VALIDATION_FAILED)
                    mock_ui.error.assert_called()

    @patch("email_processor.cli.commands.smtp.send_file")
    @patch("email_processor.__main__.ConfigLoader")
    def test_send_file_to_none(self, mock_loader_class, mock_send_file):
        """Test send file command when to is None."""
        mock_loader_class.load.return_value = {"smtp": {}}

        with patch("sys.argv", ["email_processor", "send", "file", "test.txt"]):
            with patch("email_processor.__main__.parse_arguments") as mock_parse:
                mock_args = MagicMock()
                mock_args.command = "send"
                mock_args.send_command = "file"
                mock_args.path = "test.txt"
                mock_args.to = None  # to is None
                mock_args.dry_run = False
                mock_args.config = "config.yaml"
                mock_args.verbose = False
                mock_args.quiet = False
                mock_parse.return_value = mock_args
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui_class.return_value = mock_ui
                    result = main()
                    self.assertEqual(result, ExitCode.VALIDATION_FAILED)
                    mock_ui.error.assert_called()

    @patch("email_processor.cli.commands.smtp.send_folder")
    @patch("email_processor.__main__.ConfigLoader")
    def test_send_folder_dir_none(self, mock_loader_class, mock_send_folder):
        """Test send folder command when dir is None."""
        mock_loader_class.load.return_value = {"smtp": {}}

        with patch("sys.argv", ["email_processor", "send", "folder", "--to", "test@example.com"]):
            with patch("email_processor.__main__.parse_arguments") as mock_parse:
                mock_args = MagicMock()
                mock_args.command = "send"
                mock_args.send_command = "folder"
                mock_args.dir = None  # dir is None
                mock_args.to = "test@example.com"
                mock_args.dry_run = False
                mock_args.config = "config.yaml"
                mock_args.verbose = False
                mock_args.quiet = False
                mock_parse.return_value = mock_args
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui_class.return_value = mock_ui
                    result = main()
                    self.assertEqual(result, ExitCode.VALIDATION_FAILED)
                    mock_ui.error.assert_called()

    @patch("email_processor.cli.commands.smtp.send_folder")
    @patch("email_processor.__main__.ConfigLoader")
    def test_send_folder_to_none(self, mock_loader_class, mock_send_folder):
        """Test send folder command when to is None."""
        mock_loader_class.load.return_value = {"smtp": {}}

        with patch("sys.argv", ["email_processor", "send", "folder", "test_dir"]):
            with patch("email_processor.__main__.parse_arguments") as mock_parse:
                mock_args = MagicMock()
                mock_args.command = "send"
                mock_args.send_command = "folder"
                mock_args.dir = "test_dir"
                mock_args.to = None  # to is None
                mock_args.dry_run = False
                mock_args.config = "config.yaml"
                mock_args.verbose = False
                mock_args.quiet = False
                mock_parse.return_value = mock_args
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui_class.return_value = mock_ui
                    result = main()
                    self.assertEqual(result, ExitCode.VALIDATION_FAILED)
                    mock_ui.error.assert_called()
