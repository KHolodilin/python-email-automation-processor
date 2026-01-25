# Building and Distributing the Package

This guide explains how to build and distribute the `email-processor` package for installation via `pip install`.

## Automated Build with GitHub Actions

The project includes GitHub Actions workflows for automated building and publishing:

- **`.github/workflows/ci.yml`** - Continuous Integration (runs on every push/PR)
  - Runs tests on multiple Python versions and OS
  - Checks code quality (linting, formatting, type checking)
  - Verifies package can be built

- **`.github/workflows/build-and-publish.yml`** - Build and Publish (runs on tags/releases)
  - Builds package on multiple Python versions
  - Publishes to TestPyPI (for testing)
  - Publishes to PyPI (on release)

### Setting up GitHub Actions

1. **Add PyPI API Token** (for publishing):
   - Go to PyPI → Account Settings → API tokens
   - Create a new token with "Upload packages" scope
   - Add to GitHub repository: Settings → Secrets → Actions
   - Name: `PYPI_API_TOKEN`

2. **Add TestPyPI API Token** (optional, for testing):
   - Go to TestPyPI → Account Settings → API tokens
   - Create a new token
   - Add to GitHub: `TESTPYPI_API_TOKEN`

3. **Create a Release**:
   ```bash
   git tag -a v7.1.0 -m "Release version 7.1.0"
   git push origin v7.1.0
   ```
   Or create a release on GitHub - this will trigger the publish workflow.

### Manual Build (Local)

## Prerequisites

Before building, ensure you have:

1. **Python 3.9+** installed
2. **Build tools** installed:
   ```bash
   pip install build wheel setuptools twine
   ```
   - `build` - Modern build frontend (recommended)
   - `wheel` - For building wheel distributions
   - `setuptools` - Required for setup.py-based builds
   - `twine` - For uploading to PyPI (optional, only for publishing)
3. **All dependencies** installed:
   ```bash
   pip install -r requirements.txt
   ```

## Manual Building the Package

### 1. Prepare for Build

Ensure all files are up to date:
- Run tests: `pytest`
- Run linting: `ruff check .`
- Run type checking: `mypy email_processor`
- Format code: `ruff format .`

### 2. Build Source Distribution (sdist)

Creates a `.tar.gz` archive with source code:

```bash
# Using modern build tool (recommended)
python -m build --sdist

# Or using setuptools directly
python setup.py sdist
```

Output: `dist/email-processor-7.1.0.tar.gz`

### 3. Build Wheel Distribution

Creates a `.whl` file (preferred format):

```bash
# Using modern build tool (recommended)
python -m build --wheel

# Or using setuptools directly
python setup.py bdist_wheel
```

Output: `dist/email_processer-7.1.0-py3-none-any.whl`

### 4. Build Both Formats

Build both source and wheel distributions:

```bash
python -m build
```

This creates both `.tar.gz` and `.whl` files in the `dist/` directory.

## Installing from Local Build

### Option 1: Install from Wheel (Recommended)

```bash
pip install dist/email_processer-7.1.0-py3-none-any.whl
```

### Option 2: Install from Source Distribution

```bash
pip install dist/email-processor-7.1.0.tar.gz
```

### Option 3: Install Directly from Source

```bash
pip install -e .
# or
pip install .
```

## Verifying the Build

### 1. Check Package Contents

```bash
# List files in the wheel
python -m zipfile -l dist/email_processer-7.1.0-py3-none-any.whl

# Extract and inspect
python -m zipfile -e dist/email_processer-7.1.0-py3-none-any.whl temp_extract
```

### 2. Test Installation

```bash
# Install in a clean environment
python -m venv test_env
test_env\Scripts\activate  # Windows
# or
source test_env/bin/activate  # Linux/Mac

pip install dist/email_processer-7.1.0-py3-none-any.whl

# Verify installation
email-processor --version
python -c "import email_processor; print(email_processor.__version__)"
```

