"""Email filtering by senders and topics."""

from email_processor.utils.folder_resolver import resolve_custom_folder


class EmailFilter:
    """Email filter class for sender and topic filtering."""

    def __init__(self, allowed_senders: list[str], topic_mapping: dict[str, str]):
        """
        Initialize email filter.

        Args:
            allowed_senders: List of allowed sender email addresses
            topic_mapping: Dictionary mapping regex patterns to folder names
        """
        self.allowed_senders = allowed_senders
        self.allowed_lower = {s.lower() for s in allowed_senders}
        self.topic_mapping = topic_mapping

    def is_allowed_sender(self, sender: str) -> bool:
        """Check if sender is allowed."""
        return sender.lower() in self.allowed_lower

    def resolve_folder(self, subject: str) -> str:
        """Resolve folder based on subject and topic mapping."""
        return resolve_custom_folder(subject, self.topic_mapping)
