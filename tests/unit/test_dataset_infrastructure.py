"""
Unit tests for DataLad-managed test dataset infrastructure.

This module tests the core functionality of the DataLad dataset management
system, including repository management, dataset creation, and access patterns.
"""

from pathlib import Path
from unittest.mock import Mock, patch

# Import components to test
from tests.datasets.access_patterns import DatasetAccessor, DatasetCache
from tests.datasets.dataset_manager import DatasetRegistry, TestDatasetManager
from tests.datasets.format_generators import (
    DatasetFormatRegistry,
    GenericFormatGenerator,
    OpenEphysGenerator,
    SpikeGLXGenerator,
)
from tests.datasets.repository_manager import (
    DataLadRepositoryManager,
    RepositoryConfig,
)
from tests.datasets.types import (
    DatasetFormat,
    DatasetMetadata,
    DatasetType,
    GenerationSpec,
)


class TestDataLadRepositoryManager:
    """Test DataLad repository management functionality."""

    def test_initialization(self, tmp_path):
        """Test repository manager initialization."""
        repo_manager = DataLadRepositoryManager(str(tmp_path))

        assert repo_manager.repository_path == tmp_path
        assert repo_manager.config is None
        assert repo_manager._dataset is None

    def test_repository_config_creation(self):
        """Test repository configuration creation."""
        config = RepositoryConfig(
            name="test-repo",
            description="Test repository",
            author_name="Test Author",
            author_email="test@example.com",
        )

        assert config.name == "test-repo"
        assert config.description == "Test repository"
        assert config.author_name == "Test Author"
        assert config.author_email == "test@example.com"
        assert config.annex_backend == "SHA256E"
        assert config.enable_git_annex is True

    def test_initialize_repository_with_datalad(self, tmp_path):
        """Test repository initialization with DataLad available."""
        repo_manager = DataLadRepositoryManager(str(tmp_path))
        config = RepositoryConfig(
            name="test-repo", description="Test repository for unit testing"
        )

        with patch("datalad.api.create") as mock_create:
            mock_dataset = Mock()
            mock_dataset.config = Mock()
            mock_dataset.config.set = Mock()
            mock_create.return_value = mock_dataset

            success = repo_manager.initialize_repository(config)

            assert success is True
            assert mock_create.called
            assert repo_manager.config == config

    def test_initialize_repository_without_datalad(self, tmp_path):
        """Test repository initialization fallback without DataLad."""
        with patch("tests.datasets.repository_manager.DATALAD_AVAILABLE", False):
            repo_manager = DataLadRepositoryManager(str(tmp_path))
            config = RepositoryConfig(name="test-repo", description="Test")

            success = repo_manager.initialize_repository(config)

            assert success is False

    def test_is_repository_initialized(self, tmp_path):
        """Test repository initialization check."""
        repo_manager = DataLadRepositoryManager(str(tmp_path))

        # Should return False when not initialized
        assert repo_manager.is_repository_initialized() is False

    def test_add_dataset_fallback(self, tmp_path):
        """Test adding dataset with fallback method."""
        repo_manager = DataLadRepositoryManager(str(tmp_path))

        # Create a test dataset directory
        dataset_dir = tmp_path / "test_dataset"
        dataset_dir.mkdir()
        (dataset_dir / "data.txt").write_text("test data")

        with patch("tests.datasets.repository_manager.DATALAD_AVAILABLE", False):
            success = repo_manager.add_dataset("test_dataset", "Add test dataset")

            assert success is True

    def test_get_dataset_info(self, tmp_path):
        """Test getting dataset information."""
        repo_manager = DataLadRepositoryManager(str(tmp_path))

        # Create a test dataset
        dataset_dir = tmp_path / "test_dataset"
        dataset_dir.mkdir()
        (dataset_dir / "file1.txt").write_text("content1")
        (dataset_dir / "file2.txt").write_text("content2")

        info = repo_manager.get_dataset_info("test_dataset")

        assert info is not None
        assert info["path"] == "test_dataset"
        assert info["exists"] is True
        assert info["file_count"] > 0
        assert info["size_bytes"] > 0

    def test_list_datasets(self, tmp_path):
        """Test listing datasets in repository."""
        repo_manager = DataLadRepositoryManager(str(tmp_path))

        # Create test datasets
        for i in range(3):
            dataset_dir = tmp_path / f"dataset_{i}"
            dataset_dir.mkdir()
            (dataset_dir / "data.txt").write_text(f"data {i}")

        datasets = repo_manager.list_datasets()

        assert len(datasets) == 3
        assert all(d["exists"] for d in datasets)


