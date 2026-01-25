# Test Structure

Test structure matches the main project `email_processor` structure:

```
tests/unit/
├── cli/                    # Tests for email_processor/cli/
│   ├── test_args.py        # Tests for email_processor/cli/args.py
│   ├── test_ui.py          # Tests for email_processor/cli/ui.py
│   ├── test_ui_cliui.py    # Tests for CLIUI class
│   └── commands/           # Tests for email_processor/cli/commands/
│       ├── test_config.py  # Tests for email_processor/cli/commands/config.py
│       ├── test_imap.py     # Tests for email_processor/cli/commands/imap.py
│       ├── test_passwords.py # Tests for email_processor/cli/commands/passwords.py
│       ├── test_smtp.py    # Tests for email_processor/cli/commands/smtp.py
│       └── test_status.py  # Tests for email_processor/cli/commands/status.py
├── config/                 # Tests for email_processor/config/
│   └── test_loader.py
├── imap/                   # Tests for email_processor/imap/
│   ├── test_archive.py
│   ├── test_attachments.py
│   ├── test_auth.py
│   ├── test_client.py
│   ├── test_fetcher.py
│   ├── test_fetcher_base.py         # Base class for Fetcher tests
│   ├── test_fetcher_header.py       # Header processing tests
│   ├── test_fetcher_message.py      # Message processing tests
│   ├── test_fetcher_uid.py          # UID processing tests
│   ├── test_fetcher_attachment.py   # Attachment processing tests
│   ├── test_fetcher_archive.py      # Archive operation tests
│   ├── test_fetcher_storage.py      # Processed UID storage tests
│   ├── test_fetcher_file_ops.py    # File operations tests
│   ├── test_fetcher_errors.py       # Error handling tests
│   └── test_filters.py
├── logging/                # Tests for email_processor/logging/
│   ├── test_formatters.py
│   └── test_setup.py
├── security/               # Tests for email_processor/security/
│   ├── test_encryption.py
│   ├── test_fingerprint.py
│   └── test_key_generator.py
├── smtp/                   # Tests for email_processor/smtp/
│   ├── test_client.py
│   ├── test_sender.py
│   └── test_sent_files_storage.py
├── storage/                # Tests for email_processor/storage/
│   ├── test_file_manager.py
│   └── test_uid_storage.py
├── utils/                  # Tests for email_processor/utils/
│   ├── test_context.py
│   ├── test_disk_utils.py
│   ├── test_email_utils.py
│   ├── test_folder_resolver.py
│   └── test_path_utils.py
└── test_main.py            # Tests for email_processor/__main__.py
```

## File Mapping

| Source File | Test File |
|------------|-----------|
| `email_processor/cli/args.py` | `tests/unit/cli/test_args.py` |
| `email_processor/cli/ui.py` | `tests/unit/cli/test_ui.py` |
| `email_processor/cli/commands/config.py` | `tests/unit/cli/commands/test_config.py` |
| `email_processor/cli/commands/imap.py` | `tests/unit/cli/commands/test_imap.py` |
| `email_processor/cli/commands/passwords.py` | `tests/unit/cli/commands/test_passwords.py` |
| `email_processor/cli/commands/smtp.py` | `tests/unit/cli/commands/test_smtp.py` |
| `email_processor/cli/commands/status.py` | `tests/unit/cli/commands/test_status.py` |
| `email_processor/__main__.py` | `tests/unit/test_main.py` |
| `email_processor/imap/fetcher.py` | `tests/unit/imap/test_fetcher.py`<br>`tests/unit/imap/test_fetcher_*.py` (additional tests) |
| `email_processor/imap/attachments.py` | `tests/unit/imap/test_attachments.py` |
| `email_processor/imap/filters.py` | `tests/unit/imap/test_filters.py` |
| `email_processor/security/encryption.py` | `tests/unit/security/test_encryption.py` |
| `email_processor/smtp/sender.py` | `tests/unit/smtp/test_sender.py` |
