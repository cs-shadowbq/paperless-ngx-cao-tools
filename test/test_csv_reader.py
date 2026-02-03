"""
Test CSV reading utilities.
"""

import pytest
from pathlib import Path
from src.pngx_cao.utils.csv_reader import (
    read_csv_values,
    read_actors_with_animals,
    get_actor_animals_from_tags
)


@pytest.fixture
def test_data_dir():
    """Return path to test data directory."""
    return Path(__file__).parent / "data"


class TestReadCSVValues:
    """Test read_csv_values function."""

    def test_read_actors_csv(self, test_data_dir):
        """Test reading actors CSV with multi-column format."""
        csv_path = test_data_dir / "actors.csv"
        values = read_csv_values(csv_path)

        assert len(values) == 11
        assert "MYSTIC UNICORN" in values
        assert "GOLDEN GRIFFIN" in values
        assert "ANCIENT CHUPACABRA" in values
        assert "HYPER BASALISK" in values
        assert "SHADOW BASALISK" in values
        assert "FROST BASALISK" in values

    def test_read_motivations_csv(self, test_data_dir):
        """Test reading motivations CSV."""
        csv_path = test_data_dir / "motivations.csv"
        values = read_csv_values(csv_path)

        assert len(values) == 3
        assert "Artistic" in values
        assert "Guilt" in values
        assert "Hustle" in values

    def test_read_countries_csv(self, test_data_dir):
        """Test reading targeted countries CSV."""
        csv_path = test_data_dir / "targeted_countries.csv"
        values = read_csv_values(csv_path)

        assert len(values) == 4
        assert "Wakanda" in values
        assert "Genovia" in values
        assert "Agrabah" in values
        assert "Sokovia" in values

    def test_read_industries_csv(self, test_data_dir):
        """Test reading targeted industries CSV."""
        csv_path = test_data_dir / "targeted_industries.csv"
        values = read_csv_values(csv_path)

        assert len(values) == 4
        assert "Pneumatic Tube Industry" in values
        assert "Aether Refineries" in values
        assert "Warp Drive Engineering" in values
        assert "Terraform Plants" in values


class TestReadActorsWithAnimals:
    """Test read_actors_with_animals function."""

    def test_group_actors_by_animal(self, test_data_dir):
        """Test grouping actors by animal type."""
        csv_path = test_data_dir / "actors.csv"
        actors_by_animal = read_actors_with_animals(csv_path)

        # Should have 4 animal types
        assert len(actors_by_animal) == 4
        assert "UNICORN" in actors_by_animal
        assert "GRIFFIN" in actors_by_animal
        assert "CHUPACABRA" in actors_by_animal
        assert "BASALISK" in actors_by_animal

        # Verify counts
        assert len(actors_by_animal["UNICORN"]) == 3
        assert len(actors_by_animal["GRIFFIN"]) == 2
        assert len(actors_by_animal["CHUPACABRA"]) == 3

    def test_actor_names_in_groups(self, test_data_dir):
        """Test that actor names are correctly grouped."""
        csv_path = test_data_dir / "actors.csv"
        actors_by_animal = read_actors_with_animals(csv_path)

        assert "MYSTIC UNICORN" in actors_by_animal["UNICORN"]
        assert "COSMIC UNICORN" in actors_by_animal["UNICORN"]
        assert "SHADOW UNICORN" in actors_by_animal["UNICORN"]

        assert "GOLDEN GRIFFIN" in actors_by_animal["GRIFFIN"]
        assert "STORM GRIFFIN" in actors_by_animal["GRIFFIN"]


class TestGetActorAnimalsFromTags:
    """Test get_actor_animals_from_tags function."""

    def test_extract_animals_from_tag_names(self):
        """Test extracting animal types from tag names."""
        tag_names = [
            "MYSTIC UNICORN",
            "COSMIC UNICORN",
            "GOLDEN GRIFFIN",
            "ANCIENT CHUPACABRA"
        ]

        animals = get_actor_animals_from_tags(tag_names)

        assert len(animals) == 3
        assert "UNICORN" in animals
        assert "GRIFFIN" in animals
        assert "CHUPACABRA" in animals

    def test_empty_tag_list(self):
        """Test with empty tag list."""
        animals = get_actor_animals_from_tags([])
        assert len(animals) == 0

    def test_non_actor_tags(self):
        """Test that non-actor tags are ignored."""
        tag_names = [
            "Artistic",
            "Wakanda",
            "single",
            "MYSTIC UNICORN"
        ]

        animals = get_actor_animals_from_tags(tag_names)

        assert len(animals) == 1
        assert "UNICORN" in animals
