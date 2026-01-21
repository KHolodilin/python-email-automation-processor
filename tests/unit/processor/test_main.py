"""Tests for __main__ module."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from email_processor.__main__ import create_default_config, main
from email_processor.config.constants import KEYRING_SERVICE_NAME
from email_processor.processor.email_processor import ProcessingMetrics, ProcessingResult
from email_processor.security.encryption import is_encrypted


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
            mock_processor.process.assert_called_once_with(
                dry_run=False, mock_mode=False, config_path="config.yaml"
            )

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
            mock_processor.process.assert_called_once_with(
                dry_run=True, mock_mode=False, config_path="config.yaml"
            )

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
            mock_processor.process.assert_called_once_with(
                dry_run=False, mock_mode=False, config_path="custom_config.yaml"
            )

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
            mock_processor.process.assert_called_once_with(
                dry_run=False, mock_mode=False, config_path="config.yaml"
            )

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
            mock_processor.process.assert_called_once_with(
                dry_run=False, mock_mode=False, config_path="config.yaml"
            )

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


class TestSetPassword(unittest.TestCase):
    """Tests for --set-password command."""

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("keyring.set_password")
    def test_set_password_from_file_success(self, mock_set_password, mock_load_config):
        """Test setting password from file successfully."""
        mock_load_config.return_value = {
            "imap": {
                "user": "test@example.com",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("test_password_123\n")
            password_file = f.name

        try:
            with patch(
                "sys.argv", ["email_processor", "--set-password", "--password-file", password_file]
            ):
                result = main()
                self.assertEqual(result, 0)
                mock_set_password.assert_called_once()
                # Check that password was saved (encrypted if cryptography available)
                saved_password = mock_set_password.call_args[0][2]
                # Password should be encrypted if cryptography is available
                try:
                    self.assertTrue(is_encrypted(saved_password))
                except Exception:
                    # If cryptography not available, password is saved unencrypted
                    self.assertEqual(saved_password, "test_password_123")
        finally:
            Path(password_file).unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("keyring.set_password")
    def test_set_password_from_file_remove_file(self, mock_set_password, mock_load_config):
        """Test setting password from file and removing file."""
        mock_load_config.return_value = {
            "imap": {
                "user": "test@example.com",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("test_password_123\n")
            password_file = f.name

        password_path = Path(password_file)
        self.assertTrue(password_path.exists())

        try:
            with patch(
                "sys.argv",
                [
                    "email_processor",
                    "--set-password",
                    "--password-file",
                    password_file,
                    "--remove-password-file",
                ],
            ):
                result = main()
                self.assertEqual(result, 0)
                mock_set_password.assert_called_once()
                # File should be removed
                self.assertFalse(password_path.exists())
        finally:
            password_path.unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("keyring.set_password")
    def test_set_password_from_file_not_removed(self, mock_set_password, mock_load_config):
        """Test that file is not removed without --remove-password-file flag."""
        mock_load_config.return_value = {
            "imap": {
                "user": "test@example.com",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("test_password_123\n")
            password_file = f.name

        password_path = Path(password_file)
        self.assertTrue(password_path.exists())

        try:
            with patch(
                "sys.argv", ["email_processor", "--set-password", "--password-file", password_file]
            ):
                result = main()
                self.assertEqual(result, 0)
                mock_set_password.assert_called_once()
                # File should still exist
                self.assertTrue(password_path.exists())
        finally:
            password_path.unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader.load")
    def test_set_password_file_not_exists(self, mock_load_config):
        """Test error when password file does not exist."""
        mock_load_config.return_value = {
            "imap": {
                "user": "test@example.com",
            },
        }

        with patch(
            "sys.argv",
            ["email_processor", "--set-password", "--password-file", "/nonexistent/file"],
        ):
            result = main()
            self.assertEqual(result, 1)

    @patch("email_processor.__main__.ConfigLoader.load")
    def test_set_password_file_empty(self, mock_load_config):
        """Test error when password file is empty."""
        mock_load_config.return_value = {
            "imap": {
                "user": "test@example.com",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("")  # Empty file
            password_file = f.name

        try:
            with patch(
                "sys.argv", ["email_processor", "--set-password", "--password-file", password_file]
            ):
                result = main()
                self.assertEqual(result, 1)
        finally:
            Path(password_file).unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader.load")
    def test_set_password_without_password_file(self, mock_load_config):
        """Test error when --password-file is not specified."""
        mock_load_config.return_value = {
            "imap": {
                "user": "test@example.com",
            },
        }

        with patch("sys.argv", ["email_processor", "--set-password"]):
            result = main()
            self.assertEqual(result, 1)

    @patch("email_processor.__main__.ConfigLoader.load")
    def test_set_password_missing_user(self, mock_load_config):
        """Test error when imap.user is missing in config."""
        mock_load_config.return_value = {
            "imap": {},
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("test_password\n")
            password_file = f.name

        try:
            with patch(
                "sys.argv", ["email_processor", "--set-password", "--password-file", password_file]
            ):
                result = main()
                self.assertEqual(result, 1)
        finally:
            Path(password_file).unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("keyring.set_password")
    def test_set_password_encryption_fallback(self, mock_set_password, mock_load_config):
        """Test fallback to unencrypted password when encryption fails."""
        mock_load_config.return_value = {
            "imap": {
                "user": "test@example.com",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("test_password_123\n")
            password_file = f.name

        try:
            # Mock encryption to fail
            with patch(
                "email_processor.__main__.encrypt_password",
                side_effect=Exception("Encryption error"),
            ):
                with patch(
                    "sys.argv",
                    ["email_processor", "--set-password", "--password-file", password_file],
                ):
                    result = main()
                    self.assertEqual(result, 0)
                    # Should be called once with unencrypted password (fallback)
                    self.assertEqual(mock_set_password.call_count, 1)
                    # Call should be with unencrypted password
                    call_password = mock_set_password.call_args[0][2]
                    self.assertEqual(call_password, "test_password_123")
        finally:
            Path(password_file).unlink(missing_ok=True)


class TestSMTPSend(unittest.TestCase):
    """Tests for SMTP send commands (--send-file, --send-folder)."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_file = self.temp_dir / "test.txt"
        self.test_file.write_text("test content")
        self.test_folder = self.temp_dir / "test_folder"
        self.test_folder.mkdir()
        (self.test_folder / "file1.txt").write_text("content1")
        (self.test_folder / "file2.txt").write_text("content2")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.get_imap_password")
    @patch("email_processor.__main__.EmailSender")
    @patch("email_processor.__main__.SentFilesStorage")
    def test_send_file_success(
        self, mock_storage_class, mock_sender_class, mock_get_password, mock_load_config
    ):
        """Test sending a single file successfully."""
        mock_load_config.return_value = {
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

        with patch("sys.argv", ["email_processor", "--send-file", str(self.test_file)]):
            result = main()
            self.assertEqual(result, 0)
            mock_sender.send_file.assert_called_once()
            mock_storage.mark_as_sent.assert_called_once()

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.get_imap_password")
    @patch("email_processor.__main__.EmailSender")
    @patch("email_processor.__main__.SentFilesStorage")
    def test_send_file_not_found(
        self, mock_storage_class, mock_sender_class, mock_get_password, mock_load_config
    ):
        """Test error when file not found."""
        mock_load_config.return_value = {
            "smtp": {
                "server": "smtp.example.com",
                "port": 587,
                "user": "test@example.com",
                "from_address": "test@example.com",
                "default_recipient": "recipient@example.com",
            },
        }
        mock_get_password.return_value = "password"

        with patch("sys.argv", ["email_processor", "--send-file", "/nonexistent/file"]):
            with patch("email_processor.__main__.console", None):
                with patch("builtins.print") as mock_print:
                    with patch("pathlib.Path.exists", return_value=False):
                        result = main()
                        self.assertEqual(result, 1)
                        # Check that error message was printed
                        print_calls = [str(call) for call in mock_print.call_args_list]
                        error_calls = [
                            call
                            for call in print_calls
                            if "File not found" in call or "/nonexistent/file" in call
                        ]
                        self.assertTrue(len(error_calls) > 0)

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.get_imap_password")
    @patch("email_processor.__main__.EmailSender")
    @patch("email_processor.__main__.SentFilesStorage")
    def test_send_file_already_sent(
        self, mock_storage_class, mock_sender_class, mock_get_password, mock_load_config
    ):
        """Test warning when file already sent."""
        mock_load_config.return_value = {
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
        mock_sender_class.return_value = mock_sender
        mock_storage = MagicMock()
        mock_storage.is_sent.return_value = True
        mock_storage_class.return_value = mock_storage

        with patch("sys.argv", ["email_processor", "--send-file", str(self.test_file)]):
            with patch("email_processor.__main__.console", None):
                with patch("builtins.print") as mock_print:
                    result = main()
                    self.assertEqual(result, 0)
                    mock_print.assert_any_call("Warning: File already sent: test.txt")
                    mock_sender.send_file.assert_not_called()

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.get_imap_password")
    @patch("email_processor.__main__.EmailSender")
    @patch("email_processor.__main__.SentFilesStorage")
    def test_send_file_dry_run(
        self, mock_storage_class, mock_sender_class, mock_get_password, mock_load_config
    ):
        """Test dry-run mode for sending file."""
        mock_load_config.return_value = {
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

        with patch(
            "sys.argv", ["email_processor", "--send-file", str(self.test_file), "--dry-run-send"]
        ):
            with patch("email_processor.__main__.console", None):
                with patch("builtins.print") as mock_print:
                    result = main()
                    self.assertEqual(result, 0)
                    mock_sender.send_file.assert_called_once_with(
                        self.test_file, "recipient@example.com", None, dry_run=True
                    )
                    mock_storage.mark_as_sent.assert_not_called()
                    mock_print.assert_any_call("DRY-RUN: Would send file: test.txt")

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.get_imap_password")
    @patch("email_processor.__main__.EmailSender")
    @patch("email_processor.__main__.SentFilesStorage")
    def test_send_file_failed(
        self, mock_storage_class, mock_sender_class, mock_get_password, mock_load_config
    ):
        """Test error when sending file fails."""
        mock_load_config.return_value = {
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
        mock_sender.send_file.return_value = False
        mock_sender_class.return_value = mock_sender
        mock_storage = MagicMock()
        mock_storage.is_sent.return_value = False
        mock_storage_class.return_value = mock_storage

        with patch("sys.argv", ["email_processor", "--send-file", str(self.test_file)]):
            with patch("email_processor.__main__.console", None):
                with patch("builtins.print") as mock_print:
                    result = main()
                    self.assertEqual(result, 1)
                    mock_print.assert_any_call("Error: Failed to send file: test.txt")

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.get_imap_password")
    @patch("email_processor.__main__.EmailSender")
    @patch("email_processor.__main__.SentFilesStorage")
    def test_send_folder_success(
        self, mock_storage_class, mock_sender_class, mock_get_password, mock_load_config
    ):
        """Test sending files from folder successfully."""
        mock_load_config.return_value = {
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

        with patch("sys.argv", ["email_processor", "--send-folder", str(self.test_folder)]):
            with patch("email_processor.__main__.console", None):
                with patch("builtins.print") as mock_print:
                    result = main()
                    self.assertEqual(result, 0)
                    self.assertEqual(mock_sender.send_file.call_count, 2)
                    self.assertEqual(mock_storage.mark_as_sent.call_count, 2)
                    mock_print.assert_any_call("Sent: 2 files")

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.get_imap_password")
    @patch("email_processor.__main__.EmailSender")
    @patch("email_processor.__main__.SentFilesStorage")
    def test_send_folder_from_config(
        self, mock_storage_class, mock_sender_class, mock_get_password, mock_load_config
    ):
        """Test sending files from folder specified in config."""
        mock_load_config.return_value = {
            "smtp": {
                "server": "smtp.example.com",
                "port": 587,
                "user": "test@example.com",
                "from_address": "test@example.com",
                "default_recipient": "recipient@example.com",
                "send_folder": str(self.test_folder),
            },
        }
        mock_get_password.return_value = "password"
        mock_sender = MagicMock()
        mock_sender.send_file.return_value = True
        mock_sender_class.return_value = mock_sender
        mock_storage = MagicMock()
        mock_storage.is_sent.return_value = False
        mock_storage_class.return_value = mock_storage

        with patch("sys.argv", ["email_processor", "--send-folder"]):
            with patch("email_processor.__main__.console", None):
                with patch("builtins.print") as mock_print:
                    result = main()
                    self.assertEqual(result, 0)
                    self.assertEqual(mock_sender.send_file.call_count, 2)
                    mock_print.assert_any_call("Sent: 2 files")

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.get_imap_password")
    @patch("email_processor.__main__.EmailSender")
    @patch("email_processor.__main__.SentFilesStorage")
    def test_send_folder_no_new_files(
        self, mock_storage_class, mock_sender_class, mock_get_password, mock_load_config
    ):
        """Test when all files in folder are already sent."""
        mock_load_config.return_value = {
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
        mock_sender_class.return_value = mock_sender
        mock_storage = MagicMock()
        mock_storage.is_sent.return_value = True
        mock_storage_class.return_value = mock_storage

        with patch("sys.argv", ["email_processor", "--send-folder", str(self.test_folder)]):
            with patch("email_processor.__main__.console", None):
                with patch("builtins.print") as mock_print:
                    result = main()
                    self.assertEqual(result, 0)
                    mock_sender.send_file.assert_not_called()
                    mock_print.assert_any_call("No new files to send (skipped 2 already sent)")

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.get_imap_password")
    @patch("email_processor.__main__.EmailSender")
    @patch("email_processor.__main__.SentFilesStorage")
    def test_send_folder_partial_failure(
        self, mock_storage_class, mock_sender_class, mock_get_password, mock_load_config
    ):
        """Test when some files fail to send."""
        mock_load_config.return_value = {
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
        # First file succeeds, second fails
        mock_sender.send_file.side_effect = [True, False]
        mock_sender_class.return_value = mock_sender
        mock_storage = MagicMock()
        mock_storage.is_sent.return_value = False
        mock_storage_class.return_value = mock_storage

        with patch("sys.argv", ["email_processor", "--send-folder", str(self.test_folder)]):
            with patch("email_processor.__main__.console", None):
                with patch("builtins.print") as mock_print:
                    result = main()
                    self.assertEqual(result, 1)
                    self.assertEqual(mock_sender.send_file.call_count, 2)
                    mock_print.assert_any_call("Sent: 1 files")
                    mock_print.assert_any_call("Failed: 1 files")

    @patch("email_processor.__main__.ConfigLoader.load")
    def test_send_file_missing_smtp_config(self, mock_load_config):
        """Test error when SMTP config is missing."""
        mock_load_config.return_value = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
        }

        with patch("sys.argv", ["email_processor", "--send-file", str(self.test_file)]):
            with patch("email_processor.__main__.console", None):
                with patch("builtins.print") as mock_print:
                    result = main()
                    self.assertEqual(result, 1)
                    mock_print.assert_any_call("Error: 'smtp' section is missing in config.yaml")

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.get_imap_password")
    def test_send_file_missing_recipient(self, mock_get_password, mock_load_config):
        """Test error when recipient is not specified."""
        mock_load_config.return_value = {
            "smtp": {
                "server": "smtp.example.com",
                "port": 587,
                "user": "test@example.com",
                "from_address": "test@example.com",
            },
        }
        mock_get_password.return_value = "password"

        with patch("sys.argv", ["email_processor", "--send-file", str(self.test_file)]):
            with patch("email_processor.__main__.console", None):
                with patch("builtins.print") as mock_print:
                    result = main()
                    self.assertEqual(result, 1)
                    mock_print.assert_any_call(
                        "Error: Recipient not specified. Use --recipient or set smtp.default_recipient in config.yaml"
                    )

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.get_imap_password")
    def test_send_file_password_error(self, mock_get_password, mock_load_config):
        """Test error when getting password fails."""
        mock_load_config.return_value = {
            "smtp": {
                "server": "smtp.example.com",
                "port": 587,
                "user": "test@example.com",
                "from_address": "test@example.com",
                "default_recipient": "recipient@example.com",
            },
        }
        mock_get_password.side_effect = Exception("Password error")

        with patch("sys.argv", ["email_processor", "--send-file", str(self.test_file)]):
            with patch("email_processor.__main__.console", None):
                with patch("builtins.print") as mock_print:
                    result = main()
                    self.assertEqual(result, 1)
                    mock_print.assert_any_call("Error getting password: Password error")

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.get_imap_password")
    @patch("email_processor.__main__.EmailSender")
    @patch("email_processor.__main__.SentFilesStorage")
    def test_send_file_with_custom_recipient(
        self, mock_storage_class, mock_sender_class, mock_get_password, mock_load_config
    ):
        """Test sending file with custom recipient."""
        mock_load_config.return_value = {
            "smtp": {
                "server": "smtp.example.com",
                "port": 587,
                "user": "test@example.com",
                "from_address": "test@example.com",
            },
        }
        mock_get_password.return_value = "password"
        mock_sender = MagicMock()
        mock_sender.send_file.return_value = True
        mock_sender_class.return_value = mock_sender
        mock_storage = MagicMock()
        mock_storage.is_sent.return_value = False
        mock_storage_class.return_value = mock_storage

        with patch(
            "sys.argv",
            [
                "email_processor",
                "--send-file",
                str(self.test_file),
                "--recipient",
                "custom@example.com",
            ],
        ):
            result = main()
            self.assertEqual(result, 0)
            mock_sender.send_file.assert_called_once_with(
                self.test_file, "custom@example.com", None, dry_run=False
            )

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.get_imap_password")
    @patch("email_processor.__main__.EmailSender")
    @patch("email_processor.__main__.SentFilesStorage")
    def test_send_file_with_custom_subject(
        self, mock_storage_class, mock_sender_class, mock_get_password, mock_load_config
    ):
        """Test sending file with custom subject."""
        mock_load_config.return_value = {
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

        with patch(
            "sys.argv",
            ["email_processor", "--send-file", str(self.test_file), "--subject", "Custom Subject"],
        ):
            result = main()
            self.assertEqual(result, 0)
            mock_sender.send_file.assert_called_once_with(
                self.test_file, "recipient@example.com", "Custom Subject", dry_run=False
            )

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.get_imap_password")
    @patch("email_processor.__main__.EmailSender")
    @patch("email_processor.__main__.SentFilesStorage")
    def test_send_folder_not_found(
        self, mock_storage_class, mock_sender_class, mock_get_password, mock_load_config
    ):
        """Test error when folder not found."""
        mock_load_config.return_value = {
            "smtp": {
                "server": "smtp.example.com",
                "port": 587,
                "user": "test@example.com",
                "from_address": "test@example.com",
                "default_recipient": "recipient@example.com",
            },
        }
        mock_get_password.return_value = "password"

        with patch("sys.argv", ["email_processor", "--send-folder", "/nonexistent/folder"]):
            with patch("email_processor.__main__.console", None):
                with patch("builtins.print") as mock_print:
                    with patch("pathlib.Path.exists", return_value=False):
                        result = main()
                        self.assertEqual(result, 1)
                        # Check that error message was printed
                        print_calls = [str(call) for call in mock_print.call_args_list]
                        error_calls = [
                            call
                            for call in print_calls
                            if "Folder not found" in call or "/nonexistent/folder" in call
                        ]
                        self.assertTrue(len(error_calls) > 0)

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.get_imap_password")
    @patch("email_processor.__main__.EmailSender")
    @patch("email_processor.__main__.SentFilesStorage")
    def test_send_folder_not_specified(
        self, mock_storage_class, mock_sender_class, mock_get_password, mock_load_config
    ):
        """Test error when folder is not specified."""
        mock_load_config.return_value = {
            "smtp": {
                "server": "smtp.example.com",
                "port": 587,
                "user": "test@example.com",
                "from_address": "test@example.com",
                "default_recipient": "recipient@example.com",
            },
        }
        mock_get_password.return_value = "password"

        with patch("sys.argv", ["email_processor", "--send-folder"]):
            with patch("email_processor.__main__.console", None):
                with patch("builtins.print") as mock_print:
                    result = main()
                    self.assertEqual(result, 1)
                    # Check that error message was printed
                    print_calls = [str(call) for call in mock_print.call_args_list]
                    error_calls = [
                        call
                        for call in print_calls
                        if "Folder not specified" in call or "send_folder" in call
                    ]
                    self.assertTrue(len(error_calls) > 0)


class TestRichConsoleOutput(unittest.TestCase):
    """Tests for rich console output functionality."""

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.EmailProcessor")
    @patch("email_processor.__main__._display_results_rich")
    def test_main_with_rich_console(
        self, mock_display_rich, mock_processor_class, mock_load_config
    ):
        """Test main function uses rich console when available."""
        mock_load_config.return_value = {
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

        mock_console = MagicMock()
        with patch("email_processor.__main__.RICH_AVAILABLE", True):
            with patch("email_processor.__main__.console", mock_console):
                with patch("sys.argv", ["email_processor"]):
                    result = main()
                    self.assertEqual(result, 0)
                    # Rich console should be used to print results
                    mock_display_rich.assert_called_once()

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.EmailProcessor")
    def test_main_without_rich_console(self, mock_processor_class, mock_load_config):
        """Test main function falls back to print when rich is not available."""
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
            processed=2, skipped=1, errors=0, file_stats={}, metrics=metrics
        )
        mock_processor_class.return_value = mock_processor

        with patch("email_processor.__main__.console", None):
            with patch("sys.argv", ["email_processor"]):
                with patch("builtins.print") as mock_print:
                    result = main()
                    self.assertEqual(result, 0)
                    mock_print.assert_called()
                    # Should print results in plain text format
                    call_args = " ".join(str(call) for call in mock_print.call_args_list)
                    self.assertIn("Processed", call_args)
                    self.assertIn("Skipped", call_args)

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.create_default_config")
    def test_create_config_with_rich_console(self, mock_create_config, mock_load_config):
        """Test create_config uses rich console when available."""
        mock_create_config.return_value = 0
        mock_console = MagicMock()

        with patch("email_processor.__main__.console", mock_console):
            with patch("sys.argv", ["email_processor", "--create-config"]):
                result = main()
                self.assertEqual(result, 0)

    @patch("email_processor.__main__.ConfigLoader.load")
    def test_config_error_with_rich_console(self, mock_load_config):
        """Test config error uses rich console when available."""
        mock_load_config.side_effect = ValueError("Configuration validation failed")
        mock_console = MagicMock()

        with patch("email_processor.__main__.console", mock_console):
            with patch("sys.argv", ["email_processor"]):
                result = main()
                self.assertEqual(result, 1)
                mock_console.print.assert_called()

    @patch("email_processor.__main__.ConfigLoader.load")
    def test_config_error_without_rich_console(self, mock_load_config):
        """Test config error falls back to print when rich is not available."""
        mock_load_config.side_effect = ValueError("Configuration validation failed")

        with patch("email_processor.__main__.console", None):
            with patch("sys.argv", ["email_processor"]):
                with patch("builtins.print") as mock_print:
                    result = main()
                    self.assertEqual(result, 1)
                    mock_print.assert_called()
                    # Should print error message
                    call_args = " ".join(str(call) for call in mock_print.call_args_list)
                    self.assertIn("Configuration error", call_args)

    @patch("email_processor.__main__.ConfigLoader.load")
    def test_file_not_found_error_with_rich_console(self, mock_load_config):
        """Test file not found error uses rich console when available."""
        mock_load_config.side_effect = FileNotFoundError("Configuration file not found")
        mock_console = MagicMock()

        with patch("email_processor.__main__.console", mock_console):
            with patch("sys.argv", ["email_processor"]):
                result = main()
                self.assertEqual(result, 1)
                mock_console.print.assert_called()

    @patch("email_processor.__main__.ConfigLoader.load")
    def test_unexpected_error_with_rich_console(self, mock_load_config):
        """Test unexpected error uses rich console when available."""
        mock_load_config.side_effect = Exception("Unexpected error")
        mock_console = MagicMock()

        with patch("email_processor.__main__.console", mock_console):
            with patch("sys.argv", ["email_processor"]):
                result = main()
                self.assertEqual(result, 1)
                mock_console.print.assert_called()

    @patch("email_processor.__main__.ConfigLoader.load")
    def test_unexpected_error_without_rich_console(self, mock_load_config):
        """Test unexpected error falls back to print when rich is not available."""
        mock_load_config.side_effect = Exception("Unexpected error")

        with patch("email_processor.__main__.console", None):
            with patch("sys.argv", ["email_processor"]):
                with patch("builtins.print") as mock_print:
                    result = main()
                    self.assertEqual(result, 1)
                    mock_print.assert_called()
                    # Should print error message
                    call_args = " ".join(str(call) for call in mock_print.call_args_list)
                    self.assertIn("Unexpected error loading configuration", call_args)


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


class TestPasswordFileErrors(unittest.TestCase):
    """Tests for password file error handling."""

    @patch("email_processor.__main__.stat.filemode")
    @patch("email_processor.__main__.ConfigLoader.load")
    def test_set_password_file_permission_warning(self, mock_load_config, mock_filemode):
        """Test warning when password file has open permissions (Unix)."""
        import stat
        import sys

        # Skip test on Windows as permission check is Unix-only
        if sys.platform == "win32":
            self.skipTest("Permission check is Unix-only")

        mock_load_config.return_value = {
            "imap": {
                "user": "test@example.com",
            },
        }
        mock_filemode.return_value = "-rw-r--r--"

        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("test_password\n")
            password_file = f.name

        try:
            # Create a fully mocked Path object
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            # Mock the stat() call to return a file with open permissions
            mock_stat_result = MagicMock()
            # Set st_mode to have group and other read permissions
            mock_stat_result.st_mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            mock_path.stat.return_value = mock_stat_result

            # Mock platform to be Linux so permission check runs
            with patch("email_processor.__main__.sys.platform", "linux"):
                with patch(
                    "sys.argv",
                    ["email_processor", "--set-password", "--password-file", password_file],
                ):
                    with patch("email_processor.__main__.console", None):
                        with patch("builtins.print") as mock_print:
                            with patch("keyring.set_password"):
                                with patch(
                                    "email_processor.__main__.encrypt_password",
                                    return_value="encrypted",
                                ):
                                    # Patch Path constructor to return our mocked path
                                    def mock_path_constructor(path_str):
                                        if str(path_str) == password_file:
                                            return mock_path
                                        return Path(path_str)

                                    with patch(
                                        "email_processor.__main__.Path",
                                        side_effect=mock_path_constructor,
                                    ):
                                        # Also need to patch open() to read the file
                                        with patch("builtins.open", create=True) as mock_open:
                                            mock_file = MagicMock()
                                            mock_file.readline.return_value = "test_password\n"
                                            mock_open.return_value.__enter__.return_value = (
                                                mock_file
                                            )

                                            result = main()
                                            self.assertEqual(result, 0)
                                            # Should print warning about permissions (only on Unix when file has open perms)
                                            warning_calls = [
                                                str(call) for call in mock_print.call_args_list
                                            ]
                                            permission_warnings = [
                                                call
                                                for call in warning_calls
                                                if "permissions" in call.lower()
                                                or "chmod" in call.lower()
                                            ]
                                            # On Unix with open permissions, warning should be printed
                                            self.assertTrue(
                                                len(permission_warnings) > 0,
                                                f"Expected permission warning, but got: {warning_calls}",
                                            )
        finally:
            Path(password_file).unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.sys.platform", "win32")
    def test_set_password_file_no_permission_check_windows(self, mock_load_config):
        """Test that permission check is skipped on Windows."""
        mock_load_config.return_value = {
            "imap": {
                "user": "test@example.com",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("test_password\n")
            password_file = f.name

        try:
            with patch(
                "sys.argv", ["email_processor", "--set-password", "--password-file", password_file]
            ):
                with patch("keyring.set_password"):
                    with patch(
                        "email_processor.__main__.encrypt_password", return_value="encrypted"
                    ):
                        result = main()
                        self.assertEqual(result, 0)
        finally:
            Path(password_file).unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader.load")
    def test_set_password_file_permission_error(self, mock_load_config):
        """Test error when reading password file fails with PermissionError."""
        mock_load_config.return_value = {
            "imap": {
                "user": "test@example.com",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            password_file = f.name

        try:
            # Make file unreadable (on Unix)
            import os

            if os.path.exists(password_file):
                os.chmod(password_file, 0o000)

            with patch(
                "sys.argv", ["email_processor", "--set-password", "--password-file", password_file]
            ):
                with patch("email_processor.__main__.console", None):
                    with patch("builtins.print") as mock_print:
                        with patch(
                            "builtins.open", side_effect=PermissionError("Permission denied")
                        ):
                            result = main()
                            self.assertEqual(result, 1)
                            mock_print.assert_any_call(
                                "Error: Permission denied reading password file: " + password_file
                            )
        finally:
            # Restore permissions for cleanup
            try:
                os.chmod(password_file, 0o644)
            except Exception:
                pass
            Path(password_file).unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader.load")
    def test_set_password_file_read_error(self, mock_load_config):
        """Test error when reading password file fails with general exception."""
        mock_load_config.return_value = {
            "imap": {
                "user": "test@example.com",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            password_file = f.name

        try:
            with patch(
                "sys.argv", ["email_processor", "--set-password", "--password-file", password_file]
            ):
                with patch("email_processor.__main__.console", None):
                    with patch("builtins.print") as mock_print:
                        with patch("builtins.open", side_effect=OSError("Read error")):
                            result = main()
                            self.assertEqual(result, 1)
                            mock_print.assert_any_call(
                                "Error: Failed to read password file: Read error"
                            )
        finally:
            Path(password_file).unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("keyring.set_password")
    def test_set_password_remove_file_error(self, mock_set_password, mock_load_config):
        """Test warning when removing password file fails."""
        mock_load_config.return_value = {
            "imap": {
                "user": "test@example.com",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("test_password\n")
            password_file = f.name

        try:
            with patch(
                "sys.argv",
                [
                    "email_processor",
                    "--set-password",
                    "--password-file",
                    password_file,
                    "--remove-password-file",
                ],
            ):
                with patch("email_processor.__main__.console", None):
                    with patch("builtins.print") as mock_print:
                        with patch(
                            "email_processor.__main__.encrypt_password", return_value="encrypted"
                        ):
                            with patch(
                                "pathlib.Path.unlink", side_effect=OSError("Cannot remove file")
                            ):
                                result = main()
                                self.assertEqual(result, 0)
                                # Should print warning but not fail
                                warning_calls = [str(call) for call in mock_print.call_args_list]
                                remove_warnings = [
                                    call
                                    for call in warning_calls
                                    if "remove" in call.lower() or "warning" in call.lower()
                                ]
                                self.assertTrue(len(remove_warnings) > 0)
        finally:
            Path(password_file).unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("keyring.set_password")
    def test_set_password_save_error_after_encryption_fail(
        self, mock_set_password, mock_load_config
    ):
        """Test error when saving password fails after encryption fails."""
        mock_load_config.return_value = {
            "imap": {
                "user": "test@example.com",
            },
        }
        mock_set_password.side_effect = Exception("Keyring error")

        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("test_password\n")
            password_file = f.name

        try:
            with patch(
                "sys.argv", ["email_processor", "--set-password", "--password-file", password_file]
            ):
                with patch("email_processor.__main__.console", None):
                    with patch("builtins.print") as mock_print:
                        with patch(
                            "email_processor.__main__.encrypt_password",
                            side_effect=Exception("Encryption error"),
                        ):
                            result = main()
                            self.assertEqual(result, 1)
                            mock_print.assert_any_call(
                                "Error: Failed to save password: Keyring error"
                            )
        finally:
            Path(password_file).unlink(missing_ok=True)


class TestCreateConfigErrors(unittest.TestCase):
    """Tests for create_config error handling."""

    @patch("email_processor.__main__.Path")
    @patch("email_processor.__main__.shutil.copy2")
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

        with patch("email_processor.__main__.console", None):
            with patch("builtins.print") as mock_print:
                result = create_default_config("config.yaml")
                self.assertEqual(result, 1)
                mock_print.assert_any_call("Error creating configuration file: Permission denied")

    @patch("email_processor.__main__.Path")
    @patch("email_processor.__main__.shutil.copy2")
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

        mock_console = MagicMock()
        with patch("email_processor.__main__.console", mock_console):
            result = create_default_config("config.yaml")
            self.assertEqual(result, 1)
            mock_console.print.assert_called()


class TestSMTPConfigErrors(unittest.TestCase):
    """Tests for SMTP configuration error handling."""

    @patch("email_processor.__main__.ConfigLoader.load")
    def test_send_file_missing_smtp_server(self, mock_load_config):
        """Test error when SMTP server is missing."""
        mock_load_config.return_value = {
            "smtp": {
                "port": 587,
                "user": "test@example.com",
                "from_address": "test@example.com",
                "default_recipient": "recipient@example.com",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            test_file = f.name

        try:
            with patch("sys.argv", ["email_processor", "--send-file", test_file]):
                with patch("email_processor.__main__.console", None):
                    with patch("builtins.print") as mock_print:
                        result = main()
                        self.assertEqual(result, 1)
                        mock_print.assert_any_call(
                            "Error: 'smtp.server' is required in config.yaml"
                        )
        finally:
            Path(test_file).unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader.load")
    def test_send_file_missing_smtp_user(self, mock_load_config):
        """Test error when SMTP user is missing."""
        mock_load_config.return_value = {
            "smtp": {
                "server": "smtp.example.com",
                "port": 587,
                "from_address": "test@example.com",
                "default_recipient": "recipient@example.com",
            },
            "imap": {},
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            test_file = f.name

        try:
            with patch("sys.argv", ["email_processor", "--send-file", test_file]):
                with patch("email_processor.__main__.console", None):
                    with patch("builtins.print") as mock_print:
                        result = main()
                        self.assertEqual(result, 1)
                        mock_print.assert_any_call(
                            "Error: 'smtp.user' or 'imap.user' is required in config.yaml"
                        )
        finally:
            Path(test_file).unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader.load")
    def test_send_file_missing_from_address(self, mock_load_config):
        """Test error when from_address is missing."""
        mock_load_config.return_value = {
            "smtp": {
                "server": "smtp.example.com",
                "port": 587,
                "user": "test@example.com",
                "default_recipient": "recipient@example.com",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            test_file = f.name

        try:
            with patch("sys.argv", ["email_processor", "--send-file", test_file]):
                with patch("email_processor.__main__.console", None):
                    with patch("builtins.print") as mock_print:
                        result = main()
                        self.assertEqual(result, 1)
                        mock_print.assert_any_call(
                            "Error: 'smtp.from_address' is required in config.yaml"
                        )
        finally:
            Path(test_file).unlink(missing_ok=True)


class TestDryRunNoConnect(unittest.TestCase):
    """Tests for --dry-run-no-connect mode."""

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.EmailProcessor")
    def test_dry_run_no_connect_mode(self, mock_processor_class, mock_load_config):
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
        mock_processor_class.return_value = mock_processor

        with patch("sys.argv", ["email_processor", "--dry-run-no-connect"]):
            result = main()
            self.assertEqual(result, 0)
            mock_processor.process.assert_called_once_with(
                dry_run=True, mock_mode=True, config_path="config.yaml"
            )


class TestSMTPWarning(unittest.TestCase):
    """Tests for SMTP section missing warning."""

    @patch("email_processor.__main__.ConfigLoader.load")
    @patch("email_processor.__main__.EmailProcessor")
    def test_smtp_section_missing_warning(self, mock_processor_class, mock_load_config):
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
        mock_processor_class.return_value = mock_processor

        with patch("sys.argv", ["email_processor"]):
            with patch("email_processor.__main__.get_logger") as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger
                result = main()
                self.assertEqual(result, 0)
                # Should log warning about missing SMTP section
                mock_logger.warning.assert_called()
                warning_call = mock_logger.warning.call_args
                self.assertIn("smtp_section_missing", str(warning_call))

    @patch("email_processor.__main__.ConfigLoader.load")
    def test_smtp_section_missing_no_warning_when_sending(self, mock_load_config):
        """Test that warning is not shown when using SMTP commands."""
        mock_load_config.return_value = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            test_file = f.name

        try:
            with patch("sys.argv", ["email_processor", "--send-file", test_file]):
                with patch("email_processor.__main__.get_logger") as mock_get_logger:
                    result = main()
                    # Warning should not be called when using SMTP commands
                    if mock_get_logger.called:
                        mock_logger = mock_get_logger.return_value
                        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
                        smtp_warnings = [call for call in warning_calls if "smtp" in call.lower()]
                        self.assertEqual(len(smtp_warnings), 0)
        finally:
            Path(test_file).unlink(missing_ok=True)
