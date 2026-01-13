"""Tests for __main__ module."""

import unittest
from unittest.mock import patch, MagicMock
import sys

from email_processor.__main__ import main
from email_processor.config.constants import CONFIG_FILE, KEYRING_SERVICE_NAME


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
        mock_processor.process.return_value = MagicMock(processed=5, skipped=3, errors=1)
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
        mock_processor.process.return_value = MagicMock(processed=0, skipped=0, errors=0)
        mock_processor_class.return_value = mock_processor
        
        with patch("sys.argv", ["email_processor", "--dry-run"]):
            result = main()
            self.assertEqual(result, 0)
            mock_processor.process.assert_called_once_with(dry_run=True, mock_mode=False)
    
    @patch("email_processor.__main__.ConfigLoader.load")
    def test_main_config_file_not_found(self, mock_load_config):
        """Test main function when config file not found."""
        mock_load_config.side_effect = FileNotFoundError("Configuration file not found: config.yaml")
        
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
