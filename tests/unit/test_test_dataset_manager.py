"""
Test suite for TestDatasetManager functionality.

Tests the test dataset management system including dataset addition,
metadata tracking, subdataset management, and dataset discovery.
"""

import json
from pathlib import Path
import shutil
import tempfile

import pytest

# Import the components we're testing
from agentic_neurodata_conversion.data_management.repository_structure import (
    DataLadRepositoryManager,
    TestDatasetManager,
)


@pytest.fixture
def temp_repo_dir():
    """Create a temporary directory for repository testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_source_data(temp_repo_dir):
    """Create temporary source data for testing."""
    source_dir = temp_repo_dir / "source_data"
    source_dir.mkdir()

    # Create some test files
    (source_dir / "data.csv").write_text(
        "timestamp,channel1,channel2\n1,0.1,0.2\n2,0.3,0.4\n"
    )
    (source_dir / "metadata.json").write_text('{"experiment": "test", "channels": 2}')
    (source_dir / "events.txt").write_text("1.0 stimulus_on\n2.0 stimulus_off\n")

    return source_dir


@pytest.fixture
def repository_manager(temp_repo_dir):
    """Create a DataLadRepositoryManager for testing."""
    return DataLadRepositoryManager(str(temp_repo_dir))


@pytest.fixture
def dataset_manager(repository_manager):
    """Create a TestDatasetManager for testing."""
    return TestDatasetManager(repository_manager)


@pytest.mark.unit
class TestTestDatasetManagerInitialization:
    """Test TestDatasetManager initialization and setup."""

    def test_initialization(self, repository_manager):
        """Test that TestDatasetManager initializes correctly."""
        manager = TestDatasetManager(repository_manager)

        assert manager.repo_manager == repository_manager
        assert manager.logger is not None
        assert manager.test_data_path.name == "input-data"
        assert manager.evaluation_data_path.name == "evaluation-data"
        assert manager.conversion_examples_path.name == "conversion-examples"

    def test_directory_creation(self, dataset_manager):
        """Test that required directories are created during initialization."""
        # Directories should be created during initialization
        assert dataset_manager.test_data_path.exists()
        assert dataset_manager.evaluation_data_path.exists()
        assert dataset_manager.conversion_examples_path.exists()


@pytest.mark.unit
class TestDatasetAddition:
    """Test dataset addition functionality."""

    def test_add_test_dataset_success(self, dataset_manager, temp_source_data):
        """Test successful addition of a test dataset."""
        result = dataset_manager.add_test_dataset(
            dataset_name="test_dataset",
            source_path=str(temp_source_data),
            description="Test dataset for unit testing",
            metadata={"experiment_type": "unit_test"},
        )

        assert result is True

        # Check that dataset directory was created
        dataset_path = dataset_manager.test_data_path / "test_dataset"
        assert dataset_path.exists()

        # Check that files were copied
        assert (dataset_path / "data.csv").exists()
        assert (dataset_path / "metadata.json").exists()
        assert (dataset_path / "events.txt").exists()

        # Check that metadata file was created
        metadata_file = dataset_path / "dataset_metadata.json"
        assert metadata_file.exists()

        metadata = json.loads(metadata_file.read_text())
        assert metadata["name"] == "test_dataset"
        assert metadata["description"] == "Test dataset for unit testing"
        assert metadata["dataset_type"] == "test"
        assert metadata["custom_metadata"]["experiment_type"] == "unit_test"
        assert metadata["file_count"] > 0
        assert metadata["size_bytes"] > 0

        # Check that README was created
        readme_file = dataset_path / "README.md"
        assert readme_file.exists()
        readme_content = readme_file.read_text()
        assert "test_dataset" in readme_content
        assert "Test dataset for unit testing" in readme_content

    def test_add_evaluation_dataset(self, dataset_manager, temp_source_data):
        """Test addition of an evaluation dataset."""
        result = dataset_manager.add_test_dataset(
            dataset_name="eval_dataset",
            source_path=str(temp_source_data),
            description="Evaluation dataset",
            dataset_type="evaluation",
        )

        assert result is True

        # Check that dataset was placed in evaluation directory
        dataset_path = dataset_manager.evaluation_data_path / "eval_dataset"
        assert dataset_path.exists()

        # Check metadata
        metadata_file = dataset_path / "dataset_metadata.json"
        metadata = json.loads(metadata_file.read_text())
        assert metadata["dataset_type"] == "evaluation"

    def test_add_example_dataset(self, dataset_manager, temp_source_data):
        """Test addition of an example dataset."""
        result = dataset_manager.add_test_dataset(
            dataset_name="example_dataset",
            source_path=str(temp_source_data),
            description="Example conversion dataset",
            dataset_type="example",
        )

        assert result is True

        # Check that dataset was placed in examples directory
        dataset_path = dataset_manager.conversion_examples_path / "example_dataset"
        assert dataset_path.exists()

        # Check metadata
        metadata_file = dataset_path / "dataset_metadata.json"
        metadata = json.loads(metadata_file.read_text())
        assert metadata["dataset_type"] == "example"

    def test_add_dataset_nonexistent_source(self, dataset_manager):
        """Test adding dataset with nonexistent source path."""
        result = dataset_manager.add_test_dataset(
            dataset_name="missing_dataset",
            source_path="/nonexistent/path",
            description="This should fail",
        )

        assert result is False

        # Check that no dataset directory was created
        dataset_path = dataset_manager.test_data_path / "missing_dataset"
        assert not dataset_path.exists()

    def test_add_single_file_dataset(self, dataset_manager, temp_source_data):
        """Test adding a dataset from a single file."""
        single_file = temp_source_data / "data.csv"

        result = dataset_manager.add_test_dataset(
            dataset_name="single_file_dataset",
            source_path=str(single_file),
            description="Single file dataset",
        )

        assert result is True

        # Check that dataset directory was created with the file
        dataset_path = dataset_manager.test_data_path / "single_file_dataset"
        assert dataset_path.exists()
        assert (dataset_path / "data.csv").exists()


@pytest.mark.unit
class TestDatasetDiscovery:
    """Test dataset discovery and listing functionality."""

    def test_get_available_datasets_empty(self, dataset_manager):
        """Test getting available datasets when none exist."""
        datasets = dataset_manager.get_available_datasets()
        assert datasets == []

    def test_get_available_datasets_with_data(self, dataset_manager, temp_source_data):
        """Test getting available datasets after adding some."""
        # Add test datasets
        dataset_manager.add_test_dataset("test1", str(temp_source_data), "Test 1")
        dataset_manager.add_test_dataset(
            "eval1", str(temp_source_data), "Eval 1", dataset_type="evaluation"
        )
        dataset_manager.add_test_dataset(
            "example1", str(temp_source_data), "Example 1", dataset_type="example"
        )

        # Get all datasets
        all_datasets = dataset_manager.get_available_datasets()
        assert len(all_datasets) == 3

        dataset_names = [d["name"] for d in all_datasets]
        assert "test1" in dataset_names
        assert "eval1" in dataset_names
        assert "example1" in dataset_names

    def test_get_datasets_by_type(self, dataset_manager, temp_source_data):
        """Test filtering datasets by type."""
        # Add datasets of different types
        dataset_manager.add_test_dataset("test1", str(temp_source_data), "Test 1")
        dataset_manager.add_test_dataset(
            "eval1", str(temp_source_data), "Eval 1", dataset_type="evaluation"
        )

        # Get only test datasets
        test_datasets = dataset_manager.get_available_datasets(dataset_type="test")
        assert len(test_datasets) == 1
        assert test_datasets[0]["name"] == "test1"

        # Get only evaluation datasets
        eval_datasets = dataset_manager.get_available_datasets(
            dataset_type="evaluation"
        )
        assert len(eval_datasets) == 1
        assert eval_datasets[0]["name"] == "eval1"

    def test_get_dataset_path(self, dataset_manager, temp_source_data):
        """Test getting path to a specific dataset."""
        dataset_manager.add_test_dataset(
            "test_path", str(temp_source_data), "Test path"
        )

        # Test getting existing dataset path
        path = dataset_manager.get_dataset_path("test_path")
        assert path is not None
        assert path.exists()
        assert path.name == "test_path"

        # Test getting nonexistent dataset path
        missing_path = dataset_manager.get_dataset_path("nonexistent")
        assert missing_path is None

    def test_get_datasets_by_format(self, dataset_manager, temp_source_data):
        """Test filtering datasets by detected format."""
        dataset_manager.add_test_dataset(
            "csv_dataset", str(temp_source_data), "CSV dataset"
        )

        # Get datasets by format
        csv_datasets = dataset_manager.get_datasets_by_format("generic_csv")
        assert len(csv_datasets) >= 1

        # Check that the dataset has the expected format
        found_dataset = next(
            (d for d in csv_datasets if d["name"] == "csv_dataset"), None
        )
        assert found_dataset is not None
        assert found_dataset["format_detected"] == "generic_csv"


@pytest.mark.unit
class TestDatasetRemoval:
    """Test dataset removal functionality."""

    def test_remove_existing_dataset(self, dataset_manager, temp_source_data):
        """Test removing an existing dataset."""
        # Add a dataset first
        dataset_manager.add_test_dataset(
            "to_remove", str(temp_source_data), "Will be removed"
        )

        # Verify it exists
        assert dataset_manager.get_dataset_path("to_remove") is not None

        # Remove it
        result = dataset_manager.remove_dataset("to_remove")
        assert result is True

        # Verify it's gone
        assert dataset_manager.get_dataset_path("to_remove") is None

    def test_remove_nonexistent_dataset(self, dataset_manager):
        """Test removing a dataset that doesn't exist."""
        result = dataset_manager.remove_dataset("nonexistent")
        assert result is True  # Should return True (already removed)


