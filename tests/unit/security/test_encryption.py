"""Unit tests for password encryption and decryption."""

import unittest
from unittest.mock import patch

# Skip tests if cryptography is not available
try:
    from cryptography.fernet import Fernet

    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False

from email_processor.security.encryption import (
    decrypt_password,
    encrypt_password,
    is_encrypted,
)


class TestEncryption(unittest.TestCase):
    """Tests for password encryption."""

    def test_is_encrypted(self):
        """Test encrypted password detection."""
        self.assertTrue(is_encrypted("ENC:base64data"))
        self.assertFalse(is_encrypted("plain_password"))
        self.assertFalse(is_encrypted(""))

    @unittest.skipIf(not CRYPTOGRAPHY_AVAILABLE, "cryptography not installed")
    @patch("email_processor.security.encryption.generate_encryption_key")
    def test_encrypt_decrypt_password(self, mock_key_gen):
        """Test password encryption and decryption."""
        # Mock key generation to return consistent key
        import base64

        test_key = Fernet.generate_key()
        # Fernet.generate_key() returns base64-encoded key, we need raw bytes
        raw_key = base64.urlsafe_b64decode(test_key)
        mock_key_gen.return_value = raw_key

        password = "test_password_123"
        encrypted = encrypt_password(password)
        decrypted = decrypt_password(encrypted)

        self.assertTrue(is_encrypted(encrypted))
        self.assertEqual(password, decrypted)

    @unittest.skipIf(not CRYPTOGRAPHY_AVAILABLE, "cryptography not installed")
    @patch("email_processor.security.encryption.generate_encryption_key")
    def test_encrypt_decrypt_with_config_path(self, mock_key_gen):
        """Test encryption/decryption with config path."""
        import base64

        test_key = Fernet.generate_key()
        raw_key = base64.urlsafe_b64decode(test_key)
        mock_key_gen.return_value = raw_key

        password = "test_password_456"
        encrypted = encrypt_password(password, "/path/to/config.yaml")
        decrypted = decrypt_password(encrypted, "/path/to/config.yaml")

        self.assertEqual(password, decrypted)

    def test_decrypt_unencrypted_password(self):
        """Test that decrypting unencrypted password raises error."""
        with self.assertRaises(ValueError) as context:
            decrypt_password("plain_password")

        self.assertIn("not encrypted", str(context.exception))

    @unittest.skipIf(not CRYPTOGRAPHY_AVAILABLE, "cryptography not installed")
    @patch("email_processor.security.encryption.generate_encryption_key")
    def test_encrypt_different_keys_fail(self, mock_key_gen):
        """Test that decryption fails with different key."""
        import base64

        key1 = Fernet.generate_key()
        key2 = Fernet.generate_key()

        # Encrypt with key1
        raw_key1 = base64.urlsafe_b64decode(key1)
        mock_key_gen.return_value = raw_key1
        encrypted = encrypt_password("test_password")

        # Try to decrypt with key2
        raw_key2 = base64.urlsafe_b64decode(key2)
        mock_key_gen.return_value = raw_key2
        with self.assertRaises(ValueError):
            decrypt_password(encrypted)

    @unittest.skipIf(not CRYPTOGRAPHY_AVAILABLE, "cryptography not installed")
    def test_encrypt_decrypt_different_config_paths_fail(self):
        """Test that encryption/decryption fails with different config paths.

        This test verifies the bug fix where using different config_path
        during encryption and decryption causes decryption to fail.
        """
        password = "test_password_789"
        config_path1 = "/path/to/config1.yaml"
        config_path2 = "/path/to/config2.yaml"

        # Encrypt with config_path1
        encrypted = encrypt_password(password, config_path1)

        # Try to decrypt with config_path2 - should fail
        with self.assertRaises(ValueError) as context:
            decrypt_password(encrypted, config_path2)

        self.assertIn("decrypt", str(context.exception).lower())

        # Decrypt with same config_path1 - should succeed
        decrypted = decrypt_password(encrypted, config_path1)
        self.assertEqual(password, decrypted)

    @unittest.skipIf(not CRYPTOGRAPHY_AVAILABLE, "cryptography not installed")
    def test_encrypt_decrypt_none_vs_config_path_fail(self):
        """Test that encryption with config_path and decryption with None fails.

        This test verifies the bug where encrypting with config_path
        but decrypting with None (default) causes decryption to fail.
        """
        password = "test_password_abc"
        config_path = "/path/to/config.yaml"

        # Encrypt with config_path
        encrypted = encrypt_password(password, config_path)

        # Try to decrypt with None (default) - should fail
        with self.assertRaises(ValueError) as context:
            decrypt_password(encrypted, None)

        self.assertIn("decrypt", str(context.exception).lower())

        # Decrypt with same config_path - should succeed
        decrypted = decrypt_password(encrypted, config_path)
        self.assertEqual(password, decrypted)


if __name__ == "__main__":
    unittest.main()
