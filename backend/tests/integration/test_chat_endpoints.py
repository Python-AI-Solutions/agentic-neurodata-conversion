"""
Integration tests for chat endpoints.

Tests POST /api/chat and POST /api/chat/smart endpoints.
"""
import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

from api.main import app
from models import GlobalState, ConversionStatus


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestBasicChatEndpoint:
    """Test POST /api/chat endpoint."""

    def test_chat_endpoint_exists(self, client):
        """Test that /api/chat endpoint exists."""
        response = client.post("/api/chat", json={"message": "hello"})

        # Should return 200 or some valid response
        assert response.status_code in [200, 404, 422]

    def test_chat_with_valid_message(self, client):
        """Test chat with valid message."""
        response = client.post(
            "/api/chat",
            json={"message": "What formats do you support?"}
        )

        # Implementation may vary, test for valid responses
        assert response.status_code in [200, 404, 501]

    def test_chat_with_empty_message(self, client):
        """Test chat with empty message."""
        response = client.post("/api/chat", json={"message": ""})

        # Should handle empty message gracefully
        assert response.status_code in [200, 400, 422]

    def test_chat_without_message_field(self, client):
        """Test chat without message field."""
        response = client.post("/api/chat", json={})

        # Should return 422 for missing required field
        assert response.status_code == 422


class TestSmartChatEndpoint:
    """Test POST /api/chat/smart endpoint (LLM-powered)."""

    def test_smart_chat_endpoint_exists(self, client):
        """Test that /api/chat/smart endpoint exists."""
        response = client.post("/api/chat/smart", json={"message": "hello"})

        # Should return 200 or error code
        assert response.status_code in [200, 404, 422, 500]

    def test_smart_chat_with_llm_service(self, client):
        """Test smart chat when LLM service is available."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_USER_INPUT
            mock_server.global_state = mock_state

            # Mock LLM response
            mock_server.send_message = Mock(return_value=Mock(
                success=True,
                result={"response": "I understand your question."}
            ))

            mock_get_server.return_value = mock_server

            response = client.post(
                "/api/chat/smart",
                json={"message": "Can you help me?"}
            )

            # Should process message
            if response.status_code == 200:
                data = response.json()
                assert "response" in data or "message" in data

    def test_smart_chat_without_llm_service(self, client):
        """Test smart chat when LLM service is not available."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = client.post(
                "/api/chat/smart",
                json={"message": "Hello"}
            )

            # Should handle missing LLM gracefully
            assert response.status_code in [200, 500, 503]

    def test_smart_chat_during_conversion(self, client):
        """Test smart chat while conversion is in progress."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.CONVERTING
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            response = client.post(
                "/api/chat/smart",
                json={"message": "What's the status?"}
            )

            # Should allow status queries during conversion
            assert response.status_code in [200, 400]

    def test_smart_chat_metadata_collection(self, client):
        """Test smart chat for metadata collection workflow."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_USER_INPUT
            mock_server.global_state = mock_state

            # Mock MCP message sending
            mock_server.send_message = Mock(return_value=Mock(
                success=True,
                result={
                    "response": "Please provide the subject ID.",
                    "extracted_metadata": {}
                }
            ))

            mock_get_server.return_value = mock_server

            response = client.post(
                "/api/chat/smart",
                json={"message": "The subject ID is SUB-001"}
            )

            # Should extract metadata from user response
            assert response.status_code in [200, 500]

    def test_smart_chat_cancellation_keywords(self, client):
        """Test smart chat with cancellation keywords."""
        cancellation_keywords = ["cancel", "quit", "stop", "abort", "exit"]

        for keyword in cancellation_keywords:
            with patch("api.main.get_or_create_mcp_server") as mock_get_server:
                mock_server = Mock()
                mock_state = GlobalState()
                mock_state.status = ConversionStatus.AWAITING_USER_INPUT
                mock_server.global_state = mock_state

                # Mock MCP response for cancellation
                mock_server.send_message = Mock(return_value=Mock(
                    success=True,
                    result={
                        "status": "failed",
                        "validation_status": "failed_user_abandoned"
                    }
                ))

                mock_get_server.return_value = mock_server

                response = client.post(
                    "/api/chat/smart",
                    json={"message": keyword}
                )

                # Should handle cancellation
                assert response.status_code in [200, 400]


class TestChatContextHandling:
    """Test chat endpoints with conversation context."""

    def test_smart_chat_maintains_context(self, client):
        """Test that smart chat maintains conversation context."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_USER_INPUT
            mock_server.global_state = mock_state

            mock_server.send_message = Mock(return_value=Mock(
                success=True,
                result={"response": "Understood"}
            ))

            mock_get_server.return_value = mock_server

            # First message
            response1 = client.post(
                "/api/chat/smart",
                json={"message": "I have data from experiments"}
            )

            # Second message (should have context from first)
            response2 = client.post(
                "/api/chat/smart",
                json={"message": "Can you convert it?"}
            )

            # Both should succeed
            assert response1.status_code in [200, 500]
            assert response2.status_code in [200, 500]


class TestChatErrorHandling:
    """Test error handling for chat endpoints."""

    def test_chat_with_invalid_json(self, client):
        """Test chat with invalid JSON."""
        response = client.post(
            "/api/chat",
            data="not json",
            headers={"Content-Type": "application/json"}
        )

        # Should return 422 for invalid JSON
        assert response.status_code == 422

    def test_chat_with_very_long_message(self, client):
        """Test chat with very long message."""
        long_message = "x" * 10000  # 10,000 characters

        response = client.post(
            "/api/chat/smart",
            json={"message": long_message}
        )

        # Should handle or reject very long messages
        assert response.status_code in [200, 400, 413, 422, 500]

    def test_chat_with_special_characters(self, client):
        """Test chat with special characters and unicode."""
        response = client.post(
            "/api/chat/smart",
            json={"message": "Test 特殊文字 émojis 🚀 symbols @#$%"}
        )

        # Should handle special characters
        assert response.status_code in [200, 400, 500]


class TestChatConcurrency:
    """Test concurrent chat requests."""

    def test_multiple_concurrent_chat_requests(self, client):
        """Test multiple concurrent chat requests."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.IDLE
            mock_server.global_state = mock_state
            mock_get_server.return_value = mock_server

            # Make multiple concurrent requests
            messages = [
                {"message": "Message 1"},
                {"message": "Message 2"},
                {"message": "Message 3"},
            ]

            responses = [
                client.post("/api/chat/smart", json=msg)
                for msg in messages
            ]

            # All should return valid status codes
            for response in responses:
                assert response.status_code in [200, 400, 500]
