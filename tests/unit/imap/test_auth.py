"""Tests for IMAP auth module."""

import logging
import unittest
from unittest.mock import patch

# Check if cryptography is available
try:
    import cryptography.fernet  # noqa: F401

    CRYPTOGRAPHY_AVAILABLE = True
except (ImportError, OSError):
    CRYPTOGRAPHY_AVAILABLE = False

from email_processor.config.constants import KEYRING_SERVICE_NAME
from email_processor.imap.auth import IMAPAuth, clear_passwords, get_imap_password
from email_processor.logging.setup import setup_logging
from email_processor.security.encryption import is_encrypted


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
        """Test getting password from input and saving with real cryptography if available."""
        mock_get.return_value = None
        mock_getpass.return_value = "new_password"
        mock_input.return_value = "y"

        password = get_imap_password("test@example.com")

        self.assertEqual(password, "new_password")
        # Password should be saved (encrypted if cryptography available, unencrypted as fallback)
        mock_set.assert_called_once()
        saved_password = mock_set.call_args[0][2]
        self.assertEqual(mock_set.call_args[0][0], KEYRING_SERVICE_NAME)
        self.assertEqual(mock_set.call_args[0][1], "test@example.com")

        # If cryptography is available, password should be encrypted
        if CRYPTOGRAPHY_AVAILABLE:
            self.assertTrue(
                is_encrypted(saved_password),
                "Password should be encrypted when cryptography is available",
            )
        else:
            # If cryptography is not available, password is saved unencrypted as fallback
            self.assertEqual(
                saved_password, "new_password", "Password should be saved unencrypted as fallback"
            )

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

    @patch("email_processor.imap.auth.encrypt_password")
    @patch("email_processor.imap.auth.keyring.get_password")
    @patch("email_processor.imap.auth.keyring.set_password")
    @patch("builtins.input")
    @patch("getpass.getpass")
    def test_get_password_save_error(
        self, mock_getpass, mock_input, mock_set, mock_get, mock_encrypt
    ):
        """Test handling error when saving password to keyring."""
        mock_get.return_value = None
        mock_getpass.return_value = "new_password"
        mock_input.return_value = "y"
        # Mock encryption to fail
        mock_encrypt.side_effect = Exception("Encryption error")
        # Fallback save also fails
        mock_set.side_effect = Exception("Keyring error")

        # Should still return password even if save fails
        password = get_imap_password("test@example.com")
        self.assertEqual(password, "new_password")
        # Should be called once with unencrypted password (fallback after encryption failed)
        self.assertEqual(mock_set.call_count, 1)
        # Call should be with unencrypted password (fallback)
        call_password = mock_set.call_args[0][2]
        self.assertEqual(call_password, "new_password")

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

    @unittest.skipIf(not CRYPTOGRAPHY_AVAILABLE, "cryptography not installed")
    @patch("email_processor.imap.auth.keyring.get_password")
    @patch("email_processor.imap.auth.keyring.set_password")
    def test_get_password_decryption_fails_different_config_path(self, mock_set, mock_get):
        """Test that decryption fails when config_path differs between save and retrieve.

        This test verifies the bug fix where saving password with one config_path
        but retrieving with different config_path (or None) causes decryption failure.
        """
        from email_processor.security.encryption import encrypt_password

        config_path1 = "/path/to/config1.yaml"
        config_path2 = "/path/to/config2.yaml"
        password = "test_password_xyz"

        # Simulate password saved with config_path1
        encrypted_password = encrypt_password(password, config_path1)
        mock_get.return_value = encrypted_password

        # Try to get password with config_path2 - should raise ValueError
        with self.assertRaises(ValueError) as context:
            get_imap_password("test@example.com", config_path=config_path2)

        self.assertIn("Failed to decrypt", str(context.exception))
        self.assertIn("--clear-passwords", str(context.exception))

        # Get password with same config_path1 - should succeed
        password_retrieved = get_imap_password("test@example.com", config_path=config_path1)
        self.assertEqual(password, password_retrieved)

    @unittest.skipIf(not CRYPTOGRAPHY_AVAILABLE, "cryptography not installed")
    @patch("email_processor.imap.auth.keyring.get_password")
    @patch("email_processor.imap.auth.keyring.set_password")
    def test_get_password_decryption_fails_none_vs_config_path(self, mock_set, mock_get):
        """Test that decryption fails when password saved with config_path but retrieved with None.

        This test verifies the bug where saving password with config_path
        but retrieving with None (default) causes decryption failure.
        """
        from email_processor.security.encryption import encrypt_password

        config_path = "/path/to/config.yaml"
        password = "test_password_def"

        # Simulate password saved with config_path
        encrypted_password = encrypt_password(password, config_path)
        mock_get.return_value = encrypted_password

        # Try to get password with None (default) - should raise ValueError
        with self.assertRaises(ValueError) as context:
            get_imap_password("test@example.com", config_path=None)

        self.assertIn("Failed to decrypt", str(context.exception))
        self.assertIn("--clear-passwords", str(context.exception))

        # Get password with same config_path - should succeed
        password_retrieved = get_imap_password("test@example.com", config_path=config_path)
        self.assertEqual(password, password_retrieved)

    @unittest.skipIf(not CRYPTOGRAPHY_AVAILABLE, "cryptography not installed")
    @patch("email_processor.imap.auth.keyring.get_password")
    def test_get_password_decryption_general_exception(self, mock_get):
        """Test handling general exception (not ValueError) during password decryption."""
        from email_processor.security.encryption import encrypt_password

        # Create encrypted password
        encrypted_password = encrypt_password("test_password", "/path/to/config.yaml")
        mock_get.return_value = encrypted_password

        # Mock decrypt_password to raise general exception (not ValueError)
        with patch("email_processor.imap.auth.decrypt_password") as mock_decrypt:
            # Raise a non-ValueError exception to trigger the general exception handler
            mock_decrypt.side_effect = RuntimeError("Unexpected decryption error")

            with self.assertRaises(ValueError) as context:
                get_imap_password("test@example.com", config_path="/path/to/config.yaml")

            self.assertIn("Failed to decrypt", str(context.exception))
            self.assertIn("--clear-passwords", str(context.exception))

    @patch("email_processor.imap.auth.keyring.get_password")
    @patch("email_processor.imap.auth.keyring.set_password")
    @patch("email_processor.imap.auth.encrypt_password")
    @patch("builtins.input")
    @patch("getpass.getpass")
    def test_get_password_save_encryption_fails_fallback_succeeds(
        self, mock_getpass, mock_input, mock_encrypt, mock_set, mock_get
    ):
        """Test saving password when encryption fails but unencrypted fallback succeeds."""
        mock_get.return_value = None
        mock_getpass.return_value = "new_password"
        mock_input.return_value = "y"
        # Encryption fails
        mock_encrypt.side_effect = Exception("Encryption error")
        # But unencrypted save succeeds
        mock_set.return_value = None

        password = get_imap_password("test@example.com")

        self.assertEqual(password, "new_password")
        # Should be called once with unencrypted password (fallback)
        self.assertEqual(mock_set.call_count, 1)
        call_password = mock_set.call_args[0][2]
        self.assertEqual(call_password, "new_password")


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
