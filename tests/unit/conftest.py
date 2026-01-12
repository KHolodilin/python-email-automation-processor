"""Pytest configuration for unit tests."""

import logging


def pytest_configure(config):
    """Configure pytest for unit tests."""
    # Reset logging before tests
    for handler in logging.root.handlers[:]:
        try:
            handler.close()
        except Exception:
            pass
        logging.root.removeHandler(handler)
    logging.shutdown()