class TestDatasetRegistry:
    """Test dataset registry functionality."""

    def test_registry_initialization(self, tmp_path):
        """Test registry initialization."""
        registry_path = tmp_path / "registry.json"
        registry = DatasetRegistry(str(registry_path))

        assert registry.registry_path == registry_path
        assert len(registry.datasets) == 0

    def test_register_dataset(self, tmp_path):
        """Test dataset registration."""
        registry_path = tmp_path / "registry.json"
        registry = DatasetRegistry(str(registry_path))

        metadata = DatasetMetadata(
            name="test_dataset",
            format=DatasetFormat.GENERIC,
            type=DatasetType.CLEAN,
            description="Test dataset",
        )

        success = registry.register_dataset(metadata)

        assert success is True
        assert "test_dataset" in registry.datasets
        assert registry.datasets["test_dataset"] == metadata

    def test_register_duplicate_dataset(self, tmp_path):
        """Test registering duplicate dataset."""
        registry_path = tmp_path / "registry.json"
        registry = DatasetRegistry(str(registry_path))

        metadata = DatasetMetadata(
            name="test_dataset",
            format=DatasetFormat.GENERIC,
            type=DatasetType.CLEAN,
            description="Test dataset",
        )

        # Register first time
        success1 = registry.register_dataset(metadata)
        assert success1 is True

        # Try to register again
        success2 = registry.register_dataset(metadata)
        assert success2 is False

    def test_get_dataset(self, tmp_path):
        """Test getting dataset metadata."""
        registry_path = tmp_path / "registry.json"
        registry = DatasetRegistry(str(registry_path))

        metadata = DatasetMetadata(
            name="test_dataset",
            format=DatasetFormat.GENERIC,
            type=DatasetType.CLEAN,
            description="Test dataset",
        )

        registry.register_dataset(metadata)

        retrieved = registry.get_dataset("test_dataset")
        assert retrieved == metadata

        not_found = registry.get_dataset("nonexistent")
        assert not_found is None

    def test_list_datasets_with_filters(self, tmp_path):
        """Test listing datasets with filters."""
        registry_path = tmp_path / "registry.json"
        registry = DatasetRegistry(str(registry_path))

        # Register multiple datasets
        datasets = [
            DatasetMetadata(
                name="open_ephys_clean",
                format=DatasetFormat.OPEN_EPHYS,
                type=DatasetType.CLEAN,
                description="Clean Open Ephys dataset",
                tags=["ephys", "clean"],
            ),
            DatasetMetadata(
                name="spikeglx_corrupted",
                format=DatasetFormat.SPIKEGLX,
                type=DatasetType.CORRUPTED,
                description="Corrupted SpikeGLX dataset",
                tags=["spikeglx", "corrupted"],
            ),
            DatasetMetadata(
                name="generic_minimal",
                format=DatasetFormat.GENERIC,
                type=DatasetType.MINIMAL,
                description="Minimal generic dataset",
                tags=["generic", "minimal"],
            ),
        ]

        for dataset in datasets:
            registry.register_dataset(dataset)

        # Test format filter
        open_ephys_datasets = registry.list_datasets(
            format_filter=DatasetFormat.OPEN_EPHYS
        )
        assert len(open_ephys_datasets) == 1
        assert open_ephys_datasets[0].name == "open_ephys_clean"

        # Test type filter
        clean_datasets = registry.list_datasets(type_filter=DatasetType.CLEAN)
        assert len(clean_datasets) == 1
        assert clean_datasets[0].name == "open_ephys_clean"

        # Test tag filter
        clean_tagged = registry.list_datasets(tag_filter=["clean"])
        assert len(clean_tagged) == 1
        assert clean_tagged[0].name == "open_ephys_clean"

    def test_registry_persistence(self, tmp_path):
        """Test registry persistence to file."""
        registry_path = tmp_path / "registry.json"

        # Create registry and add dataset
        registry1 = DatasetRegistry(str(registry_path))
        metadata = DatasetMetadata(
            name="test_dataset",
            format=DatasetFormat.GENERIC,
            type=DatasetType.CLEAN,
            description="Test dataset",
        )
        registry1.register_dataset(metadata)

        # Create new registry instance and verify data persisted
        registry2 = DatasetRegistry(str(registry_path))
        assert len(registry2.datasets) == 1
        assert "test_dataset" in registry2.datasets
        assert registry2.datasets["test_dataset"].name == "test_dataset"


