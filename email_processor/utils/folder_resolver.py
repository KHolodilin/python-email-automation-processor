"""Folder resolver with cached regex patterns."""

import re
from functools import lru_cache

from email_processor.logging.setup import get_logger


@lru_cache(maxsize=128)
def _compile_pattern(pattern: str) -> re.Pattern:
    """Compile regex pattern with caching for better performance."""
    return re.compile(pattern, re.IGNORECASE)


def resolve_custom_folder(subject: str, topic_mapping: dict[str, str]) -> str:
    """
    Resolve custom folder based on subject and topic mapping with cached regex patterns.
    If no pattern matches, returns the last folder from topic_mapping as default.

    Args:
        subject: Email subject to match against patterns
        topic_mapping: Dictionary mapping regex patterns to folder paths

    Returns:
        Folder path (always returns a value - last one if no match)
    """
    logger = get_logger()
    items_list = list(topic_mapping.items())

    if not items_list:
        raise ValueError("topic_mapping must contain at least one rule")

    # Get the last folder as default (will be used if no pattern matches)
    default_folder = items_list[-1][1]

    # Check all patterns except the last one
    for pattern, folder in items_list[:-1]:
        compiled = _compile_pattern(pattern)
        if compiled.search(subject):
            logger.info("subject_matched", subject=subject, pattern=pattern, folder=folder)
            return folder

    # No pattern matched, use the last folder as default
    logger.debug("subject_no_match_using_default", subject=subject, folder=default_folder)
    return default_folder


class FolderResolver:
    """Folder resolver class with cached regex patterns."""

    def __init__(self, topic_mapping: dict[str, str]):
        """
        Initialize folder resolver.

        Args:
            topic_mapping: Dictionary mapping regex patterns to folder names
        """
        self.topic_mapping = topic_mapping

    def resolve(self, subject: str) -> str:
        """Resolve custom folder based on subject."""
        return resolve_custom_folder(subject, self.topic_mapping)

    def _compile_pattern(self, pattern: str) -> re.Pattern:
        """Compile regex pattern with caching."""
        return _compile_pattern(pattern)
