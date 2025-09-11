"""Tests for conversion provenance tracking functionality."""

import pytest
import json
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

# Import the actual components that should be implemented
try:
    from agentic_neurodata_conversion.data_management.conversion_provenance import (
        ConversionProvenanceTracker,
        ProvenanceRecord,
        ConversionSession,
        ProvenanceSource
    )
    COMPONENTS_AVAILABLE = True
except ImportError:
    # These should fail until implemented
    ConversionProvenanceTracker = None
    ProvenanceRecord = None
    ConversionSession = None
    ProvenanceSource = None
    COMPONENTS_AVAILABLE = False

# Skip all tests if components are not implemented
pytestmark = pytest.mark.skipif(
    not COMPONENTS_AVAILABLE, 
    reason="Conversion provenance components not implemented yet"
)


@pytest.mark.unit
class TestProvenanceRecord:
    """Test the ProvenanceRecord dataclass functionality."""
    
    def test_provenance_record_creation(self):
        """Test that ProvenanceRecord can be created with required fields."""
        record = ProvenanceRecord(
            timestamp=time.time(),
            source=ProvenanceSource.USER_PROVIDED,
            agent="test_agent",
            operation="test_operation",
            input_data={"key": "value"},
            output_data={"result": "success"}
        )
        
        assert record.timestamp > 0
        assert record.source == ProvenanceSource.USER_PROVIDED
        assert record.agent == "test_agent"
        assert record.operation == "test_operation"
        assert record.input_data == {"key": "value"}
        assert record.output_data == {"result": "success"}
        assert record.confidence is None
        assert record.metadata == {}
    
    def test_provenance_record_with_optional_fields(self):
        """Test ProvenanceRecord with confidence and metadata."""
        metadata = {"context": "test"}
        record = ProvenanceRecord(
            timestamp=time.time(),
            source=ProvenanceSource.AI_GENERATED,
            agent="ai_agent",
            operation="generate_metadata",
            input_data={"prompt": "test"},
            output_data={"metadata": "generated"},
            confidence=0.85,
            metadata=metadata
        )
        
        assert record.confidence == 0.85
        assert record.metadata == metadata
    
    def test_provenance_source_enum(self):
        """Test that ProvenanceSource enum has expected values."""
        assert ProvenanceSource.USER_PROVIDED.value == "user_provided"
        assert ProvenanceSource.AUTO_EXTRACTED.value == "auto_extracted"
        assert ProvenanceSource.AI_GENERATED.value == "ai_generated"
        assert ProvenanceSource.EXTERNAL_ENRICHED.value == "external_enriched"
        assert ProvenanceSource.DOMAIN_KNOWLEDGE.value == "domain_knowledge"


@pytest.mark.unit
class TestConversionSession:
    """Test the ConversionSession dataclass functionality."""
    
    def test_conversion_session_creation(self):
        """Test that ConversionSession can be created with required fields."""
        session = ConversionSession(
            session_id="test_session_001",
            start_time=time.time(),
            end_time=None,
            dataset_path="/path/to/dataset",
            output_path="/path/to/output",
            status="started",
            provenance_records=[],
            final_metadata={},
            pipeline_state={}
        )
        
        assert session.session_id == "test_session_001"
        assert session.start_time > 0
        assert session.end_time is None
        assert session.dataset_path == "/path/to/dataset"
        assert session.output_path == "/path/to/output"
        assert session.status == "started"
        assert session.provenance_records == []
        assert session.final_metadata == {}
        assert session.pipeline_state == {}
    
    def test_conversion_session_post_init(self):
        """Test that ConversionSession properly initializes None fields."""
        session = ConversionSession(
            session_id="test_session_002",
            start_time=time.time(),
            end_time=None,
            dataset_path="/path/to/dataset",
            output_path="/path/to/output",
            status="started",
            provenance_records=None,
            final_metadata=None,
            pipeline_state=None
        )
        
        assert session.provenance_records == []
        assert session.final_metadata == {}
        assert session.pipeline_state == {}


