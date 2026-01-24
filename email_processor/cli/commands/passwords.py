"""Password management commands."""

import stat
import sys
from pathlib import Path
from typing import Optional

import keyring

from email_processor import KEYRING_SERVICE_NAME
from email_processor import clear_passwords as clear_passwords_func
from email_processor.cli.ui import CLIUI
from email_processor.exit_codes import ExitCode
from email_processor.logging.setup import get_logger
from email_processor.security.encryption import encrypt_password


def _read_password_from_file(password_file: str, ui: CLIUI) -> Optional[str]:
    """Read password from file.

    Args:
        password_file: Path to password file
        ui: CLIUI instance for output

    Returns:
        Password string or None on error
    """
    password_path = Path(password_file)
    if not password_path.exists():
        ui.error(f"Password file not found: {password_path}")
        return None

    # Check file permissions (Unix only)
    if sys.platform != "win32":
        try:
            file_stat = password_path.stat()
            file_mode = stat.filemode(file_stat.st_mode)
            # Check if file is readable by others (group or world)
            if file_stat.st_mode & (stat.S_IRGRP | stat.S_IROTH):
                ui.warn(
                    f"Password file has open permissions: {file_mode}. "
                    "Consider using chmod 600 for security."
                )
        except Exception:
            pass  # Ignore permission check errors

    try:
        # Read password from file (first line, strip whitespace)
        with open(password_path, encoding="utf-8") as f:
            raw_line = f.readline()
            password = raw_line.rstrip(
                "\n\r"
            )  # Only remove line endings, preserve leading/trailing spaces
    except PermissionError:
        ui.error(f"Permission denied reading password file: {password_path}")
        return None
    except Exception as e:
        ui.error(f"Failed to read password file: {e}")
        return None

    if not password:
        ui.error("Password file is empty")
        return None

    return password


def clear_passwords(user: str, ui: CLIUI) -> int:
    """Clear stored password for IMAP user.

    Args:
        user: IMAP user login
        ui: CLIUI instance for output

    Returns:
        int: 0 on success, 1 on error
    """
    try:
        clear_passwords_func(KEYRING_SERVICE_NAME, user)
        ui.success(f"Password cleared for {user}")
        return ExitCode.SUCCESS
    except Exception as e:
        ui.error(f"Failed to clear password: {e}")
        return ExitCode.PROCESSING_ERROR


def set_password(
    user: str,
    password_file: Optional[str],
    delete_after_read: bool,
    config_path: Optional[str],
    ui: CLIUI,
) -> int:
    """Set password for IMAP user.

    Args:
        user: IMAP user login
        password_file: Path to password file (if None, will prompt)
        delete_after_read: Whether to delete password file after reading
        config_path: Path to configuration file (for encryption)
        ui: CLIUI instance for output

    Returns:
        int: 0 on success, 1 on error, 4 on authentication error
    """
    # Read password
    if password_file:
        password = _read_password_from_file(password_file, ui)
        if password is None:
            return ExitCode.FILE_NOT_FOUND
        password_path = Path(password_file)
    else:
        # Prompt for password
        password = ui.input("Enter password: ")
        if not password:
            ui.error("Password cannot be empty")
            return ExitCode.VALIDATION_FAILED
        password_path = None

    # Log password length for debugging (without showing actual password)
    logger = get_logger()
    if password_path:
        logger.debug(
            "password_read_from_file", password_length=len(password), file_path=str(password_path)
        )

    # Save password to keyring
    try:
        if config_path:
            encrypted_password = encrypt_password(password, config_path)
            keyring.set_password(KEYRING_SERVICE_NAME, user, encrypted_password)
        else:
            keyring.set_password(KEYRING_SERVICE_NAME, user, password)
        ui.success(f"Password saved for {user}")
    except Exception as e:
        # Try saving unencrypted as fallback
        try:
            keyring.set_password(KEYRING_SERVICE_NAME, user, password)
            if config_path:
                # Check if it's an ImportError (cryptography not installed)
                if isinstance(e, ImportError) and "cryptography" in str(e):
                    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
                    ui.warn(
                        f"Password saved unencrypted. "
                        f"To enable encryption, install cryptography for Python {python_version}: "
                        f"pip install cryptography>=40.0.0"
                    )
                else:
                    ui.warn(f"Password saved unencrypted (encryption failed: {e})")
            ui.success(f"Password saved for {user}")
        except Exception as e2:
            ui.error(f"Failed to save password: {e2}")
            return ExitCode.UNSUPPORTED_FORMAT  # Authentication/keyring error

    # Remove password file if requested
    if delete_after_read and password_path:
        try:
            password_path.unlink()
            ui.success(f"Password file removed: {password_path}")
        except Exception as e:
            ui.warn(f"Failed to remove password file: {e}")
            # Don't fail the command if file removal fails

    return ExitCode.SUCCESS
