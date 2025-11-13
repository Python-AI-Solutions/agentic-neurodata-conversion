"""
Unit tests for MCP Server.

Tests the core message routing and state management functionality.
"""

import pytest

from agentic_neurodata_conversion.models import (
    ConversionStatus,
    GlobalState,
    MCPEvent,
    MCPMessage,
    MCPResponse,
)
from agentic_neurodata_conversion.services import MCPServer, reset_mcp_server


@pytest.fixture
def mcp_server():
    """Create a fresh MCP server for each test."""
    reset_mcp_server()
    server = MCPServer()
    return server


@pytest.fixture
def sample_message():
    """Create a sample MCP message."""
    return MCPMessage(
        target_agent="conversion",
        action="detect_format",
        context={"input_path": "/path/to/data"},
    )


@pytest.mark.unit
@pytest.mark.service
class TestMCPServerInitialization:
    """Test MCP server initialization."""

    @pytest.mark.smoke
    def test_initialization(self, mcp_server):
        """Test that MCP server initializes with correct default state."""
        assert mcp_server.global_state.status == ConversionStatus.IDLE
        assert mcp_server.global_state.correction_attempt == 0
        assert len(mcp_server.global_state.logs) == 0

    def test_get_handlers_info_empty(self, mcp_server):
        """Test getting handlers info when no handlers registered."""
        handlers = mcp_server.get_handlers_info()
        assert handlers == {}


@pytest.mark.unit
@pytest.mark.service
class TestHandlerRegistration:
    """Test handler registration functionality."""

    @pytest.mark.asyncio
    async def test_register_handler(self, mcp_server):
        """Test registering a message handler."""

        async def mock_handler(msg: MCPMessage, state: GlobalState) -> MCPResponse:
            return MCPResponse.success_response(
                reply_to=msg.message_id,
                result={"status": "ok"},
            )

        mcp_server.register_handler("conversion", "detect_format", mock_handler)

        handlers = mcp_server.get_handlers_info()
        assert "conversion" in handlers
        assert "detect_format" in handlers["conversion"]

    @pytest.mark.asyncio
    async def test_register_multiple_handlers(self, mcp_server):
        """Test registering multiple handlers for different agents."""

        async def handler1(msg: MCPMessage, state: GlobalState) -> MCPResponse:
            return MCPResponse.success_response(reply_to=msg.message_id, result={})

        async def handler2(msg: MCPMessage, state: GlobalState) -> MCPResponse:
            return MCPResponse.success_response(reply_to=msg.message_id, result={})

        mcp_server.register_handler("conversion", "detect_format", handler1)
        mcp_server.register_handler("evaluation", "run_validation", handler2)

        handlers = mcp_server.get_handlers_info()
        assert "conversion" in handlers
        assert "evaluation" in handlers
        assert "detect_format" in handlers["conversion"]
        assert "run_validation" in handlers["evaluation"]


@pytest.mark.unit
@pytest.mark.service
class TestMessageSending:
    """Test message sending and routing."""

    @pytest.mark.asyncio
    async def test_send_message_success(self, mcp_server, sample_message):
        """Test sending a message to a registered handler."""

        async def mock_handler(msg: MCPMessage, state: GlobalState) -> MCPResponse:
            return MCPResponse.success_response(
                reply_to=msg.message_id,
                result={"detected_format": "SpikeGLX"},
            )

        mcp_server.register_handler("conversion", "detect_format", mock_handler)

        response = await mcp_server.send_message(sample_message)

        assert response.success is True
        assert response.reply_to == sample_message.message_id
        assert response.result["detected_format"] == "SpikeGLX"

    @pytest.mark.asyncio
    async def test_send_message_unknown_agent(self, mcp_server):
        """Test sending a message to an unknown agent."""
        message = MCPMessage(
            target_agent="unknown_agent",
            action="some_action",
        )

        response = await mcp_server.send_message(message)

        assert response.success is False
        assert response.error["code"] == "UNKNOWN_AGENT"

    @pytest.mark.asyncio
    async def test_send_message_unknown_action(self, mcp_server):
        """Test sending a message with an unknown action."""

        async def mock_handler(msg: MCPMessage, state: GlobalState) -> MCPResponse:
            return MCPResponse.success_response(reply_to=msg.message_id, result={})

        mcp_server.register_handler("conversion", "detect_format", mock_handler)

        message = MCPMessage(
            target_agent="conversion",
            action="unknown_action",
        )

        response = await mcp_server.send_message(message)

        assert response.success is False
        assert response.error["code"] == "UNKNOWN_ACTION"

    @pytest.mark.asyncio
    async def test_send_message_handler_exception(self, mcp_server, sample_message):
        """Test handling exceptions raised by handlers."""

        async def failing_handler(msg: MCPMessage, state: GlobalState) -> MCPResponse:
            raise ValueError("Simulated handler error")

        mcp_server.register_handler("conversion", "detect_format", failing_handler)

        response = await mcp_server.send_message(sample_message)

        assert response.success is False
        assert response.error["code"] == "HANDLER_EXCEPTION"
        assert "Simulated handler error" in response.error["message"]


