# Copyright (c) 2025 Agentic Neurodata Conversion Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""DataLad repository structure management for development and conversions."""

import json
import logging
from pathlib import Path
import time
from typing import Any, Optional

try:
    import datalad.api as dl
    from datalad.api import Dataset

    DATALAD_AVAILABLE = True
except ImportError:
    # Handle case where DataLad is not installed
    DATALAD_AVAILABLE = False
    dl = None
    Dataset = None


class DataLadRepositoryManager:
    """Manages DataLad repository structure for development and conversions."""

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.logger = logging.getLogger(__name__)

        if not DATALAD_AVAILABLE:
            self.logger.warning(
                "DataLad not available. Repository management will be limited."
            )

        # Repository structure
        self.structure = {
            "etl": {
                "input-data": "Raw input datasets for testing",
                "evaluation-data": "Datasets for evaluation and benchmarking",
                "workflows": "ETL workflow definitions",
                "prompt-input-data": "Data for prompt engineering and testing",
            },
            "tests": {
                "fixtures": "Test data fixtures",
                "integration-tests": "Integration test data",
                "unit-tests": "Unit test data",
            },
            "examples": {
                "conversion-examples": "Example conversion repositories",
                "sample-datasets": "Small sample datasets for documentation",
            },
        }

    def initialize_development_repository(self) -> Optional[Dataset]:
        """Initialize the main development DataLad repository."""
        if not DATALAD_AVAILABLE:
            self.logger.error("DataLad not available. Cannot initialize repository.")
            return None

        try:
            # Check if already a DataLad dataset
            if (self.base_path / ".datalad").exists():
                dataset = Dataset(self.base_path)
                self.logger.info(f"Using existing DataLad dataset: {self.base_path}")
            else:
                # Create new DataLad dataset
                dataset = dl.create(
                    path=str(self.base_path), description="Agentic Neurodata Converter"
                )
                self.logger.info(f"Created new DataLad dataset: {self.base_path}")

            # Setup directory structure
            self._setup_directory_structure(dataset)

            # Configure git attributes
            self._configure_git_attributes(dataset)

            return dataset

        except Exception as e:
            self.logger.error(f"Failed to initialize DataLad repository: {e}")
            raise

    def _setup_directory_structure(self, dataset: Optional[Dataset]):
        """Setup the directory structure for development data."""
        for main_dir, subdirs in self.structure.items():
            main_path = self.base_path / main_dir
            main_path.mkdir(exist_ok=True)

            if isinstance(subdirs, dict):
                for subdir, description in subdirs.items():
                    subdir_path = main_path / subdir
                    subdir_path.mkdir(exist_ok=True)

                    # Create README with description
                    readme_path = subdir_path / "README.md"
                    if not readme_path.exists():
                        readme_path.write_text(
                            f"# {subdir.replace('-', ' ').title()}\n\n{description}\n"
                        )

        # Save structure to dataset if DataLad is available
        if dataset and DATALAD_AVAILABLE:
            dataset.save(
                message="Initialize directory structure", path=[str(self.base_path)]
            )

    def _configure_git_attributes(self, dataset: Optional[Dataset]):
        """Configure .gitattributes for proper file handling."""
        gitattributes_path = self.base_path / ".gitattributes"

        # Define rules for what should be annexed vs tracked in git
        gitattributes_content = """
# Development files - keep in git
*.py annex.largefiles=nothing
*.md annex.largefiles=nothing
*.txt annex.largefiles=nothing
*.json annex.largefiles=nothing
*.yaml annex.largefiles=nothing
*.yml annex.largefiles=nothing
*.toml annex.largefiles=nothing
*.cfg annex.largefiles=nothing
*.ini annex.largefiles=nothing

# Small data files - keep in git (< 10MB)
*.csv annex.largefiles=(largerthan=10MB)
*.tsv annex.largefiles=(largerthan=10MB)

# Large data files - always annex
*.nwb annex.largefiles=anything
*.dat annex.largefiles=anything
*.bin annex.largefiles=anything
*.h5 annex.largefiles=anything
*.hdf5 annex.largefiles=anything
*.mat annex.largefiles=anything
*.ncs annex.largefiles=anything
*.nev annex.largefiles=anything
*.ns* annex.largefiles=anything

# Media files - always annex
*.png annex.largefiles=anything
*.jpg annex.largefiles=anything
*.jpeg annex.largefiles=anything
*.gif annex.largefiles=anything
*.svg annex.largefiles=nothing
*.pdf annex.largefiles=(largerthan=1MB)

# Archives - always annex
*.zip annex.largefiles=anything
*.tar annex.largefiles=anything
*.tar.gz annex.largefiles=anything
*.tgz annex.largefiles=anything

# Logs and temporary files - keep in git if small
*.log annex.largefiles=(largerthan=1MB)
*.tmp annex.largefiles=(largerthan=1MB)
"""

        gitattributes_path.write_text(gitattributes_content.strip())

        if dataset and DATALAD_AVAILABLE:
            dataset.save(
                message="Configure git attributes for file handling",
                path=[str(gitattributes_path)],
            )

        self.logger.info("Configured .gitattributes for proper file handling")


