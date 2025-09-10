"""DataLad repository structure management for development and conversions."""

import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

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
            self.logger.warning("DataLad not available. Repository management will be limited.")
        
        # Repository structure
        self.structure = {
            'etl': {
                'input-data': 'Raw input datasets for testing',
                'evaluation-data': 'Datasets for evaluation and benchmarking',
                'workflows': 'ETL workflow definitions',
                'prompt-input-data': 'Data for prompt engineering and testing'
            },
            'tests': {
                'fixtures': 'Test data fixtures',
                'integration-tests': 'Integration test data',
                'unit-tests': 'Unit test data'
            },
            'examples': {
                'conversion-examples': 'Example conversion repositories',
                'sample-datasets': 'Small sample datasets for documentation'
            }
        }
    
    def initialize_development_repository(self) -> Optional[Dataset]:
        """Initialize the main development DataLad repository."""
        if not DATALAD_AVAILABLE:
            self.logger.error("DataLad not available. Cannot initialize repository.")
            return None
            
        try:
            # Check if already a DataLad dataset
            if (self.base_path / '.datalad').exists():
                dataset = Dataset(self.base_path)
                self.logger.info(f"Using existing DataLad dataset: {self.base_path}")
            else:
                # Create new DataLad dataset
                dataset = dl.create(path=str(self.base_path), description="Agentic Neurodata Converter")
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
                    readme_path = subdir_path / 'README.md'
                    if not readme_path.exists():
                        readme_path.write_text(f"# {subdir.replace('-', ' ').title()}\n\n{description}\n")
        
        # Save structure to dataset if DataLad is available
        if dataset and DATALAD_AVAILABLE:
            dataset.save(message="Initialize directory structure", path=[str(self.base_path)])
    
    def _configure_git_attributes(self, dataset: Optional[Dataset]):
        """Configure .gitattributes for proper file handling."""
        gitattributes_path = self.base_path / '.gitattributes'
        
        # Define rules for what should be annexed vs tracked in git
        gitattributes_content = '''
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
'''
        
        gitattributes_path.write_text(gitattributes_content.strip())
        
        if dataset and DATALAD_AVAILABLE:
            dataset.save(message="Configure git attributes for file handling", path=[str(gitattributes_path)])
        
        self.logger.info("Configured .gitattributes for proper file handling")


class TestDatasetManager:
    """Manages test datasets for development and testing."""
    
    def __init__(self, repository_manager: DataLadRepositoryManager):
        self.repo_manager = repository_manager
        self.logger = logging.getLogger(__name__)
        self.test_data_path = repository_manager.base_path / 'etl' / 'input-data'
    
    def add_test_dataset(self, dataset_name: str, source_path: str, 
                        description: str = "", metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Add a test dataset to the repository."""
        try:
            dataset = None
            
            # Only try to use DataLad if available and we're in a DataLad repository
            if DATALAD_AVAILABLE and (self.repo_manager.base_path / '.datalad').exists():
                try:
                    dataset = Dataset(self.repo_manager.base_path)
                except Exception as e:
                    self.logger.warning(f"Could not access DataLad dataset: {e}")
                    dataset = None
                
            target_path = self.test_data_path / dataset_name
            
            # Copy or link dataset
            if Path(source_path).exists():
                import shutil
                if Path(source_path).is_dir():
                    shutil.copytree(source_path, target_path, dirs_exist_ok=True)
                else:
                    target_path.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, target_path)
                
                # Create metadata file
                metadata_file = target_path / 'dataset_metadata.json'
                dataset_metadata = {
                    'name': dataset_name,
                    'description': description,
                    'source_path': source_path,
                    'added_timestamp': time.time(),
                    'custom_metadata': metadata or {}
                }
                
                metadata_file.write_text(json.dumps(dataset_metadata, indent=2))
                
                # Save to DataLad if available and we have a dataset
                if dataset:
                    try:
                        dataset.save(
                            message=f"Add test dataset: {dataset_name}",
                            path=[str(target_path)]
                        )
                    except Exception as e:
                        self.logger.warning(f"Could not save to DataLad: {e}")
                
                self.logger.info(f"Added test dataset: {dataset_name}")
                return True
            else:
                self.logger.error(f"Source path does not exist: {source_path}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to add test dataset {dataset_name}: {e}")
            return False
    
    def install_subdataset(self, subdataset_url: str, subdataset_path: str) -> bool:
        """Install a subdataset for test data."""
        if not DATALAD_AVAILABLE:
            self.logger.error("DataLad not available. Cannot install subdataset.")
            return False
            
        try:
            dataset = Dataset(self.repo_manager.base_path)
            target_path = self.repo_manager.base_path / subdataset_path
            
            # Install subdataset
            subdataset = dl.install(
                source=subdataset_url,
                path=str(target_path),
                dataset=dataset
            )
            
            self.logger.info(f"Installed subdataset: {subdataset_url} -> {subdataset_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to install subdataset {subdataset_url}: {e}")
            return False
    
    def get_available_datasets(self) -> List[Dict[str, Any]]:
        """Get list of available test datasets."""
        datasets = []
        
        if not self.test_data_path.exists():
            return datasets
        
        for dataset_dir in self.test_data_path.iterdir():
            if dataset_dir.is_dir():
                metadata_file = dataset_dir / 'dataset_metadata.json'
                if metadata_file.exists():
                    try:
                        metadata = json.loads(metadata_file.read_text())
                        datasets.append(metadata)
                    except Exception as e:
                        self.logger.warning(f"Could not read metadata for {dataset_dir.name}: {e}")
                        datasets.append({
                            'name': dataset_dir.name,
                            'description': 'No metadata available',
                            'path': str(dataset_dir)
                        })
                else:
                    datasets.append({
                        'name': dataset_dir.name,
                        'description': 'No metadata available',
                        'path': str(dataset_dir)
                    })
        
        return datasets