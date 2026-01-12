"""Configuration module for email processor."""

from email_processor.config.loader import ConfigLoader, load_config, validate_config
from email_processor.config.constants import KEYRING_SERVICE_NAME, CONFIG_FILE, MAX_ATTACHMENT_SIZE

__all__ = [
    "ConfigLoader",
    "load_config",
    "validate_config",
    "KEYRING_SERVICE_NAME",
    "CONFIG_FILE",
    "MAX_ATTACHMENT_SIZE",
]
