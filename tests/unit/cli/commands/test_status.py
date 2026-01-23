"""Tests for status command."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from email_processor.cli.commands.status import show_status
from email_processor.cli.ui import CLIUI


class TestStatusCommand(unittest.TestCase):
    """Tests for status command."""

    def setUp(self):
        """Setup test fixtures."""
        self.ui = MagicMock(spec=CLIUI)
        self.ui.has_rich = False
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("email_processor.cli.commands.status.ConfigLoader.load")
    @patch("email_processor.cli.commands.status.keyring.get_password")
    @patch("email_processor.cli.commands.status.keyring.get_keyring")
    def test_show_status_success(self, mock_get_keyring, mock_get_password, mock_load):
        """Test show_status with successful config load."""
        config_path = Path(self.temp_dir) / "config.yaml"
        config_path.write_text("imap:\n  user: test@example.com\n")

        mock_load.return_value = {
            "imap": {"user": "test@example.com"},
            "processing": {"processed_dir": "processed_uids"},
            "topic_mapping": {"pattern1": str(Path(self.temp_dir) / "folder1")},
            "smtp": {"sent_files_dir": "sent_files"},
        }
        mock_get_password.return_value = "encrypted_password"
        mock_get_keyring.return_value = MagicMock()

        result = show_status(str(config_path), self.ui)
        self.assertEqual(result, 0)
        mock_load.assert_called_once()
        self.ui.info.assert_called()
        self.ui.success.assert_called()

    @patch("email_processor.cli.commands.status.ConfigLoader.load")
    @patch("email_processor.cli.commands.status.keyring.get_keyring")
    def test_show_status_config_not_found(self, mock_get_keyring, mock_load):
        """Test show_status when config file does not exist."""
        config_path = Path(self.temp_dir) / "nonexistent.yaml"

        mock_load.return_value = {}
        mock_get_keyring.return_value = MagicMock()

        result = show_status(str(config_path), self.ui)
        self.assertEqual(result, 0)
        self.ui.warn.assert_called()

    @patch("email_processor.cli.commands.status.ConfigLoader.load")
    @patch("email_processor.cli.commands.status.keyring.get_password")
    @patch("email_processor.cli.commands.status.keyring.get_keyring")
    def test_show_status_config_exists(self, mock_get_keyring, mock_get_password, mock_load):
        """Test show_status when config file exists."""
        config_path = Path(self.temp_dir) / "config.yaml"
        config_path.write_text("imap:\n  user: test@example.com\n")

        mock_load.return_value = {
            "imap": {"user": "test@example.com"},
            "processing": {},
        }
        mock_get_password.return_value = "password"
        mock_get_keyring.return_value = MagicMock()

        result = show_status(str(config_path), self.ui)
        self.assertEqual(result, 0)
        self.ui.success.assert_called()

    @patch("email_processor.cli.commands.status.ConfigLoader.load")
    @patch("email_processor.cli.commands.status.keyring.get_keyring")
    def test_show_status_topic_mapping_exists(self, mock_get_keyring, mock_load):
        """Test show_status with topic mapping folders that exist."""
        folder1 = Path(self.temp_dir) / "folder1"
        folder1.mkdir()

        mock_load.return_value = {
            "topic_mapping": {"pattern1": str(folder1)},
        }
        mock_get_keyring.return_value = MagicMock()

        result = show_status("config.yaml", self.ui)
        self.assertEqual(result, 0)
        self.ui.success.assert_called()

    @patch("email_processor.cli.commands.status.ConfigLoader.load")
    @patch("email_processor.cli.commands.status.keyring.get_keyring")
    def test_show_status_topic_mapping_not_found(self, mock_get_keyring, mock_load):
        """Test show_status with topic mapping folders that don't exist."""
        folder1 = Path(self.temp_dir) / "nonexistent"

        mock_load.return_value = {
            "topic_mapping": {"pattern1": str(folder1)},
        }
        mock_get_keyring.return_value = MagicMock()

        result = show_status("config.yaml", self.ui)
        self.assertEqual(result, 0)
        self.ui.warn.assert_called()

    @patch("email_processor.cli.commands.status.ConfigLoader.load")
    @patch("email_processor.cli.commands.status.keyring.get_keyring")
    def test_show_status_topic_mapping_more_than_5(self, mock_get_keyring, mock_load):
        """Test show_status with more than 5 topic mappings."""
        mock_load.return_value = {
            "topic_mapping": {
                f"pattern{i}": str(Path(self.temp_dir) / f"folder{i}") for i in range(7)
            },
        }
        mock_get_keyring.return_value = MagicMock()

        result = show_status("config.yaml", self.ui)
        self.assertEqual(result, 0)
        # Should show "... and 2 more"
        info_calls = [str(call) for call in self.ui.info.call_args_list]
        more_calls = [call for call in info_calls if "more" in call]
        self.assertGreater(len(more_calls), 0)

    @patch("email_processor.cli.commands.status.ConfigLoader.load")
    @patch("email_processor.cli.commands.status.keyring.get_keyring")
    def test_show_status_smtp_section(self, mock_get_keyring, mock_load):
        """Test show_status with SMTP section."""
        mock_load.return_value = {
            "smtp": {"sent_files_dir": "custom_sent_files"},
        }
        mock_get_keyring.return_value = MagicMock()

        result = show_status("config.yaml", self.ui)
        self.assertEqual(result, 0)
        self.ui.info.assert_called()

    @patch("email_processor.cli.commands.status.ConfigLoader.load")
    @patch("email_processor.cli.commands.status.keyring.get_password")
    @patch("email_processor.cli.commands.status.keyring.get_keyring")
    def test_show_status_imap_user_with_password(
        self, mock_get_keyring, mock_get_password, mock_load
    ):
        """Test show_status when IMAP user has password in keyring."""
        mock_load.return_value = {
            "imap": {"user": "test@example.com"},
        }
        mock_get_password.return_value = "encrypted_password"
        mock_get_keyring.return_value = MagicMock()

        result = show_status("config.yaml", self.ui)
        self.assertEqual(result, 0)
        self.ui.success.assert_called()

    @patch("email_processor.cli.commands.status.ConfigLoader.load")
    @patch("email_processor.cli.commands.status.keyring.get_password")
    @patch("email_processor.cli.commands.status.keyring.get_keyring")
    def test_show_status_imap_user_no_password(
        self, mock_get_keyring, mock_get_password, mock_load
    ):
        """Test show_status when IMAP user has no password in keyring."""
        mock_load.return_value = {
            "imap": {"user": "test@example.com"},
        }
        mock_get_password.return_value = None
        mock_get_keyring.return_value = MagicMock()

        result = show_status("config.yaml", self.ui)
        self.assertEqual(result, 0)
        self.ui.warn.assert_called()

    @patch("email_processor.cli.commands.status.ConfigLoader.load")
    @patch("email_processor.cli.commands.status.keyring.get_password")
    @patch("email_processor.cli.commands.status.keyring.get_keyring")
    def test_show_status_keyring_error(self, mock_get_keyring, mock_get_password, mock_load):
        """Test show_status when keyring raises error."""
        mock_load.return_value = {
            "imap": {"user": "test@example.com"},
        }
        mock_get_password.side_effect = Exception("Keyring error")
        mock_get_keyring.return_value = MagicMock()

        result = show_status("config.yaml", self.ui)
        self.assertEqual(result, 0)
        self.ui.warn.assert_called()

    @patch("email_processor.cli.commands.status.ConfigLoader.load")
    @patch("email_processor.cli.commands.status.keyring.get_keyring")
    def test_show_status_imap_user_not_configured(self, mock_get_keyring, mock_load):
        """Test show_status when IMAP user is not configured."""
        mock_load.return_value = {
            "imap": {},
        }
        mock_get_keyring.return_value = MagicMock()

        result = show_status("config.yaml", self.ui)
        self.assertEqual(result, 0)
        self.ui.warn.assert_called()

    @patch("email_processor.cli.commands.status.ConfigLoader.load")
    @patch("email_processor.cli.commands.status.keyring.get_keyring")
    def test_show_status_keyring_available(self, mock_get_keyring, mock_load):
        """Test show_status when keyring is available."""
        mock_load.return_value = {}
        mock_get_keyring.return_value = MagicMock()

        result = show_status("config.yaml", self.ui)
        self.assertEqual(result, 0)
        self.ui.success.assert_called()

    @patch("email_processor.cli.commands.status.ConfigLoader.load")
    @patch("email_processor.cli.commands.status.keyring.get_keyring")
    def test_show_status_keyring_not_available(self, mock_get_keyring, mock_load):
        """Test show_status when keyring is not available."""
        mock_load.return_value = {}
        mock_get_keyring.side_effect = Exception("Keyring not available")

        result = show_status("config.yaml", self.ui)
        self.assertEqual(result, 0)
        self.ui.warn.assert_called()

    @patch("email_processor.cli.commands.status.ConfigLoader.load")
    @patch("email_processor.cli.commands.status.keyring.get_keyring")
    def test_show_status_config_load_error(self, mock_get_keyring, mock_load):
        """Test show_status when config loading fails."""
        mock_load.side_effect = Exception("Config load error")
        mock_get_keyring.return_value = MagicMock()

        result = show_status("config.yaml", self.ui)
        self.assertEqual(result, 0)
        self.ui.warn.assert_called()
