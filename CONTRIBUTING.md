# Contributing Guide

This document describes how to set up the development environment and use code quality tools.

## Development Setup

### 1. Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# Or install with dev dependencies (if using pyproject.toml)
pip install -e ".[dev]"
```

### 2. Code Quality Tools

This project uses several tools to maintain code quality:

- **Ruff**: Fast Python linter and formatter
- **Black**: Code formatter
- **MyPy**: Static type checker

#### Ruff

Ruff is configured via `ruff.toml`. It combines the functionality of multiple linters (flake8, isort, etc.).

```bash
# Check for issues
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code (alternative to black)
ruff format .
```

#### Black

Black is configured via `pyproject.toml`.

```bash
# Check formatting
black --check .

# Format code
black .
```

#### MyPy

MyPy is configured via `.mypy.ini` and `pyproject.toml`.

```bash
# Type check
mypy email_processor
```

### 3. Pre-commit Hooks (Optional)

Pre-commit hooks automatically run code quality checks before each commit.

```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

### 4. Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=email_processor --cov-report=html

# Run specific test file
pytest tests/unit/processor/test_email_processor.py
```

### 5. Code Quality Workflow

Before committing:

1. **Format code**:
   ```bash
   ruff format .
   ```

2. **Lint code**:
   ```bash
   ruff check --fix .
   ```

3. **Type check** (optional):
   ```bash
   mypy email_processor
   ```

4. **Run tests**:
   ```bash
   pytest
   ```

### 6. IDE Integration

#### VS Code

Add to `.vscode/settings.json`:

```json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

#### PyCharm

1. Install Ruff plugin
2. Configure Black as formatter
3. Enable MyPy inspection

## Configuration Files

- `ruff.toml` - Ruff linter configuration
- `pyproject.toml` - Black, MyPy, and project metadata
- `.mypy.ini` - MyPy type checker configuration
- `.pre-commit-config.yaml` - Pre-commit hooks configuration
- `pytest.ini` - Pytest test configuration

## Code Style

- **Line length**: 100 characters
- **Target Python version**: 3.9+
- **Type hints**: Recommended but not required
- **Docstrings**: Use Google style for public APIs

## Commit Messages

Follow conventional commits format:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Test additions/changes
- `chore:` Maintenance tasks

Example:
```
feat: add request ID and correlation ID to logs
fix: improve error handling with specific exceptions
```
