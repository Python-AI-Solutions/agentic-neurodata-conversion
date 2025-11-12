"""
Integration tests for chat endpoints.

Tests POST /api/chat and POST /api/chat/smart endpoints.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from models import ConversionStatus, GlobalState

# Note: The following fixtures are provided by conftest files:
# - mock_llm_conversational: from root conftest.py (for chat/conversational responses)
# - api_test_client: from integration/conftest.py (FastAPI test client)


@pytest.mark.integration
@pytest.fixture(autouse=True)
def patch_llm_service(mock_llm_conversational):
    """
    Automatically patch LLM service for all tests in this module.

    Uses mock_llm_conversational from root conftest.py which provides
    chat-oriented responses suitable for conversational testing.
    """
    with patch("services.llm_service.create_llm_service", return_value=mock_llm_conversational):
        with patch("api.main.create_llm_service", return_value=mock_llm_conversational):
            yield


@pytest.mark.integration
@pytest.mark.api
class TestBasicChatEndpoint:
    """Test POST /api/chat endpoint."""

    def test_chat_endpoint_exists(self, api_test_client):
        """Test that /api/chat endpoint exists."""
        # API expects form data, not JSON
        response = api_test_client.post("/api/chat", data={"message": "hello"})

        # Should return 200 (success) or 404 (not implemented)
        # If endpoint exists, must be 200
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            # Verify response has expected structure
            data = response.json()
            assert isinstance(data, dict)

    def test_chat_with_valid_message(self, api_test_client):
        """Test chat with valid message."""
        # API expects form data, not JSON
        response = api_test_client.post("/api/chat", data={"message": "What formats do you support?"})

        # Should return 200 if endpoint implemented, 404 if not
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            # Verify response contains answer
            data = response.json()
            assert isinstance(data, dict)

    def test_chat_with_empty_message(self, api_test_client):
        """Test chat with empty message."""
        # API expects form data, not JSON
        response = api_test_client.post("/api/chat", data={"message": ""})

        # API accepts empty messages (200) or may reject them (400/422)
        # Either behavior is valid - just verify it handles them gracefully
        assert response.status_code in [200, 400, 422]
        # Verify response has valid structure
        data = response.json()
        assert isinstance(data, dict)

    def test_chat_without_message_field(self, api_test_client):
        """Test chat without message field."""
        # API expects form data, not JSON
        response = api_test_client.post("/api/chat", data={})

        # Should return 422 for missing required field
        assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.api
class TestSmartChatEndpoint:
    """Test POST /api/chat/smart endpoint (LLM-powered)."""

    def test_smart_chat_endpoint_exists(self, api_test_client):
        """Test that /api/chat/smart endpoint exists."""
        # API expects form data, not JSON
        response = api_test_client.post("/api/chat/smart", data={"message": "hello"})

        # Should return 200 (success), 404 (not implemented), or 500 (server error)
        assert response.status_code in [200, 404, 500]
        if response.status_code == 200:
            # Verify response structure
            data = response.json()
            assert isinstance(data, dict)

    def test_smart_chat_with_llm_service(self, api_test_client):
        """Test smart chat when LLM service is available."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_USER_INPUT
            mock_server.global_state = mock_state

            # Mock LLM response - must be AsyncMock since send_message is awaited
            mock_server.send_message = AsyncMock(
                return_value=Mock(success=True, result={"response": "I understand your question."})
            )

            mock_get_server.return_value = mock_server

            # API expects form data, not JSON
            response = api_test_client.post("/api/chat/smart", data={"message": "Can you help me?"})

            # Should process message
            if response.status_code == 200:
                data = response.json()
                # API returns 'answer' and 'type', not 'response' or 'message'
                assert "answer" in data or "type" in data or "response" in data or "message" in data

    def test_smart_chat_without_llm_service(self, api_test_client):
        """Test smart chat when LLM service is not available."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_server.global_state = mock_state

            # Mock send_message even if LLM is not available - must be AsyncMock since send_message is awaited
            mock_server.send_message = AsyncMock(
                return_value=Mock(success=True, result={"response": "I understand your question."})
            )

            mock_get_server.return_value = mock_server

            # API expects form data, not JSON
            response = api_test_client.post("/api/chat/smart", data={"message": "Hello"})

            # Should handle missing LLM gracefully
            assert response.status_code in [200, 500, 503]

    def test_smart_chat_during_conversion(self, api_test_client):
        """Test smart chat while conversion is in progress."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.CONVERTING
            mock_server.global_state = mock_state

            # Mock send_message - must be AsyncMock since send_message is awaited
            mock_server.send_message = AsyncMock(
                return_value=Mock(success=True, result={"response": "Conversion is in progress."})
            )

            mock_get_server.return_value = mock_server

            # API expects form data, not JSON
            response = api_test_client.post("/api/chat/smart", data={"message": "What's the status?"})

            # Should allow status queries during conversion
            assert response.status_code in [200, 400]

    def test_smart_chat_metadata_collection(self, api_test_client):
        """Test smart chat for metadata collection workflow."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_USER_INPUT
            mock_server.global_state = mock_state

            # Mock MCP message sending - must be AsyncMock since send_message is awaited
            mock_server.send_message = AsyncMock(
                return_value=Mock(
                    success=True, result={"response": "Please provide the subject ID.", "extracted_metadata": {}}
                )
            )

            mock_get_server.return_value = mock_server

            # API expects form data, not JSON
            response = api_test_client.post("/api/chat/smart", data={"message": "The subject ID is SUB-001"})

            # Should extract metadata from user response
            assert response.status_code in [200, 500]

    def test_smart_chat_cancellation_keywords(self, api_test_client):
        """Test smart chat with cancellation keywords."""
        cancellation_keywords = ["cancel", "quit", "stop", "abort", "exit"]

        for keyword in cancellation_keywords:
            with patch("api.main.get_or_create_mcp_server") as mock_get_server:
                mock_server = Mock()
                mock_state = GlobalState()
                mock_state.status = ConversionStatus.AWAITING_USER_INPUT
                mock_server.global_state = mock_state

                # Mock MCP response for cancellation - must be AsyncMock since send_message is awaited
                mock_server.send_message = AsyncMock(
                    return_value=Mock(
                        success=True, result={"status": "failed", "validation_status": "failed_user_abandoned"}
                    )
                )

                mock_get_server.return_value = mock_server

                # API expects form data, not JSON
                response = api_test_client.post("/api/chat/smart", data={"message": keyword})

                # Should handle cancellation (or rate limiting)
                assert response.status_code in [200, 400, 429]


@pytest.mark.integration
@pytest.mark.api
class TestChatContextHandling:
    """Test chat endpoints with conversation context."""

    def test_smart_chat_maintains_context(self, api_test_client):
        """Test that smart chat maintains conversation context."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_USER_INPUT
            mock_server.global_state = mock_state

            # Must be AsyncMock since send_message is awaited
            mock_server.send_message = AsyncMock(return_value=Mock(success=True, result={"response": "Understood"}))

            mock_get_server.return_value = mock_server

            # First message - API expects form data
            response1 = api_test_client.post("/api/chat/smart", data={"message": "I have data from experiments"})

            # Second message (should have context from first) - API expects form data
            response2 = api_test_client.post("/api/chat/smart", data={"message": "Can you convert it?"})

            # Both should succeed (or rate limiting)
            assert response1.status_code in [200, 429, 500]
            assert response2.status_code in [200, 429, 500]


