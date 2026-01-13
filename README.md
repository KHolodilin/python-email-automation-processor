# 📦 Email Attachment Processor
### (YAML + keyring + per-day UID storage + password management + modular architecture)

Email Processor is a reliable, idempotent, and secure tool for automatic IMAP email processing:
- downloads attachments
- organizes them into folders based on subject
- archives processed emails
- stores processed email UIDs in separate files by date
- uses keyring for secure password storage
- **supports new command: `--clear-passwords`**
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
- On first run, the script will prompt for password and offer to save it

### ⚙️ Configuration via `config.yaml`
- Download folder management
- Subject-based sorting rules (`topic_mapping`)
- Allowed sender management
- Archive settings
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

# 🎯 Usage

## Running the Processor

### Normal Mode
```bash
python -m email_processor
# or after installation:
email-processor
```

### Custom Configuration File
```bash
python -m email_processor --config /path/to/custom_config.yaml
```

**Note:** By default, the processor uses `config.yaml` in the current directory. Use `--config` to specify a different configuration file path.

### Dry-Run Mode (Test without downloading)
```bash
python -m email_processor --dry-run
```

**Note:** In dry-run mode, the processor connects to the IMAP server to retrieve and analyze the email list (to display statistics), but files are not downloaded and emails are not archived.

### Dry-Run Mode with Mock Server (No connection)
```bash
python -m email_processor --dry-run-no-connect
```

**Note:** The `--dry-run-no-connect` mode uses a mocked IMAP server with test data. It does not require a real mail server connection or a password. It is useful for testing configuration without server access. It uses 3 test emails:
- Email from `client1@example.com` with subject "Roadmap Q1 2024" and attachment `roadmap.pdf`
- Email from `finance@example.com` with subject "Invoice #12345" and attachment `invoice.pdf`
- Email from `spam@example.com` with subject "Spam Subject" and attachment `spam.exe` (will be skipped if the sender is not in the allowed list)

### Show Version
```bash
python -m email_processor --version
```

### Clear Saved Passwords
```bash
python -m email_processor --clear-passwords
```

### Create Default Configuration
```bash
python -m email_processor --create-config
```

**Note:** This command creates a default `config.yaml` file from `config.yaml.example`. If the file already exists, you'll be prompted to confirm overwriting it. You can combine it with `--config` to specify a custom path:

```bash
python -m email_processor --create-config --config /path/to/custom_config.yaml
```

---

# ✨ Password Management Command

This command:

### ✔ removes saved password from keyring
### ✔ allows setting a new password on next run
### ✔ useful when:
- IMAP password expired / was changed
- switching to a different email account
- need to reset authorization without accessing Credential Manager

---

## 🔧 How `--clear-passwords` Works

1. Script reads `imap.user` from `config.yaml`
2. Requests confirmation:

```
Do you really want to delete saved passwords? [y/N]:
```

3. If user answers `y`:
  - password `email-vkh-processor / <user>` is removed from keyring

4. Script outputs report:

```
Done. Deleted entries: 1
```

5. On next normal mode run, the script will prompt for a new password.

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

processing:
  start_days_back: 5
  # Absolute paths are supported (Windows example):
  download_dir: "C:\\Users\\YourName\\Downloads\\EmailAttachments"
  # Or use relative path (relative to script directory):
  # download_dir: "downloads"
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
  "Request №\\d+": "applications"
```

**Note:** Both absolute and relative paths are supported for `download_dir` and `processed_dir`:
- **Absolute paths**: `"C:\\Users\\Downloads"` (Windows) or `"/home/user/downloads"` (Linux/macOS)
- **Relative paths**: `"downloads"` (relative to the script's working directory)

---

# 🔐 Password Management (Complete Command Set)

### ➕ Save Password (automatically)
```bash
python -m email_processor
```

### 🔍 Read Password
```python
import keyring
keyring.get_password("email-vkh-processor", "your_email@example.com")
```

### 🗑️ Delete Password
```bash
python -m email_processor --clear-passwords
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

# To build distributable package for pip install, see BUILD.md
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
- `download_dir`: Directory for downloaded attachments (default: "downloads")
  - **Supports absolute paths**: `"C:\\Users\\Downloads"` or `"/home/user/downloads"`
  - **Supports relative paths**: `"downloads"` (relative to script directory)
- `archive_folder`: IMAP folder for archived emails (default: "INBOX/Processed")
- `processed_dir`: Directory for processed UID files (default: "processed_uids")
  - **Supports absolute and relative paths** (same as download_dir)
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
Dictionary of regex patterns to folder names. Emails matching a pattern will be saved to the corresponding folder.

---

# 🛠️ Features & Improvements

## v7.1 Features
- ✅ **Modular architecture** - Clean separation of concerns
- ✅ **YAML configuration** - Easy configuration management
- ✅ **Keyring password storage** - Secure credential management
- ✅ **Per-day UID storage** - Optimized performance
- ✅ **Two-phase IMAP fetch** - Efficient email processing
- ✅ **Password management command** - `--clear-passwords` option
- ✅ **Configuration validation** - Validates config on startup
- ✅ **Structured logging** - JSON and console formats with file output
- ✅ **Configurable logging levels** - DEBUG, INFO, WARNING, ERROR, CRITICAL
- ✅ **Enhanced error handling** - Comprehensive error recovery
- ✅ **Detailed processing statistics** - File type statistics
- ✅ **Progress bar** - Visual progress indicator (tqdm)
- ✅ **File extension filtering** - Whitelist/blacklist support
- ✅ **Disk space checking** - Prevents out-of-space errors
- ✅ **Dry-run mode** - Test without downloading (`--dry-run`)
- ✅ **Type hints** - Full type annotation support
- ✅ **Path traversal protection** - Security hardening
- ✅ **Attachment size validation** - Prevents oversized downloads

---

# 📝 Notes

- The script is **idempotent**: safe to run multiple times
- Processed UIDs are stored per day for optimal performance
- Passwords are securely stored in system keyring
- Configuration is validated on startup
- All errors are logged with appropriate detail levels
- Progress bar shows real-time statistics (processed, skipped, errors)
- File extension filtering helps prevent unwanted downloads
- Disk space is checked before each download (with 10MB buffer)
- Logs are automatically rotated daily when file logging is enabled

# 🏗️ Architecture

The project uses a modular architecture for better maintainability:

```
email_processor/
├── config/          # Configuration loading and validation
├── logging/         # Structured logging setup
├── imap/            # IMAP operations (client, auth, archive)
├── processor/       # Email processing logic
├── storage/         # UID storage and file management
└── utils/           # Utility functions (email, path, disk, etc.)
```

See `ARCHITECTURE_PROPOSAL.md` for detailed architecture documentation.

# 📚 Additional Documentation

- **Testing Guide**: See `README_TESTS.md`
- **Building and Distribution**: See `BUILD.md` (how to build package for `pip install`)
