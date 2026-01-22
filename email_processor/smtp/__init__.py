"""SMTP module for sending emails."""

from email_processor.smtp.client import smtp_connect
from email_processor.smtp.config import SMTPConfig
from email_processor.smtp.sender import EmailSender

__all__ = ["EmailSender", "SMTPConfig", "smtp_connect"]