### 3. Check Package Metadata

```bash
pip show email-processor
pip list | grep email-processor
```

## Publishing to PyPI

### 1. Prepare for Publishing

1. **Update version** in:
   - `email_processor/__version__.py`
   - `setup.py` (if version is hardcoded)
   - `pyproject.toml` (if version is there)

2. **Create a release tag**:
   ```bash
   git tag -a v7.1.0 -m "Release version 7.1.0"
   git push origin v7.1.0
   ```

3. **Build distributions**:
   ```bash
   python -m build
   ```

### 2. Check Distribution Before Upload

```bash
# Check for common issues
python -m twine check dist/*
```

This will verify:
- Package metadata
- File structure
- README format
- License file presence

### 3. Upload to TestPyPI (Recommended First)

TestPyPI is a testing environment for PyPI:

```bash
# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# Install from TestPyPI to verify
pip install --index-url https://test.pypi.org/simple/ email-processor
```

### 4. Upload to PyPI

Once verified on TestPyPI:

```bash
# Upload to PyPI
python -m twine upload dist/*
```

You'll need:
- PyPI account credentials
- API token (recommended) or username/password

### 5. Verify Installation from PyPI

```bash
# Wait a few minutes for indexing, then:
pip install email-processor
email-processor --version
```

## Build Configuration Files

The package uses these files for building:

- **`setup.py`** - Traditional setuptools configuration
- **`pyproject.toml`** - Modern PEP 621 metadata (preferred)
- **`MANIFEST.in`** - (Optional) Additional files to include

### Current Configuration

- **Package name**: `email-processor`
- **Entry point**: `email-processor = email_processor.__main__:main`
- **Python requirement**: `>=3.9`
- **Dependencies**: Listed in `setup.py` and `pyproject.toml`

## Troubleshooting

### Issue: "No module named 'build'"

**Solution**: Install build tools:
```bash
pip install build wheel setuptools
```

### Issue: "No module named 'setuptools'"

**Solution**: Install setuptools:
```bash
pip install setuptools wheel
```

Note: Modern Python (3.9+) usually includes setuptools, but it may need to be installed explicitly.

### Issue: "Package not found after installation"

**Solution**:
- Check Python environment: `python --version`
- Verify installation: `pip list | grep email-processor`
- Check PATH includes Python Scripts directory

### Issue: "Entry point not working"

**Solution**:
- Verify entry point in `setup.py`: `entry_points={"console_scripts": [...]}`
- Reinstall package: `pip install --force-reinstall -e .`
- On Windows, restart terminal after installation

### Issue: "Missing files in distribution"

**Solution**:
- Check `MANIFEST.in` if using it
- Verify all necessary files are tracked in git
- Ensure `__init__.py` files exist in all packages

## Build Checklist

Before building for distribution:

- [ ] All tests pass: `pytest`
- [ ] Code is formatted: `ruff format .`
- [ ] No linting errors: `ruff check .`
- [ ] Type checking passes: `mypy email_processor`
- [ ] Version number updated
- [ ] README.md is up to date
- [ ] LICENSE file exists
- [ ] All dependencies listed in `setup.py` and `pyproject.toml`
- [ ] Entry points configured correctly
- [ ] `__version__` is consistent across files

## Quick Reference

```bash
# Build package
python -m build

# Install locally
pip install dist/email_processer-7.1.0-py3-none-any.whl

# Check before upload
python -m twine check dist/*

# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# Upload to PyPI
python -m twine upload dist/*
```

## Additional Resources

- [Python Packaging User Guide](https://packaging.python.org/)
- [setuptools Documentation](https://setuptools.pypa.io/)
- [PyPI Upload Guide](https://packaging.python.org/guides/distributing-packages-using-setuptools/#uploading-your-project-to-pypi)
- [PEP 621 - Project metadata](https://peps.python.org/pep-0621/)
