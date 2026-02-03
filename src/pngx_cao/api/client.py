"""
Paperless-ngx REST API client.

This module provides a clean interface to interact with the Paperless-ngx API,
following SOLID principles with a focus on Single Responsibility.
"""

import logging
import time
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class PaperlessAPIError(Exception):
    """Base exception for Paperless API errors."""
    pass


class PaperlessAPI:
    """Client for interacting with Paperless-ngx REST API."""

    # Matching algorithm constants
    MATCH_NONE = 0
    MATCH_ANY = 1
    MATCH_ALL = 2
    MATCH_LITERAL = 3
    MATCH_REGEX = 4
    MATCH_FUZZY = 5
    MATCH_AUTO = 6

    def __init__(
        self,
        base_url: str,
        token: str = None,
        username: str = None,
        password: str = None,
        global_read: bool = True,
        api_version: int = 9,
        skip_ssl_verify: bool = False
    ):
        """
        Initialize the Paperless API client.

        Args:
            base_url: Base URL of the Paperless-ngx instance
            token: API token (preferred)
            username: Username for basic auth (alternative)
            password: Password for basic auth (alternative)
            global_read: If True, items have no owner (global read)
            api_version: API version to use
            skip_ssl_verify: If True, skip SSL certificate verification (insecure)
        """
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.global_read = global_read

        # Configure SSL verification
        if skip_ssl_verify:
            self.session.verify = False
            # Suppress urllib3 warnings about insecure requests
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Set up authentication
        if token:
            self.session.headers['Authorization'] = f'Token {token}'
        elif username and password:
            self.session.auth = (username, password)
        else:
            raise ValueError("Either token or username/password must be provided")

        # Set API version
        self.session.headers['Accept'] = f'application/json; version={api_version}'

        # Cache for tags and document types to avoid repeated API calls
        self._tags_cache: Dict[str, int] = {}
        self._document_types_cache: Dict[str, int] = {}

    def _get(self, endpoint: str, params: dict = None) -> dict:
        """Make a GET request to the API."""
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def _post(self, endpoint: str, data: dict = None, files: dict = None) -> dict:
        """Make a POST request to the API."""
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"

        if files:
            # Don't set Content-Type for multipart/form-data, let requests handle it
            response = self.session.post(url, data=data, files=files)
        else:
            response = self.session.post(url, json=data)

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error: {e}")
            logger.error(f"Response content: {response.text}")
            raise PaperlessAPIError(f"API request failed: {e}")
        return response.json()

    def _patch(self, endpoint: str, data: dict) -> dict:
        """Make a PATCH request to the API."""
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        response = self.session.patch(url, json=data)

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error: {e}")
            logger.error(f"Response content: {response.text}")
            raise PaperlessAPIError(f"API request failed: {e}")
        return response.json()

    # ========================================================================
    # Tag Management
    # ========================================================================

    def get_tag_by_id(self, tag_id: int) -> Optional[dict]:
        """
        Retrieve a tag by its ID.

        Args:
            tag_id: The tag ID

        Returns:
            Tag data or None if not found
        """
        try:
            return self._get(f'tags/{tag_id}/')
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def get_tag_by_name(self, name: str, normalize_for_actor: bool = False) -> Optional[dict]:
        """
        Search for a tag by exact name match.

        When normalize_for_actor=True, handles actor tags with parentheses keywords by matching 
        "HYPER BASALISK" against "HYPER BASALISK (inactive)". This should ONLY be used for 
        final actor tags, not for animal parents, countries, industries, or motivations.

        Args:
            name: Tag name (case-insensitive)
            normalize_for_actor: If True, also search using normalized name (strips parentheses)

        Returns:
            Tag data or None if not found
        """
        try:
            # First try exact match
            result = self._get('tags/', params={'name__iexact': name})
            if result['count'] > 0:
                return result['results'][0]

            # If requested and no exact match, search with normalization for actor tags
            # This handles cases where server has "HYPER BASALISK (inactive)"
            # but we're searching for "HYPER BASALISK" from a report
            if normalize_for_actor:
                from ..utils.constants import normalize_tag_name
                normalized_search = normalize_tag_name(name).upper()

                # Get all tags and check for normalized matches
                all_tags_result = self._get('tags/', params={'page_size': 1000})
                for tag in all_tags_result.get('results', []):
                    if normalize_tag_name(tag['name']).upper() == normalized_search:
                        return tag

        except requests.exceptions.HTTPError:
            pass
        return None

    def get_all_tags(self, page_size: int = 100) -> Dict[str, dict]:
        """
        Get all tags as a dictionary mapping name -> tag object.

        Args:
            page_size: Number of tags per page

        Returns:
            Dictionary of tag name (uppercase) -> tag data
        """
        tags_dict = {}
        page = 1

        try:
            while True:
                data = self._get('tags/', params={"page": page, "page_size": page_size})
                results = data.get("results", [])

                for tag in results:
                    tags_dict[tag["name"].upper()] = tag

                if not data.get("next"):
                    break
                page += 1

            return tags_dict
        except Exception as e:
            logger.error(f"Exception fetching tags: {e}")
            return {}

    def create_tag(
        self,
        name: str,
        color: str = "#3a86ff",
        is_inbox_tag: bool = False,
        matching_algorithm: int = None,
        parent: Optional[int] = None,
        match: Optional[str] = None
    ) -> dict:
        """
        Create a new tag.

        Args:
            name: Tag name
            color: Hex color code
            is_inbox_tag: Whether this is an inbox tag
            matching_algorithm: Matching algorithm constant
            parent: Parent tag ID for hierarchical tags
            match: Match string for auto-tagging

        Returns:
            Created tag data
        """
        if matching_algorithm is None:
            matching_algorithm = self.MATCH_ALL

        data = {
            "name": name,
            "color": color,
            "is_inbox_tag": is_inbox_tag,
            "matching_algorithm": matching_algorithm
        }

        # Set ownership based on global_read setting
        if self.global_read:
            data['owner'] = None

        if parent is not None:
            data["parent"] = parent

        if match is not None:
            data["match"] = match

        return self._post('tags/', data=data)

    def update_tag(self, tag_id: int, data: dict) -> dict:
        """
        Update a tag's properties.

        Args:
            tag_id: Tag ID
            data: Fields to update (e.g., {'name': 'New Name'})

        Returns:
            Updated tag data
        """
        result = self._patch(f'tags/{tag_id}/', data=data)

        # Invalidate cache entries for this tag since name may have changed
        # Remove all cache entries (we could be more selective, but this is safer)
        self._tags_cache.clear()

        return result

    def get_or_create_tag(
        self,
        tag_name: str,
        color: str = None,
        is_actor: bool = False,
        animal_parent_id: Optional[int] = None
    ) -> int:
        """
        Get the ID of a tag by name, or create it if it doesn't exist.

        Args:
            tag_name: Name of the tag
            color: Hex color for the tag (if None, uses default #a6cee3)
            is_actor: Whether this is an actor tag (needs hierarchy)
            animal_parent_id: Parent animal tag ID for actor tags

        Returns:
            Tag ID
        """
        # Check cache first
        if tag_name in self._tags_cache:
            return self._tags_cache[tag_name]

        # Search for existing tag
        # Only use normalization for actor tags (not for countries, industries, motivations, or animal parents)
        tag = self.get_tag_by_name(tag_name, normalize_for_actor=is_actor)
        if tag:
            tag_id = tag['id']
            self._tags_cache[tag_name] = tag_id
            logger.info(f"Found existing tag: {tag_name} (ID: {tag_id})")
            return tag_id

        # Use provided color or default
        if color is None:
            color = "#a6cee3"

        # Create new tag
        tag_data = {
            'name': tag_name,
            'color': color,
            'matching_algorithm': self.MATCH_LITERAL if is_actor else self.MATCH_ALL
        }

        if animal_parent_id:
            tag_data['parent'] = animal_parent_id

        if is_actor:
            tag_data['match'] = tag_name

        tag = self.create_tag(**tag_data)
        tag_id = tag['id']
        self._tags_cache[tag_name] = tag_id
        logger.info(f"Created tag: {tag_name} (ID: {tag_id})")
        return tag_id

    # ========================================================================
    # Document Type Management
    # ========================================================================

    def get_document_type_by_name(self, type_name: str) -> Optional[dict]:
        """
        Search for a document type by exact name match.

        Args:
            type_name: Document type name (case-insensitive)

        Returns:
            Document type data or None if not found
        """
        try:
            result = self._get('document_types/')
            for doc_type in result.get('results', []):
                if doc_type['name'].lower() == type_name.lower():
                    return doc_type
        except requests.exceptions.HTTPError:
            pass
        return None

    def create_document_type(self, name: str) -> dict:
        """
        Create a new document type.

        Args:
            name: Document type name

        Returns:
            Created document type data
        """
        data = {'name': name}
        if self.global_read:
            data['owner'] = None
        return self._post('document_types/', data=data)

    def get_or_create_document_type(self, type_name: str) -> int:
        """
        Get the ID of a document type by name, or create it if it doesn't exist.

        Args:
            type_name: Name of the document type

        Returns:
            Document type ID
        """
        # Check cache first
        if type_name in self._document_types_cache:
            return self._document_types_cache[type_name]

        # Search for existing document type
        doc_type = self.get_document_type_by_name(type_name)
        if doc_type:
            doc_type_id = doc_type['id']
            self._document_types_cache[type_name] = doc_type_id
            logger.info(f"Found existing document type: {type_name} (ID: {doc_type_id})")
            return doc_type_id

        # Create new document type
        doc_type = self.create_document_type(type_name)
        doc_type_id = doc_type['id']
        self._document_types_cache[type_name] = doc_type_id
        logger.info(f"Created document type: {type_name} (ID: {doc_type_id})")
        return doc_type_id

    # ========================================================================
    # Document Management
    # ========================================================================

    def upload_document(
        self,
        file_path,
        title: str = None,
        created_date: str = None,
        tag_ids: List[int] = None,
        document_type_id: int = None,
        archive_serial_number: str = None
    ) -> dict:
        """
        Upload a document to Paperless-ngx.

        Args:
            file_path: Path to the document file
            title: Title for the document
            created_date: Created date (YYYY-MM-DD format)
            tag_ids: List of tag IDs to assign
            document_type_id: Document type ID
            archive_serial_number: Optional archive serial number

        Returns:
            API response with task UUID and metadata for tracking
        """
        logger.info(f"Uploading document: {file_path}")

        # Prepare the form data
        form_data = {}

        if title:
            form_data['title'] = title

        if created_date:
            form_data['created'] = created_date

        if document_type_id:
            form_data['document_type'] = str(document_type_id)

        if archive_serial_number:
            form_data['archive_serial_number'] = archive_serial_number

        # Tags need to be added as multiple form fields
        if tag_ids:
            form_data['tags'] = [str(tag_id) for tag_id in tag_ids]

        # Open and upload the file
        # Read file content to avoid issues with file handle being closed before request completes
        with open(file_path, 'rb') as f:
            file_content = f.read()

        files = {
            'document': (file_path.name, file_content, 'application/pdf')
        }
        result = self._post('documents/post_document/', data=form_data, files=files)

        logger.info(f"Upload successful. Task ID: {result}")

        # Return task info for batch processing
        return {
            'task_id': result,
            'search_term': file_path.stem,
            'title': title
        }

    def search_documents(self, title_contains: str) -> dict:
        """
        Search for documents by title.

        Args:
            title_contains: String to search in title

        Returns:
            Search results
        """
        return self._get('documents/', params={'title__icontains': title_contains})

    def get_document_by_title(self, title: str) -> Optional[dict]:
        """
        Get a specific document by exact title match.

        Args:
            title: Exact title to search for

        Returns:
            Document data if found, None otherwise
        """
        result = self._get('documents/', params={'title__iexact': title})
        if result['count'] > 0:
            return result['results'][0]
        return None

    def delete_document(self, document_id: int) -> None:
        """
        Delete a document (moves to trash).

        Args:
            document_id: ID of document to delete
        """
        url = f"{self.base_url}/api/documents/{document_id}/"
        response = self.session.delete(url)
        response.raise_for_status()
        logger.info(f"Document {document_id} moved to trash")

    def empty_trash(self) -> None:
        """
        Empty the trash to permanently delete documents.
        """
        url = f"{self.base_url}/api/documents/empty_trash/"
        response = self.session.post(url)
        response.raise_for_status()
        logger.info("Trash emptied")

    def update_document(self, document_id: int, data: dict) -> dict:
        """
        Update a document's metadata.

        Args:
            document_id: Document ID
            data: Fields to update

        Returns:
            Updated document data
        """
        return self._patch(f'documents/{document_id}/', data=data)

    def update_document_permissions_batch(
        self,
        upload_results: List[dict],
        wait_time: int = 10,
        max_retries: int = 5
    ) -> dict:
        """
        Update permissions for a batch of uploaded documents.

        Args:
            upload_results: List of dicts with 'task_id', 'search_term', 'title'
            wait_time: Seconds to wait between retry attempts
            max_retries: Maximum number of attempts to find each document

        Returns:
            Dict with statistics: {'updated': int, 'not_found': int, 'failed': int}
        """
        if not self.global_read:
            logger.info("Global read disabled, skipping permission updates")
            return {'updated': 0, 'not_found': 0, 'failed': 0}

        stats = {'updated': 0, 'not_found': 0, 'failed': 0}

        logger.info(f"Waiting for {len(upload_results)} documents to be processed...")

        for result in upload_results:
            search_term = result['search_term']
            found = False

            for attempt in range(1, max_retries + 1):
                logger.info(f"Attempt {attempt}/{max_retries}: Searching for '{search_term}'")

                try:
                    search_result = self.search_documents(search_term)

                    if search_result['count'] > 0:
                        doc_id = search_result['results'][0]['id']
                        logger.info(f"Found document ID {doc_id} for '{search_term}'")

                        try:
                            self.update_document(doc_id, {'owner': None})
                            logger.info(f"Updated permissions for document {doc_id}")
                            stats['updated'] += 1
                            found = True
                            break
                        except Exception as e:
                            logger.error(f"Failed to update document {doc_id}: {e}")
                            stats['failed'] += 1
                            found = True
                            break
                    else:
                        logger.warning(f"Document not found yet (attempt {attempt})")
                        if attempt < max_retries:
                            time.sleep(wait_time)
                except Exception as e:
                    logger.error(f"Error searching for document: {e}")
                    if attempt < max_retries:
                        time.sleep(wait_time)

            if not found:
                logger.error(f"Document '{search_term}' not found after {max_retries} attempts")
                stats['not_found'] += 1

        logger.info(
            f"Batch update complete: {stats['updated']} updated, "
            f"{stats['not_found']} not found, {stats['failed']} failed"
        )
        return stats
