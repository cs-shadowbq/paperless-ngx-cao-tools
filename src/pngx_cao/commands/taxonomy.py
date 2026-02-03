"""
Taxonomy command group for managing hierarchical tags.
"""

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from ..utils.constants import TAXONOMIES, get_data_dir
from ..services.taxonomy import TaxonomyService
from ..cli_utils import create_api_client

console = Console()


@click.group(name='taxonomy')
def taxonomy():
    """
    Manage hierarchical taxonomy tags in Paperless-ngx.

    Create, list, and validate taxonomy structures from CSV files.
    """
    pass


@taxonomy.command(name='create')
@click.option(
    '--taxonomy', '-t',
    type=click.Choice(list(TAXONOMIES.keys()) + ['all'], case_sensitive=False),
    default='all',
    help='Which taxonomy to create (default: all)'
)
@click.option(
    '--data-dir',
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help='Directory containing CSV files (default: ./data)'
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
def create_taxonomy(taxonomy, data_dir, env_file, env_prefix, url, token, skip_ssl_verify, debug):
    """
    Create hierarchical tags from CSV files.

    \b
    Creates tag hierarchies for:
    - Actors (3-tier: Actors -> Animal -> Individual Actor)
    - Motivations (2-tier: Motivations -> Type)
    - Targeted Countries (2-tier: Countries -> Country)
    - Targeted Industries (2-tier: Industries -> Industry)

    \b
    Examples:
        # Create all taxonomies
        pngx-cao taxonomy create --all

        # Create only actor taxonomy
        pngx-cao taxonomy create -t actor

        # Use custom data directory
        pngx-cao taxonomy create --data-dir /path/to/data
    """
    if debug:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)

    # Get data directory
    try:
        data_dir = get_data_dir(data_dir)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

    console.print(f"[dim]Using data directory: {data_dir}[/dim]\n")

    # Create API client
    api = create_api_client(
        url=url,
        token=token,
        skip_ssl_verify=skip_ssl_verify,
        env_file=env_file,
        env_prefix=env_prefix
    )

    # Create service and process taxonomies
    service = TaxonomyService(api, console)

    console.print("[bold cyan]Creating Taxonomy Tags[/bold cyan]")
    console.print("=" * 60)

    stats = service.create_taxonomies(
        taxonomy_filter=taxonomy,
        data_dir=data_dir
    )

    # Display overall summary
    console.print("\n" + "=" * 60)
    console.print("[bold]Overall Summary:[/bold]")

    summary_table = Table(show_header=False, box=None)
    summary_table.add_column("Label", style="bold")
    summary_table.add_column("Count", justify="right")

    summary_table.add_row("Created", str(stats['created']), style="green")
    summary_table.add_row("Skipped (existing)", str(stats['skipped']), style="yellow")
    summary_table.add_row("Failed", str(stats['failed']), style="red")
    summary_table.add_row("Total processed", str(stats['total']), style="cyan")

    console.print(summary_table)
    console.print("=" * 60)

    if stats['created'] > 0:
        api_config = api.base_url
        console.print(
            f"\n[green]✓[/green] Tags created successfully! "
            f"View them at:\n  {api_config}/admin/documents/tag/"
        )


