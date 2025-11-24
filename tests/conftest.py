"""
Comprehensive pytest configuration and shared fixtures.

Provides reusable fixtures for:
- Mock services (LLM, file system, etc.)
- Sample data (NWB files, metadata, validation results)
- Test utilities and helpers
- Database and state setup/teardown
"""

import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from agentic_neurodata_conversion.models import (
    ConversionStatus,
    GlobalState,
    LogLevel,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)
from agentic_neurodata_conversion.services import LLMService

# ============================================================================
# Pytest Configuration
# ============================================================================
# Note: Markers are now defined in pyproject.toml only (no duplication)


# ============================================================================
# Session-Level Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def test_data_dir():
    """Create a temporary directory for test data."""
    temp_dir = tempfile.mkdtemp(prefix="nwb_test_data_")
    yield Path(temp_dir)
    # Cleanup after all tests
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def sample_nwb_files(test_data_dir):
    """Create sample NWB files for testing."""
    files = {}

    # Valid NWB file
    valid_nwb = test_data_dir / "valid_recording.nwb"
    valid_nwb.write_bytes(b"mock valid nwb content")
    files["valid"] = valid_nwb

    # Invalid NWB file
    invalid_nwb = test_data_dir / "invalid_recording.nwb"
    invalid_nwb.write_bytes(b"corrupted data")
    files["invalid"] = invalid_nwb

    # Large NWB file (simulated)
    large_nwb = test_data_dir / "large_recording.nwb"
    large_nwb.write_bytes(b"x" * (10 * 1024 * 1024))  # 10 MB
    files["large"] = large_nwb

    return files


@pytest.fixture(scope="session")
def sample_spikeglx_files(test_data_dir):
    """Create sample SpikeGLX files for testing."""
    spikeglx_dir = test_data_dir / "spikeglx"
    spikeglx_dir.mkdir(exist_ok=True)

    files = {}

    # Binary data file
    bin_file = spikeglx_dir / "recording_g0_t0.imec0.ap.bin"
    bin_file.write_bytes(b"mock spikeglx binary data" * 1000)
    files["bin"] = bin_file

    # Metadata file
    meta_file = spikeglx_dir / "recording_g0_t0.imec0.ap.meta"
    meta_content = """
    imSampRate=30000
    imDatPrb_type=0
    nSavedChans=385
    snsApLfSy=384,0,1
    """
    meta_file.write_text(meta_content)
    files["meta"] = meta_file

    return files


# ============================================================================
# Function-Level Fixtures
# ============================================================================


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a clean temporary directory for each test."""
    return tmp_path


@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service for testing."""
    service = Mock(spec=LLMService)

    # Default successful response
    service.generate_response = AsyncMock(return_value="Mock LLM response")
    service.is_available = Mock(return_value=True)
    service.get_model_name = Mock(return_value="mock-llm-model")

    return service


@pytest.fixture
def mock_llm_service_with_structured_response():
    """Create a mock LLM service that returns structured JSON."""
    service = Mock(spec=LLMService)

    default_response = json.dumps(
        {
            "format": "NWB",
            "confidence": 0.95,
            "metadata": {
                "session_description": "Test recording session",
                "experimenter": ["John Doe"],
            },
        }
    )

    service.generate_response = AsyncMock(return_value=default_response)
    service.is_available = Mock(return_value=True)

    return service


# ============================================================================
# Specialized LLM Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_llm_format_detector():
    """
    Create a mock LLM service specialized for format detection.

    This mock returns responses suitable for testing file format detection
    logic (SpikeGLX, NWB, Intan, etc.). It simulates the behavior of a real
    LLM service without making actual API calls.

    Returns:
        Mock: LLM service mock configured for format detection with:
            - generate_response: Returns "Format: NWB"
            - generate_structured_output: Returns format detection dict
            - is_available: Returns True
            - get_model_name: Returns "mock-format-detector"

    Example:
        def test_format_detection(mock_llm_format_detector):
            result = await mock_llm_format_detector.generate_structured_output(
                "Detect format of file.nwb"
            )
            assert result["detected_format"] == "NWB"
            assert result["confidence"] > 0.9

    See also:
        - mock_llm_quality_assessor: For quality/validation testing
        - mock_llm_metadata_parser: For metadata extraction testing
    """
    service = Mock(spec=LLMService)
    service.generate_response = AsyncMock(return_value="Format: NWB")
    service.generate_structured_output = AsyncMock(
        return_value={
            "detected_format": "NWB",
            "confidence": 0.95,
            "reasoning": "File has .nwb extension and valid HDF5 structure",
            "alternative_formats": [],
        }
    )
    service.is_available = Mock(return_value=True)
    service.get_model_name = Mock(return_value="mock-format-detector")
    return service