class TestDatasetFormatGenerators:
    """Test dataset format generators."""

    def test_generation_spec_defaults(self):
        """Test generation specification defaults."""
        spec = GenerationSpec()

        assert spec.channels == 32
        assert spec.sampling_rate == 30000.0
        assert spec.duration_seconds == 60.0
        assert spec.has_events is True
        assert spec.has_metadata is True
        assert spec.corruption_level == 0.0
        assert spec.custom_params == {}

    def test_open_ephys_generator(self, tmp_path):
        """Test Open Ephys format generator."""
        generator = OpenEphysGenerator()

        spec = GenerationSpec(
            channels=4,
            sampling_rate=1000.0,
            duration_seconds=5.0,
            has_events=True,
            has_metadata=True,
        )

        result = generator.generate_dataset(
            output_dir=tmp_path, dataset_type=DatasetType.CLEAN, spec=spec
        )

        assert result["format"] == "open_ephys"
        assert result["channels"] == 4
        assert result["sampling_rate"] == 1000.0
        assert result["duration_seconds"] == 5.0
        assert len(result["files"]) > 0

        # Check that files were created
        for file_path in result["files"]:
            assert Path(file_path).exists()

    def test_spikeglx_generator(self, tmp_path):
        """Test SpikeGLX format generator."""
        generator = SpikeGLXGenerator()

        spec = GenerationSpec(
            channels=8,
            sampling_rate=2000.0,
            duration_seconds=3.0,
            has_events=False,
            has_metadata=True,
        )

        result = generator.generate_dataset(
            output_dir=tmp_path, dataset_type=DatasetType.MINIMAL, spec=spec
        )

        assert result["format"] == "spikeglx"
        assert result["channels"] == 8
        assert result["sampling_rate"] == 2000.0
        assert result["duration_seconds"] == 3.0
        assert len(result["files"]) > 0

        # Check for expected SpikeGLX files
        bin_file_exists = any(".bin" in f for f in result["files"])
        meta_file_exists = any(".meta" in f for f in result["files"])
        assert bin_file_exists
        assert meta_file_exists

    def test_generic_generator(self, tmp_path):
        """Test generic CSV format generator."""
        generator = GenericFormatGenerator()

        spec = GenerationSpec(
            channels=2,
            sampling_rate=100.0,
            duration_seconds=2.0,
            has_events=True,
            has_metadata=False,
            corruption_level=0.1,
        )

        result = generator.generate_dataset(
            output_dir=tmp_path, dataset_type=DatasetType.CORRUPTED, spec=spec
        )

        assert result["format"] == "generic"
        assert result["channels"] == 2
        assert result["sampling_rate"] == 100.0
        assert result["corruption_level"] == 0.1
        assert len(result["files"]) > 0

        # Check for CSV file
        csv_file_exists = any(".csv" in f for f in result["files"])
        assert csv_file_exists

    def test_format_registry(self):
        """Test dataset format registry."""
        registry = DatasetFormatRegistry()

        # Check default generators are registered
        formats = registry.list_formats()
        assert "open_ephys" in formats
        assert "spikeglx" in formats
        assert "generic" in formats

        # Test getting generators
        open_ephys_gen = registry.get_generator("open_ephys")
        assert isinstance(open_ephys_gen, OpenEphysGenerator)

        spikeglx_gen = registry.get_generator("spikeglx")
        assert isinstance(spikeglx_gen, SpikeGLXGenerator)

        generic_gen = registry.get_generator("generic")
        assert isinstance(generic_gen, GenericFormatGenerator)

        # Test nonexistent generator
        nonexistent = registry.get_generator("nonexistent")
        assert nonexistent is None


