"""
Test watcher service functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock
from src.pngx_cao.services.watcher import FolderStabilizer, WatcherService


class TestFolderStabilizer:
    """Test FolderStabilizer class."""

    def test_initialization(self):
        """Test stabilizer initialization with custom values."""
        stabilizer = FolderStabilizer(stability_wait=3.0, check_interval=1.0)
        assert stabilizer.stability_wait == 3.0
        assert stabilizer.check_interval == 1.0

    def test_initialization_defaults(self):
        """Test stabilizer initialization with defaults."""
        stabilizer = FolderStabilizer()
        assert stabilizer.stability_wait == 2.0
        assert stabilizer.check_interval == 0.5

    def test_is_folder_stable_nonexistent(self):
        """Test stability check on non-existent folder."""
        stabilizer = FolderStabilizer(stability_wait=0.1)
        result = stabilizer.is_folder_stable(Path("/nonexistent/path"))
        assert result is False

    def test_is_folder_stable_file_not_directory(self, tmp_path):
        """Test stability check on a file instead of directory."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        stabilizer = FolderStabilizer(stability_wait=0.1)
        result = stabilizer.is_folder_stable(test_file)
        assert result is False

    def test_is_folder_stable_empty_folder(self, tmp_path):
        """Test stability check on empty folder."""
        test_dir = tmp_path / "empty"
        test_dir.mkdir()

        stabilizer = FolderStabilizer(stability_wait=0.1)
        result = stabilizer.is_folder_stable(test_dir)
        assert result is True

    def test_is_folder_stable_with_files(self, tmp_path):
        """Test stability check on folder with files."""
        test_dir = tmp_path / "with_files"
        test_dir.mkdir()

        (test_dir / "file1.txt").write_text("content1")
        (test_dir / "file2.txt").write_text("content2")

        stabilizer = FolderStabilizer(stability_wait=0.1)
        result = stabilizer.is_folder_stable(test_dir)
        assert result is True

    def test_get_folder_state(self, tmp_path):
        """Test getting folder state."""
        test_dir = tmp_path / "state_test"
        test_dir.mkdir()

        (test_dir / "file1.txt").write_text("abc")  # 3 bytes
        (test_dir / "file2.txt").write_text("12345")  # 5 bytes

        stabilizer = FolderStabilizer()
        state = stabilizer._get_folder_state(test_dir)

        assert state['file_count'] == 2
        assert state['total_size'] == 8
        assert 'file1.txt' in state['files']
        assert 'file2.txt' in state['files']
        assert state['files']['file1.txt'] == 3
        assert state['files']['file2.txt'] == 5


