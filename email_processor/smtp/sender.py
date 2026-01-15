"""SMTP email sender with file attachments."""

import email.encoders
import email.utils
from datetime import datetime
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from email_processor.logging.setup import get_logger


def format_subject_template(template: str, context: dict[str, str]) -> str:
    """Format subject template with context variables.

    Args:
        template: Template string with {variable} placeholders
        context: Dictionary with variable values

    Returns:
        Formatted subject string
    """
    import re

    # Extract all variable names from template
    template_vars = set(re.findall(r"\{(\w+)\}", template))
    # Build context with all template variables, using empty string for missing ones
    full_context = {}
    for var in template_vars:
        full_context[var] = context.get(var, "")

    try:
        return template.format(**full_context)
    except KeyError as e:
        logger = get_logger()
        logger.warning("template_variable_missing", variable=str(e), template=template)
        # If still fails, return template with variables replaced manually
        result = template
        for var in template_vars:
            value = full_context.get(var, "")
            result = result.replace(f"{{{var}}}", value)
        return result


def create_email_subject(files: list[Path], template: Optional[str] = None) -> str:
    """Create email subject from file list.

    Args:
        files: List of file paths
        template: Optional subject template with variables

    Returns:
        Email subject string
    """
    if template:
        now = datetime.now()
        if len(files) == 1:
            file = files[0]
            context = {
                "filename": file.name,
                "date": now.strftime("%Y-%m-%d"),
                "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
                "size": str(file.stat().st_size),
            }
            return format_subject_template(template, context)
        else:
            filenames = ", ".join(f.name for f in files)
            total_size = sum(f.stat().st_size for f in files)
            context = {
                "filenames": filenames,
                "file_count": str(len(files)),
                "date": now.strftime("%Y-%m-%d"),
                "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
                "total_size": str(total_size),
            }
            return format_subject_template(template, context)

    # Default logic
    if len(files) == 1:
        return files[0].name
    else:
        now = datetime.now()
        return f"Package of files - {now.strftime('%Y-%m-%d %H:%M:%S')}"


def calculate_email_size(files: list[Path]) -> int:
    """Calculate approximate email size including MIME overhead.

    Args:
        files: List of file paths

    Returns:
        Approximate email size in bytes (file sizes + ~33% MIME overhead)
    """
    total_file_size = sum(f.stat().st_size for f in files)
    # MIME encoding adds approximately 33% overhead
    mime_overhead = int(total_file_size * 0.33)
    return total_file_size + mime_overhead


def split_files_by_size(files: list[Path], max_size_mb: float) -> list[list[Path]]:
    """Split files into groups that fit within size limit.

    Args:
        files: List of file paths to split
        max_size_mb: Maximum email size in megabytes

    Returns:
        List of file groups, where each group fits within size limit

    Raises:
        ValueError: If a single file exceeds the size limit
    """
    max_size_bytes = int(max_size_mb * 1024 * 1024)
    logger = get_logger()
    groups: list[list[Path]] = []
    current_group: list[Path] = []
    current_size = 0

    for file_path in files:
        file_size = file_path.stat().st_size
        email_size_with_file = calculate_email_size([*current_group, file_path])

        # Check if single file exceeds limit
        if file_size > max_size_bytes:
            logger.error(
                "file_exceeds_limit",
                file=str(file_path),
                size_bytes=file_size,
                max_size_bytes=max_size_bytes,
            )
            raise ValueError(
                f"File {file_path.name} ({file_size / (1024 * 1024):.2f} MB) exceeds maximum email size ({max_size_mb} MB)"
            )

        # Check if adding this file would exceed limit
        if email_size_with_file > max_size_bytes and current_group:
            # Start a new group
            logger.debug(
                "file_group_split",
                group_size=len(current_group),
                group_size_bytes=current_size,
                next_file=str(file_path),
            )
            groups.append(current_group)
            current_group = [file_path]
            current_size = file_size
        else:
            # Add to current group
            current_group.append(file_path)
            current_size = email_size_with_file

    if current_group:
        groups.append(current_group)

    if len(groups) > 1:
        logger.warning(
            "files_split_into_multiple_emails",
            total_files=len(files),
            num_emails=len(groups),
            max_size_mb=max_size_mb,
        )

    return groups


