# Testing Guide

This project includes comprehensive unit and integration tests.

## Running Tests

### Install Test Dependencies

```bash
pip install -r requirements.txt
```

### Run All Tests

```bash
pytest
```

### Run with Coverage Report

```bash
pytest --cov=email_processor --cov-report=html
```

This will generate an HTML coverage report in `htmlcov/index.html`.

### Run Specific Test Files

```bash
# Run all unit tests (modular structure)
pytest tests/unit/

# Run all integration tests
pytest tests/test_integration.py

# Run specific module tests
pytest tests/unit/processor/
pytest tests/unit/config/
pytest tests/unit/imap/
```

### Run Specific Test Classes or Functions

```bash
# Run specific test class (after modularization)
pytest tests/unit/config/test_loader.py::TestConfigValidation

# Run specific test function
pytest tests/unit/config/test_loader.py::TestConfigValidation::test_valid_config

# Note: tests/test_unit.py no longer exists - tests are now in tests/unit/
```

### Verbose Output

```bash
pytest -v
```

## Test Structure

### Unit Tests (`tests/unit/`)

Modular test structure matching the codebase architecture:

- **`tests/unit/config/`**: Configuration loading and validation tests
- **`tests/unit/logging/`**: Logging setup and formatter tests
- **`tests/unit/imap/`**: IMAP client, authentication, and archiving tests
- **`tests/unit/processor/`**: Email processing, filtering, and attachment handling tests
- **`tests/unit/storage/`**: UID storage and file management tests
- **`tests/unit/utils/`**: Utility function tests (email, path, disk, folder resolver)

### Integration Tests (`tests/test_integration.py`)

Tests with mocked IMAP server:

- **TestIMAPPassword**: Password handling with keyring
- **TestIMAPConnection**: IMAP connection and retry logic
- **TestArchiveMessage**: Message archiving functionality
- **TestDownloadAttachments**: Full email processing workflow
- **TestClearPasswords**: Password clearing functionality

## Mock IMAP Server

The integration tests use a `MockIMAP4_SSL` class that simulates an IMAP server:

- Supports login, select, search, fetch operations
- Tracks archived and deleted messages
- Returns configurable responses for testing different scenarios

## Test Coverage

The tests cover:

- ✅ Configuration validation and loading
- ✅ Structured logging setup and formatting
- ✅ Helper functions (date parsing, folder names, path utilities, etc.)
- ✅ UID storage and retrieval
- ✅ IMAP connection and retry logic
- ✅ Password management (keyring)
- ✅ Email processing workflow
- ✅ Attachment downloading with extension filtering
- ✅ Message archiving
- ✅ Sender filtering
- ✅ Topic mapping
- ✅ Already processed message skipping
- ✅ Progress bar functionality
- ✅ Disk space checking
- ✅ File extension filtering (whitelist/blacklist)
- ✅ Path traversal protection
- ✅ Attachment size validation

## Writing New Tests

When adding new functionality:

1. Add unit tests in the appropriate module directory under `tests/unit/`
   - Match the structure of the codebase (e.g., `tests/unit/processor/` for processor tests)
2. Add integration tests for workflows in `tests/test_integration.py`
3. Use fixtures from `conftest.py` when possible
4. Mock external dependencies (keyring, imaplib, file system, tqdm)
5. Follow the naming convention: `test_<module>_<functionality>.py`

### Test File Naming

- Unit tests: `tests/unit/<module>/test_<component>.py`
- Integration tests: `tests/test_integration.py`
- Example: `tests/unit/processor/test_email_processor.py`

## Example Test

```python
def test_my_function(self):
    """Test description."""
    # Arrange
    input_data = "test"

    # Act
    result = my_function(input_data)

    # Assert
    self.assertEqual(result, "expected")
```

## Troubleshooting

Если вы столкнулись с проблемами при запуске тестов, см. файл `TROUBLESHOOTING.md` для подробных объяснений и решений.

### Частые проблемы:

1. **`file or directory not found: tests/test_unit.py`**
   - Файл был удален при модуляризации
   - Используйте: `pytest tests/unit/` вместо `pytest tests/test_unit.py`

2. **Ошибки IMAP в логах при тестах**
   - Это нормально для тестов, проверяющих обработку ошибок
   - Используйте `pytest` вместо прямого запуска через `unittest.main()`

3. **`pytest: reading from stdin while output is captured!`**
   - Убедитесь, что `get_imap_password` правильно замокирован в тестах
   - Используйте правильный путь для патча: `email_processor.processor.email_processor.get_imap_password`
