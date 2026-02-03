"""
CSV file reading utilities.
"""

import csv
from pathlib import Path
from typing import Dict, List

from .constants import extract_animal_from_actor


def read_csv_values(csv_path: Path) -> List[str]:
    """
    Read tag values from CSV file.

    Supports both:
    - Quoted single-column format (simple list)
    - Multi-column format with header (uses first column)

    Args:
        csv_path: Path to CSV file

    Returns:
        List of values from first column
    """
    values = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header_row = next(reader, None)

        # Check if this is a header row (like actors.csv with "Name","Origins","ID")
        # vs a simple list (like targeted_countries.csv)
        has_header = (
            header_row and
            len(header_row) > 1 and
            "Name" in str(header_row[0])
        )

        if not has_header and header_row:
            # First row is data, not a header
            if header_row[0].strip():
                values.append(header_row[0].strip())

        for row in reader:
            if row and row[0].strip():
                values.append(row[0].strip())

    return values


def read_actors_with_animals(csv_path: Path) -> Dict[str, List[str]]:
    """
    Read actors and extract animal types.

    Args:
        csv_path: Path to actors CSV file

    Returns:
        Dictionary mapping animal type -> list of actor names
    """
    actors_by_animal = {}

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)  # Skip header

        for row in reader:
            if row and row[0].strip():
                actor_name = row[0].strip()
                # Extract animal from actor name (last word)
                parts = actor_name.split()
                if len(parts) >= 2:
                    animal = parts[-1].upper()
                    if animal not in actors_by_animal:
                        actors_by_animal[animal] = []
                    actors_by_animal[animal].append(actor_name)

    return actors_by_animal


def get_actor_animals_from_tags(tag_names: List[str]) -> set:
    """
    Extract unique animal types from actor tag names.

    Args:
        tag_names: List of tag names to analyze

    Returns:
        Set of animal types found (e.g., {'UNICORN', 'GRIFFIN', 'CHUPACABRA'})
    """
    animals = set()

    for tag_name in tag_names:
        animal = extract_animal_from_actor(tag_name)
        if animal:
            animals.add(animal)

    return animals
