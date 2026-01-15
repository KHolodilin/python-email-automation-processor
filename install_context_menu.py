"""Script to generate Windows context menu registry file."""

import sys
from pathlib import Path

# Get paths
script_dir = Path(__file__).parent.absolute()
python_exe = sys.executable
main_script = script_dir / "email_processor" / "__main__.py"


def generate_reg_file(output_path: Path) -> None:
    """Generate .reg file for Windows context menu."""
    # Escape backslashes for registry
    python_exe_escaped = str(python_exe).replace("\\", "\\\\")
    main_script_escaped = str(main_script).replace("\\", "\\\\")

    reg_content = f"""Windows Registry Editor Version 5.00

[HKEY_CURRENT_USER\\Software\\Classes\\*\\shell\\SendViaEmail]
@="Отправить по email"
"Icon"="{python_exe_escaped}"

[HKEY_CURRENT_USER\\Software\\Classes\\*\\shell\\SendViaEmail\\command]
@="{python_exe_escaped} \\"{main_script_escaped}\\" --send-file \\"%1\\""
"""

    output_path.write_text(reg_content, encoding="utf-16")
    print(f"Registry file generated: {output_path}")
    print("\nTo install:")
    print(f"  1. Double-click {output_path.name}")
    print("  2. Confirm the registry merge")
    print("\nTo uninstall, delete the registry keys:")
    print("  HKEY_CURRENT_USER\\Software\\Classes\\*\\shell\\SendViaEmail")


if __name__ == "__main__":
    output_file = script_dir / "install_context_menu.reg"
    generate_reg_file(output_file)
