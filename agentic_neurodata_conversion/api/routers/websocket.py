"""WebSocket router for real-time bidirectional communication.

Handles:
- WebSocket connection management
- Real-time event streaming from MCP server
- Client subscription management
- Keep-alive / ping-pong
"""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from agentic_neurodata_conversion.api.dependencies import get_or_create_mcp_server
from agentic_neurodata_conversion.models import WebSocketMessage

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates.

    Provides bidirectional, real-time communication between the client and server.
    The server pushes events (status updates, progress, validation results, etc.)
    to connected clients, and clients can send ping messages for keep-alive.

    Protocol:
    - Server → Client: MCP events (status_changed, progress_updated, etc.)
    - Client → Server: Control messages (ping, subscribe, unsubscribe)

    Event Types:
    - status_changed: Conversion status updates
    - progress_updated: Progress percentage and stage updates
    - validation_completed: Validation results available
    - error_occurred: Error notifications
    - conversation_message: LLM conversational messages

    Client Control Messages:
    - {"type": "ping", "timestamp": <ms>} → {"type": "pong", "timestamp": <ms>}
    - {"type": "subscribe", "event_types": [...]} → {"type": "subscribed", ...}
    - {"type": "unsubscribe", "event_types": [...]} → {"type": "unsubscribed", ...}

    Args:
        websocket: WebSocket connection instance
    """
    await websocket.accept()

    mcp_server = get_or_create_mcp_server()

    # Subscribe to MCP events
    async def event_handler(event):
        """Forward MCP events to WebSocket.

        Converts MCP events to WebSocket messages and sends them to the client.
        Handles graceful failure if the WebSocket connection is closed.
        """
        try:
            message = WebSocketMessage(
                event_type=event.event_type,
                data=event.data,
            )
            await websocket.send_json(message.model_dump())
        except Exception as e:
            # WebSocket may be closed - log for debugging
            logger.debug(f"Failed to send event to WebSocket (connection may be closed): {e}")

    mcp_server.subscribe_to_events(event_handler)

    try:
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_json()

            # Route incoming WebSocket messages
            message_type = data.get("type", "unknown")

            if message_type == "ping":
                # Health check / keep-alive
                await websocket.send_json({"type": "pong", "timestamp": data.get("timestamp")})

            elif message_type == "subscribe":
                # Client wants to subscribe to specific event types
                # (Currently all events are sent; this is for future filtering)
                event_types = data.get("event_types", [])
                logger.debug(f"Client subscribing to events: {event_types}")
                await websocket.send_json({"type": "subscribed", "event_types": event_types})

            elif message_type == "unsubscribe":
                # Client wants to unsubscribe from specific event types
                # (Currently all events are sent; this is for future filtering)
                event_types = data.get("event_types", [])
                logger.debug(f"Client unsubscribing from events: {event_types}")
                await websocket.send_json({"type": "unsubscribed", "event_types": event_types})

            else:
                # Unknown message type - log and acknowledge
                logger.warning(f"Unknown WebSocket message type: {message_type}")
                await websocket.send_json({"type": "error", "message": f"Unknown message type: {message_type}"})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
        # Clean up subscription
        try:
            mcp_server.unsubscribe_from_events(event_handler)
        except Exception as e:
            # Log at warning level since cleanup failure could indicate memory leak
            logger.warning(f"Error unsubscribing from events (potential memory leak): {e}", exc_info=True)
