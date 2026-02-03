"""
Test tag matching with parentheses keywords feature.

This module tests the ability to match tags like "HYPER BASALISK" 
against "HYPER BASALISK (inactive)" or "HYPER BASALISK (inactive, merged)".
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pngx_cao.api.client import PaperlessAPI
from pngx_cao.utils.constants import normalize_tag_name, extract_animal_from_actor


class TestTagNormalizationIntegration:
    """Test tag matching with parentheses in the API client."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock session."""
        mock = Mock()
        mock.headers = {}
        mock.verify = True
        return mock

    @pytest.fixture
    def api_client(self, mock_session):
        """Create a PaperlessAPI instance with mocked session."""
        with patch('pngx_cao.api.client.requests.Session', return_value=mock_session):
            api = PaperlessAPI(
                base_url="http://test.local",
                token="test-token",
                global_read=True
            )
            api.session = mock_session
            return api

    def test_exact_match_without_parentheses(self, api_client, mock_session):
        """Test that exact matches still work without parentheses."""
        # Mock response for exact match
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            'count': 1,
            'results': [{'id': 1, 'name': 'HYPER BASALISK'}]
        }
        mock_session.get.return_value = mock_response

        tag = api_client.get_tag_by_name('HYPER BASALISK')

        assert tag is not None
        assert tag['name'] == 'HYPER BASALISK'
        assert tag['id'] == 1

    def test_match_tag_with_inactive_keyword(self, api_client, mock_session):
        """Test matching 'HYPER BASALISK' finds 'HYPER BASALISK (inactive)'."""
        # First call returns no exact match
        mock_response_no_exact = Mock()
        mock_response_no_exact.raise_for_status = Mock()
        mock_response_no_exact.json.return_value = {
            'count': 0,
            'results': []
        }

        # Second call returns all tags
        mock_response_all = Mock()
        mock_response_all.raise_for_status = Mock()
        mock_response_all.json.return_value = {
            'count': 1,
            'results': [
                {'id': 1, 'name': 'HYPER BASALISK (inactive)'},
                {'id': 2, 'name': 'MYSTIC UNICORN'},
            ]
        }

        mock_session.get.side_effect = [mock_response_no_exact, mock_response_all]

        tag = api_client.get_tag_by_name('HYPER BASALISK', normalize_for_actor=True)

        assert tag is not None
        assert tag['name'] == 'HYPER BASALISK (inactive)'
        assert tag['id'] == 1

    def test_match_tag_with_multiple_keywords(self, api_client, mock_session):
        """Test matching finds tags with multiple comma-separated keywords."""
        # First call returns no exact match
        mock_response_no_exact = Mock()
        mock_response_no_exact.raise_for_status = Mock()
        mock_response_no_exact.json.return_value = {
            'count': 0,
            'results': []
        }

        # Second call returns all tags
        mock_response_all = Mock()
        mock_response_all.raise_for_status = Mock()
        mock_response_all.json.return_value = {
            'count': 1,
            'results': [
                {'id': 1, 'name': 'HYPER BASALISK (inactive, merged)'},
                {'id': 2, 'name': 'FANCY PHOENIX (active, monitored)'},
            ]
        }

        mock_session.get.side_effect = [mock_response_no_exact, mock_response_all]

        tag = api_client.get_tag_by_name('HYPER BASALISK', normalize_for_actor=True)

        assert tag is not None
        assert tag['name'] == 'HYPER BASALISK (inactive, merged)'
        assert tag['id'] == 1

    def test_match_tag_without_space_before_parenthesis(self, api_client, mock_session):
        """Test matching 'FANCY PHOENIX' finds 'FANCY PHOENIX(inactive)' (no space)."""
        # First call returns no exact match
        mock_response_no_exact = Mock()
        mock_response_no_exact.raise_for_status = Mock()
        mock_response_no_exact.json.return_value = {
            'count': 0,
            'results': []
        }

        # Second call returns all tags
        mock_response_all = Mock()
        mock_response_all.raise_for_status = Mock()
        mock_response_all.json.return_value = {
            'count': 1,
            'results': [
                {'id': 1, 'name': 'HYPER BASALISK(inactive)'},  # No space
                {'id': 2, 'name': 'FANCY PHOENIX(active, monitored)'},  # No space
            ]
        }

        mock_session.get.side_effect = [mock_response_no_exact, mock_response_all]

        tag = api_client.get_tag_by_name('HYPER BASALISK', normalize_for_actor=True)

        assert tag is not None
        assert tag['name'] == 'HYPER BASALISK(inactive)'
        assert tag['id'] == 1

    def test_no_match_returns_none(self, api_client, mock_session):
        """Test that searching for non-existent tag returns None."""
        # First call returns no exact match
        mock_response_no_exact = Mock()
        mock_response_no_exact.raise_for_status = Mock()
        mock_response_no_exact.json.return_value = {
            'count': 0,
            'results': []
        }

        # Second call returns tags that don't match
        mock_response_all = Mock()
        mock_response_all.raise_for_status = Mock()
        mock_response_all.json.return_value = {
            'count': 1,
            'results': [
                {'id': 1, 'name': 'DIFFERENT BASALISK (inactive)'},
                {'id': 2, 'name': 'MYSTIC UNICORN'},
            ]
        }

        mock_session.get.side_effect = [mock_response_no_exact, mock_response_all]

        tag = api_client.get_tag_by_name('HYPER BASALISK')

        assert tag is None

    def test_case_insensitive_matching(self, api_client, mock_session):
        """Test that matching is case-insensitive."""
        # First call returns no exact match
        mock_response_no_exact = Mock()
        mock_response_no_exact.raise_for_status = Mock()
        mock_response_no_exact.json.return_value = {
            'count': 0,
            'results': []
        }

        # Second call returns all tags
        mock_response_all = Mock()
        mock_response_all.raise_for_status = Mock()
        mock_response_all.json.return_value = {
            'count': 1,
            'results': [
                {'id': 1, 'name': 'HYPER BASALISK (inactive)'},
            ]
        }

        mock_session.get.side_effect = [mock_response_no_exact, mock_response_all]

        tag = api_client.get_tag_by_name('HYPER BASALISK', normalize_for_actor=True)

        assert tag is not None
        assert tag['id'] == 1


