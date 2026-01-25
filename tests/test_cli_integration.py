"""Integration tests for CLI commands end-to-end."""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import ANY, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from email_processor.__main__ import main
from email_processor.exit_codes import ExitCode


class TestCLIIntegration(unittest.TestCase):
    """Integration tests for CLI commands."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "config.yaml"
        self.config_file.write_text(
            """imap:
  server: imap.example.com
  user: test@example.com
  max_retries: 3
  retry_delay: 1
processing:
  start_days_back: 5
  archive_folder: INBOX/Processed
  processed_dir: processed_uids
  keep_processed_days: 0
allowed_senders:
  - sender@example.com
topic_mapping:
  ".*": downloads/default
logging:
  level: INFO
  format: console
"""
        )

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("email_processor.__main__.ConfigLoader")
    def test_config_init_command(self, mock_config_loader_class):
        """Test config init command."""
        mock_config_loader_class.load.side_effect = FileNotFoundError("Config not found")

        with patch("sys.argv", ["email_processor", "config", "init"]):
            with patch("email_processor.cli.commands.config.create_default_config") as mock_create:
                mock_create.return_value = 0
                result = main()
                self.assertEqual(result, 0)
                mock_create.assert_called_once()

    @patch("email_processor.__main__.ConfigLoader")
    def test_config_validate_command(self, mock_config_loader_class):
        """Test config validate command."""
        mock_config_loader_class.load.return_value = {
            "imap": {"server": "imap.example.com", "user": "test@example.com"},
            "processing": {},
            "allowed_senders": [],
        }

        with patch("sys.argv", ["email_processor", "config", "validate"]):
            with patch("email_processor.cli.commands.config.validate_config_file") as mock_validate:
                mock_validate.return_value = 0
                result = main()
                self.assertEqual(result, 0)
                mock_validate.assert_called_once()

    @patch("email_processor.__main__.ConfigLoader")
    def test_status_command(self, mock_config_loader_class):
        """Test status command."""
        mock_config_loader_class.load.return_value = {
            "imap": {"server": "imap.example.com", "user": "test@example.com"},
            "smtp": {"server": "smtp.example.com"},
            "processing": {},
            "allowed_senders": ["sender@example.com"],
            "topic_mapping": {"test": "path"},
        }

        with patch("sys.argv", ["email_processor", "status"]):
            with patch("email_processor.cli.commands.status.show_status") as mock_status:
                mock_status.return_value = 0
                result = main()
                self.assertEqual(result, 0)
                mock_status.assert_called_once()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.passwords.set_password")
    def test_password_set_command(self, mock_set_password, mock_config_loader_class):
        """Test password set command."""
        mock_config_loader_class.load.return_value = {"imap": {"user": "test@example.com"}}
        mock_set_password.return_value = 0

        with patch(
            "sys.argv", ["email_processor", "password", "set", "--user", "test@example.com"]
        ):
            result = main()
            self.assertEqual(result, 0)
            mock_set_password.assert_called_once()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.passwords.clear_passwords")
    def test_password_clear_command(self, mock_clear_passwords, mock_config_loader_class):
        """Test password clear command."""
        mock_config_loader_class.load.return_value = {"imap": {}}
        mock_clear_passwords.return_value = 0

        with patch(
            "sys.argv", ["email_processor", "password", "clear", "--user", "test@example.com"]
        ):
            result = main()
            self.assertEqual(result, 0)
            mock_clear_passwords.assert_called_once()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.passwords.clear_passwords")
    def test_password_clear_uses_imap_user_from_config(
        self, mock_clear_passwords, mock_config_loader_class
    ):
        """Test password clear without --user uses imap.user from config."""
        mock_config_loader_class.load.return_value = {
            "imap": {"user": "config_user@example.com"},
            "processing": {},
        }
        mock_clear_passwords.return_value = 0
        with patch("sys.argv", ["email_processor", "password", "clear"]):
            result = main()
            self.assertEqual(result, 0)
            mock_clear_passwords.assert_called_once_with("config_user@example.com", ANY)

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.passwords.set_password")
    def test_password_set_uses_imap_user_from_config(
        self, mock_set_password, mock_config_loader_class
    ):
        """Test password set without --user uses imap.user from config."""
        mock_config_loader_class.load.return_value = {
            "imap": {"user": "config_user@example.com"},
            "processing": {},
        }
        mock_set_password.return_value = 0
        pwd_file = Path(self.temp_dir) / "pwd.txt"
        pwd_file.write_text("secret\n")
        with patch(
            "sys.argv",
            [
                "email_processor",
                "password",
                "set",
                "--password-file",
                str(pwd_file),
            ],
        ):
            result = main()
            self.assertEqual(result, 0)
            mock_set_password.assert_called_once()
            self.assertEqual(mock_set_password.call_args[0][0], "config_user@example.com")

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.send_file")
    def test_send_file_command(self, mock_send_file, mock_config_loader_class):
        """Test send file command."""
        mock_config_loader_class.load.return_value = {"smtp": {}}
        mock_send_file.return_value = 0

        test_file = Path(self.temp_dir) / "test.pdf"
        test_file.write_bytes(b"test content")

        with patch(
            "sys.argv",
            ["email_processor", "send", "file", str(test_file), "--to", "test@example.com"],
        ):
            result = main()
            self.assertEqual(result, 0)
            mock_send_file.assert_called_once()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.send_folder")
    def test_send_folder_command(self, mock_send_folder, mock_config_loader_class):
        """Test send folder command."""
        mock_config_loader_class.load.return_value = {"smtp": {}}
        mock_send_folder.return_value = 0

        test_folder = Path(self.temp_dir) / "test_folder"
        test_folder.mkdir()
        (test_folder / "file1.pdf").write_bytes(b"content1")
        (test_folder / "file2.pdf").write_bytes(b"content2")

        with patch(
            "sys.argv",
            [
                "email_processor",
                "send",
                "folder",
                str(test_folder),
                "--to",
                "test@example.com",
            ],
        ):
            result = main()
            self.assertEqual(result, 0)
            mock_send_folder.assert_called_once()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.send_folder")
    def test_send_without_subcommand_uses_folder_config_defaults(
        self, mock_send_folder, mock_config_loader_class
    ):
        """Test 'send' without subcommand defaults to send folder from config."""
        test_folder = Path(self.temp_dir) / "outbox"
        test_folder.mkdir()
        (test_folder / "a.txt").write_bytes(b"a")
        mock_config_loader_class.load.return_value = {
            "smtp": {
                "send_folder": str(test_folder),
                "default_recipient": "default@example.com",
            },
        }
        mock_send_folder.return_value = 0

        with patch("sys.argv", ["email_processor", "send"]):
            result = main()
            self.assertEqual(result, 0)
            mock_send_folder.assert_called_once()
            call_args = mock_send_folder.call_args[0]
            self.assertEqual(call_args[1], str(test_folder))
            self.assertEqual(call_args[2], "default@example.com")

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.imap.run_processor")
    def test_fetch_command(self, mock_run_processor, mock_config_loader_class):
        """Test fetch command."""
        mock_config_loader_class.load.return_value = {
            "imap": {"server": "imap.example.com", "user": "test@example.com"},
            "processing": {},
            "allowed_senders": [],
        }
        from email_processor.imap.fetcher import ProcessingMetrics, ProcessingResult

        mock_run_processor.return_value = ProcessingResult(
            processed=2,
            skipped=1,
            errors=0,
            file_stats={},
            metrics=ProcessingMetrics(total_time=1.0),
        )

        with patch("sys.argv", ["email_processor", "fetch"]):
            result = main()
            # run_processor returns ProcessingResult, main() may return it or convert to exit code
            # Check that run_processor was called successfully
            mock_run_processor.assert_called_once()
            # Result should be either ProcessingResult or exit code (0 for success)
            from email_processor.imap.fetcher import ProcessingResult

            self.assertTrue(
                isinstance(result, ProcessingResult) or result == 0,
                f"Expected ProcessingResult or 0, got {type(result)}: {result}",
            )

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.imap.run_processor")
    def test_run_command(self, mock_run_processor, mock_config_loader_class):
        """Test run command."""
        mock_config_loader_class.load.return_value = {
            "imap": {"server": "imap.example.com", "user": "test@example.com"},
            "processing": {},
            "allowed_senders": [],
        }
        from email_processor.imap.fetcher import ProcessingMetrics, ProcessingResult

        mock_run_processor.return_value = ProcessingResult(
            processed=2,
            skipped=1,
            errors=0,
            file_stats={},
            metrics=ProcessingMetrics(total_time=1.0),
        )

        with patch("sys.argv", ["email_processor", "run"]):
            result = main()
            # run_processor returns ProcessingResult, main() may return it or convert to exit code
            # Check that run_processor was called successfully
            mock_run_processor.assert_called_once()
            # Result should be either ProcessingResult or exit code (0 for success)
            from email_processor.imap.fetcher import ProcessingResult

            self.assertTrue(
                isinstance(result, ProcessingResult) or result == 0,
                f"Expected ProcessingResult or 0, got {type(result)}: {result}",
            )


class TestCLIErrorHandling(unittest.TestCase):
    """Integration tests for CLI error handling."""

    def test_missing_command(self):
        """Test handling of missing command."""
        with patch("sys.argv", ["email_processor"]):
            # argparse will show help and exit with code 2, or may run default behavior
            # Let's check that it either raises SystemExit or returns a valid exit code
            try:
                result = main()
                # If no exception, should be a valid exit code
                self.assertIsInstance(result, (int, type(None)))
            except SystemExit as e:
                # SystemExit is expected for missing command
                self.assertIn(e.code, (None, 0, 2))

    def test_invalid_command(self):
        """Test handling of invalid command."""
        with patch("sys.argv", ["email_processor", "invalid_command"]):
            # argparse will raise SystemExit for invalid command
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, ExitCode.VALIDATION_FAILED)

    @patch("email_processor.__main__.ConfigLoader")
    def test_config_file_not_found(self, mock_config_loader_class):
        """Test handling of missing config file."""
        mock_config_loader_class.load.side_effect = FileNotFoundError("Config not found")

        with patch("sys.argv", ["email_processor", "run"]):
            result = main()
            self.assertEqual(result, ExitCode.CONFIG_ERROR)

    @patch("email_processor.__main__.ConfigLoader")
    def test_config_validation_error(self, mock_config_loader_class):
        """Test handling of config validation error."""
        mock_config_loader_class.load.side_effect = ValueError("Invalid config")

        with patch("sys.argv", ["email_processor", "run"]):
            result = main()
            self.assertEqual(result, ExitCode.CONFIG_ERROR)


if __name__ == "__main__":
    unittest.main()
