"""
Shared fixtures for agent unit tests.

This conftest.py provides agent-specific fixtures that are automatically
available to all tests in the agents/ directory. These fixtures inherit
from the root conftest.py fixtures (test scripts/conftest.py).

Fixture inheritance:
    tests in agents/ can access:
    - All fixtures from test scripts/conftest.py (root)
    - All fixtures from this file (agents/conftest.py)
    - Local fixtures defined in individual test files
"""
import pytest
from unittest.mock import Mock, AsyncMock
from pathlib import Path

from agents import (
    ConversationAgent,
    ConversionAgent,
    EvaluationAgent,
)
from agents.conversational_handler import ConversationalHandler
from models import GlobalState, ConversionStatus, ConversationPhase, MCPMessage
from services import MCPServer


# ============================================================================
# Agent Instance Fixtures
# ============================================================================


@pytest.fixture
def conversation_agent(mock_mcp_server, mock_llm_conversational):
    """
    Create ConversationAgent with mocked dependencies for testing.

    Args:
        mock_mcp_server: Mock MCP server from root conftest.py
        mock_llm_conversational: Mock LLM for conversations from root conftest.py

    Returns:
        ConversationAgent: Agent instance with mocked dependencies

    Example:
        def test_agent(conversation_agent):
            response = await conversation_agent.handle_user_input("hello")
            assert response is not None
    """
    return ConversationAgent(
        mcp_server=mock_mcp_server,
        llm_service=mock_llm_conversational
    )


@pytest.fixture
def conversion_agent(mock_mcp_server, mock_llm_format_detector):
    """
    Create ConversionAgent with mocked dependencies for testing.

    Args:
        mock_mcp_server: Mock MCP server from root conftest.py
        mock_llm_format_detector: Mock LLM for format detection from root conftest.py

    Returns:
        ConversionAgent: Agent instance with mocked dependencies

    Example:
        def test_conversion(conversion_agent, tmp_path):
            result = await conversion_agent.detect_format(str(tmp_path / "test.nwb"))
            assert result["format"] == "NWB"
    """
    return ConversionAgent(
        mcp_server=mock_mcp_server,
        llm_service=mock_llm_format_detector
    )


@pytest.fixture
def evaluation_agent(mock_llm_quality_assessor):
    """
    Create EvaluationAgent with mocked dependencies for testing.

    Args:
        mock_llm_quality_assessor: Mock LLM for quality assessment from root conftest.py

    Returns:
        EvaluationAgent: Agent instance with mocked dependencies

    Example:
        def test_evaluation(evaluation_agent):
            result = await evaluation_agent.assess_quality("/test/file.nwb")
            assert "overall_score" in result
    """
    return EvaluationAgent(
        llm_service=mock_llm_quality_assessor
    )


@pytest.fixture
def conversational_handler(mock_llm_conversational):
    """
    Create ConversationalHandler for testing user interactions.

    Args:
        mock_llm_conversational: Mock LLM for conversations from root conftest.py

    Returns:
        ConversationalHandler: Handler instance with mocked LLM

    Example:
        def test_handler(conversational_handler):
            response = await conversational_handler.process_input("help")
            assert isinstance(response, str)
    """
    return ConversationalHandler(llm_service=mock_llm_conversational)


# ============================================================================
# Agent State Fixtures
# ============================================================================


@pytest.fixture
def agent_state():
    """
    Create fresh GlobalState initialized for agent testing.

    Returns:
        GlobalState: Fresh state with IDLE status and INITIAL phase

    Example:
        def test_state(agent_state):
            assert agent_state.status == ConversionStatus.IDLE
            agent_state.status = ConversionStatus.PROCESSING
    """
    state = GlobalState(status=ConversionStatus.IDLE)
    state.conversation_phase = ConversationPhase.INITIAL
    return state


@pytest.fixture
def agent_state_with_file(agent_state, tmp_path):
    """
    Create GlobalState with uploaded file path for testing.

    Args:
        agent_state: Fresh agent state
        tmp_path: Pytest's temporary directory

    Returns:
        GlobalState: State with uploaded_file_path set

    Example:
        def test_with_file(agent_state_with_file):
            assert agent_state_with_file.uploaded_file_path is not None
            assert Path(agent_state_with_file.uploaded_file_path).exists()
    """
    test_file = tmp_path / "test_recording.nwb"
    test_file.write_bytes(b"mock nwb data" * 100)
    agent_state.uploaded_file_path = str(test_file)
    return agent_state


@pytest.fixture
def agent_state_with_logs(agent_state):
    """
    Create GlobalState with sample log entries for testing.

    Args:
        agent_state: Fresh agent state

    Returns:
        GlobalState: State with sample log entries

    Example:
        def test_logs(agent_state_with_logs):
            logs = agent_state_with_logs.logs
            assert len(logs) > 0
    """
    agent_state.add_log("INFO", "Agent initialized")
    agent_state.add_log("INFO", "Processing request")
    agent_state.add_log("WARNING", "Metadata missing")
    return agent_state


# ============================================================================
# Agent Test Helpers
# ============================================================================


@pytest.fixture
def sample_mcp_message():
    """
    Create sample MCP message for agent communication testing.

    Returns:
        MCPMessage: Sample message for inter-agent communication

    Example:
        def test_mcp(conversation_agent, sample_mcp_message):
            result = await conversation_agent.handle_message(sample_mcp_message)
            assert result.success
    """
    return MCPMessage(
        sender="conversation_agent",
        receiver="conversion_agent",
        message_type="convert_file",
        payload={"file_path": "/test/file.nwb"}
    )