class TestDatasetManager:
    """Manages test datasets for development and testing."""

    def __init__(self, repository_manager: DataLadRepositoryManager):
        self.repo_manager = repository_manager
        self.logger = logging.getLogger(__name__)
        self.test_data_path = repository_manager.base_path / "etl" / "input-data"
        self.evaluation_data_path = (
            repository_manager.base_path / "etl" / "evaluation-data"
        )
        self.conversion_examples_path = (
            repository_manager.base_path / "examples" / "conversion-examples"
        )

        # Ensure directories exist
        self.test_data_path.mkdir(parents=True, exist_ok=True)
        self.evaluation_data_path.mkdir(parents=True, exist_ok=True)
        self.conversion_examples_path.mkdir(parents=True, exist_ok=True)

    def add_test_dataset(
        self,
        dataset_name: str,
        source_path: str,
        description: str = "",
        metadata: Optional[dict[str, Any]] = None,
        dataset_type: str = "test",
    ) -> bool:
        """
        Add a test dataset to the repository with proper metadata tracking.

        Args:
            dataset_name: Name of the dataset
            source_path: Path to source data
            description: Description of the dataset
            metadata: Additional metadata
            dataset_type: Type of dataset ('test', 'evaluation', 'example')

        Returns:
            True if successful, False otherwise
        """
        try:
            dataset = None

            # Determine target path based on dataset type
            if dataset_type == "evaluation":
                target_base_path = self.evaluation_data_path
            elif dataset_type == "example":
                target_base_path = self.conversion_examples_path
            else:
                target_base_path = self.test_data_path

            # Only try to use DataLad if available and we're in a DataLad repository
            if (
                DATALAD_AVAILABLE
                and (self.repo_manager.base_path / ".datalad").exists()
            ):
                try:
                    dataset = Dataset(self.repo_manager.base_path)
                except Exception as e:
                    self.logger.warning(f"Could not access DataLad dataset: {e}")
                    dataset = None

            target_path = target_base_path / dataset_name

            # Copy or link dataset
            if Path(source_path).exists():
                import shutil

                if Path(source_path).is_dir():
                    shutil.copytree(source_path, target_path, dirs_exist_ok=True)
                else:
                    target_path.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, target_path)

                # Create comprehensive metadata file
                dataset_metadata = {
                    "name": dataset_name,
                    "description": description,
                    "source_path": source_path,
                    "dataset_type": dataset_type,
                    "added_timestamp": time.time(),
                    "added_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "file_count": self._count_files(target_path),
                    "size_bytes": self._get_directory_size(target_path),
                    "format_detected": self._detect_format(target_path),
                    "custom_metadata": metadata or {},
                    "version": "1.0",
                }

                metadata_file = target_path / "dataset_metadata.json"
                metadata_file.write_text(json.dumps(dataset_metadata, indent=2))

                # Create README if it doesn't exist
                readme_file = target_path / "README.md"
                if not readme_file.exists():
                    readme_content = f"""# {dataset_name}

{description}

## Dataset Information

- **Type**: {dataset_type}
- **Format**: {dataset_metadata["format_detected"]}
- **Files**: {dataset_metadata["file_count"]}
- **Size**: {dataset_metadata["size_bytes"]} bytes
- **Added**: {dataset_metadata["added_date"]}

## Source

Original data from: `{source_path}`

## Usage

This dataset is managed by the Agentic Neurodata Conversion test infrastructure.
"""
                    readme_file.write_text(readme_content)

                # Save to DataLad if available and we have a dataset
                if dataset:
                    try:
                        dataset.save(
                            message=f"Add {dataset_type} dataset: {dataset_name}",
                            path=[str(target_path)],
                        )
                    except Exception as e:
                        self.logger.warning(f"Could not save to DataLad: {e}")

                self.logger.info(f"Added {dataset_type} dataset: {dataset_name}")
                return True
            else:
                self.logger.error(f"Source path does not exist: {source_path}")
                return False

        except Exception as e:
            self.logger.error(f"Failed to add test dataset {dataset_name}: {e}")
            return False

    def install_subdataset(
        self, subdataset_url: str, subdataset_path: str, description: str = ""
    ) -> bool:
        """
        Install a subdataset for external test data with proper DataLad management.

        Args:
            subdataset_url: URL or path to the subdataset
            subdataset_path: Relative path where to install the subdataset
            description: Description of the subdataset

        Returns:
            True if successful, False otherwise
        """
        if not DATALAD_AVAILABLE:
            self.logger.error("DataLad not available. Cannot install subdataset.")
            return False

        try:
            dataset = Dataset(self.repo_manager.base_path)
            target_path = self.repo_manager.base_path / subdataset_path

            # Install subdataset
            dl.install(
                source=subdataset_url,
                path=str(target_path),
                dataset=dataset,
                description=description or f"External dataset from {subdataset_url}",
            )

            # Ensure target directory exists (in case install didn't create it)
            target_path.mkdir(parents=True, exist_ok=True)

            # Create metadata for the subdataset
            metadata = {
                "name": Path(subdataset_path).name,
                "type": "subdataset",
                "source_url": subdataset_url,
                "installed_path": subdataset_path,
                "description": description,
                "installed_timestamp": time.time(),
                "installed_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

            metadata_file = target_path / "subdataset_metadata.json"
            metadata_file.write_text(json.dumps(metadata, indent=2))

            # Save metadata to the parent dataset
            dataset.save(
                message=f"Add subdataset metadata for {Path(subdataset_path).name}",
                path=[str(metadata_file)],
            )

            self.logger.info(
                f"Installed subdataset: {subdataset_url} -> {subdataset_path}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to install subdataset {subdataset_url}: {e}")
            return False

    def update_subdataset(self, subdataset_path: str) -> bool:
        """
        Update an existing subdataset to the latest version.

        Args:
            subdataset_path: Path to the subdataset

        Returns:
            True if successful, False otherwise
        """
        if not DATALAD_AVAILABLE:
            self.logger.error("DataLad not available. Cannot update subdataset.")
            return False

        try:
            target_path = self.repo_manager.base_path / subdataset_path

            if not target_path.exists():
                self.logger.error(f"Subdataset not found: {subdataset_path}")
                return False

            # Update the subdataset
            subdataset = Dataset(target_path)
            subdataset.update(merge=True)

            # Update metadata
            metadata_file = target_path / "subdataset_metadata.json"
            if metadata_file.exists():
                try:
                    metadata = json.loads(metadata_file.read_text())
                    metadata["last_updated"] = time.time()
                    metadata["last_updated_date"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    metadata_file.write_text(json.dumps(metadata, indent=2))
                except Exception as e:
                    self.logger.warning(f"Could not update metadata: {e}")

            self.logger.info(f"Updated subdataset: {subdataset_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update subdataset {subdataset_path}: {e}")
            return False

    def get_available_datasets(
        self, dataset_type: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """
        Get list of available test datasets with comprehensive metadata.

        Args:
            dataset_type: Filter by dataset type ('test', 'evaluation', 'example')

        Returns:
            List of dataset metadata dictionaries
        """
        datasets = []

        # Determine which paths to search
        search_paths = []
        if dataset_type is None or dataset_type == "test":
            search_paths.append(("test", self.test_data_path))
        if dataset_type is None or dataset_type == "evaluation":
            search_paths.append(("evaluation", self.evaluation_data_path))
        if dataset_type is None or dataset_type == "example":
            search_paths.append(("example", self.conversion_examples_path))

        for path_type, search_path in search_paths:
            if not search_path.exists():
                continue

            for dataset_dir in search_path.iterdir():
                if dataset_dir.is_dir() and not dataset_dir.name.startswith("."):
                    dataset_info = self._get_dataset_info(dataset_dir, path_type)
                    if dataset_info:
                        datasets.append(dataset_info)

        return datasets

    def get_dataset_path(
        self, dataset_name: str, dataset_type: str = "test"
    ) -> Optional[Path]:
        """
        Get the file system path to a specific dataset.

        Args:
            dataset_name: Name of the dataset
            dataset_type: Type of dataset ('test', 'evaluation', 'example')

        Returns:
            Path to dataset or None if not found
        """
        if dataset_type == "evaluation":
            base_path = self.evaluation_data_path
        elif dataset_type == "example":
            base_path = self.conversion_examples_path
        else:
            base_path = self.test_data_path

        dataset_path = base_path / dataset_name
        return dataset_path if dataset_path.exists() else None

    def remove_dataset(self, dataset_name: str, dataset_type: str = "test") -> bool:
        """
        Remove a dataset from the repository.

        Args:
            dataset_name: Name of the dataset to remove
            dataset_type: Type of dataset ('test', 'evaluation', 'example')

        Returns:
            True if successful, False otherwise
        """
        try:
            dataset_path = self.get_dataset_path(dataset_name, dataset_type)
            if not dataset_path:
                self.logger.warning(f"Dataset not found: {dataset_name}")
                return True  # Already removed

            # Try to use DataLad if available
            if (
                DATALAD_AVAILABLE
                and (self.repo_manager.base_path / ".datalad").exists()
            ):
                try:
                    dataset = Dataset(self.repo_manager.base_path)
                    dataset.remove(
                        path=str(dataset_path),
                        message=f"Remove {dataset_type} dataset: {dataset_name}",
                    )
                    self.logger.info(f"Removed dataset using DataLad: {dataset_name}")
                    return True
                except Exception as e:
                    self.logger.warning(f"DataLad remove failed, using fallback: {e}")

            # Fallback to regular file operations
            import shutil

            shutil.rmtree(dataset_path)
            self.logger.info(f"Removed dataset: {dataset_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to remove dataset {dataset_name}: {e}")
            return False

    def list_subdatasets(self) -> list[dict[str, Any]]:
        """
        List all installed subdatasets.

        Returns:
            List of subdataset information
        """
        subdatasets = []

        if not DATALAD_AVAILABLE:
            return subdatasets

        try:
            Dataset(self.repo_manager.base_path)

            # Find all subdataset metadata files
            for metadata_file in self.repo_manager.base_path.rglob(
                "subdataset_metadata.json"
            ):
                try:
                    metadata = json.loads(metadata_file.read_text())
                    metadata["metadata_path"] = str(metadata_file)
                    subdatasets.append(metadata)
                except Exception as e:
                    self.logger.warning(
                        f"Could not read subdataset metadata {metadata_file}: {e}"
                    )

            return subdatasets

        except Exception as e:
            self.logger.error(f"Failed to list subdatasets: {e}")
            return subdatasets

    def get_datasets_by_format(self, format_name: str) -> list[dict[str, Any]]:
        """
        Get datasets filtered by detected format.

        Args:
            format_name: Format to filter by (e.g., 'open_ephys', 'spikeglx')

        Returns:
            List of matching datasets
        """
        all_datasets = self.get_available_datasets()
        return [d for d in all_datasets if d.get("format_detected") == format_name]

    def _get_dataset_info(
        self, dataset_path: Path, dataset_type: str
    ) -> Optional[dict[str, Any]]:
        """Get comprehensive information about a dataset."""
        try:
            metadata_file = dataset_path / "dataset_metadata.json"

            if metadata_file.exists():
                metadata = json.loads(metadata_file.read_text())
            else:
                # Create basic metadata for datasets without metadata files
                metadata = {
                    "name": dataset_path.name,
                    "description": "No metadata available",
                    "dataset_type": dataset_type,
                    "file_count": self._count_files(dataset_path),
                    "size_bytes": self._get_directory_size(dataset_path),
                    "format_detected": self._detect_format(dataset_path),
                }

            # Add current path information
            metadata["path"] = str(dataset_path)
            metadata["relative_path"] = str(
                dataset_path.relative_to(self.repo_manager.base_path)
            )

            # Add DataLad status if available
            if (
                DATALAD_AVAILABLE
                and (self.repo_manager.base_path / ".datalad").exists()
            ):
                try:
                    dataset = Dataset(self.repo_manager.base_path)
                    status = dataset.status(path=str(dataset_path), annex="basic")
                    metadata["datalad_status"] = status
                except Exception as e:
                    self.logger.debug(
                        f"Could not get DataLad status for {dataset_path}: {e}"
                    )

            return metadata

        except Exception as e:
            self.logger.warning(f"Could not get dataset info for {dataset_path}: {e}")
            return None

    def _count_files(self, path: Path) -> int:
        """Count files in a directory."""
        try:
            if path.is_file():
                return 1
            return len([f for f in path.rglob("*") if f.is_file()])
        except Exception:
            return 0

    def _get_directory_size(self, path: Path) -> int:
        """Get total size of directory in bytes."""
        total_size = 0
        try:
            if path.is_file():
                return path.stat().st_size

            for item in path.rglob("*"):
                if item.is_file():
                    total_size += item.stat().st_size
        except Exception:
            pass
        return total_size

    def _detect_format(self, path: Path) -> str:
        """Detect the format of a dataset based on file patterns."""
        try:
            files = list(path.rglob("*"))
            file_names = [f.name.lower() for f in files if f.is_file()]

            # Check for Open Ephys format
            if any(".continuous" in name for name in file_names):
                return "open_ephys"

            # Check for SpikeGLX format
            if any(name.endswith(".bin") and ".imec" in name for name in file_names):
                return "spikeglx"

            # Check for NWB format
            if any(name.endswith(".nwb") for name in file_names):
                return "nwb"

            # Check for generic CSV/TSV
            if any(name.endswith((".csv", ".tsv")) for name in file_names):
                return "generic_csv"

            # Check for HDF5/MAT files
            if any(name.endswith((".h5", ".hdf5", ".mat")) for name in file_names):
                return "hdf5_mat"

            return "unknown"

        except Exception:
            return "unknown"
