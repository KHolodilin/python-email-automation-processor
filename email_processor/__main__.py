"""Main entry point for email-processor package."""

import re
import sys
from email.utils import parseaddr

from email_processor import ConfigLoader, __version__
from email_processor.cli import CLIUI
from email_processor.cli.args import parse_arguments
from email_processor.cli.commands import config, imap, passwords, smtp, status
from email_processor.exit_codes import ExitCode
from email_processor.logging.setup import get_logger, setup_logging


def _validate_email(email_str: str) -> bool:
    """Validate email address format.

    Args:
        email_str: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    if not email_str:
        return False
    # Use email.utils.parseaddr to validate
    _name, addr = parseaddr(email_str)
    # Basic email regex check
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(email_pattern, addr)) if addr else False


def _load_config(config_path: str, ui: CLIUI) -> tuple[dict, int]:
    """Load configuration file and return config dict and status code.

    Args:
        config_path: Path to configuration file
        ui: CLIUI instance for output

    Returns:
        tuple: (config_dict, status_code) where status_code is 0 on success, 3 on config error
    """
    try:
        cfg = ConfigLoader.load(config_path, ui=ui)
        return cfg, ExitCode.SUCCESS
    except FileNotFoundError as e:
        ui.error(str(e))
        if ui.has_rich:
            ui.print(f"Please create [cyan]{config_path}[/cyan] based on config.yaml.example")
        else:
            ui.info(f"Please create {config_path} based on config.yaml.example")
        return {}, ExitCode.CONFIG_ERROR
    except ValueError as e:
        ui.error(f"Configuration error: {e}")
        return {}, ExitCode.CONFIG_ERROR
    except Exception as e:
        ui.error(f"Unexpected error loading configuration: {e}")
        return {}, ExitCode.CONFIG_ERROR


def _setup_logging_from_args(cfg: dict, args) -> None:
    """Setup logging based on configuration and command line arguments.

    Args:
        cfg: Configuration dictionary
        args: Parsed arguments
    """
    log_config = cfg.get("logging", {})
    if not log_config:
        # Fallback to old format for backward compatibility
        proc_cfg = cfg.get("processing", {})
        log_config = {
            "level": proc_cfg.get("log_level", "INFO"),
            "format": "console",
            "format_file": "json",
            "file": proc_cfg.get("log_file") if proc_cfg.get("log_file") else None,
        }

    # Override with command line arguments
    if args.log_level:
        log_config["level"] = args.log_level
    elif args.verbose:
        log_config["level"] = "DEBUG"
    elif args.quiet:
        log_config["level"] = "ERROR"

    if args.log_file:
        log_config["file"] = args.log_file
    if args.json_logs:
        log_config["format"] = "json"
        log_config["format_file"] = "json"

    setup_logging(log_config)


def _parse_duration(duration_str: str) -> int:
    """Parse duration string like '7d', '24h' to days.

    Args:
        duration_str: Duration string (e.g., '7d', '24h')

    Returns:
        Number of days
    """
    if not duration_str:
        return 0

    match = re.match(r"^(\d+)([dh])$", duration_str.lower())
    if not match:
        return 0

    value = int(match.group(1))
    unit = match.group(2)

    if unit == "d":
        return value
    elif unit == "h":
        return int(value / 24.0)  # Convert hours to days
    return 0


def main() -> int:
    """Main entry point for CLI."""
    # Parse arguments
    args = parse_arguments()

    # Create UI instance with verbose/quiet flags
    ui = CLIUI(verbose=args.verbose, quiet=args.quiet)

    # Print version to console (unless quiet mode)
    if not args.quiet:
        ui.info(f"Email Processor v{__version__}")

    # Handle subcommands
    if not args.command:
        # Default: run command (backward compatibility)
        args.command = "run"

    # Command: config init
    if args.command == "config" and args.config_command == "init":
        config_path = args.path if hasattr(args, "path") and args.path else args.config
        return config.create_default_config(config_path, ui)

    # Command: config validate
    if args.command == "config" and args.config_command == "validate":
        cfg, status_code = _load_config(args.config, ui)
        if status_code != ExitCode.SUCCESS:
            return status_code
        return config.validate_config_file(args.config, ui)

    # Command: status
    if args.command == "status":
        return status.show_status(args.config, ui)

    # Commands that require config loading
    config_path = args.config
    cfg, status_code = _load_config(config_path, ui)
    if status_code != ExitCode.SUCCESS:
        return status_code

    # Setup logging
    _setup_logging_from_args(cfg, args)

    # Command: password set
    if args.command == "password" and args.password_command == "set":
        user = args.user or cfg.get("imap", {}).get("user")
        if not user:
            ui.error("--user is required or set imap.user in config")
            return ExitCode.VALIDATION_FAILED
        return passwords.set_password(
            user,
            args.password_file if hasattr(args, "password_file") else None,
            args.delete_after_read if hasattr(args, "delete_after_read") else False,
            config_path,
            ui,
        )

    # Command: password clear
    if args.command == "password" and args.password_command == "clear":
        user = args.user or cfg.get("imap", {}).get("user")
        if not user:
            ui.error("--user is required or set imap.user in config")
            return ExitCode.VALIDATION_FAILED
        return passwords.clear_passwords(user, ui)

    # Command: send (default: send folder when no subcommand)
    if args.command == "send" and args.send_command is None:
        args.send_command = "folder"
        if not hasattr(args, "dir"):
            args.dir = None
        if not hasattr(args, "to"):
            args.to = None

    # Command: send file
    if args.command == "send" and args.send_command == "file":
        if not hasattr(args, "path") or not args.path:
            ui.error("File path is required")
            return ExitCode.VALIDATION_FAILED
        if not hasattr(args, "to") or not args.to:
            ui.error("--to is required")
            return ExitCode.VALIDATION_FAILED

        # Validate email addresses
        if not _validate_email(args.to):
            ui.error(f"Invalid email address: {args.to}")
            return ExitCode.VALIDATION_FAILED
        if hasattr(args, "cc") and args.cc and not _validate_email(args.cc):
            ui.error(f"Invalid CC email address: {args.cc}")
            return ExitCode.VALIDATION_FAILED
        if hasattr(args, "bcc") and args.bcc and not _validate_email(args.bcc):
            ui.error(f"Invalid BCC email address: {args.bcc}")
            return ExitCode.VALIDATION_FAILED

        return smtp.send_file(
            cfg,
            args.path,
            args.to,
            args.subject if hasattr(args, "subject") else None,
            args.dry_run,
            config_path,
            ui,
        )

    # Command: send folder
    if args.command == "send" and args.send_command == "folder":
        folder = args.dir if hasattr(args, "dir") else None
        to_addr = args.to if hasattr(args, "to") else None
        folder = folder or cfg.get("smtp", {}).get("send_folder")
        to_addr = to_addr or cfg.get("smtp", {}).get("default_recipient")
        if not folder:
            ui.error("Directory path is required or set smtp.send_folder in config")
            return ExitCode.VALIDATION_FAILED
        if not to_addr:
            ui.error("--to is required or set smtp.default_recipient in config")
            return ExitCode.VALIDATION_FAILED

        # Validate email addresses
        if not _validate_email(to_addr):
            ui.error(f"Invalid email address: {to_addr}")
            return ExitCode.VALIDATION_FAILED
        if hasattr(args, "cc") and args.cc and not _validate_email(args.cc):
            ui.error(f"Invalid CC email address: {args.cc}")
            return ExitCode.VALIDATION_FAILED
        if hasattr(args, "bcc") and args.bcc and not _validate_email(args.bcc):
            ui.error(f"Invalid BCC email address: {args.bcc}")
            return ExitCode.VALIDATION_FAILED

        return smtp.send_folder(
            cfg,
            folder,
            to_addr,
            args.subject if hasattr(args, "subject") else None,
            args.dry_run,
            config_path,
            ui,
        )

    # Command: fetch
    if args.command == "fetch":
        # Parse --since duration if provided
        start_days_back = 5  # default
        if hasattr(args, "since") and args.since:
            days = _parse_duration(args.since)
            if days > 0:
                start_days_back = int(days) if days >= 1 else 1

        # Update config with command line options
        if hasattr(args, "folder") and args.folder:
            cfg.setdefault("imap", {})["folder"] = args.folder
        if hasattr(args, "max_emails") and args.max_emails:
            cfg.setdefault("processing", {})["max_emails"] = args.max_emails
        cfg.setdefault("processing", {})["start_days_back"] = start_days_back

        dry_run = args.dry_run or (
            args.dry_run_no_connect if hasattr(args, "dry_run_no_connect") else False
        )
        mock_mode = args.dry_run_no_connect if hasattr(args, "dry_run_no_connect") else False
        return imap.run_processor(cfg, dry_run, mock_mode, config_path, ui)

    # Command: run (default, full pipeline)
    if args.command == "run" or args.command is None:
        # Parse --since duration if provided
        start_days_back = 5  # default
        if hasattr(args, "since") and args.since:
            days = _parse_duration(args.since)
            if days > 0:
                start_days_back = int(days) if days >= 1 else 1

        # Update config with command line options
        if hasattr(args, "folder") and args.folder:
            cfg.setdefault("imap", {})["folder"] = args.folder
        if hasattr(args, "max_emails") and args.max_emails:
            cfg.setdefault("processing", {})["max_emails"] = args.max_emails
        cfg.setdefault("processing", {})["start_days_back"] = start_days_back

        dry_run = args.dry_run or (
            args.dry_run_no_connect if hasattr(args, "dry_run_no_connect") else False
        )
        mock_mode = args.dry_run_no_connect if hasattr(args, "dry_run_no_connect") else False

        # Log warning if SMTP section is missing (for backward compatibility)
        if "smtp" not in cfg:
            logger = get_logger()
            logger.warning(
                "smtp_section_missing",
                message="SMTP section is missing in config.yaml. SMTP functionality will be skipped. "
                "Add 'smtp' section to enable email sending features.",
            )

        return imap.run_processor(cfg, dry_run, mock_mode, config_path, ui)

    # Unknown command
    ui.error(f"Unknown command: {args.command}")
    return ExitCode.VALIDATION_FAILED


if __name__ == "__main__":
    sys.exit(main())