@pytest.fixture
def mock_agent_response():
    """
    Create mock agent response for testing.

    Returns:
        dict: Standard agent response structure

    Example:
        def test_response_format(mock_agent_response):
            assert "status" in mock_agent_response
            assert mock_agent_response["status"] == "success"
    """
    return {
        "status": "success",
        "message": "Operation completed",
        "data": {}
    }


@pytest.fixture
def mock_format_detection_result():
    """
    Create mock format detection result for testing.

    Returns:
        dict: Format detection result structure

    Example:
        def test_format_result(mock_format_detection_result):
            assert mock_format_detection_result["detected_format"] == "NWB"
            assert mock_format_detection_result["confidence"] > 0.8
    """
    return {
        "detected_format": "NWB",
        "confidence": 0.95,
        "reasoning": "File has .nwb extension and valid HDF5 structure",
        "file_path": "/test/recording.nwb"
    }


@pytest.fixture
def mock_validation_result_agent():
    """
    Create mock validation result for agent testing.

    Returns:
        dict: Validation result structure

    Example:
        def test_validation(evaluation_agent, mock_validation_result_agent):
            result = mock_validation_result_agent
            assert result["is_valid"] == False
            assert len(result["issues"]) > 0
    """
    return {
        "is_valid": False,
        "issues": [
            {
                "severity": "critical",
                "message": "Missing required field: session_description",
                "location": "/",
                "check_name": "check_session_description"
            }
        ],
        "summary": {"critical": 1, "error": 0, "warning": 0, "info": 0}
    }


# ============================================================================
# User Interaction Fixtures
# ============================================================================


@pytest.fixture
def sample_user_metadata_input():
    """
    Sample user input providing metadata in natural language.

    Returns:
        dict: Various user metadata inputs for testing

    Example:
        def test_metadata_parsing(sample_user_metadata_input):
            full_text = sample_user_metadata_input["full_text"]
            assert "Jane Doe" in full_text
    """
    return {
        "full_text": "Jane Doe from MIT studied mice behavior in 2024",
        "experimenter_input": "Jane Doe",
        "institution_input": "MIT",
        "subject_input": "mouse",
        "session_description": "Visual cortex recording during maze navigation",
        "skip_input": "skip this",
        "decline_input": "no thanks"
    }


@pytest.fixture
def sample_skip_keywords():
    """
    Sample keywords users might use to skip/decline metadata.

    Returns:
        list: Keywords indicating user wants to skip metadata collection

    Example:
        def test_skip_detection(sample_skip_keywords):
            assert "skip" in sample_skip_keywords
            assert "no thanks" in sample_skip_keywords
    """
    return ["skip", "no", "no thanks", "skip this", "don't ask", "ignore"]


@pytest.fixture
def sample_validation_with_issues():
    """
    Sample validation result with warnings and info messages.

    Returns:
        dict: Validation result with non-critical issues

    Example:
        def test_validation_with_issues(sample_validation_with_issues):
            assert not sample_validation_with_issues["is_valid"]
            assert len(sample_validation_with_issues["issues"]) > 0
    """
    return {
        "is_valid": False,
        "issues": [
            {
                "severity": "WARNING",
                "message": "Missing experimenter information",
                "location": "/general/experimenter",
                "check_name": "check_experimenter"
            },
            {
                "severity": "INFO",
                "message": "Subject age not specified",
                "location": "/general/subject/age",
                "check_name": "check_subject_age"
            }
        ],
        "summary": {"critical": 0, "error": 0, "warning": 1, "info": 1}
    }


@pytest.fixture
def sample_improvement_responses():
    """
    Sample user responses for improvement decisions.

    Returns:
        dict: User responses categorized by intent (accept, retry, unsure)

    Example:
        def test_improvement_decision(sample_improvement_responses):
            accept_phrases = sample_improvement_responses["accept"]
            assert "accept it" in accept_phrases
    """
    return {
        "accept": ["accept it", "good enough", "yes, accept", "ok", "that's fine"],
        "retry": ["fix it", "retry", "improve", "try again", "make it better"],
        "unsure": ["maybe", "not sure", "what do you think", "help me decide"]
    }


@pytest.fixture
def sample_metadata_parse_response():
    """
    Sample LLM response for metadata parsing.

    Returns:
        dict: Structured metadata parsed from user input

    Example:
        def test_metadata_parse(sample_metadata_parse_response):
            assert sample_metadata_parse_response["experimenter"] == "Jane Doe"
    """
    return {
        "experimenter": "Jane Doe",
        "institution": "MIT",
        "subject_species": "Mus musculus",
        "session_description": "Visual cortex recording",
        "confidence": 0.85,
        "reasoning": "Extracted from natural language input"
    }


@pytest.fixture
def sample_provenance_metadata():
    """
    Sample metadata with provenance tracking.

    Returns:
        dict: Metadata fields with provenance information

    Example:
        def test_provenance(sample_provenance_metadata):
            field = sample_provenance_metadata["experimenter"]
            assert field["provenance"]["source"] == "USER_SPECIFIED"
    """
    return {
        "experimenter": {
            "value": "Jane Doe",
            "provenance": {
                "source": "USER_SPECIFIED",
                "confidence": 1.0,
                "timestamp": "2025-01-01T12:00:00",
                "method": "direct_input"
            }
        },
        "institution": {
            "value": "MIT",
            "provenance": {
                "source": "AI_PARSED",
                "confidence": 0.85,
                "timestamp": "2025-01-01T12:00:05",
                "method": "llm_extraction",
                "original_input": "from MIT"
            }
        }
    }