def create_email_message(
    from_addr: str,
    to_addr: str,
    subject: str,
    files: list[Path],
    body_text: Optional[str] = None,
) -> MIMEMultipart:
    """Create MIME email message with file attachments.

    Args:
        from_addr: Sender email address
        to_addr: Recipient email address
        subject: Email subject
        files: List of file paths to attach
        body_text: Optional email body text

    Returns:
        MIMEMultipart message object
    """
    logger = get_logger()
    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg["Date"] = email.utils.formatdate()

    # Add body text if provided
    if body_text:
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
    else:
        # Default body
        if len(files) == 1:
            body = f"Attached file: {files[0].name}"
        else:
            body = f"Attached {len(files)} files:\n" + "\n".join(f"  - {f.name}" for f in files)
        msg.attach(MIMEText(body, "plain", "utf-8"))

    # Attach files
    for file_path in files:
        try:
            with file_path.open("rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                email.encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{file_path.name}"',
                )
                msg.attach(part)
                logger.debug(
                    "file_attached", file=str(file_path), size_bytes=file_path.stat().st_size
                )
        except OSError as e:
            logger.error("file_attach_error", file=str(file_path), error=str(e))
            raise

    return msg


class EmailSender:
    """Email sender class for sending files via SMTP."""

    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        use_tls: bool = True,
        use_ssl: bool = False,
        max_retries: int = 5,
        retry_delay: int = 3,
        max_email_size_mb: float = 25.0,
        subject_template: Optional[str] = None,
        subject_template_package: Optional[str] = None,
    ):
        """
        Initialize email sender.

        Args:
            smtp_server: SMTP server hostname
            smtp_port: SMTP server port
            smtp_user: SMTP username (email address)
            smtp_password: SMTP password
            use_tls: Use TLS encryption
            use_ssl: Use SSL encryption
            max_retries: Maximum retry attempts for connection
            retry_delay: Delay between retries in seconds
            max_email_size_mb: Maximum email size in megabytes
            subject_template: Optional template for single file subject
            subject_template_package: Optional template for multiple files subject
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_email_size_mb = max_email_size_mb
        self.subject_template = subject_template
        self.subject_template_package = subject_template_package
        self.logger = get_logger()

    def send_file(
        self,
        file_path: Path,
        recipient: str,
        subject: Optional[str] = None,
        dry_run: bool = False,
    ) -> bool:
        """Send a single file via email.

        Args:
            file_path: Path to file to send
            recipient: Recipient email address
            subject: Optional email subject (overrides template)
            dry_run: If True, simulate sending without actually sending

        Returns:
            True if sent successfully, False otherwise
        """
        return self.send_files([file_path], recipient, subject, dry_run)

    def send_files(
        self,
        files: list[Path],
        recipient: str,
        subject: Optional[str] = None,
        dry_run: bool = False,
    ) -> bool:
        """Send multiple files via email.

        Args:
            files: List of file paths to send
            recipient: Recipient email address
            subject: Optional email subject (overrides template)
            dry_run: If True, simulate sending without actually sending

        Returns:
            True if sent successfully, False otherwise
        """
        if not files:
            self.logger.warning("no_files_to_send")
            return False

        # Determine subject
        if subject:
            email_subject = subject
        elif len(files) == 1 and self.subject_template:
            email_subject = create_email_subject(files, self.subject_template)
        elif len(files) > 1 and self.subject_template_package:
            email_subject = create_email_subject(files, self.subject_template_package)
        else:
            email_subject = create_email_subject(files)

        # Split files by size if needed
        try:
            file_groups = split_files_by_size(files, self.max_email_size_mb)
        except ValueError as e:
            self.logger.error("file_size_error", error=str(e))
            return False

        if dry_run:
            self.logger.info(
                "dry_run_send",
                recipient=recipient,
                subject=email_subject,
                num_files=len(files),
                num_emails=len(file_groups),
            )
            for i, group in enumerate(file_groups, 1):
                group_size = calculate_email_size(group)
                self.logger.debug(
                    "dry_run_email",
                    email_num=i,
                    files=[str(f) for f in group],
                    size_bytes=group_size,
                )
            return True

        # Send each group as separate email
        try:
            # Import here to avoid circular dependency
            from email_processor.smtp import smtp_connect

            smtp = smtp_connect(
                self.smtp_server,
                self.smtp_port,
                self.smtp_user,
                self.smtp_password,
                self.use_tls,
                self.use_ssl,
                self.max_retries,
                self.retry_delay,
            )

            try:
                for i, file_group in enumerate(file_groups, 1):
                    # Adjust subject for multiple emails
                    group_subject = email_subject
                    if len(file_groups) > 1:
                        group_subject = f"{email_subject} (part {i}/{len(file_groups)})"

                    msg = create_email_message(
                        self.smtp_user,
                        recipient,
                        group_subject,
                        file_group,
                    )

                    smtp.send_message(msg)
                    self.logger.info(
                        "email_sent",
                        recipient=recipient,
                        subject=group_subject,
                        files=[f.name for f in file_group],
                        email_num=i,
                        total_emails=len(file_groups),
                    )
            finally:
                smtp.quit()

            return True

        except Exception as e:
            self.logger.error(
                "email_send_error", recipient=recipient, error=str(e), error_type=type(e).__name__
            )
            return False
