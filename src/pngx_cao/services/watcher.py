"""
File system watcher service for monitoring and uploading documents.

This service watches a directory for new document folders and automatically
uploads them when they're ready.
"""

import logging
import time
from pathlib import Path
from typing import Callable, Optional, Set
from threading import Lock

logger = logging.getLogger(__name__)


class FolderStabilizer:
    """
    Checks if a folder's contents have stabilized (no longer being written).

    This prevents uploading files that are still being extracted or copied.
    """

    def __init__(self, stability_wait: float = 2.0, check_interval: float = 0.5):
        """
        Initialize the stabilizer.

        Args:
            stability_wait: Seconds to wait for no changes before considering stable
            check_interval: Seconds between stability checks
        """
        self.stability_wait = stability_wait
        self.check_interval = check_interval

    def is_folder_stable(self, folder_path: Path) -> bool:
        """
        Check if a folder's contents have stabilized.

        Args:
            folder_path: Path to the folder to check

        Returns:
            True if folder is stable (ready to process)
        """
        if not folder_path.exists() or not folder_path.is_dir():
            return False

        try:
            # Get initial state
            initial_state = self._get_folder_state(folder_path)

            # Wait for stability_wait seconds
            time.sleep(self.stability_wait)

            # Check if state has changed
            final_state = self._get_folder_state(folder_path)

            # Folder is stable if state hasn't changed
            return initial_state == final_state

        except (OSError, PermissionError) as e:
            logger.warning(f"Error checking folder stability: {e}")
            return False

    def _get_folder_state(self, folder_path: Path) -> dict:
        """
        Get the current state of a folder (file sizes and count).

        Args:
            folder_path: Path to the folder

        Returns:
            Dictionary with folder state information
        """
        state = {
            'file_count': 0,
            'total_size': 0,
            'files': {}
        }

        try:
            for file_path in folder_path.iterdir():
                if file_path.is_file():
                    state['file_count'] += 1
                    state['total_size'] += file_path.stat().st_size
                    state['files'][file_path.name] = file_path.stat().st_size
        except (OSError, PermissionError):
            pass

        return state


class WatcherService:
    """
    Service for watching a directory and processing new folders.

    This implements a polling-based approach for maximum compatibility
    across platforms and file systems (including network shares).
    """

    def __init__(
        self,
        watch_dir: Path,
        upload_callback: Callable[[Path], bool],
        stabilizer: Optional[FolderStabilizer] = None,
        poll_interval: float = 5.0
    ):
        """
        Initialize the watcher service.

        Args:
            watch_dir: Directory to watch for new folders
            upload_callback: Function to call when a folder is ready (returns success bool)
            stabilizer: FolderStabilizer instance (creates default if None)
            poll_interval: Seconds between directory scans
        """
        self.watch_dir = watch_dir
        self.upload_callback = upload_callback
        self.stabilizer = stabilizer or FolderStabilizer()
        self.poll_interval = poll_interval

        # Track processed folders to avoid reprocessing
        self._processed: Set[str] = set()
        self._processing: Set[str] = set()
        self._lock = Lock()

        self._running = False

    def start(self) -> None:
        """
        Start watching the directory.

        This is a blocking call that runs until stop() is called or interrupted.
        """
        if not self.watch_dir.exists():
            raise FileNotFoundError(f"Watch directory does not exist: {self.watch_dir}")

        if not self.watch_dir.is_dir():
            raise NotADirectoryError(f"Watch path is not a directory: {self.watch_dir}")

        logger.info(f"Starting watcher on: {self.watch_dir}")
        logger.info(f"Poll interval: {self.poll_interval}s")

        self._running = True

        try:
            while self._running:
                self._scan_for_new_folders()
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            logger.info("Watcher interrupted by user")
        finally:
            self._running = False

    def stop(self) -> None:
        """Stop watching the directory."""
        self._running = False

    def _scan_for_new_folders(self) -> None:
        """Scan the watch directory for new folders to process."""
        try:
            for item in self.watch_dir.iterdir():
                if not item.is_dir():
                    continue

                folder_name = item.name

                # Skip if already processed or currently processing
                with self._lock:
                    if folder_name in self._processed or folder_name in self._processing:
                        continue

                    # Mark as processing
                    self._processing.add(folder_name)

                try:
                    # Process the folder
                    self._process_new_folder(item)
                finally:
                    # Move from processing to processed
                    with self._lock:
                        self._processing.discard(folder_name)
                        self._processed.add(folder_name)

        except (OSError, PermissionError) as e:
            logger.error(f"Error scanning directory: {e}")

    def _process_new_folder(self, folder_path: Path) -> None:
        """
        Process a newly detected folder.

        Args:
            folder_path: Path to the folder to process
        """
        logger.info(f"New folder detected: {folder_path.name}")

        # Wait for folder to stabilize
        logger.debug(f"Waiting for folder to stabilize: {folder_path.name}")

        if not self.stabilizer.is_folder_stable(folder_path):
            logger.warning(f"Folder is still being written: {folder_path.name}")
            # Don't mark as processed, will retry on next scan
            with self._lock:
                self._processing.discard(folder_path.name)
            return

        logger.info(f"Folder is stable, uploading: {folder_path.name}")

        # Call the upload callback
        try:
            success = self.upload_callback(folder_path)
            if success:
                logger.info(f"Successfully uploaded: {folder_path.name}")
            else:
                logger.warning(f"Upload failed for: {folder_path.name}")
        except Exception as e:
            logger.error(f"Error uploading {folder_path.name}: {e}", exc_info=True)

    def get_processed_count(self) -> int:
        """Get the number of folders that have been processed."""
        with self._lock:
            return len(self._processed)

    def reset_processed(self) -> None:
        """Reset the processed folders set (useful for testing)."""
        with self._lock:
            self._processed.clear()
