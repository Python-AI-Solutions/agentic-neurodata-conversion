"""Conversion provenance tracking for complete audit trails and reproducibility."""

from dataclasses import asdict, dataclass
from enum import Enum
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


class ProvenanceSource(Enum):
    """Sources of metadata and data in the conversion pipeline."""

    USER_PROVIDED = "user_provided"
    AUTO_EXTRACTED = "auto_extracted"
    AI_GENERATED = "ai_generated"
    EXTERNAL_ENRICHED = "external_enriched"
    DOMAIN_KNOWLEDGE = "domain_knowledge"


@dataclass
class ProvenanceRecord:
    """Individual provenance record for tracking operations and decisions."""

    timestamp: float
    source: ProvenanceSource
    agent: Optional[str]
    operation: str
    input_data: dict[str, Any]
    output_data: dict[str, Any]
    confidence: Optional[float] = None
    metadata: Optional[dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ConversionSession:
    """Complete conversion session with comprehensive provenance tracking."""

    session_id: str
    start_time: float
    end_time: Optional[float]
    dataset_path: str
    output_path: str
    status: str
    provenance_records: list[ProvenanceRecord]
    final_metadata: dict[str, Any]
    pipeline_state: dict[str, Any]

    def __post_init__(self):
        if self.provenance_records is None:
            self.provenance_records = []
        if self.final_metadata is None:
            self.final_metadata = {}
        if self.pipeline_state is None:
            self.pipeline_state = {}


class ConversionProvenanceTracker:
    """
    Tracks complete provenance for individual conversions with DataLad integration.

    Creates a dedicated DataLad repository for each conversion session to maintain
    complete version control and history of the conversion process.
    """

    def __init__(self, conversion_id: str, output_dir: str, dataset_path: str = ""):
        self.conversion_id = conversion_id
        self.output_dir = Path(output_dir)
        self.logger = logging.getLogger(__name__)

        if not DATALAD_AVAILABLE:
            self.logger.warning(
                "DataLad not available. Provenance tracking will be limited."
            )

        # Create conversion-specific DataLad repository
        self.conversion_repo_path = self.output_dir / f"conversion_{conversion_id}"

        # Initialize conversion session BEFORE repository initialization
        self.session = ConversionSession(
            session_id=conversion_id,
            start_time=time.time(),
            end_time=None,
            dataset_path=dataset_path,
            output_path=str(self.conversion_repo_path),
            status="started",
            provenance_records=[],
            final_metadata={},
            pipeline_state={},
        )

        # Now initialize the repository (which needs session for README generation)
        self.dataset = self._initialize_conversion_repository()

        # Record session initialization
        self.record_provenance(
            source=ProvenanceSource.AUTO_EXTRACTED,
            agent="conversion_tracker",
            operation="session_initialize",
            input_data={"conversion_id": conversion_id, "dataset_path": dataset_path},
            output_data={
                "session_id": conversion_id,
                "output_path": str(self.conversion_repo_path),
            },
            confidence=1.0,
            metadata={"initialization_time": time.strftime("%Y-%m-%d %H:%M:%S")},
        )

    def _initialize_conversion_repository(self) -> Optional[Dataset]:
        """Initialize DataLad repository for this conversion with proper structure."""
        try:
            # Create conversion directory
            self.conversion_repo_path.mkdir(parents=True, exist_ok=True)

            dataset = None

            # Initialize DataLad dataset if available
            if DATALAD_AVAILABLE:
                try:
                    dataset = dl.create(
                        path=str(self.conversion_repo_path),
                        description=f"Conversion {self.conversion_id} - Agentic Neurodata Converter",
                    )
                    self.logger.info(
                        f"Created DataLad repository: {self.conversion_repo_path}"
                    )
                except Exception as e:
                    self.logger.warning(f"Could not create DataLad repository: {e}")
                    dataset = None

            # Create directory structure for conversion outputs
            subdirs = ["inputs", "outputs", "scripts", "reports", "provenance"]
            for subdir in subdirs:
                (self.conversion_repo_path / subdir).mkdir(exist_ok=True)

            # Create initial README
            readme_content = self._generate_initial_readme()
            readme_path = self.conversion_repo_path / "README.md"
            readme_path.write_text(readme_content)

            # Create .gitattributes for proper file handling
            self._create_gitattributes()

            # Initial commit if DataLad is available
            if dataset:
                try:
                    dataset.save(
                        message=f"Initialize conversion repository for {self.conversion_id}"
                    )
                except Exception as e:
                    self.logger.warning(f"Could not save initial commit: {e}")

            return dataset

        except Exception as e:
            self.logger.error(f"Failed to initialize conversion repository: {e}")
            raise

    def _generate_initial_readme(self) -> str:
        """Generate initial README for the conversion repository."""
        return f"""# Conversion {self.conversion_id}

This DataLad repository contains the complete conversion process and outputs for conversion session {self.conversion_id}.

## Structure

- `inputs/`: Input data and metadata files
- `outputs/`: Generated NWB files and conversion outputs
- `scripts/`: Generated conversion scripts and code
- `reports/`: Validation and evaluation reports
- `provenance/`: Detailed provenance tracking files

## Provenance Tracking

This conversion was performed using the Agentic Neurodata Converter with complete provenance tracking.
All decisions, transformations, and outputs are recorded with detailed audit trails.

- **Started**: {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.session.start_time))}
- **Session ID**: {self.conversion_id}
- **Status**: {self.session.status}

## Reproducibility

This conversion can be reproduced using the saved conversion scripts and provenance information.
All agent decisions and data transformations are recorded with complete audit trails.

## DataLad Integration

This repository uses DataLad for version control and data management:
- All files are properly versioned
- Large data files are handled efficiently through git-annex
- Complete history is maintained for reproducibility
"""

    def _create_gitattributes(self):
        """Create .gitattributes for proper file handling in conversion repository."""
        gitattributes_content = """
# Conversion scripts and metadata - keep in git
*.py annex.largefiles=nothing
*.md annex.largefiles=nothing
*.txt annex.largefiles=nothing
*.json annex.largefiles=nothing
*.yaml annex.largefiles=nothing
*.yml annex.largefiles=nothing
*.log annex.largefiles=(largerthan=1MB)

# Small data files - keep in git if small
*.csv annex.largefiles=(largerthan=10MB)
*.tsv annex.largefiles=(largerthan=10MB)

# Large data files - always annex
*.nwb annex.largefiles=anything
*.dat annex.largefiles=anything
*.bin annex.largefiles=anything
*.h5 annex.largefiles=anything
*.hdf5 annex.largefiles=anything
*.mat annex.largefiles=anything

# Reports - keep small ones in git
*.html annex.largefiles=(largerthan=5MB)
*.pdf annex.largefiles=(largerthan=5MB)
"""

        gitattributes_path = self.conversion_repo_path / ".gitattributes"
        gitattributes_path.write_text(gitattributes_content.strip())

    def record_provenance(
        self,
        source: ProvenanceSource,
        agent: Optional[str],
        operation: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        confidence: Optional[float] = None,
        metadata: Optional[dict[str, Any]] = None,
    ):
        """
        Record a provenance entry with complete tracking information.

        Args:
            source: Source of the operation (user, auto, AI, etc.)
            agent: Name of the agent or system performing the operation
            operation: Description of the operation performed
            input_data: Input data for the operation
            output_data: Output data from the operation
            confidence: Confidence level of the operation (0.0-1.0)
            metadata: Additional metadata about the operation
        """
        record = ProvenanceRecord(
            timestamp=time.time(),
            source=source,
            agent=agent,
            operation=operation,
            input_data=input_data,
            output_data=output_data,
            confidence=confidence,
            metadata=metadata or {},
        )

        self.session.provenance_records.append(record)

        # Save provenance record to file
        self._save_provenance_record(record)

        self.logger.debug(f"Recorded provenance: {operation} by {agent or 'system'}")

    def _save_provenance_record(self, record: ProvenanceRecord):
        """Save individual provenance record to file with proper formatting."""
        provenance_dir = self.conversion_repo_path / "provenance"
        record_file = (
            provenance_dir / f"record_{len(self.session.provenance_records):04d}.json"
        )

        # Convert record to dictionary with proper enum handling
        record_data = asdict(record)
        record_data["source"] = record.source.value  # Convert enum to string
        record_data["timestamp_human"] = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(record.timestamp)
        )

        record_file.write_text(json.dumps(record_data, indent=2, default=str))

        # Also append to consolidated provenance log
        provenance_log = provenance_dir / "provenance_log.jsonl"
        with open(provenance_log, "a") as f:
            f.write(json.dumps(record_data, default=str) + "\n")

    def update_pipeline_state(self, state_updates: dict[str, Any]):
        """
        Update pipeline state and record the change with provenance.

        Args:
            state_updates: Dictionary of state changes to apply
        """
        old_state = self.session.pipeline_state.copy()
        self.session.pipeline_state.update(state_updates)

        self.record_provenance(
            source=ProvenanceSource.AUTO_EXTRACTED,
            agent="pipeline_manager",
            operation="state_update",
            input_data={"previous_state": old_state},
            output_data={"new_state": self.session.pipeline_state},
            metadata={"state_changes": state_updates},
        )

        # Save current state to file
        state_file = self.conversion_repo_path / "provenance" / "pipeline_state.json"
        state_data = {
            "current_state": self.session.pipeline_state,
            "last_updated": time.time(),
            "last_updated_human": time.strftime("%Y-%m-%d %H:%M:%S"),
            "update_count": len(
                [
                    r
                    for r in self.session.provenance_records
                    if r.operation == "state_update"
                ]
            ),
        }
        state_file.write_text(json.dumps(state_data, indent=2, default=str))

    def save_conversion_artifact(
        self,
        artifact_path: str,
        artifact_type: str,
        description: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ):
        """
        Save a conversion artifact with provenance tracking and proper organization.

        Args:
            artifact_path: Path to the artifact to save
            artifact_type: Type of artifact (nwb_file, conversion_script, etc.)
            description: Description of the artifact
            metadata: Additional metadata about the artifact
        """
        artifact_source = Path(artifact_path)
        if not artifact_source.exists():
            self.logger.warning(f"Artifact not found: {artifact_path}")
            return

        # Determine target directory based on artifact type
        type_mapping = {
            "nwb_file": "outputs",
            "conversion_script": "scripts",
            "validation_report": "reports",
            "evaluation_report": "reports",
            "knowledge_graph": "outputs",
            "input_data": "inputs",
            "metadata_file": "inputs",
            "log_file": "reports",
        }

        target_dir = self.conversion_repo_path / type_mapping.get(
            artifact_type, "outputs"
        )
        target_path = target_dir / artifact_source.name

        # Copy artifact with proper handling
        import shutil

        try:
            if artifact_source.is_dir():
                shutil.copytree(artifact_source, target_path, dirs_exist_ok=True)
            else:
                shutil.copy2(artifact_source, target_path)

            # Create artifact metadata
            artifact_metadata = {
                "name": artifact_source.name,
                "type": artifact_type,
                "description": description,
                "source_path": str(artifact_source),
                "target_path": str(target_path),
                "size_bytes": self._get_file_size(target_path),
                "saved_timestamp": time.time(),
                "saved_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "custom_metadata": metadata or {},
            }

            # Save artifact metadata
            metadata_file = target_path.parent / f"{target_path.name}.metadata.json"
            metadata_file.write_text(json.dumps(artifact_metadata, indent=2))

            # Record provenance
            self.record_provenance(
                source=ProvenanceSource.AUTO_EXTRACTED,
                agent="artifact_manager",
                operation="save_artifact",
                input_data={"source_path": str(artifact_source)},
                output_data={
                    "target_path": str(target_path),
                    "artifact_type": artifact_type,
                    "size_bytes": artifact_metadata["size_bytes"],
                },
                metadata={
                    "description": description,
                    "custom_metadata": metadata or {},
                },
            )

            # Commit to DataLad if available
            if self.dataset:
                try:
                    self.dataset.save(
                        message=f"Add {artifact_type}: {artifact_source.name}",
                        path=[str(target_path), str(metadata_file)],
                    )
                except Exception as e:
                    self.logger.warning(f"Could not save to DataLad: {e}")

            self.logger.info(f"Saved artifact: {artifact_source.name} -> {target_path}")

        except Exception as e:
            self.logger.error(f"Failed to save artifact {artifact_path}: {e}")
            raise

    def finalize_conversion(self, status: str, final_metadata: dict[str, Any]):
        """
        Finalize the conversion session and create comprehensive summary.

        Args:
            status: Final status of the conversion (completed, failed, etc.)
            final_metadata: Final metadata dictionary for the conversion
        """
        self.session.end_time = time.time()
        self.session.status = status
        self.session.final_metadata = final_metadata

        # Record finalization
        self.record_provenance(
            source=ProvenanceSource.AUTO_EXTRACTED,
            agent="conversion_tracker",
            operation="session_finalize",
            input_data={"status": status},
            output_data={"final_metadata": final_metadata},
            confidence=1.0,
            metadata={"finalization_time": time.strftime("%Y-%m-%d %H:%M:%S")},
        )

        # Generate comprehensive conversion summary
        summary = self._generate_conversion_summary()

        # Save complete session data
        session_file = (
            self.conversion_repo_path / "provenance" / "conversion_session.json"
        )
        session_data = asdict(self.session)

        # Convert enums to strings for JSON serialization
        for record in session_data["provenance_records"]:
            if isinstance(record["source"], ProvenanceSource) or hasattr(
                record["source"], "value"
            ):
                record["source"] = record["source"].value

        session_file.write_text(json.dumps(session_data, indent=2, default=str))

        # Save conversion summary
        summary_file = self.conversion_repo_path / "CONVERSION_SUMMARY.md"
        summary_file.write_text(summary)

        # Update README with final status
        self._update_final_readme()

        # Final commit with descriptive message
        if self.dataset:
            try:
                self.dataset.save(
                    message=f"Finalize conversion {self.conversion_id} - Status: {status}",
                    path=[
                        str(session_file),
                        str(summary_file),
                        str(self.conversion_repo_path / "README.md"),
                    ],
                )

                # Tag successful conversions
                if status == "completed":
                    self._create_completion_tag()

            except Exception as e:
                self.logger.warning(f"Could not save final commit: {e}")

        self.logger.info(
            f"Finalized conversion {self.conversion_id} with status: {status}"
        )

    def _generate_conversion_summary(self) -> str:
        """Generate comprehensive human-readable conversion summary."""
        duration = (self.session.end_time or time.time()) - self.session.start_time

        # Analyze provenance records
        source_counts = {}
        agent_counts = {}
        operation_counts = {}

        for record in self.session.provenance_records:
            source = (
                record.source.value
                if hasattr(record.source, "value")
                else str(record.source)
            )
            source_counts[source] = source_counts.get(source, 0) + 1

            if record.agent:
                agent_counts[record.agent] = agent_counts.get(record.agent, 0) + 1

            operation_counts[record.operation] = (
                operation_counts.get(record.operation, 0) + 1
            )

        summary = f"""# Conversion Summary: {self.conversion_id}

## Overview
- **Status**: {self.session.status}
- **Duration**: {duration:.2f} seconds ({duration / 60:.1f} minutes)
- **Start Time**: {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.session.start_time))}
- **End Time**: {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.session.end_time or time.time()))}
- **Dataset Path**: {self.session.dataset_path}

## Provenance Summary
- **Total Operations**: {len(self.session.provenance_records)}
- **Pipeline State Updates**: {len([r for r in self.session.provenance_records if r.operation == "state_update"])}

### Data Sources
"""

        for source, count in sorted(source_counts.items()):
            summary += f"- **{source.replace('_', ' ').title()}**: {count} operations\n"

        summary += "\n### Agent Activity\n"
        for agent, count in sorted(agent_counts.items()):
            summary += f"- **{agent}**: {count} operations\n"

        summary += "\n### Operation Types\n"
        for operation, count in sorted(operation_counts.items()):
            summary += f"- **{operation}**: {count} times\n"

        # Add metadata summary
        if self.session.final_metadata:
            summary += f"""
## Final Metadata Summary
- **Fields Populated**: {len(self.session.final_metadata)}
- **Required NWB Fields**: {self._count_required_fields()}

### Key Metadata Fields
"""
            key_fields = [
                "identifier",
                "session_description",
                "experimenter",
                "lab",
                "institution",
            ]
            for field in key_fields:
                value = self.session.final_metadata.get(field, "Not provided")
                summary += f"- **{field}**: {value}\n"

        # Add file summary
        summary += f"""
## Generated Files
- **NWB File**: {self._get_nwb_file_info()}
- **Conversion Scripts**: {self._count_files("scripts")} files
- **Reports**: {self._count_files("reports")} files
- **Input Files**: {self._count_files("inputs")} files
- **Provenance Records**: {len(self.session.provenance_records)} records

## Repository Structure
```
{self._generate_tree_structure()}
```

## Confidence Analysis
"""

        # Analyze confidence levels
        confidence_records = [
            r for r in self.session.provenance_records if r.confidence is not None
        ]
        if confidence_records:
            avg_confidence = sum(r.confidence for r in confidence_records) / len(
                confidence_records
            )
            high_confidence = len(
                [r for r in confidence_records if r.confidence >= 0.8]
            )
            low_confidence = len([r for r in confidence_records if r.confidence < 0.5])

            summary += f"""- **Average Confidence**: {avg_confidence:.2f}
- **High Confidence Operations** (≥0.8): {high_confidence}
- **Low Confidence Operations** (<0.5): {low_confidence}
- **Total Confidence-Rated Operations**: {len(confidence_records)}
"""
        else:
            summary += "- No confidence ratings recorded\n"

        summary += f"""
## Reproducibility
This conversion can be reproduced using the saved conversion scripts and provenance information.
All agent decisions and data transformations are recorded with complete audit trails.

### DataLad Integration
- Repository path: `{self.conversion_repo_path}`
- Version control: Complete history maintained
- Data management: Large files handled via git-annex
- Reproducibility: All artifacts versioned and tracked

### Files for Reproduction
- Conversion session: `provenance/conversion_session.json`
- Pipeline state: `provenance/pipeline_state.json`
- Provenance log: `provenance/provenance_log.jsonl`
- Generated scripts: `scripts/` directory
"""

        return summary

    def _update_final_readme(self):
        """Update README with final conversion status."""
        readme_content = f"""# Conversion {self.conversion_id}

This DataLad repository contains the complete conversion process and outputs for conversion session {self.conversion_id}.

## Conversion Status: {self.session.status.upper()}

- **Started**: {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.session.start_time))}
- **Completed**: {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.session.end_time or time.time()))}
- **Duration**: {((self.session.end_time or time.time()) - self.session.start_time):.2f} seconds
- **Operations**: {len(self.session.provenance_records)} recorded

## Structure

- `inputs/`: Input data and metadata files ({self._count_files("inputs")} files)
- `outputs/`: Generated NWB files and conversion outputs ({self._count_files("outputs")} files)
- `scripts/`: Generated conversion scripts and code ({self._count_files("scripts")} files)
- `reports/`: Validation and evaluation reports ({self._count_files("reports")} files)
- `provenance/`: Detailed provenance tracking files ({self._count_files("provenance")} files)

## Key Files

- **Conversion Summary**: `CONVERSION_SUMMARY.md`
- **Complete Session Data**: `provenance/conversion_session.json`
- **Provenance Log**: `provenance/provenance_log.jsonl`
- **Pipeline State**: `provenance/pipeline_state.json`

## Provenance Tracking

This conversion was performed using the Agentic Neurodata Converter with complete provenance tracking:
- All decisions, transformations, and outputs are recorded
- Complete audit trails for reproducibility
- Source attribution for every metadata field
- Confidence levels for AI-generated content

## DataLad Integration

This repository uses DataLad for version control and data management:
- All files are properly versioned with git/git-annex
- Large data files are handled efficiently
- Complete history is maintained for reproducibility
- Repository can be cloned and shared easily

## Reproducibility

To reproduce this conversion:
1. Clone this DataLad repository
2. Review the conversion scripts in `scripts/`
3. Check the provenance records in `provenance/`
4. Use the recorded pipeline state and metadata
"""

        readme_path = self.conversion_repo_path / "README.md"
        readme_path.write_text(readme_content)

    def _create_completion_tag(self):
        """Create a git tag for successful conversion completion."""
        if not self.dataset:
            return

        try:
            import subprocess

            tag_name = f"conversion-{self.conversion_id}"
            tag_message = f"Completed conversion {self.conversion_id} at {time.strftime('%Y-%m-%d %H:%M:%S')}"

            subprocess.run(
                ["git", "tag", "-a", tag_name, "-m", tag_message],
                cwd=self.conversion_repo_path,
                check=True,
            )

            self.logger.info(f"Created completion tag: {tag_name}")

        except subprocess.CalledProcessError as e:
            self.logger.warning(f"Failed to create git tag: {e}")
        except Exception as e:
            self.logger.warning(f"Could not create completion tag: {e}")

    def _count_required_fields(self) -> int:
        """Count required NWB fields that are populated."""
        required_fields = [
            "identifier",
            "session_description",
            "session_start_time",
            "experimenter",
            "lab",
            "institution",
        ]
        return sum(
            1 for field in required_fields if field in self.session.final_metadata
        )

    def _get_nwb_file_info(self) -> str:
        """Get information about generated NWB file."""
        outputs_dir = self.conversion_repo_path / "outputs"
        nwb_files = list(outputs_dir.glob("*.nwb"))

        if nwb_files:
            nwb_file = nwb_files[0]
            size = nwb_file.stat().st_size
            return f"{nwb_file.name} ({size / (1024 * 1024):.1f} MB)"
        return "No NWB file generated"

    def _count_files(self, directory: str) -> int:
        """Count files in a directory."""
        dir_path = self.conversion_repo_path / directory
        if dir_path.exists():
            return len(
                [
                    f
                    for f in dir_path.iterdir()
                    if f.is_file() and not f.name.startswith(".")
                ]
            )
        return 0

    def _get_file_size(self, path: Path) -> int:
        """Get file or directory size in bytes."""
        if path.is_file():
            return path.stat().st_size
        elif path.is_dir():
            total_size = 0
            for item in path.rglob("*"):
                if item.is_file():
                    total_size += item.stat().st_size
            return total_size
        return 0

    def _generate_tree_structure(self) -> str:
        """Generate tree structure of the repository."""

        def _tree_recursive(
            path: Path, prefix: str = "", max_depth: int = 2, current_depth: int = 0
        ) -> str:
            if current_depth >= max_depth:
                return ""

            try:
                items = sorted(
                    [item for item in path.iterdir() if not item.name.startswith(".")],
                    key=lambda x: (x.is_file(), x.name),
                )
            except PermissionError:
                return f"{prefix}[Permission Denied]\n"

            tree_str = ""

            for i, item in enumerate(items):
                is_last = i == len(items) - 1
                current_prefix = "└── " if is_last else "├── "

                if item.is_file():
                    size = item.stat().st_size
                    size_str = (
                        f" ({size} bytes)"
                        if size < 1024
                        else f" ({size / 1024:.1f} KB)"
                    )
                    tree_str += f"{prefix}{current_prefix}{item.name}{size_str}\n"
                else:
                    tree_str += f"{prefix}{current_prefix}{item.name}/\n"

                    if item.is_dir() and current_depth < max_depth - 1:
                        next_prefix = prefix + ("    " if is_last else "│   ")
                        tree_str += _tree_recursive(
                            item, next_prefix, max_depth, current_depth + 1
                        )

            return tree_str

        return _tree_recursive(self.conversion_repo_path)

    def get_provenance_summary(self) -> dict[str, Any]:
        """
        Get a summary of provenance information for external use.

        Returns:
            Dictionary containing provenance summary statistics
        """
        source_counts = {}
        agent_counts = {}
        confidence_stats = []

        for record in self.session.provenance_records:
            source = (
                record.source.value
                if hasattr(record.source, "value")
                else str(record.source)
            )
            source_counts[source] = source_counts.get(source, 0) + 1

            if record.agent:
                agent_counts[record.agent] = agent_counts.get(record.agent, 0) + 1

            if record.confidence is not None:
                confidence_stats.append(record.confidence)

        return {
            "session_id": self.session.session_id,
            "status": self.session.status,
            "total_operations": len(self.session.provenance_records),
            "source_counts": source_counts,
            "agent_counts": agent_counts,
            "confidence_stats": {
                "count": len(confidence_stats),
                "average": (
                    sum(confidence_stats) / len(confidence_stats)
                    if confidence_stats
                    else None
                ),
                "min": min(confidence_stats) if confidence_stats else None,
                "max": max(confidence_stats) if confidence_stats else None,
            },
            "duration": (self.session.end_time or time.time())
            - self.session.start_time,
            "repository_path": str(self.conversion_repo_path),
        }
