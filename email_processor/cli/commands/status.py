"""Status and diagnostics command."""

from pathlib import Path

import keyring

from email_processor import KEYRING_SERVICE_NAME, __version__
from email_processor.cli.ui import CLIUI
from email_processor.config.loader import ConfigLoader
from email_processor.exit_codes import ExitCode


def show_status(config_path: str, ui: CLIUI) -> int:
    """Show diagnostics and environment status.

    Args:
        config_path: Path to configuration file
        ui: CLIUI instance for output

    Returns:
        int: 0 on success, 1 on error
    """
    # Version
    ui.info(f"Version: {__version__}")
    ui.info("")

    # Config path
    config_file = Path(config_path)
    ui.info(f"Config file: {config_file.absolute()}")
    if config_file.exists():
        ui.success("  ✓ Config file exists")
    else:
        ui.warn("  ✗ Config file not found")
    ui.info("")

    # Try to load config for additional info
    try:
        cfg = ConfigLoader.load(config_path, ui=ui)

        # Storage directories
        proc_cfg = cfg.get("processing", {})
        processed_dir = proc_cfg.get("processed_dir", "processed_uids")
        ui.info(f"Processed UIDs directory: {Path(processed_dir).absolute()}")

        # Topic mapping folders
        topic_mapping = cfg.get("topic_mapping", {})
        if topic_mapping:
            ui.info("Topic mapping folders:")
            for pattern, folder in list(topic_mapping.items())[:5]:  # Show first 5
                folder_path = Path(folder)
                if folder_path.exists():
                    ui.success(f"  ✓ {pattern} -> {folder_path.absolute()}")
                else:
                    ui.warn(f"  ✗ {pattern} -> {folder_path.absolute()} (not found)")
            if len(topic_mapping) > 5:
                ui.info(f"  ... and {len(topic_mapping) - 5} more")

        # SMTP sent files directory
        smtp_cfg = cfg.get("smtp", {})
        if smtp_cfg:
            sent_files_dir = smtp_cfg.get("sent_files_dir", "sent_files")
            ui.info(f"Sent files directory: {Path(sent_files_dir).absolute()}")

        ui.info("")

        # IMAP user
        imap_cfg = cfg.get("imap", {})
        user = imap_cfg.get("user")
        if user:
            ui.info(f"IMAP user: {user}")

            # Check keyring
            try:
                password = keyring.get_password(KEYRING_SERVICE_NAME, user)
                if password:
                    ui.success("  ✓ Password stored in keyring")
                else:
                    ui.warn("  ✗ No password found in keyring")
            except Exception as e:
                ui.warn(f"  ✗ Keyring error: {e}")
        else:
            ui.warn("IMAP user: not configured")

    except Exception as e:
        ui.warn(f"Could not load config: {e}")

    ui.info("")

    # Keyring availability
    try:
        keyring.get_keyring()
        ui.success("Keyring: Available")
    except Exception as e:
        ui.warn(f"Keyring: Not available ({e})")

    return ExitCode.SUCCESS
