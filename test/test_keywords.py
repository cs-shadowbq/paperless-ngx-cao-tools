"""
Test keywords service functionality.
"""

import pytest
from src.pngx_cao.services.keywords import KeywordsService


class TestKeywordsService:
    """Test KeywordsService class."""

    def test_parse_tag_name_no_keywords(self):
        """Test parsing tag name without keywords."""
        base_name, keywords = KeywordsService.parse_tag_name("HYPER BASALISK")
        assert base_name == "HYPER BASALISK"
        assert keywords == set()

    def test_parse_tag_name_with_keywords(self):
        """Test parsing tag name with keywords."""
        base_name, keywords = KeywordsService.parse_tag_name("HYPER BASALISK (inactive, retired)")
        assert base_name == "HYPER BASALISK"
        assert keywords == {"inactive", "retired"}

    def test_parse_tag_name_single_keyword(self):
        """Test parsing tag name with single keyword."""
        base_name, keywords = KeywordsService.parse_tag_name("FROST BASALISK (inactive)")
        assert base_name == "FROST BASALISK"
        assert keywords == {"inactive"}

    def test_parse_tag_name_extra_spaces(self):
        """Test parsing tag name with extra spaces."""
        base_name, keywords = KeywordsService.parse_tag_name("HYPER BASALISK  ( inactive ,  retired ) ")
        assert base_name == "HYPER BASALISK"
        assert keywords == {"inactive", "retired"}

    def test_build_tag_name_no_keywords(self):
        """Test building tag name without keywords."""
        tag_name = KeywordsService.build_tag_name("HYPER BASALISK", set())
        assert tag_name == "HYPER BASALISK"

    def test_build_tag_name_with_keywords(self):
        """Test building tag name with keywords."""
        # Note: keywords are sorted alphabetically
        tag_name = KeywordsService.build_tag_name("HYPER BASALISK", {"retired", "inactive"})
        assert tag_name == "HYPER BASALISK (inactive, retired)"

    def test_build_tag_name_single_keyword(self):
        """Test building tag name with single keyword."""
        tag_name = KeywordsService.build_tag_name("HYPER BASALISK", {"inactive"})
        assert tag_name == "HYPER BASALISK (inactive)"

    def test_roundtrip_parse_and_build(self):
        """Test that parsing and building are inverse operations."""
        original = "HYPER BASALISK (dormant, inactive, retired)"
        base_name, keywords = KeywordsService.parse_tag_name(original)
        rebuilt = KeywordsService.build_tag_name(base_name, keywords)
        assert rebuilt == original

    def test_parse_and_build_normalization(self):
        """Test that parse and build normalize keyword ordering and spacing."""
        input_name = "HYPER BASALISK (retired, inactive, dormant)"
        base_name, keywords = KeywordsService.parse_tag_name(input_name)
        normalized = KeywordsService.build_tag_name(base_name, keywords)
        assert normalized == "HYPER BASALISK (dormant, inactive, retired)"
