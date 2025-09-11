# Data Management and Provenance Design

## Overview

This design document outlines the data management and provenance tracking
systems for the agentic neurodata conversion project. The system uses DataLad
for both development data management (test datasets, evaluation data) and user
conversion output provenance tracking, ensuring complete transparency and
reproducibility of all conversion processes.

## Architecture

### High-Level Data Management Architecture

```
Data Management and Provenance Systems
├── Development Data Management
│   ├── DataLad Repository Structure
│   ├── Test Dataset Management
│   ├── Evaluation Data Management
│   └── Subdataset Management
├── Conversion Provenance Tracking
│   ├── Conversion Repository Creation
│   ├── Pipeline State Tracking
│   ├── Agent Decision Recording
│   └── Output Organization
├── DataLad Integration Layer
│   ├── Python API Wrapper
│   ├── Repository Management
│   ├── File Handling Utilities
│   └── Error Recovery Systems
└── Provenance Reporting
    ├── Audit Trail Generation
    ├── Metadata Provenance Reports
    ├── Conversion History Summaries
    └── Reproducibility Documentation
```

### Data Flow Architecture

```
Development Flow:
Test Datasets → DataLad Management → Version Control → Team Access

Conversion Flow:
Input Data → Conversion Repository → Pipeline Tracking → Output Organization → Provenance Reports

Integration Flow:
MCP Server → Agent Decisions → Provenance Recording → DataLad Commits → History Tracking
```

## Core Components

### 1. Development Data Management

#### DataLad Repository Structure

```python
# agentic_neurodata_conversion/data_management/repository_structure.py
from pathlib import Path
from typing import Dict, Any, List, Optional
import datalad.api as dl
from datalad.api import Dataset
import logging

class DataLadRepositoryManager:
    """Manages DataLad repository structure for development and conversions."""

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.logger = logging.getLogger(__name__)

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

    def initialize_development_repository(self) -> Dataset:
        """Initialize the main development DataLad repository."""
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

    def _setup_directory_structure(self, dataset: Dataset):
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
                        readme_path.write_text(f"# {subdir.replace('-', ' ').title()}\\n\\n{description}\\n")

        # Save structure to dataset
        dataset.save(message="Initialize directory structure", path=[str(self.base_path)])

    def _configure_git_attributes(self, dataset: Dataset):
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
            dataset = Dataset(self.repo_manager.base_path)
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

                import json
                metadata_file.write_text(json.dumps(dataset_metadata, indent=2))

                # Save to DataLad
                dataset.save(
                    message=f"Add test dataset: {dataset_name}",
                    path=[str(target_path)]
                )

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
                        import json
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
```

### 2. Conversion Provenance Tracking

#### Conversion Repository Management

