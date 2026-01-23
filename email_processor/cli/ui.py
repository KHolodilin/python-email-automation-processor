"""CLI UI helpers for console output."""

from typing import Optional

try:
    from rich.console import Console

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class CLIUI:
    """Unified CLI UI interface for console output."""

    def __init__(self, verbose: bool = False, quiet: bool = False):
        """Initialize CLI UI.

        Args:
            verbose: Enable verbose output
            quiet: Suppress non-error output
        """
        self._console = Console() if RICH_AVAILABLE else None
        self._verbose = verbose
        self._quiet = quiet

    def error(self, msg: str) -> None:
        """Print error message."""
        if self._console:
            self._console.print(f"[red]Error:[/red] {msg}")
        else:
            print(f"Error: {msg}")

    def warn(self, msg: str) -> None:
        """Print warning message."""
        if self._console:
            self._console.print(f"[yellow]Warning:[/yellow] {msg}")
        else:
            print(f"Warning: {msg}")

    def info(self, msg: str) -> None:
        """Print info message."""
        if self._quiet:
            return
        if self._console:
            self._console.print(msg)
        else:
            print(msg)

    def success(self, msg: str) -> None:
        """Print success message."""
        if self._quiet:
            return
        if self._console:
            self._console.print(f"[green]✓[/green] {msg}")
        else:
            print(msg)

    def print(self, msg: str, style: Optional[str] = None) -> None:
        """Print message with optional style."""
        if self._quiet:
            return
        if self._console:
            if style:
                self._console.print(f"[{style}]{msg}[/{style}]")
            else:
                self._console.print(msg)
        else:
            print(msg)

    def input(self, prompt: str) -> str:
        """Get user input."""
        return input(prompt)

    @property
    def has_rich(self) -> bool:
        """Check if rich console is available."""
        return RICH_AVAILABLE

    @property
    def console(self):
        """Get rich console instance (if available)."""
        return self._console
