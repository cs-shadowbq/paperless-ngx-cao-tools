"""
Configuration management for pngx-cao.

Handles loading configuration from environment variables and .env files.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


@dataclass
class PaperlessConfig:
    """Configuration for Paperless-ngx connection."""

    url: str
    token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    global_read: bool = False
    api_version: int = 9
    skip_ssl_verify: bool = False
    duplicate_handling: str = "skip"
    data_dir: str = "./data"
    originals_dir: str = "./originals"

    def __post_init__(self):
        """Validate configuration."""
        if not self.url:
            raise ValueError("PAPERLESS_URL must be set")

        if not self.token and not (self.username and self.password):
            raise ValueError(
                "Either PAPERLESS_TOKEN or PAPERLESS_USERNAME/PASSWORD must be set"
            )

    @property
    def has_token_auth(self) -> bool:
        """Check if token authentication is configured."""
        return bool(self.token)

    @property
    def has_basic_auth(self) -> bool:
        """Check if basic authentication is configured."""
        return bool(self.username and self.password)


def load_env_file(env_file: Optional[Path] = None) -> bool:
    """
    Load environment variables from .env file.

    Args:
        env_file: Path to .env file. If None, looks in current directory and parent.

    Returns:
        True if file was loaded, False otherwise
    """
    if not DOTENV_AVAILABLE:
        return False

    if env_file and env_file.exists():
        load_dotenv(env_file)
        return True

    # Try current directory
    current_env = Path.cwd() / ".env"
    if current_env.exists():
        load_dotenv(current_env)
        return True

    # Try parent directory (for development when running from src/)
    parent_env = Path.cwd().parent / ".env"
    if parent_env.exists():
        load_dotenv(parent_env)
        return True

    return False


def get_config(env_prefix: str = "", env_file: Optional[Path] = None) -> PaperlessConfig:
    """
    Load Paperless-ngx configuration from environment.

    Args:
        env_prefix: Optional prefix for environment variables (e.g., "BOX1_")
        env_file: Optional path to .env file

    Returns:
        PaperlessConfig instance

    Raises:
        ValueError: If required configuration is missing
    """
    # Load .env file if available
    load_env_file(env_file)

    def get_env(key: str, default: str = "") -> str:
        """Get environment variable with optional prefix."""
        prefixed_key = f"{env_prefix}{key}"
        return os.environ.get(prefixed_key, os.environ.get(key, default))

    # Parse global_read setting (default: false for owner-restricted access)
    global_read_str = get_env("PAPERLESS_GLOBAL_READ", "false").strip().lower()
    global_read = global_read_str in ('true', '1', 'yes', 'on')

    # Parse skip_ssl_verify setting (default: false for security)
    skip_ssl_str = get_env("PAPERLESS_SKIP_SSL_VERIFY", "false").strip().lower()
    skip_ssl_verify = skip_ssl_str in ('true', '1', 'yes', 'on')

    # Parse duplicate_handling setting (default: skip)
    duplicate_handling = get_env("PAPERLESS_DUPLICATE_HANDLING", "skip").strip().lower()
    if duplicate_handling not in ('skip', 'replace', 'update-metadata'):
        duplicate_handling = 'skip'

    # Get directory paths (default: ./data and ./originals)
    data_dir = get_env("PAPERLESS_DATA_DIR", "./data")
    originals_dir = get_env("PAPERLESS_ORIGINALS_DIR", "./originals")

    return PaperlessConfig(
        url=get_env("PAPERLESS_URL"),
        token=get_env("PAPERLESS_TOKEN"),
        username=get_env("PAPERLESS_USERNAME"),
        password=get_env("PAPERLESS_PASSWORD"),
        global_read=global_read,
        api_version=int(get_env("PAPERLESS_API_VERSION", "9")),
        skip_ssl_verify=skip_ssl_verify,
        duplicate_handling=duplicate_handling,
        data_dir=data_dir,
        originals_dir=originals_dir
    )
