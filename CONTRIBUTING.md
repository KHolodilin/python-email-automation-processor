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
pytest tests/unit/imap/test_fetcher_header.py

# Run all fetcher tests
pytest tests/unit/imap/test_fetcher_*.py

# Run specific test category
pytest tests/unit/imap/test_fetcher_attachment.py
```

### 5. Code Quality Workflow

**⚠️ IMPORTANT: Before committing and pushing, always run these checks:**

1. **Check formatting** (required):
   ```bash
   ruff format --check .
   ```
   If files need formatting, run:
   ```bash
   ruff format .
   ```

2. **Run pre-commit checks** (required):
   ```bash
   pre-commit run --all-files
   ```
   This will run all hooks including:
   - Trailing whitespace check
   - End of file fixer
   - Ruff linting and formatting
   - Ruff check (full project check)
   - MyPy type checking

3. **Lint code** (if pre-commit didn't fix everything):
   ```bash
   ruff check --fix .
   ```

4. **Type check** (optional, also runs in pre-commit):
   ```bash
   mypy email_processor
   ```

5. **Run tests**:
   ```bash
   pytest
   ```

**Recommended workflow:**
```bash
# 1. Check formatting first
ruff format --check .

# 2. If needed, format code
ruff format .

# 3. Run all pre-commit checks
pre-commit run --all-files

# 4. Run tests
pytest

# 5. Only then commit and push
git add .
git commit -m "your message"
git push
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