@pytest.fixture
def mock_llm_quality_assessor():
    """
    Create a mock LLM service specialized for quality and validation assessment.

    This mock returns quality assessment responses suitable for testing
    evaluation agents and validation logic.

    Returns:
        Mock: LLM service mock configured for quality assessment with:
            - generate_structured_output: Returns quality assessment dict
            - is_available: Returns True
            - get_model_name: Returns "mock-quality-assessor"

    Example:
        def test_quality_assessment(mock_llm_quality_assessor):
            result = await mock_llm_quality_assessor.generate_structured_output(
                "Assess quality of NWB file"
            )
            assert result["overall_score"] >= 0
            assert "assessment" in result

    See also:
        - mock_llm_format_detector: For format detection testing
        - mock_llm_corrector: For error correction testing
    """
    service = Mock(spec=LLMService)
    service.generate_structured_output = AsyncMock(
        return_value={
            "overall_score": 85,
            "grade": "B",
            "assessment": "Good quality NWB file with minor issues",
            "strengths": ["Valid HDF5 structure", "Required fields present"],
            "weaknesses": ["Missing recommended metadata"],
            "recommendations": ["Add experimenter metadata", "Include institution"],
        }
    )
    service.generate_response = AsyncMock(
        return_value="Quality assessment: The NWB file has good structure with minor metadata issues."
    )
    service.is_available = Mock(return_value=True)
    service.get_model_name = Mock(return_value="mock-quality-assessor")
    return service


@pytest.fixture
def mock_llm_metadata_parser():
    """
    Create a mock LLM service specialized for metadata parsing and inference.

    This mock returns metadata extraction responses suitable for testing
    metadata inference engines and intelligent parsers.

    Returns:
        Mock: LLM service mock configured for metadata parsing with:
            - generate_structured_output: Returns metadata dict
            - is_available: Returns True
            - get_model_name: Returns "mock-metadata-parser"

    Example:
        def test_metadata_parsing(mock_llm_metadata_parser):
            result = await mock_llm_metadata_parser.generate_structured_output(
                "Extract metadata from file"
            )
            assert "session_description" in result
            assert "experimenter" in result

    See also:
        - mock_llm_corrector: For metadata correction suggestions
        - sample_metadata: For pre-defined metadata samples
    """
    service = Mock(spec=LLMService)
    service.generate_structured_output = AsyncMock(
        return_value={
            "session_description": "Neural recording session from mouse V1",
            "experimenter": ["John Doe"],
            "institution": "Research Lab",
            "lab": "Neuroscience Lab",
            "session_start_time": "2023-06-15T10:30:00-05:00",
        }
    )
    service.generate_response = AsyncMock(
        return_value="Extracted metadata: Neural recording session from mouse V1, experimenter John Doe"
    )
    service.is_available = Mock(return_value=True)
    service.get_model_name = Mock(return_value="mock-metadata-parser")
    return service


@pytest.fixture
def mock_llm_corrector():
    """
    Create a mock LLM service specialized for error correction and suggestions.

    This mock returns correction suggestions suitable for testing smart
    autocorrect agents and error recovery logic.

    Returns:
        Mock: LLM service mock configured for error correction with:
            - generate_response: Returns correction suggestion text
            - generate_structured_output: Returns structured corrections
            - is_available: Returns True
            - get_model_name: Returns "mock-corrector"

    Example:
        def test_error_correction(mock_llm_corrector):
            result = await mock_llm_corrector.generate_structured_output(
                "Suggest fixes for validation errors"
            )
            assert "corrections" in result
            assert len(result["corrections"]) > 0

    See also:
        - mock_llm_quality_assessor: For identifying issues
        - mock_llm_metadata_parser: For metadata suggestions
    """
    service = Mock(spec=LLMService)
    service.generate_response = AsyncMock(
        return_value="Suggested fix: Add session_description field with minimum 10 characters"
    )
    service.generate_structured_output = AsyncMock(
        return_value={
            "corrections": [
                {
                    "field": "session_description",
                    "issue": "Too short",
                    "current_value": "a",
                    "suggested_value": "Neural recording session from mouse V1",
                    "fix": "Add detailed description",
                }
            ],
            "auto_fixable": True,
            "confidence": 0.9,
        }
    )
    service.is_available = Mock(return_value=True)
    service.get_model_name = Mock(return_value="mock-corrector")
    return service


