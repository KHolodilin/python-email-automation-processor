"""Unit tests for system fingerprint generation."""

import os
from unittest.mock import MagicMock, patch

import pytest

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


class TestFingerprint:
    # ----------------------------
    # Hostname
    # ----------------------------

    def test_get_hostname(self):
        hostname = get_hostname()
        assert isinstance(hostname, str)
        assert len(hostname) > 0

    @patch("email_processor.security.fingerprint.socket.gethostname")
    def test_get_hostname_exception(self, mock_gethostname):
        mock_gethostname.side_effect = Exception("Network error")
        hostname = get_hostname()
        assert hostname == "unknown"

    # ----------------------------
    # MAC address
    # ----------------------------

    @patch("email_processor.security.fingerprint.uuid.getnode")
    def test_get_mac_address_success(self, mock_getnode):
        mock_getnode.return_value = 0x123456789ABC
        mac = get_mac_address()
        assert mac == "123456789abc"

    @patch("email_processor.security.fingerprint.uuid.getnode")
    def test_get_mac_address_failure(self, mock_getnode):
        mock_getnode.side_effect = Exception("Error")
        mac = get_mac_address()
        assert mac is None

    # ----------------------------
    # Config path hash
    # ----------------------------

    def test_get_config_path_hash(self):
        hash1 = get_config_path_hash("/path/to/config.yaml")
        hash2 = get_config_path_hash("/path/to/config.yaml")
        hash3 = get_config_path_hash("/different/path.yaml")

        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 16

    def test_get_config_path_hash_none(self):
        hash1 = get_config_path_hash(None)
        hash2 = get_config_path_hash(None)

        assert hash1 == hash2
        assert len(hash1) == 16

    # ----------------------------
    # User ID
    # ----------------------------

    def test_get_user_id(self):
        user_id = get_user_id()
        assert isinstance(user_id, str)
        assert len(user_id) > 0

    @pytest.mark.skipif(os.name != "nt", reason="Windows SID test runs only on Windows")
    @patch("builtins.__import__")
    def test_get_user_id_windows_with_sid(self, mock_import):
        """Windows + pywin32 available + SID retrieval success -> returns SID string."""
        mock_win32security = MagicMock()

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
        assert user_id == sid_value

    @pytest.mark.skipif(os.name != "nt", reason="Windows SID test runs only on Windows")
    @patch("builtins.__import__")
    def test_get_user_id_windows_sid_exception(self, mock_import):
        """Windows SID retrieval fails -> fallback to username from environment."""
        mock_win32security = MagicMock()

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

        assert user_id == "testuser"

    @pytest.mark.skipif(os.name == "nt", reason="Linux-only UID tests")
    @patch("email_processor.security.fingerprint.os.getuid", return_value=1000, create=True)
    def test_get_user_id_linux_with_uid(self, mock_getuid):
        """Test get_user_id on Linux when getuid is available and returns UID."""
        user_id = get_user_id()
        assert user_id == "1000"
        # Verify getuid was called
        mock_getuid.assert_called_once()

    @patch("email_processor.security.fingerprint.platform.system", return_value="Linux")
    @patch("email_processor.security.fingerprint.os.getuid", return_value=1000, create=True)
    def test_get_user_id_linux_with_uid_mocked(self, mock_getuid, mock_platform):
        """Test get_user_id on Linux when getuid is available and returns UID (works on all platforms)."""
        user_id = get_user_id()
        assert user_id == "1000"
        # Verify getuid was called
        mock_getuid.assert_called_once()

    @patch("email_processor.security.fingerprint.platform.system", return_value="Linux")
    @patch(
        "email_processor.security.fingerprint.os.getuid",
        side_effect=Exception("Permission denied"),
        create=True,
    )
    def test_get_user_id_linux_uid_exception_mocked(self, mock_getuid, mock_platform):
        """Test get_user_id on Linux when getuid() raises exception, fallback to username (works on all platforms)."""
        with patch.dict(os.environ, {"USERNAME": "testuser", "USER": "testuser"}, clear=False):
            user_id = get_user_id()
        assert user_id == "testuser"
        # Verify getuid was called
        mock_getuid.assert_called_once()

    @pytest.mark.skipif(os.name == "nt", reason="Linux-only UID tests")
    @patch(
        "email_processor.security.fingerprint.os.getuid",
        side_effect=Exception("Permission denied"),
        create=True,
    )
    def test_get_user_id_linux_uid_exception(self, mock_getuid):
        """Test get_user_id when getuid() raises exception, fallback to username."""
        with patch.dict(os.environ, {"USERNAME": "testuser", "USER": "testuser"}, clear=False):
            user_id = get_user_id()
        assert user_id == "testuser"
        # Verify getuid was called
        mock_getuid.assert_called_once()

    @patch("email_processor.security.fingerprint.platform.system", return_value="Linux")
    def test_get_user_id_linux_getuid_none(self, mock_platform):
        """Test get_user_id when getuid is not available (getattr returns None)."""
        # Mock os module to not have getuid attribute
        with (
            patch("email_processor.security.fingerprint.os") as mock_os,
            patch.dict(os.environ, {"USERNAME": "testuser", "USER": "testuser"}, clear=False),
        ):
            # Make getattr return None for getuid
            def getattr_side_effect(obj, name, default=None):
                if name == "getuid":
                    return None
                return getattr(obj, name, default)

            mock_os.getenv = os.getenv
            with patch("builtins.getattr", side_effect=getattr_side_effect):
                user_id = get_user_id()
            assert user_id == "testuser"

    @patch(
        "email_processor.security.fingerprint.platform.system",
        side_effect=Exception("Platform error"),
    )
    def test_get_user_id_platform_exception(self, mock_platform):
        """Test get_user_id when platform.system() raises exception."""
        with patch.dict(os.environ, {"USERNAME": "testuser", "USER": "testuser"}, clear=False):
            user_id = get_user_id()
        assert user_id == "testuser"

    @pytest.mark.skipif(os.name == "nt", reason="Linux-only UID tests")
    @patch("email_processor.security.fingerprint.os")
    def test_get_user_id_linux_getattr_exception(self, mock_os):
        """Test get_user_id when getattr(os, 'getuid') raises exception."""

        # Make getattr raise exception when accessing os.getuid
        def getattr_side_effect(obj, name, default=None):
            if name == "getuid":
                raise Exception("getattr error")
            return getattr(obj, name, default)

        mock_os.getenv = os.getenv
        with (
            patch("builtins.getattr", side_effect=getattr_side_effect),
            patch.dict(os.environ, {"USERNAME": "testuser", "USER": "testuser"}, clear=False),
        ):
            user_id = get_user_id()
        assert user_id == "testuser"

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
        fp1 = get_system_fingerprint()
        fp2 = get_system_fingerprint()

        assert fp1 == fp2
        assert len(fp1) == 64

    @patch("email_processor.security.fingerprint.get_mac_address", return_value="123456789abc")
    @patch("email_processor.security.fingerprint.get_hostname", return_value="test-host")
    @patch("email_processor.security.fingerprint.get_user_id", return_value="1000")
    def test_get_system_fingerprint_with_config(self, *_):
        fp1 = get_system_fingerprint("/path/to/config.yaml")
        fp2 = get_system_fingerprint("/path/to/config.yaml")
        fp3 = get_system_fingerprint("/different/path.yaml")

        assert fp1 == fp2
        assert fp1 != fp3
        assert len(fp1) == 64
        assert len(fp3) == 64

    @patch("email_processor.security.fingerprint.get_mac_address", return_value=None)
    @patch("email_processor.security.fingerprint.get_hostname", return_value="test-host")
    @patch("email_processor.security.fingerprint.get_user_id", return_value="1000")
    @patch(
        "email_processor.security.fingerprint.get_config_path_hash", return_value="deadbeefdeadbeef"
    )
    def test_get_system_fingerprint_no_mac(self, *_):
        fp = get_system_fingerprint()
        assert isinstance(fp, str)
        assert len(fp) == 64
