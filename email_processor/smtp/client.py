"""SMTP client for email sending operations."""

import smtplib
import time
from typing import Union

from email_processor.logging.setup import get_logger
from email_processor.utils.redact import redact_email


def smtp_connect(
    server: str,
    port: int,
    user: str,
    password: str,
    use_tls: bool = True,
    use_ssl: bool = False,
    max_retries: int = 5,
    retry_delay: int = 3,
) -> Union[smtplib.SMTP, smtplib.SMTP_SSL]:
    """Connect to SMTP server with retry logic.

    Args:
        server: SMTP server hostname
        port: SMTP server port
        user: SMTP username (email address)
        password: SMTP password
        use_tls: Use TLS encryption (for port 587)
        use_ssl: Use SSL encryption (for port 465)
        max_retries: Maximum number of connection retry attempts
        retry_delay: Delay between retry attempts in seconds

    Returns:
        Connected SMTP object

    Raises:
        ConnectionError: If connection fails after all retries
        ValueError: If both use_tls and use_ssl are True, or if authentication fails
    """
    if use_tls and use_ssl:
        raise ValueError("Cannot use both TLS and SSL at the same time")

    logger = get_logger()
    attempts = 0

    while attempts < max_retries:
        try:
            attempts += 1
            logger.debug(
                "smtp_connecting",
                server=server,
                port=port,
                use_tls=use_tls,
                use_ssl=use_ssl,
                attempt=attempts,
                max_retries=max_retries,
            )

            if use_ssl:
                logger.debug("smtp_ssl_connection", server=server, port=port)
                smtp: Union[smtplib.SMTP, smtplib.SMTP_SSL] = smtplib.SMTP_SSL(server, port)
                logger.debug("smtp_ssl_connected")
            else:
                logger.debug("smtp_plain_connection", server=server, port=port)
                smtp = smtplib.SMTP(server, port)
                if use_tls:
                    logger.debug("smtp_starting_tls")
                    smtp.starttls()
                    logger.debug("smtp_tls_started")

            logger.debug("smtp_authenticating", user=redact_email(user))
            smtp.login(user, password)
            logger.debug("smtp_authenticated")
            logger.info(
                "smtp_connected", server=server, port=port, use_tls=use_tls, use_ssl=use_ssl
            )
            return smtp

        except smtplib.SMTPAuthenticationError as e:
            # Authentication errors should not be retried
            logger.error("smtp_authentication_failed", server=server, error=str(e))
            raise ValueError(f"SMTP authentication failed: {e}") from e

        except (smtplib.SMTPException, OSError, ConnectionError) as e:
            # Other SMTP errors can be retried
            logger.error(
                "smtp_connection_error",
                server=server,
                port=port,
                error=str(e),
                attempt=attempts,
            )
            if attempts < max_retries:
                logger.info("smtp_retry", delay=retry_delay, attempt=attempts)
                time.sleep(retry_delay)
            else:
                logger.error(
                    "smtp_connection_failed", server=server, port=port, max_retries=max_retries
                )
                raise ConnectionError(
                    f"Failed to connect to SMTP server {server}:{port} after {max_retries} attempts: {e}"
                ) from e

        except Exception as e:
            # Unexpected errors should not be retried
            logger.error(
                "smtp_unexpected_error",
                server=server,
                port=port,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ConnectionError(
                f"Unexpected error connecting to SMTP server {server}:{port}: {e}"
            ) from e

    # Should not reach here, but just in case
    raise ConnectionError(
        f"Failed to connect to SMTP server {server}:{port} after {max_retries} attempts"
    )
