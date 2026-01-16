"""Encryption key generation from system fingerprint."""

import hashlib
from typing import Union

from email_processor.logging.setup import get_logger
from email_processor.security.fingerprint import get_system_fingerprint

# Salt for PBKDF2 - constant for the application
PBKDF2_SALT = b"email-processor-v1"
PBKDF2_ITERATIONS = 100000


def generate_encryption_key(config_path: Union[str, None] = None) -> bytes:
    """Generate encryption key from system fingerprint using PBKDF2.

    Args:
        config_path: Optional path to config file for fingerprint binding

    Returns:
        32-byte encryption key suitable for Fernet (AES-128)
    """
    logger = get_logger()
    fingerprint = get_system_fingerprint(config_path)

    # Use PBKDF2-HMAC-SHA256 to derive key
    # Fernet requires 32 bytes (256 bits)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        fingerprint.encode("utf-8"),
        PBKDF2_SALT,
        PBKDF2_ITERATIONS,
        dklen=32,
    )

    logger.debug("encryption_key_generated", key_hash=hashlib.sha256(key).hexdigest()[:16] + "...")
    return key