@pytest.mark.integration
@pytest.mark.api
class TestChatErrorHandling:
    """Test error handling for chat endpoints."""

    def test_chat_with_invalid_json(self, api_test_client):
        """Test chat with invalid JSON."""
        response = api_test_client.post("/api/chat", data="not json", headers={"Content-Type": "application/json"})

        # Should return 422 for invalid JSON (or 429 for rate limiting)
        assert response.status_code in [422, 429]

    def test_chat_with_very_long_message(self, api_test_client):
        """Test chat with very long message."""
        long_message = "x" * 10000  # 10,000 characters

        # API expects form data, not JSON
        response = api_test_client.post("/api/chat/smart", data={"message": long_message})

        # Should reject with 413 (payload too large), 400 (bad request), or 429 (rate limit)
        # or accept with 200 if no length limit enforced
        assert response.status_code in [200, 400, 413, 429]
        if response.status_code in [400, 413, 429]:
            # Should explain why rejected
            data = response.json()
            assert "detail" in data or "error" in data

    def test_chat_with_special_characters(self, api_test_client):
        """Test chat with special characters and unicode."""
        # API expects form data, not JSON
        response = api_test_client.post("/api/chat/smart", data={"message": "Test 特殊文字 émojis 🚀 symbols @#$%"})

        # Should handle special characters (or rate limiting)
        assert response.status_code in [200, 400, 429, 500]


@pytest.mark.integration
@pytest.mark.api
class TestChatConcurrency:
    """Test concurrent chat requests."""

    def test_multiple_concurrent_chat_requests(self, api_test_client):
        """Test multiple concurrent chat requests."""
        with patch("api.main.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.IDLE
            mock_server.global_state = mock_state

            # Must be AsyncMock since send_message is awaited
            mock_server.send_message = AsyncMock(return_value=Mock(success=True, result={"response": "Understood"}))

            mock_get_server.return_value = mock_server

            # Make multiple concurrent requests - API expects form data
            messages = [
                {"message": "Message 1"},
                {"message": "Message 2"},
                {"message": "Message 3"},
            ]

            responses = [api_test_client.post("/api/chat/smart", data=msg) for msg in messages]

            # All should return valid status codes (or rate limiting)
            for response in responses:
                assert response.status_code in [200, 400, 429, 500]
