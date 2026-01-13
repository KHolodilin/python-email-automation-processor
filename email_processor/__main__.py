"""Main entry point for email_processor package."""

import argparse
import logging
import shutil
import sys
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from email_processor import (
    CONFIG_FILE,
    KEYRING_SERVICE_NAME,
    ConfigLoader,
    EmailProcessor,
    __version__,
    clear_passwords,
)

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

    if args.clear_passwords:
        user = cfg.get("imap", {}).get("user")
        if not user:
            if console:
                console.print("[red]Error:[/red] 'imap.user' is missing in config.yaml")
            else:
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
        and result.metrics.total_time > 0
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


if __name__ == "__main__":
    sys.exit(main())
