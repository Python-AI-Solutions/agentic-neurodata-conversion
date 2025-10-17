"""
Message Router for MCP Server.

Routes MCP messages between agents via HTTP POST requests. This component
is responsible for creating properly formatted MCPMessage objects and
delivering them to the correct agent endpoints.

Critical path component requiring ≥90% test coverage.
"""

from datetime import datetime
from typing import Any, cast
import uuid

import httpx

from agentic_neurodata_conversion.mcp_server.agent_registry import AgentRegistry
from agentic_neurodata_conversion.models.mcp_message import MCPMessage, MessageType


class MessageRouter:
    """
    Routes MCP messages between agents via HTTP.

    The MessageRouter is responsible for:
    - Creating properly formatted MCPMessage objects with unique IDs
    - Looking up agent endpoints from the AgentRegistry
    - Sending HTTP POST requests to agent endpoints
    - Handling errors (unregistered agents, network issues, timeouts)

    HTTP Endpoint Contract:
    - All agents expose POST /mcp/message endpoint
    - Request body: MCPMessage as JSON
    - Response: {"status": "success"/"error", "result": {...}}

    Example:
        router = MessageRouter(agent_registry, timeout=60)
        result = await router.send_message(
            target_agent="conversation_agent",
            message_type=MessageType.AGENT_EXECUTE,
            payload={"task": "initialize_session", "session_id": "test-123"}
        )
        await router.close()
    """

    def __init__(self, agent_registry: AgentRegistry, timeout: int = 60) -> None:
        """
        Initialize MessageRouter.

        Args:
            agent_registry: AgentRegistry instance for agent lookup
            timeout: HTTP request timeout in seconds (default: 60)
        """
        self.agent_registry = agent_registry
        self.timeout = timeout
        self.http_client = httpx.AsyncClient(timeout=timeout)

    async def send_message(
        self,
        target_agent: str,
        message_type: MessageType,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Send MCP message to target agent via HTTP POST.

        Creates an MCPMessage with a unique ID and sends it to the agent's
        /mcp/message endpoint. Raises exceptions for network errors, timeouts,
        and HTTP errors which should be handled by the caller.

        Args:
            target_agent: Name of the agent to send message to
            message_type: Type of MCP message (e.g., AGENT_EXECUTE)
            payload: Message-specific payload data

        Returns:
            Agent response as dict with "status" and "result" fields

        Raises:
            ValueError: If target agent is not registered
            httpx.TimeoutException: If request times out
            httpx.ConnectError: If connection to agent fails
            httpx.HTTPStatusError: If agent returns HTTP error status
        """
        # 1. Check agent is registered
        agent_info = self.agent_registry.get_agent(target_agent)
        if agent_info is None:
            raise ValueError(f"Agent '{target_agent}' not found in registry")

        # 2. Extract session_id from payload if present
        session_id = payload.get("session_id")

        # 3. Create MCPMessage with unique ID
        message = MCPMessage(
            message_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            source_agent="mcp_server",
            target_agent=target_agent,
            session_id=session_id,
            message_type=message_type,
            payload=payload,
        )

        # 4. Send HTTP POST to agent endpoint
        url = f"{agent_info['base_url']}/mcp/message"
        response = await self.http_client.post(
            url,
            json=message.model_dump(mode="json"),
        )

        # 5. Raise exception for HTTP errors (4xx, 5xx)
        response.raise_for_status()

        # 6. Return agent response
        return cast("dict[str, Any]", response.json())

    async def execute_agent_task(
        self,
        target_agent: str,
        task_name: str,
        session_id: str,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Convenience method for sending AGENT_EXECUTE messages.

        This is the most common message type, used to instruct an agent to
        perform a specific task within a session context.

        Args:
            target_agent: Name of the agent to execute the task
            task_name: Name of the task to execute
            session_id: Session context identifier
            parameters: Task-specific parameters

        Returns:
            Agent response as dict with "status" and "result" fields

        Raises:
            ValueError: If target agent is not registered
            httpx.TimeoutException: If request times out
            httpx.ConnectError: If connection to agent fails
            httpx.HTTPStatusError: If agent returns HTTP error status
        """
        payload = {
            "task_name": task_name,
            "session_id": session_id,
            "parameters": parameters,
        }

        return await self.send_message(
            target_agent=target_agent,
            message_type=MessageType.AGENT_EXECUTE,
            payload=payload,
        )

    async def close(self) -> None:
        """
        Close HTTP client and release resources.

        Should be called when the MessageRouter is no longer needed,
        typically during server shutdown.
        """
        await self.http_client.aclose()
