"""Unit tests for encryption key generation."""

import unittest
from unittest.mock import patch

from email_processor.security.key_generator import generate_encryption_key


class TestKeyGenerator(unittest.TestCase):
    """Tests for key generation."""

    def test_generate_encryption_key(self):
        """Test encryption key generation."""
        key1 = generate_encryption_key()
        key2 = generate_encryption_key()

        # Should be consistent on same system
        self.assertEqual(key1, key2)
        # Should be 32 bytes (256 bits for Fernet)
        self.assertEqual(len(key1), 32)

    def test_generate_encryption_key_with_config(self):
        """Test encryption key generation with config path."""
        key1 = generate_encryption_key("/path/to/config.yaml")
        key2 = generate_encryption_key("/path/to/config.yaml")
        key3 = generate_encryption_key("/different/path.yaml")

        # Same config path should produce same key
        self.assertEqual(key1, key2)
        # Different config paths should produce different keys
        self.assertNotEqual(key1, key3)

    @patch("email_processor.security.key_generator.get_system_fingerprint")
    def test_generate_encryption_key_deterministic(self, mock_fingerprint):
        """Test that key generation is deterministic."""
        mock_fingerprint.return_value = "test_fingerprint_12345"

        key1 = generate_encryption_key()
        key2 = generate_encryption_key()

        # Same fingerprint should produce same key
        self.assertEqual(key1, key2)
        self.assertEqual(len(key1), 32)


if __name__ == "__main__":
    unittest.main()
