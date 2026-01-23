"""Configuration loading and validation."""

import re
from pathlib import Path
from typing import Any, Optional

import yaml


def validate_config(cfg: dict, ui: Optional[Any] = None) -> None:
    """Validate configuration structure and required fields.

    Args:
        cfg: Configuration dictionary to validate
        ui: Optional CLIUI instance for output (if None, uses print as fallback)
    """
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
            # Use ui.warn if available, otherwise print as fallback
            warning_msg = "Warning: 'allowed_senders' is empty - no emails will be processed"
            if ui is not None:
                ui.warn(warning_msg)
            else:
                print(warning_msg)

    # Validate topic_mapping (required, must have at least one rule)
    if "topic_mapping" not in cfg:
        errors.append("Missing required section: 'topic_mapping'")
    elif not isinstance(cfg["topic_mapping"], dict):
        errors.append("'topic_mapping' must be a dictionary")
    elif len(cfg["topic_mapping"]) == 0:
        errors.append(
            "'topic_mapping' must contain at least one rule (the last one is used as default)"
        )
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

    # Validate SMTP section (optional)
    if "smtp" in cfg:
        smtp = cfg["smtp"]
        if not isinstance(smtp, dict):
            errors.append("'smtp' must be a dictionary")
        else:
            if "server" not in smtp or not smtp["server"]:
                errors.append("'smtp.server' is required when smtp section is present")
            if "port" in smtp:
                try:
                    port = int(smtp["port"])
                    if port < 1 or port > 65535:
                        errors.append("'smtp.port' must be between 1 and 65535")
                except (ValueError, TypeError):
                    errors.append("'smtp.port' must be an integer")
            if "use_tls" in smtp and not isinstance(smtp["use_tls"], bool):
                errors.append("'smtp.use_tls' must be a boolean")
            if "use_ssl" in smtp and not isinstance(smtp["use_ssl"], bool):
                errors.append("'smtp.use_ssl' must be a boolean")
            if "max_email_size" in smtp:
                try:
                    size = float(smtp["max_email_size"])
                    if size <= 0:
                        errors.append("'smtp.max_email_size' must be > 0")
                except (ValueError, TypeError):
                    errors.append("'smtp.max_email_size' must be a number")
            if "from_address" not in smtp or not smtp["from_address"]:
                errors.append("'smtp.from_address' is required when smtp section is present")
            else:
                from_addr = smtp["from_address"]
                if not isinstance(from_addr, str) or not from_addr:
                    errors.append("'smtp.from_address' must be a non-empty string")
                # Basic email validation
                elif "@" not in from_addr or "." not in from_addr.split("@")[-1]:
                    errors.append("'smtp.from_address' must be a valid email address")
            if "default_recipient" in smtp:
                recipient = smtp["default_recipient"]
                if not isinstance(recipient, str) or not recipient:
                    errors.append("'smtp.default_recipient' must be a non-empty string")
                elif "@" not in recipient or "." not in recipient.split("@")[-1]:
                    # Basic email validation
                    errors.append("'smtp.default_recipient' must be a valid email address")

    if errors:
        error_msg = "Configuration validation failed:\n  - " + "\n  - ".join(errors)
        raise ValueError(error_msg)


def load_config(path: str, ui: Optional[Any] = None) -> dict[str, Any]:
    """Load and validate configuration from YAML file.

    Args:
        path: Path to configuration file
        ui: Optional CLIUI instance for output (if None, uses print as fallback)

    Returns:
        Configuration dictionary
    """
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

    validate_config(cfg, ui=ui)
    return cfg


class ConfigLoader:
    """Configuration loader class."""

    @staticmethod
    def load(path: str, ui: Optional[Any] = None) -> dict[str, Any]:
        """Load and validate configuration from YAML file.

        Args:
            path: Path to configuration file
            ui: Optional CLIUI instance for output (if None, uses print as fallback)

        Returns:
            Configuration dictionary
        """
        return load_config(path, ui=ui)

    @staticmethod
    def validate(cfg: dict, ui: Optional[Any] = None) -> None:
        """Validate configuration structure and required fields.

        Args:
            cfg: Configuration dictionary to validate
            ui: Optional CLIUI instance for output (if None, uses print as fallback)
        """
        validate_config(cfg, ui=ui)
