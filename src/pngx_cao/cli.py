"""
Main CLI entry point for pngx-cao.

Uses Click for command-line interface with subcommands.
"""

from .commands import keywords, taxonomy, upload, validate
import logging
import sys

import click
from rich.console import Console
from rich.logging import RichHandler

from . import __version__


# Set up rich logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, show_path=False)]
)

logger = logging.getLogger(__name__)
console = Console()


@click.group()
@click.version_option(version=__version__, prog_name='pngx-cao')
@click.pass_context
def cli(ctx):
    """
    pngx-cao: Paperless-ngx tools for CrowdStrike Falcon CAO Intel Reports.

    A command-line tool for managing hierarchical taxonomy tags and uploading
    CrowdStrike threat intelligence documents to Paperless-ngx.

    \b
    Examples:
        # Create all taxonomies from CSV files
        pnValidate configuration and connectivity
        pngx-cao validate

        # gx-cao taxonomy create --all

        # Upload documents from originals directory
        pngx-cao upload batch ./originals

        # Upload a single document folder
        pngx-cao upload folder ./originals/CSIT-14004

    Environment variables:
        PAPERLESS_URL              Paperless-ngx base URL
        PAPERLESS_TOKEN            API token (preferred)
        PAPERLESS_USERNAME         Username for basic auth
        PAPERLESS_PASSWORD         Password for basic auth
        PAPERLESS_GLOBAL_READ      Set to 'false' to set ownership (default: true)
        ENV_PREFIX                 Prefix for all env vars (e.g., "BOX1_")
    """
    # Ensure context object exists
    ctx.ensure_object(dict)


cli.add_command(validate.validate)

# Import and register command groups

cli.add_command(keywords.keywords)
cli.add_command(taxonomy.taxonomy)
cli.add_command(upload.upload)


def main():
    """Main entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]Unexpected error:[/red] {e}")
        logger.exception("Unexpected error occurred")
        sys.exit(1)


if __name__ == '__main__':
    main()