class TestDatasetCache:
    """Test dataset caching functionality."""

    def test_cache_initialization(self, tmp_path):
        """Test cache initialization."""
        cache_dir = tmp_path / "cache"
        cache = DatasetCache(
            cache_dir=str(cache_dir), max_cache_size_mb=100, max_age_hours=24
        )

        assert cache.cache_dir == cache_dir
        assert cache.max_cache_size_bytes == 100 * 1024 * 1024
        assert len(cache.entries) == 0

    def test_cache_dataset(self, tmp_path):
        """Test caching a dataset."""
        cache_dir = tmp_path / "cache"
        cache = DatasetCache(str(cache_dir))

        # Create source dataset
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "data.txt").write_text("test data")

        # Create mock metadata
        metadata = DatasetMetadata(
            name="test_dataset",
            format=DatasetFormat.GENERIC,
            type=DatasetType.CLEAN,
            description="Test dataset",
        )

        success = cache.cache_dataset("test_dataset", source_dir, metadata)

        assert success is True
        assert "test_dataset" in cache.entries

        # Check cached files exist
        cached_path = cache.entries["test_dataset"].path
        assert cached_path.exists()
        assert (cached_path / "data.txt").exists()

    def test_get_cached_dataset(self, tmp_path):
        """Test retrieving cached dataset."""
        cache_dir = tmp_path / "cache"
        cache = DatasetCache(str(cache_dir))

        # Create and cache dataset
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "data.txt").write_text("test data")

        metadata = DatasetMetadata(
            name="test_dataset",
            format=DatasetFormat.GENERIC,
            type=DatasetType.CLEAN,
            description="Test dataset",
        )

        cache.cache_dataset("test_dataset", source_dir, metadata)

        # Retrieve from cache
        cached_path = cache.get_cached_dataset("test_dataset")

        assert cached_path is not None
        assert cached_path.exists()
        assert (cached_path / "data.txt").exists()

        # Test cache miss
        not_cached = cache.get_cached_dataset("nonexistent")
        assert not_cached is None

    def test_cache_stats(self, tmp_path):
        """Test cache statistics."""
        cache_dir = tmp_path / "cache"
        cache = DatasetCache(str(cache_dir), max_cache_size_mb=10)

        stats = cache.get_cache_stats()

        assert stats["total_entries"] == 0
        assert stats["total_size_mb"] == 0.0
        assert stats["max_size_mb"] == 10.0
        assert stats["utilization_percent"] == 0.0
        assert stats["total_accesses"] == 0
        assert len(stats["entries"]) == 0


class TestDatasetAccessor:
    """Test dataset accessor functionality."""

    def test_accessor_initialization(self, tmp_path):
        """Test dataset accessor initialization."""
        # Create mock dataset manager
        mock_manager = Mock(spec=TestDatasetManager)
        mock_manager.repository_path = tmp_path

        accessor = DatasetAccessor(dataset_manager=mock_manager, enable_caching=True)

        assert accessor.dataset_manager == mock_manager
        assert accessor.enable_caching is True
        assert accessor.cache is not None
        assert len(accessor.access_stats) == 0

    def test_get_dataset_without_cache(self, tmp_path):
        """Test getting dataset without caching."""
        # Create mock dataset manager
        mock_manager = Mock(spec=TestDatasetManager)
        mock_manager.get_dataset_path.return_value = tmp_path / "test_dataset"

        # Create the dataset directory
        dataset_dir = tmp_path / "test_dataset"
        dataset_dir.mkdir()

        accessor = DatasetAccessor(dataset_manager=mock_manager, enable_caching=False)

        result_path = accessor.get_dataset("test_dataset")

        assert result_path == dataset_dir
        assert mock_manager.get_dataset_path.called
        assert "test_dataset" in accessor.access_stats
        assert accessor.access_stats["test_dataset"] == 1

    def test_get_access_stats(self, tmp_path):
        """Test access statistics."""
        mock_manager = Mock(spec=TestDatasetManager)
        mock_manager.get_dataset_path.return_value = tmp_path / "test_dataset"

        dataset_dir = tmp_path / "test_dataset"
        dataset_dir.mkdir()

        accessor = DatasetAccessor(dataset_manager=mock_manager, enable_caching=False)

        # Access dataset multiple times
        accessor.get_dataset("test_dataset")
        accessor.get_dataset("test_dataset")
        accessor.get_dataset("another_dataset")

        stats = accessor.get_access_stats()

        assert stats["total_accesses"] == 3
        assert stats["unique_datasets_accessed"] == 2
        assert stats["dataset_access_counts"]["test_dataset"] == 2
        assert stats["dataset_access_counts"]["another_dataset"] == 1


