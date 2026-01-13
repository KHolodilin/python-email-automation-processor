"""IMAP authentication with keyring support."""

import getpass

import keyring

from email_processor.config.constants import KEYRING_SERVICE_NAME
from email_processor.logging.setup import get_logger


def get_imap_password(imap_user: str) -> str:
    """Get IMAP password from keyring or prompt user."""
    logger = get_logger()
    password = keyring.get_password(KEYRING_SERVICE_NAME, imap_user)
    if password:
        logger.info("password_retrieved", user=imap_user, service=KEYRING_SERVICE_NAME)
        return password  # type: ignore[no-any-return]

    logger.info("password_not_found", user=imap_user)
    pw = getpass.getpass(f"Enter IMAP password for {imap_user}: ")
    if not pw:
        raise ValueError("Password not entered, operation aborted.")

    answer = input("Save password to system storage (keyring)? [y/N]: ").strip().lower()
    if answer == "y":
        try:
            keyring.set_password(KEYRING_SERVICE_NAME, imap_user, pw)
            logger.info("password_saved", user=imap_user, service=KEYRING_SERVICE_NAME)
        except Exception as e:
            logger.error("password_save_error", user=imap_user, error=str(e))

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
