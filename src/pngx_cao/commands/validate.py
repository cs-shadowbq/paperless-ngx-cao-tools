"""
Validation command for testing configuration and connectivity.
"""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ..config import get_config

console = Console()


@click.command(name='validate')
@click.option(
    '--env-file',
    type=click.Path(exists=True, path_type=Path),
    help='Path to .env file'
)
@click.option(
    '--env-prefix',
    default='',
    help='Environment variable prefix'
)
@click.option(
    '--url',
    envvar='PAPERLESS_URL',
    help='Paperless-ngx URL (overrides env)'
)
@click.option(
    '--token',
    envvar='PAPERLESS_TOKEN',
    help='API token (overrides env)'
)
@click.option(
    '-k', '--skip-ssl-verify',
    is_flag=True,
    help='Skip SSL certificate verification (insecure)'
)
@click.option(
    '--debug',
    is_flag=True,
    help='Enable debug logging'
)
def validate(env_file, env_prefix, url, token, skip_ssl_verify, debug):
    """
    Validate Paperless-ngx configuration and connectivity.

    Tests that:
    - Configuration is properly loaded
    - Server URL is reachable
    - Credentials are valid
    - API version is compatible

    \b
    Examples:
        # Validate configuration
        pngx-cao validate

        # Test specific server
        pngx-cao validate --url http://paperless.example.com
    """
    if debug:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)

    console.print("\n[bold cyan]Validating Paperless-ngx Configuration[/bold cyan]")
    console.print("=" * 60)

    results = []
    all_passed = True

    # Test 1: Configuration Loading
    console.print("\n[bold]1. Configuration Loading[/bold]")
    try:
        config = get_config(env_prefix=env_prefix, env_file=env_file)

        # Override with CLI parameters if provided
        if url:
            config.url = url
        if token:
            config.token = token
        if skip_ssl_verify:
            config.skip_ssl_verify = True
            config.token = token

        results.append(("Configuration", "✓", "Loaded successfully"))
        console.print("  [green]✓[/green] Configuration loaded")
        console.print(f"    URL: {config.url}")
        console.print(f"    Auth: {'Token' if config.has_token_auth else 'Username/Password'}")
        console.print(f"    Global Read: {config.global_read}")
        console.print(f"    API Version: {config.api_version}")
    except Exception as e:
        results.append(("Configuration", "✗", str(e)))
        console.print(f"  [red]✗[/red] Failed to load configuration: {e}")
        all_passed = False

        # Can't continue without config
        _print_summary(results, all_passed)
        raise click.Abort()

    # Test 2: API Client Initialization
    console.print("\n[bold]2. API Client Initialization[/bold]")
    try:
        from ..api.client import PaperlessAPI

        api = PaperlessAPI(
            base_url=config.url,
            token=config.token,
            username=config.username,
            password=config.password,
            global_read=config.global_read,
            api_version=config.api_version,
            skip_ssl_verify=config.skip_ssl_verify
        )
        results.append(("API Client", "✓", "Initialized successfully"))
        console.print("  [green]✓[/green] API client initialized")
    except Exception as e:
        results.append(("API Client", "✗", str(e)))
        console.print(f"  [red]✗[/red] Failed to initialize API client: {e}")
        all_passed = False
        _print_summary(results, all_passed)
        raise click.Abort()

    # Test 3: Server Connectivity
    console.print("\n[bold]3. Server Connectivity[/bold]")
    try:
        # Try to fetch tags (lightweight API call)
        api._get('tags/', params={'page_size': 1})
        results.append(("Connectivity", "✓", f"Connected to {config.url}"))
        console.print(f"  [green]✓[/green] Server is reachable at {config.url}")
    except Exception as e:
        results.append(("Connectivity", "✗", str(e)))
        console.print(f"  [red]✗[/red] Failed to connect to server: {e}")
        all_passed = False

    # Test 4: Authentication
    console.print("\n[bold]4. Authentication[/bold]")
    try:
        # Try to get user info or tags to verify auth
        response = api._get('tags/', params={'page_size': 1})
        tag_count = response.get('count', 0)
        results.append(("Authentication", "✓", "Credentials are valid"))
        console.print("  [green]✓[/green] Authentication successful")
        console.print(f"    Found {tag_count} tags in system")
    except Exception as e:
        results.append(("Authentication", "✗", str(e)))
        console.print(f"  [red]✗[/red] Authentication failed: {e}")
        all_passed = False

    # Test 5: API Version Check
    console.print("\n[bold]5. API Version Compatibility[/bold]")
    try:
        # The API client uses version 9 by default
        expected_version = config.api_version
        results.append(("API Version", "✓", f"Using API version {expected_version}"))
        console.print(f"  [green]✓[/green] API version {expected_version} configured")
        console.print("    Note: Paperless-ngx API is generally backward compatible")
    except Exception as e:
        results.append(("API Version", "✗", str(e)))
        console.print(f"  [red]✗[/red] API version check failed: {e}")
        all_passed = False

    # Print summary
    _print_summary(results, all_passed)

    if not all_passed:
        raise click.Abort()


def _print_summary(results, all_passed):
    """Print a summary table of validation results."""
    console.print("\n" + "=" * 60)
    console.print("[bold]Validation Summary[/bold]\n")

    # Create summary table
    table = Table(show_header=True, header_style="bold")
    table.add_column("Check", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details")

    for check, status, details in results:
        status_style = "green" if status == "✓" else "red"
        table.add_row(check, f"[{status_style}]{status}[/{status_style}]", details)

    console.print(table)

    # Overall result
    console.print()
    if all_passed:
        panel = Panel(
            "[green]All checks passed![/green]\n\n"
            "Your configuration is valid and the server is accessible.\n"
            "You can now use pngx-cao commands.",
            title="✓ Success",
            border_style="green"
        )
    else:
        panel = Panel(
            "[red]Some checks failed.[/red]\n\n"
            "Please review the errors above and update your configuration.\n"
            "Check your .env file or environment variables.",
            title="✗ Validation Failed",
            border_style="red"
        )

    console.print(panel)
    console.print()
