"""Folder resolver with cached regex patterns."""

import re
from functools import lru_cache
from typing import Optional

from email_processor.logging.setup import get_logger


@lru_cache(maxsize=128)
def _compile_pattern(pattern: str) -> re.Pattern:
    """Compile regex pattern with caching for better performance."""
    return re.compile(pattern, re.IGNORECASE)


def resolve_custom_folder(subject: str, topic_mapping: dict[str, str]) -> Optional[str]:
    """Resolve custom folder based on subject and topic mapping with cached regex patterns."""
    logger = get_logger()
    for pattern, folder in topic_mapping.items():
        compiled = _compile_pattern(pattern)
        if compiled.search(subject):
            logger.info("subject_matched", subject=subject, pattern=pattern, folder=folder)
            return folder
    return None


class FolderResolver:
    """Folder resolver class with cached regex patterns."""

    def __init__(self, topic_mapping: dict[str, str]):
        """
        Initialize folder resolver.

        Args:
            topic_mapping: Dictionary mapping regex patterns to folder names
        """
        self.topic_mapping = topic_mapping

    def resolve(self, subject: str) -> Optional[str]:
        """Resolve custom folder based on subject."""
        return resolve_custom_folder(subject, self.topic_mapping)

    def _compile_pattern(self, pattern: str) -> re.Pattern:
        """Compile regex pattern with caching."""
        return _compile_pattern(pattern)
