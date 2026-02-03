"""
Upload service for processing and uploading documents to Paperless-ngx.

This service handles the business logic for uploading CrowdStrike CAO
intelligence reports with metadata.
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from ..api.client import PaperlessAPI
from ..utils.constants import (
    is_actor_tag,
    extract_animal_from_actor,
    get_actor_animals_from_csv,
    TAXONOMIES,
)

logger = logging.getLogger(__name__)


class UploadService:
    """Service for uploading documents with metadata."""

    def __init__(self, api: PaperlessAPI, console: Console = None, duplicate_handling: str = "skip"):
        """
        Initialize the upload service.

        Args:
            api: PaperlessAPI client
            console: Rich console for output (optional)
            duplicate_handling: How to handle duplicates: 'skip', 'replace', or 'update-metadata'
        """
        self.api = api
        self.console = console or Console()
        self.duplicate_handling = duplicate_handling

    def process_crowdstrike_metadata(self, metadata: dict) -> Dict[str, any]:
        """
        Extract relevant fields from CrowdStrike CAO report metadata.

        Args:
            metadata: Parsed JSON metadata from CrowdStrike

        Returns:
            Dictionary with extracted fields
        """
        extracted = {
            'title': metadata.get('name', ''),
            'url': metadata.get('url', ''),
            'description': metadata.get('short_description', ''),
            'document_type_slug': None,
            'created_timestamp': None,
            'created_date': None,
            'tag_names': [],
            'actor_names': []  # Track actors separately
        }

        # Extract document type from type->slug
        if 'type' in metadata and isinstance(metadata['type'], dict):
            extracted['document_type_slug'] = metadata['type'].get('slug')

        # Extract created date (Unix timestamp to YYYY-MM-DD)
        if 'created_date' in metadata:
            try:
                timestamp = metadata['created_date']
                dt = datetime.fromtimestamp(timestamp)
                extracted['created_date'] = dt.strftime('%Y-%m-%d')
                extracted['created_timestamp'] = timestamp
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing created_date: {e}")

        # Extract actors as tags (track separately as actors)
        if 'actors' in metadata and isinstance(metadata['actors'], list):
            for actor in metadata['actors']:
                if isinstance(actor, dict) and 'name' in actor:
                    actor_name = actor['name']
                    extracted['tag_names'].append(actor_name)
                    extracted['actor_names'].append(actor_name)  # Track as actor

        # Extract target industries as tags
        if 'target_industries' in metadata and isinstance(metadata['target_industries'], list):
            for industry in metadata['target_industries']:
                if isinstance(industry, dict):
                    industry_name = industry.get('value') or industry.get('name')
                    if industry_name:
                        extracted['tag_names'].append(industry_name)
                elif isinstance(industry, str):
                    extracted['tag_names'].append(industry)

        # Extract target countries as tags
        if 'target_countries' in metadata and isinstance(metadata['target_countries'], list):
            for country in metadata['target_countries']:
                if isinstance(country, dict):
                    country_name = country.get('value') or country.get('name')
                    if country_name:
                        extracted['tag_names'].append(country_name)
                elif isinstance(country, str):
                    extracted['tag_names'].append(country)

        # Extract motivations as tags
        if 'motivations' in metadata and isinstance(metadata['motivations'], list):
            for motivation in metadata['motivations']:
                if isinstance(motivation, dict):
                    motivation_name = motivation.get('value') or motivation.get('name')
                    if motivation_name:
                        extracted['tag_names'].append(motivation_name)
                elif isinstance(motivation, str):
                    extracted['tag_names'].append(motivation)

        return extracted

    def find_or_create_animal_parent_tag(self, animal_name: str) -> Optional[int]:
        """
        Find or create the animal parent tag (e.g., BASALISK, UNICORN).
        If the animal tag doesn't exist, it will be created with 'Actor' as its parent.

        Args:
            animal_name: Name of the animal

        Returns:
            Tag ID or None if creation failed
        """
        # First try to find existing animal tag
        tag = self.api.get_tag_by_name(animal_name)
        if tag:
            return tag['id']

        # Animal tag doesn't exist, need to create it under the Actor parent
        logger.info(f"Animal tag '{animal_name}' not found, creating with Actor parent")

        # Get the Actor parent tag ID from taxonomy config
        actor_parent_id = TAXONOMIES.get('actor', {}).get('parent_id')
        child_color = TAXONOMIES.get('actor', {}).get('child_color', '#8338ec')

        if not actor_parent_id:
            logger.error("Actor parent ID not found in TAXONOMIES config")
            return None

        # Ensure Actor parent exists (it should, but let's verify)
        actor_tag = self.api.get_tag_by_id(actor_parent_id)
        if not actor_tag:
            # Try to find by name
            actor_tag = self.api.get_tag_by_name('Actor')
            if actor_tag:
                actor_parent_id = actor_tag['id']
            else:
                logger.warning(f"Actor parent tag (ID {actor_parent_id}) not found, creating animal tag without parent")
                actor_parent_id = None

        # Create the animal tag with Actor as parent
        try:
            animal_tag = self.api.create_tag(
                name=animal_name,
                color=child_color,
                is_inbox_tag=False,
                matching_algorithm=self.api.MATCH_NONE,
                parent=actor_parent_id
            )
            logger.info(f"Created animal tag '{animal_name}' (ID: {animal_tag['id']}) with Actor parent")
            return animal_tag['id']
        except Exception as e:
            logger.error(f"Failed to create animal tag '{animal_name}': {e}")
            return None

    def process_folder(
        self,
        folder_path: Path,
        dry_run: bool = False
    ) -> Optional[dict]:
        """
        Process a single folder containing a PDF and its metadata.

        Args:
            folder_path: Path to the folder
            dry_run: If True, don't actually upload

        Returns:
            Upload result dict or None if failed
        """
        self.console.print(f"\n[bold]Processing:[/bold] {folder_path.name}")

        # Find PDF file
        pdf_files = list(folder_path.glob("*.pdf"))
        if not pdf_files:
            self.console.print("  [yellow]⚠[/yellow] No PDF file found")
            return None

        if len(pdf_files) > 1:
            self.console.print(
                f"  [yellow]⚠[/yellow] Multiple PDFs found, using {pdf_files[0].name}"
            )

        pdf_file = pdf_files[0]
        base_name = pdf_file.stem

        # Check if PDF file is empty (zero bytes)
        if pdf_file.stat().st_size == 0:
            self.console.print("  [yellow]⚠[/yellow] PDF file is empty (0 bytes), skipping")
            logger.warning(f"Skipping empty PDF file: {pdf_file}")
            return {'skipped': True, 'reason': 'empty_file'}

        # Find corresponding JSON file (not .meta.json)
        json_file = folder_path / f"{base_name}.json"
        if not json_file.exists():
            self.console.print("  [yellow]⚠[/yellow] No metadata JSON found, uploading without metadata")
            if not dry_run:
                return self.api.upload_document(pdf_file, title=base_name)
            return {'skipped': True}

        # Load and process metadata
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except json.JSONDecodeError as e:
            self.console.print(f"  [red]✗[/red] Error parsing JSON: {e}")
            return None

        extracted = self.process_crowdstrike_metadata(metadata)

        # Build title with URL reference
        title = extracted['title']
        if extracted['url']:
            title = f"{title} - {extracted['url']}"

        # Display metadata
        self.console.print(f"  [bold]Title:[/bold] {extracted['title']}")
        self.console.print(f"  [bold]Date:[/bold] {extracted['created_date']}")
        self.console.print(f"  [bold]Type:[/bold] {extracted['document_type_slug']}")
        self.console.print(f"  [bold]Tags:[/bold] {len(extracted['tag_names'])} tags")

        if dry_run:
            self.console.print("  [cyan]DRY RUN[/cyan] - Would upload with above metadata")
            return {'skipped': True}

        # Get or create document type
        document_type_id = None
        if extracted['document_type_slug']:
            try:
                document_type_id = self.api.get_or_create_document_type(
                    extracted['document_type_slug']
                )
            except Exception as e:
                logger.error(f"Error creating document type: {e}")

        # Get or create tags
        tag_ids = []

        for tag_name in extracted['tag_names']:
            try:
                # Check if this tag came from the actors JSON section
                is_actor = tag_name in extracted['actor_names']
                animal_parent_id = None
                animal_color = None

                if is_actor:
                    animal = extract_animal_from_actor(tag_name)
                    if animal:
                        # This now creates the animal tag if it doesn't exist
                        animal_parent_id = self.find_or_create_animal_parent_tag(animal)
                        if not animal_parent_id:
                            logger.warning(f"Failed to get/create animal parent '{animal}' for '{tag_name}'")
                        else:
                            # Get the animal parent tag to inherit its color
                            animal_tag = self.api.get_tag_by_id(animal_parent_id)
                            if animal_tag:
                                animal_color = animal_tag.get('color')
                                logger.debug(f"Inheriting color {animal_color} from animal parent '{animal}'")

                tag_id = self.api.get_or_create_tag(
                    tag_name,
                    color=animal_color,  # Pass the animal's color
                    is_actor=is_actor,
                    animal_parent_id=animal_parent_id
                )
                tag_ids.append(tag_id)
            except Exception as e:
                logger.error(f"Error processing tag '{tag_name}': {e}")

        # Generate archive serial number from report name using hash
        # disable bandit B324 as this is not security hash only for ID generation

        archive_serial_number = int(
            hashlib.md5(base_name.encode()).hexdigest()[:7], 16  # nosec: B324
        )

        # Check for duplicate document
        existing_doc = self.api.get_document_by_title(title)
        if existing_doc:
            doc_id = existing_doc['id']

            if self.duplicate_handling == "skip":
                self.console.print(f"  [yellow]⊘[/yellow] Duplicate found (ID: {doc_id}), skipping")
                return {'skipped': True, 'reason': 'duplicate', 'document_id': doc_id}

            elif self.duplicate_handling == "replace":
                self.console.print(f"  [yellow]⟳[/yellow] Duplicate found (ID: {doc_id}), replacing...")
                try:
                    self.api.delete_document(doc_id)
                    self.console.print("    Deleted old document")
                    self.api.empty_trash()
                    self.console.print("    Emptied trash")
                except Exception as e:
                    self.console.print(f"  [red]✗[/red] Failed to delete duplicate: {e}")
                    return None

            elif self.duplicate_handling == "update-metadata":
                self.console.print(f"  [yellow]⟳[/yellow] Duplicate found (ID: {doc_id}), updating metadata...")
                try:
                    update_data = {
                        'tags': tag_ids,
                        'created_date': extracted['created_date']
                    }
                    if document_type_id:
                        update_data['document_type'] = document_type_id

                    self.api.update_document(doc_id, update_data)
                    self.console.print("  [green]✓[/green] Metadata updated")
                    # Return document_id for permissions update
                    return {
                        'updated': True,
                        'document_id': doc_id,
                        'search_term': title  # Used for permissions tracking
                    }
                except Exception as e:
                    self.console.print(f"  [red]✗[/red] Failed to update metadata: {e}")
                    logger.error(f"Error updating document: {e}", exc_info=True)
                    return None

        # Upload document
        try:
            result = self.api.upload_document(
                file_path=pdf_file,
                title=title,
                created_date=extracted['created_date'],
                tag_ids=tag_ids,
                document_type_id=document_type_id,
                archive_serial_number=archive_serial_number
            )
            self.console.print("  [green]✓[/green] Upload successful")
            return result
        except Exception as e:
            self.console.print(f"  [red]✗[/red] Upload failed: {e}")
            logger.error(f"Error uploading document: {e}", exc_info=True)
            return None

    def upload_batch(
        self,
        originals_dir: Path,
        folder_filter: Optional[str] = None,
        dry_run: bool = False
    ) -> dict:
        """
        Upload a batch of documents from originals directory.

        Args:
            originals_dir: Directory containing document folders
            folder_filter: Optional specific folder name to process
            dry_run: If True, don't actually upload

        Returns:
            Statistics dict with counts
        """
        if not originals_dir.exists():
            self.console.print(f"[red]Error:[/red] Directory not found: {originals_dir}")
            return {"uploaded": 0, "failed": 0, "skipped": 0}

        # Get folders to process
        if folder_filter:
            folders = [originals_dir / folder_filter]
            if not folders[0].exists() or not folders[0].is_dir():
                self.console.print(f"[red]Error:[/red] Folder not found: {folders[0]}")
                return {"uploaded": 0, "failed": 0, "skipped": 0}
        else:
            folders = [d for d in originals_dir.iterdir() if d.is_dir()]

        if not folders:
            self.console.print(f"[yellow]No folders found in {originals_dir}[/yellow]")
            return {"uploaded": 0, "failed": 0, "skipped": 0}

        # Display summary table
        table = Table(title=f"Found {len(folders)} folder(s) to process")
        table.add_column("Folder", style="cyan")
        table.add_column("Status", style="green")

        for folder in sorted(folders[:10]):  # Show first 10
            table.add_row(folder.name, "Ready")

        if len(folders) > 10:
            table.add_row("...", f"and {len(folders) - 10} more")

        self.console.print(table)

        # Process folders
        upload_results = []
        failed_count = 0
        skipped_count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task(
                "Processing documents...",
                total=len(folders)
            )

            for folder in folders:
                result = self.process_folder(folder, dry_run=dry_run)

                if result:
                    if result.get('skipped'):
                        skipped_count += 1
                    else:
                        upload_results.append(result)
                else:
                    failed_count += 1

                progress.advance(task)

        # Batch update permissions
        if upload_results and not dry_run:
            self.console.print("\n[bold]Updating document permissions...[/bold]")
            stats = self.api.update_document_permissions_batch(upload_results)

            self.console.print(
                f"  Updated: {stats['updated']} | "
                f"Not found: {stats['not_found']} | "
                f"Failed: {stats['failed']}"
            )

        # Summary
        summary_table = Table(title="Upload Summary")
        summary_table.add_column("Status", style="bold")
        summary_table.add_column("Count", justify="right")

        summary_table.add_row("Uploaded", str(len(upload_results)), style="green")
        summary_table.add_row("Failed", str(failed_count), style="red")
        summary_table.add_row("Skipped", str(skipped_count), style="yellow")

        self.console.print("\n")
        self.console.print(summary_table)

        return {
            "uploaded": len(upload_results),
            "failed": failed_count,
            "skipped": skipped_count
        }
