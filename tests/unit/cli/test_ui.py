"""Tests for CLI UI module (rich console output)."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from email_processor.__main__ import main
from email_processor.cli import CLIUI
from email_processor.cli.commands.config import create_default_config
from email_processor.exit_codes import ExitCode
from email_processor.imap.fetcher import ProcessingMetrics, ProcessingResult


class TestRichConsoleOutput(unittest.TestCase):
    """Tests for rich console output functionality."""

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.imap.fetcher.Fetcher")
    @patch("email_processor.cli.commands.imap._display_results")
    def test_main_with_rich_console(
        self, mock_display_results, mock_processor_class, mock_load_config
    ):
        """Test main function uses rich console when available."""
        mock_load_config.load.return_value = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
            "processing": {},
            "allowed_senders": [],
            "smtp": {},  # Add SMTP section to avoid warning
        }
        mock_processor = MagicMock()
        metrics = ProcessingMetrics(total_time=1.5)
        mock_processor.process.return_value = ProcessingResult(
            processed=5, skipped=3, errors=1, file_stats={".pdf": 2, ".txt": 3}, metrics=metrics
        )
        mock_processor_class.return_value = mock_processor

        with patch("email_processor.cli.ui.RICH_AVAILABLE", True):
            with patch("email_processor.cli.ui.Console", create=True) as mock_console_class:
                mock_console = MagicMock()
                mock_console_class.return_value = mock_console
                with patch("sys.argv", ["email_processor", "run"]):
                    with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                        mock_ui = MagicMock()
                        mock_ui_class.return_value = mock_ui
                        result = main()
                    self.assertEqual(result, 0)
                    # Results should be displayed
                    mock_display_results.assert_called_once()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.imap.fetcher.Fetcher")
    def test_main_without_rich_console(self, mock_processor_class, mock_load_config):
        """Test main function falls back to print when rich is not available."""
        mock_load_config.load.return_value = {
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
            processed=2, skipped=1, errors=0, file_stats={}, metrics=metrics
        )
        mock_processor_class.return_value = mock_processor

        with patch("email_processor.cli.ui.RICH_AVAILABLE", False):
            with patch("sys.argv", ["email_processor", "run"]):
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = False
                    mock_ui_class.return_value = mock_ui
                    result = main()
                    self.assertEqual(result, 0)
                    # Results should be displayed via UI (info or print)
                    # When has_rich is False, it uses info() instead of print()
                    self.assertTrue(mock_ui.info.called or mock_ui.print.called)

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.config.create_default_config")
    def test_create_config_with_rich_console(self, mock_create_config, mock_load_config):
        """Test create_config uses rich console when available."""
        mock_create_config.return_value = 0
        mock_console = MagicMock()

        with patch("email_processor.__main__.CLIUI") as mock_ui_class:
            mock_ui = MagicMock()
            mock_ui.has_rich = True
            mock_ui.console = mock_console
            mock_ui_class.return_value = mock_ui
            with patch("sys.argv", ["email_processor", "config", "init"]):
                result = main()
                self.assertEqual(result, 0)

    @patch("email_processor.__main__.ConfigLoader")
    def test_config_error_with_rich_console(self, mock_config_loader_class):
        """Test config error uses rich console when available."""
        mock_config_loader_class.load.side_effect = ValueError("Configuration validation failed")
        mock_console = MagicMock()

        with patch("email_processor.__main__.CLIUI") as mock_ui_class:
            mock_ui = MagicMock()
            mock_ui.has_rich = True
            mock_ui.console = mock_console
            mock_ui_class.return_value = mock_ui
            with patch("sys.argv", ["email_processor", "run"]):
                result = main()
                from email_processor.exit_codes import ExitCode

                self.assertEqual(result, ExitCode.CONFIG_ERROR)
                mock_ui.error.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    def test_config_error_without_rich_console(self, mock_config_loader_class):
        """Test config error falls back to print when rich is not available."""
        mock_config_loader_class.load.side_effect = ValueError("Configuration validation failed")

        with patch("email_processor.__main__.CLIUI") as mock_ui_class:
            mock_ui = MagicMock()
            mock_ui.has_rich = False
            mock_ui_class.return_value = mock_ui
            with patch("sys.argv", ["email_processor", "run"]):
                result = main()
                from email_processor.exit_codes import ExitCode

                self.assertEqual(result, ExitCode.CONFIG_ERROR)
                mock_ui.error.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    def test_file_not_found_error_with_rich_console(self, mock_config_loader_class):
        """Test file not found error uses rich console when available."""
        mock_config_loader_class.load.side_effect = FileNotFoundError(
            "Configuration file not found"
        )
        mock_console = MagicMock()

        with patch("email_processor.__main__.CLIUI") as mock_ui_class:
            mock_ui = MagicMock()
            mock_ui.has_rich = True
            mock_ui.console = mock_console
            mock_ui_class.return_value = mock_ui
            with patch("sys.argv", ["email_processor", "run"]):
                result = main()
                from email_processor.exit_codes import ExitCode

                self.assertEqual(result, ExitCode.CONFIG_ERROR)
                mock_ui.error.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    def test_unexpected_error_with_rich_console(self, mock_config_loader_class):
        """Test unexpected error uses rich console when available."""
        mock_config_loader_class.load.side_effect = Exception("Unexpected error")
        mock_console = MagicMock()

        with patch("email_processor.__main__.CLIUI") as mock_ui_class:
            mock_ui = MagicMock()
            mock_ui.has_rich = True
            mock_ui.console = mock_console
            mock_ui_class.return_value = mock_ui
            with patch("sys.argv", ["email_processor", "run"]):
                result = main()
                from email_processor.exit_codes import ExitCode

                self.assertEqual(result, ExitCode.CONFIG_ERROR)
                mock_ui.error.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    def test_unexpected_error_without_rich_console(self, mock_config_loader_class):
        """Test unexpected error falls back to print when rich is not available."""
        mock_config_loader_class.load.side_effect = Exception("Unexpected error")

        with patch("email_processor.__main__.CLIUI") as mock_ui_class:
            mock_ui = MagicMock()
            mock_ui.has_rich = False
            mock_ui_class.return_value = mock_ui
            with patch("sys.argv", ["email_processor", "run"]):
                result = main()
                from email_processor.exit_codes import ExitCode

                self.assertEqual(result, ExitCode.CONFIG_ERROR)
                mock_ui.error.assert_called()


class TestDisplayResultsRich(unittest.TestCase):
    """Tests for _display_results_rich function.

    Note: These tests are skipped if rich is not available, as the function
    requires rich.table.Table which is conditionally imported.
    """

    @unittest.skip("Rich module not available in test environment")
    def test_display_results_rich_basic(self):
        """Test displaying basic results with rich."""

    @unittest.skip("Rich module not available in test environment")
    def test_display_results_rich_with_file_stats(self):
        """Test displaying results with file statistics."""

    @unittest.skip("Rich module not available in test environment")
    def test_display_results_rich_with_metrics(self):
        """Test displaying results with performance metrics."""

    @unittest.skip("Rich module not available in test environment")
    def test_display_results_rich_with_metrics_short_time(self):
        """Test displaying results with metrics showing milliseconds."""

    @unittest.skip("Rich module not available in test environment")
    def test_display_results_rich_with_metrics_long_time(self):
        """Test displaying results with metrics showing minutes and seconds."""

    @unittest.skip("Rich module not available in test environment")
    def test_display_results_rich_with_errors(self):
        """Test displaying results with errors highlighted."""

    @unittest.skip("Table is conditionally imported, cannot mock easily")
    @patch("email_processor.cli.ui.RICH_AVAILABLE", True)
    @patch("email_processor.__main__.Table")
    def test_display_results_rich_basic_mocked(self, mock_table_class):
        """Test displaying basic results with rich (mocked)."""
        from email_processor.cli.commands.imap import _display_results_rich
        from email_processor.imap.fetcher import ProcessingResult

        mock_console = MagicMock()
        mock_table = MagicMock()
        mock_table_class.return_value = mock_table

        result = ProcessingResult(processed=5, skipped=3, errors=0, blocked=1)

        _display_results_rich(result, mock_console)

        mock_table_class.assert_called_once()
        mock_table.add_row.assert_called()
        mock_console.print.assert_called()

    @unittest.skip("Table is conditionally imported, cannot mock easily")
    @patch("email_processor.cli.ui.RICH_AVAILABLE", True)
    @patch("email_processor.__main__.Table")
    def test_display_results_rich_with_file_stats_mocked(self, mock_table_class):
        """Test displaying results with file statistics (mocked)."""
        from email_processor.cli.commands.imap import _display_results_rich
        from email_processor.imap.fetcher import ProcessingResult

        mock_console = MagicMock()
        mock_table = MagicMock()
        mock_table_class.return_value = mock_table

        result = ProcessingResult(
            processed=5, skipped=3, errors=0, blocked=1, file_stats={".pdf": 2, ".txt": 3}
        )

        _display_results_rich(result, mock_console)

        mock_table_class.assert_called()
        mock_table.add_row.assert_called()
        mock_console.print.assert_called()

    @unittest.skip("Table is conditionally imported, cannot mock easily")
    @patch("email_processor.cli.ui.RICH_AVAILABLE", True)
    @patch("email_processor.__main__.Table")
    def test_display_results_rich_with_metrics_mocked(self, mock_table_class):
        """Test displaying results with performance metrics (mocked)."""
        from email_processor.cli.commands.imap import _display_results_rich
        from email_processor.imap.fetcher import ProcessingMetrics, ProcessingResult

        mock_console = MagicMock()
        mock_table = MagicMock()
        mock_table_class.return_value = mock_table

        metrics = ProcessingMetrics(total_time=1.5)
        result = ProcessingResult(processed=5, skipped=3, errors=0, blocked=1, metrics=metrics)

        _display_results_rich(result, mock_console)

        mock_table_class.assert_called()
        mock_table.add_row.assert_called()
        mock_console.print.assert_called()

    @unittest.skip("Table is conditionally imported, cannot mock easily")
    @patch("email_processor.cli.ui.RICH_AVAILABLE", True)
    @patch("email_processor.__main__.Table")
    def test_display_results_rich_with_metrics_short_time_mocked(self, mock_table_class):
        """Test displaying results with metrics showing milliseconds (mocked)."""
        from email_processor.cli.commands.imap import _display_results_rich
        from email_processor.imap.fetcher import ProcessingMetrics, ProcessingResult

        mock_console = MagicMock()
        mock_table = MagicMock()
        mock_table_class.return_value = mock_table

        metrics = ProcessingMetrics(total_time=0.5)
        result = ProcessingResult(processed=5, skipped=3, errors=0, blocked=1, metrics=metrics)

        _display_results_rich(result, mock_console)

        mock_table_class.assert_called()
        mock_table.add_row.assert_called()
        mock_console.print.assert_called()

    @unittest.skip("Table is conditionally imported, cannot mock easily")
    @patch("email_processor.cli.ui.RICH_AVAILABLE", True)
    @patch("email_processor.__main__.Table")
    def test_display_results_rich_with_metrics_long_time_mocked(self, mock_table_class):
        """Test displaying results with metrics showing minutes and seconds (mocked)."""
        from email_processor.cli.commands.imap import _display_results_rich
        from email_processor.imap.fetcher import ProcessingMetrics, ProcessingResult

        mock_console = MagicMock()
        mock_table = MagicMock()
        mock_table_class.return_value = mock_table

        metrics = ProcessingMetrics(total_time=125.5)
        result = ProcessingResult(processed=5, skipped=3, errors=0, blocked=1, metrics=metrics)

        _display_results_rich(result, mock_console)

        mock_table_class.assert_called()
        mock_table.add_row.assert_called()
        mock_console.print.assert_called()

    @unittest.skip("Table is conditionally imported, cannot mock easily")
    @patch("email_processor.cli.ui.RICH_AVAILABLE", True)
    @patch("email_processor.__main__.Table")
    def test_display_results_rich_with_errors_mocked(self, mock_table_class):
        """Test displaying results with errors highlighted (mocked)."""
        from email_processor.cli.commands.imap import _display_results_rich
        from email_processor.imap.fetcher import ProcessingResult

        mock_console = MagicMock()
        mock_table = MagicMock()
        mock_table_class.return_value = mock_table

        result = ProcessingResult(processed=5, skipped=3, errors=2, blocked=1)

        _display_results_rich(result, mock_console)

        mock_table_class.assert_called()
        mock_table.add_row.assert_called()
        mock_console.print.assert_called()

    @unittest.skip("Table is conditionally imported, cannot mock easily")
    @patch("email_processor.cli.ui.RICH_AVAILABLE", True)
    @patch("email_processor.__main__.Table")
    def test_display_results_rich_with_full_metrics_mocked(self, mock_table_class):
        """Test displaying results with full metrics (mocked)."""
        from email_processor.cli.commands.imap import _display_results_rich
        from email_processor.imap.fetcher import ProcessingMetrics, ProcessingResult

        mock_console = MagicMock()
        mock_table = MagicMock()
        mock_table_class.return_value = mock_table

        metrics = ProcessingMetrics(
            total_time=1.5,
            per_email_time=[0.1, 0.2, 0.3],
            imap_operations=10,
            imap_operation_times=[0.05, 0.06, 0.07],
            total_downloaded_size=1024 * 1024,  # 1 MB
        )
        metrics.memory_current = 50 * 1024 * 1024  # 50 MB
        metrics.memory_peak = 60 * 1024 * 1024  # 60 MB
        result = ProcessingResult(processed=5, skipped=3, errors=0, blocked=1, metrics=metrics)

        _display_results_rich(result, mock_console)

        mock_table_class.assert_called()
        mock_table.add_row.assert_called()
        mock_console.print.assert_called()


class TestMainRichConsoleOutput(unittest.TestCase):
    """Tests for main function with rich console output."""

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.passwords.clear_passwords")
    def test_clear_passwords_with_rich_console(self, mock_clear_passwords, mock_load_config):
        """Test clear_passwords mode with rich console."""
        mock_load_config.load.return_value = {
            "imap": {
                "user": "test@example.com",
            },
        }
        mock_console = MagicMock()

        with (
            patch("email_processor.cli.ui.RICH_AVAILABLE", True),
            patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
        ):
            mock_console_class.return_value = mock_console
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = True
                mock_ui.console = mock_console
                mock_ui_class.return_value = mock_ui
                with patch(
                    "sys.argv",
                    ["email_processor", "password", "clear", "--user", "test@example.com"],
                ):
                    main()
                    mock_clear_passwords.assert_called_once()

    @patch("email_processor.__main__.ConfigLoader")
    def test_clear_passwords_missing_user_with_rich_console(self, mock_load_config):
        """Test clear_passwords mode with missing user and rich console."""
        mock_load_config.load.return_value = {
            "imap": {},
        }
        mock_console = MagicMock()

        with (
            patch("email_processor.cli.ui.RICH_AVAILABLE", True),
            patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
        ):
            mock_console_class.return_value = mock_console
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = True
                mock_ui.console = mock_console
                mock_ui_class.return_value = mock_ui
                with patch(
                    "sys.argv",
                    ["email_processor", "password", "clear", "--user", "test@example.com"],
                ):
                    result = main()
                    # Check appropriate exit code based on test context
                    self.assertIn(
                        result,
                        (
                            ExitCode.FILE_NOT_FOUND,
                            ExitCode.VALIDATION_FAILED,
                            ExitCode.CONFIG_ERROR,
                            ExitCode.PROCESSING_ERROR,
                        ),
                    )
                    mock_ui.error.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    def test_set_password_missing_user_with_rich_console(self, mock_load_config):
        """Test set_password mode with missing user and rich console."""
        mock_load_config.load.return_value = {
            "imap": {},
        }
        mock_console = MagicMock()

        with (
            patch("email_processor.cli.ui.RICH_AVAILABLE", True),
            patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
        ):
            mock_console_class.return_value = mock_console
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = True
                mock_ui.console = mock_console
                mock_ui_class.return_value = mock_ui
                with patch(
                    "sys.argv",
                    [
                        "email_processor",
                        "password",
                        "set",
                        "--user",
                        "test@example.com",
                        "--password-file",
                        "test.txt",
                    ],
                ):
                    result = main()
                    # Check appropriate exit code based on test context
                    self.assertIn(
                        result,
                        (
                            ExitCode.FILE_NOT_FOUND,
                            ExitCode.VALIDATION_FAILED,
                            ExitCode.CONFIG_ERROR,
                            ExitCode.PROCESSING_ERROR,
                        ),
                    )
                    mock_ui.error.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    def test_set_password_missing_password_file_with_rich_console(self, mock_load_config):
        """Test set_password mode with missing password_file arg and rich console."""
        mock_load_config.load.return_value = {
            "imap": {
                "user": "test@example.com",
            },
        }
        mock_console = MagicMock()

        with (
            patch("email_processor.cli.ui.RICH_AVAILABLE", True),
            patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
        ):
            mock_console_class.return_value = mock_console
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = True
                mock_ui.console = mock_console
                mock_ui_class.return_value = mock_ui
                mock_ui.input.return_value = ""  # Empty password
                with patch(
                    "sys.argv", ["email_processor", "password", "set", "--user", "test@example.com"]
                ):
                    result = main()
                    # Check appropriate exit code based on test context
                    self.assertIn(
                        result,
                        (
                            ExitCode.FILE_NOT_FOUND,
                            ExitCode.VALIDATION_FAILED,
                            ExitCode.CONFIG_ERROR,
                            ExitCode.PROCESSING_ERROR,
                        ),
                    )
                    mock_ui.error.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    def test_set_password_file_not_found_with_rich_console(self, mock_load_config):
        """Test set_password mode with file not found and rich console."""
        mock_load_config.load.return_value = {
            "imap": {
                "user": "test@example.com",
            },
        }
        mock_console = MagicMock()

        with (
            patch("email_processor.cli.ui.RICH_AVAILABLE", True),
            patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
        ):
            mock_console_class.return_value = mock_console
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = True
                mock_ui.console = mock_console
                mock_ui_class.return_value = mock_ui
                with patch(
                    "sys.argv",
                    [
                        "email_processor",
                        "password",
                        "set",
                        "--user",
                        "test@example.com",
                        "--password-file",
                        "/nonexistent/file",
                    ],
                ):
                    result = main()
                    # Check appropriate exit code based on test context
                    self.assertIn(
                        result,
                        (
                            ExitCode.FILE_NOT_FOUND,
                            ExitCode.VALIDATION_FAILED,
                            ExitCode.CONFIG_ERROR,
                            ExitCode.PROCESSING_ERROR,
                        ),
                    )
                    mock_ui.error.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.security.encryption.encrypt_password")
    @patch("keyring.set_password")
    def test_set_password_success_with_rich_console(
        self, mock_set_password, mock_encrypt, mock_load_config
    ):
        """Test set_password mode success with rich console."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            test_file = f.name
            f.write("testpassword\n")

        try:
            mock_load_config.load.return_value = {
                "imap": {
                    "user": "test@example.com",
                },
                "smtp": {},
            }
            mock_encrypt.return_value = "encrypted_password"
            mock_console = MagicMock()

            with (
                patch("email_processor.cli.ui.RICH_AVAILABLE", True),
                patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
            ):
                mock_console_class.return_value = mock_console
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = True
                    mock_ui.console = mock_console
                    mock_ui_class.return_value = mock_ui
                    with patch(
                        "sys.argv",
                        [
                            "email_processor",
                            "password",
                            "set",
                            "--user",
                            "test@example.com",
                            "--password-file",
                            test_file,
                        ],
                    ):
                        result = main()
                        self.assertEqual(result, 0)
                        mock_ui.success.assert_called()
        finally:
            Path(test_file).unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.passwords.encrypt_password")
    @patch("keyring.set_password")
    def test_set_password_encryption_fallback_with_rich_console(
        self, mock_set_password, mock_encrypt, mock_load_config
    ):
        """Test set_password mode with encryption fallback and rich console."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            test_file = f.name
            f.write("testpassword\n")

        try:
            mock_load_config.load.return_value = {
                "imap": {
                    "user": "test@example.com",
                },
                "smtp": {},
            }
            # encrypt_password raises exception, triggering fallback
            mock_encrypt.side_effect = Exception("Encryption error")
            # keyring.set_password should succeed in fallback
            mock_set_password.return_value = None
            mock_console = MagicMock()

            with (
                patch("email_processor.cli.ui.RICH_AVAILABLE", True),
                patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
            ):
                mock_console_class.return_value = mock_console
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = True
                    mock_ui.console = mock_console
                    mock_ui_class.return_value = mock_ui
                    with patch(
                        "sys.argv",
                        [
                            "email_processor",
                            "password",
                            "set",
                            "--user",
                            "test@example.com",
                            "--password-file",
                            test_file,
                        ],
                    ):
                        result = main()
                        self.assertEqual(result, 0)
                        # Should print warning about unencrypted password
                        mock_ui.warn.assert_called()
        finally:
            Path(test_file).unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.security.encryption.encrypt_password")
    @patch("keyring.set_password")
    def test_set_password_save_error_with_rich_console(
        self, mock_set_password, mock_encrypt, mock_load_config
    ):
        """Test set_password mode with save error and rich console."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            test_file = f.name
            f.write("testpassword\n")

        try:
            mock_load_config.load.return_value = {
                "imap": {
                    "user": "test@example.com",
                },
                "smtp": {},
            }
            mock_encrypt.side_effect = Exception("Encryption error")
            mock_set_password.side_effect = Exception("Keyring error")
            mock_console = MagicMock()

            with (
                patch("email_processor.cli.ui.RICH_AVAILABLE", True),
                patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
            ):
                mock_console_class.return_value = mock_console
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = True
                    mock_ui.console = mock_console
                    mock_ui_class.return_value = mock_ui
                    with patch(
                        "sys.argv",
                        [
                            "email_processor",
                            "password",
                            "set",
                            "--user",
                            "test@example.com",
                            "--password-file",
                            test_file,
                        ],
                    ):
                        result = main()
                        from email_processor.exit_codes import ExitCode

                        self.assertEqual(
                            result, ExitCode.UNSUPPORTED_FORMAT
                        )  # Authentication/keyring error
                        # Should print error
                        mock_ui.error.assert_called()
        finally:
            Path(test_file).unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.security.encryption.encrypt_password")
    @patch("keyring.set_password")
    def test_set_password_remove_file_with_rich_console(
        self, mock_set_password, mock_encrypt, mock_load_config
    ):
        """Test set_password mode with remove file and rich console."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            test_file = f.name
            f.write("testpassword\n")

        try:
            mock_load_config.load.return_value = {
                "imap": {
                    "user": "test@example.com",
                },
                "smtp": {},
            }
            mock_encrypt.return_value = "encrypted_password"
            mock_console = MagicMock()

            with (
                patch("email_processor.cli.ui.RICH_AVAILABLE", True),
                patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
            ):
                mock_console_class.return_value = mock_console
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = True
                    mock_ui.console = mock_console
                    mock_ui_class.return_value = mock_ui
                    with patch(
                        "sys.argv",
                        [
                            "email_processor",
                            "password",
                            "set",
                            "--user",
                            "test@example.com",
                            "--password-file",
                            test_file,
                            "--delete-after-read",
                        ],
                    ):
                        result = main()
                        self.assertEqual(result, 0)
                        # File should be deleted after reading
                        self.assertFalse(Path(test_file).exists())
                        mock_ui.success.assert_called()
        finally:
            Path(test_file).unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.security.encryption.encrypt_password")
    @patch("keyring.set_password")
    @patch("builtins.open", create=True)
    def test_set_password_remove_file_error_with_rich_console(
        self, mock_open, mock_set_password, mock_encrypt, mock_load_config
    ):
        """Test set_password mode with remove file error and rich console."""
        mock_load_config.load.return_value = {
            "imap": {
                "user": "test@example.com",
            },
            "smtp": {},
        }
        mock_encrypt.return_value = "encrypted_password"
        mock_console = MagicMock()

        # Mock file operations
        mock_file = MagicMock()
        mock_file.readline.return_value = "testpassword\n"
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock Path to return a mock object with unlink that raises exception
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.unlink.side_effect = Exception("Remove error")

        with (
            patch("email_processor.cli.ui.RICH_AVAILABLE", True),
        ):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = True
                mock_ui.console = mock_console
                mock_ui_class.return_value = mock_ui
                with patch("email_processor.cli.commands.passwords.Path", return_value=mock_path):
                    with patch(
                        "sys.argv",
                        [
                            "email_processor",
                            "password",
                            "set",
                            "--user",
                            "test@example.com",
                            "--password-file",
                            "test.txt",
                            "--delete-after-read",
                        ],
                    ):
                        result = main()
                        self.assertEqual(result, 0)  # Should not fail on remove error
                        # Check that warning was printed
                        mock_ui.warn.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.config.create_default_config")
    def test_create_config_example_not_found_with_rich_console(
        self, mock_create_config, mock_load_config
    ):
        """Test create_config with example not found and rich console."""
        mock_load_config.load.return_value = {}
        mock_console = MagicMock()
        mock_create_config.return_value = 1

        with (
            patch("email_processor.cli.ui.RICH_AVAILABLE", True),
            patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
        ):
            mock_console_class.return_value = mock_console
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = True
                mock_ui.console = mock_console
                mock_ui_class.return_value = mock_ui
                with patch("sys.argv", ["email_processor", "config", "init"]):
                    result = main()
                    self.assertEqual(result, 1)

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.config.create_default_config")
    def test_create_config_success_with_rich_console(self, mock_create_config, mock_load_config):
        """Test create_config success with rich console."""
        mock_load_config.load.return_value = {}
        mock_console = MagicMock()
        mock_create_config.return_value = 0

        with (
            patch("email_processor.cli.ui.RICH_AVAILABLE", True),
            patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
        ):
            mock_console_class.return_value = mock_console
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = True
                mock_ui.console = mock_console
                mock_ui_class.return_value = mock_ui
                with patch("sys.argv", ["email_processor", "config", "init"]):
                    result = main()
                    self.assertEqual(result, 0)

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_smtp_send_file_not_found_with_rich_console(
        self, mock_storage_class, mock_sender_class, mock_get_password, mock_load_config
    ):
        """Test SMTP send file not found with rich console."""
        mock_load_config.load.return_value = {
            "smtp": {
                "server": "smtp.example.com",
                "port": 587,
                "user": "test@example.com",
                "from_address": "test@example.com",
                "default_recipient": "recipient@example.com",
            },
        }
        mock_get_password.return_value = "password"
        mock_console = MagicMock()

        with (
            patch("email_processor.cli.ui.RICH_AVAILABLE", True),
            patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
        ):
            mock_console_class.return_value = mock_console
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = True
                mock_ui.console = mock_console
                mock_ui_class.return_value = mock_ui
                with patch(
                    "sys.argv",
                    [
                        "email_processor",
                        "send",
                        "file",
                        "/nonexistent/file",
                        "--to",
                        "test@example.com",
                    ],
                ):
                    result = main()
                    # Check appropriate exit code based on test context
                    self.assertIn(
                        result,
                        (
                            ExitCode.FILE_NOT_FOUND,
                            ExitCode.VALIDATION_FAILED,
                            ExitCode.CONFIG_ERROR,
                            ExitCode.PROCESSING_ERROR,
                        ),
                    )
                    mock_ui.error.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_smtp_send_file_not_a_file_with_rich_console(
        self, mock_storage_class, mock_sender_class, mock_get_password, mock_load_config
    ):
        """Test SMTP send when path is not a file with rich console."""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_load_config.load.return_value = {
                "smtp": {
                    "server": "smtp.example.com",
                    "port": 587,
                    "user": "test@example.com",
                    "from_address": "test@example.com",
                    "default_recipient": "recipient@example.com",
                },
            }
            mock_get_password.return_value = "password"
            mock_console = MagicMock()

            with (
                patch("email_processor.cli.ui.RICH_AVAILABLE", True),
                patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
            ):
                mock_console_class.return_value = mock_console
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = True
                    mock_ui.console = mock_console
                    mock_ui_class.return_value = mock_ui
                    with patch(
                        "sys.argv",
                        ["email_processor", "send", "file", temp_dir, "--to", "test@example.com"],
                    ):
                        result = main()
                        # Check appropriate exit code based on test context
                        self.assertIn(
                            result,
                            (
                                ExitCode.FILE_NOT_FOUND,
                                ExitCode.VALIDATION_FAILED,
                                ExitCode.CONFIG_ERROR,
                                ExitCode.PROCESSING_ERROR,
                            ),
                        )
                        mock_ui.error.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.smtp.smtp_connect")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_smtp_send_file_already_sent_with_rich_console(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test SMTP send file already sent with rich console."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_file = f.name

        try:
            mock_load_config.load.return_value = {
                "smtp": {
                    "server": "smtp.example.com",
                    "port": 587,
                    "user": "test@example.com",
                    "from_address": "test@example.com",
                    "default_recipient": "recipient@example.com",
                },
            }
            mock_get_password.return_value = "password"
            mock_smtp = MagicMock()
            mock_smtp_connect.return_value = mock_smtp
            mock_sender = MagicMock()
            mock_sender_class.return_value = mock_sender
            mock_storage = MagicMock()
            mock_storage.is_sent.return_value = True
            mock_storage_class.return_value = mock_storage
            mock_console = MagicMock()

            with (
                patch("email_processor.cli.ui.RICH_AVAILABLE", True),
                patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
            ):
                mock_console_class.return_value = mock_console
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = True
                    mock_ui.console = mock_console
                    mock_ui_class.return_value = mock_ui
                    with patch(
                        "sys.argv",
                        ["email_processor", "send", "file", test_file, "--to", "test@example.com"],
                    ):
                        result = main()
                        self.assertEqual(result, 0)
                        mock_ui.warn.assert_called()
        finally:
            Path(test_file).unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.smtp.smtp_connect")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_smtp_send_file_success_with_rich_console(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test SMTP send file success with rich console."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_file = f.name

        try:
            mock_load_config.load.return_value = {
                "smtp": {
                    "server": "smtp.example.com",
                    "port": 587,
                    "user": "test@example.com",
                    "from_address": "test@example.com",
                    "default_recipient": "recipient@example.com",
                },
            }
            mock_get_password.return_value = "password"
            mock_smtp_connect.return_value = MagicMock()
            mock_sender = MagicMock()
            mock_sender.send_file.return_value = True
            mock_sender_class.return_value = mock_sender
            mock_storage = MagicMock()
            mock_storage.is_sent.return_value = False
            mock_storage_class.return_value = mock_storage
            mock_console = MagicMock()

            with (
                patch("email_processor.cli.ui.RICH_AVAILABLE", True),
                patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
            ):
                mock_console_class.return_value = mock_console
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = True
                    mock_ui.console = mock_console
                    mock_ui_class.return_value = mock_ui
                    with patch(
                        "sys.argv",
                        ["email_processor", "send", "file", test_file, "--to", "test@example.com"],
                    ):
                        result = main()
                        self.assertEqual(result, 0)
                        mock_ui.success.assert_called()
        finally:
            Path(test_file).unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_smtp_send_file_dry_run_with_rich_console(
        self, mock_storage_class, mock_sender_class, mock_get_password, mock_load_config
    ):
        """Test SMTP send file dry-run with rich console."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_file = f.name

        try:
            mock_load_config.load.return_value = {
                "smtp": {
                    "server": "smtp.example.com",
                    "port": 587,
                    "user": "test@example.com",
                    "from_address": "test@example.com",
                    "default_recipient": "recipient@example.com",
                },
            }
            mock_get_password.return_value = "password"
            mock_sender = MagicMock()
            mock_sender.send_file.return_value = True
            mock_sender_class.return_value = mock_sender
            mock_storage = MagicMock()
            mock_storage.is_sent.return_value = False
            mock_storage_class.return_value = mock_storage
            mock_console = MagicMock()

            with (
                patch("email_processor.cli.ui.RICH_AVAILABLE", True),
                patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
            ):
                mock_console_class.return_value = mock_console
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = True
                    mock_ui.console = mock_console
                    mock_ui_class.return_value = mock_ui
                    with patch(
                        "sys.argv",
                        [
                            "email_processor",
                            "send",
                            "file",
                            test_file,
                            "--dry-run",
                            "--to",
                            "test@example.com",
                        ],
                    ):
                        result = main()
                        self.assertEqual(result, 0)
                        # Should show dry-run message
                        if mock_ui.has_rich:
                            mock_ui.print.assert_called()
                        else:
                            mock_ui.info.assert_called()
        finally:
            Path(test_file).unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.smtp.smtp_connect")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_smtp_send_file_failed_with_rich_console(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test SMTP send file failed with rich console."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_file = f.name

        try:
            mock_load_config.load.return_value = {
                "smtp": {
                    "server": "smtp.example.com",
                    "port": 587,
                    "user": "test@example.com",
                    "from_address": "test@example.com",
                    "default_recipient": "recipient@example.com",
                },
            }
            mock_get_password.return_value = "password"
            mock_smtp_connect.return_value = MagicMock()
            mock_sender = MagicMock()
            mock_sender.send_file.return_value = False
            mock_sender_class.return_value = mock_sender
            mock_storage = MagicMock()
            mock_storage.is_sent.return_value = False
            mock_storage_class.return_value = mock_storage
            mock_console = MagicMock()

            with (
                patch("email_processor.cli.ui.RICH_AVAILABLE", True),
                patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
            ):
                mock_console_class.return_value = mock_console
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = True
                    mock_ui.console = mock_console
                    mock_ui_class.return_value = mock_ui
                    with patch(
                        "sys.argv",
                        ["email_processor", "send", "file", test_file, "--to", "test@example.com"],
                    ):
                        result = main()
                        # Check appropriate exit code based on test context
                        self.assertIn(
                            result,
                            (
                                ExitCode.FILE_NOT_FOUND,
                                ExitCode.VALIDATION_FAILED,
                                ExitCode.CONFIG_ERROR,
                                ExitCode.PROCESSING_ERROR,
                            ),
                        )
                        mock_ui.error.assert_called()
        finally:
            Path(test_file).unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_smtp_send_folder_not_found_with_rich_console(
        self, mock_storage_class, mock_sender_class, mock_get_password, mock_load_config
    ):
        """Test SMTP send folder not found with rich console."""
        mock_load_config.load.return_value = {
            "smtp": {
                "server": "smtp.example.com",
                "port": 587,
                "user": "test@example.com",
                "from_address": "test@example.com",
                "default_recipient": "recipient@example.com",
            },
        }
        mock_get_password.return_value = "password"
        mock_console = MagicMock()

        with (
            patch("email_processor.cli.ui.RICH_AVAILABLE", True),
            patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
        ):
            mock_console_class.return_value = mock_console
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = True
                mock_ui.console = mock_console
                mock_ui_class.return_value = mock_ui
                with patch(
                    "sys.argv",
                    [
                        "email_processor",
                        "send",
                        "folder",
                        "/nonexistent/folder",
                        "--to",
                        "test@example.com",
                    ],
                ):
                    result = main()
                    # Check appropriate exit code based on test context
                    self.assertIn(
                        result,
                        (
                            ExitCode.FILE_NOT_FOUND,
                            ExitCode.VALIDATION_FAILED,
                            ExitCode.CONFIG_ERROR,
                            ExitCode.PROCESSING_ERROR,
                        ),
                    )
                    mock_ui.error.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_smtp_send_folder_not_a_directory_with_rich_console(
        self, mock_storage_class, mock_sender_class, mock_get_password, mock_load_config
    ):
        """Test SMTP send when folder path is not a directory with rich console."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            test_file = f.name

        try:
            mock_load_config.load.return_value = {
                "smtp": {
                    "server": "smtp.example.com",
                    "port": 587,
                    "user": "test@example.com",
                    "from_address": "test@example.com",
                    "default_recipient": "recipient@example.com",
                },
            }
            mock_get_password.return_value = "password"
            mock_console = MagicMock()

            with (
                patch("email_processor.cli.ui.RICH_AVAILABLE", True),
                patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
            ):
                mock_console_class.return_value = mock_console
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = True
                    mock_ui.console = mock_console
                    mock_ui_class.return_value = mock_ui
                    with patch(
                        "sys.argv",
                        [
                            "email_processor",
                            "send",
                            "folder",
                            test_file,
                            "--to",
                            "test@example.com",
                        ],
                    ):
                        result = main()
                        # Check appropriate exit code based on test context
                        self.assertIn(
                            result,
                            (
                                ExitCode.FILE_NOT_FOUND,
                                ExitCode.VALIDATION_FAILED,
                                ExitCode.CONFIG_ERROR,
                                ExitCode.PROCESSING_ERROR,
                            ),
                        )
                        mock_ui.error.assert_called()
        finally:
            Path(test_file).unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.smtp.smtp_connect")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_smtp_send_folder_success_with_rich_console(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test SMTP send folder success with rich console."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file1 = Path(temp_dir) / "file1.txt"
            test_file1.write_text("content1")
            test_file2 = Path(temp_dir) / "file2.txt"
            test_file2.write_text("content2")

            mock_load_config.load.return_value = {
                "smtp": {
                    "server": "smtp.example.com",
                    "port": 587,
                    "user": "test@example.com",
                    "from_address": "test@example.com",
                    "default_recipient": "recipient@example.com",
                },
            }
            mock_get_password.return_value = "password"
            mock_smtp = MagicMock()
            mock_smtp_connect.return_value = mock_smtp
            mock_sender = MagicMock()
            mock_sender.send_file.return_value = True
            mock_sender_class.return_value = mock_sender
            mock_storage = MagicMock()
            mock_storage.is_sent.return_value = False
            mock_storage_class.return_value = mock_storage
            mock_console = MagicMock()

            with (
                patch("email_processor.cli.ui.RICH_AVAILABLE", True),
                patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
            ):
                mock_console_class.return_value = mock_console
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = True
                    mock_ui.console = mock_console
                    mock_ui_class.return_value = mock_ui
                    with patch(
                        "sys.argv",
                        ["email_processor", "send", "folder", temp_dir, "--to", "test@example.com"],
                    ):
                        result = main()
                        self.assertEqual(result, 0)
                        # Should show results
                        if mock_ui.has_rich:
                            mock_ui.print.assert_called()
                        else:
                            mock_ui.info.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.smtp.smtp_connect")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_smtp_send_folder_partial_failure_with_rich_console(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test SMTP send folder with partial failure and rich console."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file1 = Path(temp_dir) / "file1.txt"
            test_file1.write_text("content1")
            test_file2 = Path(temp_dir) / "file2.txt"
            test_file2.write_text("content2")

            mock_load_config.load.return_value = {
                "smtp": {
                    "server": "smtp.example.com",
                    "port": 587,
                    "user": "test@example.com",
                    "from_address": "test@example.com",
                    "default_recipient": "recipient@example.com",
                },
            }
            mock_get_password.return_value = "password"
            mock_smtp_connect.return_value = MagicMock()
            mock_sender = MagicMock()
            # First file succeeds, second fails
            mock_sender.send_file.side_effect = [True, False]
            mock_sender_class.return_value = mock_sender
            mock_storage = MagicMock()
            mock_storage.is_sent.return_value = False
            mock_storage_class.return_value = mock_storage
            mock_console = MagicMock()

            with (
                patch("email_processor.cli.ui.RICH_AVAILABLE", True),
                patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
            ):
                mock_console_class.return_value = mock_console
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = True
                    mock_ui.console = mock_console
                    mock_ui_class.return_value = mock_ui
                    with patch(
                        "sys.argv",
                        ["email_processor", "send", "folder", temp_dir, "--to", "test@example.com"],
                    ):
                        result = main()
                        self.assertEqual(result, 1)
                        # Should show results with failures
                        # When has_rich is True, print() is called multiple times
                        # Check that UI output was called (print, info, or warn)
                        self.assertTrue(
                            mock_ui.print.called or mock_ui.info.called or mock_ui.warn.called,
                            "UI output should be called to show results",
                        )

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    def test_smtp_send_missing_config_with_rich_console(self, mock_get_password, mock_load_config):
        """Test SMTP send with missing SMTP config and rich console."""
        mock_load_config.load.return_value = {
            "imap": {
                "user": "test@example.com",
            },
        }
        mock_console = MagicMock()

        with (
            patch("email_processor.cli.ui.RICH_AVAILABLE", True),
            patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
        ):
            mock_console_class.return_value = mock_console
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = True
                mock_ui.console = mock_console
                mock_ui_class.return_value = mock_ui
                with patch(
                    "sys.argv",
                    ["email_processor", "send", "file", "test.txt", "--to", "test@example.com"],
                ):
                    result = main()
                    # Check appropriate exit code based on test context
                    self.assertIn(
                        result,
                        (
                            ExitCode.FILE_NOT_FOUND,
                            ExitCode.VALIDATION_FAILED,
                            ExitCode.CONFIG_ERROR,
                            ExitCode.PROCESSING_ERROR,
                        ),
                    )
                    mock_ui.error.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    def test_smtp_send_missing_server_with_rich_console(self, mock_get_password, mock_load_config):
        """Test SMTP send with missing server and rich console."""
        mock_load_config.load.return_value = {
            "smtp": {
                "port": 587,
                "user": "test@example.com",
                "from_address": "test@example.com",
            },
        }
        mock_console = MagicMock()

        with (
            patch("email_processor.cli.ui.RICH_AVAILABLE", True),
            patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
        ):
            mock_console_class.return_value = mock_console
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = True
                mock_ui.console = mock_console
                mock_ui_class.return_value = mock_ui
                with patch(
                    "sys.argv",
                    ["email_processor", "send", "file", "test.txt", "--to", "test@example.com"],
                ):
                    result = main()
                    # Check appropriate exit code based on test context
                    self.assertIn(
                        result,
                        (
                            ExitCode.FILE_NOT_FOUND,
                            ExitCode.VALIDATION_FAILED,
                            ExitCode.CONFIG_ERROR,
                            ExitCode.PROCESSING_ERROR,
                        ),
                    )
                    mock_ui.error.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    def test_smtp_send_missing_user_with_rich_console(self, mock_get_password, mock_load_config):
        """Test SMTP send with missing user and rich console."""
        mock_load_config.load.return_value = {
            "smtp": {
                "server": "smtp.example.com",
                "port": 587,
                "from_address": "test@example.com",
            },
        }
        mock_console = MagicMock()

        with (
            patch("email_processor.cli.ui.RICH_AVAILABLE", True),
            patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
        ):
            mock_console_class.return_value = mock_console
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = True
                mock_ui.console = mock_console
                mock_ui_class.return_value = mock_ui
                with patch(
                    "sys.argv",
                    ["email_processor", "send", "file", "test.txt", "--to", "test@example.com"],
                ):
                    result = main()
                    # Check appropriate exit code based on test context
                    self.assertIn(
                        result,
                        (
                            ExitCode.FILE_NOT_FOUND,
                            ExitCode.VALIDATION_FAILED,
                            ExitCode.CONFIG_ERROR,
                            ExitCode.PROCESSING_ERROR,
                        ),
                    )
                    mock_ui.error.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    def test_smtp_send_missing_from_address_with_rich_console(
        self, mock_get_password, mock_load_config
    ):
        """Test SMTP send with missing from_address and rich console."""
        mock_load_config.load.return_value = {
            "smtp": {
                "server": "smtp.example.com",
                "port": 587,
                "user": "test@example.com",
            },
        }
        mock_console = MagicMock()

        with (
            patch("email_processor.cli.ui.RICH_AVAILABLE", True),
            patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
        ):
            mock_console_class.return_value = mock_console
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = True
                mock_ui.console = mock_console
                mock_ui_class.return_value = mock_ui
                with patch(
                    "sys.argv",
                    ["email_processor", "send", "file", "test.txt", "--to", "test@example.com"],
                ):
                    result = main()
                    # Check appropriate exit code based on test context
                    self.assertIn(
                        result,
                        (
                            ExitCode.FILE_NOT_FOUND,
                            ExitCode.VALIDATION_FAILED,
                            ExitCode.CONFIG_ERROR,
                            ExitCode.PROCESSING_ERROR,
                        ),
                    )
                    mock_ui.error.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    def test_smtp_send_missing_recipient_with_rich_console(
        self, mock_get_password, mock_load_config
    ):
        """Test SMTP send with missing recipient and rich console."""
        mock_load_config.load.return_value = {
            "smtp": {
                "server": "smtp.example.com",
                "port": 587,
                "user": "test@example.com",
                "from_address": "test@example.com",
            },
        }
        mock_get_password.return_value = "password"
        mock_console = MagicMock()

        with (
            patch("email_processor.cli.ui.RICH_AVAILABLE", True),
            patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
        ):
            mock_console_class.return_value = mock_console
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = True
                mock_ui.console = mock_console
                mock_ui_class.return_value = mock_ui
                with patch(
                    "sys.argv",
                    ["email_processor", "send", "file", "test.txt", "--to", "test@example.com"],
                ):
                    result = main()
                    # Check appropriate exit code based on test context
                    self.assertIn(
                        result,
                        (
                            ExitCode.FILE_NOT_FOUND,
                            ExitCode.VALIDATION_FAILED,
                            ExitCode.CONFIG_ERROR,
                            ExitCode.PROCESSING_ERROR,
                        ),
                    )
                    mock_ui.error.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    def test_smtp_send_password_error_with_rich_console(self, mock_get_password, mock_load_config):
        """Test SMTP send with password error and rich console."""
        mock_load_config.load.return_value = {
            "smtp": {
                "server": "smtp.example.com",
                "port": 587,
                "user": "test@example.com",
                "from_address": "test@example.com",
                "default_recipient": "recipient@example.com",
            },
        }
        mock_get_password.side_effect = Exception("Password error")
        mock_console = MagicMock()

        with (
            patch("email_processor.cli.ui.RICH_AVAILABLE", True),
            patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
        ):
            mock_console_class.return_value = mock_console
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = True
                mock_ui.console = mock_console
                mock_ui_class.return_value = mock_ui
                with patch(
                    "sys.argv",
                    ["email_processor", "send", "file", "test.txt", "--to", "test@example.com"],
                ):
                    result = main()
                    # Check appropriate exit code based on test context
                    self.assertIn(
                        result,
                        (
                            ExitCode.FILE_NOT_FOUND,
                            ExitCode.VALIDATION_FAILED,
                            ExitCode.CONFIG_ERROR,
                            ExitCode.PROCESSING_ERROR,
                        ),
                    )
                    mock_ui.error.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.config.create_default_config")
    def test_create_config_os_error_with_rich_console(self, mock_create_config, mock_load_config):
        """Test create_config with OSError and rich console."""
        mock_load_config.load.return_value = {}
        mock_console = MagicMock()
        mock_create_config.return_value = 1

        with (
            patch("email_processor.cli.ui.RICH_AVAILABLE", True),
            patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
        ):
            mock_console_class.return_value = mock_console
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = True
                mock_ui.console = mock_console
                mock_ui_class.return_value = mock_ui
                with patch("sys.argv", ["email_processor", "config", "init"]):
                    result = main()
                    self.assertEqual(result, 1)

    @patch("shutil.copy2")
    @patch("email_processor.cli.commands.config.Path")
    def test_create_default_config_example_not_found_with_rich_console(
        self, mock_path_class, mock_copy
    ):
        """Test create_default_config when example file not found with rich console."""
        example_path = MagicMock()
        example_path.exists.return_value = False
        example_path.absolute.return_value = Path("/path/to/config.yaml.example")

        def path_side_effect(path_str):
            if "example" in str(path_str):
                return example_path
            return Path(path_str)

        mock_path_class.side_effect = path_side_effect

        ui = CLIUI()
        with patch.object(ui, "error") as mock_error:
            result = create_default_config("config.yaml", ui)
            self.assertEqual(result, ExitCode.FILE_NOT_FOUND)
            mock_error.assert_called_once()

    @patch("email_processor.cli.commands.config.Path")
    def test_create_default_config_cancel_with_rich_console(self, mock_path_class):
        """Test create_default_config when user cancels with rich console."""
        example_path = MagicMock()
        example_path.exists.return_value = True

        target_path = MagicMock()
        target_path.exists.return_value = True

        def path_side_effect(path_str):
            if "example" in str(path_str):
                return example_path
            return target_path

        mock_path_class.side_effect = path_side_effect

        ui = CLIUI()
        with patch.object(ui, "input", return_value="n"):
            with patch.object(ui, "warn") as mock_warn:
                result = create_default_config("config.yaml", ui)
                self.assertEqual(result, 0)
                mock_warn.assert_called_once_with("Cancelled.")

    @patch("email_processor.cli.commands.config.Path")
    @patch("email_processor.cli.commands.config.shutil.copy2")
    def test_create_default_config_success_with_rich_console(self, mock_copy, mock_path_class):
        """Test create_default_config successfully creates config file with rich console."""
        example_path = MagicMock()
        example_path.exists.return_value = True
        example_path.absolute.return_value = Path("/path/to/config.yaml.example")

        target_path = MagicMock()
        target_path.exists.return_value = False
        target_path.parent = MagicMock()
        target_path.parent.mkdir.return_value = None
        target_path.absolute.return_value = Path("/path/to/config.yaml")

        def path_side_effect(path_str):
            if "example" in str(path_str):
                return example_path
            return target_path

        mock_path_class.side_effect = path_side_effect

        ui = CLIUI()
        result = create_default_config("config.yaml", ui)
        self.assertEqual(result, 0)
        mock_copy.assert_called_once_with(example_path, target_path)

    @patch("email_processor.cli.commands.config.Path")
    @patch("email_processor.cli.commands.config.shutil.copy2")
    def test_create_default_config_os_error_with_rich_console(self, mock_copy, mock_path_class):
        """Test create_default_config with OSError and rich console."""
        example_path = MagicMock()
        example_path.exists.return_value = True

        target_path = MagicMock()
        target_path.exists.return_value = False
        target_path.parent = MagicMock()
        target_path.parent.mkdir.side_effect = OSError("Permission denied")

        def path_side_effect(path_str):
            if "example" in str(path_str):
                return example_path
            return target_path

        mock_path_class.side_effect = path_side_effect

        ui = CLIUI()
        with patch.object(ui, "error") as mock_error:
            result = create_default_config("config.yaml", ui)
            self.assertEqual(result, 1)
            mock_error.assert_called_once()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.security.encryption.encrypt_password")
    @patch("keyring.set_password")
    def test_set_password_file_permission_error_with_rich_console(
        self, mock_set_password, mock_encrypt, mock_load_config
    ):
        """Test set_password with PermissionError reading file and rich console."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            test_file = f.name
            f.write("testpassword\n")

        try:
            mock_load_config.load.return_value = {
                "imap": {
                    "user": "test@example.com",
                },
                "smtp": {},
            }
            mock_console = MagicMock()

            with (
                patch("email_processor.cli.ui.RICH_AVAILABLE", True),
                patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
            ):
                mock_console_class.return_value = mock_console
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = True
                    mock_ui.console = mock_console
                    mock_ui_class.return_value = mock_ui
                    with patch("builtins.open", side_effect=PermissionError("Permission denied")):
                        with patch(
                            "sys.argv",
                            [
                                "email_processor",
                                "password",
                                "set",
                                "--user",
                                "test@example.com",
                                "--password-file",
                                test_file,
                            ],
                        ):
                            result = main()
                            self.assertEqual(result, ExitCode.FILE_NOT_FOUND)
                            mock_ui.error.assert_called()
        finally:
            Path(test_file).unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.security.encryption.encrypt_password")
    @patch("keyring.set_password")
    def test_set_password_file_read_error_with_rich_console(
        self, mock_set_password, mock_encrypt, mock_load_config
    ):
        """Test set_password with read error and rich console."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            test_file = f.name
            f.write("testpassword\n")

        try:
            mock_load_config.load.return_value = {
                "imap": {
                    "user": "test@example.com",
                },
                "smtp": {},
            }
            mock_console = MagicMock()

            with (
                patch("email_processor.cli.ui.RICH_AVAILABLE", True),
                patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
            ):
                mock_console_class.return_value = mock_console
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = True
                    mock_ui.console = mock_console
                    mock_ui_class.return_value = mock_ui
                    with patch("builtins.open", side_effect=OSError("Read error")):
                        with patch(
                            "sys.argv",
                            [
                                "email_processor",
                                "password",
                                "set",
                                "--user",
                                "test@example.com",
                                "--password-file",
                                test_file,
                            ],
                        ):
                            result = main()
                            self.assertEqual(result, ExitCode.FILE_NOT_FOUND)
                            mock_ui.error.assert_called()
        finally:
            Path(test_file).unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.security.encryption.encrypt_password")
    @patch("keyring.set_password")
    def test_set_password_file_empty_with_rich_console(
        self, mock_set_password, mock_encrypt, mock_load_config
    ):
        """Test set_password with empty file and rich console."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            test_file = f.name
            f.write("")

        try:
            mock_load_config.load.return_value = {
                "imap": {
                    "user": "test@example.com",
                },
                "smtp": {},
            }
            mock_console = MagicMock()

            with (
                patch("email_processor.cli.ui.RICH_AVAILABLE", True),
                patch("email_processor.cli.ui.Console", create=True) as mock_console_class,
            ):
                mock_console_class.return_value = mock_console
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = True
                    mock_ui.console = mock_console
                    mock_ui_class.return_value = mock_ui
                    with patch(
                        "sys.argv",
                        [
                            "email_processor",
                            "password",
                            "set",
                            "--user",
                            "test@example.com",
                            "--password-file",
                            test_file,
                        ],
                    ):
                        result = main()
                        # Check appropriate exit code based on test context
                        self.assertIn(
                            result,
                            (
                                ExitCode.FILE_NOT_FOUND,
                                ExitCode.VALIDATION_FAILED,
                                ExitCode.CONFIG_ERROR,
                                ExitCode.PROCESSING_ERROR,
                            ),
                        )
                        mock_ui.error.assert_called()
        finally:
            Path(test_file).unlink(missing_ok=True)
