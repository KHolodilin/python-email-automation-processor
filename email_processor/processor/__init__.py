"""Processor module for email processing."""

from email_processor.processor.attachments import AttachmentHandler
from email_processor.processor.email_processor import EmailProcessor
from email_processor.processor.filters import EmailFilter

__all__ = [
    "AttachmentHandler",
    "EmailFilter",
    "EmailProcessor",
]
