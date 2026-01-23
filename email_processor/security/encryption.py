"""Password encryption and decryption using Fernet."""

import base64
from typing import Any, Union

from email_processor.logging.setup import get_logger
from email_processor.security.key_generator import generate_encryption_key


def _get_fernet() -> type[Any]:
    """Get Fernet class, importing cryptography if needed.

    Returns:
        Fernet class from cryptography.fernet

    Raises:
        ImportError: If cryptography is not installed
    """
    try:
        from cryptography.fernet import Fernet

        return Fernet  # type: ignore[no-any-return]
    except ImportError as e:
        import sys

        python_version = (
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )
        raise ImportError(
            f"cryptography package is required for password encryption. "
            f"Install it with: pip install cryptography>=40.0.0. "
            f"Note: You are using Python {python_version}. "
            f"Make sure cryptography is installed for this Python version."
        ) from e


# Prefix for encrypted passwords
ENCRYPTED_PREFIX = "ENC:"


def is_encrypted(password: str) -> bool:
    """Check if password is encrypted.

    Args:
        password: Password string to check

    Returns:
        True if password starts with ENCRYPTED_PREFIX
    """
    return password.startswith(ENCRYPTED_PREFIX)


def encrypt_password(password: str, config_path: Union[str, None] = None) -> str:
    """Encrypt password using system-based key.

    Args:
        password: Plain text password to encrypt
        config_path: Optional path to config file for key generation

    Returns:
        Encrypted password with ENCRYPTED_PREFIX prefix

    Raises:
        Exception: If encryption fails
    """
    logger = get_logger()
    try:
        Fernet = _get_fernet()
        key = generate_encryption_key(config_path)
        fernet = Fernet(base64.urlsafe_b64encode(key))
        encrypted = fernet.encrypt(password.encode("utf-8"))
        encrypted_str = base64.b64encode(encrypted).decode("utf-8")
        result = f"{ENCRYPTED_PREFIX}{encrypted_str}"
        logger.debug("password_encrypted", password_length=len(password))
        return result
    except Exception as e:
        logger.error("password_encryption_error", error=str(e), error_type=type(e).__name__)
        raise


def decrypt_password(encrypted_password: str, config_path: Union[str, None] = None) -> str:
    """Decrypt password using system-based key.

    Args:
        encrypted_password: Encrypted password string (with or without prefix)
        config_path: Optional path to config file for key generation

    Returns:
        Decrypted plain text password

    Raises:
        ValueError: If password is not encrypted or decryption fails
        Exception: If decryption fails due to key mismatch
    """
    logger = get_logger()
    if not is_encrypted(encrypted_password):
        raise ValueError(f"Password is not encrypted (missing {ENCRYPTED_PREFIX} prefix)")

    try:
        # Remove prefix
        encrypted_data = encrypted_password[len(ENCRYPTED_PREFIX) :]

        # Decode base64
        encrypted_bytes = base64.b64decode(encrypted_data)

        # Generate key and decrypt
        Fernet = _get_fernet()
        key = generate_encryption_key(config_path)
        fernet = Fernet(base64.urlsafe_b64encode(key))
        decrypted = fernet.decrypt(encrypted_bytes)
        password: str = decrypted.decode("utf-8")

        logger.debug("password_decrypted", password_length=len(password))
        return password
    except Exception as e:
        logger.error(
            "password_decryption_error",
            error=str(e),
            error_type=type(e).__name__,
            hint="System characteristics may have changed. Password needs to be re-entered.",
        )
        raise ValueError(
            "Failed to decrypt password. System characteristics may have changed. "
            "Please re-enter your password."
        ) from e