@taxonomy.command(name='list')
@click.option(
    '--data-dir',
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help='Directory containing CSV files (default: ./data or PAPERLESS_DATA_DIR)'
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
def list_taxonomies(data_dir, env_file, env_prefix):
    """
    List available taxonomies (local CSV files check only).

    Shows what taxonomies can be created based on local CSV files.
    Does NOT connect to Paperless-ngx server.
    Use 'pngx-cao taxonomy remote' to check server status.
    """
    # Get data directory
    try:
        data_dir = get_data_dir(data_dir, env_file=env_file, env_prefix=env_prefix)
    except FileNotFoundError as e:
        console.print(f"[yellow]Warning:[/yellow] {e}")
        console.print("[dim]Showing available taxonomies (CSV files not checked)[/dim]\n")
        data_dir = None

    # Create table
    table = Table(title="Available Taxonomies (Local CSV Files)")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("CSV File", style="yellow")
    table.add_column("Description", style="dim")
    table.add_column("Status", style="green")

    for name, config in TAXONOMIES.items():
        csv_file = config['csv_file']
        description = config.get('description', '')

        # Check if CSV file exists
        status = "✓" if data_dir and (data_dir / csv_file).exists() else "?"
        status_style = "green" if status == "✓" else "yellow"

        table.add_row(
            name,
            csv_file,
            description,
            f"[{status_style}]{status}[/{status_style}]",
            style=None if status == "✓" else "dim"
        )

    console.print(table)

    if data_dir:
        console.print(f"\n[dim]Data directory: {data_dir}[/dim]")

    console.print(
        "\n[bold]Usage:[/bold] "
        "[cyan]pngx-cao taxonomy create -t <name>[/cyan] or "
        "[cyan]pngx-cao taxonomy create --all[/cyan]"
    )

    console.print(
        "\n[dim]Note: This is a local check only. "
        "Use [cyan]pngx-cao taxonomy remote[/cyan] to check server status.[/dim]"
    )


@taxonomy.command(name='remote')
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
def remote_taxonomies(env_file, env_prefix, url, token, skip_ssl_verify, debug):
    """
    Check taxonomy status on remote Paperless-ngx server.

    Shows how many tags exist for each taxonomy on the server.
    """
    import logging
    from collections import defaultdict

    if debug:
        logging.basicConfig(level=logging.DEBUG)

    console.print("[bold]Checking remote taxonomy status...[/bold]\n")

    # Create API client
    api = create_api_client(
        url=url,
        token=token,
        skip_ssl_verify=skip_ssl_verify,
        env_file=env_file,
        env_prefix=env_prefix
    )

    # Get all tags from server
    try:
        all_tags = api.get_all_tags()
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to fetch tags from server: {e}")
        raise click.Abort()

    if not all_tags:
        console.print("[yellow]No tags found on server[/yellow]")
        return

    # Build parent lookup for hierarchical checking
    parent_lookup = {}
    for tag_name, tag_data in all_tags.items():
        tag_id = tag_data.get('id')
        parent_id = tag_data.get('parent')
        if tag_id:
            parent_lookup[tag_id] = parent_id

    # Helper function to get all ancestors of a tag
    def get_ancestors(tag_data):
        ancestors = []
        parent_id = tag_data.get('parent')
        while parent_id:
            # Find parent tag
            for name, data in all_tags.items():
                if data.get('id') == parent_id:
                    ancestors.append(name)
                    parent_id = data.get('parent')
                    break
            else:
                break
        return ancestors

    # Categorize tags by taxonomy
    taxonomy_counts = defaultdict(list)
    uncategorized = []

    # Get actor animals from tags
    from ..utils.csv_reader import get_actor_animals_from_tags
    actor_animals = get_actor_animals_from_tags(all_tags.keys())

    # Build sets of root taxonomy names for faster checking
    actors_root = {'ACTORS'}
    motivations_root = {'MOTIVATIONS'}
    countries_root = {'TARGETED COUNTRIES', 'TARGETED_COUNTRIES'}
    industries_root = {'TARGETED INDUSTRIES', 'TARGETED_INDUSTRIES'}

    for tag_name, tag_data in all_tags.items():
        tag_upper = tag_name.upper()
        ancestors = [a.upper() for a in get_ancestors(tag_data)]
        categorized = False

        # Check Actors taxonomy
        if tag_upper in actors_root or 'ACTORS' in ancestors or tag_name in actor_animals:
            taxonomy_counts['Actors'].append(tag_data)
            categorized = True
        # Check Motivations taxonomy
        elif tag_upper in motivations_root or 'MOTIVATIONS' in ancestors:
            taxonomy_counts['Motivations'].append(tag_data)
            categorized = True
        # Check Targeted Countries taxonomy
        elif tag_upper in countries_root or 'TARGETED COUNTRIES' in ancestors or 'TARGETED_COUNTRIES' in ancestors:
            taxonomy_counts['Targeted Countries'].append(tag_data)
            categorized = True
        # Check Targeted Industries taxonomy
        elif tag_upper in industries_root or 'TARGETED INDUSTRIES' in ancestors or 'TARGETED_INDUSTRIES' in ancestors:
            taxonomy_counts['Targeted Industries'].append(tag_data)
            categorized = True

        if not categorized:
            uncategorized.append(tag_data)

    # Create table
    table = Table(title="Remote Taxonomy Status")
    table.add_column("Taxonomy", style="cyan", no_wrap=True)
    table.add_column("Tags on Server", style="green", justify="right")
    table.add_column("Sample Tags", style="dim")

    for taxonomy_name in ['Actors', 'Motivations', 'Targeted Countries', 'Targeted Industries']:
        tags = taxonomy_counts.get(taxonomy_name, [])
        count = len(tags)

        # Get sample tag names (up to 3)
        samples = [tag['name'] for tag in tags[:3]]
        sample_str = ', '.join(samples)
        if count > 3:
            sample_str += f" (+{count - 3} more)"

        style = "green" if count > 0 else "dim"
        table.add_row(
            taxonomy_name,
            str(count),
            sample_str if sample_str else "(none)",
            style=style
        )

    console.print(table)
    console.print(f"\n[dim]Total tags on server: {len(all_tags)}[/dim]")

    if uncategorized:
        console.print(f"[dim]Uncategorized tags: {len(uncategorized)}[/dim]")


@taxonomy.command(name='validate')
@click.option(
    '--data-dir',
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help='Directory containing CSV files (default: ./data or PAPERLESS_DATA_DIR)'
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
def validate_taxonomies(data_dir, env_file, env_prefix):
    """
    Validate CSV files and check for issues.

    Checks that all required CSV files exist and are readable.
    """
    # Get data directory
    try:
        data_dir = get_data_dir(data_dir, env_file=env_file, env_prefix=env_prefix)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise click.Abort()

    console.print(f"[bold]Validating taxonomies in:[/bold] {data_dir}\n")

    from ..utils.csv_reader import read_csv_values, read_actors_with_animals

    all_valid = True

    for name, config in TAXONOMIES.items():
        csv_path = data_dir / config['csv_file']

        console.print(f"[cyan]{name}[/cyan]: {config['csv_file']}")

        if not csv_path.exists():
            console.print(f"  [red]✗[/red] File not found: {csv_path}")
            all_valid = False
            continue

        try:
            if name == "actor":
                data = read_actors_with_animals(csv_path)
                total_actors = sum(len(actors) for actors in data.values())
                console.print(
                    f"  [green]✓[/green] Valid: {total_actors} actors in "
                    f"{len(data)} animal groups"
                )
            else:
                data = read_csv_values(csv_path)
                console.print(f"  [green]✓[/green] Valid: {len(data)} values")
        except Exception as e:
            console.print(f"  [red]✗[/red] Error reading file: {e}")
            all_valid = False

    console.print()
    if all_valid:
        console.print("[green]✓ All taxonomies are valid![/green]")
    else:
        console.print("[red]✗ Some taxonomies have issues[/red]")
        raise click.Abort()
