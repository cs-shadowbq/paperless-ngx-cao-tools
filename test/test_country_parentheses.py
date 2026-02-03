"""
Test that country names with parentheses (like "Falkland Islands(Malvinas)") 
are NOT treated as keywords and work correctly.
"""

import pytest
from unittest.mock import Mock, patch
from pngx_cao.api.client import PaperlessAPI
from pngx_cao.services.upload import UploadService
from rich.console import Console


class TestCountryNamesWithParentheses:
    """Test that parentheses in country names are preserved, not treated as keywords."""

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

    def test_country_with_parentheses_exact_match(self, api_client, mock_session):
        """Test that "Falkland Islands(Malvinas)" is searched exactly, not normalized."""
        # Mock response for exact match
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            'count': 1,
            'results': [{'id': 1, 'name': 'Falkland Islands(Malvinas)'}]
        }
        mock_session.get.return_value = mock_response

        # Search without normalize_for_actor (default behavior for countries)
        tag = api_client.get_tag_by_name('Falkland Islands(Malvinas)')

        assert tag is not None
        assert tag['name'] == 'Falkland Islands(Malvinas)'
        assert tag['id'] == 1

    def test_country_with_parentheses_not_normalized_in_search(self, api_client, mock_session):
        """Test that country search does NOT normalize - exact match only."""
        # Mock responses: first for exact match (none), then should NOT try normalization
        mock_response_no_exact = Mock()
        mock_response_no_exact.raise_for_status = Mock()
        mock_response_no_exact.json.return_value = {
            'count': 0,
            'results': []
        }

        mock_session.get.return_value = mock_response_no_exact

        # Search for country without normalization
        tag = api_client.get_tag_by_name('Falkland Islands(Malvinas)', normalize_for_actor=False)

        # Should return None since no exact match and no normalization attempted
        assert tag is None
        # Should only make ONE call (the exact match attempt)
        assert mock_session.get.call_count == 1

    def test_actor_with_keywords_uses_normalization(self, api_client, mock_session):
        """Test that actor tags DO use normalization when requested."""
        # First call returns no exact match
        mock_response_no_exact = Mock()
        mock_response_no_exact.raise_for_status = Mock()
        mock_response_no_exact.json.return_value = {
            'count': 0,
            'results': []
        }

        # Second call returns all tags with normalized match
        mock_response_all = Mock()
        mock_response_all.raise_for_status = Mock()
        mock_response_all.json.return_value = {
            'count': 1,
            'results': [
                {'id': 1, 'name': 'HYPER BASALISK (inactive)'},
            ]
        }

        mock_session.get.side_effect = [mock_response_no_exact, mock_response_all]

        # Search for actor WITH normalization
        tag = api_client.get_tag_by_name('HYPER BASALISK', normalize_for_actor=True)

        assert tag is not None
        assert tag['name'] == 'HYPER BASALISK (inactive)'
        assert tag['id'] == 1
        # Should make TWO calls (exact match, then normalized search)
        assert mock_session.get.call_count == 2

    def test_upload_service_processes_countries_without_normalization(self):
        """Test that UploadService does not normalize country names."""
        mock_api = Mock(spec=PaperlessAPI)
        console = Console(file=None, force_terminal=False)
        upload_service = UploadService(mock_api, console)

        # Mock metadata with country that has parentheses
        metadata = {
            'name': 'Test Report',
            'url': 'http://test.com',
            'type': {'slug': 'intelligence-report'},
            'created_date': 1640000000,
            'actors': [],
            'target_countries': [
                {'value': 'Falkland Islands(Malvinas)'}
            ],
            'target_industries': [],
            'motivations': []
        }

        extracted = upload_service.process_crowdstrike_metadata(metadata)

        # Verify country is in tag_names
        assert 'Falkland Islands(Malvinas)' in extracted['tag_names']
        # Verify country is NOT in actor_names
        assert 'Falkland Islands(Malvinas)' not in extracted['actor_names']

    def test_get_or_create_tag_for_country_no_normalization(self, api_client, mock_session):
        """Test that get_or_create_tag for non-actor tags doesn't normalize."""
        # Mock exact match found
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {
            'count': 1,
            'results': [{'id': 100, 'name': 'Falkland Islands(Malvinas)'}]
        }
        mock_session.get.return_value = mock_response

        # Call get_or_create_tag with is_actor=False (like for countries)
        tag_id = api_client.get_or_create_tag(
            'Falkland Islands(Malvinas)',
            is_actor=False  # This is a country, not an actor
        )

        assert tag_id == 100
        # Should only call exact match, not normalized search
        assert mock_session.get.call_count == 1

    def test_get_or_create_tag_for_actor_with_normalization(self, api_client, mock_session):
        """Test that get_or_create_tag for actor tags uses normalization."""
        # First call: no exact match
        mock_response_no_exact = Mock()
        mock_response_no_exact.raise_for_status = Mock()
        mock_response_no_exact.json.return_value = {
            'count': 0,
            'results': []
        }

        # Second call: normalized search finds the tag
        mock_response_all = Mock()
        mock_response_all.raise_for_status = Mock()
        mock_response_all.json.return_value = {
            'count': 1,
            'results': [
                {'id': 200, 'name': 'FRIGID UNICORN (inactive)'},
            ]
        }

        mock_session.get.side_effect = [mock_response_no_exact, mock_response_all]

        # Call get_or_create_tag with is_actor=True
        tag_id = api_client.get_or_create_tag(
            'FRIGID UNICORN',
            is_actor=True,  # This is an actor tag
            animal_parent_id=50
        )

        assert tag_id == 200
        # Should call exact match AND normalized search
        assert mock_session.get.call_count == 2

    def test_animal_parent_tags_never_have_keywords(self):
        """Test that animal parent tags are never searched with normalization."""
        mock_api = Mock(spec=PaperlessAPI)
        mock_api.get_tag_by_name.return_value = {'id': 42, 'name': 'UNICORN'}

        console = Console(file=None, force_terminal=False)
        upload_service = UploadService(mock_api, console)

        # Find or create animal parent tag
        animal_id = upload_service.find_or_create_animal_parent_tag('UNICORN')

        assert animal_id == 42
        # Verify get_tag_by_name was called WITHOUT normalize_for_actor parameter
        # (defaults to False)
        mock_api.get_tag_by_name.assert_called_once_with('UNICORN')


class TestKeywordsOnlyOnFinalActorTags:
    """Test that keywords in parentheses only apply to final actor tags, not animals."""

    def test_extract_animal_from_actor_with_keywords(self):
        """Test that we extract the animal correctly even when actor has keywords."""
        from pngx_cao.utils.constants import extract_animal_from_actor

        # Final actor tag with keywords should extract animal without keywords
        assert extract_animal_from_actor("FRIGID UNICORN (inactive)") == "UNICORN"
        assert extract_animal_from_actor("FRIGID UNICORN(inactive)") == "UNICORN"
        assert extract_animal_from_actor("HYPER BASALISK (inactive, merged)") == "BASALISK"

        # Animal name itself should never have keywords
        assert extract_animal_from_actor("UNICORN") == ""  # Single word, not an actor

    def test_animal_tags_created_without_parentheses(self):
        """Test that when we create animal parent tags, they never have parentheses."""
        from pngx_cao.utils.constants import extract_animal_from_actor

        # Process actor with keywords
        actor_with_keywords = "FRIGID UNICORN (inactive)"
        animal = extract_animal_from_actor(actor_with_keywords)

        # Animal should be just "UNICORN", no keywords
        assert animal == "UNICORN"
        assert "(" not in animal
        assert ")" not in animal
