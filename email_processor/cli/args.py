"""Command line argument parsing."""

import argparse

from email_processor import CONFIG_FILE, __version__


def _add_global_options(parser: argparse.ArgumentParser) -> None:
    """Add global options that work for all commands."""
    parser.add_argument(
        "--config",
        type=str,
        default=CONFIG_FILE,
        help=f"Path to configuration file (default: {CONFIG_FILE})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate processing without downloading, archiving, or sending",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set logging level",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        help="Path to log file",
    )
    parser.add_argument(
        "--json-logs",
        action="store_true",
        help="Output logs in JSON format",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress non-error output",
    )


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments using subcommands."""
    parser = argparse.ArgumentParser(
        prog="email-processor",
        description="Email Attachment Processor - Downloads attachments from IMAP, organizes by topic, and archives messages.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Version {__version__}",
    )

    # Add global options
    _add_global_options(parser)

    parser.add_argument("--version", action="version", version=f"Email Processor {__version__}")

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands", metavar="COMMAND")

    # Command: run (full pipeline)
    run_parser = subparsers.add_parser(
        "run",
        help="Full pipeline: fetch emails, process attachments, and send files",
        description="Execute full processing pipeline: connect to IMAP, fetch emails/attachments, process and store results, send files via SMTP.",
    )
    _add_global_options(run_parser)
    run_parser.add_argument(
        "--since",
        type=str,
        help="Process emails since duration (e.g., '7d', '24h')",
    )
    run_parser.add_argument(
        "--folder",
        type=str,
        help="IMAP folder to process (default: INBOX)",
    )
    run_parser.add_argument(
        "--max-emails",
        type=int,
        help="Limit number of processed emails",
    )
    run_parser.add_argument(
        "--dry-run-no-connect",
        action="store_true",
        help="Dry-run mode with mock IMAP server (no real connection)",
    )

    # Command: fetch (fetch only)
    fetch_parser = subparsers.add_parser(
        "fetch",
        help="Fetch emails and attachments only (no sending)",
        description="Connect to IMAP, fetch emails/attachments, store files locally. Does not send anything.",
    )
    _add_global_options(fetch_parser)
    fetch_parser.add_argument(
        "--since",
        type=str,
        help="Process emails since duration (e.g., '7d', '24h')",
    )
    fetch_parser.add_argument(
        "--folder",
        type=str,
        help="IMAP folder to process (default: INBOX)",
    )
    fetch_parser.add_argument(
        "--max-emails",
        type=int,
        help="Limit number of processed emails",
    )
    fetch_parser.add_argument(
        "--dry-run-no-connect",
        action="store_true",
        help="Dry-run mode with mock IMAP server (no real connection)",
    )

    # Command: send (with subcommands)
    send_parser = subparsers.add_parser(
        "send",
        help="Send files via SMTP",
        description="Send files via email using SMTP.",
    )
    send_subparsers = send_parser.add_subparsers(
        dest="send_command", help="Send subcommands", metavar="SUBCOMMAND"
    )

    # Subcommand: send file
    send_file_parser = send_subparsers.add_parser(
        "file",
        help="Send a single file",
        description="Send a single file via email.",
    )
    _add_global_options(send_file_parser)
    send_file_parser.add_argument(
        "path",
        type=str,
        help="Path to file to send",
    )
    send_file_parser.add_argument(
        "--to",
        type=str,
        required=True,
        help="Recipient email address",
    )
    send_file_parser.add_argument(
        "--subject",
        type=str,
        help="Email subject (overrides default)",
    )
    send_file_parser.add_argument(
        "--cc",
        type=str,
        help="CC email address",
    )
    send_file_parser.add_argument(
        "--bcc",
        type=str,
        help="BCC email address",
    )
    send_file_parser.add_argument(
        "--max-size-mb",
        type=float,
        help="Maximum email size in MB (overrides config)",
    )
    send_file_parser.add_argument(
        "--template",
        type=str,
        help="Subject template name",
    )

    # Subcommand: send folder
    send_folder_parser = send_subparsers.add_parser(
        "folder",
        help="Send all files from a folder",
        description="Send all files from a folder via email.",
    )
    _add_global_options(send_folder_parser)
    send_folder_parser.add_argument(
        "dir",
        type=str,
        nargs="?",
        default=None,
        help="Directory path (default: smtp.send_folder from config)",
    )
    send_folder_parser.add_argument(
        "--to",
        type=str,
        default=None,
        help="Recipient email (default: smtp.default_recipient from config)",
    )
    send_folder_parser.add_argument(
        "--subject",
        type=str,
        help="Email subject (overrides default)",
    )
    send_folder_parser.add_argument(
        "--cc",
        type=str,
        help="CC email address",
    )
    send_folder_parser.add_argument(
        "--bcc",
        type=str,
        help="BCC email address",
    )
    send_folder_parser.add_argument(
        "--max-size-mb",
        type=float,
        help="Maximum email size in MB (overrides config)",
    )
    send_folder_parser.add_argument(
        "--template",
        type=str,
        help="Subject template name",
    )

    # Command: password (with subcommands)
    password_parser = subparsers.add_parser(
        "password",
        help="Manage IMAP password storage",
        description="Manage password storage for IMAP authentication.",
    )
    password_subparsers = password_parser.add_subparsers(
        dest="password_command", help="Password subcommands", metavar="SUBCOMMAND"
    )

    # Subcommand: password set
    password_set_parser = password_subparsers.add_parser(
        "set",
        help="Store password for IMAP user",
        description="Store password for IMAP user in keyring.",
    )
    _add_global_options(password_set_parser)
    password_set_parser.add_argument(
        "--user",
        type=str,
        default=None,
        help="IMAP user login (default: imap.user from config)",
    )
    password_set_parser.add_argument(
        "--password-file",
        type=str,
        help="Path to file containing password (if not provided, will prompt)",
    )
    password_set_parser.add_argument(
        "--delete-after-read",
        action="store_true",
        help="Delete password file after successful read",
    )

    # Subcommand: password clear
    password_clear_parser = password_subparsers.add_parser(
        "clear",
        help="Clear stored password for IMAP user",
        description="Clear stored password for IMAP user from keyring.",
    )
    _add_global_options(password_clear_parser)
    password_clear_parser.add_argument(
        "--user",
        type=str,
        default=None,
        help="IMAP user login (default: imap.user from config)",
    )

    # Command: config (with subcommands)
    config_parser = subparsers.add_parser(
        "config",
        help="Configuration management",
        description="Manage configuration files.",
    )
    config_subparsers = config_parser.add_subparsers(
        dest="config_command", help="Config subcommands", metavar="SUBCOMMAND"
    )

    # Subcommand: config init
    config_init_parser = config_subparsers.add_parser(
        "init",
        help="Create example configuration file",
        description="Create an example configuration file from template.",
    )
    _add_global_options(config_init_parser)
    config_init_parser.add_argument(
        "--path",
        type=str,
        help="Path for configuration file (default: config.yaml)",
    )

    # Subcommand: config validate
    config_validate_parser = config_subparsers.add_parser(
        "validate",
        help="Validate configuration file",
        description="Validate configuration file structure and required fields.",
    )
    _add_global_options(config_validate_parser)

    # Command: status
    status_parser = subparsers.add_parser(
        "status",
        help="Print diagnostics and environment status",
        description="Print diagnostics including version, config path, storage directories, keyring availability, and fingerprint summary.",
    )
    _add_global_options(status_parser)

    args = parser.parse_args()

    # Validate mutually exclusive options
    if args.verbose and args.quiet:
        parser.error("--verbose and --quiet cannot be used together")

    return args
