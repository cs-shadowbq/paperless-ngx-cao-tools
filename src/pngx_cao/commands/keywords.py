"""
Keywords command group for managing keywords on actor tags.

Adds or removes keywords from actor tags by appending them in parentheses.
For example: "HYPER BASALISK" becomes "HYPER BASALISK (inactive, retired)"
"""

from pathlib import Path

import click
from rich.console import Console

from ..services.keywords import KeywordsService
from ..cli_utils import create_api_client

console = Console()


@click.group(name='keywords')
def keywords():
    """
    Manage keywords on actor tags.

    Add or remove keywords from actor tags by appending them in parentheses.
    Keywords are added to the tag name, e.g., "HYPER BASALISK (inactive, retired)".
    """
    pass


@keywords.command(name='add-from-csv')
@click.argument(
    'csv_file',
    type=click.Path(exists=True, path_type=Path),
)
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
@click.option(
    '--dry-run',
    is_flag=True,
    help='Show what would be changed without making actual changes'
)
def add_from_csv(csv_file, env_file, env_prefix, url, token, skip_ssl_verify, debug, dry_run):
    """
    Add keywords to actor tags from a CSV file.

    The CSV file should have two columns: "Name" and "Keywords"
    - Name: The actor tag name (e.g., "HYPER BASALISK")
    - Keywords: Comma-separated keywords to add (e.g., "inactive, retired")

    \b
    Examples:
        # Add keywords from CSV file
        pngx-cao keywords add-from-csv data/inactive.csv

        # Dry run to see what would change
        pngx-cao keywords add-from-csv data/inactive.csv --dry-run
    """
    if debug:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)

    # Create API client
    api = create_api_client(
        env_file=env_file,
        env_prefix=env_prefix,
        url=url,
        token=token,
        skip_ssl_verify=skip_ssl_verify
    )

    # Create keywords service
    service = KeywordsService(api, console)

    # Process CSV file
    try:
        stats = service.add_keywords_from_csv(csv_file, dry_run=dry_run)

        # Display summary
        console.print("\n[bold]Summary:[/bold]")
        console.print(f"  Updated: {stats['updated']}")
        console.print(f"  Skipped: {stats['skipped']}")
        console.print(f"  Not found: {stats['not_found']}")
        console.print(f"  Failed: {stats['failed']}")

        if dry_run:
            console.print("\n[yellow]Note: This was a dry run. No changes were made.[/yellow]")

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        raise click.Abort()


@keywords.command(name='add')
@click.argument('tag_name')
@click.option(
    '--add-keywords', '-a',
    multiple=True,
    help='Keywords to add (can be specified multiple times)'
)
@click.option(
    '--remove-keywords', '-r',
    multiple=True,
    help='Keywords to remove (can be specified multiple times)'
)
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
@click.option(
    '--dry-run',
    is_flag=True,
    help='Show what would be changed without making actual changes'
)
def add_keywords(tag_name, add_keywords, remove_keywords, env_file, env_prefix, url, token,
                 skip_ssl_verify, debug, dry_run):
    """
    Add or remove keywords from a specific actor tag.

    Provide the tag name and keywords to add or remove. Keywords are managed
    in parentheses appended to the tag name.

    \b
    Examples:
        # Add keywords to a tag
        pngx-cao keywords add "HYPER BASALISK" -a inactive -a retired

        # Remove a keyword
        pngx-cao keywords add "HYPER BASALISK" -r inactive

        # Add and remove in one command
        pngx-cao keywords add "HYPER BASALISK" -a dormant -r inactive

        # Dry run to see what would change
        pngx-cao keywords add "HYPER BASALISK" -a inactive --dry-run
    """
    if debug:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)

    if not add_keywords and not remove_keywords:
        console.print("[red]Error:[/red] You must specify at least one keyword to add or remove")
        console.print("Use -a/--add-keywords or -r/--remove-keywords")
        raise click.Abort()

    # Create API client
    api = create_api_client(
        env_file=env_file,
        env_prefix=env_prefix,
        url=url,
        token=token,
        skip_ssl_verify=skip_ssl_verify
    )

    # Create keywords service
    service = KeywordsService(api, console)

    # Process tag
    try:
        result = service.update_tag_keywords(
            tag_name,
            add_keywords=list(add_keywords),
            remove_keywords=list(remove_keywords),
            dry_run=dry_run
        )

        if result:
            console.print(f"\n[green]✓[/green] Successfully updated tag: {result['old_name']} → {result['new_name']}")
        else:
            console.print(f"\n[yellow]No changes needed for tag: {tag_name}[/yellow]")

        if dry_run:
            console.print("[yellow]Note: This was a dry run. No changes were made.[/yellow]")

    except ValueError as e:
        console.print(f"\n[red]Error:[/red] {e}")
        raise click.Abort()
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        raise click.Abort()