@pytest.mark.unit
class TestFormatDetection:
    """Test dataset format detection functionality."""

    def test_detect_csv_format(self, dataset_manager):
        """Test detection of CSV format."""
        # Create a temporary directory with CSV files
        temp_dir = dataset_manager.test_data_path / "csv_test"
        temp_dir.mkdir()
        (temp_dir / "data.csv").write_text("col1,col2\n1,2\n")

        format_detected = dataset_manager._detect_format(temp_dir)
        assert format_detected == "generic_csv"

    def test_detect_open_ephys_format(self, dataset_manager):
        """Test detection of Open Ephys format."""
        temp_dir = dataset_manager.test_data_path / "oe_test"
        temp_dir.mkdir()
        (temp_dir / "100_CH1.continuous").write_text("fake continuous data")

        format_detected = dataset_manager._detect_format(temp_dir)
        assert format_detected == "open_ephys"

    def test_detect_spikeglx_format(self, dataset_manager):
        """Test detection of SpikeGLX format."""
        temp_dir = dataset_manager.test_data_path / "sglx_test"
        temp_dir.mkdir()
        (temp_dir / "test_g0_t0.imec0.ap.bin").write_text("fake binary data")

        format_detected = dataset_manager._detect_format(temp_dir)
        assert format_detected == "spikeglx"

    def test_detect_unknown_format(self, dataset_manager):
        """Test detection of unknown format."""
        temp_dir = dataset_manager.test_data_path / "unknown_test"
        temp_dir.mkdir()
        (temp_dir / "unknown.xyz").write_text("unknown format")

        format_detected = dataset_manager._detect_format(temp_dir)
        assert format_detected == "unknown"


