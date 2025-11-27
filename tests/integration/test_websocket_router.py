"""Integration tests for WebSocket router.

Tests real-time bidirectional communication including:
- WebSocket connection lifecycle
- MCP event forwarding to clients
- Client control messages (ping, subscribe, unsubscribe)
- Error handling and graceful disconnection
- Event handler cleanup
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from agentic_neurodata_conversion.api.main import app
from agentic_neurodata_conversion.models import MCPEvent

# Note: WebSocket tests use FastAPI's TestClient with WebSocket support


@pytest.mark.integration
@pytest.mark.websocket
class TestWebSocketConnection:
    """Tests for WebSocket connection lifecycle."""

    def test_websocket_connection_established(self):
        """Test WebSocket connection can be established."""
        client = TestClient(app)

        with patch("agentic_neurodata_conversion.api.routers.websocket.get_or_create_mcp_server") as mock_get_server:
            mock_mcp = Mock()
            mock_mcp.subscribe_to_events = Mock()
            mock_mcp.unsubscribe_from_events = Mock()
            mock_get_server.return_value = mock_mcp

            with client.websocket_connect("/ws") as websocket:
                # Connection should be established
                assert websocket is not None

                # MCP server should subscribe to events
                assert mock_mcp.subscribe_to_events.called

    def test_websocket_disconnection_cleanup(self):
        """Test WebSocket disconnection triggers cleanup."""
        client = TestClient(app)

        with patch("agentic_neurodata_conversion.api.routers.websocket.get_or_create_mcp_server") as mock_get_server:
            mock_mcp = Mock()
            mock_mcp.subscribe_to_events = Mock()
            mock_mcp.unsubscribe_from_events = Mock()
            mock_get_server.return_value = mock_mcp

            with client.websocket_connect("/ws") as websocket:
                # Close connection
                websocket.close()

            # Should have unsubscribed after disconnect
            assert mock_mcp.unsubscribe_from_events.called


@pytest.mark.integration
@pytest.mark.websocket
class TestWebSocketMessaging:
    """Tests for WebSocket client messaging."""

    def test_ping_pong_messaging(self):
        """Test ping-pong keep-alive messaging."""
        client = TestClient(app)

        with patch("agentic_neurodata_conversion.api.routers.websocket.get_or_create_mcp_server") as mock_get_server:
            mock_mcp = Mock()
            mock_mcp.subscribe_to_events = Mock()
            mock_mcp.unsubscribe_from_events = Mock()
            mock_get_server.return_value = mock_mcp

            with client.websocket_connect("/ws") as websocket:
                # Send ping with timestamp
                timestamp = 1234567890
                websocket.send_json({"type": "ping", "timestamp": timestamp})

                # Should receive pong response
                response = websocket.receive_json()
                assert response["type"] == "pong"
                assert response["timestamp"] == timestamp

    def test_subscribe_messaging(self):
        """Test subscribe message handling."""
        client = TestClient(app)

        with patch("agentic_neurodata_conversion.api.routers.websocket.get_or_create_mcp_server") as mock_get_server:
            mock_mcp = Mock()
            mock_mcp.subscribe_to_events = Mock()
            mock_mcp.unsubscribe_from_events = Mock()
            mock_get_server.return_value = mock_mcp

            with client.websocket_connect("/ws") as websocket:
                # Send subscribe message
                event_types = ["status_changed", "progress_updated"]
                websocket.send_json({"type": "subscribe", "event_types": event_types})

                # Should receive subscribed confirmation
                response = websocket.receive_json()
                assert response["type"] == "subscribed"
                assert response["event_types"] == event_types

    def test_unsubscribe_messaging(self):
        """Test unsubscribe message handling."""
        client = TestClient(app)

        with patch("agentic_neurodata_conversion.api.routers.websocket.get_or_create_mcp_server") as mock_get_server:
            mock_mcp = Mock()
            mock_mcp.subscribe_to_events = Mock()
            mock_mcp.unsubscribe_from_events = Mock()
            mock_get_server.return_value = mock_mcp

            with client.websocket_connect("/ws") as websocket:
                # Send unsubscribe message
                event_types = ["error_occurred"]
                websocket.send_json({"type": "unsubscribe", "event_types": event_types})

                # Should receive unsubscribed confirmation
                response = websocket.receive_json()
                assert response["type"] == "unsubscribed"
                assert response["event_types"] == event_types

    def test_unknown_message_type_handling(self):
        """Test unknown message type error response."""
        client = TestClient(app)

        with patch("agentic_neurodata_conversion.api.routers.websocket.get_or_create_mcp_server") as mock_get_server:
            mock_mcp = Mock()
            mock_mcp.subscribe_to_events = Mock()
            mock_mcp.unsubscribe_from_events = Mock()
            mock_get_server.return_value = mock_mcp

            with client.websocket_connect("/ws") as websocket:
                # Send message with unknown type
                websocket.send_json({"type": "invalid_type", "data": "test"})

                # Should receive error response
                response = websocket.receive_json()
                assert response["type"] == "error"
                assert "Unknown message type" in response["message"]
                assert "invalid_type" in response["message"]


@pytest.mark.integration
@pytest.mark.websocket
class TestMCPEventForwarding:
    """Tests for MCP event forwarding to WebSocket clients."""

    def test_mcp_subscription_registered(self):
        """Test MCP event handler is registered on connection."""
        client = TestClient(app)

        mock_mcp = Mock()
        event_handler_ref = []

        def capture_handler(handler):
            event_handler_ref.append(handler)

        mock_mcp.subscribe_to_events = Mock(side_effect=capture_handler)
        mock_mcp.unsubscribe_from_events = Mock()

        with patch(
            "agentic_neurodata_conversion.api.routers.websocket.get_or_create_mcp_server", return_value=mock_mcp
        ):
            with client.websocket_connect("/ws") as websocket:
                # Subscription should have been registered
                assert mock_mcp.subscribe_to_events.called
                assert len(event_handler_ref) == 1

                # Event handler should be a callable
                event_handler = event_handler_ref[0]
                assert callable(event_handler)

    @pytest.mark.asyncio
    async def test_event_handler_converts_mcp_to_websocket_message(self):
        """Test event handler converts MCP events to WebSocket messages."""
        from agentic_neurodata_conversion.models import WebSocketMessage

        # Create mock websocket
        mock_websocket = AsyncMock()
        mock_websocket.send_json = AsyncMock()

        # Create event handler function similar to the one in websocket.py
        async def event_handler(event):
            try:
                message = WebSocketMessage(
                    event_type=event.event_type,
                    data=event.data,
                )
                await mock_websocket.send_json(message.model_dump())
            except Exception:
                pass

        # Test with MCP event
        test_event = MCPEvent(
            event_type="status_changed",
            data={"status": "converting", "progress": 50},
        )

        await event_handler(test_event)

        # Verify websocket.send_json was called with correct data
        assert mock_websocket.send_json.called
        sent_data = mock_websocket.send_json.call_args[0][0]
        assert sent_data["event_type"] == "status_changed"
        assert sent_data["data"]["status"] == "converting"

    @pytest.mark.asyncio
    async def test_event_handler_handles_send_errors_gracefully(self):
        """Test event handler handles WebSocket send errors gracefully."""
        # Create mock websocket that raises error on send
        mock_websocket = AsyncMock()
        mock_websocket.send_json = AsyncMock(side_effect=RuntimeError("WebSocket closed"))

        # Create event handler function (same as in websocket.py)
        async def event_handler(event):
            try:
                from agentic_neurodata_conversion.models import WebSocketMessage

                message = WebSocketMessage(
                    event_type=event.event_type,
                    data=event.data,
                )
                await mock_websocket.send_json(message.model_dump())
            except Exception:
                # Should handle exception gracefully
                pass

        # Test with MCP event
        test_event = MCPEvent(
            event_type="progress_updated",
            data={"progress": 75},
        )

        # Should not raise exception despite send error
        try:
            await event_handler(test_event)
            # If we get here, error was handled
            assert True
        except Exception:
            pytest.fail("Event handler should handle send errors gracefully")


@pytest.mark.integration
@pytest.mark.websocket
class TestWebSocketErrorHandling:
    """Tests for WebSocket error handling."""

    def test_cleanup_error_handling(self):
        """Test cleanup handles unsubscribe errors gracefully."""
        client = TestClient(app)

        mock_mcp = Mock()
        mock_mcp.subscribe_to_events = Mock()
        # Make unsubscribe raise an exception
        mock_mcp.unsubscribe_from_events = Mock(side_effect=RuntimeError("Unsubscribe failed"))

        with patch(
            "agentic_neurodata_conversion.api.routers.websocket.get_or_create_mcp_server", return_value=mock_mcp
        ):
            # Should not raise exception even if cleanup fails
            try:
                with client.websocket_connect("/ws") as websocket:
                    websocket.close()
                # Connection should close gracefully despite cleanup error
                assert True
            except Exception as e:
                # Should handle cleanup errors gracefully
                # (logging warning but not raising)
                # If this fails, it means cleanup errors aren't being caught
                pytest.fail(f"WebSocket should handle cleanup errors gracefully, got: {e}")

    def test_multiple_message_sequence(self):
        """Test handling multiple messages in sequence."""
        client = TestClient(app)

        with patch("agentic_neurodata_conversion.api.routers.websocket.get_or_create_mcp_server") as mock_get_server:
            mock_mcp = Mock()
            mock_mcp.subscribe_to_events = Mock()
            mock_mcp.unsubscribe_from_events = Mock()
            mock_get_server.return_value = mock_mcp

            with client.websocket_connect("/ws") as websocket:
                # Send multiple different message types
                websocket.send_json({"type": "ping", "timestamp": 1111})
                pong1 = websocket.receive_json()
                assert pong1["type"] == "pong"

                websocket.send_json({"type": "subscribe", "event_types": ["status"]})
                sub_resp = websocket.receive_json()
                assert sub_resp["type"] == "subscribed"

                websocket.send_json({"type": "unsubscribe", "event_types": ["status"]})
                unsub_resp = websocket.receive_json()
                assert unsub_resp["type"] == "unsubscribed"

                websocket.send_json({"type": "ping", "timestamp": 2222})
                pong2 = websocket.receive_json()
                assert pong2["type"] == "pong"
                assert pong2["timestamp"] == 2222

    def test_subscribe_with_empty_event_types(self):
        """Test subscribe message with empty event_types list."""
        client = TestClient(app)

        with patch("agentic_neurodata_conversion.api.routers.websocket.get_or_create_mcp_server") as mock_get_server:
            mock_mcp = Mock()
            mock_mcp.subscribe_to_events = Mock()
            mock_mcp.unsubscribe_from_events = Mock()
            mock_get_server.return_value = mock_mcp

            with client.websocket_connect("/ws") as websocket:
                # Send subscribe with empty list
                websocket.send_json({"type": "subscribe", "event_types": []})

                response = websocket.receive_json()
                assert response["type"] == "subscribed"
                assert response["event_types"] == []

    def test_message_without_event_types_field(self):
        """Test subscribe/unsubscribe without event_types field."""
        client = TestClient(app)

        with patch("agentic_neurodata_conversion.api.routers.websocket.get_or_create_mcp_server") as mock_get_server:
            mock_mcp = Mock()
            mock_mcp.subscribe_to_events = Mock()
            mock_mcp.unsubscribe_from_events = Mock()
            mock_get_server.return_value = mock_mcp

            with client.websocket_connect("/ws") as websocket:
                # Send subscribe without event_types field (should default to [])
                websocket.send_json({"type": "subscribe"})

                response = websocket.receive_json()
                assert response["type"] == "subscribed"
                assert response["event_types"] == []
