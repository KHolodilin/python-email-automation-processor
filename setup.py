"""Setup script for email-processor package."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = ""
if readme_file.exists():
    with readme_file.open("r", encoding="utf-8") as f:
        long_description = f.read()

# Read version
version_file = Path(__file__).parent / "email_processor" / "__version__.py"
version = "7.1.0"
if version_file.exists():
    with version_file.open("r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("__version__"):
                version = line.split("=")[1].strip().strip('"').strip("'")
                break

setup(
    name="email-processor",
    version=version,
    author="Your Name",
    description="Email attachment processor with IMAP support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    install_requires=[
        "pyyaml>=6.0",
        "keyring>=24.0",
        "structlog>=24.0.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "email-processor=email_processor.__main__:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
