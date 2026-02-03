"""
Keywords service for managing keywords on actor tags.

This service handles the business logic for adding/removing keywords
from actor tag names by modifying the parenthetical keywords section.
"""

import csv
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Set

from rich.console import Console
from rich.table import Table

from ..api.client import PaperlessAPI

logger = logging.getLogger(__name__)


class KeywordsService:
    """Service for managing keywords on actor tags."""

    def __init__(self, api: PaperlessAPI, console: Console = None):
        """
        Initialize the keywords service.

        Args:
            api: PaperlessAPI client
            console: Rich console for output (optional)
        """
        self.api = api
        self.console = console or Console()

    @staticmethod
    def parse_tag_name(tag_name: str) -> tuple[str, Set[str]]:
        """
        Parse a tag name to extract the base name and existing keywords.

        Args:
            tag_name: Tag name like "HYPER BASALISK" or "HYPER BASALISK (inactive, retired)"

        Returns:
            Tuple of (base_name, set_of_keywords)
        """
        # Match pattern: "BASE NAME (keyword1, keyword2)"
        match = re.match(r'^(.+?)\s*(?:\(([^)]+)\))?$', tag_name.strip())
        if not match:
            return tag_name.strip(), set()

        base_name = match.group(1).strip()
        keywords_str = match.group(2)

        if keywords_str:
            # Split by comma and clean up whitespace
            keywords = {kw.strip() for kw in keywords_str.split(',') if kw.strip()}
            return base_name, keywords

        return base_name, set()

    @staticmethod
    def build_tag_name(base_name: str, keywords: Set[str]) -> str:
        """
        Build a tag name from base name and keywords.

        Args:
            base_name: Base tag name (e.g., "HYPER BASALISK")
            keywords: Set of keywords

        Returns:
            Full tag name with keywords in parentheses
        """
        if not keywords:
            return base_name

        # Sort keywords for consistent ordering
        sorted_keywords = sorted(keywords)
        keywords_str = ', '.join(sorted_keywords)
        return f"{base_name} ({keywords_str})"

    def update_tag_keywords(
        self,
        tag_name: str,
        add_keywords: Optional[List[str]] = None,
        remove_keywords: Optional[List[str]] = None,
        dry_run: bool = False
    ) -> Optional[Dict]:
        """
        Update keywords for a specific tag.

        Args:
            tag_name: Current tag name (can include or exclude keywords)
            add_keywords: List of keywords to add
            remove_keywords: List of keywords to remove
            dry_run: If True, only show what would change

        Returns:
            Dict with old_name and new_name if changed, None if no change needed

        Raises:
            ValueError: If tag not found
        """
        # Parse the input tag name to get base name
        base_name, _ = self.parse_tag_name(tag_name)

        # Find the tag (this handles normalization for actor tags)
        tag = self.api.get_tag_by_name(base_name, normalize_for_actor=True)
        if not tag:
            raise ValueError(f"Tag not found: {base_name}")

        # Parse the actual tag name from the API
        current_base_name, current_keywords = self.parse_tag_name(tag['name'])

        # Build new keyword set
        new_keywords = current_keywords.copy()

        if add_keywords:
            new_keywords.update(add_keywords)

        if remove_keywords:
            new_keywords.difference_update(remove_keywords)

        # Build new tag name
        new_tag_name = self.build_tag_name(current_base_name, new_keywords)

        # Check if anything changed
        if new_tag_name == tag['name']:
            self.console.print(f"  [dim]No change needed for: {tag['name']}[/dim]")
            return None

        # Display the change
        self.console.print(f"  {tag['name']} → {new_tag_name}")

        if not dry_run:
            # Update the tag
            self.api.update_tag(tag['id'], {'name': new_tag_name})
            self.console.print(f"  [green]✓[/green] Updated tag ID {tag['id']}")

        return {
            'old_name': tag['name'],
            'new_name': new_tag_name,
            'tag_id': tag['id']
        }

    def add_keywords_from_csv(
        self,
        csv_file: Path,
        dry_run: bool = False
    ) -> Dict[str, int]:
        """
        Add keywords to tags from a CSV file.

        Args:
            csv_file: Path to CSV file with columns: Name, Keywords
            dry_run: If True, only show what would change

        Returns:
            Statistics dict with updated/skipped/not_found/failed counts
        """
        self.console.print(f"\n[bold cyan]Processing keywords from CSV:[/bold cyan] {csv_file}")

        stats = {
            'updated': 0,
            'skipped': 0,
            'not_found': 0,
            'failed': 0
        }

        # Read CSV file
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except Exception as e:
            raise ValueError(f"Failed to read CSV file: {e}")

        if not rows:
            self.console.print("[yellow]No rows found in CSV file[/yellow]")
            return stats

        # Create a table to display changes
        table = Table(title=f"Keywords to Add{' (Dry Run)' if dry_run else ''}")
        table.add_column("Actor Tag", style="cyan")
        table.add_column("Keywords to Add", style="yellow")
        table.add_column("Status", style="green")

        for row in rows:
            tag_name = row.get('Name', '').strip()
            keywords_str = row.get('Keywords', '').strip()

            if not tag_name:
                self.console.print("[yellow]  Skipping row with empty Name[/yellow]")
                stats['skipped'] += 1
                continue

            if not keywords_str:
                self.console.print(f"[yellow]  Skipping {tag_name}: no keywords specified[/yellow]")
                stats['skipped'] += 1
                continue

            # Parse keywords from CSV
            keywords_to_add = [kw.strip() for kw in keywords_str.split(',') if kw.strip()]

            try:
                result = self.update_tag_keywords(
                    tag_name,
                    add_keywords=keywords_to_add,
                    dry_run=dry_run
                )

                if result:
                    stats['updated'] += 1
                    table.add_row(
                        tag_name,
                        ', '.join(keywords_to_add),
                        "Would update" if dry_run else "Updated"
                    )
                else:
                    stats['skipped'] += 1
                    table.add_row(
                        tag_name,
                        ', '.join(keywords_to_add),
                        "No change"
                    )

            except ValueError as e:
                logger.error(f"Error processing {tag_name}: {e}")
                stats['not_found'] += 1
                table.add_row(
                    tag_name,
                    ', '.join(keywords_to_add),
                    "[red]Not found[/red]"
                )
            except Exception as e:
                logger.error(f"Failed to update {tag_name}: {e}")
                stats['failed'] += 1
                table.add_row(
                    tag_name,
                    ', '.join(keywords_to_add),
                    "[red]Failed[/red]"
                )

        # Display the table
        self.console.print("\n")
        self.console.print(table)

        return stats
