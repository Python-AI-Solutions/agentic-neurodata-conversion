"""
Unit tests for Pydantic data models.

Tests cover:
- SessionContext model validation
- WorkflowStage enum values
- AgentHistoryEntry creation and validation
- DatasetInfo model with all fields
- MetadataExtractionResult with confidence scores
- ConversionResults model
- ValidationIssue and ValidationResults models
- Datetime serialization to ISO format
- MCPMessage model with all message types
- API request/response models
"""

from datetime import datetime

from pydantic import ValidationError
import pytest

from agentic_neurodata_conversion.models.api_models import (
    SessionClarifyRequest,
    SessionClarifyResponse,
    SessionInitializeRequest,
    SessionInitializeResponse,
    SessionResultResponse,
    SessionStatusResponse,
)
from agentic_neurodata_conversion.models.mcp_message import (
    MCPMessage,
    MessageType,
)
from agentic_neurodata_conversion.models.session_context import (
    AgentHistoryEntry,
    ConversionResults,
    DatasetInfo,
    MetadataExtractionResult,
    SessionContext,
    ValidationIssue,
    ValidationResults,
    WorkflowStage,
)


class TestWorkflowStage:
    """Test WorkflowStage enum."""

    def test_workflow_stage_values(self) -> None:
        """Test all workflow stage enum values are defined."""
        assert WorkflowStage.INITIALIZED == "initialized"
        assert WorkflowStage.COLLECTING_METADATA == "collecting_metadata"
        assert WorkflowStage.CONVERTING == "converting"
        assert WorkflowStage.EVALUATING == "evaluating"
        assert WorkflowStage.COMPLETED == "completed"
        assert WorkflowStage.FAILED == "failed"


class TestAgentHistoryEntry:
    """Test AgentHistoryEntry model."""

    def test_agent_history_entry_creation(self) -> None:
        """Test creating an agent history entry."""
        now = datetime.utcnow()
        entry = AgentHistoryEntry(
            agent_name="conversation_agent",
            started_at=now,
            completed_at=None,
            status="in_progress",
            error_message=None,
            stack_trace=None,
        )
        assert entry.agent_name == "conversation_agent"
        assert entry.started_at == now
        assert entry.completed_at is None
        assert entry.status == "in_progress"

    def test_agent_history_entry_with_error(self) -> None:
        """Test agent history entry with error details."""
        now = datetime.utcnow()
        entry = AgentHistoryEntry(
            agent_name="conversion_agent",
            started_at=now,
            completed_at=now,
            status="failed",
            error_message="Conversion failed",
            stack_trace="Traceback...",
        )
        assert entry.status == "failed"
        assert entry.error_message == "Conversion failed"
        assert entry.stack_trace == "Traceback..."


class TestDatasetInfo:
    """Test DatasetInfo model."""

    def test_dataset_info_all_fields(self) -> None:
        """Test dataset info with all fields populated."""
        info = DatasetInfo(
            dataset_path="/path/to/dataset",
            format="openephys",
            total_size_bytes=1024000,
            file_count=50,
            channel_count=4,
            sampling_rate_hz=30000.0,
            duration_seconds=120.5,
            has_metadata_files=True,
            metadata_files=["README.md", "notes.md"],
        )
        assert info.dataset_path == "/path/to/dataset"
        assert info.format == "openephys"
        assert info.total_size_bytes == 1024000
        assert info.file_count == 50
        assert info.channel_count == 4
        assert info.sampling_rate_hz == 30000.0
        assert info.duration_seconds == 120.5
        assert info.has_metadata_files is True
        assert len(info.metadata_files) == 2

    def test_dataset_info_minimal(self) -> None:
        """Test dataset info with only required fields."""
        info = DatasetInfo(
            dataset_path="/path/to/dataset",
            format="openephys",
            total_size_bytes=1024000,
            file_count=50,
        )
        assert info.channel_count is None
        assert info.sampling_rate_hz is None
        assert info.duration_seconds is None
        assert info.has_metadata_files is False
        assert info.metadata_files == []


