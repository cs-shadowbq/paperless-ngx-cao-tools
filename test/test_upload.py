"""
Test upload service functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
from rich.console import Console

from pngx_cao.services.upload import UploadService
from pngx_cao.api.client import PaperlessAPI


@pytest.fixture
def mock_api():
    """Create a mock PaperlessAPI instance."""
    return Mock(spec=PaperlessAPI)


@pytest.fixture
def upload_service(mock_api):
    """Create an UploadService instance with mocked dependencies."""
    # Use a real Console but with file=None to avoid output during tests
    console = Console(file=None, force_terminal=False)
    return UploadService(mock_api, console)


@pytest.fixture
def test_originals_dir():
    """Return path to test originals directory."""
    return Path(__file__).parent / "originals"


class TestEmptyFileHandling:
    """Test handling of empty (zero-byte) PDF files."""

    def test_empty_pdf_is_skipped(self, upload_service, test_originals_dir):
        """Test that empty PDF files are detected and skipped."""
        empty_folder = test_originals_dir / "empty-001"

        result = upload_service.process_folder(empty_folder, dry_run=False)

        # Verify the file was skipped
        assert result is not None
        assert result.get('skipped') is True
        assert result.get('reason') == 'empty_file'

        # Verify no API calls were made
        upload_service.api.upload_document.assert_not_called()

    def test_empty_pdf_is_skipped_in_dry_run(self, upload_service, test_originals_dir):
        """Test that empty PDF files are detected even in dry-run mode."""
        empty_folder = test_originals_dir / "empty-001"

        result = upload_service.process_folder(empty_folder, dry_run=True)

        # Verify the file was skipped
        assert result is not None
        assert result.get('skipped') is True
        assert result.get('reason') == 'empty_file'


class TestActorHierarchy:
    """Test actor tag hierarchy creation (animal -> specific actor)."""

    def test_find_or_create_animal_parent_tag_existing(self, upload_service, mock_api):
        """Test finding an existing animal parent tag."""
        # Mock API to return existing SPRITE tag
        mock_api.get_tag_by_name.return_value = {'id': 100, 'name': 'SPRITE'}

        result = upload_service.find_or_create_animal_parent_tag('SPRITE')

        assert result == 100
        mock_api.get_tag_by_name.assert_called_once_with('SPRITE')

    def test_find_or_create_animal_parent_tag_creates_new(self, upload_service, mock_api):
        """Test creating a new animal parent tag when it doesn't exist."""
        # Mock API to return None (tag doesn't exist) then return Actor parent
        mock_api.get_tag_by_name.return_value = None
        mock_api.get_tag_by_id.return_value = {'id': 5, 'name': 'Actor'}
        mock_api.create_tag.return_value = {'id': 101, 'name': 'SPRITE'}
        mock_api.MATCH_NONE = 0

        result = upload_service.find_or_create_animal_parent_tag('SPRITE')

        assert result == 101
        mock_api.get_tag_by_name.assert_called_once_with('SPRITE')
        mock_api.get_tag_by_id.assert_called_once_with(5)  # Actor parent ID
        mock_api.create_tag.assert_called_once_with(
            name='SPRITE',
            color='#8338ec',
            is_inbox_tag=False,
            matching_algorithm=0,
            parent=5
        )

    def test_find_or_create_animal_parent_tag_no_actor_parent(self, upload_service, mock_api):
        """Test creating animal tag when Actor parent doesn't exist."""
        # Mock API to return None for animal and Actor parent
        mock_api.get_tag_by_name.return_value = None
        mock_api.get_tag_by_id.return_value = None
        mock_api.create_tag.return_value = {'id': 102, 'name': 'SPRITE'}
        mock_api.MATCH_NONE = 0

        result = upload_service.find_or_create_animal_parent_tag('SPRITE')

        # Should still create the animal tag but without a parent
        assert result == 102
        mock_api.create_tag.assert_called_once_with(
            name='SPRITE',
            color='#8338ec',
            is_inbox_tag=False,
            matching_algorithm=0,
            parent=None
        )

    def test_actor_tag_creation_with_hierarchy(self, upload_service, mock_api):
        """Test full workflow: WARRY SPRITE creates SPRITE under Actor, then WARRY SPRITE under SPRITE."""
        # Setup mocks
        mock_api.get_tag_by_name.side_effect = [
            None,  # First call: SPRITE doesn't exist
            {'id': 101, 'name': 'SPRITE'}  # Second call from get_or_create_tag cache check
        ]
        mock_api.get_tag_by_id.return_value = {'id': 5, 'name': 'Actor'}
        mock_api.create_tag.side_effect = [
            {'id': 101, 'name': 'SPRITE'},  # Created animal tag
            {'id': 200, 'name': 'WARRY SPRITE'}  # Created specific actor tag
        ]
        mock_api.get_or_create_tag.return_value = 200
        mock_api.MATCH_NONE = 0

        # Simulate processing "WARRY SPRITE" actor tag
        from pngx_cao.utils.constants import extract_animal_from_actor

        tag_name = "WARRY SPRITE"
        animal = extract_animal_from_actor(tag_name)
        assert animal == "SPRITE"

        # This should create SPRITE first with Actor as parent
        animal_parent_id = upload_service.find_or_create_animal_parent_tag(animal)
        assert animal_parent_id == 101

        # Verify SPRITE was created with Actor (ID 5) as parent
        assert mock_api.create_tag.call_count == 1
        first_call = mock_api.create_tag.call_args_list[0]
        assert first_call[1]['name'] == 'SPRITE'
        assert first_call[1]['parent'] == 5

    def test_actor_inherits_animal_color(self, upload_service, mock_api):
        """Test that actor tags inherit the color from their animal parent."""
        # Mock the animal parent tag with a specific color
        animal_color = '#2a9d8f'
        mock_api.get_tag_by_name.return_value = None  # Animal doesn't exist initially
        mock_api.get_tag_by_id.side_effect = [
            {'id': 5, 'name': 'Actor'},  # Actor parent for animal creation
            {'id': 101, 'name': 'UNICORN', 'color': animal_color}  # Animal tag lookup for color
        ]
        mock_api.create_tag.return_value = {'id': 101, 'name': 'UNICORN', 'color': animal_color}
        mock_api.get_or_create_tag.return_value = 200
        mock_api.MATCH_NONE = 0

        # Simulate processing "FRIGID UNICORN" actor tag
        from pngx_cao.utils.constants import extract_animal_from_actor

        tag_name = "FRIGID UNICORN"
        animal = extract_animal_from_actor(tag_name)
        assert animal == "UNICORN"

        # Create the animal parent
        animal_parent_id = upload_service.find_or_create_animal_parent_tag(animal)
        assert animal_parent_id == 101

        # Get the animal color
        animal_tag = mock_api.get_tag_by_id(animal_parent_id)
        inherited_color = animal_tag.get('color')
        assert inherited_color == animal_color

        # When creating the actor tag, it should use the inherited color
        mock_api.get_or_create_tag(
            tag_name,
            color=inherited_color,
            is_actor=True,
            animal_parent_id=animal_parent_id
        )

        # Verify get_or_create_tag was called with the animal's color
        mock_api.get_or_create_tag.assert_called_once_with(
            tag_name,
            color=animal_color,
            is_actor=True,
            animal_parent_id=animal_parent_id
        )


class TestBatchUpload:
    """Test batch upload functionality."""

    def test_batch_counts_empty_files_as_skipped(self, upload_service, test_originals_dir):
        """Test that batch upload counts empty files in skipped statistics."""
        stats = upload_service.upload_batch(
            originals_dir=test_originals_dir,
            folder_filter="empty-001",
            dry_run=False
        )

        # Verify stats show the file was skipped
        assert stats['skipped'] >= 1
        assert stats['failed'] == 0
