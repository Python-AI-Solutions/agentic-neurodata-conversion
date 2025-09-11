"""
Integration tests for TestDatasetManager with existing test infrastructure.

Tests the integration between TestDatasetManager and the existing
test dataset infrastructure in the tests/datasets directory.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

# Import the components we're testing
try:
    from agentic_neurodata_conversion.data_management.repository_structure import (
        DataLadRepositoryManager,
        TestDatasetManager
    )
    COMPONENTS_AVAILABLE = True
except ImportError:
    # Components not implemented yet
    DataLadRepositoryManager = None
    TestDatasetManager = None
    COMPONENTS_AVAILABLE = False

# Skip all tests if components are not implemented
pytestmark = pytest.mark.skipif(
    not COMPONENTS_AVAILABLE,
    reason="TestDatasetManager components not implemented yet"
)


@pytest.fixture
def temp_repo_dir():
    """Create a temporary directory for repository testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_datasets_dir(temp_repo_dir):
    """Create sample datasets similar to those in tests/datasets."""
    datasets_dir = temp_repo_dir / "sample_datasets"
    datasets_dir.mkdir()
    
    # Create Open Ephys-like dataset
    oe_dir = datasets_dir / "open_ephys_sample"
    oe_dir.mkdir()
    (oe_dir / "100_CH1.continuous").write_bytes(b"fake continuous data")
    (oe_dir / "100_CH2.continuous").write_bytes(b"fake continuous data")
    (oe_dir / "events.txt").write_text("1.0 stimulus_on\n2.0 stimulus_off\n")
    (oe_dir / "metadata.json").write_text('{"format": "open_ephys", "channels": 2}')
    
    # Create SpikeGLX-like dataset
    sglx_dir = datasets_dir / "spikeglx_sample"
    sglx_dir.mkdir()
    (sglx_dir / "test_g0_t0.imec0.ap.bin").write_bytes(b"fake binary data")
    (sglx_dir / "test_g0_t0.imec0.ap.meta").write_text("nSavedChans=32\nsampleRate=30000\n")
    (sglx_dir / "metadata.json").write_text('{"format": "spikeglx", "channels": 32}')
    
    # Create generic CSV dataset
    csv_dir = datasets_dir / "generic_sample"
    csv_dir.mkdir()
    (csv_dir / "recording_data.csv").write_text("timestamp,ch1,ch2,ch3\n0.0,0.1,0.2,0.3\n0.001,0.4,0.5,0.6\n")
    (csv_dir / "events.csv").write_text("timestamp,event\n1.0,stimulus\n2.0,response\n")
    (csv_dir / "metadata.json").write_text('{"format": "generic", "channels": 3}')
    
    return datasets_dir


