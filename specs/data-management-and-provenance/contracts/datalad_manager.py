"""
DataLad Manager API Contract

Defines the interface for DataLad dataset operations.
All implementations MUST use DataLad Python API exclusively (no CLI commands).
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional


class DataLadManagerInterface(ABC):
    """Interface for managing DataLad datasets."""

    @abstractmethod
    def create_dataset(
        self, path: Path, description: Optional[str] = None, force: bool = False
    ) -> dict[str, Any]:
        """
        Create a new DataLad dataset.

        Args:
            path: Absolute path where dataset should be created
            description: Human-readable dataset description
            force: If True, reinitialize existing dataset

        Returns:
            Dict containing:
                - path: Path to created dataset
                - is_installed: bool
                - git_sha: Initial commit hash

        Raises:
            DatasetExistsError: If dataset exists and force=False
            InvalidPathError: If path is invalid or inaccessible
        """
        pass

    @abstractmethod
    def install_subdataset(
        self,
        parent_path: Path,
        subdataset_path: str,
        source: str,
        recursive: bool = False,
        get_data: bool = False,
    ) -> dict[str, Any]:
        """
        Install a subdataset within a parent dataset.

        Args:
            parent_path: Path to parent dataset
            subdataset_path: Relative path within parent for subdataset
            source: URL or path to subdataset source
            recursive: If True, install nested subdatasets
            get_data: If True, download annexed content

        Returns:
            Dict containing:
                - subdataset_path: Path to installed subdataset
                - is_installed: bool
                - commit_sha: Commit hash recording installation

        Raises:
            DatasetNotFoundError: If parent dataset doesn't exist
            InstallationError: If installation fails
        """
        pass

    @abstractmethod
    def get_files(
        self, dataset_path: Path, file_paths: list[Path], recursive: bool = False
    ) -> dict[str, bool]:
        """
        Retrieve annexed file content from DataLad dataset.

        Args:
            dataset_path: Path to dataset
            file_paths: List of file paths to retrieve (relative to dataset)
            recursive: If True, get files from subdatasets

        Returns:
            Dict mapping file paths to success status

        Raises:
            DatasetNotFoundError: If dataset doesn't exist
            FileNotFoundError: If file doesn't exist in annex
        """
        pass

    @abstractmethod
    def save_changes(
        self,
        dataset_path: Path,
        message: str,
        paths: Optional[list[Path]] = None,
        recursive: bool = False,
    ) -> dict[str, Any]:
        """
        Save changes to DataLad dataset with commit message.

        Args:
            dataset_path: Path to dataset
            message: Descriptive commit message
            paths: Specific paths to save (None = save all changes)
            recursive: If True, save changes in subdatasets

        Returns:
            Dict containing:
                - commit_sha: Hash of created commit
                - files_saved: List of saved file paths
                - timestamp: Commit timestamp

        Raises:
            DatasetNotFoundError: If dataset doesn't exist
            SaveError: If save operation fails
        """
        pass

    @abstractmethod
    def configure_annex(
        self, dataset_path: Path, large_file_threshold_mb: int = 10
    ) -> None:
        """
        Configure .gitattributes for selective annexing.

        Args:
            dataset_path: Path to dataset
            large_file_threshold_mb: Files larger than this are annexed

        Configuration sets:
            - Files > threshold: annexed
            - Development files (.py, .md, etc.): not annexed
            - Binary data files: always annexed

        Raises:
            DatasetNotFoundError: If dataset doesn't exist
            ConfigurationError: If .gitattributes cannot be written
        """
        pass

    @abstractmethod
    def unlock_files(
        self, dataset_path: Path, file_paths: list[Path]
    ) -> dict[str, bool]:
        """
        Unlock annexed files for modification.

        Args:
            dataset_path: Path to dataset
            file_paths: List of file paths to unlock

        Returns:
            Dict mapping file paths to unlock success status

        Raises:
            DatasetNotFoundError: If dataset doesn't exist
            FileNotFoundError: If file doesn't exist
        """
        pass

    @abstractmethod
    def get_status(
        self, dataset_path: Path, include_subdatasets: bool = False
    ) -> dict[str, Any]:
        """
        Get current status of DataLad dataset.

        Args:
            dataset_path: Path to dataset
            include_subdatasets: If True, include subdataset status

        Returns:
            Dict containing:
                - is_installed: bool
                - clean: bool (no uncommitted changes)
                - modified_files: List[Path]
                - untracked_files: List[Path]
                - subdatasets: List[Dict] (if include_subdatasets=True)

        Raises:
            DatasetNotFoundError: If dataset doesn't exist
        """
        pass

    @abstractmethod
    def tag_version(
        self, dataset_path: Path, tag_name: str, message: Optional[str] = None
    ) -> str:
        """
        Tag the current dataset state with a version identifier.

        Args:
            dataset_path: Path to dataset
            tag_name: Tag identifier (e.g., "v1.0", "success-20251007")
            message: Optional tag annotation message

        Returns:
            Commit SHA that was tagged

        Raises:
            DatasetNotFoundError: If dataset doesn't exist
            TagExistsError: If tag already exists
        """
        pass