```python
# agentic_neurodata_conversion/data_management/conversion_provenance.py
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import datalad.api as dl
from datalad.api import Dataset
import logging

class ProvenanceSource(Enum):
    """Sources of metadata and data."""
    USER_PROVIDED = "user_provided"
    AUTO_EXTRACTED = "auto_extracted"
    AI_GENERATED = "ai_generated"
    EXTERNAL_ENRICHED = "external_enriched"
    DOMAIN_KNOWLEDGE = "domain_knowledge"

@dataclass
class ProvenanceRecord:
    """Individual provenance record."""
    timestamp: float
    source: ProvenanceSource
    agent: Optional[str]
    operation: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class ConversionSession:
    """Complete conversion session with provenance."""
    session_id: str
    start_time: float
    end_time: Optional[float]
    dataset_path: str
    output_path: str
    status: str
    provenance_records: List[ProvenanceRecord]
    final_metadata: Dict[str, Any]
    pipeline_state: Dict[str, Any]

    def __post_init__(self):
        if self.provenance_records is None:
            self.provenance_records = []

class ConversionProvenanceTracker:
    """Tracks provenance for individual conversions."""

    def __init__(self, conversion_id: str, output_dir: str):
        self.conversion_id = conversion_id
        self.output_dir = Path(output_dir)
        self.logger = logging.getLogger(__name__)

        # Create conversion-specific DataLad repository
        self.conversion_repo_path = self.output_dir / f"conversion_{conversion_id}"
        self.dataset = self._initialize_conversion_repository()

        # Initialize session
        self.session = ConversionSession(
            session_id=conversion_id,
            start_time=time.time(),
            end_time=None,
            dataset_path="",
            output_path=str(self.conversion_repo_path),
            status="started",
            provenance_records=[],
            final_metadata={},
            pipeline_state={}
        )

    def _initialize_conversion_repository(self) -> Dataset:
        """Initialize DataLad repository for this conversion."""
        try:
            # Create conversion directory
            self.conversion_repo_path.mkdir(parents=True, exist_ok=True)

            # Initialize DataLad dataset
            dataset = dl.create(
                path=str(self.conversion_repo_path),
                description=f"Conversion {self.conversion_id} - Agentic Neurodata Converter"
            )

            # Create directory structure
            subdirs = ['inputs', 'outputs', 'scripts', 'reports', 'provenance']
            for subdir in subdirs:
                (self.conversion_repo_path / subdir).mkdir(exist_ok=True)

            # Create initial README
            readme_content = f"""# Conversion {self.conversion_id}

This DataLad repository contains the complete conversion process and outputs for conversion session {self.conversion_id}.

## Structure

- `inputs/`: Input data and metadata
- `outputs/`: Generated NWB files and conversion outputs
- `scripts/`: Generated conversion scripts
- `reports/`: Validation and evaluation reports
- `provenance/`: Detailed provenance tracking files

## Provenance

This conversion was performed using the Agentic Neurodata Converter.
All decisions, transformations, and outputs are tracked with complete provenance.

Started: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.session.start_time))}
"""

            readme_path = self.conversion_repo_path / 'README.md'
            readme_path.write_text(readme_content)

            # Initial commit
            dataset.save(message=f"Initialize conversion repository for {self.conversion_id}")

            self.logger.info(f"Initialized conversion repository: {self.conversion_repo_path}")
            return dataset

        except Exception as e:
            self.logger.error(f"Failed to initialize conversion repository: {e}")
            raise

    def record_provenance(self, source: ProvenanceSource, agent: Optional[str],
                         operation: str, input_data: Dict[str, Any],
                         output_data: Dict[str, Any], confidence: Optional[float] = None,
                         metadata: Optional[Dict[str, Any]] = None):
        """Record a provenance entry."""
        record = ProvenanceRecord(
            timestamp=time.time(),
            source=source,
            agent=agent,
            operation=operation,
            input_data=input_data,
            output_data=output_data,
            confidence=confidence,
            metadata=metadata or {}
        )

        self.session.provenance_records.append(record)

        # Save provenance record to file
        self._save_provenance_record(record)

        self.logger.debug(f"Recorded provenance: {operation} by {agent or 'system'}")

    def _save_provenance_record(self, record: ProvenanceRecord):
        """Save individual provenance record to file."""
        provenance_dir = self.conversion_repo_path / 'provenance'
        record_file = provenance_dir / f"record_{len(self.session.provenance_records):04d}.json"

        record_data = asdict(record)
        record_data['source'] = record.source.value  # Convert enum to string

        record_file.write_text(json.dumps(record_data, indent=2, default=str))

    def update_pipeline_state(self, state_updates: Dict[str, Any]):
        """Update pipeline state and record the change."""
        old_state = self.session.pipeline_state.copy()
        self.session.pipeline_state.update(state_updates)

        self.record_provenance(
            source=ProvenanceSource.AUTO_EXTRACTED,
            agent="pipeline_manager",
            operation="state_update",
            input_data={"previous_state": old_state},
            output_data={"new_state": self.session.pipeline_state},
            metadata={"state_changes": state_updates}
        )

        # Save current state
        state_file = self.conversion_repo_path / 'provenance' / 'pipeline_state.json'
        state_file.write_text(json.dumps(self.session.pipeline_state, indent=2, default=str))

    def save_conversion_artifact(self, artifact_path: str, artifact_type: str,
                               description: str = "", metadata: Optional[Dict[str, Any]] = None):
        """Save a conversion artifact with provenance."""
        artifact_source = Path(artifact_path)
        if not artifact_source.exists():
            self.logger.warning(f"Artifact not found: {artifact_path}")
            return

        # Determine target directory based on artifact type
        type_mapping = {
            'nwb_file': 'outputs',
            'conversion_script': 'scripts',
            'validation_report': 'reports',
            'evaluation_report': 'reports',
            'knowledge_graph': 'outputs',
            'input_data': 'inputs'
        }

        target_dir = self.conversion_repo_path / type_mapping.get(artifact_type, 'outputs')
        target_path = target_dir / artifact_source.name

        # Copy artifact
        import shutil
        if artifact_source.is_dir():
            shutil.copytree(artifact_source, target_path, dirs_exist_ok=True)
        else:
            shutil.copy2(artifact_source, target_path)

        # Record provenance
        self.record_provenance(
            source=ProvenanceSource.AUTO_EXTRACTED,
            agent="artifact_manager",
            operation="save_artifact",
            input_data={"source_path": str(artifact_source)},
            output_data={"target_path": str(target_path), "artifact_type": artifact_type},
            metadata={"description": description, "custom_metadata": metadata or {}}
        )

        # Commit to DataLad
        self.dataset.save(
            message=f"Add {artifact_type}: {artifact_source.name}",
            path=[str(target_path)]
        )

        self.logger.info(f"Saved artifact: {artifact_source.name} -> {target_path}")

    def finalize_conversion(self, status: str, final_metadata: Dict[str, Any]):
        """Finalize the conversion and create summary."""
        self.session.end_time = time.time()
        self.session.status = status
        self.session.final_metadata = final_metadata

        # Generate conversion summary
        summary = self._generate_conversion_summary()

        # Save complete session data
        session_file = self.conversion_repo_path / 'provenance' / 'conversion_session.json'
        session_data = asdict(self.session)
        # Convert enums to strings
        for record in session_data['provenance_records']:
            record['source'] = record['source'] if isinstance(record['source'], str) else record['source'].value

        session_file.write_text(json.dumps(session_data, indent=2, default=str))

        # Save summary
        summary_file = self.conversion_repo_path / 'CONVERSION_SUMMARY.md'
        summary_file.write_text(summary)

        # Final commit with tag
        self.dataset.save(message=f"Finalize conversion {self.conversion_id} - Status: {status}")

        if status == "completed":
            # Tag successful conversion
            try:
                import subprocess
                subprocess.run([
                    'git', 'tag', '-a', f'conversion-{self.conversion_id}',
                    '-m', f'Completed conversion {self.conversion_id}'
                ], cwd=self.conversion_repo_path, check=True)
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"Failed to create git tag: {e}")

        self.logger.info(f"Finalized conversion {self.conversion_id} with status: {status}")

    def _generate_conversion_summary(self) -> str:
        """Generate human-readable conversion summary."""
        duration = (self.session.end_time or time.time()) - self.session.start_time

        # Count provenance records by source
        source_counts = {}
        agent_counts = {}

        for record in self.session.provenance_records:
            source = record.source.value if hasattr(record.source, 'value') else str(record.source)
            source_counts[source] = source_counts.get(source, 0) + 1

            if record.agent:
                agent_counts[record.agent] = agent_counts.get(record.agent, 0) + 1

        summary = f"""# Conversion Summary: {self.conversion_id}

## Overview
- **Status**: {self.session.status}
- **Duration**: {duration:.2f} seconds
- **Start Time**: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.session.start_time))}
- **End Time**: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.session.end_time or time.time()))}

## Provenance Summary
- **Total Operations**: {len(self.session.provenance_records)}

### Data Sources
"""

        for source, count in source_counts.items():
            summary += f"- **{source.replace('_', ' ').title()}**: {count} operations\\n"

        summary += "\\n### Agent Activity\\n"
        for agent, count in agent_counts.items():
            summary += f"- **{agent}**: {count} operations\\n"

        # Add metadata summary
        if self.session.final_metadata:
            summary += f"""
## Final Metadata Summary
- **Fields Populated**: {len(self.session.final_metadata)}
- **Required NWB Fields**: {self._count_required_fields()}

## Key Metadata Fields
"""
            key_fields = ['identifier', 'session_description', 'experimenter', 'lab', 'institution']
            for field in key_fields:
                value = self.session.final_metadata.get(field, 'Not provided')
                summary += f"- **{field}**: {value}\\n"

        # Add file summary
        summary += f"""
## Generated Files
- **NWB File**: {self._get_nwb_file_info()}
- **Conversion Scripts**: {self._count_files('scripts')}
- **Reports**: {self._count_files('reports')}
- **Provenance Records**: {len(self.session.provenance_records)}

## Repository Structure
```

