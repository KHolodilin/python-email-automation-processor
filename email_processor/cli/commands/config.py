"""Configuration management commands."""

import shutil
from pathlib import Path

from email_processor.cli.ui import CLIUI
from email_processor.config.loader import ConfigLoader, validate_config
from email_processor.exit_codes import ExitCode

CONFIG_EXAMPLE = "config.yaml.example"


def create_default_config(config_path: str, ui: CLIUI) -> int:
    """Create default configuration file from config.yaml.example.

    Args:
        config_path: Path to target configuration file
        ui: CLIUI instance for output

    Returns:
        int: 0 on success, 1 on error
    """
    example_path = Path(CONFIG_EXAMPLE)
    target_path = Path(config_path)

    if not example_path.exists():
        ui.error(f"Template file {CONFIG_EXAMPLE} not found")
        ui.info(f"Expected location: {example_path.absolute()}")
        return ExitCode.FILE_NOT_FOUND

    if target_path.exists():
        response = ui.input(f"Configuration file {config_path} already exists. Overwrite? [y/N]: ")
        if response.lower() != "y":
            ui.warn("Cancelled.")
            return ExitCode.SUCCESS

    try:
        # Create parent directories if needed
        target_path.parent.mkdir(parents=True, exist_ok=True)
        # Copy the example file
        shutil.copy2(example_path, target_path)
        ui.success(f"Created configuration file: {target_path.absolute()}")
        if ui.has_rich:
            ui.print(f"Please edit [cyan]{config_path}[/cyan] with your IMAP settings.")
        else:
            ui.info(f"Please edit {config_path} with your IMAP settings.")
        return ExitCode.SUCCESS
    except OSError as e:
        ui.error(f"Error creating configuration file: {e}")
        return ExitCode.PROCESSING_ERROR


def validate_config_file(config_path: str, ui: CLIUI) -> int:
    """Validate configuration file.

    Args:
        config_path: Path to configuration file
        ui: CLIUI instance for output

    Returns:
        int: 0 on success, 3 on validation error, 1 on other error
    """
    try:
        cfg = ConfigLoader.load(config_path, ui=ui)
        validate_config(cfg, ui=ui)
        ui.success(f"Configuration file is valid: {config_path}")
        return ExitCode.SUCCESS
    except FileNotFoundError as e:
        ui.error(f"Configuration file not found: {e}")
        return ExitCode.FILE_NOT_FOUND
    except ValueError as e:
        ui.error(f"Configuration validation failed: {e}")
        return ExitCode.CONFIG_ERROR
    except Exception as e:
        ui.error(f"Unexpected error validating configuration: {e}")
        return ExitCode.PROCESSING_ERROR