@pytest.mark.unit
@pytest.mark.service
class TestEventBroadcasting:
    """Test event broadcasting functionality."""

    @pytest.mark.asyncio
    async def test_subscribe_to_events(self, mcp_server):
        """Test subscribing to events."""
        received_events = []

        async def subscriber(event: MCPEvent):
            received_events.append(event)

        mcp_server.subscribe_to_events(subscriber)

        event = MCPEvent(
            event_type="status_update",
            data={"status": "converting"},
        )

        await mcp_server.broadcast_event(event)

        assert len(received_events) == 1
        assert received_events[0].event_type == "status_update"

    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, mcp_server):
        """Test broadcasting to multiple subscribers."""
        received_count = [0, 0]

        async def subscriber1(event: MCPEvent):
            received_count[0] += 1

        async def subscriber2(event: MCPEvent):
            received_count[1] += 1

        mcp_server.subscribe_to_events(subscriber1)
        mcp_server.subscribe_to_events(subscriber2)

        event = MCPEvent(
            event_type="test_event",
            data={},
        )

        await mcp_server.broadcast_event(event)

        assert received_count[0] == 1
        assert received_count[1] == 1


@pytest.mark.unit
@pytest.mark.service
class TestStateManagement:
    """Test global state management."""

    def test_global_state_access(self, mcp_server):
        """Test accessing global state."""
        state = mcp_server.global_state
        assert isinstance(state, GlobalState)
        assert state.status == ConversionStatus.IDLE

    @pytest.mark.asyncio
    async def test_reset_state(self, mcp_server):
        """Test resetting global state."""
        # Modify state
        await mcp_server.global_state.update_status(ConversionStatus.CONVERTING)  # Fixed: await async call
        mcp_server.global_state.input_path = "/path/to/input"
        mcp_server.global_state.correction_attempt = 2

        # Reset
        mcp_server.reset_state()

        # Verify reset
        assert mcp_server.global_state.status == ConversionStatus.IDLE
        assert mcp_server.global_state.input_path is None
        assert mcp_server.global_state.correction_attempt == 0

    @pytest.mark.asyncio
    async def test_state_logging_on_message(self, mcp_server, sample_message):
        """Test that messages are logged to global state."""
        initial_log_count = len(mcp_server.global_state.logs)

        async def mock_handler(msg: MCPMessage, state: GlobalState) -> MCPResponse:
            return MCPResponse.success_response(reply_to=msg.message_id, result={})

        mcp_server.register_handler("conversion", "detect_format", mock_handler)
        await mcp_server.send_message(sample_message)

        # Should have logs for: handler registration, message send, message response
        assert len(mcp_server.global_state.logs) > initial_log_count


@pytest.mark.unit
@pytest.mark.service
class TestGlobalServerInstance:
    """Test global server instance management."""

    def test_get_mcp_server_singleton(self):
        """Test that get_mcp_server returns a singleton."""
        from agentic_neurodata_conversion.services import get_mcp_server

        server1 = get_mcp_server()
        server2 = get_mcp_server()

        assert server1 is server2

    def test_reset_mcp_server(self):
        """Test resetting the global server instance."""
        from agentic_neurodata_conversion.services import get_mcp_server, reset_mcp_server

        server1 = get_mcp_server()
        reset_mcp_server()
        server2 = get_mcp_server()

        assert server1 is not server2