{self.\_generate_tree_structure()}

```

## Reproducibility
This conversion can be reproduced using the saved conversion scripts and provenance information.
All agent decisions and data transformations are recorded with complete audit trails.
"""

        return summary

    def _count_required_fields(self) -> int:
        """Count required NWB fields that are populated."""
        required_fields = [
            'identifier', 'session_description', 'session_start_time',
            'experimenter', 'lab', 'institution'
        ]
        return sum(1 for field in required_fields if field in self.session.final_metadata)

    def _get_nwb_file_info(self) -> str:
        """Get information about generated NWB file."""
        outputs_dir = self.conversion_repo_path / 'outputs'
        nwb_files = list(outputs_dir.glob('*.nwb'))

        if nwb_files:
            nwb_file = nwb_files[0]
            size = nwb_file.stat().st_size
            return f"{nwb_file.name} ({size / (1024*1024):.1f} MB)"
        return "No NWB file generated"

    def _count_files(self, directory: str) -> int:
        """Count files in a directory."""
        dir_path = self.conversion_repo_path / directory
        if dir_path.exists():
            return len([f for f in dir_path.iterdir() if f.is_file()])
        return 0

    def _generate_tree_structure(self) -> str:
        """Generate tree structure of the repository."""
        def _tree_recursive(path: Path, prefix: str = "", max_depth: int = 2, current_depth: int = 0) -> str:
            if current_depth >= max_depth:
                return ""

            items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name))
            tree_str = ""

            for i, item in enumerate(items):
                is_last = i == len(items) - 1
                current_prefix = "└── " if is_last else "├── "
                tree_str += f"{prefix}{current_prefix}{item.name}\\n"

                if item.is_dir() and current_depth < max_depth - 1:
                    next_prefix = prefix + ("    " if is_last else "│   ")
                    tree_str += _tree_recursive(item, next_prefix, max_depth, current_depth + 1)

            return tree_str

        return _tree_recursive(self.conversion_repo_path)

class ProvenanceIntegration:
    """Integrates provenance tracking with MCP server operations."""

    def __init__(self, provenance_tracker: ConversionProvenanceTracker):
        self.tracker = provenance_tracker
        self.logger = logging.getLogger(__name__)

    def record_agent_operation(self, agent_name: str, operation: str,
                             input_data: Dict[str, Any], output_data: Dict[str, Any],
                             confidence: Optional[float] = None):
        """Record an agent operation with provenance."""
        # Determine source based on agent type
        source_mapping = {
            'conversation': ProvenanceSource.AI_GENERATED,
            'conversion': ProvenanceSource.AUTO_EXTRACTED,
            'evaluation': ProvenanceSource.AUTO_EXTRACTED,
            'knowledge_graph': ProvenanceSource.EXTERNAL_ENRICHED
        }

        source = source_mapping.get(agent_name, ProvenanceSource.AUTO_EXTRACTED)

        self.tracker.record_provenance(
            source=source,
            agent=agent_name,
            operation=operation,
            input_data=input_data,
            output_data=output_data,
            confidence=confidence,
            metadata={'mcp_server_operation': True}
        )

    def record_user_input(self, field: str, value: Any, context: Dict[str, Any] = None):
        """Record user-provided input."""
        self.tracker.record_provenance(
            source=ProvenanceSource.USER_PROVIDED,
            agent=None,
            operation="user_input",
            input_data={"field": field, "context": context or {}},
            output_data={"field": field, "value": value},
            confidence=1.0,  # User input has highest confidence
            metadata={'user_provided': True}
        )

    def record_external_enrichment(self, source_system: str, field: str,
                                 original_value: Any, enriched_value: Any,
                                 confidence: float):
        """Record external knowledge enrichment."""
        self.tracker.record_provenance(
            source=ProvenanceSource.EXTERNAL_ENRICHED,
            agent=source_system,
            operation="external_enrichment",
            input_data={"field": field, "original_value": original_value},
            output_data={"field": field, "enriched_value": enriched_value},
            confidence=confidence,
            metadata={'external_source': source_system}
        )

    def generate_metadata_provenance_report(self) -> Dict[str, Any]:
        """Generate detailed provenance report for metadata fields."""
        metadata_provenance = {}

        for record in self.tracker.session.provenance_records:
            if 'field' in record.output_data:
                field = record.output_data['field']
                if field not in metadata_provenance:
                    metadata_provenance[field] = []

                metadata_provenance[field].append({
                    'timestamp': record.timestamp,
                    'source': record.source.value if hasattr(record.source, 'value') else str(record.source),
                    'agent': record.agent,
                    'operation': record.operation,
                    'value': record.output_data.get('value', record.output_data.get('enriched_value')),
                    'confidence': record.confidence,
                    'metadata': record.metadata
                })

        return metadata_provenance
```

