"""Redaction helpers for avoiding clear-text logging of sensitive data (CodeQL)."""

from typing import Optional


def redact_email(email: Optional[str]) -> str:
    """Redact email for safe logging (e.g. 'user@example.com' -> 'u***@***').

    Use in log calls to satisfy py/clear-text-logging-sensitive-data.
    """
    if not email or not isinstance(email, str):
        return ""
    s = email.strip()
    if "@" not in s:
        return "***" if s else ""
    local, _, domain = s.partition("@")
    if not local:
        return "***@" + ("***" if domain else "")
    return f"{local[0]}***@***"
