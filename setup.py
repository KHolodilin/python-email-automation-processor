"""Setup script for email-processor package.

This file is kept for backward compatibility with older pip versions (Python 3.9+).
All package metadata is defined in pyproject.toml.
"""

import site
from pathlib import Path
from typing import Union

from setuptools import setup
from setuptools.command.develop import develop


class DevelopCommand(develop):
    """Override develop command to avoid calling pip."""

    def run(self) -> None:
        """Run the develop command without calling pip."""
        # Call parent's run but skip the pip install step
        install_dir: Union[str, None] = getattr(self, "install_dir", None)
        if install_dir is None:
            # Use default install directory
            install_cmd = self.get_finalized_command("install")
            install_dir = getattr(install_cmd, "install_lib", None)
            if install_dir is None:
                # Fallback to site-packages
                install_dir = site.getsitepackages()[0] if site.getsitepackages() else "."

        install_dir_path = Path(install_dir).resolve()
        self.install_dir = str(install_dir_path)
        self.egg_path = install_dir_path / f"{self.distribution.get_name()}.egg-link"
        self.egg_base = str(install_dir_path)
        self.ensure_target_dir()
        self.egg_info = self.distribution.get_command_obj("egg_info")
        self.egg_info.egg_base = self.egg_base
        self.egg_info.egg_name = self.distribution.get_name()
        self.egg_info.egg_version = self.distribution.get_version()
        self.egg_info.run()
        self.install_egg_info()
        self.install_scripts()
        self.create_distutils_lib()


# Minimal setup.py - all configuration is in pyproject.toml
# This file exists only for backward compatibility with Python 3.9+
setup(
    cmdclass={"develop": DevelopCommand},
)
