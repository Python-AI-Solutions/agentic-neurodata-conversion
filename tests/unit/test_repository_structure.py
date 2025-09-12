"""Unit tests for DataLad repository structure management."""

import json
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch

import pytest

# Import the actual components
from agentic_neurodata_conversion.data_management.repository_structure import (
    DataLadRepositoryManager,
    TestDatasetManager,
)


@pytest.mark.unit
class TestDataLadRepositoryManager:
    """Test DataLad repository manager functionality."""

    def test_initialization(self):
        """Test repository manager initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DataLadRepositoryManager(base_path=temp_dir)
            assert manager.base_path == Path(temp_dir)
            assert isinstance(manager.structure, dict)
            assert "etl" in manager.structure
            assert "tests" in manager.structure
            assert "examples" in manager.structure

    def test_directory_structure_creation(self):
        """Test directory structure creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DataLadRepositoryManager(base_path=temp_dir)

            # Create directory structure without DataLad
            manager._setup_directory_structure(None)

            # Verify main directories
            base_path = Path(temp_dir)
            assert (base_path / "etl").exists()
            assert (base_path / "tests").exists()
            assert (base_path / "examples").exists()

            # Verify subdirectories
            assert (base_path / "etl" / "input-data").exists()
            assert (base_path / "etl" / "evaluation-data").exists()
            assert (base_path / "etl" / "workflows").exists()
            assert (base_path / "etl" / "prompt-input-data").exists()

            # Verify README files
            readme_path = base_path / "etl" / "input-data" / "README.md"
            assert readme_path.exists()
            content = readme_path.read_text()
            assert "Input Data" in content
            assert "Raw input datasets for testing" in content

    def test_gitattributes_configuration(self):
        """Test .gitattributes configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DataLadRepositoryManager(base_path=temp_dir)

            # Configure git attributes
            manager._configure_git_attributes(None)

            gitattributes_path = Path(temp_dir) / ".gitattributes"
            assert gitattributes_path.exists()

            content = gitattributes_path.read_text()

            # Check key rules
            assert "*.py annex.largefiles=nothing" in content
            assert "*.nwb annex.largefiles=anything" in content
            assert "*.csv annex.largefiles=(largerthan=10MB)" in content
            assert "*.json annex.largefiles=nothing" in content
            assert "*.zip annex.largefiles=anything" in content

    def test_datalad_initialization(self):
        """Test DataLad repository initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = DataLadRepositoryManager(base_path=temp_dir)

            # Mock DataLad operations
            with patch(
                "agentic_neurodata_conversion.data_management.repository_structure.dl"
            ) as mock_dl:
                mock_dataset = Mock()
                mock_dl.create.return_value = mock_dataset

                result = manager.initialize_development_repository()

                # Verify DataLad create was called
                mock_dl.create.assert_called_once_with(
                    path=temp_dir, description="Agentic Neurodata Converter"
                )
                assert result == mock_dataset


