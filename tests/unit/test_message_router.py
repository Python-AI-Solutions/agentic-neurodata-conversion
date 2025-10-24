"""
Unit tests for MessageRouter.

Tests cover:
- send_message creates valid MCPMessage
- send_message sends HTTP POST to agent
- send_message raises error for unregistered agent
- execute_agent_task sends AGENT_EXECUTE message
- execute_agent_task includes session_id and parameters
- execute_agent_task returns agent response
- Message routing with multiple agents
- HTTP timeout handling
- Network error handling
- Message ID uniqueness
"""

import json
import uuid

import httpx
import pytest
import respx

from agentic_neurodata_conversion.mcp_server.agent_registry import AgentRegistry
from agentic_neurodata_conversion.mcp_server.message_router import MessageRouter
from agentic_neurodata_conversion.models.mcp_message import MessageType


class TestMessageRouter:
    """Test MessageRouter class."""

    @pytest.fixture
    def agent_registry(self) -> AgentRegistry:
        """Create AgentRegistry with test agents registered."""
        registry = AgentRegistry()
        registry.register_agent(
            agent_name="conversation_agent",
            agent_type="conversation",
            base_url="http://localhost:3001",
            capabilities=["initialize_session", "handle_clarification"],
        )
        registry.register_agent(
            agent_name="conversion_agent",
            agent_type="conversion",
            base_url="http://localhost:3002",
            capabilities=["convert_to_nwb"],
        )
        registry.register_agent(
            agent_name="evaluation_agent",
            agent_type="evaluation",
            base_url="http://localhost:3003",
            capabilities=["validate_nwb"],
        )
        return registry

    @pytest.fixture
    async def message_router(self, agent_registry: AgentRegistry) -> MessageRouter:
        """Create MessageRouter instance with test registry."""
        router = MessageRouter(agent_registry=agent_registry, timeout=60)
        yield router
        # Cleanup
        await router.close()

    @pytest.mark.asyncio
    async def test_send_message_creates_valid_mcp_message(
        self, message_router: MessageRouter
    ) -> None:
        """Test send_message creates a valid MCPMessage with all required fields."""
        # Mock HTTP client to capture the message
        with respx.mock:
            route = respx.post("http://localhost:3001/mcp/message").mock(
                return_value=httpx.Response(
                    200, json={"status": "success", "result": {}}
                )
            )

            await message_router.send_message(
                target_agent="conversation_agent",
                message_type=MessageType.AGENT_EXECUTE,
                payload={"task": "initialize_session", "session_id": "test-123"},
            )

            # Verify the request was made
            assert route.called
            request = route.calls.last.request
            # respx stores content as bytes, need to decode
            message_data = json.loads(request.content.decode("utf-8"))

            # Verify MCPMessage structure
            assert "message_id" in message_data
            assert "timestamp" in message_data
            assert message_data["source_agent"] == "mcp_server"
            assert message_data["target_agent"] == "conversation_agent"
            assert message_data["message_type"] == "agent_execute"
            assert message_data["payload"]["task"] == "initialize_session"
            assert message_data["payload"]["session_id"] == "test-123"

    @pytest.mark.asyncio
    async def test_send_message_sends_http_post_to_agent(
        self, message_router: MessageRouter
    ) -> None:
        """Test send_message sends HTTP POST to correct agent endpoint."""
        with respx.mock:
            route = respx.post("http://localhost:3002/mcp/message").mock(
                return_value=httpx.Response(
                    200, json={"status": "success", "result": {"data": "test"}}
                )
            )

            result = await message_router.send_message(
                target_agent="conversion_agent",
                message_type=MessageType.AGENT_EXECUTE,
                payload={"task": "convert_to_nwb"},
            )

            # Verify POST was made to correct URL
            assert route.called
            assert route.calls.last.request.url == "http://localhost:3002/mcp/message"
            assert route.calls.last.request.method == "POST"

            # Verify response returned correctly
            assert result["status"] == "success"
            assert result["result"]["data"] == "test"

    @pytest.mark.asyncio
    async def test_send_message_raises_error_for_unregistered_agent(
        self, message_router: MessageRouter
    ) -> None:
        """Test send_message raises ValueError for unregistered agent."""
        with pytest.raises(ValueError, match="Agent 'unknown_agent' not found"):
            await message_router.send_message(
                target_agent="unknown_agent",
                message_type=MessageType.AGENT_EXECUTE,
                payload={},
            )

    @pytest.mark.asyncio
    async def test_execute_agent_task_sends_agent_execute_message(
        self, message_router: MessageRouter
    ) -> None:
        """Test execute_agent_task sends AGENT_EXECUTE message type."""
        with respx.mock:
            route = respx.post("http://localhost:3001/mcp/message").mock(
                return_value=httpx.Response(
                    200, json={"status": "success", "result": {}}
                )
            )

            await message_router.execute_agent_task(
                target_agent="conversation_agent",
                task_name="initialize_session",
                session_id="session-123",
                parameters={"dataset_path": "/data/test"},
            )

            assert route.called
            request = route.calls.last.request
            message_data = json.loads(request.content.decode("utf-8"))

            # Verify message type is AGENT_EXECUTE
            assert message_data["message_type"] == "agent_execute"

    @pytest.mark.asyncio
    async def test_execute_agent_task_includes_session_id_and_parameters(
        self, message_router: MessageRouter
    ) -> None:
        """Test execute_agent_task includes session_id and parameters in payload."""
        with respx.mock:
            route = respx.post("http://localhost:3001/mcp/message").mock(
                return_value=httpx.Response(
                    200, json={"status": "success", "result": {}}
                )
            )

            await message_router.execute_agent_task(
                target_agent="conversation_agent",
                task_name="initialize_session",
                session_id="session-456",
                parameters={
                    "dataset_path": "/data/openephys",
                    "format": "openephys",
                },
            )

            assert route.called
            request = route.calls.last.request
            message_data = json.loads(request.content.decode("utf-8"))

            # Verify payload structure
            assert message_data["session_id"] == "session-456"
            assert message_data["payload"]["task_name"] == "initialize_session"
            assert message_data["payload"]["session_id"] == "session-456"
            assert (
                message_data["payload"]["parameters"]["dataset_path"]
                == "/data/openephys"
            )
            assert message_data["payload"]["parameters"]["format"] == "openephys"

    @pytest.mark.asyncio
    async def test_execute_agent_task_returns_agent_response(
        self, message_router: MessageRouter
    ) -> None:
        """Test execute_agent_task returns the agent's response."""
        expected_response = {
            "status": "success",
            "result": {
                "dataset_info": {"format": "openephys"},
                "metadata": {"subject_id": "mouse_001"},
            },
        }

        with respx.mock:
            respx.post("http://localhost:3001/mcp/message").mock(
                return_value=httpx.Response(200, json=expected_response)
            )

            result = await message_router.execute_agent_task(
                target_agent="conversation_agent",
                task_name="initialize_session",
                session_id="session-789",
                parameters={},
            )

            assert result == expected_response
            assert result["status"] == "success"
            assert result["result"]["dataset_info"]["format"] == "openephys"

    @pytest.mark.asyncio
    async def test_message_routing_with_multiple_agents(
        self, message_router: MessageRouter
    ) -> None:
        """Test message routing works correctly with multiple different agents."""
        with respx.mock:
            # Mock responses for different agents
            conv_route = respx.post("http://localhost:3001/mcp/message").mock(
                return_value=httpx.Response(
                    200, json={"status": "success", "agent": "conversation"}
                )
            )
            convert_route = respx.post("http://localhost:3002/mcp/message").mock(
                return_value=httpx.Response(
                    200, json={"status": "success", "agent": "conversion"}
                )
            )
            eval_route = respx.post("http://localhost:3003/mcp/message").mock(
                return_value=httpx.Response(
                    200, json={"status": "success", "agent": "evaluation"}
                )
            )

            # Send messages to different agents
            result1 = await message_router.send_message(
                target_agent="conversation_agent",
                message_type=MessageType.AGENT_EXECUTE,
                payload={},
            )
            result2 = await message_router.send_message(
                target_agent="conversion_agent",
                message_type=MessageType.AGENT_EXECUTE,
                payload={},
            )
            result3 = await message_router.send_message(
                target_agent="evaluation_agent",
                message_type=MessageType.AGENT_EXECUTE,
                payload={},
            )

            # Verify each route was called
            assert conv_route.called
            assert convert_route.called
            assert eval_route.called

            # Verify correct responses
            assert result1["agent"] == "conversation"
            assert result2["agent"] == "conversion"
            assert result3["agent"] == "evaluation"

    @pytest.mark.asyncio
    async def test_http_timeout_handling(self, message_router: MessageRouter) -> None:
        """Test HTTP timeout errors are handled appropriately."""
        with respx.mock:
            respx.post("http://localhost:3001/mcp/message").mock(
                side_effect=httpx.TimeoutException("Request timeout")
            )

            with pytest.raises(httpx.TimeoutException, match="Request timeout"):
                await message_router.send_message(
                    target_agent="conversation_agent",
                    message_type=MessageType.AGENT_EXECUTE,
                    payload={},
                )

    @pytest.mark.asyncio
    async def test_network_error_handling(self, message_router: MessageRouter) -> None:
        """Test network errors are handled appropriately."""
        with respx.mock:
            respx.post("http://localhost:3001/mcp/message").mock(
                side_effect=httpx.ConnectError("Connection refused")
            )

            with pytest.raises(httpx.ConnectError, match="Connection refused"):
                await message_router.send_message(
                    target_agent="conversation_agent",
                    message_type=MessageType.AGENT_EXECUTE,
                    payload={},
                )

    @pytest.mark.asyncio
    async def test_http_error_status_handling(
        self, message_router: MessageRouter
    ) -> None:
        """Test HTTP error status codes are handled appropriately."""
        with respx.mock:
            respx.post("http://localhost:3001/mcp/message").mock(
                return_value=httpx.Response(
                    500, json={"error": "Internal server error"}
                )
            )

            # Should raise HTTPStatusError for 5xx responses
            with pytest.raises(httpx.HTTPStatusError):
                await message_router.send_message(
                    target_agent="conversation_agent",
                    message_type=MessageType.AGENT_EXECUTE,
                    payload={},
                )

    @pytest.mark.asyncio
    async def test_message_id_uniqueness(self, message_router: MessageRouter) -> None:
        """Test that each message gets a unique message ID (UUID)."""
        message_ids = set()

        with respx.mock:
            route = respx.post("http://localhost:3001/mcp/message").mock(
                return_value=httpx.Response(
                    200, json={"status": "success", "result": {}}
                )
            )

            # Send multiple messages
            for _ in range(10):
                await message_router.send_message(
                    target_agent="conversation_agent",
                    message_type=MessageType.AGENT_EXECUTE,
                    payload={},
                )

            # Extract message IDs from all requests
            for call in route.calls:
                message_data = json.loads(call.request.content.decode("utf-8"))
                message_ids.add(message_data["message_id"])

            # Verify all IDs are unique
            assert len(message_ids) == 10

            # Verify each ID is a valid UUID
            for message_id in message_ids:
                uuid.UUID(message_id)  # This will raise ValueError if invalid

    @pytest.mark.asyncio
    async def test_close_method_closes_http_client(
        self, agent_registry: AgentRegistry
    ) -> None:
        """Test close method properly closes the HTTP client."""
        router = MessageRouter(agent_registry=agent_registry)

        # Verify client is open initially
        assert not router.http_client.is_closed

        # Close the router
        await router.close()

        # Verify client is closed
        assert router.http_client.is_closed

    @pytest.mark.asyncio
    async def test_timeout_configuration(self, agent_registry: AgentRegistry) -> None:
        """Test timeout can be configured during initialization."""
        router = MessageRouter(agent_registry=agent_registry, timeout=30)

        # Verify timeout is set correctly
        assert router.timeout == 30
        assert router.http_client.timeout.read == 30

        await router.close()

    @pytest.mark.asyncio
    async def test_send_message_with_session_id_in_message(
        self, message_router: MessageRouter
    ) -> None:
        """Test send_message includes session_id at message level when provided in payload."""
        with respx.mock:
            route = respx.post("http://localhost:3001/mcp/message").mock(
                return_value=httpx.Response(
                    200, json={"status": "success", "result": {}}
                )
            )

            await message_router.send_message(
                target_agent="conversation_agent",
                message_type=MessageType.AGENT_EXECUTE,
                payload={"session_id": "test-session-999"},
            )

            assert route.called
            request = route.calls.last.request
            message_data = json.loads(request.content.decode("utf-8"))

            # Verify session_id is extracted from payload to message level
            assert message_data["session_id"] == "test-session-999"
