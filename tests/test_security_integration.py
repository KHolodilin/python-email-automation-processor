"""Integration tests for password encryption with keyring."""

import unittest
from unittest.mock import patch

# Skip tests if cryptography is not available
try:
    from cryptography.fernet import Fernet

    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

from email_processor.imap.auth import get_imap_password
from email_processor.security.encryption import encrypt_password, is_encrypted


class TestSecurityIntegration(unittest.TestCase):
    """Integration tests for password encryption."""

    @unittest.skipIf(not CRYPTOGRAPHY_AVAILABLE, "cryptography not installed")
    @patch("email_processor.imap.auth.keyring.get_password")
    @patch("email_processor.imap.auth.keyring.set_password")
    def test_password_encryption_integration(self, mock_set, mock_get):
        """Test full integration of password encryption with keyring."""
        # Simulate encrypted password in keyring
        test_password = "test_password_123"
        encrypted = encrypt_password(test_password)

        mock_get.return_value = encrypted

        # Get password should decrypt automatically
        password = get_imap_password("test@example.com")

        self.assertEqual(password, test_password)
        # Should not save password since it's already in keyring
        mock_set.assert_not_called()

    @unittest.skipIf(not CRYPTOGRAPHY_AVAILABLE, "cryptography not installed")
    @patch("email_processor.imap.auth.keyring.get_password")
    @patch("email_processor.imap.auth.keyring.set_password")
    @patch("builtins.input")
    @patch("getpass.getpass")
    def test_backward_compatibility_unencrypted(self, mock_getpass, mock_input, mock_set, mock_get):
        """Test backward compatibility with unencrypted passwords."""
        # Simulate old unencrypted password in keyring
        old_password = "plain_password_123"
        mock_get.return_value = old_password

        password = get_imap_password("test@example.com")

        # Should read unencrypted password
        self.assertEqual(password, old_password)
        # Should not try to save (no user input)
        mock_getpass.assert_not_called()

    @unittest.skipIf(not CRYPTOGRAPHY_AVAILABLE, "cryptography not installed")
    @patch("email_processor.imap.auth.keyring.get_password")
    @patch("email_processor.imap.auth.keyring.set_password")
    @patch("builtins.input")
    @patch("getpass.getpass")
    def test_migration_to_encrypted(self, mock_getpass, mock_input, mock_set, mock_get):
        """Test migration from unencrypted to encrypted password."""
        # Start with unencrypted password
        old_password = "plain_password_123"
        mock_get.return_value = old_password

        # User re-enters password (simulating password change)
        mock_getpass.return_value = "new_password_456"
        mock_input.return_value = "y"

        password = get_imap_password("test@example.com")

        # Should use old password (from keyring)
        self.assertEqual(password, old_password)

        # Now simulate saving new password
        mock_get.return_value = None  # No password in keyring
        mock_getpass.return_value = "new_password_456"
        mock_input.return_value = "y"

        password = get_imap_password("test@example.com")

        # Should save encrypted
        mock_set.assert_called()
        saved_password = mock_set.call_args[0][2]
        self.assertTrue(is_encrypted(saved_password))

    @unittest.skipIf(not CRYPTOGRAPHY_AVAILABLE, "cryptography not installed")
    @patch("email_processor.imap.auth.keyring.get_password")
    def test_decryption_failure_handling(self, mock_get):
        """Test handling of decryption failure."""
        # Simulate encrypted password that can't be decrypted (wrong key)
        # This would happen if system characteristics changed
        import base64

        # Create encrypted data with different key
        wrong_key = Fernet.generate_key()
        fernet = Fernet(wrong_key)
        encrypted_data = fernet.encrypt(b"test_password")
        encrypted_str = base64.b64encode(encrypted_data).decode("utf-8")
        wrong_encrypted = f"ENC:{encrypted_str}"

        mock_get.return_value = wrong_encrypted

        # Should raise ValueError instead of prompting for new password
        with self.assertRaises(ValueError) as context:
            get_imap_password("test@example.com")

        # Should contain error message about decryption failure
        self.assertIn("Failed to decrypt", str(context.exception))
        self.assertIn("--clear-passwords", str(context.exception))


if __name__ == "__main__":
    unittest.main()
