"""Tests for SMTP send commands."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from email_processor.__main__ import main
from email_processor.exit_codes import ExitCode
from email_processor.imap.fetcher import ProcessingMetrics, ProcessingResult


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

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.smtp.smtp_connect")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_send_file_success(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_config_loader_class,
    ):
        """Test sending a single file successfully."""
        mock_config_loader_class.load.return_value = {
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

        with patch(
            "sys.argv",
            ["email_processor", "send", "file", str(self.test_file), "--to", "test@example.com"],
        ):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = False
                mock_ui_class.return_value = mock_ui
                # Ensure file exists
                self.assertTrue(
                    self.test_file.exists(), f"Test file should exist: {self.test_file}"
                )
                result = main()
                self.assertEqual(
                    result,
                    0,
                    f"Expected 0 but got {result}. UI error calls: {mock_ui.error.call_args_list}",
                )
                mock_sender.send_file.assert_called_once()
                mock_storage.mark_as_sent.assert_called_once()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.smtp.smtp_connect")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_send_file_not_found(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test error when file not found."""
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

        with patch(
            "sys.argv",
            ["email_processor", "send", "file", "/nonexistent/file", "--to", "test@example.com"],
        ):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui_class.return_value = mock_ui
                with patch("pathlib.Path.exists", return_value=False):
                    result = main()
                    self.assertEqual(result, ExitCode.FILE_NOT_FOUND)
                    # Check that error message was printed
                    mock_ui.error.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.smtp.smtp_connect")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_send_file_already_sent(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test warning when file already sent."""
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

        with patch(
            "sys.argv",
            ["email_processor", "send", "file", str(self.test_file), "--to", "test@example.com"],
        ):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = False
                mock_ui_class.return_value = mock_ui
                # Ensure file exists
                self.assertTrue(
                    self.test_file.exists(), f"Test file should exist: {self.test_file}"
                )
                result = main()
                self.assertEqual(
                    result,
                    0,
                    f"Expected 0 but got {result}. UI error calls: {mock_ui.error.call_args_list}",
                )
                mock_ui.warn.assert_called()
                mock_sender.send_file.assert_not_called()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.smtp.smtp_connect")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_send_file_dry_run(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test dry-run mode for sending file."""
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

        with patch(
            "sys.argv",
            [
                "email_processor",
                "send",
                "file",
                str(self.test_file),
                "--dry-run",
                "--to",
                "test@example.com",
            ],
        ):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = False
                mock_ui_class.return_value = mock_ui
                # Ensure file exists
                self.assertTrue(
                    self.test_file.exists(), f"Test file should exist: {self.test_file}"
                )
                result = main()
                self.assertEqual(
                    result,
                    0,
                    f"Expected 0 but got {result}. UI error calls: {mock_ui.error.call_args_list}",
                )
                # In dry-run mode, send_file is called but with dry_run=True
                mock_sender.send_file.assert_called_once()
                mock_storage.mark_as_sent.assert_not_called()
                # When has_rich is False, dry-run uses info() instead of print()
                mock_ui.info.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.smtp.smtp_connect")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_send_file_failed(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test error when sending file fails."""
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
        mock_sender.send_file.return_value = False
        mock_sender_class.return_value = mock_sender
        mock_storage = MagicMock()
        mock_storage.is_sent.return_value = False
        mock_storage_class.return_value = mock_storage

        with patch(
            "sys.argv",
            ["email_processor", "send", "file", str(self.test_file), "--to", "test@example.com"],
        ):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui_class.return_value = mock_ui
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
    def test_send_folder_success(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test sending files from folder successfully."""
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

        with patch(
            "sys.argv",
            [
                "email_processor",
                "send",
                "folder",
                str(self.test_folder),
                "--to",
                "test@example.com",
            ],
        ):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = False
                mock_ui_class.return_value = mock_ui
                # Ensure file/folder exists for file/folder tests
                if hasattr(self, "test_file") and "file" in str(sys.argv):
                    self.assertTrue(
                        self.test_file.exists(), f"Test file should exist: {self.test_file}"
                    )
                result = main()
                self.assertEqual(
                    result,
                    0,
                    f"Expected 0 but got {result}. UI error calls: {mock_ui.error.call_args_list}",
                )
                self.assertEqual(mock_sender.send_file.call_count, 2)
                self.assertEqual(mock_storage.mark_as_sent.call_count, 2)
                # When has_rich is False, uses info() instead of print()
                mock_ui.info.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.smtp.smtp_connect")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_send_folder_from_config(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test sending files from folder specified in config."""
        mock_load_config.load.return_value = {
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
        mock_smtp = MagicMock()
        mock_smtp_connect.return_value = mock_smtp
        mock_sender = MagicMock()
        mock_sender.send_file.return_value = True
        mock_sender_class.return_value = mock_sender
        mock_storage = MagicMock()
        mock_storage.is_sent.return_value = False
        mock_storage_class.return_value = mock_storage

        # Use the folder path from config
        with patch(
            "sys.argv",
            [
                "email_processor",
                "send",
                "folder",
                str(self.test_folder),
                "--to",
                "test@example.com",
            ],
        ):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = False
                mock_ui_class.return_value = mock_ui
                # Ensure file/folder exists for file/folder tests
                if hasattr(self, "test_file") and "file" in str(sys.argv):
                    self.assertTrue(
                        self.test_file.exists(), f"Test file should exist: {self.test_file}"
                    )
                result = main()
                self.assertEqual(
                    result,
                    0,
                    f"Expected 0 but got {result}. UI error calls: {mock_ui.error.call_args_list}",
                )
                self.assertEqual(mock_sender.send_file.call_count, 2)
                # When has_rich is False, uses info() instead of print()
                mock_ui.info.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.smtp.smtp_connect")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_send_folder_no_new_files(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test when all files in folder are already sent."""
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

        with patch(
            "sys.argv",
            [
                "email_processor",
                "send",
                "folder",
                str(self.test_folder),
                "--to",
                "test@example.com",
            ],
        ):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = False
                mock_ui_class.return_value = mock_ui
                # Ensure file/folder exists for file/folder tests
                if hasattr(self, "test_file") and "file" in str(sys.argv):
                    self.assertTrue(
                        self.test_file.exists(), f"Test file should exist: {self.test_file}"
                    )
                result = main()
                self.assertEqual(
                    result,
                    0,
                    f"Expected 0 but got {result}. UI error calls: {mock_ui.error.call_args_list}",
                )
                mock_sender.send_file.assert_not_called()
                # When has_rich is False, uses info() instead of print()
                mock_ui.info.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.smtp.smtp_connect")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_send_file_not_a_file(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test error when send-file path is not a file."""
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
        mock_storage_class.return_value = mock_storage

        with patch(
            "sys.argv",
            ["email_processor", "send", "file", str(self.test_folder), "--to", "test@example.com"],
        ):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui_class.return_value = mock_ui
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
    def test_send_folder_not_a_folder(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test error when send-folder path is not a folder."""
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
        mock_storage_class.return_value = mock_storage

        with patch(
            "sys.argv",
            ["email_processor", "send", "folder", str(self.test_file), "--to", "test@example.com"],
        ):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui_class.return_value = mock_ui
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
    def test_send_folder_not_specified_no_config(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test error when send-folder is not specified and not in config."""
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
        mock_storage_class.return_value = mock_storage

        with patch(
            "sys.argv", ["email_processor", "send", "folder", "folder", "--to", "test@example.com"]
        ):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui_class.return_value = mock_ui
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
    def test_send_folder_with_skipped_and_failed(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test sending folder with some files skipped and some failed."""
        # Create additional test files
        test_file3 = self.test_folder / "file3.txt"
        test_file3.write_text("content3")
        test_file4 = self.test_folder / "file4.txt"
        test_file4.write_text("content4")

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
            # First new file succeeds, second new file fails
            mock_sender.send_file.side_effect = [True, False]
            mock_sender_class.return_value = mock_sender
            mock_storage = MagicMock()

            # First two files are already sent (skipped), last two are new
            def is_sent_side_effect(file_path, day_str):
                return file_path.name in ["file1.txt", "file2.txt"]

            mock_storage.is_sent.side_effect = is_sent_side_effect
            mock_storage_class.return_value = mock_storage

            with patch(
                "sys.argv",
                [
                    "email_processor",
                    "send",
                    "folder",
                    str(self.test_folder),
                    "--to",
                    "test@example.com",
                ],
            ):
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = False
                    mock_ui_class.return_value = mock_ui
                    with patch("email_processor.smtp.smtp_connect") as mock_smtp_connect_patch:
                        mock_smtp = MagicMock()
                        mock_smtp_connect_patch.return_value = mock_smtp
                    result = main()
                    self.assertEqual(
                        result, ExitCode.PROCESSING_ERROR
                    )  # Failed because one file failed
                    # Check that messages were printed via UI (info or print)
                    # When has_rich is False, it uses info() instead of print()
                    # Note: info() is called multiple times, so check if any call was made
                    self.assertTrue(
                        mock_ui.info.called or mock_ui.print.called or mock_ui.warn.called
                    )
        finally:
            test_file3.unlink(missing_ok=True)
            test_file4.unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.smtp.smtp_connect")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_send_folder_with_skipped_only(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test sending folder with some files skipped but all new files sent successfully."""
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

        # First file is already sent (skipped), second is new
        def is_sent_side_effect(file_path, day_str):
            return file_path.name == "file1.txt"

        mock_storage.is_sent.side_effect = is_sent_side_effect
        mock_storage_class.return_value = mock_storage

        with patch(
            "sys.argv",
            [
                "email_processor",
                "send",
                "folder",
                str(self.test_folder),
                "--to",
                "test@example.com",
            ],
        ):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = False
                mock_ui_class.return_value = mock_ui
                # Ensure file/folder exists for file/folder tests
                if hasattr(self, "test_file") and "file" in str(sys.argv):
                    self.assertTrue(
                        self.test_file.exists(), f"Test file should exist: {self.test_file}"
                    )
                result = main()
                self.assertEqual(
                    result,
                    0,
                    f"Expected 0 but got {result}. UI error calls: {mock_ui.error.call_args_list}",
                )  # Success
                # Check that skipped message was printed
                # When has_rich is False, uses info() instead of print()
                mock_ui.info.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.smtp.smtp_connect")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_send_folder_partial_failure(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test when some files fail to send."""
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
        # First file succeeds, second fails
        mock_sender.send_file.side_effect = [True, False]
        mock_sender_class.return_value = mock_sender
        mock_storage = MagicMock()
        mock_storage.is_sent.return_value = False
        mock_storage_class.return_value = mock_storage

        with patch(
            "sys.argv",
            [
                "email_processor",
                "send",
                "folder",
                str(self.test_folder),
                "--to",
                "test@example.com",
            ],
        ):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui_class.return_value = mock_ui
                result = main()
                self.assertEqual(result, 1)  # Failed because one file failed
                self.assertEqual(mock_sender.send_file.call_count, 2)
                # Check that messages were printed via UI (info or print)
                # When has_rich is False, it uses info() instead of print()
                self.assertTrue(mock_ui.info.called or mock_ui.print.called or mock_ui.warn.called)

    @patch("email_processor.__main__.ConfigLoader")
    def test_send_file_missing_smtp_config(self, mock_load_config):
        """Test error when SMTP config is missing."""
        mock_load_config.load.return_value = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
        }

        with patch(
            "sys.argv",
            ["email_processor", "send", "file", str(self.test_file), "--to", "test@example.com"],
        ):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui_class.return_value = mock_ui
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
    def test_send_file_missing_recipient(self, mock_get_password, mock_load_config):
        """Test error when recipient is not specified."""
        mock_load_config.load.return_value = {
            "smtp": {
                "server": "smtp.example.com",
                "port": 587,
                "user": "test@example.com",
                "from_address": "test@example.com",
            },
        }
        mock_get_password.return_value = "password"

        with patch("sys.argv", ["email_processor", "send", "file", str(self.test_file)]):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui_class.return_value = mock_ui
                # argparse will raise SystemExit: 2 when required --to is missing
                with self.assertRaises(SystemExit) as cm:
                    main()
                from email_processor.exit_codes import ExitCode

                self.assertEqual(cm.exception.code, ExitCode.VALIDATION_FAILED)

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.storage.sent_files_storage.SentFilesStorage")
    def test_send_file_password_error(
        self, mock_storage_class, mock_get_password, mock_load_config
    ):
        """Test error when getting password fails."""
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
        mock_storage = MagicMock()
        mock_storage.is_sent.return_value = False
        mock_storage_class.return_value = mock_storage

        with patch(
            "sys.argv",
            ["email_processor", "send", "file", str(self.test_file), "--to", "test@example.com"],
        ):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui_class.return_value = mock_ui
                # Need to patch get_imap_password in the commands module
                with patch(
                    "email_processor.cli.commands.smtp.get_imap_password",
                    side_effect=Exception("Password error"),
                ):
                    result = main()
                    self.assertEqual(result, ExitCode.CONFIG_ERROR)
                    mock_ui.error.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.smtp.smtp_connect")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_send_file_with_custom_recipient(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test sending file with custom recipient."""
        mock_load_config.load.return_value = {
            "smtp": {
                "server": "smtp.example.com",
                "port": 587,
                "user": "test@example.com",
                "from_address": "test@example.com",
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

        with patch(
            "sys.argv",
            ["email_processor", "send", "file", str(self.test_file), "--to", "custom@example.com"],
        ):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = False
                mock_ui_class.return_value = mock_ui
                # Ensure file/folder exists for file/folder tests
                if hasattr(self, "test_file") and "file" in str(sys.argv):
                    self.assertTrue(
                        self.test_file.exists(), f"Test file should exist: {self.test_file}"
                    )
                result = main()
                self.assertEqual(
                    result,
                    0,
                    f"Expected 0 but got {result}. UI error calls: {mock_ui.error.call_args_list}",
                )
                mock_sender.send_file.assert_called_once_with(
                    self.test_file, "custom@example.com", None, dry_run=False
                )

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.smtp.smtp_connect")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_send_file_with_custom_subject(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test sending file with custom subject."""
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

        with patch(
            "sys.argv",
            [
                "email_processor",
                "send",
                "file",
                str(self.test_file),
                "--subject",
                "Custom Subject",
                "--to",
                "test@example.com",
            ],
        ):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = False
                mock_ui_class.return_value = mock_ui
                # Ensure file/folder exists for file/folder tests
                if hasattr(self, "test_file") and "file" in str(sys.argv):
                    self.assertTrue(
                        self.test_file.exists(), f"Test file should exist: {self.test_file}"
                    )
                result = main()
                self.assertEqual(
                    result,
                    0,
                    f"Expected 0 but got {result}. UI error calls: {mock_ui.error.call_args_list}",
                )
                mock_sender.send_file.assert_called_once_with(
                    self.test_file, "test@example.com", "Custom Subject", dry_run=False
                )

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.smtp.smtp_connect")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_send_folder_not_found(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test error when folder not found."""
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
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui_class.return_value = mock_ui
                with patch("pathlib.Path.exists", return_value=False):
                    result = main()
                    self.assertEqual(result, ExitCode.FILE_NOT_FOUND)
                    # Check that error message was printed
                    mock_ui.error.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.smtp.smtp_connect")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_send_folder_not_specified(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test error when folder is not specified."""
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

        with patch(
            "sys.argv", ["email_processor", "send", "folder", "folder", "--to", "test@example.com"]
        ):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui_class.return_value = mock_ui
                result = main()
                self.assertEqual(result, ExitCode.FILE_NOT_FOUND)
                # Check that error message was printed
                mock_ui.error.assert_called()


class TestSMTPConfigErrors(unittest.TestCase):
    """Tests for SMTP configuration error handling."""

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

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    def test_send_file_missing_smtp_server(self, mock_get_password, mock_load_config):
        """Test error when SMTP server is missing."""
        mock_load_config.load.return_value = {
            "smtp": {
                "port": 587,
                "user": "test@example.com",
                "from_address": "test@example.com",
                "default_recipient": "recipient@example.com",
            },
        }
        mock_get_password.return_value = "password"

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            test_file = f.name

        try:
            with patch(
                "sys.argv",
                ["email_processor", "send", "file", test_file, "--to", "test@example.com"],
            ):
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = False
                    mock_ui._console = None  # Simulate no rich console
                    # Make error() method actually callable and trackable
                    mock_ui.error = MagicMock()
                    mock_ui_class.return_value = mock_ui
                    # Remove old mock_print patches - use mock_ui instead
                    with patch(
                        "email_processor.storage.sent_files_storage.SentFilesStorage"
                    ) as mock_storage_class:
                        mock_storage = MagicMock()
                        mock_storage.is_sent.return_value = False
                        mock_storage_class.return_value = mock_storage
                        result = main()
                        self.assertEqual(result, ExitCode.CONFIG_ERROR)
                        mock_ui.error.assert_called()
        finally:
            Path(test_file).unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader")
    def test_send_file_missing_smtp_user(self, mock_load_config):
        """Test error when SMTP user is missing."""
        mock_load_config.load.return_value = {
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
            with patch(
                "sys.argv",
                ["email_processor", "send", "file", test_file, "--to", "test@example.com"],
            ):
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = False
                    mock_ui._console = None  # Simulate no rich console
                    # Make error() method actually callable and trackable
                    mock_ui.error = MagicMock()
                    mock_ui_class.return_value = mock_ui
                    # Remove old mock_print patches - use mock_ui instead
                    with patch(
                        "email_processor.storage.sent_files_storage.SentFilesStorage"
                    ) as mock_storage_class:
                        mock_storage = MagicMock()
                        mock_storage.is_sent.return_value = False
                        mock_storage_class.return_value = mock_storage
                        result = main()
                        self.assertEqual(result, ExitCode.CONFIG_ERROR)
                        mock_ui.error.assert_called()
        finally:
            Path(test_file).unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    def test_send_file_missing_from_address(self, mock_get_password, mock_load_config):
        """Test error when from_address is missing."""
        mock_load_config.load.return_value = {
            "smtp": {
                "server": "smtp.example.com",
                "port": 587,
                "user": "test@example.com",
                "default_recipient": "recipient@example.com",
            },
        }
        mock_get_password.return_value = "password"

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            test_file = f.name

        try:
            with patch(
                "sys.argv",
                ["email_processor", "send", "file", test_file, "--to", "test@example.com"],
            ):
                with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                    mock_ui = MagicMock()
                    mock_ui.has_rich = False
                    mock_ui._console = None  # Simulate no rich console
                    # Make error() method actually callable and trackable
                    mock_ui.error = MagicMock()
                    mock_ui_class.return_value = mock_ui
                    # Remove old mock_print patches - use mock_ui instead
                    with patch(
                        "email_processor.storage.sent_files_storage.SentFilesStorage"
                    ) as mock_storage_class:
                        mock_storage = MagicMock()
                        mock_storage.is_sent.return_value = False
                        mock_storage_class.return_value = mock_storage
                        result = main()
                        self.assertEqual(result, ExitCode.CONFIG_ERROR)
                        mock_ui.error.assert_called()
        finally:
            Path(test_file).unlink(missing_ok=True)


class TestSMTPWarning(unittest.TestCase):
    """Tests for SMTP section missing warning."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_file = self.temp_dir / "test.txt"
        self.test_file.write_text("test content")
        self.test_folder = self.temp_dir / "test_folder"
        self.test_folder.mkdir()
        (self.test_folder / "file1.txt").write_text("content1")
        (self.test_folder / "file2.txt").write_text("content2")
        (self.test_folder / "file3.txt").write_text("content3")  # Add third file for skipped test

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.imap.fetcher.Fetcher")
    def test_smtp_section_missing_warning(self, mock_processor_class, mock_load_config):
        """Test warning when SMTP section is missing and not using SMTP commands."""
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
            processed=0, skipped=0, errors=0, file_stats={}, metrics=metrics
        )
        mock_processor_class.return_value = mock_processor

        with patch("sys.argv", ["email_processor", "run"]):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = False
                mock_ui_class.return_value = mock_ui
                with patch("email_processor.__main__.get_logger") as mock_get_logger:
                    mock_logger = MagicMock()
                    mock_get_logger.return_value = mock_logger
                    result = main()
                    self.assertEqual(result, 0)
                    # Should log warning about missing SMTP section
                    mock_logger.warning.assert_called()
                    warning_call = mock_logger.warning.call_args
                    self.assertIn("smtp_section_missing", str(warning_call))

    @patch("email_processor.__main__.ConfigLoader")
    def test_smtp_section_missing_no_warning_when_sending(self, mock_load_config):
        """Test that warning is not shown when using SMTP commands."""
        mock_load_config.load.return_value = {
            "imap": {
                "server": "imap.example.com",
                "user": "test@example.com",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            test_file = f.name

        try:
            with patch(
                "sys.argv",
                ["email_processor", "send", "file", test_file, "--to", "test@example.com"],
            ):
                with patch("email_processor.logging.setup.get_logger") as mock_get_logger:
                    result = main()
                    # Warning should not be called when using SMTP commands
                    if mock_get_logger.called:
                        mock_logger = mock_get_logger.return_value
                        warning_calls = [str(call) for call in mock_logger.warning.call_args_list]
                        smtp_warnings = [call for call in warning_calls if "smtp" in call.lower()]
                        self.assertEqual(len(smtp_warnings), 0)
        finally:
            Path(test_file).unlink(missing_ok=True)

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.smtp.smtp_connect")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_send_file_dry_run_without_rich(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test send_file in dry-run mode without rich console."""
        mock_load_config.load.return_value = {
            "smtp": {
                "server": "smtp.example.com",
                "port": 587,
                "user": "test@example.com",
                "from_address": "test@example.com",
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

        with patch(
            "sys.argv",
            [
                "email_processor",
                "send",
                "file",
                str(self.test_file),
                "--to",
                "test@example.com",
                "--dry-run",
            ],
        ):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = False  # No rich console
                mock_ui_class.return_value = mock_ui
                result = main()
                self.assertEqual(result, 0)
                # Should use info() instead of print() when rich is not available
                mock_ui.info.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    def test_send_folder_missing_smtp_section(self, mock_load_config):
        """Test send_folder when smtp section is missing."""
        mock_load_config.load.return_value = {}  # No smtp section

        from email_processor.cli.commands.smtp import send_folder
        from email_processor.cli.ui import CLIUI

        ui = CLIUI()
        with patch.object(ui, "error") as mock_error:
            result = send_folder(
                {}, str(self.test_folder), "test@example.com", None, False, "config.yaml", ui
            )
            self.assertEqual(result, ExitCode.CONFIG_ERROR)
            mock_error.assert_called_once()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp._init_smtp_components")
    def test_send_folder_init_failed(self, mock_init, mock_load_config):
        """Test send_folder when _init_smtp_components returns None."""
        mock_load_config.load.return_value = {"smtp": {}}
        mock_init.return_value = (None, None, None, "", None)  # Failed initialization

        from email_processor.cli.commands.smtp import send_folder
        from email_processor.cli.ui import CLIUI

        ui = CLIUI()
        result = send_folder(
            {"smtp": {}}, str(self.test_folder), "test@example.com", None, False, "config.yaml", ui
        )
        self.assertEqual(result, ExitCode.CONFIG_ERROR)

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.smtp.smtp_connect")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_send_folder_no_new_files_without_rich(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test send_folder when no new files without rich console."""
        mock_load_config.load.return_value = {
            "smtp": {
                "server": "smtp.example.com",
                "port": 587,
                "user": "test@example.com",
                "from_address": "test@example.com",
            },
        }
        mock_get_password.return_value = "password"
        mock_smtp = MagicMock()
        mock_smtp_connect.return_value = mock_smtp
        mock_sender = MagicMock()
        mock_sender_class.return_value = mock_sender
        mock_storage = MagicMock()
        # All files already sent
        mock_storage.is_sent.return_value = True
        mock_storage_class.return_value = mock_storage

        with patch(
            "sys.argv",
            [
                "email_processor",
                "send",
                "folder",
                str(self.test_folder),
                "--to",
                "test@example.com",
            ],
        ):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = False  # No rich console
                mock_ui_class.return_value = mock_ui
                result = main()
                self.assertEqual(result, 0)
                # Should use info() instead of print() when rich is not available
                mock_ui.info.assert_called()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    def test_init_smtp_components_empty_recipient(self, mock_get_password, mock_load_config):
        """Test _init_smtp_components when recipient is empty."""
        mock_load_config.load.return_value = {
            "smtp": {
                "server": "smtp.example.com",
                "port": 587,
                "user": "test@example.com",
            },
        }
        mock_get_password.return_value = "password"

        from email_processor.cli.commands.smtp import _init_smtp_components
        from email_processor.cli.ui import CLIUI

        ui = CLIUI()
        with patch.object(ui, "error") as mock_error:
            result = _init_smtp_components({"smtp": {}}, "", "config.yaml", ui)
            self.assertEqual(result[0], None)  # Should return None when recipient is empty
            mock_error.assert_called_once()

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.smtp.smtp_connect")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_send_folder_no_new_files_with_rich(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test send_folder with no new files and rich console (covers line 133)."""
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

        with patch(
            "sys.argv",
            [
                "email_processor",
                "send",
                "folder",
                str(self.test_folder),
                "--to",
                "test@example.com",
            ],
        ):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = True
                mock_ui_class.return_value = mock_ui
                result = main()
                self.assertEqual(result, 0)
                mock_sender.send_file.assert_not_called()
                # Should use print() with rich formatting
                mock_ui.print.assert_called()
                print_call = mock_ui.print.call_args[0][0]
                self.assertIn("No new files to send", print_call)
                self.assertIn("[yellow]", print_call)

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    @patch("email_processor.smtp.smtp_connect")
    @patch("email_processor.cli.commands.smtp.EmailSender")
    @patch("email_processor.cli.commands.smtp.SentFilesStorage")
    def test_send_folder_with_skipped_count_rich(
        self,
        mock_storage_class,
        mock_sender_class,
        mock_smtp_connect,
        mock_get_password,
        mock_load_config,
    ):
        """Test send_folder with skipped files and rich console (covers line 157)."""
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

        # First file already sent (skipped), second file is new (will be sent)
        # This ensures skipped_count > 0 and new_files is not empty, so line 157 executes
        def is_sent_side_effect(file_path, day_str):
            # Only file1.txt is already sent, file2.txt and file3.txt are new
            return "file1.txt" in str(file_path)

        mock_storage.is_sent.side_effect = is_sent_side_effect
        mock_storage_class.return_value = mock_storage

        with patch(
            "sys.argv",
            [
                "email_processor",
                "send",
                "folder",
                str(self.test_folder),
                "--to",
                "test@example.com",
            ],
        ):
            with patch("email_processor.__main__.CLIUI") as mock_ui_class:
                mock_ui = MagicMock()
                mock_ui.has_rich = True
                mock_ui_class.return_value = mock_ui
                result = main()
                self.assertEqual(result, 0)
                # Should show skipped count with rich formatting
                mock_ui.print.assert_called()
                print_calls = [call[0][0] for call in mock_ui.print.call_args_list]
                skipped_call = next((c for c in print_calls if "Skipped" in str(c)), None)
                self.assertIsNotNone(skipped_call, "Should show skipped count")
                self.assertIn("[yellow]", str(skipped_call))

    @patch("email_processor.__main__.ConfigLoader")
    @patch("email_processor.cli.commands.smtp.get_imap_password")
    def test_init_smtp_components_missing_to_address(self, mock_get_password, mock_load_config):
        """Test _init_smtp_components when --to is missing (covers lines 231-232)."""
        mock_get_password.return_value = "password"
        mock_load_config.load.return_value = {
            "smtp": {
                "server": "smtp.example.com",
                "port": 587,
                "user": "test@example.com",
                "from_address": "test@example.com",
            },
        }

        from email_processor.cli.commands.smtp import _init_smtp_components
        from email_processor.cli.ui import CLIUI

        ui = CLIUI()
        with patch.object(ui, "error") as mock_error:
            # Pass full config with server, but empty to_address
            result = _init_smtp_components(
                {
                    "smtp": {
                        "server": "smtp.example.com",
                        "port": 587,
                        "user": "test@example.com",
                        "from_address": "test@example.com",
                    }
                },
                "",  # Empty to_address
                "config.yaml",
                ui,
            )
            self.assertEqual(result[0], None)  # Should return None when --to is missing
            mock_error.assert_called_once_with("--to is required")
