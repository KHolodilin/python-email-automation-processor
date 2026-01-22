# 📦 Email Attachment Processor
### (YAML + keyring + per-day UID storage + password management + modular architecture)

Email Processor is a reliable, idempotent, and secure tool for automatic email processing:
- **IMAP**: downloads attachments, organizes them into folders based on subject, archives processed emails
- **SMTP**: sends files via email with automatic tracking of sent files
- stores processed email UIDs in separate files by date
- uses keyring for secure password storage
- **поддержка командной структуры с подкомандами**
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

# 🚀 Быстрый старт

## Установка и первая настройка

### 1. Установка зависимостей
```bash
# Создайте виртуальное окружение (рекомендуется)
python -m venv .venv
.venv\Scripts\activate  # Windows
# или
source .venv/bin/activate  # Linux/macOS

# Установите зависимости
pip install -r requirements.txt
```

### 2. Создание конфигурации
```bash
# Создайте файл конфигурации из шаблона
python -m email_processor config init

# Отредактируйте config.yaml с вашими настройками IMAP/SMTP
```

### 3. Установка пароля
```bash
# Установите пароль для IMAP (будет запрошен интерактивно)
python -m email_processor password set --user your_email@example.com

# Или из файла
python -m email_processor password set --user your_email@example.com --password-file ~/.pass --delete-after-read
```

### 4. Проверка конфигурации
```bash
# Проверьте корректность конфигурации
python -m email_processor config validate

# Просмотрите статус системы
python -m email_processor status
```

### 5. Первый запуск
```bash
# Запустите обработку писем (тестовый режим без реальных действий)
python -m email_processor fetch --dry-run

# Реальный запуск
python -m email_processor fetch
```

---

# 🎯 Использование

## Основные команды

### Обработка писем

#### Полный пайплайн (fetch + send)
```bash
# Обработать письма и отправить файлы
python -m email_processor run

# С ограничениями
python -m email_processor run --since 7d --max-emails 100
```

#### Только получение писем (без отправки)
```bash
# Получить письма и вложения
python -m email_processor fetch

# Обработать письма за последние 7 дней
python -m email_processor fetch --since 7d

# Обработать конкретную папку
python -m email_processor fetch --folder "INBOX/Important"

# Ограничить количество писем
python -m email_processor fetch --max-emails 50

# Тестовый режим (без реальных действий)
python -m email_processor fetch --dry-run

# Тестовый режим с мок-сервером (без подключения)
python -m email_processor fetch --dry-run-no-connect
```

### Отправка файлов по email

#### Отправить один файл
```bash
# Отправить файл (--to обязателен)
python -m email_processor send file /path/to/file.pdf --to recipient@example.com

# С кастомной темой
python -m email_processor send file file.pdf --to user@example.com --subject "Важный документ"

# С CC и BCC
python -m email_processor send file file.pdf --to user@example.com --cc copy@example.com --bcc hidden@example.com

# Тестовый режим (без реальной отправки)
python -m email_processor send file file.pdf --to user@example.com --dry-run
```

#### Отправить все файлы из папки
```bash
# Отправить все новые файлы из папки
python -m email_processor send folder /path/to/folder --to recipient@example.com

# С кастомной темой
python -m email_processor send folder /path/to/folder --to user@example.com --subject "Пакет файлов"
```

**Примечания:**
- Файлы отслеживаются по SHA256 хешу, поэтому переименованные файлы с тем же содержимым не будут отправлены повторно
- Уже отправленные файлы автоматически пропускаются

### Управление паролями

#### Установить пароль
```bash
# Интерактивный ввод пароля
python -m email_processor password set --user your_email@example.com

# Из файла (файл будет удален после чтения)
python -m email_processor password set --user your_email@example.com --password-file ~/.pass --delete-after-read
```

#### Очистить пароль
```bash
# Удалить сохраненный пароль
python -m email_processor password clear --user your_email@example.com
```

### Управление конфигурацией

#### Создать конфигурацию
```bash
# Создать config.yaml из шаблона
python -m email_processor config init

# С указанием пути
python -m email_processor config init --path /path/to/custom_config.yaml
```

#### Проверить конфигурацию
```bash
# Валидация конфигурации
python -m email_processor config validate

# С указанием файла
python -m email_processor config validate --config /path/to/config.yaml
```

### Просмотр статуса
```bash
# Показать статус системы
python -m email_processor status
```

Показывает:
- Версию приложения
- Путь к конфигурации
- Настройки IMAP/SMTP
- Доступность keyring
- Статистику хранилищ

### Глобальные опции

Все команды поддерживают следующие опции:

```bash
# Указать конфигурационный файл
--config /path/to/config.yaml

# Тестовый режим (без реальных действий)
--dry-run

# Уровень логирования
--log-level DEBUG|INFO|WARNING|ERROR

# Путь к файлу логов
--log-file /path/to/logs/app.log

# JSON формат логов
--json-logs

# Подробный вывод
--verbose

# Тихий режим (только ошибки)
--quiet

# Версия
--version
```

### Примеры комбинирования опций

```bash
# Подробный вывод с DEBUG логированием
python -m email_processor fetch --verbose --log-level DEBUG

# Тестовый режим с JSON логами
python -m email_processor run --dry-run --json-logs

# Обработка с ограничениями и логированием
python -m email_processor fetch --since 3d --max-emails 20 --log-file logs/run.log
```

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

# 🛠️ Features & Improvements

## v7.1 Features
- ✅ **Modular architecture** - Clean separation of concerns
- ✅ **YAML configuration** - Easy configuration management
- ✅ **Keyring password storage** - Secure credential management
- ✅ **Per-day UID storage** - Optimized performance
- ✅ **Two-phase IMAP fetch** - Efficient email processing
- ✅ **Password management commands** - `password set` and `password clear` subcommands
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