@pytest.fixture
def mock_llm_conversational():
    """
    Create a mock LLM service specialized for conversational interactions.

    This mock returns conversational responses suitable for testing
    conversation agents and user interaction handlers.

    Returns:
        Mock: LLM service mock configured for conversations with:
            - generate_response: Returns friendly conversational text
            - is_available: Returns True
            - get_model_name: Returns "mock-conversational"

    Example:
        def test_user_interaction(mock_llm_conversational):
            response = await mock_llm_conversational.generate_response(
                "User asked for help"
            )
            assert isinstance(response, str)
            assert len(response) > 0

    See also:
        - mock_llm_service: For basic non-specialized responses
    """
    service = Mock(spec=LLMService)
    service.generate_response = AsyncMock(return_value="I understand. Let me help you with that.")
    service.generate_structured_output = AsyncMock(
        return_value={"explanation": "The error occurred because of missing metadata fields."}
    )
    service.is_available = Mock(return_value=True)
    service.get_model_name = Mock(return_value="mock-conversational")
    return service


@pytest.fixture
def mock_llm_api_only():
    """
    Create a MockLLMService that only mocks the API calls, not the service logic.

    This fixture uses the real MockLLMService class which implements the full
    LLM service interface but returns mock responses without making actual API calls.
    This allows testing the actual service logic while avoiding API costs.

    Returns:
        MockLLMService: Real service class with mocked API responses

    Example:
        @pytest.mark.asyncio
        async def test_with_real_service(mock_llm_api_only):
            # Tests real service logic
            response = await mock_llm_api_only.generate_response("test prompt")
            assert isinstance(response, str)
            assert len(response) > 0

    See also:
        - mock_llm_service: Fully mocked version (deprecated for unit tests)
        - MockLLMService: The actual mock service class
    """
    from agentic_neurodata_conversion.services.llm_service import MockLLMService

    return MockLLMService()


# ============================================================================
# Real Agent Instance Fixtures
# ============================================================================


@pytest.fixture
def real_conversational_handler(mock_llm_service):
    """
    Create a real ConversationalHandler instance with MockLLMService.

    This fixture provides a fully functional ConversationalHandler that uses
    real helper agents (MetadataRequestStrategy, MetadataParser, ContextManager)
    but mocked LLM service, allowing tests to validate actual interaction logic
    without making real API calls.

    Use this instead of mocking the conversational_handler or its helper agents
    to test real conversation flow and metadata handling logic.

    Returns:
        ConversationalHandler: Real instance with:
            - Real MetadataRequestStrategy
            - Real MetadataParser (with MockLLMService)
            - Real ContextManager
            - MockLLMService for LLM calls

    Example:
        def test_conversation_flow(real_conversational_handler, global_state):
            result = await real_conversational_handler.process_user_response(
                "The experimenter is Dr. Smith",
                global_state
            )
            assert result["type"] == "metadata_provided"
            assert "experimenter" in result["extracted_metadata"]

    See also:
        - mock_llm_service: Used internally by this fixture
        - global_state: Use with this fixture for state management
    """
    from agentic_neurodata_conversion.agents.utils.conversational_handler import ConversationalHandler

    return ConversationalHandler(llm_service=mock_llm_service)


# ============================================================================
# Infrastructure Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_mcp_server():
    """
    Create a mock MCP server for inter-agent communication testing.

    NOTE: This fixture is deprecated for unit tests. Use real_mcp_server instead.
    This mock simulates the MCP (Multi-agent Communication Protocol) server
    used for agent-to-agent messaging without requiring actual server setup.

    Returns:
        Mock: MCP server mock with:
            - send_message: AsyncMock returning success response
            - receive_message: AsyncMock returning sample message
            - register_agent: Mock for agent registration

    Example:
        def test_agent_communication(mock_mcp_server):
            from agentic_neurodata_conversion.models import MCPMessage
            message = MCPMessage(
                sender="agent_a",
                receiver="agent_b",
                message_type="request",
                payload={"data": "test"}
            )
            response = await mock_mcp_server.send_message(message)
            assert response.success

    See also:
        - real_mcp_server: Real MCP server for better test coverage
        - conversation_agent: Agent fixture using MCP server
        - sample_mcp_message: Sample MCP message fixture
    """
    from agentic_neurodata_conversion.models import MCPMessage, MCPResponse
    from agentic_neurodata_conversion.services import MCPServer

    server = Mock(spec=MCPServer)
    server.send_message = AsyncMock(return_value=MCPResponse(success=True, reply_to="test_message_id", result={}))
    server.receive_message = AsyncMock(
        return_value=MCPMessage(target_agent="test_agent", action="test_action", context={})
    )
    server.register_agent = Mock()
    return server


