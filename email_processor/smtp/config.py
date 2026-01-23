"""SMTP configuration dataclass."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SMTPConfig:
    """SMTP configuration parameters."""

    smtp_server: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    from_address: str
    use_tls: bool = True
    use_ssl: bool = False
    max_retries: int = 5
    retry_delay: int = 3
    max_email_size_mb: float = 25.0
    subject_template: Optional[str] = None
    subject_template_package: Optional[str] = None