class TestTestDatasetManager:
    """Test the main test dataset manager."""

    def test_manager_initialization(self, tmp_path):
        """Test dataset manager initialization."""
        manager = TestDatasetManager(str(tmp_path))

        assert manager.repository_path == tmp_path
        assert manager.repo_manager is not None
        assert manager.registry is not None
        assert manager.format_registry is not None

    def test_create_dataset(self, tmp_path):
        """Test creating a dataset."""
        manager = TestDatasetManager(str(tmp_path))

        # Mock the format registry to return a working generator
        mock_generator = Mock()
        mock_generator.generate_dataset.return_value = {
            "file_count": 2,
            "size_bytes": 1024,
            "channels": 4,
            "sampling_rate": 1000.0,
            "duration_seconds": 5.0,
            "has_events": True,
            "has_metadata": True,
            "corruption_level": 0.0,
            "tags": ["test"],
            "requirements": ["test_req"],
        }

        manager.format_registry.get_generator = Mock(return_value=mock_generator)

        metadata = manager.create_dataset(
            name="test_dataset",
            format=DatasetFormat.GENERIC,
            type=DatasetType.CLEAN,
            description="Test dataset",
        )

        assert metadata is not None
        assert metadata.name == "test_dataset"
        assert metadata.format == DatasetFormat.GENERIC
        assert metadata.type == DatasetType.CLEAN
        assert metadata.channels == 4
        assert mock_generator.generate_dataset.called

    def test_get_dataset_path(self, tmp_path):
        """Test getting dataset path."""
        manager = TestDatasetManager(str(tmp_path))

        # Create a mock dataset in registry
        metadata = DatasetMetadata(
            name="test_dataset",
            format=DatasetFormat.GENERIC,
            type=DatasetType.CLEAN,
            description="Test dataset",
        )
        manager.registry.register_dataset(metadata)

        # Create the actual directory
        dataset_dir = tmp_path / "formats" / "generic" / "test_dataset"
        dataset_dir.mkdir(parents=True)

        path = manager.get_dataset_path("test_dataset")

        assert path == dataset_dir
        assert path.exists()

    def test_list_available_datasets(self, tmp_path):
        """Test listing available datasets."""
        manager = TestDatasetManager(str(tmp_path))

        # Add some datasets to registry
        datasets = [
            DatasetMetadata(
                name="dataset1",
                format=DatasetFormat.OPEN_EPHYS,
                type=DatasetType.CLEAN,
                description="Dataset 1",
            ),
            DatasetMetadata(
                name="dataset2",
                format=DatasetFormat.SPIKEGLX,
                type=DatasetType.MINIMAL,
                description="Dataset 2",
            ),
        ]

        for dataset in datasets:
            manager.registry.register_dataset(dataset)

        available = manager.list_available_datasets()

        assert len(available) == 2
        assert any(d.name == "dataset1" for d in available)
        assert any(d.name == "dataset2" for d in available)

        # Test filtering
        open_ephys_datasets = manager.list_available_datasets(
            format_filter=DatasetFormat.OPEN_EPHYS
        )
        assert len(open_ephys_datasets) == 1
        assert open_ephys_datasets[0].name == "dataset1"