@pytest.fixture
def real_mcp_server():
    """
    Create a real MCP server for inter-agent communication testing.

    This fixture creates an actual MCPServer instance that can process real
    messages in-memory, allowing tests to verify actual message passing logic
    instead of mocking it away.

    Returns:
        MCPServer: Real MCP server instance for in-memory message passing

    Example:
        @pytest.mark.asyncio
        async def test_agent_communication(real_mcp_server):
            from agentic_neurodata_conversion.models import MCPMessage

            # Register agents
            real_mcp_server.register_agent("agent_a", mock_handler)
            real_mcp_server.register_agent("agent_b", mock_handler)

            # Send real message
            message = MCPMessage(
                target_agent="agent_b",
                action="test_action",
                context={"data": "test"}
            )
            response = await real_mcp_server.send_message(message)
            assert response.success

    See also:
        - mock_mcp_server: Fully mocked version (deprecated for unit tests)
        - conversation_agent_real: Agent using real MCP server
    """
    from agentic_neurodata_conversion.services import MCPServer

    # Create real MCP server instance
    server = MCPServer()
    return server


@pytest.fixture
def global_state():
    """Create a fresh GlobalState instance for each test."""
    state = GlobalState()
    # Note: GlobalState doesn't have session_id, uses status instead of conversion_status
    state.status = ConversionStatus.IDLE
    return state


@pytest.fixture
def global_state_with_logs():
    """Create GlobalState with sample logs."""
    state = GlobalState()
    # Note: GlobalState doesn't have session_id field

    # Add various log levels
    state.add_log(LogLevel.DEBUG, "Debug message for testing")
    state.add_log(LogLevel.INFO, "System initialized successfully")
    state.add_log(LogLevel.INFO, "File upload received: test_file.nwb")
    state.add_log(LogLevel.INFO, "Detecting format with LLM")
    state.add_log(LogLevel.WARNING, "Missing recommended field: experimenter")
    state.add_log(LogLevel.ERROR, "Validation failed: critical error")

    return state


@pytest.fixture
def sample_metadata():
    """Create sample metadata dictionary."""
    return {
        "session_description": "Test recording session from mouse V1",
        "experimenter": ["John Doe", "Jane Smith"],
        "institution": "Test University",
        "lab": "Neuroscience Research Lab",
        "session_start_time": "2023-06-15T10:30:00-05:00",
        "identifier": "test-recording-001",
        "subject": {
            "species": "Mus musculus",
            "age": "P90D",
            "sex": "M",
            "subject_id": "mouse_001",
            "description": "Wild-type C57BL/6J mouse",
        },
        "devices": {
            "NeuropixelsProbe": {
                "description": "Neuropixels 1.0 probe",
                "manufacturer": "IMEC",
            }
        },
    }


@pytest.fixture
def sample_validation_result():
    """Create sample validation result."""
    return ValidationResult(
        is_valid=False,
        issues=[
            ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                message="Missing required field: session_description",
                location="/",
                check_name="check_session_description",
            ),
            ValidationIssue(
                severity=ValidationSeverity.WARNING,
                message="Missing recommended field: experimenter",
                location="/",
                check_name="check_experimenter",
            ),
            ValidationIssue(
                severity=ValidationSeverity.INFO,
                message="Consider adding institution information",
                location="/",
                check_name="check_institution",
            ),
        ],
        summary={
            "critical": 1,
            "error": 0,
            "warning": 1,
            "info": 1,
        },
        inspector_version="0.5.0",
    )


@pytest.fixture
def sample_file_info():
    """Create sample file information."""
    return {
        "original_name": "test_recording.nwb",
        "size": 52428800,  # 50 MB
        "format": "NWB",
        "path": "/uploads/test_recording.nwb",
        "upload_timestamp": datetime.now().isoformat(),
        "checksum": "abc123def456",
    }


