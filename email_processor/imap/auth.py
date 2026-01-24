"""IMAP authentication with keyring support."""

import getpass
from typing import Optional

import keyring

from email_processor.config.constants import KEYRING_SERVICE_NAME
from email_processor.logging.setup import get_logger
from email_processor.security.encryption import (
    decrypt_password,
    encrypt_password,
    is_encrypted,
)
from email_processor.utils.redact import redact_email


def get_imap_password(imap_user: str, config_path: Optional[str] = None) -> str:
    """Get IMAP password from keyring or prompt user.

    Args:
        imap_user: IMAP username (email address)
        config_path: Optional path to config file for encryption key generation

    Returns:
        Plain text password (decrypted if stored encrypted)
    """
    logger = get_logger()
    stored_password = keyring.get_password(KEYRING_SERVICE_NAME, imap_user)
    if stored_password:
        # Check if password is encrypted
        if is_encrypted(stored_password):
            try:
                password = decrypt_password(stored_password, config_path)
                logger.debug(
                    "password_decrypted_length",
                    password_length=len(password),
                    user=redact_email(imap_user),
                )
                logger.info(
                    "password_retrieved_decrypted",
                    user=redact_email(imap_user),
                    service=KEYRING_SERVICE_NAME,
                )
                return password
            except ValueError as e:
                # Decryption failed - system characteristics may have changed
                logger.error(
                    "password_decryption_failed",
                    user=redact_email(imap_user),
                    error=str(e),
                    hint="System characteristics may have changed. Password needs to be re-entered.",
                )
                raise ValueError(
                    f"Failed to decrypt password for {imap_user}. "
                    "System characteristics may have changed. "
                    "Please clear saved password with --clear-passwords and re-enter it."
                ) from e
            except Exception as e:
                logger.error(
                    "password_decryption_error",
                    user=redact_email(imap_user),
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise ValueError(
                    f"Failed to decrypt password for {imap_user}. "
                    "Please clear saved password with --clear-passwords and re-enter it."
                ) from e
        else:
            # Old format - unencrypted password
            logger.info(
                "password_retrieved",
                user=redact_email(imap_user),
                service=KEYRING_SERVICE_NAME,
                encrypted=False,
            )
            return stored_password  # type: ignore[no-any-return]

    logger.info("password_not_found", user=redact_email(imap_user))
    pw = getpass.getpass(f"Enter IMAP password for {imap_user}: ")
    if not pw:
        raise ValueError("Password not entered, operation aborted.")

    answer = input("Save password to system storage (keyring)? [y/N]: ").strip().lower()
    if answer == "y":
        try:
            # Encrypt password before saving
            encrypted_password = encrypt_password(pw, config_path)
            keyring.set_password(KEYRING_SERVICE_NAME, imap_user, encrypted_password)
            logger.info(
                "password_saved_encrypted",
                user=redact_email(imap_user),
                service=KEYRING_SERVICE_NAME,
                encrypted=True,
            )
        except Exception as e:
            logger.error("password_save_error", user=redact_email(imap_user), error=str(e))
            # Try saving unencrypted as fallback
            try:
                keyring.set_password(KEYRING_SERVICE_NAME, imap_user, pw)
                logger.warning(
                    "password_saved_unencrypted_fallback",
                    user=redact_email(imap_user),
                    error=str(e),
                )
            except Exception as e2:
                logger.error(
                    "password_save_fallback_error",
                    user=redact_email(imap_user),
                    error=str(e2),
                )

    return pw


def clear_passwords(service: str, primary_user: str) -> None:
    """Clear saved passwords from keyring."""
    print(f"\nClearing passwords for service: {service}")
    confirm = input("Do you really want to delete all saved passwords? [y/N]: ").strip().lower()

    if confirm != "y":
        print("Cancelled.")
        return

    deleted = 0

    # Primary user from config.yaml
    try:
        keyring.delete_password(service, primary_user)
        print(f"Deleted: {service} / {primary_user}")
        deleted += 1
    except Exception:
        print(f"Not found: {service} / {primary_user}")

    # Can also delete fallback logins if they appear
    possible_users = [
        primary_user,
        primary_user.lower(),
        primary_user.upper(),
    ]

    for user in set(possible_users):
        try:
            keyring.delete_password(service, user)
            print(f"Deleted: {service} / {user}")
            deleted += 1
        except Exception:
            pass

    print(f"\nDone. Deleted entries: {deleted}")


class IMAPAuth:
    """IMAP authentication class."""

    @staticmethod
    def get_password(user: str) -> str:
        """Get IMAP password from keyring or prompt user."""
        return get_imap_password(user)

    @staticmethod
    def clear_passwords(service: str, user: str) -> None:
        """Clear saved passwords from keyring."""
        clear_passwords(service, user)
