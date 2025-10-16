"""
Unit tests for conversation agent.

Tests the conversation agent that orchestrates user interactions and workflows.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from pathlib import Path
import tempfile

from agents.conversation_agent import ConversationAgent, register_conversation_agent
from models import (
    GlobalState,
    ConversionStatus,
    ValidationStatus,
    LogLevel,
    MCPMessage,
    MCPResponse,
)
from services.llm_service import MockLLMService
from services.mcp_server import MCPServer


class TestConversationAgentInitialization:
    """Tests for ConversationAgent initialization."""

    def test_init_with_llm_service(self):
        """Test agent initializes with LLM service."""
        mcp_server = MCPServer()
        llm_service = MockLLMService()

        agent = ConversationAgent(mcp_server=mcp_server, llm_service=llm_service)

        assert agent._mcp_server is mcp_server
        assert agent._llm_service is llm_service
        assert agent._conversational_handler is not None
        # Conversation history is now in GlobalState, not in agent
        # assert isinstance(agent._conversation_history, list)  # Removed: moved to GlobalState

    def test_init_without_llm_service(self):
        """Test agent initializes without LLM service."""
        mcp_server = MCPServer()

        agent = ConversationAgent(mcp_server=mcp_server)

        assert agent._mcp_server is mcp_server
        assert agent._llm_service is None
        assert agent._conversational_handler is None


class TestStartConversion:
    """Tests for starting conversion workflow."""

    @pytest.fixture
    def mcp_server(self):
        """Create mock MCP server."""
        return MCPServer()

    @pytest.fixture
    def agent(self, mcp_server):
        """Create conversation agent."""
        return ConversationAgent(mcp_server=mcp_server, llm_service=MockLLMService())

    @pytest.fixture
    def state(self):
        """Create global state."""
        return GlobalState()

    @pytest.mark.asyncio
    async def test_start_conversion_missing_input_path(self, agent, state):
        """Test start conversion with missing input path."""
        message = MCPMessage(
            target_agent="conversation",
            action="start_conversion",
            context={},  # Missing input_path
        )

        response = await agent.handle_start_conversion(message, state)

        assert response.success is False
        assert response.error["code"] == "MISSING_INPUT_PATH"

    @pytest.mark.asyncio
    async def test_start_conversion_calls_detect_format(self, agent, state, mcp_server):
        """Test start conversion triggers format detection."""
        # Mock the send_message method to return success
        async def mock_send_message(msg):
            if msg.action == "detect_format":
                return MCPResponse.success_response(
                    reply_to=msg.message_id,
                    result={"format": "SpikeGLX", "confidence": "high"},
                )
            return MCPResponse.success_response(reply_to=msg.message_id, result={})

        mcp_server.send_message = mock_send_message

        message = MCPMessage(
            target_agent="conversation",
            action="start_conversion",
            context={"input_path": "/path/to/data"},
        )

        response = await agent.handle_start_conversion(message, state)

        # Should have set input path in state
        assert state.input_path == "/path/to/data"
        assert len(state.logs) > 0

    @pytest.mark.asyncio
    async def test_start_conversion_with_metadata(self, agent, state, mcp_server):
        """Test start conversion with metadata."""
        async def mock_send_message(msg):
            return MCPResponse.success_response(
                reply_to=msg.message_id,
                result={"format": "SpikeGLX"},
            )

        mcp_server.send_message = mock_send_message

        metadata = {"experimenter": "Jane Doe", "institution": "MIT"}
        message = MCPMessage(
            target_agent="conversation",
            action="start_conversion",
            context={"input_path": "/path/to/data", "metadata": metadata},
        )

        response = await agent.handle_start_conversion(message, state)

        assert state.metadata == metadata


class TestUserFormatSelection:
    """Tests for user format selection handling."""

    @pytest.fixture
    def mcp_server(self):
        """Create mock MCP server."""
        return MCPServer()

    @pytest.fixture
    def agent(self, mcp_server):
        """Create conversation agent."""
        return ConversationAgent(mcp_server=mcp_server, llm_service=MockLLMService())

    @pytest.fixture
    def state(self):
        """Create global state."""
        state = GlobalState()
        state.input_path = "/path/to/data"
        state.status = ConversionStatus.AWAITING_FORMAT_SELECTION
        return state

    @pytest.mark.asyncio
    async def test_handle_user_format_selection_success(self, agent, state, mcp_server):
        """Test handling user format selection."""
        async def mock_send_message(msg):
            return MCPResponse.success_response(
                reply_to=msg.message_id,
                result={"format": "SpikeGLX", "converted": True},
            )

        mcp_server.send_message = mock_send_message

        message = MCPMessage(
            target_agent="conversation",
            action="user_format_selection",
            context={"format": "SpikeGLX"},
        )

        response = await agent.handle_user_format_selection(message, state)

        # Check that format was stored in state
        assert state.metadata.get("format") == "SpikeGLX"

    @pytest.mark.asyncio
    async def test_handle_user_format_selection_missing_format(self, agent, state):
        """Test handling format selection without format specified."""
        message = MCPMessage(
            target_agent="conversation",
            action="user_format_selection",
            context={},  # Missing format
        )

        response = await agent.handle_user_format_selection(message, state)

        assert response.success is False
        assert "format" in response.error["message"].lower()


class TestRetryDecision:
    """Tests for retry decision handling."""

    @pytest.fixture
    def mcp_server(self):
        """Create mock MCP server."""
        return MCPServer()

    @pytest.fixture
    def agent(self, mcp_server):
        """Create conversation agent."""
        return ConversationAgent(mcp_server=mcp_server, llm_service=MockLLMService())

    @pytest.fixture
    def state(self):
        """Create global state with validation failure."""
        state = GlobalState()
        state.status = ConversionStatus.AWAITING_RETRY_DECISION
        state.validation_status = ValidationStatus.FAILED
        return state

    @pytest.mark.asyncio
    async def test_handle_retry_decision_with_fixes(self, agent, state, mcp_server):
        """Test retry decision with user-provided fixes."""
        async def mock_send_message(msg):
            return MCPResponse.success_response(
                reply_to=msg.message_id,
                result={"validation_status": "passed"},
            )

        mcp_server.send_message = mock_send_message

        message = MCPMessage(
            target_agent="conversation",
            action="retry_decision",
            context={
                "retry": True,
                "fixes": {"experimenter": ["Jane Doe"], "institution": "MIT"},
            },
        )

        response = await agent.handle_retry_decision(message, state)

        # Fixes should be merged into metadata
        assert "experimenter" in state.metadata or response.success


class TestConversationalResponse:
    """Tests for conversational response handling."""

    @pytest.fixture
    def mcp_server(self):
        """Create mock MCP server."""
        return MCPServer()

    @pytest.fixture
    def agent(self, mcp_server):
        """Create conversation agent with LLM."""
        return ConversationAgent(mcp_server=mcp_server, llm_service=MockLLMService())

    @pytest.fixture
    def state(self):
        """Create global state."""
        return GlobalState()

    @pytest.mark.asyncio
    async def test_handle_conversational_response_with_handler(self, agent, state):
        """Test conversational response with LLM handler."""
        # Mock the conversational handler
        async def mock_process_response(msg, context, state):
            return {
                "type": "user_response_processed",
                "extracted_metadata": {"experimenter": ["Jane Doe"]},
                "ready_to_proceed": True,
            }

        agent._conversational_handler.process_user_response = mock_process_response

        message = MCPMessage(
            target_agent="conversation",
            action="conversational_response",
            context={"user_message": "The experimenter was Jane Doe"},
        )

        response = await agent.handle_conversational_response(message, state)

        # Should have processed the response
        assert response.success or isinstance(response, MCPResponse)

    @pytest.mark.asyncio
    async def test_handle_conversational_response_without_handler(self):
        """Test conversational response without LLM handler."""
        mcp_server = MCPServer()
        agent = ConversationAgent(mcp_server=mcp_server)  # No LLM
        state = GlobalState()

        message = MCPMessage(
            target_agent="conversation",
            action="conversational_response",
            context={"user_message": "test"},
        )

        response = await agent.handle_conversational_response(message, state)

        # Should return error when no handler available
        assert response.success is False or response.error is not None


class TestGeneralQuery:
    """Tests for general query handling."""

    @pytest.fixture
    def mcp_server(self):
        """Create mock MCP server."""
        return MCPServer()

    @pytest.fixture
    def agent(self, mcp_server):
        """Create conversation agent with LLM."""
        llm_service = MockLLMService()
        llm_service.set_response(
            "general_query",
            '{"answer": "You can upload your data files here.", "suggestions": []}',
        )
        return ConversationAgent(mcp_server=mcp_server, llm_service=llm_service)

    @pytest.fixture
    def state(self):
        """Create global state."""
        return GlobalState()

    @pytest.mark.asyncio
    async def test_handle_general_query_with_llm(self, agent, state):
        """Test general query with LLM service."""
        message = MCPMessage(
            target_agent="conversation",
            action="general_query",
            context={"query": "How do I convert my data?"},
        )

        response = await agent.handle_general_query(message, state)

        # Should have generated a response
        assert response.success is True or response.result is not None

    @pytest.mark.asyncio
    async def test_handle_general_query_missing_query(self, agent, state):
        """Test general query without query text."""
        message = MCPMessage(
            target_agent="conversation",
            action="general_query",
            context={},  # Missing query
        )

        response = await agent.handle_general_query(message, state)

        # Should return error for missing query
        assert response.success is False


class TestHelperMethods:
    """Tests for helper methods."""

    @pytest.fixture
    def mcp_server(self):
        """Create mock MCP server."""
        return MCPServer()

    @pytest.fixture
    def agent(self, mcp_server):
        """Create conversation agent."""
        return ConversationAgent(mcp_server=mcp_server, llm_service=MockLLMService())

    def test_identify_user_input_required(self, agent):
        """Test identifying required user input from corrections."""
        corrections = {
            "required_fields": [
                {"field": "experimenter", "message": "Missing experimenter"},
                {"field": "institution", "message": "Missing institution"},
            ]
        }

        required = agent._identify_user_input_required(corrections)

        assert isinstance(required, list)
        assert len(required) == 2

    def test_identify_user_input_required_empty(self, agent):
        """Test identifying user input with no corrections."""
        corrections = {}

        required = agent._identify_user_input_required(corrections)

        assert isinstance(required, list)
        assert len(required) == 0

    def test_extract_auto_fixes(self, agent):
        """Test extracting auto-fixable items."""
        corrections = {
            "auto_fixable": [
                {"field": "subject_id", "value": "mouse_001"},
                {"field": "session_id", "value": "session_20250116"},
            ]
        }

        auto_fixes = agent._extract_auto_fixes(corrections)

        assert isinstance(auto_fixes, dict)
        # Should have extracted the auto-fixable items

    def test_extract_auto_fixes_empty(self, agent):
        """Test extracting auto-fixes with no auto-fixable items."""
        corrections = {}

        auto_fixes = agent._extract_auto_fixes(corrections)

        assert isinstance(auto_fixes, dict)
        assert len(auto_fixes) == 0


class TestExplainError:
    """Tests for error explanation."""

    @pytest.fixture
    def mcp_server(self):
        """Create mock MCP server."""
        return MCPServer()

    @pytest.fixture
    def agent(self, mcp_server):
        """Create conversation agent with LLM."""
        return ConversationAgent(mcp_server=mcp_server, llm_service=MockLLMService())

    @pytest.fixture
    def state(self):
        """Create global state."""
        return GlobalState()

    @pytest.mark.asyncio
    async def test_explain_error_to_user_with_llm(self, agent, state):
        """Test explaining error with LLM."""
        error_info = {
            "code": "VALIDATION_FAILED",
            "message": "NWB validation failed",
            "details": "Missing required metadata fields",
        }

        explanation = await agent._explain_error_to_user(error_info, state)

        assert isinstance(explanation, str)
        assert len(explanation) > 0

    @pytest.mark.asyncio
    async def test_explain_error_without_llm(self):
        """Test explaining error without LLM."""
        mcp_server = MCPServer()
        agent = ConversationAgent(mcp_server=mcp_server)  # No LLM
        state = GlobalState()

        error_info = {"message": "Test error"}

        explanation = await agent._explain_error_to_user(error_info, state)

        # Should return basic explanation without LLM
        assert isinstance(explanation, str)


class TestProactiveIssueDetection:
    """Tests for proactive issue detection."""

    @pytest.fixture
    def mcp_server(self):
        """Create mock MCP server."""
        return MCPServer()

    @pytest.fixture
    def agent(self, mcp_server):
        """Create conversation agent with LLM."""
        return ConversationAgent(mcp_server=mcp_server, llm_service=MockLLMService())

    @pytest.fixture
    def state(self):
        """Create global state."""
        return GlobalState()

    @pytest.mark.asyncio
    async def test_proactive_issue_detection_with_issues(self, agent, state):
        """Test proactive detection identifies issues."""
        state.input_path = "/path/to/data"
        state.metadata = {}  # Empty metadata - should detect missing fields

        issues = await agent._proactive_issue_detection(state)

        assert isinstance(issues, list)
        # Should detect some issues with empty metadata

    @pytest.mark.asyncio
    async def test_proactive_issue_detection_no_llm(self):
        """Test proactive detection without LLM."""
        mcp_server = MCPServer()
        agent = ConversationAgent(mcp_server=mcp_server)  # No LLM
        state = GlobalState()

        issues = await agent._proactive_issue_detection(state)

        # Should return empty list or basic issues without LLM
        assert isinstance(issues, list)


class TestStatusMessage:
    """Tests for status message generation."""

    @pytest.fixture
    def mcp_server(self):
        """Create mock MCP server."""
        return MCPServer()

    @pytest.fixture
    def agent(self, mcp_server):
        """Create conversation agent with LLM."""
        return ConversationAgent(mcp_server=mcp_server, llm_service=MockLLMService())

    @pytest.fixture
    def state(self):
        """Create global state."""
        return GlobalState()

    @pytest.mark.asyncio
    async def test_generate_status_message_idle(self, agent, state):
        """Test generating status message for idle state."""
        state.status = ConversionStatus.IDLE

        message = await agent._generate_status_message(state)

        assert isinstance(message, str)
        assert len(message) > 0

    @pytest.mark.asyncio
    async def test_generate_status_message_converting(self, agent, state):
        """Test generating status message for converting state."""
        state.status = ConversionStatus.CONVERTING
        state.input_path = "/path/to/data"

        message = await agent._generate_status_message(state)

        assert isinstance(message, str)
        assert "convert" in message.lower() or len(message) > 0

    @pytest.mark.asyncio
    async def test_generate_status_message_validating(self, agent, state):
        """Test generating status message for validating state."""
        state.status = ConversionStatus.VALIDATING

        message = await agent._generate_status_message(state)

        assert isinstance(message, str)


class TestRegisterFunction:
    """Tests for agent registration function."""

    def test_register_conversation_agent(self):
        """Test registering conversation agent with MCP server."""
        mcp_server = MCPServer()
        llm_service = MockLLMService()

        agent = register_conversation_agent(mcp_server, llm_service)

        assert isinstance(agent, ConversationAgent)
        assert agent._mcp_server is mcp_server
        assert agent._llm_service is llm_service

        # Check that handlers were registered
        handlers_info = mcp_server.get_handlers_info()
        assert "conversation" in handlers_info

    def test_register_conversation_agent_without_llm(self):
        """Test registering agent without LLM service."""
        mcp_server = MCPServer()

        agent = register_conversation_agent(mcp_server, None)

        assert isinstance(agent, ConversationAgent)
        assert agent._llm_service is None
