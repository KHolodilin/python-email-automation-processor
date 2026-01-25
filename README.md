# 📦 Email Attachment Processor
### (YAML + keyring + per-day UID storage + password management + modular architecture)

[![PyPI](https://img.shields.io/pypi/v/email-processor)](https://pypi.org/project/email-processor/)
[![CI](https://github.com/KHolodilin/python-email-automation-processor/actions/workflows/ci.yml/badge.svg)](https://github.com/KHolodilin/python-email-automation-processor/actions/workflows/ci.yml)
[![Test Coverage](https://codecov.io/gh/KHolodilin/python-email-automation-processor/branch/main/graph/badge.svg)](https://codecov.io/gh/KHolodilin/python-email-automation-processor)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/KHolodilin/python-email-automation-processor)](LICENSE)
[![Stars](https://img.shields.io/github/stars/KHolodilin/python-email-automation-processor)](https://github.com/KHolodilin/python-email-automation-processor/stargazers)
[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Email Processor is a reliable, idempotent, and secure tool for automatic email processing:
- **IMAP**: downloads attachments, organizes them into folders based on subject, archives processed emails
- **SMTP**: sends files via email with automatic tracking of sent files
- stores processed email UIDs in separate files by date
- uses keyring for secure password storage
- **command structure with subcommands support**
- **standardized exit codes** (`email_processor.exit_codes.ExitCode`) for scripting and automation
- **progress bar** for long-running operations
- **file extension filtering** (whitelist/blacklist)
- **disk space checking** before downloads
- **structured logging** with file output
- **dry-run mode** for testing
---

# 🚀 Key Features

### 🔐 Secure IMAP Password Management
- Password is not stored in code or YAML
- Saved in system storage (**Windows Credential Manager**, **macOS Keychain**, **Linux SecretService**)
- **Passwords are encrypted** before storing in keyring using system-based key derivation
- Encryption key is generated from system characteristics (MAC address, hostname, user ID) - never stored
- On first run, the script will prompt for password and offer to save it
- Backward compatible: automatically migrates unencrypted passwords on next save

### ⚙️ Configuration via `config.yaml`
- **IMAP**: Download folder management, subject-based sorting rules (`topic_mapping`), allowed sender management, archive settings
- **SMTP**: Server settings, default recipient, email size limits, subject templates
- Behavior options ("process / skip / archive")
- File extension filtering (whitelist/blacklist)
- Progress bar control
- Structured logging configuration

### ⚡ Fast Two-Phase IMAP Fetch
1. Fast header fetch: `FROM SUBJECT DATE UID`
2. Full email (`RFC822`) is loaded **only if it matches the logic**

### 📁 Optimized Processed Email Storage
Each email's UID is saved in:

```
processed_uids/YYYY-MM-DD.txt
```

This ensures:

- 🔥 fast lookup of already processed UIDs
- ⚡ minimal memory usage
- 📉 no duplicate downloads
- 📁 convenient rotation of old records

---

# 🚀 Quick Start

## Installation and Initial Setup

### 1. Install the module
```bash
pip install email-processor
```

### 2. Create Configuration
```bash
# Create configuration file from template
python -m email_processor config init

# Edit config.yaml with your IMAP/SMTP settings
```

### 3. Set Password
```bash
# Set IMAP password (will be prompted interactively)
# --user can be omitted if imap.user is set in config.yaml
python -m email_processor password set --user your_email@example.com
python -m email_processor password set   # uses imap.user from config

# Or from file
python -m email_processor password set --user your_email@example.com --password-file ~/.pass --delete-after-read
```

### 4. Validate Configuration
```bash
# Validate configuration
python -m email_processor config validate

# View system status
python -m email_processor status
```

### 5. Fetch (download emails and attachments)
Uses config by default (IMAP server, folder, processing options).
```bash
# Test mode (no real actions)
python -m email_processor fetch --dry-run

# Run fetch
python -m email_processor fetch
```

### 6. Send (email files)
```bash
# Send a single file
python -m email_processor send file /path/to/file.pdf --to recipient@example.com
```

### 7. Send All Files from Folder
Uses config by default (`smtp.send_folder`, `smtp.default_recipient`).
```bash
# Send from folder (config defaults)
python -m email_processor send
# Or explicitly:
python -m email_processor send folder
```

### 8. Full pipeline: fetch + send
```bash
python -m email_processor run
```

---

# 🎯 Usage

## Main Commands

### Email Processing

#### Full Pipeline (fetch + send)
```bash
# Process emails and send files
python -m email_processor run

# With limitations
python -m email_processor run --since 7d --max-emails 100
```

#### Email Fetching Only (without sending)
Uses config (IMAP, processing) by default.
```bash
# Fetch emails and attachments
python -m email_processor fetch

# Process emails from last 7 days
python -m email_processor fetch --since 7d

# Process specific folder
python -m email_processor fetch --folder "INBOX/Important"

# Limit number of emails
python -m email_processor fetch --max-emails 50

# Test mode (without real actions)
python -m email_processor fetch --dry-run

# Test mode with mock server (without connection)
python -m email_processor fetch --dry-run-no-connect
```

### Sending Files via Email

#### Send Single File
```bash
# Send file (--to is required)
python -m email_processor send file /path/to/file.pdf --to recipient@example.com

# With custom subject
python -m email_processor send file file.pdf --to user@example.com --subject "Important Document"

# With CC and BCC
python -m email_processor send file file.pdf --to user@example.com --cc copy@example.com --bcc hidden@example.com

# Test mode (without real sending)
python -m email_processor send file file.pdf --to user@example.com --dry-run
```

#### Send All Files from Folder
```bash
# With config defaults (smtp.send_folder, smtp.default_recipient)
python -m email_processor send
# Or explicitly:
python -m email_processor send folder

# Explicit path and recipient
python -m email_processor send folder /path/to/folder --to recipient@example.com

# With custom subject
python -m email_processor send folder /path/to/folder --to user@example.com --subject "File Package"
```

**Notes:**
- Files are tracked by SHA256 hash, so renamed files with the same content won't be sent again
- Already sent files are automatically skipped

### Password Management

#### Set Password
```bash
# Interactive password input
# --user is optional when imap.user is in config.yaml
python -m email_processor password set --user your_email@example.com
python -m email_processor password set   # uses imap.user from config

# From file (file will be deleted after reading)
python -m email_processor password set --user your_email@example.com --password-file ~/.pass --delete-after-read
```

#### Clear Password
```bash
# Delete saved password (--user optional if imap.user in config)
python -m email_processor password clear --user your_email@example.com
python -m email_processor password clear   # uses imap.user from config
```

### Configuration Management

#### Create Configuration
```bash
# Create config.yaml from template
python -m email_processor config init

# With custom path
python -m email_processor config init --path /path/to/custom_config.yaml
```

#### Validate Configuration
```bash
# Validate configuration
python -m email_processor config validate

# With custom file
python -m email_processor config validate --config /path/to/config.yaml
```

### View Status
```bash
# Show system status
python -m email_processor status
```

Shows:
- Application version
- Configuration path
- IMAP/SMTP settings
- Keyring availability
- Storage statistics

### Global Options

All commands support the following options:

```bash
# Specify configuration file
--config /path/to/config.yaml

# Test mode (without real actions)
--dry-run

# Logging level
--log-level DEBUG|INFO|WARNING|ERROR

# Log file path
--log-file /path/to/logs/app.log

# JSON log format
--json-logs

# Verbose output
--verbose

# Quiet mode (errors only)
--quiet

# Version
--version
```

### Option Combination Examples

```bash
# Verbose output with DEBUG logging
python -m email_processor fetch --verbose --log-level DEBUG

# Test mode with JSON logs
python -m email_processor run --dry-run --json-logs

# Processing with limitations and logging
python -m email_processor fetch --since 3d --max-emails 20 --log-file logs/run.log
```

---

## Exit Codes

The CLI uses standardized exit codes to provide clear error reporting and enable proper error handling in scripts and automation tools. All exit codes are defined in the `ExitCode` enum in `email_processor.exit_codes`. The `main()` entry point and all CLI commands return `ExitCode` values (or exit with them); as an `IntEnum`, they compare equal to their integer values (e.g. `ExitCode.SUCCESS == 0`).

### Standard Exit Codes

| Code | Constant | Description |
|------|----------|-------------|
| `0` | `SUCCESS` | Operation completed successfully |
| `1` | `PROCESSING_ERROR` | Errors during extraction, parsing, mapping, or write operations |
| `2` | `VALIDATION_FAILED` | Input validation errors (e.g., invalid arguments, email format) |
| `3` | `FILE_NOT_FOUND` | Requested file or directory does not exist |
| `4` | `UNSUPPORTED_FORMAT` | Cannot detect or process the requested format (e.g., authentication/keyring errors) |
| `5` | `WARNINGS_AS_ERRORS` | Warnings were treated as errors (when `--fail-on-warnings` is enabled) |
| `6` | `CONFIG_ERROR` | Errors loading or validating configuration file |

### Usage in Scripts

You can use exit codes in shell scripts to handle different error scenarios:

```bash
#!/bin/bash

# Run email processor
python -m email_processor run

# Check exit code
case $? in
    0)
        echo "Success: Emails processed successfully"
        ;;
    1)
        echo "Error: Processing failed"
        exit 1
        ;;
    2)
        echo "Error: Invalid arguments or validation failed"
        exit 1
        ;;
    3)
        echo "Error: File not found"
        exit 1
        ;;
    6)
        echo "Error: Configuration file error"
        exit 1
        ;;
    *)
        echo "Error: Unknown error"
        exit 1
        ;;
esac
```

### Python Script Example

```python
import subprocess
from email_processor.exit_codes import ExitCode

result = subprocess.run(
    ["python", "-m", "email_processor", "run"],
    capture_output=True
)

if result.returncode == ExitCode.SUCCESS:
    print("Processing completed successfully")
elif result.returncode == ExitCode.CONFIG_ERROR:
    print("Configuration error - check config.yaml")
elif result.returncode == ExitCode.PROCESSING_ERROR:
    print("Processing error occurred")
else:
    print(f"Unexpected exit code: {result.returncode}")
```

### Common Exit Code Scenarios

- **`0` (SUCCESS)**: Command executed successfully
- **`1` (PROCESSING_ERROR)**: IMAP/SMTP processing failed, send/archive error, or write error
- **`2` (VALIDATION_FAILED)**: Invalid email address, missing required arguments, or invalid command
- **`3` (FILE_NOT_FOUND)**: Configuration file not found, password file not found, or target file/directory missing
- **`4` (UNSUPPORTED_FORMAT)**: Authentication/keyring error or unsupported format
- **`6` (CONFIG_ERROR)**: Configuration file syntax error, validation failure, or missing required settings

---

## 🔒 Password Encryption

Passwords stored in keyring are encrypted using a system-based encryption key:

### How It Works
- **Encryption key** is generated from system characteristics:
  - MAC address of network interface
  - Hostname
  - User ID (Windows SID / Linux UID)
  - Config file path hash
  - Python version
- **Key is never stored** - computed dynamically each time
- **PBKDF2-HMAC-SHA256** with 100,000 iterations for key derivation
- **Fernet (AES-128)** encryption for passwords

### Security Benefits
- ✅ Passwords encrypted even if keyring is compromised
- ✅ Key cannot be stolen (not stored anywhere)
- ✅ Automatic operation (no user input required)
- ✅ Backward compatible with existing unencrypted passwords

### Limitations
- ⚠️ System changes (MAC address, hostname, user) require password re-entry
- ⚠️ Cannot transfer passwords to another system
- ⚠️ System reinstall requires password re-entry

### Migration
- Old unencrypted passwords are automatically encrypted on next save
- If decryption fails (system changed), you'll be prompted to re-enter password

---

# ⚡ Implementation Benefits

### ⚡ Time Savings
Duplicate emails are skipped instantly.

### ⚡ Reduced IMAP Server Load
Minimal IMAP operations, partial fetch.

### ⚡ No Duplicate Attachment Downloads
Each attachment is downloaded only once.

### ⚡ No File Duplicates
Automatic numbering is used: `file_01.pdf`, `file_02.pdf`.

### ⚡ Absolute Idempotency
Can be run 20 times in a row — result doesn't change.

### ⚡ Scalability
Per-day UID files ensure high performance.

---

# ⚙ Example config.yaml

```yaml
imap:
  server: "imap.example.com"
  user: "your_email@example.com"
  max_retries: 5
  retry_delay: 3

# SMTP settings for sending emails
smtp:
  server: "smtp.example.com"
  port: 587  # or 465 for SSL
  use_tls: true  # for port 587
  use_ssl: false  # for port 465
  user: "your_email@example.com"  # reuse from imap.user or set separately
  default_recipient: "recipient@example.com"
  max_email_size: 25  # MB
  sent_files_dir: "sent_files"  # directory for storing sent file hashes
  # Optional: subject templates
  # subject_template: "File: {filename}"  # template for single file
  # subject_template_package: "Package of files - {date}"  # template for multiple files
  # Available variables: {filename}, {filenames}, {file_count}, {date}, {datetime}, {size}, {total_size}

processing:
  start_days_back: 5
  archive_folder: "INBOX/Processed"
  processed_dir: "C:\\Users\\YourName\\AppData\\EmailProcessor\\processed_uids"
  keep_processed_days: 180
  archive_only_mapped: true
  skip_non_allowed_as_processed: true
  skip_unmapped_as_processed: true
  show_progress: true  # Show progress bar during processing
  # Extension filtering (optional):
  # allowed_extensions: [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".txt"]
  # blocked_extensions: [".exe", ".bat", ".sh", ".scr", ".vbs", ".js"]

# Logging settings
logging:
  level: INFO                      # DEBUG, INFO, WARNING, ERROR, CRITICAL
  format: console                  # "console" (readable) or "json" (structured)
  format_file: json                # Format for file logs (default: "json")
  file: logs                       # Optional: Directory for log files (rotated daily)

allowed_senders:
  - "client1@example.com"
  - "finance@example.com"
  - "boss@example.com"

topic_mapping:
  ".*Roadmap.*": "roadmap"
  "(Report).*": "reports"
  "(Invoice|Bill).*": "invoices"
  ".*": "default"  # Last rule is used as default for unmatched emails
```

### SMTP Configuration Details

**Required settings:**
- `smtp.server`: SMTP server hostname
- `smtp.port`: SMTP server port (typically 587 for TLS or 465 for SSL)
- `smtp.default_recipient`: Default recipient email address

**Optional settings:**
- `smtp.user`: SMTP username (defaults to `imap.user` if not specified)
- `smtp.use_tls`: Use TLS encryption (default: `true` for port 587)
- `smtp.use_ssl`: Use SSL encryption (default: `false`, use for port 465)
- `smtp.max_email_size`: Maximum email size in MB (default: `25`)
- `smtp.sent_files_dir`: Directory for storing sent file hashes (default: `"sent_files"`)
- `smtp.send_folder`: Default folder to send files from (optional, can be overridden with `send folder` command)
- `smtp.subject_template`: Template for single file subject (e.g., `"File: {filename}"`)
- `smtp.subject_template_package`: Template for multiple files subject (e.g., `"Package - {file_count} files"`)

**Subject template variables:**
- `{filename}` - Single file name
- `{filenames}` - Comma-separated list of file names (for packages)
- `{file_count}` - Number of files (for packages)
- `{date}` - Date in format YYYY-MM-DD
- `{datetime}` - Date and time in format YYYY-MM-DD HH:MM:SS
- `{size}` - File size in bytes (single file)
- `{total_size}` - Total size in bytes (for packages)

**Note:** Password is reused from IMAP keyring storage (same `imap.user` key). No separate SMTP password needed.
```

**Note:**
- All paths in `topic_mapping` can be either absolute or relative:
  - **Absolute paths**: `"C:\\Documents\\Roadmaps"` (Windows) or `"/home/user/documents/reports"` (Linux/macOS)
  - **Relative paths**: `"roadmap"` (relative to the script's working directory)
- **The last rule in `topic_mapping` is used as default** for all emails that don't match any of the previous patterns
- Both absolute and relative paths are supported for `processed_dir`:
  - **Absolute paths**: `"C:\\Users\\AppData\\processed_uids"` (Windows) or `"/home/user/.cache/processed_uids"` (Linux/macOS)
  - **Relative paths**: `"processed_uids"` (relative to the script's working directory)

  Example with mixed paths:
  ```yaml
  topic_mapping:
    ".*Roadmap.*": "C:\\Documents\\Roadmaps"  # Absolute path
    "(Report).*": "reports"                     # Relative path
    "(Invoice|Bill).*": "C:\\Finance\\Invoices" # Absolute path
    ".*": "default"                             # Default folder (relative path)
  ```

---

# 🔐 Password Management (Complete Command Set)

### ➕ Save Password (automatically)
```bash
python -m email_processor
```
On first run, the script will prompt for password and offer to save it.

### ➕ Set Password from File
```bash
# Read password from file and save it
python -m email_processor password set --user your_email@example.com --password-file ~/.pass

# Read password from file, save it, and remove the file
python -m email_processor password set --user your_email@example.com --password-file ~/.pass --delete-after-read
```

**Security Notes:**
- Password file should have restricted permissions (chmod 600 on Unix)
- Use `--delete-after-read` to automatically delete the file after reading
- Password is encrypted before saving to keyring
- Supports complex passwords via file (can copy-paste)

**Example:**
```bash
# Create password file
echo "your_complex_password" > ~/.email_password
chmod 600 ~/.email_password  # Restrict access (Unix only)

# Set password and remove file
python -m email_processor password set --user your_email@example.com --password-file ~/.email_password --delete-after-read
```

### 🔍 Read Password
```python
import keyring
keyring.get_password("email-vkh-processor", "your_email@example.com")
```

### 🗑️ Delete Password
```bash
python -m email_processor password clear --user your_email@example.com
```

### ➕ Add Password Manually
```python
import keyring
keyring.set_password(
  "email-vkh-processor",
  "your_email@example.com",
  "MY_PASSWORD"
)
```

---

# 📋 Installation

## Using Virtual Environment (Recommended)

### 1. Create Virtual Environment

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note:** If you're using 32-bit Python on Windows and encounter DLL errors with cryptography, you may need to install an older version:
```bash
pip install cryptography==40.0.2
```
Alternatively, use 64-bit Python for better compatibility.

### 3. Copy Configuration Template

```bash
cp config.yaml.example config.yaml
```

### 4. Edit Configuration

Edit `config.yaml` with your IMAP settings

### 5. Run the Script

```bash
# As a module
python -m email_processor

# Or install and use as command
pip install -e .
email-processor
```

### 6. Deactivate Virtual Environment (when done)

```bash
deactivate
```

## Alternative: Global Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy configuration template:
```bash
cp config.yaml.example config.yaml
```

3. Edit `config.yaml` with your IMAP settings

4. Run the script:
```bash
# As a module
python -m email_processor

# Or install and use as command
pip install -e .
email-processor

# To build distributable package for pip install, see `docs/_build/BUILD.md`
```

## 🛠️ Development Setup

For development, install additional tools:

```bash
pip install ruff mypy types-PyYAML
```

### Code Quality Tools

- **Ruff**: Fast linter and formatter (replaces Black)
  ```bash
  ruff check .          # Check for issues
  ruff check --fix .    # Auto-fix issues
  ruff format .         # Format code
  ruff format --check . # Check formatting
  ```

- **MyPy**: Type checker
  ```bash
  mypy email_processor  # Type check
  ```

### Test Coverage

The project uses [Codecov](https://codecov.io) for test coverage tracking and reporting. Coverage reports are automatically generated during CI runs and uploaded to Codecov.

- **View coverage reports**: [Codecov Dashboard](https://codecov.io/gh/KHolodilin/python-email-automation-processor)
- **Run tests with coverage locally**:
  ```bash
  pytest --cov=email_processor --cov-report=term-missing --cov-report=html
  ```
- **View HTML coverage report**: Open `htmlcov/index.html` in your browser after running tests

The project maintains a minimum test coverage threshold of 70% (with plans to increase to 95%+). Coverage reports help identify untested code paths and ensure code quality.

See `CONTRIBUTING.md` for detailed development guidelines.

---

# 🔧 Configuration Options

## IMAP Settings
- `server`: IMAP server address (required)
- `user`: Email address (required)
- `max_retries`: Maximum connection retry attempts (default: 5)
- `retry_delay`: Delay between retries in seconds (default: 3)

## Processing Settings
- `start_days_back`: How many days back to process emails (default: 5)
- `archive_folder`: IMAP folder for archived emails (default: "INBOX/Processed")
- `processed_dir`: Directory for processed UID files (default: "processed_uids")
  - **Supports absolute paths**: `"C:\\Users\\AppData\\processed_uids"` or `"/home/user/.cache/processed_uids"`
  - **Supports relative paths**: `"processed_uids"` (relative to script directory)
- `keep_processed_days`: Days to keep processed UID files (0 = keep forever, default: 0)
- `archive_only_mapped`: Archive only emails matching topic_mapping (default: true)
- `skip_non_allowed_as_processed`: Mark non-allowed senders as processed (default: true)
- `skip_unmapped_as_processed`: Mark unmapped emails as processed (default: true)
- `show_progress`: Show progress bar during processing (default: true, requires tqdm)
- `allowed_extensions`: List of allowed file extensions (e.g., `[".pdf", ".doc"]`)
  - If specified, only files with these extensions will be downloaded
  - Case-insensitive, dot prefix optional
- `blocked_extensions`: List of blocked file extensions (e.g., `[".exe", ".bat"]`)
  - Takes priority over `allowed_extensions`
  - Files with these extensions will be skipped
  - Case-insensitive, dot prefix optional

## Logging Settings
- `level`: Logging level - DEBUG, INFO, WARNING, ERROR, CRITICAL (default: "INFO")
- `format`: Console output format - "console" (readable) or "json" (structured, default: "console")
- `format_file`: File log format - "console" or "json" (default: "json")
- `file`: Directory for log files (optional, format: `yyyy-mm-dd.log`, rotated daily)
  - If not set, logs go to stdout only

## Allowed Senders
List of email addresses allowed to process. If empty, no emails will be processed.

## Topic Mapping
Dictionary of regex patterns to folder paths. Emails matching a pattern will be saved to the corresponding folder.
- **The last rule in `topic_mapping` is used as default** for all emails that don't match any of the previous patterns
- All paths can be absolute (e.g., `"C:\\Documents\\Roadmaps"`) or relative (e.g., `"roadmap"`)
- Patterns are checked in order, and the first match is used

---

# 🏗️ Architecture

The project uses a modular architecture for better maintainability:

```
email_processor/
├── cli/             # CLI commands and user interface
│   ├── commands/    # CLI subcommands (config, imap, passwords, smtp, status)
│   └── ui.py        # UI components and console output
├── config/          # Configuration loading and validation
├── imap/            # IMAP operations (client, auth, archive, fetcher, filters)
├── logging/         # Structured logging setup and formatters
├── security/        # Security features (encryption, fingerprint, key generation)
├── smtp/            # SMTP operations (client, sender, config)
├── storage/         # UID storage and file management
└── utils/           # Utility functions (email, path, disk, folder resolver, context)
```

Key modules:
- **`cli/`**: Command-line interface with subcommands for all operations
- **`config/`**: YAML configuration loading and validation
- **`imap/`**: Email fetching, attachment downloading, and archiving
- **`smtp/`**: Email sending with file tracking
- **`security/`**: Password encryption and system-based key derivation
- **`storage/`**: Processed UID tracking and sent file management
- **`utils/`**: Helper functions for common operations

# 📚 Additional Documentation

- **Testing Guide**: See `docs/_build/README_TESTS.md`
- **Building and Distribution**: See `docs/_build/BUILD.md` (how to build package for `pip install`)
- **Plans, reports, internal docs**: `docs/_build/` (PLAN, REDUNDANT_CODE_REPORT, unit-tests-structure, etc.)
