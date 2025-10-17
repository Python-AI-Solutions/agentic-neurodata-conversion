"""
Comprehensive tests for ConversionAgent - Tasks 5.2, 5.3, and 5.4.

Task 5.2: Metadata Preparation
Task 5.3: LLM Error Message Generation
Task 5.4: Conversion Message Handler
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from agentic_neurodata_conversion.agents.conversion_agent import ConversionAgent
from agentic_neurodata_conversion.config import AgentConfig
from agentic_neurodata_conversion.models.mcp_message import MCPMessage
from agentic_neurodata_conversion.models.session_context import (
    DatasetInfo,
    MetadataExtractionResult,
    SessionContext,
    WorkflowStage,
)


@pytest.fixture
def conversion_agent(tmp_path: Path) -> ConversionAgent:
    """Create ConversionAgent instance for testing."""
    config = AgentConfig(
        agent_name="test-conversion-agent",
        agent_type="conversion",
        agent_port=8002,
        mcp_server_url="http://localhost:3000",
        llm_provider="anthropic",
        llm_api_key="test-key",
        llm_model="claude-3-5-sonnet-20241022",
        temperature=0.3,
        max_tokens=8192,
    )
    return ConversionAgent(config)


# ==================== Task 5.2: Metadata Preparation Tests ====================


@pytest.mark.unit
def test_prepare_metadata_all_fields(conversion_agent: ConversionAgent) -> None:
    """Test prepare metadata with all fields present."""
    metadata = {
        "subject_id": "Mouse001",
        "species": "Mus musculus",
        "age": "P56",
        "sex": "M",
        "subject_description": "Test mouse",
        "session_description": "Test session",
        "identifier": "test-id-001",
        "session_start_time": "2024-01-15T12:00:00Z",
        "experimenter": "Dr. Smith",
        "lab": "Neuroscience Lab",
        "institution": "Test University",
        "device_name": "OpenEphys",
        "device_manufacturer": "Open Ephys",
        "device_description": "Acquisition Board",
    }

    result = conversion_agent._prepare_metadata(metadata)

    assert "Subject" in result
    assert result["Subject"]["subject_id"] == "Mouse001"
    assert result["Subject"]["species"] == "Mus musculus"
    assert result["Subject"]["age"] == "P56"
    assert result["Subject"]["sex"] == "M"
    assert result["Subject"]["description"] == "Test mouse"

    assert "NWBFile" in result
    assert result["NWBFile"]["session_description"] == "Test session"
    assert result["NWBFile"]["identifier"] == "test-id-001"
    assert result["NWBFile"]["session_start_time"] == "2024-01-15T12:00:00Z"
    assert result["NWBFile"]["experimenter"] == ["Dr. Smith"]  # Converted to list
    assert result["NWBFile"]["lab"] == "Neuroscience Lab"
    assert result["NWBFile"]["institution"] == "Test University"

    assert "Ecephys" in result
    assert "Device" in result["Ecephys"]
    assert len(result["Ecephys"]["Device"]) == 1
    assert result["Ecephys"]["Device"][0]["name"] == "OpenEphys"
    assert result["Ecephys"]["Device"][0]["manufacturer"] == "Open Ephys"
    assert result["Ecephys"]["Device"][0]["description"] == "Acquisition Board"


@pytest.mark.unit
def test_prepare_metadata_minimal(conversion_agent: ConversionAgent) -> None:
    """Test prepare metadata with minimal fields."""
    metadata = {}

    result = conversion_agent._prepare_metadata(metadata)

    # Should have NWBFile with defaults
    assert "NWBFile" in result
    assert result["NWBFile"]["session_description"] == "OpenEphys recording session"
    assert result["NWBFile"]["identifier"] == "UNSPECIFIED"
    assert "session_start_time" in result["NWBFile"]  # Should have a default

    # Should not have Subject if no subject fields provided
    assert "Subject" not in result


@pytest.mark.unit
def test_prepare_metadata_experimenter_list(conversion_agent: ConversionAgent) -> None:
    """Test experimenter converted to list."""
    metadata = {"experimenter": "Single Person"}
    result = conversion_agent._prepare_metadata(metadata)
    assert result["NWBFile"]["experimenter"] == ["Single Person"]

    metadata2 = {"experimenter": ["Person 1", "Person 2"]}
    result2 = conversion_agent._prepare_metadata(metadata2)
    assert result2["NWBFile"]["experimenter"] == ["Person 1", "Person 2"]


@pytest.mark.unit
def test_prepare_metadata_default_session_start_time(
    conversion_agent: ConversionAgent,
) -> None:
    """Test applies defaults for missing session_start_time."""
    metadata = {}

    result = conversion_agent._prepare_metadata(metadata)

    assert "session_start_time" in result["NWBFile"]
    # Should be ISO format with Z
    assert result["NWBFile"]["session_start_time"].endswith("Z")


@pytest.mark.unit
def test_prepare_metadata_device_defaults(conversion_agent: ConversionAgent) -> None:
    """Test Device metadata with defaults."""
    metadata = {"device_name": "TestDevice"}

    result = conversion_agent._prepare_metadata(metadata)

    assert "Ecephys" in result
    assert result["Ecephys"]["Device"][0]["name"] == "TestDevice"
    assert result["Ecephys"]["Device"][0]["description"] == "Recording device"


# ==================== Task 5.3: LLM Error Message Generation Tests ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_error_message_basic(conversion_agent: ConversionAgent) -> None:
    """Test generate error message for conversion failure."""
    # Mock the LLM call
    mock_response = "**Error**: Test error\n**Remediation**: 1. Step 1\n2. Step 2"
    conversion_agent.call_llm = AsyncMock(return_value=mock_response)

    error = ValueError("Test conversion error")
    dataset_path = "/path/to/dataset"
    metadata = {"subject_id": "test"}

    result = await conversion_agent._generate_error_message(
        error, dataset_path, metadata
    )

    assert "Error" in result
    assert "Remediation" in result
    assert len(result) < 2000  # Should be concise


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_error_message_includes_context(
    conversion_agent: ConversionAgent,
) -> None:
    """Test error message includes dataset context in prompt."""
    # Capture the prompt sent to LLM
    captured_prompt = None

    async def mock_call_llm(prompt, system_message=None):
        nonlocal captured_prompt
        captured_prompt = prompt
        return "**Error**: Test\n**Remediation**: Fix it"

    conversion_agent.call_llm = mock_call_llm

    error = ValueError("Test error")
    dataset_path = "/test/path"
    metadata = {"subject_id": "SUB001", "session_description": "Test session"}

    await conversion_agent._generate_error_message(error, dataset_path, metadata)

    assert captured_prompt is not None
    assert "Test error" in captured_prompt
    assert "/test/path" in captured_prompt
    assert "SUB001" in captured_prompt


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_error_message_llm_fallback(
    conversion_agent: ConversionAgent,
) -> None:
    """Test fallback when LLM call fails."""
    # Mock LLM to raise an exception
    conversion_agent.call_llm = AsyncMock(side_effect=Exception("LLM failed"))

    error = ValueError("Test error")
    dataset_path = "/test/path"
    metadata = {}

    result = await conversion_agent._generate_error_message(
        error, dataset_path, metadata
    )

    # Should have fallback message
    assert "Error" in result
    assert "Remediation" in result
    assert "ValueError" in result
    assert "/test/path" in result


# ==================== Task 5.4: Conversion Message Handler Tests ====================


@pytest.mark.asyncio
@pytest.mark.unit
async def test_handle_message_routes_correctly(
    conversion_agent: ConversionAgent,
) -> None:
    """Test handle_message routes to _convert_dataset."""
    # Mock _convert_dataset
    conversion_agent._convert_dataset = AsyncMock(return_value={"status": "success"})

    message = MCPMessage(
        message_id="msg-001",
        source_agent="test",
        target_agent="conversion_agent",
        message_type="agent_execute",
        session_id="test-001",
        payload={"action": "convert_dataset"},
    )

    result = await conversion_agent.handle_message(message)

    assert result["status"] == "success"
    conversion_agent._convert_dataset.assert_called_once_with("test-001")


@pytest.mark.asyncio
@pytest.mark.unit
async def test_handle_message_unknown_action(conversion_agent: ConversionAgent) -> None:
    """Test handle_message with unknown action."""
    message = MCPMessage(
        message_id="msg-002",
        source_agent="test",
        target_agent="conversion_agent",
        message_type="agent_execute",
        session_id="test-001",
        payload={"action": "unknown_action"},
    )

    result = await conversion_agent.handle_message(message)

    assert result["status"] == "error"
    assert "Unknown action" in result["message"]


@pytest.mark.asyncio
@pytest.mark.unit
@patch(
    "agentic_neurodata_conversion.agents.conversion_agent.OpenEphysRecordingInterface"
)
async def test_convert_dataset_full_workflow(
    mock_interface_class: MagicMock,
    conversion_agent: ConversionAgent,
) -> None:
    """Test successful conversion updates session context correctly."""
    # Mock session context
    session_context = SessionContext(
        session_id="test-001",
        workflow_stage=WorkflowStage.COLLECTING_METADATA,
        dataset_info=DatasetInfo(
            dataset_path="/test/path",
            format="openephys",
            total_size_bytes=1000,
            file_count=5,
        ),
        metadata=MetadataExtractionResult(
            subject_id="Mouse001",
            species="Mus musculus",
        ),
    )

    # Mock get_session_context
    conversion_agent.get_session_context = AsyncMock(return_value=session_context)

    # Mock update_session_context
    conversion_agent.update_session_context = AsyncMock(return_value={})

    # Mock OpenEphys interface
    mock_interface = Mock()
    mock_interface.run_conversion = Mock()
    mock_interface_class.return_value = mock_interface

    # Mock HTTP client for agent handoff
    conversion_agent.http_client.post = AsyncMock()

    # Call _convert_dataset
    result = await conversion_agent._convert_dataset("test-001")

    assert result["status"] == "success"
    assert "nwb_file_path" in result

    # Verify workflow stage was updated to CONVERTING
    calls = conversion_agent.update_session_context.call_args_list
    assert any(
        call[0][1].get("workflow_stage") == WorkflowStage.CONVERTING for call in calls
    )

    # Verify workflow stage was updated to EVALUATING
    assert any(
        call[0][1].get("workflow_stage") == WorkflowStage.EVALUATING for call in calls
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_convert_dataset_missing_dataset_info(
    conversion_agent: ConversionAgent,
) -> None:
    """Test conversion fails gracefully when dataset info missing."""
    session_context = SessionContext(
        session_id="test-001",
        workflow_stage=WorkflowStage.INITIALIZED,
        dataset_info=None,  # Missing!
    )

    conversion_agent.get_session_context = AsyncMock(return_value=session_context)

    result = await conversion_agent._convert_dataset("test-001")

    assert result["status"] == "error"
    assert "No dataset information" in result["message"]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_convert_dataset_missing_metadata(
    conversion_agent: ConversionAgent,
) -> None:
    """Test conversion fails gracefully when metadata missing."""
    session_context = SessionContext(
        session_id="test-001",
        workflow_stage=WorkflowStage.INITIALIZED,
        dataset_info=DatasetInfo(
            dataset_path="/test",
            format="openephys",
            total_size_bytes=1000,
            file_count=5,
        ),
        metadata=None,  # Missing!
    )

    conversion_agent.get_session_context = AsyncMock(return_value=session_context)

    result = await conversion_agent._convert_dataset("test-001")

    assert result["status"] == "error"
    assert "No metadata found" in result["message"]


@pytest.mark.asyncio
@pytest.mark.unit
@patch(
    "agentic_neurodata_conversion.agents.conversion_agent.OpenEphysRecordingInterface"
)
async def test_convert_dataset_error_handling(
    mock_interface_class: MagicMock,
    conversion_agent: ConversionAgent,
) -> None:
    """Test failed conversion captures error details."""
    # Mock session context
    session_context = SessionContext(
        session_id="test-001",
        workflow_stage=WorkflowStage.COLLECTING_METADATA,
        dataset_info=DatasetInfo(
            dataset_path="/test/path",
            format="openephys",
            total_size_bytes=1000,
            file_count=5,
        ),
        metadata=MetadataExtractionResult(subject_id="Mouse001"),
    )

    conversion_agent.get_session_context = AsyncMock(return_value=session_context)
    conversion_agent.update_session_context = AsyncMock(return_value={})

    # Mock interface to raise error
    mock_interface_class.side_effect = ValueError("Invalid dataset")

    # Mock error message generation
    conversion_agent._generate_error_message = AsyncMock(
        return_value="Test error message with remediation steps"
    )

    result = await conversion_agent._convert_dataset("test-001")

    assert result["status"] == "error"
    assert "error_details" in result
    assert result["error_type"] == "ValueError"

    # Verify error message was generated
    conversion_agent._generate_error_message.assert_called_once()

    # Verify session was updated to FAILED with clarification
    calls = conversion_agent.update_session_context.call_args_list
    final_update = calls[-1][0][1]
    assert final_update["workflow_stage"] == WorkflowStage.FAILED
    assert final_update["requires_user_clarification"] is True
    assert "clarification_prompt" in final_update


@pytest.mark.asyncio
@pytest.mark.unit
@patch(
    "agentic_neurodata_conversion.agents.conversion_agent.OpenEphysRecordingInterface"
)
async def test_convert_dataset_triggers_evaluation_agent(
    mock_interface_class: MagicMock,
    conversion_agent: ConversionAgent,
) -> None:
    """Test successful conversion triggers evaluation agent."""
    # Mock session context
    session_context = SessionContext(
        session_id="test-001",
        workflow_stage=WorkflowStage.COLLECTING_METADATA,
        dataset_info=DatasetInfo(
            dataset_path="/test/path",
            format="openephys",
            total_size_bytes=1000,
            file_count=5,
        ),
        metadata=MetadataExtractionResult(subject_id="Mouse001"),
    )

    conversion_agent.get_session_context = AsyncMock(return_value=session_context)
    conversion_agent.update_session_context = AsyncMock(return_value={})

    # Mock interface
    mock_interface = Mock()
    mock_interface.run_conversion = Mock()
    mock_interface_class.return_value = mock_interface

    # Mock HTTP client
    mock_post = AsyncMock()
    conversion_agent.http_client.post = mock_post

    result = await conversion_agent._convert_dataset("test-001")

    assert result["status"] == "success"

    # Verify evaluation agent was triggered
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert "internal/route_message" in call_args[0][0]
    assert call_args[1]["json"]["target_agent"] == "evaluation_agent"
    assert call_args[1]["json"]["action"] == "validate_nwb"
