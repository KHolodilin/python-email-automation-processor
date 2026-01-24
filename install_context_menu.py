"""Script to generate Windows context menu registry file for 'Send via email'."""

import argparse
import sys
from pathlib import Path
from typing import Optional

# Paths
SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = "config.yaml"
DEFAULT_RECIPIENT_PLACEHOLDER = "REPLACE_WITH_YOUR_EMAIL"


def generate_reg_file(output_path: Path, to_email: str, config_path: Optional[Path]) -> None:
    """Generate .reg file for Windows context menu.

    Invokes: python -m email_processor send file "%1" --to <to> [--config <path>].
    """
    python_exe = sys.executable
    parts = [
        f'"{python_exe}"',
        "-m",
        "email_processor",
        "send",
        "file",
        '"%1"',
        "--to",
        f'"{to_email}"',
    ]
    if config_path and config_path.exists():
        parts.extend(["--config", f'"{config_path}"'])
    cmd = " ".join(parts)
    # Registry: escape backslashes then quotes for the command string value
    cmd_reg = cmd.replace("\\", "\\\\").replace('"', '\\"')
    python_escaped = str(python_exe).replace("\\", "\\\\")

    reg_content = f"""Windows Registry Editor Version 5.00

[HKEY_CURRENT_USER\\Software\\Classes\\*\\shell\\SendViaEmail]
@="Send via email"
"Icon"="{python_escaped}"

[HKEY_CURRENT_USER\\Software\\Classes\\*\\shell\\SendViaEmail\\command]
@="{cmd_reg}"
"""

    output_path.write_text(reg_content, encoding="utf-16")
    print(f"Registry file generated: {output_path}")
    print("\nTo install:")
    print(
        f"  1. Edit {output_path.name} and set the correct recipient (--to) if you used a placeholder."
    )
    print(f"  2. Double-click {output_path.name}")
    print("  3. Confirm the registry merge.")
    print("\nTo uninstall, delete the registry keys:")
    print("  HKEY_CURRENT_USER\\Software\\Classes\\*\\shell\\SendViaEmail")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Windows context menu .reg for 'Send via email' (send file)."
    )
    parser.add_argument(
        "--to",
        type=str,
        default=DEFAULT_RECIPIENT_PLACEHOLDER,
        help=f"Recipient email for 'send file'. Default: {DEFAULT_RECIPIENT_PLACEHOLDER} (edit .reg before install).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to config.yaml. Default: project config.yaml next to this script.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output .reg path. Default: install_context_menu.reg in script directory.",
    )
    args = parser.parse_args()

    config_path = args.config if args.config is not None else (SCRIPT_DIR / CONFIG_FILE)
    output_path = args.output or (SCRIPT_DIR / "install_context_menu.reg")
    generate_reg_file(output_path, args.to, config_path)

    if args.to == DEFAULT_RECIPIENT_PLACEHOLDER:
        print(
            f"\nNote: Recipient is set to '{DEFAULT_RECIPIENT_PLACEHOLDER}'. Edit the .reg file and replace it before installing."
        )


if __name__ == "__main__":
    main()
