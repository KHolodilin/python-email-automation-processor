"""Exit codes for CLI commands.

This module defines standardized exit codes used throughout the application
to provide clear error reporting and better integration with scripts and automation tools.

See also: README § Exit Codes for the full table, usage examples (bash, Python),
and common scenarios.
"""

from enum import IntEnum


class ExitCode(IntEnum):
    """Standardized exit codes for CLI commands.

    These codes follow common Unix conventions and provide clear error reporting
    for different types of failures, enabling proper error handling in automated workflows.
    """

    SUCCESS = 0
    """Success - operation completed successfully."""

    PROCESSING_ERROR = 1
    """Processing error - errors during extraction, parsing, mapping, or write operations."""

    VALIDATION_FAILED = 2
    """Validation failed - input validation errors (e.g., invalid arguments, strict mode failures)."""

    FILE_NOT_FOUND = 3
    """File not found - requested file or directory does not exist."""

    UNSUPPORTED_FORMAT = 4
    """Unsupported format - cannot detect or process the requested format."""

    WARNINGS_AS_ERRORS = 5
    """Warnings as errors - warnings were treated as errors (e.g., --fail-on-warnings enabled)."""

    CONFIG_ERROR = 6
    """Configuration error - errors loading or validating configuration file."""

    def __int__(self) -> int:
        """Return integer value of the exit code."""
        return self.value