@pytest.fixture
def sample_workflow_trace():
    """Create sample workflow trace."""
    return {
        "summary": "Complete NWB conversion and validation workflow",
        "technologies": ["Python", "NWB Inspector", "NeuroConv"],
        "steps": [
            {
                "stage": "Initialization",
                "description": "System initialized and ready",
                "timestamp": "2023-06-15T10:00:00Z",
                "duration_ms": 150,
            },
            {
                "stage": "Upload",
                "description": "File uploaded successfully: test_recording.nwb",
                "timestamp": "2023-06-15T10:00:05Z",
                "duration_ms": 5000,
            },
            {
                "stage": "Format Detection",
                "description": "Detected format as NWB with 95% confidence",
                "timestamp": "2023-06-15T10:00:10Z",
                "duration_ms": 2500,
            },
            {
                "stage": "Validation",
                "description": "Validation completed with 2 issues found",
                "timestamp": "2023-06-15T10:00:30Z",
                "duration_ms": 18000,
            },
        ],
        "detailed_logs_sequential": [
            {
                "timestamp": "2023-06-15T10:00:00Z",
                "level": "INFO",
                "message": "System initialized",
                "stage": "initialization",
                "stage_display": "Initialization",
                "stage_icon": "🚀",
            },
            {
                "timestamp": "2023-06-15T10:00:05Z",
                "level": "INFO",
                "message": "File upload received: test_recording.nwb",
                "stage": "upload",
                "stage_display": "Upload",
                "stage_icon": "📤",
            },
        ],
        "stage_options": [
            {"value": "initialization", "label": "🚀 Initialization"},
            {"value": "upload", "label": "📤 Upload"},
            {"value": "validation", "label": "✅ Validation"},
        ],
    }


@pytest.fixture
def sample_issues():
    """Create sample validation issues."""
    return [
        {
            "severity": "critical",
            "message": "Missing required field: session_description",
            "location": "/",
            "category": "metadata",
            "fix_suggestion": "Add a session_description field to the NWBFile",
        },
        {
            "severity": "critical",
            "message": "Missing required field: session_start_time",
            "location": "/",
            "category": "metadata",
            "fix_suggestion": "Add session_start_time in ISO 8601 format",
        },
        {
            "severity": "warning",
            "message": "Missing recommended field: experimenter",
            "location": "/",
            "category": "metadata",
            "fix_suggestion": "Add experimenter as a list of names",
        },
        {
            "severity": "info",
            "message": "Consider adding institution information",
            "location": "/",
            "category": "best_practice",
            "fix_suggestion": "Add institution field for better metadata",
        },
    ]


# ============================================================================
# Utility Fixtures and Helpers
# ============================================================================


@pytest.fixture
def create_test_nwb_file():
    """Factory fixture to create test NWB files with custom content."""

    def _create_file(tmp_path, name="test.nwb", content=b"mock nwb data"):
        file_path = tmp_path / name
        file_path.write_bytes(content)
        return file_path

    return _create_file


@pytest.fixture
def create_test_metadata():
    """Factory fixture to create test metadata with custom fields."""

    def _create_metadata(**kwargs):
        base_metadata = {
            "session_description": "Test session",
            "experimenter": ["Test User"],
        }
        base_metadata.update(kwargs)
        return base_metadata

    return _create_metadata


@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run for testing external command execution."""
    with pytest.mock.patch("subprocess.run") as mock_run:
        # Default successful command execution
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Command executed successfully",
            stderr="",
        )
        yield mock_run


# ============================================================================
# Async Test Utilities
# ============================================================================


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Performance Testing Utilities
# ============================================================================


@pytest.fixture
def performance_timer():
    """Utility to measure test execution time."""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()

        @property
        def elapsed_ms(self):
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time) * 1000
            return None

    return Timer()


# ============================================================================
# Cleanup Hooks
# ============================================================================


@pytest.fixture(autouse=True)
def cleanup_test_artifacts(request, tmp_path):
    """Automatically cleanup test artifacts after each test."""
    yield

    # Cleanup any .nwb files created during tests
    for nwb_file in tmp_path.glob("**/*.nwb"):
        try:
            nwb_file.unlink()
        except Exception:
            pass


# ============================================================================
# Markers Configuration
# ============================================================================


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on their names and location.

    Auto-marking strategy:
    - Directory-based: /unit/, /integration/, /property_based/ -> primary scope markers
    - Keyword-based: slow, e2e, api, websocket -> characteristic markers
    """
    for item in items:
        nodeid = item.nodeid.lower()

        # Directory-based marking (PRIMARY CATEGORIES)
        if "/unit/" in nodeid:
            item.add_marker(pytest.mark.unit)
        if "/integration/" in nodeid:
            item.add_marker(pytest.mark.integration)
        if "/property_based/" in nodeid:
            item.add_marker(pytest.mark.property)

        # Keyword-based marking (SECONDARY ATTRIBUTES)
        if "slow" in nodeid:
            item.add_marker(pytest.mark.slow)
        if "e2e" in nodeid or "end_to_end" in nodeid:
            item.add_marker(pytest.mark.e2e)
        if "api" in nodeid or "/test_api" in nodeid:
            item.add_marker(pytest.mark.api)
        if "websocket" in nodeid or "/test_ws" in nodeid:
            item.add_marker(pytest.mark.websocket)
