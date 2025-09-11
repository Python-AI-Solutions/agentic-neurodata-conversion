"""Integration tests for conversion provenance tracking with data management."""

import json
from pathlib import Path
import tempfile

import pytest

# Import the actual components
try:
    from agentic_neurodata_conversion.data_management import (
        ConversionProvenanceTracker,
        DataLadRepositoryManager,
        ProvenanceSource,
        TestDatasetManager,
    )

    COMPONENTS_AVAILABLE = True
except ImportError:
    COMPONENTS_AVAILABLE = False

# Skip all tests if components are not implemented
pytestmark = pytest.mark.skipif(
    not COMPONENTS_AVAILABLE, reason="Data management components not implemented yet"
)


@pytest.mark.integration
class TestConversionProvenanceIntegration:
    """Integration tests for conversion provenance with data management infrastructure."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for integration testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_provenance_with_data_management_workflow(self, temp_workspace):
        """Test complete workflow integrating provenance tracking with data management."""

        # 1. Set up data management infrastructure
        repo_manager = DataLadRepositoryManager(str(temp_workspace))
        dataset_manager = TestDatasetManager(repo_manager)

        # 2. Create a test dataset
        test_data_dir = temp_workspace / "test_input_data"
        test_data_dir.mkdir()

        # Create some test files
        (test_data_dir / "recording.dat").write_text("binary data placeholder")
        (test_data_dir / "metadata.json").write_text('{"experiment": "test"}')
        (test_data_dir / "events.csv").write_text("timestamp,event\n1.0,start\n2.0,end")

        # Add test dataset to data management
        success = dataset_manager.add_test_dataset(
            dataset_name="integration_test_dataset",
            source_path=str(test_data_dir),
            description="Test dataset for integration testing",
            metadata={"format": "custom", "channels": 32},
        )
        assert success

        # 3. Initialize conversion provenance tracking
        conversion_outputs = temp_workspace / "conversion_outputs"
        conversion_outputs.mkdir()

        tracker = ConversionProvenanceTracker(
            conversion_id="integration_test_conversion",
            output_dir=str(conversion_outputs),
            dataset_path=str(test_data_dir),
        )

        # 4. Simulate conversion workflow with provenance tracking

        # Record dataset analysis
        tracker.record_provenance(
            source=ProvenanceSource.AUTO_EXTRACTED,
            agent="dataset_analyzer",
            operation="analyze_dataset_structure",
            input_data={"dataset_path": str(test_data_dir)},
            output_data={
                "files_found": 3,
                "formats_detected": ["dat", "json", "csv"],
                "estimated_channels": 32,
            },
            confidence=0.95,
            metadata={"analysis_method": "file_pattern_matching"},
        )

        # Update pipeline state
        tracker.update_pipeline_state(
            {
                "stage": "dataset_analysis_complete",
                "files_processed": 3,
                "metadata_extracted": True,
            }
        )

        # Record user input for missing metadata
        tracker.record_provenance(
            source=ProvenanceSource.USER_PROVIDED,
            agent="user",
            operation="provide_experimenter_info",
            input_data={"field": "experimenter"},
            output_data={"experimenter": "Dr. Integration Test"},
            confidence=1.0,
            metadata={"input_method": "manual_entry"},
        )

        # Record AI-generated session description
        tracker.record_provenance(
            source=ProvenanceSource.AI_GENERATED,
            agent="conversation_agent",
            operation="generate_session_description",
            input_data={
                "context": "electrophysiology recording with 32 channels",
                "experiment_type": "test",
            },
            output_data={
                "session_description": "Test electrophysiology recording session with 32 channels"
            },
            confidence=0.8,
            metadata={"model": "test_llm", "prompt_version": "v1.0"},
        )

        # Create and save conversion script
        conversion_script = """
# Auto-generated conversion script
import numpy as np
from neuroconv import NWBConverter

def convert_session(input_path, output_path):
    # Load data
    data = np.loadtxt(input_path / "recording.dat")

    # Create NWB file
    converter = NWBConverter()
    # ... conversion logic here ...

    return output_path / "converted.nwb"

if __name__ == "__main__":
    convert_session("input", "output")
