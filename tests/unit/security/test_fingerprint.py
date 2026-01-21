"""Unit tests for system fingerprint generation."""

import os
import unittest
from unittest.mock import MagicMock, patch

from email_processor.security.fingerprint import (
    get_config_path_hash,
    get_hostname,
    get_mac_address,
    get_system_fingerprint,
    get_user_id,
)


class _SidObject:
    def __init__(self, sid: str):
        self.Sid = sid


class TestFingerprint(unittest.TestCase):
    """Tests for fingerprint generation."""

    # ----------------------------
    # Hostname
    # ----------------------------

    def test_get_hostname(self):
        hostname = get_hostname()
        self.assertIsInstance(hostname, str)
        self.assertGreater(len(hostname), 0)

    @patch("email_processor.security.fingerprint.socket.gethostname")
    def test_get_hostname_exception(self, mock_gethostname):
        mock_gethostname.side_effect = Exception("Network error")
        hostname = get_hostname()
        self.assertEqual(hostname, "unknown")

    # ----------------------------
    # MAC address
    # ----------------------------

    @patch("email_processor.security.fingerprint.uuid.getnode")
    def test_get_mac_address_success(self, mock_getnode):
        mock_getnode.return_value = 0x123456789ABC
        mac = get_mac_address()
        self.assertEqual(mac, "123456789abc")

    @patch("email_processor.security.fingerprint.uuid.getnode")
    def test_get_mac_address_failure(self, mock_getnode):
        mock_getnode.side_effect = Exception("Error")
        mac = get_mac_address()
        self.assertIsNone(mac)

    # ----------------------------
    # Config path hash
    # ----------------------------

    def test_get_config_path_hash(self):
        hash1 = get_config_path_hash("/path/to/config.yaml")
        hash2 = get_config_path_hash("/path/to/config.yaml")
        hash3 = get_config_path_hash("/different/path.yaml")

        self.assertEqual(hash1, hash2)
        self.assertNotEqual(hash1, hash3)
        self.assertEqual(len(hash1), 16)

    def test_get_config_path_hash_none(self):
        hash1 = get_config_path_hash(None)
        hash2 = get_config_path_hash(None)
        self.assertEqual(hash1, hash2)
        self.assertEqual(len(hash1), 16)

    # ----------------------------
    # User ID
    # ----------------------------

    def test_get_user_id(self):
        user_id = get_user_id()
        self.assertIsInstance(user_id, str)
        self.assertGreater(len(user_id), 0)

    @patch("email_processor.security.fingerprint.platform.system", return_value="Windows")
    def test_get_user_id_windows_no_pywin32(self, mock_system):
        with patch.dict(os.environ, {"USERNAME": "testuser", "USER": "testuser"}, clear=False):
            user_id = get_user_id()
        self.assertEqual(user_id, "testuser")

    @patch("email_processor.security.fingerprint.platform.system", return_value="Windows")
    @patch("builtins.__import__")
    def test_get_user_id_windows_with_sid(self, mock_import, mock_system):
        """Windows with pywin32 available and SID retrieval success -> returns SID string."""
        mock_win32security = MagicMock()

        # Important: this must match code: str(user[0].Sid)
        sid_value = "S-1-5-21-1234567890-1234567890-1234567890-1001"
        mock_win32security.GetTokenInformation.return_value = (_SidObject(sid_value),)

        mock_win32security.OpenProcessToken.return_value = MagicMock()
        mock_win32security.GetCurrentProcess.return_value = MagicMock()
        mock_win32security.TOKEN_QUERY = 0x0008
        mock_win32security.TokenUser = 1

        real_import = __import__

        def import_side_effect(name, *args, **kwargs):
            if name == "win32security":
                return mock_win32security
            return real_import(name, *args, **kwargs)

        mock_import.side_effect = import_side_effect

        user_id = get_user_id()
        self.assertEqual(user_id, sid_value)

    @patch("email_processor.security.fingerprint.platform.system", return_value="Windows")
    @patch("builtins.__import__")
    def test_get_user_id_windows_sid_exception(self, mock_import, mock_system):
        """Windows SID retrieval fails -> fallback to username."""
        mock_win32security = MagicMock()

        # Fail early inside SID retrieval path
        mock_win32security.OpenProcessToken.side_effect = Exception("Access denied")
        mock_win32security.GetCurrentProcess.return_value = MagicMock()
        mock_win32security.TOKEN_QUERY = 0x0008
        mock_win32security.TokenUser = 1

        real_import = __import__

        def import_side_effect(name, *args, **kwargs):
            if name == "win32security":
                return mock_win32security
            return real_import(name, *args, **kwargs)

        mock_import.side_effect = import_side_effect

        with patch.dict(os.environ, {"USERNAME": "testuser", "USER": "testuser"}, clear=False):
            user_id = get_user_id()

        self.assertEqual(user_id, "testuser")

    @patch(
        "email_processor.security.fingerprint.platform.system",
        side_effect=Exception("Platform error"),
    )
    def test_get_user_id_general_exception(self, mock_system):
        with patch.dict(os.environ, {"USERNAME": "testuser", "USER": "testuser"}, clear=False):
            user_id = get_user_id()
        self.assertEqual(user_id, "testuser")

    @patch("email_processor.security.fingerprint.platform.system", return_value="Linux")
    @patch("email_processor.security.fingerprint.os.getuid", return_value=1000, create=True)
    def test_get_user_id_linux_with_uid(self, mock_getuid, mock_system):
        user_id = get_user_id()
        self.assertEqual(user_id, "1000")

    @patch("email_processor.security.fingerprint.platform.system", return_value="Linux")
    @patch(
        "email_processor.security.fingerprint.os.getuid",
        side_effect=Exception("Permission denied"),
        create=True,
    )
    def test_get_user_id_linux_uid_exception(self, mock_getuid, mock_system):
        with patch.dict(os.environ, {"USERNAME": "testuser", "USER": "testuser"}, clear=False):
            user_id = get_user_id()
        self.assertEqual(user_id, "testuser")

    # ----------------------------
    # System fingerprint
    # ----------------------------

    @patch("email_processor.security.fingerprint.get_mac_address", return_value="123456789abc")
    @patch("email_processor.security.fingerprint.get_hostname", return_value="test-host")
    @patch("email_processor.security.fingerprint.get_user_id", return_value="1000")
    @patch(
        "email_processor.security.fingerprint.get_config_path_hash", return_value="deadbeefdeadbeef"
    )
    def test_get_system_fingerprint(self, *_):
        fingerprint1 = get_system_fingerprint()
        fingerprint2 = get_system_fingerprint()
        self.assertEqual(fingerprint1, fingerprint2)
        self.assertEqual(len(fingerprint1), 64)

    @patch("email_processor.security.fingerprint.get_mac_address", return_value="123456789abc")
    @patch("email_processor.security.fingerprint.get_hostname", return_value="test-host")
    @patch("email_processor.security.fingerprint.get_user_id", return_value="1000")
    def test_get_system_fingerprint_with_config(self, *_):
        fp1 = get_system_fingerprint("/path/to/config.yaml")
        fp2 = get_system_fingerprint("/path/to/config.yaml")
        fp3 = get_system_fingerprint("/different/path.yaml")

        self.assertEqual(fp1, fp2)
        self.assertNotEqual(fp1, fp3)
        self.assertEqual(len(fp1), 64)
        self.assertEqual(len(fp3), 64)

    @patch("email_processor.security.fingerprint.get_mac_address", return_value=None)
    @patch("email_processor.security.fingerprint.get_hostname", return_value="test-host")
    @patch("email_processor.security.fingerprint.get_user_id", return_value="1000")
    @patch(
        "email_processor.security.fingerprint.get_config_path_hash", return_value="deadbeefdeadbeef"
    )
    def test_get_system_fingerprint_no_mac(self, *_):
        fingerprint = get_system_fingerprint()
        self.assertIsInstance(fingerprint, str)
        self.assertEqual(len(fingerprint), 64)


if __name__ == "__main__":
    unittest.main()
