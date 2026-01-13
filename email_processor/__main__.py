"""Main entry point for email_processor package."""

import argparse
import logging
import shutil
import sys
from pathlib import Path

from email_processor import (
    CONFIG_FILE,
    KEYRING_SERVICE_NAME,
    ConfigLoader,
    EmailProcessor,
    __version__,
    clear_passwords,
)

CONFIG_EXAMPLE = "config.yaml.example"


def create_default_config(config_path: str) -> int:
    """Create default configuration file from config.yaml.example."""
    example_path = Path(CONFIG_EXAMPLE)
    target_path = Path(config_path)

    if not example_path.exists():
        print(f"Error: Template file {CONFIG_EXAMPLE} not found")
        print(f"Expected location: {example_path.absolute()}")
        return 1

    if target_path.exists():
        response = input(f"Configuration file {config_path} already exists. Overwrite? [y/N]: ")
        if response.lower() != "y":
            print("Cancelled.")
            return 0

    try:
        # Create parent directories if needed
        target_path.parent.mkdir(parents=True, exist_ok=True)
        # Copy the example file
        shutil.copy2(example_path, target_path)
        print(f"Created configuration file: {target_path.absolute()}")
        print(f"Please edit {config_path} with your IMAP settings.")
        return 0
    except OSError as e:
        print(f"Error creating configuration file: {e}")
        return 1


def main() -> int:
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Email Attachment Processor - Downloads attachments from IMAP, organizes by topic, and archives messages.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Version {__version__}",
    )
    parser.add_argument(
        "--clear-passwords", action="store_true", help="Clear saved passwords from keyring"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate processing without downloading or archiving",
    )
    parser.add_argument(
        "--dry-run-no-connect",
        action="store_true",
        help="Dry-run mode with mock IMAP server (no real connection, uses simulated data)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=CONFIG_FILE,
        help=f"Path to configuration file (default: {CONFIG_FILE})",
    )
    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Create default configuration file from config.yaml.example",
    )
    parser.add_argument("--version", action="version", version=f"Email Processor {__version__}")
    args = parser.parse_args()

    # Handle --create-config command
    if args.create_config:
        return create_default_config(args.config)

    config_path = args.config
    try:
        cfg = ConfigLoader.load(config_path)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print(f"Please create {config_path} based on config.yaml.example")
        return 1
    except ValueError as e:
        print(f"Configuration error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error loading configuration: {e}")
        return 1

    if args.clear_passwords:
        user = cfg.get("imap", {}).get("user")
        if not user:
            print("Error: 'imap.user' is missing in config.yaml")
            return 1
        clear_passwords(KEYRING_SERVICE_NAME, user)
    else:
        try:
            processor = EmailProcessor(cfg)
            # If --dry-run-no-connect is set, enable both dry_run and mock_mode
            dry_run = args.dry_run or args.dry_run_no_connect
            mock_mode = args.dry_run_no_connect
            result = processor.process(dry_run=dry_run, mock_mode=mock_mode)
            print(
                f"Processed: {result.processed}, Skipped: {result.skipped}, Errors: {result.errors}"
            )
        except KeyboardInterrupt:
            logging.info("Interrupted by user")
            return 0
        except Exception:
            logging.exception("Fatal error during email processing")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
