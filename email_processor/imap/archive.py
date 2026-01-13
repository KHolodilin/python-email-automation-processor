"""Archive manager for email messages."""

import imaplib

from email_processor.logging.setup import get_logger


def archive_message(mail: imaplib.IMAP4_SSL, uid: str, archive_folder: str) -> None:
    """Archive message with improved error handling."""
    logger = get_logger(uid=uid)
    try:
        mail.create(archive_folder)
    except imaplib.IMAP4.error as e:
        # Folder might already exist, which is fine
        logger.debug("archive_folder_create", archive_folder=archive_folder, error=str(e))
    except Exception as e:
        logger.warning("archive_folder_create_error", archive_folder=archive_folder, error=str(e))

    try:
        result = mail.uid("COPY", uid, archive_folder)
        if not result or result[0] != "OK":
            logger.error(
                "archive_copy_failed",
                archive_folder=archive_folder,
                status=result[0] if result else "None",
            )
            return
    except imaplib.IMAP4.error as e:
        logger.error("archive_copy_imap_error", archive_folder=archive_folder, error=str(e))
        return
    except Exception as e:
        logger.error("archive_copy_error", archive_folder=archive_folder, error=str(e))
        return

    try:
        mail.uid("STORE", uid, "+FLAGS", "(\\Deleted)")
        mail.expunge()
        logger.info("message_archived", archive_folder=archive_folder)
    except imaplib.IMAP4.error as e:
        logger.error("archive_store_imap_error", error=str(e))
    except Exception as e:
        logger.error("archive_store_error", error=str(e))


class ArchiveManager:
    """Archive manager class for email messages."""

    @staticmethod
    def archive_message(client, uid: str, folder: str) -> None:
        """Archive message with improved error handling."""
        if hasattr(client, "_mail"):
            archive_message(client._mail, uid, folder)
        else:
            archive_message(client, uid, folder)
