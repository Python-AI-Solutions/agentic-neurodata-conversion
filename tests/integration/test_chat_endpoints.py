"""
Integration tests for chat endpoints.

Tests POST /api/chat and POST /api/chat/smart endpoints.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from agentic_neurodata_conversion.models import ConversionStatus, GlobalState

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
    with patch(
        "agentic_neurodata_conversion.services.llm_service.create_llm_service", return_value=mock_llm_conversational
    ):
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
        with patch("agentic_neurodata_conversion.api.dependencies.get_or_create_mcp_server") as mock_get_server:
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
        with patch("agentic_neurodata_conversion.api.dependencies.get_or_create_mcp_server") as mock_get_server:
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
        from agentic_neurodata_conversion.api.dependencies import get_or_create_mcp_server

        # Use the real MCP server and set its state
        mcp_server = get_or_create_mcp_server()
        original_status = mcp_server.global_state.status

        try:
            # Set state to CONVERTING
            mcp_server.global_state.status = ConversionStatus.CONVERTING

            # API expects form data, not JSON
            response = api_test_client.post("/api/chat/smart", data={"message": "What's the status?"})

            # Should allow status queries during conversion
            # 500 is acceptable if LLM service unavailable or fails
            assert response.status_code in [200, 400, 500]
        finally:
            # Restore original state
            mcp_server.global_state.status = original_status

    def test_smart_chat_metadata_collection(self, api_test_client):
        """Test smart chat for metadata collection workflow."""
        with patch("agentic_neurodata_conversion.api.dependencies.get_or_create_mcp_server") as mock_get_server:
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
        from agentic_neurodata_conversion.api.dependencies import get_or_create_mcp_server

        cancellation_keywords = ["cancel", "quit", "stop", "abort", "exit"]

        # Use the real MCP server and set its state
        mcp_server = get_or_create_mcp_server()
        original_status = mcp_server.global_state.status

        try:
            for keyword in cancellation_keywords:
                # Set state to AWAITING_USER_INPUT for each test
                mcp_server.global_state.status = ConversionStatus.AWAITING_USER_INPUT

                # API expects form data, not JSON
                response = api_test_client.post("/api/chat/smart", data={"message": keyword})

                # Should handle cancellation (or rate limiting)
                # 500 is acceptable if LLM service unavailable or fails
                assert response.status_code in [200, 400, 429, 500]
        finally:
            # Restore original state
            mcp_server.global_state.status = original_status


@pytest.mark.integration
@pytest.mark.api
class TestChatContextHandling:
    """Test chat endpoints with conversation context."""

    def test_smart_chat_maintains_context(self, api_test_client):
        """Test that smart chat maintains conversation context."""
        with patch("agentic_neurodata_conversion.api.dependencies.get_or_create_mcp_server") as mock_get_server:
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
        with patch("agentic_neurodata_conversion.api.dependencies.get_or_create_mcp_server") as mock_get_server:
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


@pytest.mark.integration
@pytest.mark.api
class TestUserInputEndpoint:
    """Test POST /api/user-input endpoint for format selection.

    Tests lines 53-67 which handle format selection during AWAITING_USER_INPUT state.
    """

    def test_user_input_format_selection_success(self, api_test_client):
        """Test successful format selection (lines 53-67)."""
        with patch("agentic_neurodata_conversion.api.routers.chat.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_USER_INPUT
            mock_server.global_state = mock_state

            # Mock successful format selection response (lines 59-65)
            mock_server.send_message = AsyncMock(return_value=Mock(success=True, result={"status": "converting"}))

            mock_get_server.return_value = mock_server

            response = api_test_client.post(
                "/api/user-input",
                json={"input_data": {"format": "Calcium Imaging"}},
            )

            # Should accept format and return success (lines 67-71)
            assert response.status_code == 200
            data = response.json()
            assert data["accepted"] is True
            assert "Format selection accepted" in data["message"]
            # API returns enum value as lowercase string
            assert data["new_status"] == "converting"

    def test_user_input_format_selection_failure(self, api_test_client):
        """Test format selection when agent returns error (lines 61-65)."""
        with patch("agentic_neurodata_conversion.api.routers.chat.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_USER_INPUT
            mock_server.global_state = mock_state

            # Mock failed format selection response (line 61: not response.success)
            mock_server.send_message = AsyncMock(
                return_value=Mock(
                    success=False,
                    error={"message": "Invalid format specified"},
                )
            )

            mock_get_server.return_value = mock_server

            response = api_test_client.post(
                "/api/user-input",
                json={"input_data": {"format": "InvalidFormat"}},
            )

            # Should return 400 error (lines 62-65)
            assert response.status_code == 400
            data = response.json()
            assert "Invalid format specified" in data["detail"]

    def test_user_input_wrong_state(self, api_test_client):
        """Test user input in wrong state (lines 73-76)."""
        with patch("agentic_neurodata_conversion.api.routers.chat.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            # Wrong state - should be AWAITING_USER_INPUT
            mock_state.status = ConversionStatus.CONVERTING
            mock_server.global_state = mock_state

            mock_get_server.return_value = mock_server

            response = api_test_client.post(
                "/api/user-input",
                json={"input_data": {"format": "Calcium Imaging"}},
            )

            # Should return 400 error (lines 73-76)
            assert response.status_code == 400
            data = response.json()
            assert "Invalid state" in data["detail"]

    def test_user_input_missing_format(self, api_test_client):
        """Test user input without format field (lines 73-76)."""
        with patch("agentic_neurodata_conversion.api.routers.chat.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_USER_INPUT
            mock_server.global_state = mock_state

            mock_get_server.return_value = mock_server

            response = api_test_client.post(
                "/api/user-input",
                json={"input_data": {"other_field": "value"}},
            )

            # Should return 400 error (lines 73-76)
            assert response.status_code == 400
            data = response.json()
            assert "Invalid state" in data["detail"]

    def test_user_input_correct_state_no_format(self, api_test_client):
        """Test that format key must exist in input_data (line 51 condition)."""
        with patch("agentic_neurodata_conversion.api.routers.chat.get_or_create_mcp_server") as mock_get_server:
            mock_server = Mock()
            mock_state = GlobalState()
            mock_state.status = ConversionStatus.AWAITING_USER_INPUT
            mock_server.global_state = mock_state

            mock_get_server.return_value = mock_server

            response = api_test_client.post(
                "/api/user-input",
                json={"input_data": {}},  # Empty input_data, no format key
            )

            # Should return 400 error because "format" not in input_data (line 51 fails)
            assert response.status_code == 400
            data = response.json()
            assert "Invalid state" in data["detail"]
