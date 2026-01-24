"""SMTP sending commands."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from email_processor.cli.ui import CLIUI
from email_processor.exit_codes import ExitCode
from email_processor.imap.auth import get_imap_password
from email_processor.smtp.config import SMTPConfig
from email_processor.smtp.sender import EmailSender
from email_processor.storage.sent_files_storage import SentFilesStorage


def send_file(
    cfg: dict,
    file_path: str,
    to_address: str,
    subject: Optional[str],
    dry_run: bool,
    config_path: str,
    ui: CLIUI,
) -> int:
    """Send a single file via SMTP.

    Args:
        cfg: Configuration dictionary
        file_path: Path to file to send
        to_address: Email recipient address (required, --to)
        subject: Optional email subject
        dry_run: If True, simulate sending without actually sending
        config_path: Path to configuration file
        ui: CLIUI instance for output

    Returns:
        int: 0 on success, 1 on error
    """
    # Initialize SMTP components
    smtp_cfg, sender, storage, day_str, final_recipient = _init_smtp_components(
        cfg, to_address, config_path, ui
    )
    if smtp_cfg is None:
        return ExitCode.CONFIG_ERROR

    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        ui.error(f"File not found: {file_path_obj}")
        return ExitCode.FILE_NOT_FOUND

    if not file_path_obj.is_file():
        ui.error(f"Not a file: {file_path_obj}")
        return ExitCode.VALIDATION_FAILED

    # Check if already sent
    if not dry_run and storage.is_sent(file_path_obj, day_str):
        ui.warn(f"File already sent: {file_path_obj.name}")
        return ExitCode.SUCCESS

    # Send file
    success = sender.send_file(file_path_obj, final_recipient, subject, dry_run=dry_run)

    if success and not dry_run:
        storage.mark_as_sent(file_path_obj, day_str)
        ui.success(f"File sent: {file_path_obj.name}")
    elif success and dry_run:
        if ui.has_rich:
            ui.print(f"[cyan]DRY-RUN:[/cyan] Would send file: {file_path_obj.name}")
        else:
            ui.info(f"DRY-RUN: Would send file: {file_path_obj.name}")
    else:
        ui.error(f"Failed to send file: {file_path_obj.name}")
        return ExitCode.PROCESSING_ERROR

    return ExitCode.SUCCESS


def send_folder(
    cfg: dict,
    folder_path: str,
    to_address: str,
    subject: Optional[str],
    dry_run: bool,
    config_path: str,
    ui: CLIUI,
) -> int:
    """Send files from a folder via SMTP.

    Args:
        cfg: Configuration dictionary
        folder_path: Path to folder containing files to send
        to_address: Email recipient address (required, --to)
        subject: Optional email subject
        dry_run: If True, simulate sending without actually sending
        config_path: Path to configuration file
        ui: CLIUI instance for output

    Returns:
        int: 0 on success, 1 on error
    """
    smtp_cfg = cfg.get("smtp")
    if not smtp_cfg:
        ui.error("'smtp' section is missing in config.yaml")
        return ExitCode.CONFIG_ERROR

    # Initialize SMTP components
    smtp_cfg_obj, sender, storage, day_str, final_recipient = _init_smtp_components(
        cfg, to_address, config_path, ui
    )
    if smtp_cfg_obj is None:
        return ExitCode.CONFIG_ERROR

    folder_path_obj = Path(folder_path)
    if not folder_path_obj.exists():
        ui.error(f"Folder not found: {folder_path_obj}")
        return ExitCode.FILE_NOT_FOUND

    if not folder_path_obj.is_dir():
        ui.error(f"Not a folder: {folder_path_obj}")
        return ExitCode.VALIDATION_FAILED

    # Find new files
    all_files = [f for f in folder_path_obj.iterdir() if f.is_file()]
    new_files = []
    skipped_count = 0

    for file_path in all_files:
        if not dry_run and storage.is_sent(file_path, day_str):
            skipped_count += 1
        else:
            new_files.append(file_path)

    if not new_files:
        if ui.has_rich:
            ui.print(
                f"[yellow]No new files to send[/yellow] (skipped {skipped_count} already sent)"
            )
        else:
            ui.info(f"No new files to send (skipped {skipped_count} already sent)")
        return ExitCode.SUCCESS

    # Send files
    sent_count = 0
    failed_count = 0

    for file_path in new_files:
        success = sender.send_file(file_path, final_recipient, subject, dry_run=dry_run)
        if success:
            if not dry_run:
                storage.mark_as_sent(file_path, day_str)
            sent_count += 1
        else:
            failed_count += 1

    # Display results
    if ui.has_rich:
        ui.print(f"[green]Sent:[/green] {sent_count} files")
        if skipped_count > 0:
            ui.print(f"[yellow]Skipped:[/yellow] {skipped_count} files (already sent)")
        if failed_count > 0:
            ui.print(f"[red]Failed:[/red] {failed_count} files")
    else:
        ui.info(f"Sent: {sent_count} files")
        if skipped_count > 0:
            ui.info(f"Skipped: {skipped_count} files (already sent)")
        if failed_count > 0:
            ui.info(f"Failed: {failed_count} files")

    return ExitCode.SUCCESS if failed_count == 0 else ExitCode.PROCESSING_ERROR


def _init_smtp_components(
    cfg: dict, to_address: Optional[str], config_path: str, ui: CLIUI
) -> tuple[
    Optional[SMTPConfig], Optional[EmailSender], Optional[SentFilesStorage], str, Optional[str]
]:
    """Initialize SMTP components.

    Args:
        cfg: Configuration dictionary
        to_address: Required recipient email address (--to)
        config_path: Path to configuration file
        ui: CLIUI instance for output

    Returns:
        tuple: (smtp_config, sender, storage, day_str, final_recipient) or (None, None, None, "", None) on error
    """
    smtp_cfg = cfg.get("smtp")
    if not smtp_cfg:
        ui.error("'smtp' section is missing in config.yaml")
        return None, None, None, "", None

    # Get SMTP settings and create config immediately
    smtp_user = smtp_cfg.get("user") or cfg.get("imap", {}).get("user")

    # Get password first (needed for config)
    try:
        password = get_imap_password(smtp_user, config_path)
    except Exception as e:
        ui.error(f"Error getting password: {e}")
        return None, None, None, "", None

    # Create SMTPConfig from settings
    smtp_config = SMTPConfig(
        smtp_server=smtp_cfg.get("server", ""),
        smtp_port=int(smtp_cfg.get("port", 587)),
        smtp_user=smtp_user or "",
        smtp_password=password,
        from_address=smtp_cfg.get("from_address", ""),
        use_tls=smtp_cfg.get("use_tls", True),
        use_ssl=smtp_cfg.get("use_ssl", False),
        max_email_size_mb=float(smtp_cfg.get("max_email_size", 25)),
        subject_template=smtp_cfg.get("subject_template"),
        subject_template_package=smtp_cfg.get("subject_template_package"),
    )

    # Validate required fields
    if not smtp_config.smtp_server:
        ui.error("'smtp.server' is required in config.yaml")
        return None, None, None, "", None

    if not smtp_config.smtp_user:
        ui.error("'smtp.user' or 'imap.user' is required in config.yaml")
        return None, None, None, "", None

    if not smtp_config.from_address:
        ui.error("'smtp.from_address' is required in config.yaml")
        return None, None, None, "", None

    # Get recipient (--to is required, so this should always be set)
    final_recipient = to_address
    if not final_recipient:
        ui.error("--to is required")
        return None, None, None, "", None

    # Get other settings
    sent_files_dir = smtp_cfg.get("sent_files_dir", "sent_files")
    sender = EmailSender(config=smtp_config)
    storage = SentFilesStorage(sent_files_dir)
    day_str = datetime.now().strftime("%Y-%m-%d")

    return smtp_config, sender, storage, day_str, final_recipient
