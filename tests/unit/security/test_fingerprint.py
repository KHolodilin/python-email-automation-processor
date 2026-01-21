"""Unit tests for system fingerprint generation."""

import unittest
from unittest.mock import patch

from email_processor.security.fingerprint import (
    get_config_path_hash,
    get_hostname,
    get_mac_address,
    get_system_fingerprint,
    get_user_id,
)


class TestFingerprint(unittest.TestCase):
    """Tests for fingerprint generation."""

    def test_get_hostname(self):
        """Test hostname retrieval."""
        hostname = get_hostname()
        self.assertIsInstance(hostname, str)
        self.assertGreater(len(hostname), 0)

    @patch("email_processor.security.fingerprint.uuid.getnode")
    def test_get_mac_address_success(self, mock_getnode):
        """Test MAC address retrieval when available."""
        mock_getnode.return_value = 0x123456789ABC
        mac = get_mac_address()
        self.assertEqual(mac, "123456789abc")

    @patch("email_processor.security.fingerprint.uuid.getnode")
    def test_get_mac_address_failure(self, mock_getnode):
        """Test MAC address retrieval when unavailable."""
        mock_getnode.side_effect = Exception("Error")
        mac = get_mac_address()
        self.assertIsNone(mac)

    def test_get_user_id(self):
        """Test user ID retrieval."""
        user_id = get_user_id()
        self.assertIsInstance(user_id, str)
        self.assertGreater(len(user_id), 0)

    def test_get_config_path_hash(self):
        """Test config path hash generation."""
        hash1 = get_config_path_hash("/path/to/config.yaml")
        hash2 = get_config_path_hash("/path/to/config.yaml")
        hash3 = get_config_path_hash("/different/path.yaml")

        # Same path should produce same hash
        self.assertEqual(hash1, hash2)
        # Different paths should produce different hashes
        self.assertNotEqual(hash1, hash3)
        # Hash should be 16 characters
        self.assertEqual(len(hash1), 16)

    def test_get_config_path_hash_none(self):
        """Test config path hash with None."""
        hash1 = get_config_path_hash(None)
        hash2 = get_config_path_hash(None)
        # Should be consistent
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 16)

    def test_get_system_fingerprint(self):
        """Test system fingerprint generation."""
        fingerprint1 = get_system_fingerprint()
        fingerprint2 = get_system_fingerprint()

        # Should be consistent on same system
        self.assertEqual(fingerprint1, fingerprint2)
        # Should be 64 characters (SHA256 hex)
        self.assertEqual(len(fingerprint1), 64)

    def test_get_system_fingerprint_with_config(self):
        """Test system fingerprint with config path."""
        fingerprint1 = get_system_fingerprint("/path/to/config.yaml")
        fingerprint2 = get_system_fingerprint("/path/to/config.yaml")
        fingerprint3 = get_system_fingerprint("/different/path.yaml")

        # Same config path should produce same fingerprint
        self.assertEqual(fingerprint1, fingerprint2)
        # Different config paths should produce different fingerprints
        self.assertNotEqual(fingerprint1, fingerprint3)

    @patch("email_processor.security.fingerprint.socket.gethostname")
    def test_get_hostname_exception(self, mock_gethostname):
        """Test hostname retrieval when exception occurs."""
        mock_gethostname.side_effect = Exception("Network error")
        hostname = get_hostname()
        self.assertEqual(hostname, "unknown")

    @patch("email_processor.security.fingerprint.platform.system")
    @patch("email_processor.security.fingerprint.os.getenv")
    def test_get_user_id_windows_no_pywin32(self, mock_getenv, mock_system):
        """Test user ID retrieval on Windows without pywin32."""
        mock_system.return_value = "Windows"
        mock_getenv.return_value = "testuser"
        user_id = get_user_id()
        # Should return username (on Windows, pywin32 may not be available)
        self.assertIsInstance(user_id, str)

    @patch("email_processor.security.fingerprint.get_mac_address")
    def test_get_system_fingerprint_no_mac(self, mock_get_mac):
        """Test system fingerprint generation when MAC is unavailable."""
        mock_get_mac.return_value = None
        fingerprint = get_system_fingerprint()
        self.assertIsInstance(fingerprint, str)
        self.assertEqual(len(fingerprint), 64)  # SHA256 hex digest length

    @patch("email_processor.security.fingerprint.platform.system")
    def test_get_user_id_general_exception(self, mock_system):
        """Test user ID retrieval when general exception occurs."""
        mock_system.side_effect = Exception("Platform error")
        user_id = get_user_id()
        # Should fallback to username
        self.assertIsInstance(user_id, str)


if __name__ == "__main__":
    unittest.main()
