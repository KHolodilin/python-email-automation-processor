"""IMAP email processing commands."""

import logging
from typing import Optional

from email_processor import EmailProcessor
from email_processor.cli.ui import CLIUI
from email_processor.exit_codes import ExitCode
from email_processor.imap.fetcher import ProcessingResult


def run_processor(
    cfg: dict, dry_run: bool, mock_mode: bool, config_path: Optional[str], ui: CLIUI
) -> int:
    """Handle normal email processing command.

    Args:
        cfg: Configuration dictionary
        dry_run: If True, simulate processing without downloading or archiving
        mock_mode: If True, use mock IMAP server
        config_path: Path to configuration file
        ui: CLIUI instance for output

    Returns:
        int: 0 on success, 1 on error
    """
    try:
        processor = EmailProcessor(cfg)
        result = processor.process(dry_run=dry_run, mock_mode=mock_mode, config_path=config_path)

        # Display results
        _display_results(result, ui)
        return ExitCode.SUCCESS
    except KeyboardInterrupt:
        logging.info("Interrupted by user")
        return ExitCode.SUCCESS
    except Exception:
        logging.exception("Fatal error during email processing")
        return ExitCode.PROCESSING_ERROR


def _display_results(result: ProcessingResult, ui: CLIUI) -> None:
    """Display processing results.

    Args:
        result: ProcessingResult instance
        ui: CLIUI instance for output
    """
    if ui.has_rich and ui.console:
        _display_results_rich(result, ui.console)
    else:
        ui.info(
            f"Processed: {result.processed}, Skipped: {result.skipped}, "
            f"Blocked: {result.blocked}, Errors: {result.errors}"
        )


def _display_results_rich(result: ProcessingResult, console) -> None:
    """Display processing results with rich formatting."""
    try:
        from rich.table import Table
    except ImportError:
        # Fallback if rich is not available
        return

    # Create results table
    table = Table(title="Processing Results", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")

    table.add_row("Processed", str(result.processed))
    table.add_row("Skipped", str(result.skipped))
    table.add_row("Blocked", str(result.blocked))
    table.add_row(
        "Errors", str(result.errors) if result.errors == 0 else f"[red]{result.errors}[/red]"
    )

    # Add file stats if available
    if result.file_stats:
        table.add_row("", "")
        table.add_row("[bold]File Statistics[/bold]", "")
        for ext, count in list(result.file_stats.items())[:10]:  # Show top 10
            table.add_row(f"  {ext}", str(count))

    console.print(table)

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

        console.print(metrics_table)
