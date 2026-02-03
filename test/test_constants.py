"""
Test constants and utility functions.
"""


from pathlib import Path
from src.pngx_cao.utils.constants import (
    extract_animal_from_actor,
    is_actor_tag,
    get_actor_animals_from_csv,
    normalize_tag_name,
    TAXONOMIES,
    COLOR_PALETTE
)


class TestNormalizeTagName:
    """Test normalize_tag_name function for handling parentheses keywords."""

    def test_tag_without_parentheses(self):
        """Test that tags without parentheses are unchanged."""
        assert normalize_tag_name("HYPER BASALISK") == "HYPER BASALISK"
        assert normalize_tag_name("MYSTIC UNICORN") == "MYSTIC UNICORN"
        assert normalize_tag_name("Simple Tag") == "Simple Tag"

    def test_tag_with_single_keyword(self):
        """Test stripping single keyword in parentheses."""
        assert normalize_tag_name("HYPER BASALISK (inactive)") == "HYPER BASALISK"
        assert normalize_tag_name("MYSTIC UNICORN (retired)") == "MYSTIC UNICORN"
        assert normalize_tag_name("TEST ANIMAL (active)") == "TEST ANIMAL"

    def test_tag_with_multiple_keywords(self):
        """Test stripping multiple comma-separated keywords."""
        assert normalize_tag_name("HYPER BASALISK (inactive, merged)") == "HYPER BASALISK"
        assert normalize_tag_name("FANCY PHOENIX (active, monitored, high-risk)") == "FANCY PHOENIX"

    def test_tag_with_whitespace_variations(self):
        """Test handling various whitespace patterns."""
        assert normalize_tag_name("HYPER BASALISK  (inactive)") == "HYPER BASALISK"
        assert normalize_tag_name("HYPER BASALISK(inactive)") == "HYPER BASALISK"
        assert normalize_tag_name("HYPER BASALISK ( inactive )") == "HYPER BASALISK"

    def test_tag_without_space_before_parenthesis(self):
        """Test tags with no space before opening parenthesis."""
        assert normalize_tag_name("FANCY PHOENIX(inactive)") == "FANCY PHOENIX"
        assert normalize_tag_name("MYSTIC UNICORN(retired)") == "MYSTIC UNICORN"
        assert normalize_tag_name("HYPER BASALISK(inactive, merged)") == "HYPER BASALISK"
        assert normalize_tag_name("GOLDEN GRIFFIN(active, monitored, high-risk)") == "GOLDEN GRIFFIN"

    def test_empty_parentheses(self):
        """Test handling empty parentheses."""
        assert normalize_tag_name("HYPER BASALISK ()") == "HYPER BASALISK"
        assert normalize_tag_name("MYSTIC UNICORN (  )") == "MYSTIC UNICORN"

    def test_multiple_parentheses_groups(self):
        """Test that only the first parenthesis group is removed."""
        # This is an edge case - we strip from first ( onwards
        assert normalize_tag_name("BASALISK (inactive) (old)") == "BASALISK"

    def test_empty_and_whitespace_strings(self):
        """Test edge cases with empty or whitespace strings."""
        assert normalize_tag_name("") == ""
        assert normalize_tag_name("   ") == ""
        assert normalize_tag_name("(inactive)") == ""


class TestExtractAnimalFromActor:
    """Test extract_animal_from_actor function."""

    def test_valid_actor_names(self):
        """Test extracting animal from valid actor names."""
        assert extract_animal_from_actor("MYSTIC UNICORN") == "UNICORN"
        assert extract_animal_from_actor("GOLDEN GRIFFIN") == "GRIFFIN"
        assert extract_animal_from_actor("ANCIENT CHUPACABRA") == "CHUPACABRA"
        assert extract_animal_from_actor("COSMIC UNICORN") == "UNICORN"

    def test_actor_names_with_parentheses(self):
        """Test extracting animal from actor names with keywords in parentheses."""
        assert extract_animal_from_actor("HYPER BASALISK (inactive)") == "BASALISK"
        assert extract_animal_from_actor("HYPER BASALISK(inactive)") == "BASALISK"  # No space
        assert extract_animal_from_actor("MYSTIC UNICORN (retired)") == "UNICORN"
        assert extract_animal_from_actor("MYSTIC UNICORN(retired)") == "UNICORN"  # No space
        assert extract_animal_from_actor("GOLDEN GRIFFIN (inactive, merged)") == "GRIFFIN"
        assert extract_animal_from_actor("GOLDEN GRIFFIN(inactive, merged)") == "GRIFFIN"  # No space
        assert extract_animal_from_actor("FANCY PHOENIX (active, monitored)") == "PHOENIX"
        assert extract_animal_from_actor("FANCY PHOENIX(active, monitored)") == "PHOENIX"  # No space

    def test_single_word_name(self):
        """Test with single word (should return empty)."""
        assert extract_animal_from_actor("UNICORN") == ""
        assert extract_animal_from_actor("Test") == ""

    def test_single_word_with_parentheses(self):
        """Test single word with parentheses (should still return empty)."""
        assert extract_animal_from_actor("UNICORN (inactive)") == ""

    def test_empty_string(self):
        """Test with empty string."""
        assert extract_animal_from_actor("") == ""