class TestMetadataExtractionResult:
    """Test MetadataExtractionResult model."""

    def test_metadata_extraction_all_fields(self) -> None:
        """Test metadata extraction with all fields."""
        metadata = MetadataExtractionResult(
            subject_id="mouse_001",
            species="Mus musculus",
            age="P90",
            sex="M",
            session_start_time="2025-01-15T10:00:00",
            experimenter="Dr. Smith",
            device_name="OpenEphys Acquisition Board",
            manufacturer="Open Ephys",
            recording_location="CA1",
            description="Recording session for experiment X",
            extraction_confidence={
                "subject_id": "high",
                "species": "default",
                "age": "medium",
            },
            llm_extraction_log="Extracted subject_id from README...",
        )
        assert metadata.subject_id == "mouse_001"
        assert metadata.species == "Mus musculus"
        assert metadata.extraction_confidence["subject_id"] == "high"
        assert metadata.llm_extraction_log is not None

    def test_metadata_extraction_empty(self) -> None:
        """Test metadata extraction with no fields."""
        metadata = MetadataExtractionResult()
        assert metadata.subject_id is None
        assert metadata.species is None
        assert metadata.extraction_confidence == {}
        assert metadata.llm_extraction_log is None


class TestConversionResults:
    """Test ConversionResults model."""

    def test_conversion_results_success(self) -> None:
        """Test conversion results for successful conversion."""
        results = ConversionResults(
            nwb_file_path="/output/session.nwb",
            conversion_duration_seconds=45.2,
            conversion_warnings=["Warning: Low sampling rate"],
            conversion_errors=[],
            conversion_log="Conversion started...",
        )
        assert results.nwb_file_path == "/output/session.nwb"
        assert results.conversion_duration_seconds == 45.2
        assert len(results.conversion_warnings) == 1
        assert len(results.conversion_errors) == 0

    def test_conversion_results_failure(self) -> None:
        """Test conversion results for failed conversion."""
        results = ConversionResults(
            nwb_file_path=None,
            conversion_duration_seconds=None,
            conversion_warnings=[],
            conversion_errors=["Error: Invalid format"],
            conversion_log=None,
        )
        assert results.nwb_file_path is None
        assert len(results.conversion_errors) == 1


class TestValidationIssue:
    """Test ValidationIssue model."""

    def test_validation_issue_creation(self) -> None:
        """Test creating a validation issue."""
        issue = ValidationIssue(
            severity="critical",
            message="Missing required field",
            location="/NWBFile/session_description",
            check_name="check_session_description",
        )
        assert issue.severity == "critical"
        assert issue.message == "Missing required field"
        assert issue.location == "/NWBFile/session_description"
        assert issue.check_name == "check_session_description"


class TestValidationResults:
    """Test ValidationResults model."""

    def test_validation_results_passed(self) -> None:
        """Test validation results for passed validation."""
        results = ValidationResults(
            overall_status="passed",
            issue_count={"critical": 0, "warning": 0, "info": 0},
            issues=[],
            metadata_completeness_score=1.0,
            best_practices_score=0.95,
            validation_report_path="/reports/session_validation.json",
            llm_validation_summary="All checks passed.",
        )
        assert results.overall_status == "passed"
        assert results.issue_count["critical"] == 0
        assert results.metadata_completeness_score == 1.0

    def test_validation_results_with_warnings(self) -> None:
        """Test validation results with warnings."""
        issue = ValidationIssue(
            severity="warning",
            message="Missing optional field",
            location=None,
            check_name="check_optional_field",
        )
        results = ValidationResults(
            overall_status="passed_with_warnings",
            issue_count={"critical": 0, "warning": 1, "info": 0},
            issues=[issue],
            metadata_completeness_score=0.8,
            best_practices_score=0.7,
        )
        assert results.overall_status == "passed_with_warnings"
        assert len(results.issues) == 1
        assert results.issues[0].severity == "warning"


class TestSessionContext:
    """Test SessionContext model."""

    def test_session_context_creation(self) -> None:
        """Test creating a session context."""
        session = SessionContext(
            session_id="550e8400-e29b-41d4-a716-446655440000",
            workflow_stage=WorkflowStage.INITIALIZED,
        )
        assert session.session_id == "550e8400-e29b-41d4-a716-446655440000"
        assert session.workflow_stage == WorkflowStage.INITIALIZED
        assert session.created_at is not None
        assert session.last_updated is not None
        assert session.current_agent is None
        assert len(session.agent_history) == 0

    def test_session_context_with_dataset_info(self) -> None:
        """Test session context with dataset info."""
        dataset_info = DatasetInfo(
            dataset_path="/data/openephys",
            format="openephys",
            total_size_bytes=1024000,
            file_count=50,
        )
        session = SessionContext(
            session_id="test-session",
            dataset_info=dataset_info,
        )
        assert session.dataset_info is not None
        assert session.dataset_info.format == "openephys"

    def test_session_context_datetime_serialization(self) -> None:
        """Test datetime fields serialize to ISO format."""
        session = SessionContext(
            session_id="test-session",
        )
        data = session.model_dump(mode="json")
        # Check that datetime is serialized as string
        assert isinstance(data["created_at"], str)
        assert isinstance(data["last_updated"], str)
        # Verify ISO format
        datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))


