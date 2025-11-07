"""
MCP (Model Context Protocol) Server implementation.

This is the central orchestration layer that routes messages between agents
and manages the global state.
"""

import asyncio
from typing import Callable, Optional

from models.mcp import MCPEvent, MCPMessage, MCPResponse
from models.state import GlobalState, LogLevel


class MCPServer:
    """
    Central MCP server for agent communication.

    Manages:
    - Message routing between agents
    - Global state management
    - Event broadcasting
    - Handler registration
    """

    def __init__(self):
        """Initialize the MCP server."""
        self._handlers: dict[str, dict[str, Callable]] = {}
        self._event_subscribers: list[Callable] = []
        self._global_state: GlobalState = GlobalState()
        self._message_queue: asyncio.Queue = asyncio.Queue()

    @property
    def global_state(self) -> GlobalState:
        """Get the current global state."""
        return self._global_state

    def register_handler(
        self,
        agent_name: str,
        action: str,
        handler: Callable[[MCPMessage, GlobalState], MCPResponse],
    ) -> None:
        """
        Register a message handler for a specific agent and action.

        Args:
            agent_name: Name of the agent (conversation|conversion|evaluation)
            action: Action identifier (e.g., detect_format, run_conversion)
            handler: Async callable that processes the message
        """
        if agent_name not in self._handlers:
            self._handlers[agent_name] = {}

        self._handlers[agent_name][action] = handler
        self._global_state.add_log(
            LogLevel.DEBUG,
            f"Registered handler: {agent_name}.{action}",
            {"agent": agent_name, "action": action},
        )

    def subscribe_to_events(self, subscriber: Callable[[MCPEvent], None]) -> None:
        """
        Subscribe to all MCP events.

        Args:
            subscriber: Async callable that receives events
        """
        self._event_subscribers.append(subscriber)

    def unsubscribe_from_events(self, subscriber: Callable[[MCPEvent], None]) -> None:
        """
        Unsubscribe from MCP events.

        Args:
            subscriber: Async callable to remove from subscribers

        Note:
            If subscriber is not in the list, this is a no-op (silently fails).
            This prevents errors during cleanup when subscriber may already be removed.
        """
        try:
            self._event_subscribers.remove(subscriber)
        except ValueError:
            # Subscriber not in list - already removed or never added
            # This is expected during cleanup, so we don't raise an error
            pass

    async def send_message(self, message: MCPMessage) -> MCPResponse:
        """
        Send a message to the target agent and wait for response.

        Args:
            message: MCP message to send

        Returns:
            Response from the target agent

        Raises:
            ValueError: If no handler is registered for the target agent/action
        """
        agent_name = message.target_agent
        action = message.action

        # Log the message
        self._global_state.add_log(
            LogLevel.DEBUG,
            f"Sending message to {agent_name}.{action}",
            {
                "message_id": message.message_id,
                "agent": agent_name,
                "action": action,
            },
        )

        # Find handler
        if agent_name not in self._handlers:
            error_msg = f"No handlers registered for agent '{agent_name}'"
            self._global_state.add_log(
                LogLevel.ERROR,
                error_msg,
                {"agent": agent_name},
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="UNKNOWN_AGENT",
                error_message=error_msg,
            )

        if action not in self._handlers[agent_name]:
            error_msg = f"No handler registered for action '{action}' on agent '{agent_name}'"
            self._global_state.add_log(
                LogLevel.ERROR,
                error_msg,
                {"agent": agent_name, "action": action},
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="UNKNOWN_ACTION",
                error_message=error_msg,
            )

        # Execute handler
        handler = self._handlers[agent_name][action]
        try:
            response = await handler(message, self._global_state)
            self._global_state.add_log(
                LogLevel.DEBUG,
                f"Received response from {agent_name}.{action}",
                {
                    "message_id": message.message_id,
                    "response_id": response.message_id,
                    "success": response.success,
                },
            )
            return response
        except Exception as e:
            error_msg = f"Handler {agent_name}.{action} raised exception: {str(e)}"
            self._global_state.add_log(
                LogLevel.ERROR,
                error_msg,
                {
                    "agent": agent_name,
                    "action": action,
                    "exception": str(e),
                },
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="HANDLER_EXCEPTION",
                error_message=error_msg,
                error_context={"exception": str(e)},
            )

    async def broadcast_event(self, event: MCPEvent) -> None:
        """
        Broadcast an event to all subscribers.

        Args:
            event: Event to broadcast
        """
        self._global_state.add_log(
            LogLevel.DEBUG,
            f"Broadcasting event: {event.event_type}",
            {"event_id": event.event_id, "event_type": event.event_type},
        )

        # Send to all subscribers
        tasks = [subscriber(event) for subscriber in self._event_subscribers]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def reset_state(self) -> None:
        """Reset the global state for a new conversion session."""
        self._global_state.reset()
        self._global_state.add_log(
            LogLevel.INFO,
            "Global state reset",
        )

    def get_handlers_info(self) -> dict[str, list[str]]:
        """
        Get information about registered handlers.

        Returns:
            Dictionary mapping agent names to lists of registered actions
        """
        return {agent: list(actions.keys()) for agent, actions in self._handlers.items()}


# Global MCP server instance
_mcp_server: Optional[MCPServer] = None


def get_mcp_server() -> MCPServer:
    """
    Get or create the global MCP server instance.

    Returns:
        Global MCPServer instance
    """
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = MCPServer()
        # Set MCP server reference in global state for WebSocket event broadcasting
        _mcp_server.global_state.set_mcp_server(_mcp_server)
    return _mcp_server


def reset_mcp_server() -> None:
    """
    Reset the global MCP server instance.

    Used primarily for testing.
    """
    global _mcp_server
    _mcp_server = None
