"""Main entry point for email_processor package."""

import argparse
import logging
import shutil
import stat
import sys
from datetime import datetime
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

import keyring

from email_processor import (
    CONFIG_FILE,
    KEYRING_SERVICE_NAME,
    ConfigLoader,
    EmailProcessor,
    __version__,
    clear_passwords,
)
from email_processor.imap.auth import get_imap_password
from email_processor.logging.setup import get_logger, setup_logging
from email_processor.smtp.sender import EmailSender
from email_processor.storage.sent_files_storage import SentFilesStorage

CONFIG_EXAMPLE = "config.yaml.example"

# Initialize rich console if available
console = Console() if RICH_AVAILABLE else None


def create_default_config(config_path: str) -> int:
    """Create default configuration file from config.yaml.example."""
    example_path = Path(CONFIG_EXAMPLE)
    target_path = Path(config_path)

    if not example_path.exists():
        if console:
            console.print(f"[red]Error:[/red] Template file {CONFIG_EXAMPLE} not found")
            console.print(f"Expected location: {example_path.absolute()}")
        else:
            print(f"Error: Template file {CONFIG_EXAMPLE} not found")
            print(f"Expected location: {example_path.absolute()}")
        return 1

    if target_path.exists():
        response = input(f"Configuration file {config_path} already exists. Overwrite? [y/N]: ")
        if response.lower() != "y":
            if console:
                console.print("[yellow]Cancelled.[/yellow]")
            else:
                print("Cancelled.")
            return 0

    try:
        # Create parent directories if needed
        target_path.parent.mkdir(parents=True, exist_ok=True)
        # Copy the example file
        shutil.copy2(example_path, target_path)
        if console:
            console.print(
                f"[green]✓[/green] Created configuration file: [cyan]{target_path.absolute()}[/cyan]"
            )
            console.print(f"Please edit [cyan]{config_path}[/cyan] with your IMAP settings.")
        else:
            print(f"Created configuration file: {target_path.absolute()}")
            print(f"Please edit {config_path} with your IMAP settings.")
        return 0
    except OSError as e:
        if console:
            console.print(f"[red]Error creating configuration file:[/red] {e}")
        else:
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
        "--set-password",
        action="store_true",
        help="Set password for IMAP user from password file",
    )
    parser.add_argument(
        "--password-file",
        type=str,
        help="Path to file containing password (required with --set-password)",
    )
    parser.add_argument(
        "--remove-password-file",
        action="store_true",
        help="Remove password file after reading (use with --password-file)",
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
    parser.add_argument(
        "--send-file",
        type=str,
        help="Send a single file via email",
    )
    parser.add_argument(
        "--send-folder",
        type=str,
        nargs="?",
        const="",  # Use empty string to detect flag presence
        help="Send all new files from specified folder via email (or use smtp.send_folder from config if not specified)",
    )
    parser.add_argument(
        "--recipient",
        type=str,
        help="Override default recipient email address from config",
    )
    parser.add_argument(
        "--subject",
        type=str,
        help="Override email subject (default: filename or template from config)",
    )
    parser.add_argument(
        "--dry-run-send",
        action="store_true",
        help="Dry-run mode for sending emails (test without actually sending)",
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
        if console:
            console.print(f"[red]Error:[/red] {e}")
            console.print(f"Please create [cyan]{config_path}[/cyan] based on config.yaml.example")
        else:
            print(f"Error: {e}")
            print(f"Please create {config_path} based on config.yaml.example")
        return 1
    except ValueError as e:
        if console:
            console.print(f"[red]Configuration error:[/red] {e}")
        else:
            print(f"Configuration error: {e}")
        return 1
    except Exception as e:
        if console:
            console.print(f"[red]Unexpected error loading configuration:[/red] {e}")
        else:
            print(f"Unexpected error loading configuration: {e}")
        return 1

    # Setup basic logging early for warnings (before EmailProcessor initializes it)
    # Use config if available, otherwise use defaults
    log_config = cfg.get("logging", {})
    if not log_config:
        # Fallback to old format for backward compatibility
        proc_cfg = cfg.get("processing", {})
        log_config = {
            "level": proc_cfg.get("log_level", "INFO"),
            "format": "console",
        }
    setup_logging(log_config)

    # Log warning if SMTP section is missing (for backward compatibility)
    # Only warn if SMTP commands are not being used
    if "smtp" not in cfg and not (args.send_file or args.send_folder is not None):
        logger = get_logger()
        logger.warning(
            "smtp_section_missing",
            message="SMTP section is missing in config.yaml. SMTP functionality will be skipped. "
            "Add 'smtp' section to enable email sending features.",
        )

    if args.clear_passwords:
        user = cfg.get("imap", {}).get("user")
        if not user:
            if console:
                console.print("[red]Error:[/red] 'imap.user' is missing in config.yaml")
            else:
                print("Error: 'imap.user' is missing in config.yaml")
            return 1
        clear_passwords(KEYRING_SERVICE_NAME, user)
    elif args.set_password:
        # Set password from file
        user = cfg.get("imap", {}).get("user")
        if not user:
            if console:
                console.print("[red]Error:[/red] 'imap.user' is missing in config.yaml")
            else:
                print("Error: 'imap.user' is missing in config.yaml")
            return 1

        if not args.password_file:
            if console:
                console.print("[red]Error:[/red] --password-file is required with --set-password")
            else:
                print("Error: --password-file is required with --set-password")
            return 1

        # Read password from file
        password_file = Path(args.password_file)
        if not password_file.exists():
            if console:
                console.print(f"[red]Error:[/red] Password file not found: {password_file}")
            else:
                print(f"Error: Password file not found: {password_file}")
            return 1

        # Check file permissions (Unix only)
        if sys.platform != "win32":
            try:
                file_stat = password_file.stat()
                file_mode = stat.filemode(file_stat.st_mode)
                # Check if file is readable by others (group or world)
                if file_stat.st_mode & (stat.S_IRGRP | stat.S_IROTH):
                    if console:
                        console.print(
                            f"[yellow]Warning:[/yellow] Password file has open permissions: {file_mode}. "
                            "Consider using chmod 600 for security."
                        )
                    else:
                        print(
                            f"Warning: Password file has open permissions: {file_mode}. "
                            "Consider using chmod 600 for security."
                        )
            except Exception:
                pass  # Ignore permission check errors

        try:
            # Read password from file (first line, strip whitespace)
            with open(password_file, encoding="utf-8") as f:
                password = f.readline().strip()
        except PermissionError:
            if console:
                console.print(
                    f"[red]Error:[/red] Permission denied reading password file: {password_file}"
                )
            else:
                print(f"Error: Permission denied reading password file: {password_file}")
            return 1
        except Exception as e:
            if console:
                console.print(f"[red]Error:[/red] Failed to read password file: {e}")
            else:
                print(f"Error: Failed to read password file: {e}")
            return 1

        if not password:
            if console:
                console.print("[red]Error:[/red] Password file is empty")
            else:
                print("Error: Password file is empty")
            return 1

        # Save password to keyring
        try:
            from email_processor.security.encryption import encrypt_password

            encrypted_password = encrypt_password(password, config_path)
            keyring.set_password(KEYRING_SERVICE_NAME, user, encrypted_password)
            if console:
                console.print(f"[green]✓[/green] Password saved for {user}")
            else:
                print(f"Password saved for {user}")
        except Exception as e:
            # Try saving unencrypted as fallback
            try:
                keyring.set_password(KEYRING_SERVICE_NAME, user, password)
                if console:
                    console.print(
                        f"[yellow]Warning:[/yellow] Password saved unencrypted (encryption failed: {e})"
                    )
                    console.print(f"[green]✓[/green] Password saved for {user}")
                else:
                    print(f"Warning: Password saved unencrypted (encryption failed: {e})")
                    print(f"Password saved for {user}")
            except Exception as e2:
                if console:
                    console.print(f"[red]Error:[/red] Failed to save password: {e2}")
                else:
                    print(f"Error: Failed to save password: {e2}")
                return 1

        # Remove password file if requested
        if args.remove_password_file:
            try:
                password_file.unlink()
                if console:
                    console.print(f"[green]✓[/green] Password file removed: {password_file}")
                else:
                    print(f"Password file removed: {password_file}")
            except Exception as e:
                if console:
                    console.print(f"[yellow]Warning:[/yellow] Failed to remove password file: {e}")
                else:
                    print(f"Warning: Failed to remove password file: {e}")
                # Don't fail the command if file removal fails

        return 0
    elif args.send_file or args.send_folder is not None:
        # Handle SMTP sending commands
        return _handle_smtp_send(cfg, args, console, config_path)
    else:
        try:
            processor = EmailProcessor(cfg)
            # If --dry-run-no-connect is set, enable both dry_run and mock_mode
            dry_run = args.dry_run or args.dry_run_no_connect
            mock_mode = args.dry_run_no_connect
            result = processor.process(dry_run=dry_run, mock_mode=mock_mode)

            # Display results with rich if available
            if console:
                _display_results_rich(result, console)
            else:
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


def _display_results_rich(result, console_instance: "Console") -> None:
    """Display processing results with rich formatting."""
    # Create results table
    table = Table(title="Processing Results", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")

    table.add_row("Processed", str(result.processed))
    table.add_row("Skipped", str(result.skipped))
    table.add_row(
        "Errors", str(result.errors) if result.errors == 0 else f"[red]{result.errors}[/red]"
    )

    # Add file stats if available
    if result.file_stats:
        table.add_row("", "")
        table.add_row("[bold]File Statistics[/bold]", "")
        for ext, count in list(result.file_stats.items())[:10]:  # Show top 10
            table.add_row(f"  {ext}", str(count))

    console_instance.print(table)

    # Display performance metrics
    # Safely check if metrics exists and is a real ProcessingMetrics object
    if (
        result.metrics
        and hasattr(result.metrics, "total_time")
        and isinstance(result.metrics.total_time, (int, float))
    ):
        metrics_table = Table(
            title="Performance Metrics", show_header=True, header_style="bold blue"
        )
        metrics_table.add_column("Metric", style="cyan", no_wrap=True)
        metrics_table.add_column("Value", style="yellow")

        # Format time
        total_time = result.metrics.total_time
        if total_time < 1:
            time_str = f"{total_time * 1000:.2f} ms"
        elif total_time < 60:
            time_str = f"{total_time:.2f} s"
        else:
            minutes = int(total_time // 60)
            seconds = total_time % 60
            time_str = f"{minutes}m {seconds:.2f}s"

        metrics_table.add_row("Total Time", time_str)

        # Average time per email
        if (
            hasattr(result.metrics, "per_email_time")
            and result.metrics.per_email_time
            and isinstance(result.metrics.per_email_time, list)
        ):
            avg_time = sum(result.metrics.per_email_time) / len(result.metrics.per_email_time)
            avg_time_str = f"{avg_time * 1000:.2f} ms" if avg_time < 1 else f"{avg_time:.2f} s"
            metrics_table.add_row("Avg Time/Email", avg_time_str)

        # IMAP operations
        if (
            hasattr(result.metrics, "imap_operations")
            and isinstance(result.metrics.imap_operations, int)
            and result.metrics.imap_operations > 0
        ):
            metrics_table.add_row("IMAP Operations", str(result.metrics.imap_operations))
            if (
                hasattr(result.metrics, "imap_operation_times")
                and result.metrics.imap_operation_times
                and isinstance(result.metrics.imap_operation_times, list)
            ):
                avg_imap = sum(result.metrics.imap_operation_times) / len(
                    result.metrics.imap_operation_times
                )
                avg_imap_str = f"{avg_imap * 1000:.2f} ms" if avg_imap < 1 else f"{avg_imap:.2f} s"
                metrics_table.add_row("Avg IMAP Time", avg_imap_str)

        # Downloaded size
        if result.metrics.total_downloaded_size > 0:
            size_mb = result.metrics.total_downloaded_size / (1024 * 1024)
            if size_mb < 1:
                size_str = f"{result.metrics.total_downloaded_size / 1024:.2f} KB"
            else:
                size_str = f"{size_mb:.2f} MB"
            metrics_table.add_row("Downloaded Size", size_str)

        # Memory usage
        if (
            hasattr(result.metrics, "memory_current")
            and result.metrics.memory_current is not None
            and isinstance(result.metrics.memory_current, int)
        ):
            mem_mb = result.metrics.memory_current / (1024 * 1024)
            metrics_table.add_row("Memory Usage", f"{mem_mb:.2f} MB")
            if result.metrics.memory_peak:
                peak_mb = result.metrics.memory_peak / (1024 * 1024)
                metrics_table.add_row("Peak Memory", f"{peak_mb:.2f} MB")

        console_instance.print(metrics_table)


def _handle_smtp_send(
    cfg: dict, args: argparse.Namespace, console: "Console | None", config_path: str
) -> int:
    """Handle SMTP sending commands."""
    # Check SMTP config
    smtp_cfg = cfg.get("smtp")
    if not smtp_cfg:
        if console:
            console.print("[red]Error:[/red] 'smtp' section is missing in config.yaml")
        else:
            print("Error: 'smtp' section is missing in config.yaml")
        return 1

    # Get SMTP settings
    smtp_server = smtp_cfg.get("server")
    smtp_port = int(smtp_cfg.get("port", 587))
    smtp_user = smtp_cfg.get("user") or cfg.get("imap", {}).get("user")
    from_address = smtp_cfg.get("from_address")
    use_tls = smtp_cfg.get("use_tls", True)
    use_ssl = smtp_cfg.get("use_ssl", False)
    max_email_size_mb = float(smtp_cfg.get("max_email_size", 25))
    sent_files_dir = smtp_cfg.get("sent_files_dir", "sent_files")
    subject_template = smtp_cfg.get("subject_template")
    subject_template_package = smtp_cfg.get("subject_template_package")

    if not smtp_server:
        if console:
            console.print("[red]Error:[/red] 'smtp.server' is required in config.yaml")
        else:
            print("Error: 'smtp.server' is required in config.yaml")
        return 1

    if not smtp_user:
        if console:
            console.print("[red]Error:[/red] 'smtp.user' or 'imap.user' is required in config.yaml")
        else:
            print("Error: 'smtp.user' or 'imap.user' is required in config.yaml")
        return 1

    if not from_address:
        if console:
            console.print("[red]Error:[/red] 'smtp.from_address' is required in config.yaml")
        else:
            print("Error: 'smtp.from_address' is required in config.yaml")
        return 1

    # Get recipient
    recipient = args.recipient or smtp_cfg.get("default_recipient")
    if not recipient:
        if console:
            console.print(
                "[red]Error:[/red] Recipient not specified. Use --recipient or set smtp.default_recipient in config.yaml"
            )
        else:
            print(
                "Error: Recipient not specified. Use --recipient or set smtp.default_recipient in config.yaml"
            )
        return 1

    # Get password
    try:
        password = get_imap_password(smtp_user, config_path)
    except Exception as e:
        if console:
            console.print(f"[red]Error getting password:[/red] {e}")
        else:
            print(f"Error getting password: {e}")
        return 1

    # Initialize sender and storage
    sender = EmailSender(
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_password=password,
        from_address=from_address,
        use_tls=use_tls,
        use_ssl=use_ssl,
        max_email_size_mb=max_email_size_mb,
        subject_template=subject_template,
        subject_template_package=subject_template_package,
    )
    storage = SentFilesStorage(sent_files_dir)
    day_str = datetime.now().strftime("%Y-%m-%d")

    dry_run = args.dry_run_send

    if args.send_file:
        # Send single file
        file_path = Path(args.send_file)
        if not file_path.exists():
            if console:
                console.print(f"[red]Error:[/red] File not found: {file_path}")
            else:
                print(f"Error: File not found: {file_path}")
            return 1

        if not file_path.is_file():
            if console:
                console.print(f"[red]Error:[/red] Not a file: {file_path}")
            else:
                print(f"Error: Not a file: {file_path}")
            return 1

        # Check if already sent
        if not dry_run and storage.is_sent(file_path, day_str):
            if console:
                console.print(f"[yellow]Warning:[/yellow] File already sent: {file_path.name}")
            else:
                print(f"Warning: File already sent: {file_path.name}")
            return 0

        # Send file
        success = sender.send_file(file_path, recipient, args.subject, dry_run=dry_run)

        if success and not dry_run:
            storage.mark_as_sent(file_path, day_str)
            if console:
                console.print(f"[green]✓[/green] File sent: {file_path.name}")
            else:
                print(f"File sent: {file_path.name}")
        elif success and dry_run:
            if console:
                console.print(f"[cyan]DRY-RUN:[/cyan] Would send file: {file_path.name}")
            else:
                print(f"DRY-RUN: Would send file: {file_path.name}")
        else:
            if console:
                console.print(f"[red]Error:[/red] Failed to send file: {file_path.name}")
            else:
                print(f"Error: Failed to send file: {file_path.name}")
            return 1

        return 0

    elif args.send_folder is not None or smtp_cfg.get("send_folder"):
        # Send files from folder
        # Use argument if provided (and not empty), otherwise use config value
        # If --send-folder specified without argument, args.send_folder will be empty string
        # Use config value in that case, otherwise use provided argument
        folder_path_str = (
            args.send_folder
            if (args.send_folder and args.send_folder != "")
            else smtp_cfg.get("send_folder")
        )
        if not folder_path_str:
            if console:
                console.print(
                    "[red]Error:[/red] Folder not specified. Use --send-folder <path> or set smtp.send_folder in config.yaml"
                )
            else:
                print(
                    "Error: Folder not specified. Use --send-folder <path> or set smtp.send_folder in config.yaml"
                )
            return 1
        folder_path = Path(folder_path_str)
        if not folder_path.exists():
            if console:
                console.print(f"[red]Error:[/red] Folder not found: {folder_path}")
            else:
                print(f"Error: Folder not found: {folder_path}")
            return 1

        if not folder_path.is_dir():
            if console:
                console.print(f"[red]Error:[/red] Not a folder: {folder_path}")
            else:
                print(f"Error: Not a folder: {folder_path}")
            return 1

        # Find new files
        all_files = [f for f in folder_path.iterdir() if f.is_file()]
        new_files = []
        skipped_count = 0

        for file_path in all_files:
            if not dry_run and storage.is_sent(file_path, day_str):
                skipped_count += 1
            else:
                new_files.append(file_path)

        if not new_files:
            if console:
                console.print(
                    f"[yellow]No new files to send[/yellow] (skipped {skipped_count} already sent)"
                )
            else:
                print(f"No new files to send (skipped {skipped_count} already sent)")
            return 0

        # Send files
        sent_count = 0
        failed_count = 0

        for file_path in new_files:
            success = sender.send_file(file_path, recipient, args.subject, dry_run=dry_run)
            if success:
                if not dry_run:
                    storage.mark_as_sent(file_path, day_str)
                sent_count += 1
            else:
                failed_count += 1

        # Display results
        if console:
            console.print(f"[green]Sent:[/green] {sent_count} files")
            if skipped_count > 0:
                console.print(f"[yellow]Skipped:[/yellow] {skipped_count} files (already sent)")
            if failed_count > 0:
                console.print(f"[red]Failed:[/red] {failed_count} files")
        else:
            print(f"Sent: {sent_count} files")
            if skipped_count > 0:
                print(f"Skipped: {skipped_count} files (already sent)")
            if failed_count > 0:
                print(f"Failed: {failed_count} files")

        return 0 if failed_count == 0 else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
