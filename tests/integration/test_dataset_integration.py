"""
Integration tests for DataLad-managed test dataset infrastructure.

This module tests the integration between different components of the
DataLad dataset management system to ensure they work together correctly.
These tests focus on core functionality without heavy DataLad operations.
"""

import pytest
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch
pytest.skip(allow_module_level=True)
# Import components to test
try:
    from tests.datasets.dataset_manager import TestDatasetManager
    from tests.datasets.types import DatasetFormat, DatasetType, GenerationSpec
    from tests.datasets.access_patterns import DatasetAccessor
    from tests.datasets.repository_manager import DATALAD_AVAILABLE
    COMPONENTS_AVAILABLE = True
except ImportError:
    # Components not implemented yet
    COMPONENTS_AVAILABLE = False

# Skip all tests if components are not implemented
pytestmark = pytest.mark.skipif(
    not COMPONENTS_AVAILABLE,
    reason="Dataset infrastructure components not implemented yet"
)


@pytest.mark.integration
class TestDatasetInfrastructureIntegration:
    """Test integration of dataset infrastructure components."""
    
    def test_end_to_end_dataset_creation_and_access(self, tmp_path):
        """Test complete workflow from dataset creation to access without DataLad."""
        # Use unique test name to avoid conflicts
        test_id = str(uuid.uuid4())[:8]
        
        # Initialize dataset manager without DataLad to avoid performance issues
        manager = TestDatasetManager(str(tmp_path))
        
        # Don't initialize DataLad for this test - just test the core functionality
        # Create a test dataset
        metadata = manager.create_dataset(
            name=f"integration_test_{test_id}",
            format=DatasetFormat.GENERIC,
            type=DatasetType.MINIMAL,
            description="Integration test dataset",
            channels=2,
            duration_seconds=1.0,
            sampling_rate=100.0
        )
        
        assert metadata is not None
        assert metadata.name == f"integration_test_{test_id}"
        
        # Verify dataset was created
        dataset_path = manager.get_dataset_path(f"integration_test_{test_id}")
        assert dataset_path is not None
        assert dataset_path.exists()
        
        # Check that files were created
        files = list(dataset_path.rglob("*"))
        data_files = [f for f in files if f.is_file()]
        assert len(data_files) > 0
        
        # Verify dataset is in registry
        available_datasets = manager.list_available_datasets()
        test_datasets = [d for d in available_datasets if d.name == f"integration_test_{test_id}"]
        assert len(test_datasets) == 1
        assert test_datasets[0].name == f"integration_test_{test_id}"
    
    def test_dataset_accessor_integration(self, tmp_path):
        """Test dataset accessor integration with manager."""
        # Setup manager and create dataset
        manager = TestDatasetManager(str(tmp_path))
        manager.initialize(force=True)
        
        metadata = manager.create_dataset(
            name="accessor_test_dataset",
            format=DatasetFormat.GENERIC,
            type=DatasetType.MINIMAL,
            description="Dataset for accessor testing",
            channels=2,
            duration_seconds=3.0,
            sampling_rate=500.0
        )
        
        assert metadata is not None
        
        # Create accessor
        accessor = DatasetAccessor(
            dataset_manager=manager,
            enable_caching=True
        )
        
        # Access dataset through accessor
        dataset_path = accessor.get_dataset("accessor_test_dataset")
        assert dataset_path is not None
        assert dataset_path.exists()
        
        # Verify access statistics
        stats = accessor.get_access_stats()
        assert stats["total_accesses"] == 1
        assert "accessor_test_dataset" in stats["dataset_access_counts"]
        
        # Access again to test caching
        dataset_path2 = accessor.get_dataset("accessor_test_dataset")
        assert dataset_path2 == dataset_path
        
        # Check updated statistics
        stats2 = accessor.get_access_stats()
        assert stats2["total_accesses"] == 2
        assert stats2["dataset_access_counts"]["accessor_test_dataset"] == 2
    
    def test_multiple_format_creation(self, tmp_path):
        """Test creating datasets in multiple formats."""
        manager = TestDatasetManager(str(tmp_path))
        manager.initialize(force=True)
        
        # Create datasets in different formats
        formats_to_test = [
            (DatasetFormat.OPEN_EPHYS, "open_ephys_test"),
            (DatasetFormat.SPIKEGLX, "spikeglx_test"),
            (DatasetFormat.GENERIC, "generic_test")
        ]
        
        created_datasets = []
        
        for format_type, name in formats_to_test:
            metadata = manager.create_dataset(
                name=name,
                format=format_type,
                type=DatasetType.MINIMAL,
                description=f"Test dataset for {format_type.value}",
                channels=2,
                duration_seconds=2.0,
                sampling_rate=1000.0
            )
            
            if metadata:
                created_datasets.append(metadata)
                
                # Verify dataset exists
                dataset_path = manager.get_dataset_path(name)
                assert dataset_path is not None
                assert dataset_path.exists()
        
        # Should have created at least some datasets
        assert len(created_datasets) > 0
        
        # Verify all datasets are listed
        available_datasets = manager.list_available_datasets()
        assert len(available_datasets) == len(created_datasets)
        
        # Test format filtering
        for format_type, name in formats_to_test:
            format_datasets = manager.list_available_datasets(format_filter=format_type)
            format_names = [d.name for d in format_datasets]
            
            if name in [d.name for d in created_datasets]:
                assert name in format_names
    
    def test_dataset_type_variations(self, tmp_path):
        """Test creating datasets of different types."""
        manager = TestDatasetManager(str(tmp_path))
        manager.initialize(force=True)
        
        # Create datasets of different types
        dataset_types = [
            (DatasetType.CLEAN, "clean_test", 0.0),
            (DatasetType.MINIMAL, "minimal_test", 0.0),
            (DatasetType.CORRUPTED, "corrupted_test", 0.1)
        ]
        
        created_datasets = []
        
        for dataset_type, name, corruption_level in dataset_types:
            metadata = manager.create_dataset(
                name=name,
                format=DatasetFormat.GENERIC,
                type=dataset_type,
                description=f"Test dataset of type {dataset_type.value}",
                channels=4,
                duration_seconds=3.0,
                sampling_rate=1000.0,
                corruption_level=corruption_level
            )
            
            if metadata:
                created_datasets.append(metadata)
                assert metadata.corruption_level == corruption_level
        
        # Verify datasets were created
        assert len(created_datasets) > 0
        
        # Test type filtering
        for dataset_type, name, _ in dataset_types:
            type_datasets = manager.list_available_datasets(type_filter=dataset_type)
            type_names = [d.name for d in type_datasets]
            
            if name in [d.name for d in created_datasets]:
                assert name in type_names
    
    def test_dataset_removal_integration(self, tmp_path):
        """Test dataset removal integration."""
        manager = TestDatasetManager(str(tmp_path))
        manager.initialize(force=True)
        
        # Create a dataset
        metadata = manager.create_dataset(
            name="removal_test_dataset",
            format=DatasetFormat.GENERIC,
            type=DatasetType.CLEAN,
            description="Dataset for removal testing",
            channels=2,
            duration_seconds=2.0,
            sampling_rate=500.0
        )
        
        assert metadata is not None
        
        # Verify dataset exists
        dataset_path = manager.get_dataset_path("removal_test_dataset")
        assert dataset_path is not None
        assert dataset_path.exists()
        
        # Verify it's in the registry
        available_before = manager.list_available_datasets()
        assert len(available_before) == 1
        
        # Remove the dataset
        success = manager.remove_dataset("removal_test_dataset")
        assert success is True
        
        # Verify dataset is removed from registry
        available_after = manager.list_available_datasets()
        assert len(available_after) == 0
        
        # Verify path no longer exists or returns None
        dataset_path_after = manager.get_dataset_path("removal_test_dataset")
        assert dataset_path_after is None or not dataset_path_after.exists()
    
    def test_cache_integration(self, tmp_path):
        """Test caching integration with dataset access."""
        manager = TestDatasetManager(str(tmp_path))
        manager.initialize(force=True)
        
        # Create a dataset
        metadata = manager.create_dataset(
            name="cache_test_dataset",
            format=DatasetFormat.GENERIC,
            type=DatasetType.CLEAN,
            description="Dataset for cache testing",
            channels=2,
            duration_seconds=2.0,
            sampling_rate=500.0
        )
        
        assert metadata is not None
        
        # Create accessor with caching enabled
        cache_dir = tmp_path / "cache"
        accessor = DatasetAccessor(
            dataset_manager=manager,
            cache_dir=str(cache_dir),
            enable_caching=True
        )
        
        # First access - should cache the dataset
        dataset_path1 = accessor.get_dataset("cache_test_dataset", use_cache=True)
        assert dataset_path1 is not None
        
        # Check cache statistics
        stats1 = accessor.get_access_stats()
        assert "cache_stats" in stats1
        
        # Second access - should use cache
        dataset_path2 = accessor.get_dataset("cache_test_dataset", use_cache=True)
        assert dataset_path2 is not None
        
        # Paths might be different (original vs cached) but both should exist
        assert dataset_path1.exists()
        assert dataset_path2.exists()
        
        # Check updated statistics
        stats2 = accessor.get_access_stats()
        assert stats2["total_accesses"] == 2
    
    @pytest.mark.skipif(not DATALAD_AVAILABLE, reason="DataLad not available")
    def test_datalad_integration(self, tmp_path):
        """Test integration with actual DataLad functionality."""
        manager = TestDatasetManager(str(tmp_path))
        
        # Initialize with DataLad
        success = manager.initialize(force=True)
        assert success is True
        
        # Verify DataLad repository was created
        assert manager.repo_manager.is_repository_initialized()
        
        # Create a dataset
        metadata = manager.create_dataset(
            name="datalad_test_dataset",
            format=DatasetFormat.GENERIC,
            type=DatasetType.CLEAN,
            description="Dataset for DataLad testing",
            channels=2,
            duration_seconds=2.0,
            sampling_rate=500.0
        )
        
        assert metadata is not None
        
        # Verify dataset was added to DataLad repository
        dataset_info = manager.repo_manager.get_dataset_info("formats/generic/datalad_test_dataset")
        assert dataset_info is not None
        assert dataset_info["exists"] is True
    
    def test_error_handling_integration(self, tmp_path):
        """Test error handling across integrated components."""
        manager = TestDatasetManager(str(tmp_path))
        manager.initialize(force=True)
        
        # Test creating dataset with invalid parameters
        metadata = manager.create_dataset(
            name="",  # Invalid empty name
            format=DatasetFormat.GENERIC,
            type=DatasetType.CLEAN,
            description="Invalid dataset"
        )
        
        # Should handle error gracefully
        assert metadata is None
        
        # Test accessing non-existent dataset
        accessor = DatasetAccessor(dataset_manager=manager)
        
        dataset_path = accessor.get_dataset("nonexistent_dataset")
        assert dataset_path is None
        
        # Test removing non-existent dataset
        success = manager.remove_dataset("nonexistent_dataset")
        assert success is True  # Should return True for already removed
    
    def test_concurrent_access_simulation(self, tmp_path):
        """Test simulated concurrent access to datasets."""
        manager = TestDatasetManager(str(tmp_path))
        manager.initialize(force=True)
        
        # Create multiple datasets
        dataset_names = []
        for i in range(3):
            name = f"concurrent_test_{i}"
            metadata = manager.create_dataset(
                name=name,
                format=DatasetFormat.GENERIC,
                type=DatasetType.MINIMAL,
                description=f"Dataset {i} for concurrent testing",
                channels=1,
                duration_seconds=1.0,
                sampling_rate=100.0
            )
            
            if metadata:
                dataset_names.append(name)
        
        # Create multiple accessors (simulating concurrent access)
        accessors = []
        for i in range(2):
            accessor = DatasetAccessor(
                dataset_manager=manager,
                enable_caching=True
            )
            accessors.append(accessor)
        
        # Access datasets from multiple accessors
        for accessor in accessors:
            for name in dataset_names:
                dataset_path = accessor.get_dataset(name)
                assert dataset_path is not None
                assert dataset_path.exists()
        
        # Verify all accessors have correct statistics
        for accessor in accessors:
            stats = accessor.get_access_stats()
            assert stats["total_accesses"] == len(dataset_names)
            assert stats["unique_datasets_accessed"] == len(dataset_names)