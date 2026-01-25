"""SMTP email sender with file attachments."""

import email.encoders
import email.utils
import re
from datetime import datetime
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from email_processor.logging.setup import get_logger
from email_processor.smtp.config import SMTPConfig
from email_processor.utils.redact import redact_email


def format_subject_template(template: str, context: dict[str, str]) -> str:
    """Format subject template with context variables.

    Args:
        template: Template string with {variable} placeholders
        context: Dictionary with variable values

    Returns:
        Formatted subject string
    """
    logger = get_logger()
    # Extract all variable names from template
    template_vars = set(re.findall(r"\{(\w+)\}", template))
    logger.debug(
        "template_vars_extracted",
        template=template,
        found_vars=list(template_vars),
        provided_vars=list(context.keys()),
    )
    # Build context with all template variables, using empty string for missing ones
    full_context = {}
    for var in template_vars:
        full_context[var] = context.get(var, "")
        if var not in context:
            logger.debug("template_var_missing_using_empty", variable=var)

    logger.debug("template_formatting", template=template, context=full_context)
    try:
        result = template.format(**full_context)
        logger.debug("template_formatted", result=result)
        return result
    except KeyError as e:
        logger.warning("template_variable_missing", variable=str(e), template=template)
        # If still fails, return template with variables replaced manually
        result = template
        for var in template_vars:
            value = full_context.get(var, "")
            result = result.replace(f"{{{var}}}", value)
        logger.debug("template_manual_replacement", result=result)
        return result


def create_email_subject(files: list[Path], template: Optional[str] = None) -> str:
    """Create email subject from file list.

    Args:
        files: List of file paths
        template: Optional subject template with variables

    Returns:
        Email subject string
    """
    logger = get_logger()
    logger.debug("creating_email_subject", num_files=len(files), has_template=template is not None)
    if template:
        now = datetime.now()
        if len(files) == 1:
            file = files[0]
            file_size = file.stat().st_size
            context = {
                "filename": file.name,
                "date": now.strftime("%Y-%m-%d"),
                "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
                "size": str(file_size),
            }
            logger.debug(
                "subject_single_file_template",
                template=template,
                context=context,
                file_size_bytes=file_size,
            )
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
            logger.debug(
                "subject_package_template",
                template=template,
                context=context,
                total_size_bytes=total_size,
            )
            return format_subject_template(template, context)

    # Default logic
    if len(files) == 1:
        subject = files[0].name
        logger.debug("subject_default_single_file", subject=subject)
        return subject
    else:
        now = datetime.now()
        subject = f"Package of files - {now.strftime('%Y-%m-%d %H:%M:%S')}"
        logger.debug("subject_default_package", subject=subject, num_files=len(files))
        return subject


def calculate_email_size(files: list[Path]) -> int:
    """Calculate approximate email size including MIME overhead.

    Args:
        files: List of file paths

    Returns:
        Approximate email size in bytes (file sizes + ~33% MIME overhead)
    """
    logger = get_logger()
    file_sizes = [f.stat().st_size for f in files]
    total_file_size = sum(file_sizes)
    # MIME encoding adds approximately 33% overhead
    mime_overhead = int(total_file_size * 0.33)
    total_size = total_file_size + mime_overhead
    logger.debug(
        "email_size_calculated",
        num_files=len(files),
        total_file_size_bytes=total_file_size,
        mime_overhead_bytes=mime_overhead,
        total_size_bytes=total_size,
        file_sizes_bytes=file_sizes,
    )
    return total_size


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
    logger.debug(
        "splitting_files_by_size",
        num_files=len(files),
        max_size_mb=max_size_mb,
        max_size_bytes=max_size_bytes,
    )
    groups: list[list[Path]] = []
    current_group: list[Path] = []
    current_size = 0

    for file_path in files:
        file_size = file_path.stat().st_size
        email_size_with_file = calculate_email_size([*current_group, file_path])

        logger.debug(
            "file_size_check",
            file=str(file_path),
            file_size_bytes=file_size,
            current_group_size=len(current_group),
            current_group_email_size_bytes=current_size,
            email_size_with_file_bytes=email_size_with_file,
            max_size_bytes=max_size_bytes,
        )

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
                next_file_size_bytes=file_size,
            )
            groups.append(current_group)
            current_group = [file_path]
            current_size = calculate_email_size([file_path])
        else:
            # Add to current group
            current_group.append(file_path)
            current_size = email_size_with_file
            logger.debug(
                "file_added_to_group",
                file=str(file_path),
                group_size=len(current_group),
                group_email_size_bytes=current_size,
            )

    if current_group:
        groups.append(current_group)
        logger.debug("final_group_added", group_size=len(current_group))

    logger.debug(
        "files_split_complete",
        total_files=len(files),
        num_groups=len(groups),
        group_sizes=[len(g) for g in groups],
    )

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
    logger.debug(
        "creating_email_message",
        from_addr=from_addr,
        to_addr=to_addr,
        subject=subject,
        num_files=len(files),
        has_custom_body=body_text is not None,
    )
    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg["Date"] = email.utils.formatdate()

    # Add body text if provided
    if body_text:
        logger.debug("using_custom_body", body_length=len(body_text))
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
    else:
        # Default body
        if len(files) == 1:
            body = f"Attached file: {files[0].name}"
        else:
            body = f"Attached {len(files)} files:\n" + "\n".join(f"  - {f.name}" for f in files)
        logger.debug("using_default_body", body_length=len(body))
        msg.attach(MIMEText(body, "plain", "utf-8"))

    # Attach files
    total_attachment_size = 0
    for file_path in files:
        try:
            file_size = file_path.stat().st_size
            logger.debug(
                "attaching_file",
                file=str(file_path),
                size_bytes=file_size,
                filename=file_path.name,
            )
            with file_path.open("rb") as f:
                part = MIMEBase("application", "octet-stream")
                file_data = f.read()
                part.set_payload(file_data)
                email.encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{file_path.name}"',
                )
                msg.attach(part)
                total_attachment_size += file_size
                logger.debug(
                    "file_attached",
                    file=str(file_path),
                    size_bytes=file_size,
                    total_attachments_size_bytes=total_attachment_size,
                )
        except OSError as e:
            logger.error("file_attach_error", file=str(file_path), error=str(e))
            raise

    # Calculate approximate message size
    msg_str = str(msg)
    msg_size = len(msg_str.encode("utf-8"))
    logger.debug(
        "email_message_created",
        num_files=len(files),
        total_attachment_size_bytes=total_attachment_size,
        estimated_message_size_bytes=msg_size,
    )
    return msg


