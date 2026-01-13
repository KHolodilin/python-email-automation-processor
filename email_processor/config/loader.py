"""Configuration loading and validation."""

import re
from pathlib import Path
from typing import Any

import yaml


def validate_config(cfg: dict) -> None:
    """Validate configuration structure and required fields."""
    errors = []

    # Validate IMAP section
    if "imap" not in cfg:
        errors.append("Missing required section: 'imap'")
    else:
        imap = cfg["imap"]
        if not isinstance(imap, dict):
            errors.append("'imap' must be a dictionary")
        else:
            if "server" not in imap or not imap["server"]:
                errors.append("'imap.server' is required")
            if "user" not in imap or not imap["user"]:
                errors.append("'imap.user' is required")
            if "max_retries" in imap:
                try:
                    retries = int(imap["max_retries"])
                    if retries < 1:
                        errors.append("'imap.max_retries' must be >= 1")
                except (ValueError, TypeError):
                    errors.append("'imap.max_retries' must be an integer")
            if "retry_delay" in imap:
                try:
                    delay = int(imap["retry_delay"])
                    if delay < 0:
                        errors.append("'imap.retry_delay' must be >= 0")
                except (ValueError, TypeError):
                    errors.append("'imap.retry_delay' must be an integer")

    # Validate processing section
    if "processing" not in cfg:
        errors.append("Missing required section: 'processing'")
    else:
        proc = cfg["processing"]
        if not isinstance(proc, dict):
            errors.append("'processing' must be a dictionary")
        else:
            if "start_days_back" in proc:
                try:
                    days = int(proc["start_days_back"])
                    if days < 0:
                        errors.append("'processing.start_days_back' must be >= 0")
                except (ValueError, TypeError):
                    errors.append("'processing.start_days_back' must be an integer")
            if "keep_processed_days" in proc:
                try:
                    keep = int(proc["keep_processed_days"])
                    if keep < 0:
                        errors.append("'processing.keep_processed_days' must be >= 0")
                except (ValueError, TypeError):
                    errors.append("'processing.keep_processed_days' must be an integer")
            if "log_level" in proc:
                valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                if proc["log_level"].upper() not in valid_levels:
                    errors.append(
                        f"'processing.log_level' must be one of: {', '.join(valid_levels)}"
                    )

    # Validate allowed_senders
    if "allowed_senders" in cfg:
        if not isinstance(cfg["allowed_senders"], list):
            errors.append("'allowed_senders' must be a list")
        elif len(cfg["allowed_senders"]) == 0:
            # Use print for validation warnings before logging is set up
            print("Warning: 'allowed_senders' is empty - no emails will be processed")

    # Validate topic_mapping
    if "topic_mapping" in cfg:
        if not isinstance(cfg["topic_mapping"], dict):
            errors.append("'topic_mapping' must be a dictionary")
        else:
            for pattern, folder in cfg["topic_mapping"].items():
                try:
                    re.compile(pattern)
                except re.error as e:
                    errors.append(f"Invalid regex pattern in topic_mapping: '{pattern}' - {e}")
                if not isinstance(folder, str) or not folder:
                    errors.append(
                        f"Invalid folder name for pattern '{pattern}': must be non-empty string"
                    )

    if errors:
        error_msg = "Configuration validation failed:\n  - " + "\n  - ".join(errors)
        raise ValueError(error_msg)


def load_config(path: str) -> dict[str, Any]:
    """Load and validate configuration from YAML file."""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    try:
        with config_path.open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML syntax in {path}: {e}") from e
    except Exception as e:
        raise OSError(f"Error reading configuration file {path}: {e}") from e

    if not isinstance(cfg, dict):
        raise TypeError(f"{path} must contain a top-level YAML object (dictionary).")

    validate_config(cfg)
    return cfg


class ConfigLoader:
    """Configuration loader class."""

    @staticmethod
    def load(path: str) -> dict[str, Any]:
        """Load and validate configuration from YAML file."""
        return load_config(path)

    @staticmethod
    def validate(cfg: dict) -> None:
        """Validate configuration structure and required fields."""
        validate_config(cfg)