@pytest.mark.unit
class TestConversionProvenanceTracker:
    """Test the ConversionProvenanceTracker functionality."""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def mock_datalad(self):
        """Mock DataLad functionality for testing without DataLad dependency."""
        with patch('agentic_neurodata_conversion.data_management.conversion_provenance.DATALAD_AVAILABLE', False):
            yield
    
    def test_tracker_initialization(self, temp_output_dir, mock_datalad):
        """Test that ConversionProvenanceTracker initializes properly."""
        conversion_id = "test_conversion_001"
        dataset_path = "/path/to/test/dataset"
        
        tracker = ConversionProvenanceTracker(
            conversion_id=conversion_id,
            output_dir=str(temp_output_dir),
            dataset_path=dataset_path
        )
        
        assert tracker.conversion_id == conversion_id
        assert tracker.output_dir == temp_output_dir
        assert tracker.conversion_repo_path == temp_output_dir / f"conversion_{conversion_id}"
        assert tracker.session.session_id == conversion_id
        assert tracker.session.dataset_path == dataset_path
        assert tracker.session.status == "started"
        assert len(tracker.session.provenance_records) == 1  # Initialization record
    
    def test_repository_structure_creation(self, temp_output_dir, mock_datalad):
        """Test that proper directory structure is created."""
        conversion_id = "test_conversion_002"
        
        tracker = ConversionProvenanceTracker(
            conversion_id=conversion_id,
            output_dir=str(temp_output_dir)
        )
        
        repo_path = tracker.conversion_repo_path
        
        # Check that all required directories exist
        assert (repo_path / 'inputs').exists()
        assert (repo_path / 'outputs').exists()
        assert (repo_path / 'scripts').exists()
        assert (repo_path / 'reports').exists()
        assert (repo_path / 'provenance').exists()
        
        # Check that README and .gitattributes are created
        assert (repo_path / 'README.md').exists()
        assert (repo_path / '.gitattributes').exists()
    
    def test_record_provenance(self, temp_output_dir, mock_datalad):
        """Test recording provenance entries."""
        tracker = ConversionProvenanceTracker(
            conversion_id="test_conversion_003",
            output_dir=str(temp_output_dir)
        )
        
        # Record a test provenance entry
        tracker.record_provenance(
            source=ProvenanceSource.USER_PROVIDED,
            agent="test_user",
            operation="provide_metadata",
            input_data={"field": "experimenter"},
            output_data={"field": "experimenter", "value": "Dr. Test"},
            confidence=1.0,
            metadata={"source": "manual_input"}
        )
        
        # Check that provenance was recorded
        assert len(tracker.session.provenance_records) == 2  # Init + new record
        
        latest_record = tracker.session.provenance_records[-1]
        assert latest_record.source == ProvenanceSource.USER_PROVIDED
        assert latest_record.agent == "test_user"
        assert latest_record.operation == "provide_metadata"
        assert latest_record.confidence == 1.0
        
        # Check that provenance file was created
        provenance_files = list((tracker.conversion_repo_path / 'provenance').glob('record_*.json'))
        assert len(provenance_files) == 2  # Init + new record
        
        # Check provenance log exists
        provenance_log = tracker.conversion_repo_path / 'provenance' / 'provenance_log.jsonl'
        assert provenance_log.exists()
    
    def test_update_pipeline_state(self, temp_output_dir, mock_datalad):
        """Test updating pipeline state with provenance tracking."""
        tracker = ConversionProvenanceTracker(
            conversion_id="test_conversion_004",
            output_dir=str(temp_output_dir)
        )
        
        # Update pipeline state
        state_updates = {
            "current_step": "metadata_extraction",
            "files_processed": 5,
            "errors_encountered": 0
        }
        
        tracker.update_pipeline_state(state_updates)
        
        # Check that state was updated
        assert tracker.session.pipeline_state["current_step"] == "metadata_extraction"
        assert tracker.session.pipeline_state["files_processed"] == 5
        assert tracker.session.pipeline_state["errors_encountered"] == 0
        
        # Check that state update was recorded in provenance
        state_update_records = [
            r for r in tracker.session.provenance_records 
            if r.operation == "state_update"
        ]
        assert len(state_update_records) == 1
        
        # Check that state file was created
        state_file = tracker.conversion_repo_path / 'provenance' / 'pipeline_state.json'
        assert state_file.exists()
        
        state_data = json.loads(state_file.read_text())
        assert state_data['current_state'] == tracker.session.pipeline_state
    
    def test_save_conversion_artifact(self, temp_output_dir, mock_datalad):
        """Test saving conversion artifacts with provenance."""
        tracker = ConversionProvenanceTracker(
            conversion_id="test_conversion_005",
            output_dir=str(temp_output_dir)
        )
        
        # Create a test artifact file
        test_artifact = temp_output_dir / "test_script.py"
        test_artifact.write_text("# Test conversion script\nprint('Hello, World!')")
        
        # Save the artifact
        tracker.save_conversion_artifact(
            artifact_path=str(test_artifact),
            artifact_type="conversion_script",
            description="Test conversion script",
            metadata={"language": "python", "version": "1.0"}
        )
        
        # Check that artifact was copied to correct location
        saved_artifact = tracker.conversion_repo_path / 'scripts' / 'test_script.py'
        assert saved_artifact.exists()
        assert saved_artifact.read_text() == test_artifact.read_text()
        
        # Check that metadata file was created
        metadata_file = tracker.conversion_repo_path / 'scripts' / 'test_script.py.metadata.json'
        assert metadata_file.exists()
        
        metadata = json.loads(metadata_file.read_text())
        assert metadata['type'] == 'conversion_script'
        assert metadata['description'] == 'Test conversion script'
        assert metadata['custom_metadata']['language'] == 'python'
        
        # Check that artifact saving was recorded in provenance
        artifact_records = [
            r for r in tracker.session.provenance_records 
            if r.operation == "save_artifact"
        ]
        assert len(artifact_records) == 1
    
    def test_finalize_conversion(self, temp_output_dir, mock_datalad):
        """Test conversion finalization with summary generation."""
        tracker = ConversionProvenanceTracker(
            conversion_id="test_conversion_006",
            output_dir=str(temp_output_dir)
        )
        
        # Add some test provenance records
        tracker.record_provenance(
            source=ProvenanceSource.AUTO_EXTRACTED,
            agent="file_analyzer",
            operation="extract_metadata",
            input_data={"file": "test.dat"},
            output_data={"format": "binary", "size": 1024},
            confidence=0.9
        )
        
        # Finalize the conversion
        final_metadata = {
            "identifier": "test_session_001",
            "session_description": "Test conversion session",
            "experimenter": "Dr. Test"
        }
        
        tracker.finalize_conversion("completed", final_metadata)
        
        # Check that session was finalized
        assert tracker.session.status == "completed"
        assert tracker.session.end_time is not None
        assert tracker.session.final_metadata == final_metadata
        
        # Check that finalization was recorded in provenance
        finalize_records = [
            r for r in tracker.session.provenance_records 
            if r.operation == "session_finalize"
        ]
        assert len(finalize_records) == 1
        
        # Check that session file was created
        session_file = tracker.conversion_repo_path / 'provenance' / 'conversion_session.json'
        assert session_file.exists()
        
        session_data = json.loads(session_file.read_text())
        assert session_data['session_id'] == tracker.conversion_id
        assert session_data['status'] == "completed"
        
        # Check that summary was created
        summary_file = tracker.conversion_repo_path / 'CONVERSION_SUMMARY.md'
        assert summary_file.exists()
        
        summary_content = summary_file.read_text()
        assert "Conversion Summary" in summary_content
        assert "completed" in summary_content
        assert "Dr. Test" in summary_content
    
    def test_get_provenance_summary(self, temp_output_dir, mock_datalad):
        """Test getting provenance summary statistics."""
        tracker = ConversionProvenanceTracker(
            conversion_id="test_conversion_007",
            output_dir=str(temp_output_dir)
        )
        
        # Add various provenance records
        tracker.record_provenance(
            source=ProvenanceSource.USER_PROVIDED,
            agent="user",
            operation="input_metadata",
            input_data={},
            output_data={},
            confidence=1.0
        )
        
        tracker.record_provenance(
            source=ProvenanceSource.AI_GENERATED,
            agent="ai_agent",
            operation="generate_description",
            input_data={},
            output_data={},
            confidence=0.7
        )
        
        summary = tracker.get_provenance_summary()
        
        assert summary['session_id'] == "test_conversion_007"
        assert summary['status'] == "started"
        assert summary['total_operations'] == 3  # Init + 2 new records
        assert 'user_provided' in summary['source_counts']
        assert 'ai_generated' in summary['source_counts']
        assert summary['confidence_stats']['count'] == 3  # Init (1.0) + user (1.0) + AI (0.7)
        assert abs(summary['confidence_stats']['average'] - 0.9) < 0.01  # (1.0 + 1.0 + 0.7) / 3 ≈ 0.9
    
    def test_artifact_type_mapping(self, temp_output_dir, mock_datalad):
        """Test that different artifact types are saved to correct directories."""
        tracker = ConversionProvenanceTracker(
            conversion_id="test_conversion_008",
            output_dir=str(temp_output_dir)
        )
        
        # Create test files for different artifact types
        test_files = {
            "test.nwb": "nwb_file",
            "convert.py": "conversion_script", 
            "validation.html": "validation_report",
            "metadata.json": "metadata_file"
        }
        
        expected_dirs = {
            "nwb_file": "outputs",
            "conversion_script": "scripts",
            "validation_report": "reports", 
            "metadata_file": "inputs"
        }
        
        for filename, artifact_type in test_files.items():
            # Create test file
            test_file = temp_output_dir / filename
            test_file.write_text(f"Test content for {filename}")
            
            # Save artifact
            tracker.save_conversion_artifact(
                artifact_path=str(test_file),
                artifact_type=artifact_type,
                description=f"Test {artifact_type}"
            )
            
            # Check it was saved to correct directory
            expected_dir = expected_dirs[artifact_type]
            saved_file = tracker.conversion_repo_path / expected_dir / filename
            assert saved_file.exists()
            assert saved_file.read_text() == f"Test content for {filename}"