"""

        script_file = temp_workspace / "generated_conversion_script.py"
        script_file.write_text(conversion_script)

        tracker.save_conversion_artifact(
            artifact_path=str(script_file),
            artifact_type="conversion_script",
            description="Auto-generated conversion script for integration test",
            metadata={"generator": "integration_test", "version": "1.0"},
        )

        # Save input metadata
        input_metadata = {
            "dataset_name": "integration_test_dataset",
            "experimenter": "Dr. Integration Test",
            "session_description": "Test electrophysiology recording session with 32 channels",
            "channels": 32,
            "sampling_rate": 30000,
            "session_start_time": "2024-01-01T10:00:00",
        }

        metadata_file = temp_workspace / "conversion_metadata.json"
        metadata_file.write_text(json.dumps(input_metadata, indent=2))

        tracker.save_conversion_artifact(
            artifact_path=str(metadata_file),
            artifact_type="metadata_file",
            description="Final metadata for NWB conversion",
            metadata={"source": "combined_user_ai_auto"},
        )

        # Update pipeline state for conversion completion
        tracker.update_pipeline_state(
            {
                "stage": "conversion_complete",
                "nwb_file_generated": True,
                "validation_passed": True,
            }
        )

        # Finalize conversion
        tracker.finalize_conversion("completed", input_metadata)

        # 5. Verify integration results

        # Check that conversion repository was created with proper structure
        conversion_repo = conversion_outputs / "conversion_integration_test_conversion"
        assert conversion_repo.exists()
        assert (conversion_repo / "inputs").exists()
        assert (conversion_repo / "outputs").exists()
        assert (conversion_repo / "scripts").exists()
        assert (conversion_repo / "reports").exists()
        assert (conversion_repo / "provenance").exists()

        # Check that artifacts were saved correctly
        assert (conversion_repo / "scripts" / "generated_conversion_script.py").exists()
        assert (conversion_repo / "inputs" / "conversion_metadata.json").exists()

        # Check that provenance was recorded properly
        session_file = conversion_repo / "provenance" / "conversion_session.json"
        assert session_file.exists()

        session_data = json.loads(session_file.read_text())
        assert session_data["session_id"] == "integration_test_conversion"
        assert session_data["status"] == "completed"
        assert len(session_data["provenance_records"]) >= 6  # Init + 5 operations

        # Check that summary was generated
        summary_file = conversion_repo / "CONVERSION_SUMMARY.md"
        assert summary_file.exists()

        summary_content = summary_file.read_text()
        assert "Dr. Integration Test" in summary_content
        assert "completed" in summary_content
        assert "32 channels" in summary_content

        # Check provenance log
        provenance_log = conversion_repo / "provenance" / "provenance_log.jsonl"
        assert provenance_log.exists()

        # Verify different provenance sources are recorded
        log_lines = provenance_log.read_text().strip().split("\n")
        sources_found = set()

        for line in log_lines:
            record = json.loads(line)
            sources_found.add(record["source"])

        assert "auto_extracted" in sources_found
        assert "user_provided" in sources_found
        assert "ai_generated" in sources_found

        # 6. Verify data management integration

        # Check that test dataset is still accessible
        available_datasets = dataset_manager.get_available_datasets()
        dataset_names = [d["name"] for d in available_datasets]
        assert "integration_test_dataset" in dataset_names

        # Check that we can get the dataset path
        dataset_path = dataset_manager.get_dataset_path("integration_test_dataset")
        assert dataset_path is not None
        assert dataset_path.exists()

        # Verify dataset metadata
        dataset_info = next(
            d for d in available_datasets if d["name"] == "integration_test_dataset"
        )
        assert dataset_info["description"] == "Test dataset for integration testing"
        assert dataset_info["custom_metadata"]["format"] == "custom"
        assert dataset_info["custom_metadata"]["channels"] == 32

    def test_provenance_summary_integration(self, temp_workspace):
        """Test provenance summary generation with realistic data."""

        conversion_outputs = temp_workspace / "conversion_outputs"
        conversion_outputs.mkdir()

        tracker = ConversionProvenanceTracker(
            conversion_id="summary_test_conversion",
            output_dir=str(conversion_outputs),
            dataset_path="/test/dataset/path",
        )

        # Add various types of provenance records
        operations = [
            {
                "source": ProvenanceSource.AUTO_EXTRACTED,
                "agent": "file_analyzer",
                "operation": "detect_format",
                "confidence": 0.95,
            },
            {
                "source": ProvenanceSource.USER_PROVIDED,
                "agent": "user",
                "operation": "provide_metadata",
                "confidence": 1.0,
            },
            {
                "source": ProvenanceSource.AI_GENERATED,
                "agent": "llm_agent",
                "operation": "generate_description",
                "confidence": 0.75,
            },
            {
                "source": ProvenanceSource.EXTERNAL_ENRICHED,
                "agent": "knowledge_graph",
                "operation": "enrich_metadata",
                "confidence": 0.85,
            },
        ]

        for i, op in enumerate(operations):
            tracker.record_provenance(
                source=op["source"],
                agent=op["agent"],
                operation=op["operation"],
                input_data={"step": i},
                output_data={"result": f"step_{i}_complete"},
                confidence=op["confidence"],
            )

        # Get provenance summary
        summary = tracker.get_provenance_summary()

        # Verify summary contains expected information
        assert summary["session_id"] == "summary_test_conversion"
        assert summary["total_operations"] == 5  # Init + 4 operations

        # Check source counts
        assert summary["source_counts"]["auto_extracted"] >= 1
        assert summary["source_counts"]["user_provided"] == 1
        assert summary["source_counts"]["ai_generated"] == 1
        assert summary["source_counts"]["external_enriched"] == 1

        # Check confidence statistics
        assert (
            summary["confidence_stats"]["count"] == 5
        )  # All operations have confidence
        assert (
            0.8 < summary["confidence_stats"]["average"] < 1.0
        )  # Should be reasonable average
        assert summary["confidence_stats"]["min"] == 0.75  # Lowest confidence
        assert summary["confidence_stats"]["max"] == 1.0  # Highest confidence

        # Check agent counts
        assert "file_analyzer" in summary["agent_counts"]
        assert "user" in summary["agent_counts"]
        assert "llm_agent" in summary["agent_counts"]
        assert "knowledge_graph" in summary["agent_counts"]
