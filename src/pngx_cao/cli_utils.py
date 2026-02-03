"""
Common utilities for CLI commands.
"""

import sys
from pathlib import Path

from rich.console import Console

from .config import get_config, DOTENV_AVAILABLE
from .api.client import PaperlessAPI

console = Console()


def create_api_client(
    url: str = None,
    token: str = None,
    skip_ssl_verify: bool = None,
    env_file: Path = None,
    env_prefix: str = ''
) -> PaperlessAPI:
    """
    Create and return a configured PaperlessAPI client.

    Args:
        url: Optional URL override
        token: Optional token override
        skip_ssl_verify: Optional SSL verification override
        env_file: Optional path to .env file
        env_prefix: Optional environment variable prefix

    Returns:
        Configured PaperlessAPI instance

    Raises:
        SystemExit: If configuration is invalid
    """
    try:
        # Load config from environment
        config = get_config(env_prefix=env_prefix, env_file=env_file)

        # Override with CLI parameters if provided
        if url:
            config.url = url
        if token:
            config.token = token
        if skip_ssl_verify is not None:
            config.skip_ssl_verify = skip_ssl_verify

        # Display connection info
        auth_method = "token" if config.has_token_auth else "username/password"
        ssl_warning = " [yellow](SSL verification disabled)[/yellow]" if config.skip_ssl_verify else ""
        console.print(f"[dim]Connecting to {config.url} using {auth_method}{ssl_warning}[/dim]")

        return PaperlessAPI(
            base_url=config.url,
            token=config.token,
            username=config.username,
            password=config.password,
            global_read=config.global_read,
            api_version=config.api_version,
            skip_ssl_verify=config.skip_ssl_verify
        )
    except ValueError as e:
        console.print(f"[red]Configuration Error:[/red] {e}")
        if not DOTENV_AVAILABLE:
            console.print(
                "\n[yellow]Tip:[/yellow] Install python-dotenv to use .env files: "
                "[cyan]pip install python-dotenv[/cyan]"
            )
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to initialize API client: {e}")
        import logging
        logging.exception("API client initialization failed")
        sys.exit(1)