@pytest.mark.integration
class TestConversionProvenanceIntegration:
    """Integration tests for conversion provenance tracking."""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary directory for test outputs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    def test_complete_conversion_workflow(self, temp_output_dir):
        """Test a complete conversion workflow with provenance tracking."""
        conversion_id = "integration_test_001"
        dataset_path = "/path/to/test/dataset"
        
        # Initialize tracker
        tracker = ConversionProvenanceTracker(
            conversion_id=conversion_id,
            output_dir=str(temp_output_dir),
            dataset_path=dataset_path
        )
        
        # Simulate conversion workflow
        
        # 1. User provides initial metadata
        tracker.record_provenance(
            source=ProvenanceSource.USER_PROVIDED,
            agent="user",
            operation="provide_experimenter",
            input_data={"field": "experimenter"},
            output_data={"field": "experimenter", "value": "Dr. Smith"},
            confidence=1.0
        )
        
        # 2. Update pipeline state
        tracker.update_pipeline_state({
            "step": "file_analysis",
            "files_found": 10
        })
        
        # 3. AI generates session description
        tracker.record_provenance(
            source=ProvenanceSource.AI_GENERATED,
            agent="conversation_agent",
            operation="generate_session_description",
            input_data={"context": "electrophysiology recording"},
            output_data={"session_description": "Extracellular recording from mouse V1"},
            confidence=0.8
        )
        
        # 4. Save conversion script
        script_content = """
# Generated conversion script
from neuroconv import NWBConverter

def convert_session():
    converter = NWBConverter()
    # ... conversion logic
    pass
"""
        script_file = temp_output_dir / "conversion_script.py"
        script_file.write_text(script_content)
        
        tracker.save_conversion_artifact(
            artifact_path=str(script_file),
            artifact_type="conversion_script",
            description="Auto-generated conversion script"
        )
        
        # 5. Update pipeline state again
        tracker.update_pipeline_state({
            "step": "conversion_complete",
            "nwb_file_created": True
        })
        
        # 6. Finalize conversion
        final_metadata = {
            "identifier": "mouse_v1_001",
            "session_description": "Extracellular recording from mouse V1",
            "experimenter": "Dr. Smith",
            "lab": "Vision Lab",
            "institution": "Test University"
        }
        
        tracker.finalize_conversion("completed", final_metadata)
        
        # Verify complete workflow
        assert tracker.session.status == "completed"
        assert len(tracker.session.provenance_records) >= 6  # Init + 5 operations
        
        # Check all files were created
        repo_path = tracker.conversion_repo_path
        assert (repo_path / 'README.md').exists()
        assert (repo_path / 'CONVERSION_SUMMARY.md').exists()
        assert (repo_path / 'scripts' / 'conversion_script.py').exists()
        assert (repo_path / 'provenance' / 'conversion_session.json').exists()
        assert (repo_path / 'provenance' / 'pipeline_state.json').exists()
        
        # Verify summary contains expected information
        summary_content = (repo_path / 'CONVERSION_SUMMARY.md').read_text()
        assert "Dr. Smith" in summary_content
        assert "completed" in summary_content
        assert "mouse_v1_001" in summary_content
        
        # Verify provenance summary
        summary = tracker.get_provenance_summary()
        assert summary['status'] == 'completed'
        assert 'user_provided' in summary['source_counts']
        assert 'ai_generated' in summary['source_counts']
        assert summary['confidence_stats']['count'] >= 1