"""Script to run all tests with coverage."""

import subprocess
import sys

if __name__ == "__main__":
    # Run pytest with coverage
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/",
        "-v",
        "--cov=email_processor",
        "--cov-report=term-missing",
        "--cov-report=html",
        "--cov-fail-under=95",
    ]

    result = subprocess.run(cmd, check=False)
    sys.exit(result.returncode)