class TestWatcherService:
    """Test WatcherService class."""

    def test_initialization(self, tmp_path):
        """Test watcher initialization."""
        callback = Mock()
        watcher = WatcherService(
            watch_dir=tmp_path,
            upload_callback=callback,
            poll_interval=1.0
        )

        assert watcher.watch_dir == tmp_path
        assert watcher.upload_callback == callback
        assert watcher.poll_interval == 1.0
        assert isinstance(watcher.stabilizer, FolderStabilizer)

    def test_initialization_custom_stabilizer(self, tmp_path):
        """Test watcher initialization with custom stabilizer."""
        callback = Mock()
        custom_stabilizer = FolderStabilizer(stability_wait=5.0)

        watcher = WatcherService(
            watch_dir=tmp_path,
            upload_callback=callback,
            stabilizer=custom_stabilizer
        )

        assert watcher.stabilizer == custom_stabilizer

    def test_start_nonexistent_directory(self):
        """Test starting watcher on non-existent directory."""
        callback = Mock()
        watcher = WatcherService(
            watch_dir=Path("/nonexistent"),
            upload_callback=callback
        )

        with pytest.raises(FileNotFoundError):
            watcher.start()

    def test_start_not_a_directory(self, tmp_path):
        """Test starting watcher on a file instead of directory."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        callback = Mock()
        watcher = WatcherService(
            watch_dir=test_file,
            upload_callback=callback
        )

        with pytest.raises(NotADirectoryError):
            watcher.start()

    def test_process_new_folder_stable(self, tmp_path):
        """Test processing a stable folder."""
        test_dir = tmp_path / "test_folder"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")

        callback = Mock(return_value=True)
        stabilizer = Mock()
        stabilizer.is_folder_stable.return_value = True

        watcher = WatcherService(
            watch_dir=tmp_path,
            upload_callback=callback,
            stabilizer=stabilizer
        )

        watcher._process_new_folder(test_dir)

        callback.assert_called_once_with(test_dir)

    def test_process_new_folder_unstable(self, tmp_path):
        """Test processing an unstable folder."""
        test_dir = tmp_path / "test_folder"
        test_dir.mkdir()

        callback = Mock()
        stabilizer = Mock()
        stabilizer.is_folder_stable.return_value = False

        watcher = WatcherService(
            watch_dir=tmp_path,
            upload_callback=callback,
            stabilizer=stabilizer
        )

        watcher._process_new_folder(test_dir)

        # Should not call callback for unstable folder
        callback.assert_not_called()

    def test_process_new_folder_upload_fails(self, tmp_path):
        """Test handling upload failure."""
        test_dir = tmp_path / "test_folder"
        test_dir.mkdir()

        callback = Mock(return_value=False)
        stabilizer = Mock()
        stabilizer.is_folder_stable.return_value = True

        watcher = WatcherService(
            watch_dir=tmp_path,
            upload_callback=callback,
            stabilizer=stabilizer
        )

        # Should not raise exception
        watcher._process_new_folder(test_dir)

        callback.assert_called_once()

    def test_process_new_folder_exception(self, tmp_path):
        """Test handling callback exception."""
        test_dir = tmp_path / "test_folder"
        test_dir.mkdir()

        callback = Mock(side_effect=Exception("Upload error"))
        stabilizer = Mock()
        stabilizer.is_folder_stable.return_value = True

        watcher = WatcherService(
            watch_dir=tmp_path,
            upload_callback=callback,
            stabilizer=stabilizer
        )

        # Should not propagate exception
        watcher._process_new_folder(test_dir)

        callback.assert_called_once()

    def test_scan_for_new_folders(self, tmp_path):
        """Test scanning for new folders."""
        # Create test folders
        folder1 = tmp_path / "folder1"
        folder1.mkdir()
        folder2 = tmp_path / "folder2"
        folder2.mkdir()

        # Create a file (should be ignored)
        (tmp_path / "file.txt").write_text("content")

        callback = Mock(return_value=True)
        stabilizer = Mock()
        stabilizer.is_folder_stable.return_value = True

        watcher = WatcherService(
            watch_dir=tmp_path,
            upload_callback=callback,
            stabilizer=stabilizer,
            poll_interval=0.1
        )

        watcher._scan_for_new_folders()

        # Should process both folders
        assert callback.call_count == 2

    def test_scan_avoids_reprocessing(self, tmp_path):
        """Test that already processed folders are not reprocessed."""
        folder1 = tmp_path / "folder1"
        folder1.mkdir()

        callback = Mock(return_value=True)
        stabilizer = Mock()
        stabilizer.is_folder_stable.return_value = True

        watcher = WatcherService(
            watch_dir=tmp_path,
            upload_callback=callback,
            stabilizer=stabilizer
        )

        # First scan
        watcher._scan_for_new_folders()
        assert callback.call_count == 1

        # Second scan (should not reprocess)
        watcher._scan_for_new_folders()
        assert callback.call_count == 1

    def test_get_processed_count(self, tmp_path):
        """Test getting processed count."""
        callback = Mock()
        watcher = WatcherService(
            watch_dir=tmp_path,
            upload_callback=callback
        )

        assert watcher.get_processed_count() == 0

        # Manually add processed folders
        watcher._processed.add("folder1")
        watcher._processed.add("folder2")

        assert watcher.get_processed_count() == 2

    def test_reset_processed(self, tmp_path):
        """Test resetting processed folders."""
        callback = Mock()
        watcher = WatcherService(
            watch_dir=tmp_path,
            upload_callback=callback
        )

        watcher._processed.add("folder1")
        watcher._processed.add("folder2")
        assert watcher.get_processed_count() == 2

        watcher.reset_processed()
        assert watcher.get_processed_count() == 0

    def test_stop(self, tmp_path):
        """Test stopping the watcher."""
        callback = Mock()
        watcher = WatcherService(
            watch_dir=tmp_path,
            upload_callback=callback
        )

        watcher._running = True
        watcher.stop()
        assert watcher._running is False


class TestWatcherIntegration:
    """Integration tests for watcher service."""

    def test_watch_and_upload_new_folder(self, tmp_path):
        """Test watching and uploading a new folder."""
        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()

        callback = Mock(return_value=True)
        stabilizer = FolderStabilizer(stability_wait=0.1)

        watcher = WatcherService(
            watch_dir=watch_dir,
            upload_callback=callback,
            stabilizer=stabilizer,
            poll_interval=0.1
        )

        # Create a new folder after watcher is set up
        new_folder = watch_dir / "new_document"
        new_folder.mkdir()
        (new_folder / "document.pdf").write_text("PDF content")
        (new_folder / "document.json").write_text('{"name": "test"}')

        # Run one scan
        watcher._scan_for_new_folders()

        # Callback should be called
        callback.assert_called_once()
        assert callback.call_args[0][0] == new_folder

    def test_multiple_folders_processed_in_order(self, tmp_path):
        """Test that multiple folders are processed."""
        watch_dir = tmp_path / "watch"
        watch_dir.mkdir()

        # Create folders before watching
        folder1 = watch_dir / "doc1"
        folder1.mkdir()
        folder2 = watch_dir / "doc2"
        folder2.mkdir()

        processed_folders = []

        def track_callback(folder_path: Path) -> bool:
            processed_folders.append(folder_path.name)
            return True

        stabilizer = FolderStabilizer(stability_wait=0.1)

        watcher = WatcherService(
            watch_dir=watch_dir,
            upload_callback=track_callback,
            stabilizer=stabilizer
        )

        watcher._scan_for_new_folders()

        # Both folders should be processed
        assert len(processed_folders) == 2
        assert "doc1" in processed_folders
        assert "doc2" in processed_folders