### 3. DataLad Integration Layer

#### Python API Wrapper

```python
# agentic_neurodata_conversion/data_management/datalad_wrapper.py
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import datalad.api as dl
from datalad.api import Dataset
from datalad.support.exceptions import IncompleteResultsError, CommandError
import logging
import time

class DataLadWrapper:
    """Wrapper for DataLad operations with error handling and best practices."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def safe_create_dataset(self, path: Union[str, Path], description: str = "",
                          force: bool = False) -> Optional[Dataset]:
        """Safely create a DataLad dataset with error handling."""
        path = Path(path)

        try:
            # Check if already exists
            if (path / '.datalad').exists() and not force:
                self.logger.info(f"Dataset already exists: {path}")
                return Dataset(path)

            # Create dataset
            dataset = dl.create(
                path=str(path),
                description=description,
                force=force
            )

            self.logger.info(f"Created DataLad dataset: {path}")
            return dataset

        except Exception as e:
            self.logger.error(f"Failed to create dataset at {path}: {e}")
            return None

    def safe_install_subdataset(self, parent_dataset: Dataset, source: str,
                              path: str, recursive: bool = False) -> Optional[Dataset]:
        """Safely install a subdataset with error handling."""
        try:
            subdataset = dl.install(
                source=source,
                path=path,
                dataset=parent_dataset,
                recursive=recursive
            )

            self.logger.info(f"Installed subdataset: {source} -> {path}")
            return subdataset

        except Exception as e:
            self.logger.error(f"Failed to install subdataset {source}: {e}")
            return None

    def safe_save(self, dataset: Dataset, message: str, path: Optional[List[str]] = None,
                 recursive: bool = False) -> bool:
        """Safely save dataset changes with error handling."""
        try:
            result = dataset.save(
                message=message,
                path=path,
                recursive=recursive
            )

            # Check for any failures in the result
            if hasattr(result, '__iter__'):
                failures = [r for r in result if r.get('status') == 'error']
                if failures:
                    self.logger.warning(f"Some files failed to save: {failures}")
                    return False

            self.logger.debug(f"Saved dataset changes: {message}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to save dataset: {e}")
            return False

    def safe_get(self, dataset: Dataset, path: Union[str, List[str]],
                source: Optional[str] = None) -> bool:
        """Safely get data files with error handling."""
        try:
            result = dataset.get(path=path, source=source)

            # Check for failures
            if hasattr(result, '__iter__'):
                failures = [r for r in result if r.get('status') == 'error']
                if failures:
                    self.logger.warning(f"Some files failed to download: {failures}")
                    return False

            self.logger.debug(f"Retrieved data: {path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to get data {path}: {e}")
            return False

    def check_dataset_integrity(self, dataset: Dataset) -> Dict[str, Any]:
        """Check dataset integrity and report issues."""
        integrity_report = {
            'is_valid': True,
            'issues': [],
            'warnings': [],
            'statistics': {}
        }

        try:
            # Check if dataset is properly initialized
            if not (Path(dataset.path) / '.datalad').exists():
                integrity_report['is_valid'] = False
                integrity_report['issues'].append("Dataset not properly initialized")
                return integrity_report

            # Check for locked files
            locked_files = self._find_locked_files(dataset)
            if locked_files:
                integrity_report['warnings'].append(f"Found {len(locked_files)} locked files")
                integrity_report['statistics']['locked_files'] = len(locked_files)

            # Check for missing subdatasets
            missing_subdatasets = self._find_missing_subdatasets(dataset)
            if missing_subdatasets:
                integrity_report['warnings'].append(f"Found {len(missing_subdatasets)} missing subdatasets")
                integrity_report['statistics']['missing_subdatasets'] = len(missing_subdatasets)

            # Check git status
            git_status = self._check_git_status(dataset)
            integrity_report['statistics'].update(git_status)

            self.logger.info(f"Dataset integrity check completed for {dataset.path}")

        except Exception as e:
            integrity_report['is_valid'] = False
            integrity_report['issues'].append(f"Integrity check failed: {e}")
            self.logger.error(f"Dataset integrity check failed: {e}")

        return integrity_report

    def _find_locked_files(self, dataset: Dataset) -> List[str]:
        """Find locked files in the dataset."""
        locked_files = []
        try:
            # This would use git-annex commands to find locked files
            # Implementation depends on specific DataLad/git-annex version
            pass
        except Exception as e:
            self.logger.debug(f"Could not check for locked files: {e}")

        return locked_files

    def _find_missing_subdatasets(self, dataset: Dataset) -> List[str]:
        """Find missing or uninstalled subdatasets."""
        missing = []
        try:
            # Check .gitmodules for subdatasets
            gitmodules_path = Path(dataset.path) / '.gitmodules'
            if gitmodules_path.exists():
                # Parse .gitmodules and check if subdatasets are installed
                # Implementation would parse the file and check paths
                pass
        except Exception as e:
            self.logger.debug(f"Could not check for missing subdatasets: {e}")

        return missing

    def _check_git_status(self, dataset: Dataset) -> Dict[str, int]:
        """Check git status of the dataset."""
        status = {
            'untracked_files': 0,
            'modified_files': 0,
            'staged_files': 0
        }

        try:
            import subprocess
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=dataset.path,
                capture_output=True,
                text=True,
                check=True
            )

            for line in result.stdout.strip().split('\\n'):
                if line:
                    if line.startswith('??'):
                        status['untracked_files'] += 1
                    elif line.startswith(' M'):
                        status['modified_files'] += 1
                    elif line.startswith('A ') or line.startswith('M '):
                        status['staged_files'] += 1

        except Exception as e:
            self.logger.debug(f"Could not check git status: {e}")

        return status

    def repair_dataset(self, dataset: Dataset) -> bool:
        """Attempt to repair common dataset issues."""
        try:
            self.logger.info(f"Attempting to repair dataset: {dataset.path}")

            # Unlock any locked files
            try:
                import subprocess
                subprocess.run(
                    ['git', 'annex', 'unlock', '.'],
                    cwd=dataset.path,
                    check=False  # Don't fail if no files to unlock
                )
            except Exception as e:
                self.logger.debug(f"Could not unlock files: {e}")

            # Try to fix any git issues
            try:
                subprocess.run(
                    ['git', 'fsck'],
                    cwd=dataset.path,
                    check=False
                )
            except Exception as e:
                self.logger.debug(f"Git fsck reported issues: {e}")

            self.logger.info("Dataset repair completed")
            return True

        except Exception as e:
            self.logger.error(f"Dataset repair failed: {e}")
            return False

# Utility functions for common DataLad operations
def setup_development_data_infrastructure(base_path: str = ".") -> bool:
    """Setup complete DataLad infrastructure for development."""
    try:
        # Initialize repository manager
        repo_manager = DataLadRepositoryManager(base_path)
        dataset = repo_manager.initialize_development_repository()

        # Initialize test dataset manager
        test_manager = TestDatasetManager(repo_manager)

        # Setup evaluation data from documents/possible-datasets
        possible_datasets_path = Path(base_path) / 'documents' / 'possible-datasets'
        if possible_datasets_path.exists():
            # Read and process possible datasets
            # Implementation would read dataset specifications and install them
            pass

        logging.info("Development data infrastructure setup completed")
        return True

    except Exception as e:
        logging.error(f"Failed to setup development data infrastructure: {e}")
        return False

def create_conversion_tracker(conversion_id: str, output_dir: str) -> ConversionProvenanceTracker:
    """Create a new conversion provenance tracker."""
    return ConversionProvenanceTracker(conversion_id, output_dir)
```

