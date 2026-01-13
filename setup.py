"""Setup script for email-processor package."""

from pathlib import Path

from setuptools import find_packages, setup

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = ""
if readme_file.exists():
    with readme_file.open("r", encoding="utf-8") as f:
        long_description = f.read()

# Read version
version_file = Path(__file__).parent / "email_processor" / "__version__.py"
version = "7.1.5"
if version_file.exists():
    with version_file.open("r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("__version__"):
                version = line.split("=")[1].strip().strip('"').strip("'")
                break

setup(
    name="email-processor",
    version=version,
    author="Vladimir Kholodilin",
    author_email="vkholodilin@example.com",
    description="Email attachment processor with IMAP support - Downloads attachments, organizes by topic, and archives messages",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/vkholodilin/python-email-automation-processor",
    project_urls={
        "Bug Reports": "https://github.com/vkholodilin/python-email-automation-processor/issues",
        "Source": "https://github.com/vkholodilin/python-email-automation-processor",
        "Documentation": "https://github.com/vkholodilin/python-email-automation-processor#readme",
    },
    packages=find_packages(),
    install_requires=[
        "pyyaml>=6.0",
        "keyring>=24.0",
        "structlog>=24.0.0",
        "tqdm>=4.66.0",
    ],
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "email-processor=email_processor.__main__:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Communications :: Email",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Utilities",
    ],
    keywords=["email", "imap", "attachment", "processor", "automation", "email-processing"],
)