@pytest.mark.unit
class TestUtilityMethods:
    """Test utility methods of TestDatasetManager."""

    def test_count_files(self, dataset_manager, temp_source_data):
        """Test file counting functionality."""
        count = dataset_manager._count_files(temp_source_data)
        assert count == 3  # data.csv, metadata.json, events.txt

        # Test with single file
        single_file = temp_source_data / "data.csv"
        count = dataset_manager._count_files(single_file)
        assert count == 1

    def test_get_directory_size(self, dataset_manager, temp_source_data):
        """Test directory size calculation."""
        size = dataset_manager._get_directory_size(temp_source_data)
        assert size > 0

        # Test with single file
        single_file = temp_source_data / "data.csv"
        file_size = dataset_manager._get_directory_size(single_file)
        assert file_size > 0
        assert file_size < size  # Single file should be smaller than directory


@pytest.mark.integration
class TestSubdatasetManagement:
    """Test subdataset management functionality (requires DataLad)."""

    @pytest.mark.skipif(True, reason="Requires DataLad installation and network access")
    def test_install_subdataset(self, dataset_manager):
        """Test installing a subdataset."""
        # This test would require a real DataLad repository URL
        # Skipped for now as it requires network access and DataLad installation
        pass

    @pytest.mark.skipif(True, reason="Requires DataLad installation")
    def test_list_subdatasets(self, dataset_manager):
        """Test listing installed subdatasets."""
        # This test would require DataLad to be installed
        subdatasets = dataset_manager.list_subdatasets()
        assert isinstance(subdatasets, list)

    @pytest.mark.skipif(True, reason="Requires DataLad installation")
    def test_update_subdataset(self, dataset_manager):
        """Test updating an existing subdataset."""
        # This test would require an existing subdataset
        pass


@pytest.mark.unit
class TestDatasetMetadata:
    """Test dataset metadata handling."""

    def test_metadata_file_creation(self, dataset_manager, temp_source_data):
        """Test that metadata files are created with correct information."""
        custom_metadata = {"experiment_id": "EXP001", "researcher": "Test User"}

        dataset_manager.add_test_dataset(
            dataset_name="metadata_test",
            source_path=str(temp_source_data),
            description="Testing metadata creation",
            metadata=custom_metadata,
        )

        metadata_file = (
            dataset_manager.test_data_path / "metadata_test" / "dataset_metadata.json"
        )
        assert metadata_file.exists()

        metadata = json.loads(metadata_file.read_text())

        # Check required fields
        assert metadata["name"] == "metadata_test"
        assert metadata["description"] == "Testing metadata creation"
        assert metadata["dataset_type"] == "test"
        assert "added_timestamp" in metadata
        assert "added_date" in metadata
        assert "file_count" in metadata
        assert "size_bytes" in metadata
        assert "format_detected" in metadata
        assert metadata["version"] == "1.0"

        # Check custom metadata
        assert metadata["custom_metadata"]["experiment_id"] == "EXP001"
        assert metadata["custom_metadata"]["researcher"] == "Test User"

    def test_readme_creation(self, dataset_manager, temp_source_data):
        """Test that README files are created for datasets."""
        dataset_manager.add_test_dataset(
            dataset_name="readme_test",
            source_path=str(temp_source_data),
            description="Testing README creation",
        )

        readme_file = dataset_manager.test_data_path / "readme_test" / "README.md"
        assert readme_file.exists()

        readme_content = readme_file.read_text()
        assert "readme_test" in readme_content
        assert "Testing README creation" in readme_content
        assert "Dataset Information" in readme_content
        assert "Usage" in readme_content