### 4. Integration with MCP Server

#### MCP Server Provenance Integration

```python
# agentic_neurodata_conversion/mcp_server/provenance_integration.py
from typing import Dict, Any, Optional
from ..data_management.conversion_provenance import ConversionProvenanceTracker, ProvenanceIntegration
from ..data_management.datalad_wrapper import create_conversion_tracker
import uuid
import logging

class MCPProvenanceManager:
    """Manages provenance tracking for MCP server operations."""

    def __init__(self):
        self.active_conversions: Dict[str, ConversionProvenanceTracker] = {}
        self.logger = logging.getLogger(__name__)

    def start_conversion_tracking(self, dataset_dir: str, output_dir: str = "outputs") -> str:
        """Start provenance tracking for a new conversion."""
        conversion_id = str(uuid.uuid4())[:8]

        tracker = create_conversion_tracker(conversion_id, output_dir)
        tracker.session.dataset_path = dataset_dir

        self.active_conversions[conversion_id] = tracker

        self.logger.info(f"Started provenance tracking for conversion {conversion_id}")
        return conversion_id

    def get_tracker(self, conversion_id: str) -> Optional[ConversionProvenanceTracker]:
        """Get provenance tracker for a conversion."""
        return self.active_conversions.get(conversion_id)

    def record_tool_execution(self, conversion_id: str, tool_name: str,
                            input_data: Dict[str, Any], output_data: Dict[str, Any],
                            agent_name: Optional[str] = None):
        """Record MCP tool execution with provenance."""
        tracker = self.get_tracker(conversion_id)
        if tracker:
            integration = ProvenanceIntegration(tracker)
            integration.record_agent_operation(
                agent_name=agent_name or tool_name,
                operation=f"mcp_tool_{tool_name}",
                input_data=input_data,
                output_data=output_data
            )

    def finalize_conversion(self, conversion_id: str, status: str,
                          final_metadata: Dict[str, Any]):
        """Finalize conversion tracking."""
        tracker = self.get_tracker(conversion_id)
        if tracker:
            tracker.finalize_conversion(status, final_metadata)
            # Remove from active conversions
            del self.active_conversions[conversion_id]
            self.logger.info(f"Finalized conversion tracking for {conversion_id}")

# Global provenance manager instance
provenance_manager = MCPProvenanceManager()
```

This design provides a comprehensive data management and provenance tracking
system that integrates seamlessly with the MCP server architecture while
maintaining complete transparency and reproducibility of all conversion
processes.
