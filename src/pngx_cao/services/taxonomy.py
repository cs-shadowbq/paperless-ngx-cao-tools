"""
Taxonomy service for creating and managing hierarchical tags.

This service handles the business logic for creating tag hierarchies
in Paperless-ngx from CSV files.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..api.client import PaperlessAPI
from ..utils.constants import TAXONOMIES, COLOR_PALETTE
from ..utils.csv_reader import read_csv_values, read_actors_with_animals

logger = logging.getLogger(__name__)


class TaxonomyService:
    """Service for managing taxonomy tags."""

    def __init__(self, api: PaperlessAPI, console: Console = None):
        """
        Initialize the taxonomy service.

        Args:
            api: PaperlessAPI client
            console: Rich console for output (optional)
        """
        self.api = api
        self.console = console or Console()

    def ensure_parent_tag(
        self,
        taxonomy_name: str,
        taxonomy_config: dict
    ) -> Optional[int]:
        """
        Ensure the parent tag exists, return its ID.

        Args:
            taxonomy_name: Name of the taxonomy
            taxonomy_config: Configuration dict with parent_id and parent_color

        Returns:
            Parent tag ID or None if failed
        """
        parent_id = taxonomy_config["parent_id"]
        parent_color = taxonomy_config["parent_color"]

        # First check if tag with expected ID exists
        tag = self.api.get_tag_by_id(parent_id)
        if tag and tag["name"].lower() == taxonomy_name.lower():
            self.console.print(
                f"  [green]✓[/green] Parent tag '{taxonomy_name}' found with ID {tag['id']}"
            )
            return tag["id"]

        # Search for tag by name
        tag = self.api.get_tag_by_name(taxonomy_name)
        if tag:
            self.console.print(
                f"  [green]✓[/green] Parent tag '{taxonomy_name}' found with ID {tag['id']}"
            )
            return tag["id"]

        # Create the parent tag
        self.console.print(f"  Creating parent tag '{taxonomy_name}'...")
        tag = self.api.create_tag(
            taxonomy_name,
            color=parent_color,
            is_inbox_tag=False,
            matching_algorithm=self.api.MATCH_NONE,
            parent=None
        )

        if tag:
            self.console.print(
                f"  [green]✓[/green] Created parent tag '{taxonomy_name}' (ID: {tag['id']})"
            )
            return tag["id"]

        return None

    def create_actor_taxonomy(
        self,
        taxonomy_name: str,
        taxonomy_config: dict,
        data_dir: Path,
        existing_tags: Dict[str, dict]
    ) -> dict:
        """
        Create actor taxonomy with 3-tier hierarchy: Actors -> Animal -> Actor.

        Args:
            taxonomy_name: Name of the taxonomy
            taxonomy_config: Configuration dict
            data_dir: Path to data directory
            existing_tags: Dict of existing tags (name -> tag data)

        Returns:
            Statistics dict with created/skipped/failed counts
        """
        self.console.print(f"\n[bold cyan]Processing taxonomy: {taxonomy_name}[/bold cyan]")
        self.console.print(f"[dim]{taxonomy_config.get('description', '')}[/dim]")

        # Ensure parent tag exists
        parent_id = self.ensure_parent_tag(taxonomy_name, taxonomy_config)
        if not parent_id:
            self.console.print(
                f"  [red]✗[/red] Failed to create parent tag for '{taxonomy_name}'"
            )
            return {"created": 0, "skipped": 0, "failed": 0, "total": 0}

        # Read actors grouped by animal
        csv_path = data_dir / "actors.csv"
        if not csv_path.exists():
            self.console.print(f"  [red]✗[/red] CSV file not found: {csv_path}")
            return {"created": 0, "skipped": 0, "failed": 0, "total": 0}

        actors_by_animal = read_actors_with_animals(csv_path)

        if not actors_by_animal:
            self.console.print("  [yellow]No actors found in CSV[/yellow]")
            return {"created": 0, "skipped": 0, "failed": 0, "total": 0}

        total_actors = sum(len(actors) for actors in actors_by_animal.values())
        self.console.print(
            f"  Found {total_actors} actors in {len(actors_by_animal)} animal groups"
        )

        # Create tags with progress tracking
        created_count = 0
        skipped_count = 0
        failed_count = 0

        # Assign colors to animals deterministically
        sorted_animals = sorted(actors_by_animal.keys())
        animal_color_map = {
            animal: COLOR_PALETTE[idx % len(COLOR_PALETTE)]
            for idx, animal in enumerate(sorted_animals)
        }

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True
        ) as progress:
            progress.add_task("Creating tags...", total=None)

            for animal, actors in sorted(actors_by_animal.items()):
                animal_color = animal_color_map[animal]

                # Create or find animal tag
                animal_tag_id = None
                if animal.upper() in existing_tags:
                    animal_tag_id = existing_tags[animal.upper()]['id']
                    skipped_count += 1
                else:
                    try:
                        animal_tag = self.api.create_tag(
                            animal,
                            color=animal_color,
                            is_inbox_tag=False,
                            matching_algorithm=self.api.MATCH_LITERAL,
                            parent=parent_id,
                            match=animal
                        )
                        animal_tag_id = animal_tag['id']
                        created_count += 1
                    except Exception as e:
                        logger.error(f"Failed to create animal tag '{animal}': {e}")
                        failed_count += 1
                        continue

                # Create actor tags under this animal
                for actor in sorted(actors):
                    if actor.upper() in existing_tags:
                        skipped_count += 1
                        continue

                    try:
                        self.api.create_tag(
                            actor,
                            color=animal_color,
                            is_inbox_tag=False,
                            matching_algorithm=self.api.MATCH_LITERAL,
                            parent=animal_tag_id,
                            match=actor
                        )
                        created_count += 1
                    except Exception as e:
                        logger.error(f"Failed to create actor tag '{actor}': {e}")
                        failed_count += 1

        total_items = len(actors_by_animal) + total_actors

        return {
            "created": created_count,
            "skipped": skipped_count,
            "failed": failed_count,
            "total": total_items
        }

    def create_simple_taxonomy(
        self,
        taxonomy_name: str,
        taxonomy_config: dict,
        data_dir: Path,
        existing_tags: Dict[str, dict]
    ) -> dict:
        """
        Create a simple 2-tier taxonomy: Parent -> Children.

        Args:
            taxonomy_name: Name of the taxonomy
            taxonomy_config: Configuration dict
            data_dir: Path to data directory
            existing_tags: Dict of existing tags (name -> tag data)

        Returns:
            Statistics dict with created/skipped/failed counts
        """
        self.console.print(f"\n[bold cyan]Processing taxonomy: {taxonomy_name}[/bold cyan]")
        self.console.print(f"[dim]{taxonomy_config.get('description', '')}[/dim]")

        # Ensure parent tag exists
        parent_id = self.ensure_parent_tag(taxonomy_name, taxonomy_config)
        if not parent_id:
            self.console.print(
                f"  [red]✗[/red] Failed to create parent tag for '{taxonomy_name}'"
            )
            return {"created": 0, "skipped": 0, "failed": 0, "total": 0}

        # Read values from CSV
        csv_path = data_dir / taxonomy_config["csv_file"]
        if not csv_path.exists():
            self.console.print(f"  [red]✗[/red] CSV file not found: {csv_path}")
            return {"created": 0, "skipped": 0, "failed": 0, "total": 0}

        values = read_csv_values(csv_path)

        if not values:
            self.console.print("  [yellow]No values found in CSV[/yellow]")
            return {"created": 0, "skipped": 0, "failed": 0, "total": 0}

        self.console.print(f"  Found {len(values)} values in CSV")

        # Create tags with progress tracking
        created_count = 0
        skipped_count = 0
        failed_count = 0
        child_color = taxonomy_config["child_color"]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True
        ) as progress:
            progress.add_task("Creating tags...", total=None)

            for value in values:
                if value.upper() in existing_tags:
                    skipped_count += 1
                    continue

                try:
                    self.api.create_tag(
                        value,
                        color=child_color,
                        is_inbox_tag=False,
                        matching_algorithm=self.api.MATCH_LITERAL,
                        parent=parent_id,
                        match=value
                    )
                    created_count += 1
                except Exception as e:
                    logger.error(f"Failed to create tag '{value}': {e}")
                    failed_count += 1

        return {
            "created": created_count,
            "skipped": skipped_count,
            "failed": failed_count,
            "total": len(values)
        }

    def create_taxonomies(
        self,
        taxonomy_filter: str = "all",
        data_dir: Path = None
    ) -> dict:
        """
        Create one or all taxonomies.

        Args:
            taxonomy_filter: Which taxonomy to create ("all" or specific name)
            data_dir: Path to data directory

        Returns:
            Overall statistics dict
        """
        # Get existing tags once
        self.console.print("\n[bold]Fetching existing tags...[/bold]")
        existing_tags = self.api.get_all_tags()
        self.console.print(f"Found {len(existing_tags)} existing tags\n")

        # Determine which taxonomies to process
        if taxonomy_filter == "all":
            taxonomies_to_process = list(TAXONOMIES.items())
        elif taxonomy_filter in TAXONOMIES:
            taxonomies_to_process = [(taxonomy_filter, TAXONOMIES[taxonomy_filter])]
        else:
            self.console.print(
                f"[red]Error:[/red] Unknown taxonomy '{taxonomy_filter}'. "
                f"Choose from: {', '.join(TAXONOMIES.keys())}, all"
            )
            return {"created": 0, "skipped": 0, "failed": 0, "total": 0}

        # Process each taxonomy
        overall_stats = {"created": 0, "skipped": 0, "failed": 0, "total": 0}

        for taxonomy_name, taxonomy_config in taxonomies_to_process:
            # Special handling for actors (3-tier hierarchy)
            if taxonomy_name == "actor":
                stats = self.create_actor_taxonomy(
                    taxonomy_name,
                    taxonomy_config,
                    data_dir,
                    existing_tags
                )
            else:
                stats = self.create_simple_taxonomy(
                    taxonomy_name,
                    taxonomy_config,
                    data_dir,
                    existing_tags
                )

            # Update overall stats
            for key in overall_stats:
                overall_stats[key] += stats[key]

            # Print taxonomy summary
            self.console.print(
                f"  [bold]Created:[/bold] {stats['created']} | "
                f"[bold]Skipped:[/bold] {stats['skipped']} | "
                f"[bold]Failed:[/bold] {stats['failed']}"
            )

        return overall_stats