class TestIsActorTag:
    """Test is_actor_tag function."""

    def test_valid_actor_tags(self):
        """Test identifying valid actor tags."""
        assert is_actor_tag("MYSTIC UNICORN") is True
        assert is_actor_tag("GOLDEN GRIFFIN") is True
        assert is_actor_tag("CYBER CHUPACABRA") is True

    def test_non_actor_tags(self):
        """Test rejecting non-actor tags."""
        assert is_actor_tag("Artistic") is False
        assert is_actor_tag("Wakanda") is False
        assert is_actor_tag("single") is False

    def test_with_known_animals(self):
        """Test with known_animals set - CSV is a hint, not a requirement."""
        known_animals = {"UNICORN", "GRIFFIN"}

        # Known animals should be recognized
        assert is_actor_tag("MYSTIC UNICORN", known_animals) is True
        assert is_actor_tag("GOLDEN GRIFFIN", known_animals) is True

        # NEW animals NOT in CSV should STILL be recognized by pattern
        assert is_actor_tag("ANCIENT CHUPACABRA", known_animals) is True
        assert is_actor_tag("WARRY SPRITE", known_animals) is True

    def test_pattern_matching_for_new_animals(self):
        """Test that new animals not in CSV are recognized by pattern."""
        # Even with an empty known_animals set, pattern matching should work
        assert is_actor_tag("WARRY SPRITE", set()) is True
        assert is_actor_tag("FANCY PHOENIX", set()) is True

        # Case-insensitive matching should work (any multi-word is potential actor)
        assert is_actor_tag("Fancy phoenix", set()) is True
        assert is_actor_tag("warry SPRITE", set()) is True

        # Single word should be rejected
        assert is_actor_tag("ONLYONEWORD", set()) is False


class TestGetActorAnimalsFromCSV:
    """Test get_actor_animals_from_csv function."""

    def test_extract_animals_from_test_csv(self):
        """Test extracting animals from test data CSV."""
        test_data_dir = Path(__file__).parent / "data"
        animals = get_actor_animals_from_csv(test_data_dir)

        assert len(animals) == 4
        assert "UNICORN" in animals
        assert "GRIFFIN" in animals
        assert "CHUPACABRA" in animals
        assert "BASALISK" in animals

    def test_nonexistent_directory(self):
        """Test with non-existent directory."""
        animals = get_actor_animals_from_csv(Path("/nonexistent/path"))
        assert len(animals) == 0


class TestTaxonomiesConfiguration:
    """Test TAXONOMIES configuration."""

    def test_all_taxonomies_present(self):
        """Test that all required taxonomies are defined."""
        assert "actor" in TAXONOMIES
        assert "motivations" in TAXONOMIES
        assert "targeted_countries" in TAXONOMIES
        assert "targeted_industries" in TAXONOMIES

    def test_taxonomy_structure(self):
        """Test that each taxonomy has required fields."""
        for taxonomy_name, taxonomy in TAXONOMIES.items():
            assert "csv_file" in taxonomy
            assert "parent_id" in taxonomy
            assert "parent_color" in taxonomy
            assert "child_color" in taxonomy
            assert "description" in taxonomy

    def test_csv_filenames(self):
        """Test that CSV filenames are correct."""
        assert TAXONOMIES["actor"]["csv_file"] == "actors.csv"
        assert TAXONOMIES["motivations"]["csv_file"] == "motivations.csv"
        assert TAXONOMIES["targeted_countries"]["csv_file"] == "targeted_countries.csv"
        assert TAXONOMIES["targeted_industries"]["csv_file"] == "targeted_industries.csv"


class TestColorPalette:
    """Test COLOR_PALETTE configuration."""

    def test_palette_has_colors(self):
        """Test that color palette is not empty."""
        assert len(COLOR_PALETTE) > 0

    def test_colors_are_valid_hex(self):
        """Test that all colors are valid hex codes."""
        for color in COLOR_PALETTE:
            assert color.startswith("#")
            assert len(color) == 7
            # Verify hex characters after #
            hex_chars = color[1:]
            assert all(c in "0123456789abcdefABCDEF" for c in hex_chars)
