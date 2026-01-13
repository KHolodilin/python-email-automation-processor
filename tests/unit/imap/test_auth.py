"""Tests for IMAP auth module."""

import logging
import unittest
from unittest.mock import patch

from email_processor.config.constants import KEYRING_SERVICE_NAME
from email_processor.imap.auth import IMAPAuth, clear_passwords, get_imap_password
from email_processor.logging.setup import setup_logging


class TestIMAPPassword(unittest.TestCase):
    """Tests for IMAP password handling."""

    def setUp(self):
        """Close any file handlers from previous tests."""
        for handler in logging.root.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                try:
                    handler.close()
                except Exception:
                    pass
                logging.root.removeHandler(handler)
        setup_logging({"level": "INFO", "format": "console"})

    @patch("email_processor.imap.auth.keyring.get_password")
    @patch("email_processor.imap.auth.keyring.set_password")
    def test_get_password_from_keyring(self, mock_set, mock_get):
        """Test getting password from keyring."""
        mock_get.return_value = "stored_password"

        password = get_imap_password("test@example.com")

        self.assertEqual(password, "stored_password")
        mock_get.assert_called_once_with(KEYRING_SERVICE_NAME, "test@example.com")
        mock_set.assert_not_called()

    @patch("email_processor.imap.auth.keyring.get_password")
    @patch("email_processor.imap.auth.keyring.set_password")
    @patch("builtins.input")
    @patch("getpass.getpass")
    def test_get_password_from_input_save(self, mock_getpass, mock_input, mock_set, mock_get):
        """Test getting password from input and saving."""
        mock_get.return_value = None
        mock_getpass.return_value = "new_password"
        mock_input.return_value = "y"

        password = get_imap_password("test@example.com")

        self.assertEqual(password, "new_password")
        mock_set.assert_called_once_with(KEYRING_SERVICE_NAME, "test@example.com", "new_password")

    @patch("email_processor.imap.auth.keyring.get_password")
    @patch("email_processor.imap.auth.keyring.set_password")
    @patch("builtins.input")
    @patch("getpass.getpass")
    def test_get_password_from_input_no_save(self, mock_getpass, mock_input, mock_set, mock_get):
        """Test getting password from input without saving."""
        mock_get.return_value = None
        mock_getpass.return_value = "new_password"
        mock_input.return_value = "n"

        password = get_imap_password("test@example.com")

        self.assertEqual(password, "new_password")
        mock_set.assert_not_called()

    @patch("email_processor.imap.auth.keyring.get_password")
    @patch("getpass.getpass")
    def test_get_password_empty(self, mock_getpass, mock_get):
        """Test getting empty password raises error."""
        mock_get.return_value = None
        mock_getpass.return_value = ""

        with self.assertRaises(ValueError):
            get_imap_password("test@example.com")

    @patch("email_processor.imap.auth.keyring.get_password")
    @patch("email_processor.imap.auth.keyring.set_password")
    @patch("builtins.input")
    @patch("getpass.getpass")
    def test_get_password_save_error(self, mock_getpass, mock_input, mock_set, mock_get):
        """Test handling error when saving password to keyring."""
        mock_get.return_value = None
        mock_getpass.return_value = "new_password"
        mock_input.return_value = "y"
        mock_set.side_effect = Exception("Keyring error")

        # Should still return password even if save fails
        password = get_imap_password("test@example.com")
        self.assertEqual(password, "new_password")
        mock_set.assert_called_once()

    def test_imap_auth_get_password(self):
        """Test IMAPAuth.get_password method."""
        with patch(
            "email_processor.imap.auth.keyring.get_password", return_value="stored_password"
        ):
            password = IMAPAuth.get_password("test@example.com")
            self.assertEqual(password, "stored_password")

    @patch("email_processor.imap.auth.keyring.delete_password")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_imap_auth_clear_passwords(self, mock_print, mock_input, mock_delete):
        """Test IMAPAuth.clear_passwords method."""
        mock_input.return_value = "y"
        mock_delete.side_effect = [None, None]

        IMAPAuth.clear_passwords("test-service", "user@example.com")
        self.assertGreater(mock_delete.call_count, 0)


class TestClearPasswords(unittest.TestCase):
    """Tests for clear_passwords function."""

    def setUp(self):
        """Setup logging."""
        setup_logging({"level": "INFO", "format": "console"})

    @patch("email_processor.imap.auth.keyring.delete_password")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_clear_passwords_confirm(self, mock_print, mock_input, mock_delete):
        """Test clearing passwords with confirmation."""
        mock_input.return_value = "y"
        mock_delete.side_effect = [None, None, None]  # No exception

        clear_passwords("test-service", "user@example.com")

        # Should call delete_password multiple times (for different case variations)
        self.assertGreater(mock_delete.call_count, 0)
        # Check that print was called with the correct message format
        print_calls = [str(call) for call in mock_print.call_args_list]
        found = False
        for call_str in print_calls:
            if "Done. Deleted entries:" in call_str and str(mock_delete.call_count) in call_str:
                found = True
                break
        self.assertTrue(
            found,
            f"Expected print call with 'Done. Deleted entries: {mock_delete.call_count}' not found",
        )

    @patch("email_processor.imap.auth.keyring.delete_password")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_clear_passwords_cancel(self, mock_print, mock_input, mock_delete):
        """Test clearing passwords with cancellation."""
        mock_input.return_value = "n"

        clear_passwords("test-service", "user@example.com")

        mock_delete.assert_not_called()
        mock_print.assert_any_call("Cancelled.")

    @patch("email_processor.imap.auth.keyring.delete_password")
    @patch("builtins.input")
    @patch("builtins.print")
    def test_clear_passwords_not_found(self, mock_print, mock_input, mock_delete):
        """Test clearing passwords when password not found."""
        mock_input.return_value = "y"
        mock_delete.side_effect = Exception("Not found")

        clear_passwords("test-service", "user@example.com")

        # Should continue even if some deletions fail
        self.assertGreater(mock_delete.call_count, 0)