@pytest.mark.integration
class TestTestDatasetManagerIntegration:
    """Test TestDatasetManager integration with test infrastructure."""
    
    def test_repository_initialization_with_structure(self, temp_repo_dir):
        """Test that TestDatasetManager creates proper repository structure."""
        repo_manager = DataLadRepositoryManager(str(temp_repo_dir))
        dataset_manager = TestDatasetManager(repo_manager)
        
        # Check that all expected directories exist
        assert dataset_manager.test_data_path.exists()
        assert dataset_manager.evaluation_data_path.exists()
        assert dataset_manager.conversion_examples_path.exists()
        
        # Check that the directory structure matches expected layout
        assert dataset_manager.test_data_path == temp_repo_dir / 'etl' / 'input-data'
        assert dataset_manager.evaluation_data_path == temp_repo_dir / 'etl' / 'evaluation-data'
        assert dataset_manager.conversion_examples_path == temp_repo_dir / 'examples' / 'conversion-examples'
    
    def test_add_multiple_format_datasets(self, temp_repo_dir, sample_datasets_dir):
        """Test adding datasets of different formats."""
        repo_manager = DataLadRepositoryManager(str(temp_repo_dir))
        dataset_manager = TestDatasetManager(repo_manager)
        
        # Add datasets of different formats
        oe_result = dataset_manager.add_test_dataset(
            "open_ephys_test",
            str(sample_datasets_dir / "open_ephys_sample"),
            "Open Ephys test dataset"
        )
        
        sglx_result = dataset_manager.add_test_dataset(
            "spikeglx_test", 
            str(sample_datasets_dir / "spikeglx_sample"),
            "SpikeGLX test dataset"
        )
        
        csv_result = dataset_manager.add_test_dataset(
            "generic_test",
            str(sample_datasets_dir / "generic_sample"), 
            "Generic CSV test dataset"
        )
        
        assert oe_result is True
        assert sglx_result is True
        assert csv_result is True
        
        # Verify all datasets are available
        datasets = dataset_manager.get_available_datasets()
        assert len(datasets) == 3
        
        dataset_names = [d["name"] for d in datasets]
        assert "open_ephys_test" in dataset_names
        assert "spikeglx_test" in dataset_names
        assert "generic_test" in dataset_names
    
    def test_format_detection_accuracy(self, temp_repo_dir, sample_datasets_dir):
        """Test that format detection works correctly for different formats."""
        repo_manager = DataLadRepositoryManager(str(temp_repo_dir))
        dataset_manager = TestDatasetManager(repo_manager)
        
        # Add datasets and check format detection
        dataset_manager.add_test_dataset(
            "oe_format_test",
            str(sample_datasets_dir / "open_ephys_sample"),
            "Open Ephys format test"
        )
        
        dataset_manager.add_test_dataset(
            "sglx_format_test",
            str(sample_datasets_dir / "spikeglx_sample"),
            "SpikeGLX format test"
        )
        
        dataset_manager.add_test_dataset(
            "csv_format_test",
            str(sample_datasets_dir / "generic_sample"),
            "CSV format test"
        )
        
        # Check format detection
        oe_datasets = dataset_manager.get_datasets_by_format("open_ephys")
        sglx_datasets = dataset_manager.get_datasets_by_format("spikeglx")
        csv_datasets = dataset_manager.get_datasets_by_format("generic_csv")
        
        assert len(oe_datasets) == 1
        assert oe_datasets[0]["name"] == "oe_format_test"
        
        assert len(sglx_datasets) == 1
        assert sglx_datasets[0]["name"] == "sglx_format_test"
        
        assert len(csv_datasets) == 1
        assert csv_datasets[0]["name"] == "csv_format_test"
    
    def test_dataset_type_organization(self, temp_repo_dir, sample_datasets_dir):
        """Test that datasets are properly organized by type."""
        repo_manager = DataLadRepositoryManager(str(temp_repo_dir))
        dataset_manager = TestDatasetManager(repo_manager)
        
        # Add datasets of different types
        dataset_manager.add_test_dataset(
            "test_data",
            str(sample_datasets_dir / "generic_sample"),
            "Test dataset",
            dataset_type="test"
        )
        
        dataset_manager.add_test_dataset(
            "eval_data",
            str(sample_datasets_dir / "open_ephys_sample"),
            "Evaluation dataset",
            dataset_type="evaluation"
        )
        
        dataset_manager.add_test_dataset(
            "example_data",
            str(sample_datasets_dir / "spikeglx_sample"),
            "Example dataset",
            dataset_type="example"
        )
        
        # Check that datasets are in correct directories
        test_path = dataset_manager.get_dataset_path("test_data", "test")
        eval_path = dataset_manager.get_dataset_path("eval_data", "evaluation")
        example_path = dataset_manager.get_dataset_path("example_data", "example")
        
        assert test_path is not None
        assert eval_path is not None
        assert example_path is not None
        
        # Check directory structure
        assert "input-data" in str(test_path)
        assert "evaluation-data" in str(eval_path)
        assert "conversion-examples" in str(example_path)
    
    def test_comprehensive_metadata_tracking(self, temp_repo_dir, sample_datasets_dir):
        """Test comprehensive metadata tracking and retrieval."""
        repo_manager = DataLadRepositoryManager(str(temp_repo_dir))
        dataset_manager = TestDatasetManager(repo_manager)
        
        custom_metadata = {
            "experiment_id": "EXP_001",
            "researcher": "Test Researcher",
            "lab": "Test Lab",
            "species": "mouse",
            "brain_region": "hippocampus"
        }
        
        dataset_manager.add_test_dataset(
            "comprehensive_test",
            str(sample_datasets_dir / "open_ephys_sample"),
            "Comprehensive metadata test dataset",
            metadata=custom_metadata
        )
        
        # Get dataset info and verify metadata
        datasets = dataset_manager.get_available_datasets()
        test_dataset = next(d for d in datasets if d["name"] == "comprehensive_test")
        
        # Check basic metadata
        assert test_dataset["name"] == "comprehensive_test"
        assert test_dataset["description"] == "Comprehensive metadata test dataset"
        assert test_dataset["dataset_type"] == "test"
        assert test_dataset["format_detected"] == "open_ephys"
        assert test_dataset["file_count"] > 0
        assert test_dataset["size_bytes"] > 0
        
        # Check custom metadata
        assert test_dataset["custom_metadata"]["experiment_id"] == "EXP_001"
        assert test_dataset["custom_metadata"]["researcher"] == "Test Researcher"
        assert test_dataset["custom_metadata"]["lab"] == "Test Lab"
        assert test_dataset["custom_metadata"]["species"] == "mouse"
        assert test_dataset["custom_metadata"]["brain_region"] == "hippocampus"
    
    def test_dataset_lifecycle_management(self, temp_repo_dir, sample_datasets_dir):
        """Test complete dataset lifecycle: add, list, access, remove."""
        repo_manager = DataLadRepositoryManager(str(temp_repo_dir))
        dataset_manager = TestDatasetManager(repo_manager)
        
        # Add dataset
        result = dataset_manager.add_test_dataset(
            "lifecycle_test",
            str(sample_datasets_dir / "generic_sample"),
            "Dataset lifecycle test"
        )
        assert result is True
        
        # List and verify it exists
        datasets = dataset_manager.get_available_datasets()
        assert len(datasets) == 1
        assert datasets[0]["name"] == "lifecycle_test"
        
        # Access dataset path
        dataset_path = dataset_manager.get_dataset_path("lifecycle_test")
        assert dataset_path is not None
        assert dataset_path.exists()
        
        # Verify files were copied
        assert (dataset_path / "recording_data.csv").exists()
        assert (dataset_path / "events.csv").exists()
        assert (dataset_path / "metadata.json").exists()
        assert (dataset_path / "dataset_metadata.json").exists()
        assert (dataset_path / "README.md").exists()
        
        # Remove dataset
        remove_result = dataset_manager.remove_dataset("lifecycle_test")
        assert remove_result is True
        
        # Verify it's gone
        datasets_after_removal = dataset_manager.get_available_datasets()
        assert len(datasets_after_removal) == 0
        
        dataset_path_after_removal = dataset_manager.get_dataset_path("lifecycle_test")
        assert dataset_path_after_removal is None