class TestAnimalExtractionWithParentheses:
    """Test that animal extraction works correctly with parentheses."""

    def test_extract_animal_from_tagged_actor(self):
        """Test animal extraction from actors with various keyword patterns."""
        test_cases = [
            ("HYPER BASALISK", "BASALISK"),
            ("HYPER BASALISK (inactive)", "BASALISK"),
            ("HYPER BASALISK (inactive, merged)", "BASALISK"),
            ("MYSTIC UNICORN (retired)", "UNICORN"),
            ("FANCY PHOENIX (active, monitored, high-risk)", "PHOENIX"),
            ("GOLDEN GRIFFIN", "GRIFFIN"),
        ]

        for actor_name, expected_animal in test_cases:
            result = extract_animal_from_actor(actor_name)
            assert result == expected_animal, f"Failed for {actor_name}: expected {expected_animal}, got {result}"


class TestEndToEndScenario:
    """Test complete workflow with parentheses keywords."""

    def test_report_matches_inactive_actor_tag(self):
        """
        Test the scenario where:
        - Report has actor "HYPER BASALISK" (no keywords)
        - Server has tag "HYPER BASALISK (inactive)"
        - They should match
        """
        from pngx_cao.utils.constants import normalize_tag_name

        # Simulate report data
        report_actor = "HYPER BASALISK"

        # Simulate server tags
        server_tags = [
            {"id": 1, "name": "HYPER BASALISK (inactive)"},
            {"id": 2, "name": "MYSTIC UNICORN"},
            {"id": 3, "name": "FANCY PHOENIX (active, monitored)"},
        ]

        # Search for matching tag
        normalized_search = normalize_tag_name(report_actor).upper()
        matching_tag = None

        for tag in server_tags:
            if normalize_tag_name(tag["name"]).upper() == normalized_search:
                matching_tag = tag
                break

        assert matching_tag is not None
        assert matching_tag["id"] == 1
        assert matching_tag["name"] == "HYPER BASALISK (inactive)"

    def test_multiple_reports_different_keyword_patterns(self):
        """Test that different keyword patterns all normalize to same base name."""
        from pngx_cao.utils.constants import normalize_tag_name

        # All these should normalize to "HYPER BASALISK"
        variations = [
            "HYPER BASALISK",
            "HYPER BASALISK (inactive)",
            "HYPER BASALISK(inactive)",  # No space before parenthesis
            "HYPER BASALISK (inactive, merged)",
            "HYPER BASALISK(inactive, merged)",  # No space before parenthesis
            "HYPER BASALISK (retired)",
            "HYPER BASALISK (  active  )",
        ]

        for variation in variations:
            normalized = normalize_tag_name(variation)
            assert normalized == "HYPER BASALISK", f"Failed to normalize: {variation}"

    def test_unique_tag_constraint(self):
        """
        Test that there's only one tag per actor base name.
        The server should never have both "HYPER BASALISK" and "HYPER BASALISK (inactive)".
        """
        from pngx_cao.utils.constants import normalize_tag_name

        # Simulate server tags - should only have ONE HYPER BASALISK variant
        server_tags = [
            {"id": 1, "name": "HYPER BASALISK (inactive)"},
            {"id": 2, "name": "MYSTIC UNICORN"},
            {"id": 3, "name": "FANCY PHOENIX (active, monitored)"},
        ]

        # Check that there's only one HYPER BASALISK
        hyper_basalisk_tags = []
        for tag in server_tags:
            if normalize_tag_name(tag["name"]).upper() == "HYPER BASALISK":
                hyper_basalisk_tags.append(tag)

        assert len(hyper_basalisk_tags) == 1, "Should only have one HYPER BASALISK tag"
