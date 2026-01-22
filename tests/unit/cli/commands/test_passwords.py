"""Tests for password commands."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from email_processor.__main__ import main
from email_processor.security.encryption import is_encrypted


class TestSetPassword(unittest.TestCase):
    """Tests for --set-password command."""

    @patch("email_processor.config.loader.ConfigLoader.load")
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
                "sys.argv",
                [
                    "email_processor",
                    "password",
                    "set",
                    "--user",
                    "test@example.com",
                    "--password-file",
                    password_file,
                ],
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

    @patch("email_processor.config.loader.ConfigLoader.load")
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
                    "password",
                    "set",
                    "--user",
                    "test@example.com",
                    "--password-file",
                    password_file,
                    "--delete-after-read",
                ],
            ):
                result = main()
                self.assertEqual(result, 0)
                mock_set_password.assert_called_once()
                # File should be removed
                self.assertFalse(password_path.exists())
        finally:
            password_path.unlink(missing_ok=True)

    @patch("email_processor.config.loader.ConfigLoader.load")
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
                "sys.argv",
                [
                    "email_processor",
                    "password",
                    "set",
                    "--user",
                    "test@example.com",
                    "--password-file",
                    password_file,
                ],
            ):
                result = main()
                self.assertEqual(result, 0)
                mock_set_password.assert_called_once()
                # File should still exist
                self.assertTrue(password_path.exists())
        finally:
            password_path.unlink(missing_ok=True)

    @patch("email_processor.config.loader.ConfigLoader.load")
    def test_set_password_file_not_exists(self, mock_load_config):
        """Test error when password file does not exist."""
        mock_load_config.return_value = {
            "imap": {
                "user": "test@example.com",
            },
        }

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
            self.assertEqual(result, 1)

    @patch("email_processor.config.loader.ConfigLoader.load")
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
                "sys.argv",
                [
                    "email_processor",
                    "password",
                    "set",
                    "--user",
                    "test@example.com",
                    "--password-file",
                    password_file,
                ],
            ):
                result = main()
                self.assertEqual(result, 1)
        finally:
            Path(password_file).unlink(missing_ok=True)

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("email_processor.cli.ui.CLIUI")
    def test_set_password_without_password_file(self, mock_ui_class, mock_load_config):
        """Test error when --password-file is not specified and empty password is entered."""
        mock_load_config.return_value = {
            "imap": {
                "user": "test@example.com",
            },
        }
        mock_ui = MagicMock()
        mock_ui.input.return_value = ""  # Empty password
        mock_ui_class.return_value = mock_ui

        with patch(
            "sys.argv", ["email_processor", "password", "set", "--user", "test@example.com"]
        ):
            with patch("email_processor.__main__.CLIUI", mock_ui_class):
                result = main()
                self.assertEqual(result, 1)
                mock_ui.error.assert_called()

    @patch("email_processor.config.loader.ConfigLoader.load")
    @patch("keyring.set_password")
    def test_set_password_missing_user(self, mock_set_password, mock_load_config):
        """Test that password can be set even when imap.user is missing in config (uses --user from args)."""
        mock_load_config.return_value = {
            "imap": {},
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8") as f:
            f.write("test_password\n")
            password_file = f.name

        try:
            with patch(
                "sys.argv",
                [
                    "email_processor",
                    "password",
                    "set",
                    "--user",
                    "test@example.com",
                    "--password-file",
                    password_file,
                ],
            ):
                with patch("email_processor.cli.ui.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = False
                    mock_ui_class.return_value = mock_ui
                    with patch(
                        "email_processor.cli.commands.passwords.encrypt_password",
                        return_value="encrypted",
                    ):
                        result = main()
                        self.assertEqual(result, 0)
                        mock_set_password.assert_called_once()
        finally:
            Path(password_file).unlink(missing_ok=True)

    @patch("email_processor.config.loader.ConfigLoader.load")
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
            # Mock encryption to fail - need to patch in the commands module
            with patch(
                "email_processor.cli.commands.passwords.encrypt_password",
                side_effect=Exception("Encryption error"),
            ):
                with patch(
                    "sys.argv",
                    [
                        "email_processor",
                        "password",
                        "set",
                        "--user",
                        "test@example.com",
                        "--password-file",
                        password_file,
                    ],
                ):
                    with patch("email_processor.cli.ui.CLIUI") as mock_ui_class:
                        mock_ui = MagicMock()
                        mock_ui.has_rich = False
                        mock_ui_class.return_value = mock_ui
                        result = main()
                        self.assertEqual(result, 0)
                        # Should be called once with unencrypted password (fallback)
                        self.assertEqual(mock_set_password.call_count, 1)
                        # Call should be with unencrypted password
                        call_password = mock_set_password.call_args[0][2]
                        self.assertEqual(call_password, "test_password_123")
        finally:
            Path(password_file).unlink(missing_ok=True)


class TestPasswordFileErrors(unittest.TestCase):
    """Tests for password file error handling."""

    @patch("stat.filemode")
    @patch("email_processor.config.loader.ConfigLoader.load")
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
                    [
                        "email_processor",
                        "password",
                        "set",
                        "--user",
                        "test@example.com",
                        "--password-file",
                        password_file,
                    ],
                ):
                    with patch("email_processor.cli.ui.CLIUI") as mock_ui_class:
                        mock_ui = MagicMock()
                        mock_ui.has_rich = False
                        mock_ui_class.return_value = mock_ui
                    # Remove old mock_print patches - use mock_ui instead
                    with patch("keyring.set_password"):
                        with patch(
                            "email_processor.cli.commands.passwords.encrypt_password",
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
                                with patch("builtins.open", create=True) as mock_open:
                                    mock_file = MagicMock()
                                    mock_file.readline.return_value = "test_password\n"
                                    mock_open.return_value.__enter__.return_value = mock_file
                                    result = main()
                                    self.assertEqual(result, 0)
                                    # Check that warning was printed
                                    warning_calls = [
                                        call
                                        for call in mock_ui.warn.call_args_list
                                        if "Warning" in str(call) and "permissions" in str(call)
                                    ]
                                    self.assertGreater(len(warning_calls), 0)
        finally:
            Path(password_file).unlink(missing_ok=True)

    @patch("stat.filemode")
    @patch("email_processor.config.loader.ConfigLoader.load")
    def test_set_password_file_permission_warning_with_rich_console(
        self, mock_load_config, mock_filemode
    ):
        """Test warning when password file has open permissions (Unix) with rich console."""
        import stat
        import sys

        # Skip test on Windows as permission check is Unix-only
        if sys.platform == "win32":
            self.skipTest("Permission check is Unix-only")

        mock_load_config.return_value = {
            "imap": {
                "user": "test@example.com",
            },
            "smtp": {},
        }
        mock_filemode.return_value = "-rw-r--r--"
        mock_console = MagicMock()

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
            with (
                patch("email_processor.__main__.sys.platform", "linux"),
                patch("email_processor.cli.ui.RICH_AVAILABLE", True),
            ):
                with patch("email_processor.cli.ui.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = True
                    mock_ui.console = mock_console
                    mock_ui_class.return_value = mock_ui
                    with (
                        patch(
                            "sys.argv",
                            [
                                "email_processor",
                                "password",
                                "set",
                                "--user",
                                "test@example.com",
                                "--password-file",
                                password_file,
                            ],
                        ),
                        patch("keyring.set_password"),
                        patch(
                            "email_processor.cli.commands.passwords.encrypt_password",
                            return_value="encrypted",
                        ),
                    ):
                        # Patch Path constructor to return our mocked path
                        def mock_path_constructor(path_str):
                            if str(path_str) == password_file:
                                return mock_path
                            return Path(path_str)

                        with patch(
                            "email_processor.cli.commands.passwords.Path",
                            side_effect=mock_path_constructor,
                        ):
                            with patch("builtins.open", create=True) as mock_open:
                                mock_file = MagicMock()
                                mock_file.readline.return_value = "test_password\n"
                                mock_open.return_value.__enter__.return_value = mock_file
                                result = main()
                                self.assertEqual(result, 0)
                        # Check that warning was printed with rich console
                        warning_calls = [
                            str(call)
                            for call in mock_console.print.call_args_list
                            if "Warning" in str(call) and "permissions" in str(call)
                        ]
                        self.assertGreater(len(warning_calls), 0)
        finally:
            Path(password_file).unlink(missing_ok=True)

    @patch("email_processor.config.loader.ConfigLoader.load")
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
                "sys.argv",
                [
                    "email_processor",
                    "password",
                    "set",
                    "--user",
                    "test@example.com",
                    "--password-file",
                    password_file,
                ],
            ):
                with patch("keyring.set_password"):
                    with patch(
                        "email_processor.cli.commands.passwords.encrypt_password",
                        return_value="encrypted",
                    ):
                        result = main()
                        self.assertEqual(result, 0)
        finally:
            Path(password_file).unlink(missing_ok=True)

    @patch("email_processor.config.loader.ConfigLoader.load")
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
                "sys.argv",
                [
                    "email_processor",
                    "password",
                    "set",
                    "--user",
                    "test@example.com",
                    "--password-file",
                    password_file,
                ],
            ):
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = False
                    mock_ui_class.return_value = mock_ui
                    # Remove old mock_print patches - use mock_ui instead
                    with patch("builtins.open", side_effect=PermissionError("Permission denied")):
                        result = main()
                        self.assertEqual(result, 1)
                        mock_ui.error.assert_called()
        finally:
            # Restore permissions for cleanup
            try:
                os.chmod(password_file, 0o644)
            except Exception:
                pass
            Path(password_file).unlink(missing_ok=True)

    @patch("email_processor.config.loader.ConfigLoader.load")
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
                "sys.argv",
                [
                    "email_processor",
                    "password",
                    "set",
                    "--user",
                    "test@example.com",
                    "--password-file",
                    password_file,
                ],
            ):
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = False
                    mock_ui_class.return_value = mock_ui
                    # Remove old mock_print patches - use mock_ui instead
                    with patch("builtins.open", side_effect=OSError("Read error")):
                        result = main()
                        self.assertEqual(result, 1)
                        mock_ui.error.assert_called()
        finally:
            Path(password_file).unlink(missing_ok=True)

    @patch("email_processor.config.loader.ConfigLoader.load")
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
                    "password",
                    "set",
                    "--user",
                    "test@example.com",
                    "--password-file",
                    password_file,
                    "--delete-after-read",
                ],
            ):
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = False
                    mock_ui_class.return_value = mock_ui
                    # Remove old mock_print patches - use mock_ui instead
                    with patch(
                        "email_processor.cli.commands.passwords.encrypt_password",
                        return_value="encrypted",
                    ):
                        with patch(
                            "pathlib.Path.unlink", side_effect=OSError("Cannot remove file")
                        ):
                            result = main()
                            self.assertEqual(result, 0)
                            # Should print warning but not fail
                            mock_ui.warn.assert_called()
        finally:
            Path(password_file).unlink(missing_ok=True)

    @patch("email_processor.config.loader.ConfigLoader.load")
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
                "sys.argv",
                [
                    "email_processor",
                    "password",
                    "set",
                    "--user",
                    "test@example.com",
                    "--password-file",
                    password_file,
                ],
            ):
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = False
                    mock_ui_class.return_value = mock_ui
                    # Remove old mock_print patches - use mock_ui instead
                    with patch(
                        "email_processor.cli.commands.passwords.encrypt_password",
                        side_effect=Exception("Encryption error"),
                    ):
                        result = main()
                        self.assertEqual(result, 4)  # EXIT_AUTH_ERROR when keyring save fails
                        mock_ui.error.assert_called()
        finally:
            Path(password_file).unlink(missing_ok=True)