@pytest.mark.unit
class TestTestDatasetManager:
    """Test test dataset manager functionality."""

    def test_initialization(self):
        """Test dataset manager initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_manager = DataLadRepositoryManager(base_path=temp_dir)
            dataset_manager = TestDatasetManager(repo_manager)

            assert dataset_manager.repo_manager == repo_manager
            expected_path = Path(temp_dir) / "etl" / "input-data"
            assert dataset_manager.test_data_path == expected_path

    def test_add_test_dataset_file(self):
        """Test adding a single file as test dataset."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup repository structure
            repo_manager = DataLadRepositoryManager(base_path=temp_dir)
            repo_manager._setup_directory_structure(None)

            dataset_manager = TestDatasetManager(repo_manager)

            # Create a test file
            test_file = Path(temp_dir) / "test_data.txt"
            test_file.write_text("This is test data")

            # Add dataset
            success = dataset_manager.add_test_dataset(
                dataset_name="test_dataset",
                source_path=str(test_file),
                description="Test dataset for unit testing",
            )

            assert success

            # Verify dataset was copied
            dataset_path = Path(temp_dir) / "etl" / "input-data" / "test_dataset"
            assert dataset_path.exists()
            assert (dataset_path / "test_data.txt").exists()

            # Verify metadata was created
            metadata_path = dataset_path / "dataset_metadata.json"
            assert metadata_path.exists()

            metadata = json.loads(metadata_path.read_text())
            assert metadata["name"] == "test_dataset"
            assert metadata["description"] == "Test dataset for unit testing"
            assert "added_timestamp" in metadata

    def test_add_test_dataset_directory(self):
        """Test adding a directory as test dataset."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup repository structure
            repo_manager = DataLadRepositoryManager(base_path=temp_dir)
            repo_manager._setup_directory_structure(None)

            dataset_manager = TestDatasetManager(repo_manager)

            # Create a test directory with files
            test_dir = Path(temp_dir) / "source_dataset"
            test_dir.mkdir()
            (test_dir / "data1.txt").write_text("Data 1")
            (test_dir / "data2.txt").write_text("Data 2")

            # Add dataset
            success = dataset_manager.add_test_dataset(
                dataset_name="dir_dataset",
                source_path=str(test_dir),
                description="Directory test dataset",
                metadata={"format": "text", "size": "small"},
            )

            assert success

            # Verify dataset was copied
            dataset_path = Path(temp_dir) / "etl" / "input-data" / "dir_dataset"
            assert dataset_path.exists()
            assert (dataset_path / "data1.txt").exists()
            assert (dataset_path / "data2.txt").exists()

            # Verify metadata includes custom metadata
            metadata_path = dataset_path / "dataset_metadata.json"
            metadata = json.loads(metadata_path.read_text())
            assert metadata["custom_metadata"]["format"] == "text"
            assert metadata["custom_metadata"]["size"] == "small"

    def test_add_nonexistent_dataset(self):
        """Test adding a dataset from nonexistent source."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_manager = DataLadRepositoryManager(base_path=temp_dir)
            repo_manager._setup_directory_structure(None)

            dataset_manager = TestDatasetManager(repo_manager)

            # Try to add nonexistent dataset
            success = dataset_manager.add_test_dataset(
                dataset_name="missing_dataset",
                source_path="/nonexistent/path",
                description="This should fail",
            )

            assert not success

    def test_get_available_datasets_empty(self):
        """Test getting available datasets when none exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_manager = DataLadRepositoryManager(base_path=temp_dir)
            dataset_manager = TestDatasetManager(repo_manager)

            datasets = dataset_manager.get_available_datasets()
            assert datasets == []

    def test_get_available_datasets_with_data(self):
        """Test getting available datasets with existing data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup repository structure
            repo_manager = DataLadRepositoryManager(base_path=temp_dir)
            repo_manager._setup_directory_structure(None)

            dataset_manager = TestDatasetManager(repo_manager)

            # Add a test dataset
            test_file = Path(temp_dir) / "test_data.txt"
            test_file.write_text("Test data")

            dataset_manager.add_test_dataset(
                dataset_name="test_dataset",
                source_path=str(test_file),
                description="Test dataset",
            )

            # Get available datasets
            datasets = dataset_manager.get_available_datasets()

            assert len(datasets) == 1
            assert datasets[0]["name"] == "test_dataset"
            assert datasets[0]["description"] == "Test dataset"

    def test_get_available_datasets_without_metadata(self):
        """Test getting datasets that don't have metadata files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup repository structure
            repo_manager = DataLadRepositoryManager(base_path=temp_dir)
            repo_manager._setup_directory_structure(None)

            dataset_manager = TestDatasetManager(repo_manager)

            # Create a dataset directory without metadata
            dataset_path = Path(temp_dir) / "etl" / "input-data" / "manual_dataset"
            dataset_path.mkdir(parents=True)
            (dataset_path / "data.txt").write_text("Manual data")

            # Get available datasets
            datasets = dataset_manager.get_available_datasets()

            assert len(datasets) == 1
            assert datasets[0]["name"] == "manual_dataset"
            assert datasets[0]["description"] == "No metadata available"

    def test_install_subdataset(self):
        """Test installing a subdataset."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_manager = DataLadRepositoryManager(base_path=temp_dir)
            dataset_manager = TestDatasetManager(repo_manager)

            # Mock DataLad operations
            with patch(
                "agentic_neurodata_conversion.data_management.repository_structure.dl"
            ) as mock_dl:
                mock_subdataset = Mock()
                mock_dl.install.return_value = mock_subdataset

                # Mock Dataset class
                with patch(
                    "agentic_neurodata_conversion.data_management.repository_structure.Dataset"
                ) as mock_dataset_class:
                    mock_dataset = Mock()
                    mock_dataset_class.return_value = mock_dataset

                    success = dataset_manager.install_subdataset(
                        subdataset_url="https://example.com/dataset.git",
                        subdataset_path="external/example_dataset",
                    )

                    assert success
                    mock_dl.install.assert_called_once()


@pytest.mark.unit
class TestDataLadAvailability:
    """Test handling of DataLad availability."""

    def test_datalad_not_available_warning(self):
        """Test that appropriate warnings are logged when DataLad is not available."""
        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch(
                "agentic_neurodata_conversion.data_management.repository_structure.DATALAD_AVAILABLE",
                False,
            ),
        ):
            manager = DataLadRepositoryManager(base_path=temp_dir)

            # Should still be able to create directory structure
            manager._setup_directory_structure(None)

            # Verify directories were created
            base_path = Path(temp_dir)
            assert (base_path / "etl" / "input-data").exists()

            # DataLad operations should return None
            result = manager.initialize_development_repository()
            assert result is None
