"""
Utility functions for common operations.
"""

from pathlib import Path
from typing import Dict, List

# Color palette for dynamic assignment (50 distinct colors)
COLOR_PALETTE = [
    "#ec3838", "#3a86ff", "#d6ad9a", "#855469", "#8cb1a3",
    "#ffbe0b", "#5c0209", "#857263", "#2a9d8f", "#e76f51",
    "#4ebedd", "#06d6a0", "#ef476f", "#ffd60a", "#073b4c",
    "#7a11b2", "#7209b7", "#f72585", "#4361ee", "#3f37c9",
    "#526267", "#7209b7", "#560bad", "#b5179e", "#f72585",
    "#b96806", "#4361ee", "#3a0ca3", "#7209b7", "#10002b",
    "#e0aaff", "#c77dff", "#9d4edd", "#7b2cbf", "#5a189a",
    "#240046", "#10002b", "#ff9e00", "#ff9100", "#ff8500",
    "#ff7900", "#ff6d00", "#06ffa5", "#00f5d4", "#00bbf9",
    "#00f5d4", "#00d9ff", "#00bbf9", "#0077b6", "#023e8a"
]

# Taxonomy configurations
TAXONOMIES = {
    "actor": {
        "csv_file": "actors.csv",
        "parent_id": 5,
        "parent_color": "#dd00ff",
        "child_color": "#8338ec",
        "description": "Threat actor names organized by animal type (tier hierarchy: Animal → Individual Actor)"
    },
    "motivations": {
        "csv_file": "motivations.csv",
        "parent_id": 200,
        "parent_color": "#39e67b",
        "child_color": "#09a25b",
        "description": "What drives the threat actors"
    },
    "targeted_countries": {
        "csv_file": "targeted_countries.csv",
        "parent_id": 310,
        "parent_color": "#f3fb07",
        "child_color": "#778307",
        "description": "Geographic regions and countries"
    },
    "targeted_industries": {
        "csv_file": "targeted_industries.csv",
        "parent_id": 400,
        "parent_color": "#068bff",
        "child_color": "#0540a0",
        "description": "Industry sectors and verticals"
    }
}


def is_actor_tag(tag_name: str, known_animals: set = None) -> bool:
    """
    Determine if a tag name represents a threat actor based on known animal types.

    NOTE: This function is used primarily for taxonomy management and validation.
    For upload processing, tags are identified as actors based on their source in the
    JSON (actors vs target_countries vs motivations sections).

    Args:
        tag_name: Name of the tag (case-insensitive)
        known_animals: Set of known animal types from actors.csv (optional)

    Returns:
        True if the tag appears to be an actor tag, False otherwise
    """
    # Normalize the tag name first to handle parentheses
    normalized = normalize_tag_name(tag_name)
    parts = normalized.split()

    # Single word tags are not actors
    if len(parts) < 2:
        return False

    # If known_animals provided and not empty, check if last word matches
    if known_animals:
        last_word = parts[-1].upper()
        if last_word in known_animals:
            return True

    # Pattern matching: multi-word names are potential actors
    # This handles new animals not yet in the CSV
    return len(parts) >= 2


def get_actor_animals_from_csv(data_dir: Path = None) -> set:
    """
    Dynamically extract animal types from the actors.csv file.

    Args:
        data_dir: Optional path to data directory

    Returns:
        Set of unique animal types found in actors.csv
    """
    try:
        data_path = get_data_dir(data_dir)
        csv_file = data_path / "actors.csv"

        if not csv_file.exists():
            return set()

        animals = set()
        import csv
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header

            for row in reader:
                if row and row[0].strip():
                    actor_name = row[0].strip()
                    parts = actor_name.split()
                    if len(parts) >= 2:
                        animals.add(parts[-1].upper())

        return animals
    except Exception:
        # If we can't read the file, return empty set
        return set()


def normalize_tag_name(tag_name: str) -> str:
    """
    Normalize an ACTOR tag name by removing keywords in parentheses.

    This function is ONLY for final actor tags like "HYPER BASALISK (inactive)".
    It should NOT be used for:
    - Animal parent tags (like "UNICORN") - these never have keywords
    - Country names (like "Falkland Islands(Malvinas)") - parentheses are part of the name
    - Industry names
    - Motivation names

    This allows matching between "HYPER BASALISK" and "HYPER BASALISK (inactive)"
    or "HYPER BASALISK (inactive, merged)" by returning just "HYPER BASALISK".

    Args:
        tag_name: Actor tag name that may contain parentheses with keywords

    Returns:
        Normalized tag name without parentheses and their contents

    Examples:
        >>> normalize_tag_name("HYPER BASALISK")
        'HYPER BASALISK'
        >>> normalize_tag_name("HYPER BASALISK (inactive)")
        'HYPER BASALISK'
        >>> normalize_tag_name("HYPER BASALISK(inactive)")
        'HYPER BASALISK'
        >>> normalize_tag_name("HYPER BASALISK (inactive, merged)")
        'HYPER BASALISK'
    """
    # Find the first opening parenthesis
    paren_pos = tag_name.find('(')
    if paren_pos != -1:
        # Strip everything from the opening parenthesis onwards and trim whitespace
        return tag_name[:paren_pos].strip()
    return tag_name.strip()


def extract_animal_from_actor(actor_name: str) -> str:
    """
    Extract the animal type from an actor name.

    Handles actor names with parentheses keywords by normalizing first.

    Args:
        actor_name: Full actor name (e.g., "MYSTIC UNICORN" or "MYSTIC UNICORN (inactive)")

    Returns:
        Animal type (e.g., "UNICORN")
    """
    # First normalize to remove any parentheses keywords
    normalized = normalize_tag_name(actor_name)
    parts = normalized.split()
    if len(parts) >= 2:
        return parts[-1].upper()
    return ""


def get_data_dir(custom_path: Path = None, env_file: Path = None, env_prefix: str = "") -> Path:
    """
    Get the data directory path.

    Args:
        custom_path: Custom data directory path
        env_file: Optional path to .env file
        env_prefix: Optional environment variable prefix

    Returns:
        Path to data directory
    """
    if custom_path:
        return custom_path

    # Try to get from config
    try:
        from ..config import get_config
        config = get_config(env_prefix=env_prefix, env_file=env_file)
        data_dir = Path(config.data_dir)
        if data_dir.exists():
            return data_dir
    except Exception:
        pass

    # Try relative to current directory
    data_dir = Path.cwd() / "data"
    if data_dir.exists():
        return data_dir

    # Try parent directory (for development)
    parent_data = Path.cwd().parent / "data"
    if parent_data.exists():
        return parent_data

    raise FileNotFoundError("Data directory not found. Use --data-dir to specify location or set PAPERLESS_DATA_DIR.")
