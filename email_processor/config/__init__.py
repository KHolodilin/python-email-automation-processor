"""Configuration module for email processor."""

from email_processor.config.constants import CONFIG_FILE, KEYRING_SERVICE_NAME, MAX_ATTACHMENT_SIZE
from email_processor.config.loader import ConfigLoader, load_config, validate_config

__all__ = [
    "CONFIG_FILE",
    "KEYRING_SERVICE_NAME",
    "MAX_ATTACHMENT_SIZE",
    "ConfigLoader",
    "load_config",
    "validate_config",
]