class EmailSender:
    """Email sender class for sending files via SMTP."""

    def __init__(
        self,
        config: SMTPConfig,
    ):
        """
        Initialize email sender.

        Args:
            config: SMTP configuration parameters
        """
        self.smtp_server = config.smtp_server
        self.smtp_port = config.smtp_port
        self.smtp_user = config.smtp_user
        self.smtp_password = config.smtp_password
        self.from_address = config.from_address
        self.use_tls = config.use_tls
        self.use_ssl = config.use_ssl
        self.max_retries = config.max_retries
        self.retry_delay = config.retry_delay
        self.max_email_size_mb = config.max_email_size_mb
        self.subject_template = config.subject_template
        self.subject_template_package = config.subject_template_package
        self.logger = get_logger()
        self.logger.debug(
            "email_sender_initialized",
            smtp_server=config.smtp_server,
            smtp_port=config.smtp_port,
            smtp_user=redact_email(config.smtp_user or ""),
            from_address=redact_email(config.from_address or ""),
        )

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
        self.logger.debug(
            "determining_email_subject",
            num_files=len(files),
            has_custom_subject=subject is not None,
            has_single_template=self.subject_template is not None,
            has_package_template=self.subject_template_package is not None,
        )
        if subject:
            email_subject = subject
            self.logger.debug("using_custom_subject", subject=subject)
        elif len(files) == 1 and self.subject_template:
            email_subject = create_email_subject(files, self.subject_template)
            self.logger.debug("using_single_file_template", template=self.subject_template)
        elif len(files) > 1 and self.subject_template_package:
            email_subject = create_email_subject(files, self.subject_template_package)
            self.logger.debug("using_package_template", template=self.subject_template_package)
        else:
            email_subject = create_email_subject(files)
            self.logger.debug("using_default_subject", subject=email_subject)

        # Split files by size if needed
        self.logger.debug(
            "splitting_files",
            num_files=len(files),
            max_email_size_mb=self.max_email_size_mb,
        )
        try:
            file_groups = split_files_by_size(files, self.max_email_size_mb)
            self.logger.debug(
                "files_split_result",
                num_groups=len(file_groups),
                group_sizes=[len(g) for g in file_groups],
            )
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
                        self.logger.debug(
                            "adjusting_subject_for_multipart",
                            original_subject=email_subject,
                            adjusted_subject=group_subject,
                            part_num=i,
                            total_parts=len(file_groups),
                        )

                    group_size = calculate_email_size(file_group)
                    self.logger.debug(
                        "sending_email_group",
                        email_num=i,
                        total_emails=len(file_groups),
                        group_size=len(file_group),
                        group_size_bytes=group_size,
                        files=[str(f) for f in file_group],
                        subject=group_subject,
                        from_address=self.from_address,
                        recipient=recipient,
                    )

                    msg = create_email_message(
                        self.from_address,
                        recipient,
                        group_subject,
                        file_group,
                    )

                    self.logger.debug("sending_message_via_smtp", email_num=i)
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
