"""System fingerprint generation for encryption key derivation."""

import hashlib
import os
import platform
import socket
import sys
import uuid
from pathlib import Path
from typing import Optional

from email_processor.logging.setup import get_logger


def get_mac_address() -> Optional[str]:
    """Get MAC address of first active network interface.

    Returns:
        MAC address as string, or None if not available
    """
    try:
        mac = uuid.getnode()
        if mac:
            return f"{mac:012x}"
    except Exception:
        pass
    return None


def get_hostname() -> str:
    """Get system hostname.

    Returns:
        Hostname string
    """
    try:
        return socket.gethostname()
    except Exception:
        return "unknown"


def get_user_id() -> str:
    """Get user identifier.

    Returns:
        User ID string (Windows SID, Linux UID, or username)
    """
    try:
        if platform.system() == "Windows":
            # Try to get Windows SID (requires pywin32, but it's optional)
            try:
                import win32security

                try:
                    user = win32security.GetTokenInformation(
                        win32security.OpenProcessToken(
                            win32security.GetCurrentProcess(), win32security.TOKEN_QUERY
                        ),
                        win32security.TokenUser,
                    )
                    return str(user[0].Sid)
                except Exception:
                    # Fallback to username
                    pass
            except ImportError:
                # pywin32 not available, fallback to username
                pass
            # Fallback to username
            return os.getenv("USERNAME", os.getenv("USER", "unknown"))
        else:
            # Linux/Unix: use UID if available
            getuid = getattr(os, "getuid", None)
            if getuid is not None:
                try:
                    return str(getuid())
                except Exception:
                    pass
            # Fallback to username
            return os.getenv("USERNAME", os.getenv("USER", "unknown"))
    except Exception:
        # Fallback to username
        return os.getenv("USERNAME", os.getenv("USER", "unknown"))


def get_config_path_hash(config_path: Optional[str] = None) -> str:
    """Get hash of config file path for installation binding.

    Args:
        config_path: Optional path to config file. If None, uses default.

    Returns:
        SHA256 hash of config path
    """
    path_str = str(Path(config_path).resolve()) if config_path else str(Path.cwd().resolve())

    return hashlib.sha256(path_str.encode("utf-8")).hexdigest()[:16]


def get_system_fingerprint(config_path: Optional[str] = None) -> str:
    """Generate unique system fingerprint from system characteristics.

    Combines:
    - MAC address of first network interface
    - Hostname
    - User ID (SID/UID)
    - Config file path hash
    - Python version

    Args:
        config_path: Optional path to config file for binding

    Returns:
        SHA256 hash of combined system characteristics
    """
    logger = get_logger()
    components = []

    # MAC address
    mac = get_mac_address()
    if mac:
        components.append(f"mac:{mac}")
        logger.debug("fingerprint_component", component="mac_address", value=mac[:8] + "...")
    else:
        logger.warning("fingerprint_mac_unavailable")

    # Hostname
    hostname = get_hostname()
    components.append(f"hostname:{hostname}")
    logger.debug("fingerprint_component", component="hostname", value=hostname)

    # User ID
    user_id = get_user_id()
    components.append(f"user:{user_id}")
    logger.debug(
        "fingerprint_component",
        component="user_id",
        value=user_id[:16] + "..." if len(user_id) > 16 else user_id,
    )

    # Config path hash
    config_hash = get_config_path_hash(config_path)
    components.append(f"config:{config_hash}")
    logger.debug("fingerprint_component", component="config_path", value=config_hash)

    # Python version (for stability)
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    components.append(f"python:{python_version}")

    # Combine and hash
    combined = "|".join(components)
    fingerprint = hashlib.sha256(combined.encode("utf-8")).hexdigest()

    logger.debug(
        "fingerprint_generated",
        fingerprint=fingerprint[:16] + "...",
        components_count=len(components),
    )
    return fingerprint
