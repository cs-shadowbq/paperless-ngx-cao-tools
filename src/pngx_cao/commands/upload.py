"""
Upload command group for document management.
"""

import logging
from pathlib import Path

import click
from rich.console import Console

from ..services.upload import UploadService
from ..services.watcher import WatcherService, FolderStabilizer
from ..cli_utils import create_api_client

console = Console()
logger = logging.getLogger(__name__)


@click.group(name='upload')
def upload():
    """
    Upload CrowdStrike CAO reports to Paperless-ngx.

    Process and upload PDF documents with metadata from JSON files.
    """
    pass


@upload.command(name='batch')
@click.argument(
    'originals-dir',
    type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@click.option(
    '--folder',
    help='Process only this specific folder by name'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Process folders but do not actually upload'
)
@click.option(
    '--duplicate-handling',
    type=click.Choice(['skip', 'replace', 'update-metadata'], case_sensitive=False),
    default='skip',
    help='How to handle duplicate documents: skip (default), replace (delete & re-upload), or update-metadata (update tags/metadata only)'
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
def batch_upload(originals_dir, folder, dry_run, duplicate_handling, env_file, env_prefix, url, token, skip_ssl_verify, debug):
    """
    Upload documents from originals directory.

    Each folder in the originals directory should contain:
    - A PDF file (e.g., CSIT-14004.pdf)
    - A JSON metadata file with the same name (e.g., CSIT-14004.json)

    The JSON file should contain CrowdStrike CAO report data with taxonomy
    information that will be mapped to Paperless-ngx tags.

    \b
    Duplicate Handling:
    - skip: If a document with the same title exists, skip uploading (default)
    - replace: Delete the existing document and upload the new version
    - update-metadata: Keep the existing file, but update tags and metadata

    \b
    Examples:
        # Upload all documents in originals directory
        pngx-cao upload batch ./originals

        # Upload only a specific folder
        pngx-cao upload batch ./originals --folder CSIT-14004

        # Replace existing documents with new versions
        pngx-cao upload batch ./originals --duplicate-handling replace

        # Test without actually uploading
        pngx-cao upload batch ./originals --dry-run
    """
    if debug:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)

    if dry_run:
        console.print("[yellow]DRY RUN MODE[/yellow] - No documents will be uploaded\n")

    # Create API client
    api = create_api_client(
        url=url,
        token=token,
        skip_ssl_verify=skip_ssl_verify,
        env_file=env_file,
        env_prefix=env_prefix
    )

    # Create service and upload
    service = UploadService(api, console, duplicate_handling=duplicate_handling)

    console.print("[bold cyan]Uploading Documents[/bold cyan]")
    console.print("=" * 60)

    stats = service.upload_batch(
        originals_dir=originals_dir,
        folder_filter=folder,
        dry_run=dry_run
    )

    # Exit with error if all uploads failed
    if stats['uploaded'] == 0 and stats['failed'] > 0:
        raise click.Abort()


@upload.command(name='folder')
@click.argument(
    'folder-path',
    type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Process folder but do not actually upload'
)
@click.option(
    '--duplicate-handling',
    type=click.Choice(['skip', 'replace', 'update-metadata'], case_sensitive=False),
    default='skip',
    help='How to handle duplicate documents: skip (default), replace (delete & re-upload), or update-metadata (update tags/metadata only)'
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
def upload_folder(folder_path, dry_run, duplicate_handling, env_file, env_prefix, url, token, skip_ssl_verify, debug):
    """
    Upload a single document folder.

    The folder should contain:
    - A PDF file (e.g., CSIT-14004.pdf)
    - A JSON metadata file with the same name (e.g., CSIT-14004.json)

    \b
    Duplicate Handling:
    - skip: If a document with the same title exists, skip uploading (default)
    - replace: Delete the existing document and upload the new version
    - update-metadata: Keep the existing file, but update tags and metadata

    \b
    Examples:
        # Upload a single folder
        pngx-cao upload folder ./originals/CSIT-14004

        # Replace existing document
        pngx-cao upload folder ./originals/CSIT-14004 --duplicate-handling replace

        # Test without actually uploading
        pngx-cao upload folder ./originals/CSIT-14004 --dry-run
    """
    if debug:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)

    if dry_run:
        console.print("[yellow]DRY RUN MODE[/yellow] - Document will not be uploaded\n")

    # Create API client
    api = create_api_client(
        url=url,
        token=token,
        skip_ssl_verify=skip_ssl_verify,
        env_file=env_file,
        env_prefix=env_prefix
    )

    # Create service and upload
    service = UploadService(api, console, duplicate_handling=duplicate_handling)

    console.print("[bold cyan]Uploading Document[/bold cyan]")
    console.print("=" * 60)

    result = service.process_folder(folder_path, dry_run=dry_run)

    if result and not result.get('skipped'):
        if not dry_run:
            # Update permissions
            console.print("\n[bold]Updating document permissions...[/bold]")
            stats = api.update_document_permissions_batch([result])
            console.print(
                f"  Updated: {stats['updated']} | "
                f"Not found: {stats['not_found']} | "
                f"Failed: {stats['failed']}"
            )
        console.print("\n[green]✓ Upload complete![/green]")
    elif result and result.get('skipped'):
        console.print("\n[yellow]Skipped (dry run)[/yellow]")
    else:
        console.print("\n[red]✗ Upload failed[/red]")
        raise click.Abort()


@upload.command(name='watch')
@click.argument(
    'originals-dir',
    type=click.Path(exists=True, file_okay=False, path_type=Path)
)
@click.option(
    '--poll-interval',
    type=float,
    default=5.0,
    help='Seconds between directory scans (default: 5.0)'
)
@click.option(
    '--stability-wait',
    type=float,
    default=2.0,
    help='Seconds to wait for folder stability before uploading (default: 2.0)'
)
@click.option(
    '--duplicate-handling',
    type=click.Choice(['skip', 'replace', 'update-metadata'], case_sensitive=False),
    default='skip',
    help='How to handle duplicate documents: skip (default), replace (delete & re-upload), or update-metadata (update tags/metadata only)'
)
@click.option(
    '--env-file',
    type=click.Path(exists=True, path_type=Path),
    help='Path to .env file'
)
@click.option(
    '--env-prefix',
    help='Environment variable prefix'
)
@click.option(
    '--url',
    help='Paperless-ngx URL (overrides env)'
)
@click.option(
    '--token',
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
def watch(
    originals_dir: Path,
    poll_interval: float,
    stability_wait: float,
    duplicate_handling: str,
    env_file: Path,
    env_prefix: str,
    url: str,
    token: str,
    skip_ssl_verify: bool,
    debug: bool
):
    """
    Watch a directory for new document folders and upload them automatically.

    This command monitors ORIGINALS-DIR for new folders and automatically
    uploads them when they're ready. Useful for automated workflows.

    The watcher will:
    - Scan for new folders every POLL_INTERVAL seconds
    - Wait for folders to stabilize (no file changes for STABILITY_WAIT seconds)
    - Upload documents using the same logic as the 'folder' command
    - Continue running until interrupted (Ctrl+C)

    \b
    Examples:
        # Watch directory with default settings
        pngx-cao upload watch ./originals

        # Watch with faster polling and custom duplicate handling
        pngx-cao upload watch ./originals --poll-interval 2 --duplicate-handling replace

        # Watch with longer stability wait for slow extractions
        pngx-cao upload watch ./originals --stability-wait 5
    """
    if debug:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    # Create API client
    api = create_api_client(
        url=url,
        token=token,
        skip_ssl_verify=skip_ssl_verify,
        env_file=env_file,
        env_prefix=env_prefix
    )

    # Create upload service
    upload_service = UploadService(api, console, duplicate_handling=duplicate_handling)

    # Create upload callback
    def upload_callback(folder_path: Path) -> bool:
        """
        Callback for uploading a folder.

        Args:
            folder_path: Path to the folder to upload

        Returns:
            True if upload succeeded, False otherwise
        """
        try:
            result = upload_service.process_folder(folder_path, dry_run=False)

            if result and not result.get('skipped'):
                # Update permissions
                console.print(f"[dim]Updating permissions for {folder_path.name}...[/dim]")
                stats = api.update_document_permissions_batch([result])
                logger.debug(
                    f"Permissions updated - "
                    f"Updated: {stats['updated']}, "
                    f"Not found: {stats['not_found']}, "
                    f"Failed: {stats['failed']}"
                )
                console.print(f"[green]✓ Successfully uploaded: {folder_path.name}[/green]\n")
                return True
            elif result and result.get('skipped'):
                console.print(f"[yellow]⊘ Skipped (already exists): {folder_path.name}[/yellow]\n")
                return True
            else:
                console.print(f"[red]✗ Upload failed: {folder_path.name}[/red]\n")
                return False

        except Exception as e:
            console.print(f"[red]✗ Error uploading {folder_path.name}: {e}[/red]\n")
            logger.exception(f"Upload error for {folder_path.name}")
            return False

    # Create stabilizer and watcher
    stabilizer = FolderStabilizer(
        stability_wait=stability_wait,
        check_interval=0.5
    )

    watcher = WatcherService(
        watch_dir=originals_dir,
        upload_callback=upload_callback,
        stabilizer=stabilizer,
        poll_interval=poll_interval
    )

    # Display startup information
    console.print("[bold cyan]Document Watcher Started[/bold cyan]")
    console.print("=" * 60)
    console.print(f"[bold]Watching:[/bold] {originals_dir}")
    console.print(f"[bold]Poll interval:[/bold] {poll_interval}s")
    console.print(f"[bold]Stability wait:[/bold] {stability_wait}s")
    console.print(f"[bold]Duplicate handling:[/bold] {duplicate_handling}")
    console.print("=" * 60)
    console.print("\n[yellow]Press Ctrl+C to stop watching[/yellow]\n")

    # Start watching
    try:
        watcher.start()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Watcher stopped by user[/yellow]")
        console.print(f"[dim]Processed {watcher.get_processed_count()} folder(s)[/dim]")
    except Exception as e:
        console.print(f"\n\n[red]Watcher error: {e}[/red]")
        logger.exception("Watcher error")
        raise click.Abort()