@pytest.mark.integration
class TestCompatibilityWithExistingInfrastructure:
    """Test compatibility with existing test dataset infrastructure."""
    
    def test_works_with_existing_datasets_directory(self, temp_repo_dir):
        """Test that TestDatasetManager works with existing datasets directory structure."""
        # Create structure similar to existing tests/datasets
        datasets_dir = temp_repo_dir / "tests" / "datasets"
        datasets_dir.mkdir(parents=True)
        
        # Create some existing dataset files
        formats_dir = datasets_dir / "formats"
        formats_dir.mkdir()
        
        existing_oe_dir = formats_dir / "open_ephys" / "existing_dataset"
        existing_oe_dir.mkdir(parents=True)
        (existing_oe_dir / "100_CH1.continuous").write_bytes(b"existing data")
        
        # Initialize TestDatasetManager in parent directory
        repo_manager = DataLadRepositoryManager(str(temp_repo_dir))
        dataset_manager = TestDatasetManager(repo_manager)
        
        # Should work without conflicts
        assert dataset_manager.test_data_path.exists()
        
        # Should be able to add new datasets
        sample_dir = temp_repo_dir / "sample"
        sample_dir.mkdir()
        (sample_dir / "data.csv").write_text("col1,col2\n1,2\n")
        
        result = dataset_manager.add_test_dataset(
            "new_dataset",
            str(sample_dir),
            "New dataset alongside existing"
        )
        assert result is True
        
        # Verify new dataset exists
        new_datasets = dataset_manager.get_available_datasets()
        assert len(new_datasets) == 1
        assert new_datasets[0]["name"] == "new_dataset"