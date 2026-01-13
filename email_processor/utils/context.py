"""Context management for request ID and correlation ID."""

import contextvars
import uuid
from typing import Optional

# Context variables for request tracking
_request_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=None
)
_correlation_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)


def generate_request_id() -> str:
    """Generate a unique request ID."""
    return str(uuid.uuid4())


def generate_correlation_id() -> str:
    """Generate a unique correlation ID."""
    return str(uuid.uuid4())


def set_request_id(request_id: Optional[str] = None) -> str:
    """
    Set request ID in context.

    Args:
        request_id: Optional request ID. If None, generates a new one.

    Returns:
        The request ID that was set
    """
    if request_id is None:
        request_id = generate_request_id()
    _request_id.set(request_id)
    return request_id


def get_request_id() -> Optional[str]:
    """Get current request ID from context."""
    return _request_id.get()


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """
    Set correlation ID in context.

    Args:
        correlation_id: Optional correlation ID. If None, generates a new one.

    Returns:
        The correlation ID that was set
    """
    if correlation_id is None:
        correlation_id = generate_correlation_id()
    _correlation_id.set(correlation_id)
    return correlation_id


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context."""
    return _correlation_id.get()


def clear_context() -> None:
    """Clear all context variables."""
    _request_id.set(None)
    _correlation_id.set(None)


def get_context_dict() -> dict:
    """
    Get dictionary with all context IDs.

    Returns:
        Dictionary with request_id and correlation_id (if set)
    """
    ctx = {}
    request_id = get_request_id()
    if request_id:
        ctx["request_id"] = request_id
    correlation_id = get_correlation_id()
    if correlation_id:
        ctx["correlation_id"] = correlation_id
    return ctx