class TestMessageType:
    """Test MessageType enum."""

    def test_message_type_values(self) -> None:
        """Test all message type enum values are defined."""
        assert MessageType.AGENT_REGISTER == "agent_register"
        assert MessageType.AGENT_EXECUTE == "agent_execute"
        assert MessageType.AGENT_RESPONSE == "agent_response"
        assert MessageType.CONTEXT_UPDATE == "context_update"
        assert MessageType.ERROR == "error"
        assert MessageType.HEALTH_CHECK == "health_check"
        assert MessageType.HEALTH_RESPONSE == "health_response"


class TestMCPMessage:
    """Test MCPMessage model."""

    def test_mcp_message_creation(self) -> None:
        """Test creating an MCP message."""
        message = MCPMessage(
            message_id="msg-001",
            source_agent="mcp_server",
            target_agent="conversation_agent",
            session_id="test-session",
            message_type=MessageType.AGENT_EXECUTE,
            payload={"task": "initialize_session"},
        )
        assert message.message_id == "msg-001"
        assert message.source_agent == "mcp_server"
        assert message.target_agent == "conversation_agent"
        assert message.message_type == MessageType.AGENT_EXECUTE
        assert message.payload["task"] == "initialize_session"

    def test_mcp_message_datetime_serialization(self) -> None:
        """Test MCP message datetime serialization."""
        message = MCPMessage(
            message_id="msg-001",
            source_agent="test",
            target_agent="test",
            message_type=MessageType.HEALTH_CHECK,
        )
        data = message.model_dump(mode="json")
        assert isinstance(data["timestamp"], str)


class TestAPIModels:
    """Test API request/response models."""

    def test_session_initialize_request(self) -> None:
        """Test session initialize request."""
        request = SessionInitializeRequest(dataset_path="/path/to/dataset")
        assert request.dataset_path == "/path/to/dataset"

    def test_session_initialize_request_validation(self) -> None:
        """Test session initialize request requires dataset_path."""
        with pytest.raises(ValidationError):
            SessionInitializeRequest()  # type: ignore

    def test_session_initialize_response(self) -> None:
        """Test session initialize response."""
        response = SessionInitializeResponse(
            session_id="test-session",
            message="Session initialized",
            workflow_stage="initialized",
        )
        assert response.session_id == "test-session"
        assert response.message == "Session initialized"

    def test_session_status_response(self) -> None:
        """Test session status response."""
        response = SessionStatusResponse(
            session_id="test-session",
            workflow_stage="converting",
            progress_percentage=50,
            status_message="Converting dataset...",
            current_agent="conversion_agent",
            requires_clarification=False,
        )
        assert response.session_id == "test-session"
        assert response.progress_percentage == 50
        assert response.current_agent == "conversion_agent"

    def test_session_clarify_request(self) -> None:
        """Test session clarify request."""
        request = SessionClarifyRequest(
            user_input="Use species: Mus musculus",
            updated_metadata={"species": "Mus musculus"},
        )
        assert request.user_input == "Use species: Mus musculus"
        assert request.updated_metadata is not None

    def test_session_clarify_response(self) -> None:
        """Test session clarify response."""
        response = SessionClarifyResponse(
            message="Clarification received",
            workflow_stage="converting",
        )
        assert response.message == "Clarification received"

    def test_session_result_response(self) -> None:
        """Test session result response."""
        response = SessionResultResponse(
            session_id="test-session",
            nwb_file_path="/output/session.nwb",
            validation_report_path="/reports/validation.json",
            overall_status="passed",
            llm_validation_summary="Conversion successful",
            validation_issues=[],
        )
        assert response.session_id == "test-session"
        assert response.nwb_file_path == "/output/session.nwb"
        assert response.overall_status == "passed"
