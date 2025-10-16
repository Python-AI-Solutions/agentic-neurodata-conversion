"""
Unit tests for BaseAgent abstract class.

Tests cover:
- BaseAgent initialization with Anthropic provider
- BaseAgent initialization with OpenAI provider
- register_with_server sends registration request
- get_session_context retrieves session from server
- update_session_context sends updates to server
- call_llm with Anthropic provider
- call_llm with OpenAI provider
- call_llm retry logic for rate limits
- call_llm exponential backoff
- call_llm fails after max retries
- create_agent_server creates FastAPI app
- Agent HTTP server has /mcp/message endpoint
- Agent HTTP server has /health endpoint
- get_capabilities is abstract (must override)
- handle_message is abstract (must override)
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

from anthropic import APIError as AnthropicAPIError
from anthropic import RateLimitError as AnthropicRateLimitError
from fastapi.testclient import TestClient
from httpx import Response
from openai import RateLimitError as OpenAIRateLimitError
import pytest
import respx

from agentic_neurodata_conversion.agents.base_agent import BaseAgent
from agentic_neurodata_conversion.config import AgentConfig
from agentic_neurodata_conversion.models.mcp_message import MCPMessage
from agentic_neurodata_conversion.models.session_context import (
    SessionContext,
    WorkflowStage,
)


# Concrete implementation for testing abstract class
class ConcreteAgent(BaseAgent):
    """Concrete implementation of BaseAgent for testing."""

    def get_capabilities(self) -> list[str]:
        """Return test capabilities."""
        return ["test_capability"]

    async def handle_message(self, message: MCPMessage) -> dict:
        """Handle test message."""
        return {"status": "success", "message": "Test message handled"}


class TestBaseAgentInitialization:
    """Test BaseAgent initialization."""

    def test_base_agent_initialization_with_anthropic_provider(self) -> None:
        """Test BaseAgent initializes correctly with Anthropic provider."""
        config = AgentConfig(
            agent_name="test_agent",
            agent_type="conversation",
            llm_provider="anthropic",
            llm_model="claude-3-5-sonnet-20241022",
            llm_api_key="sk-ant-test-key",
            temperature=0.7,
            max_tokens=4096,
            mcp_server_url="http://localhost:3000",
            agent_port=3001,
        )

        with patch("agentic_neurodata_conversion.agents.base_agent.AsyncAnthropic"):
            agent = ConcreteAgent(config)

            assert agent.config == config
            assert agent.agent_name == "test_agent"
            assert agent.agent_type == "conversation"
            assert agent.mcp_server_url == "http://localhost:3000"
            assert agent.llm_client is not None
            assert agent.http_client is not None

    def test_base_agent_initialization_with_openai_provider(self) -> None:
        """Test BaseAgent initializes correctly with OpenAI provider."""
        config = AgentConfig(
            agent_name="test_agent",
            agent_type="conversion",
            llm_provider="openai",
            llm_model="gpt-4-turbo",
            llm_api_key="sk-test-key",
            temperature=0.3,
            max_tokens=8192,
            mcp_server_url="http://localhost:3000",
            agent_port=3002,
        )

        with patch("agentic_neurodata_conversion.agents.base_agent.AsyncOpenAI"):
            agent = ConcreteAgent(config)

            assert agent.config == config
            assert agent.agent_name == "test_agent"
            assert agent.agent_type == "conversion"
            assert agent.llm_client is not None

    def test_base_agent_initialization_raises_error_for_unsupported_provider(
        self,
    ) -> None:
        """Test BaseAgent raises error for unsupported LLM provider."""
        # This test would fail during config validation, not agent initialization
        # But we can test the initialization method directly
        config = AgentConfig(
            agent_name="test_agent",
            agent_type="conversation",
            llm_provider="anthropic",
            llm_model="claude-3-5-sonnet-20241022",
            llm_api_key="sk-ant-test-key",
            temperature=0.7,
            max_tokens=4096,
            mcp_server_url="http://localhost:3000",
            agent_port=3001,
        )

        with patch("agentic_neurodata_conversion.agents.base_agent.AsyncAnthropic"):
            agent = ConcreteAgent(config)
            # Manually override to test error handling
            agent.config.llm_provider = "unsupported_provider"  # type: ignore

            with pytest.raises(ValueError, match="Unsupported LLM provider"):
                agent._initialize_llm_client()


class TestMCPServerCommunication:
    """Test BaseAgent communication with MCP server."""

    @pytest.mark.asyncio
    async def test_register_with_server_sends_registration_request(self) -> None:
        """Test register_with_server sends correct HTTP POST request."""
        config = AgentConfig(
            agent_name="test_agent",
            agent_type="conversation",
            llm_provider="anthropic",
            llm_model="claude-3-5-sonnet-20241022",
            llm_api_key="sk-ant-test-key",
            temperature=0.7,
            max_tokens=4096,
            mcp_server_url="http://localhost:3000",
            agent_port=3001,
        )

        with patch("agentic_neurodata_conversion.agents.base_agent.AsyncAnthropic"):
            agent = ConcreteAgent(config)

        with respx.mock:
            route = respx.post("http://localhost:3000/internal/register_agent").mock(
                return_value=Response(
                    200,
                    json={
                        "status": "registered",
                        "agent_name": "test_agent",
                        "agent_type": "conversation",
                    },
                )
            )

            result = await agent.register_with_server()

            assert result["status"] == "registered"
            assert route.called
            # Verify request payload
            request = route.calls.last.request
            import json
            json_data = json.loads(request.content)
            assert json_data["agent_name"] == "test_agent"
            assert json_data["agent_type"] == "conversation"
            assert json_data["base_url"] == "http://0.0.0.0:3001"
            assert json_data["capabilities"] == ["test_capability"]

    @pytest.mark.asyncio
    async def test_get_session_context_retrieves_session_from_server(self) -> None:
        """Test get_session_context retrieves session context from MCP server."""
        config = AgentConfig(
            agent_name="test_agent",
            agent_type="conversation",
            llm_provider="anthropic",
            llm_model="claude-3-5-sonnet-20241022",
            llm_api_key="sk-ant-test-key",
            temperature=0.7,
            max_tokens=4096,
            mcp_server_url="http://localhost:3000",
            agent_port=3001,
        )

        with patch("agentic_neurodata_conversion.agents.base_agent.AsyncAnthropic"):
            agent = ConcreteAgent(config)

        session_data = {
            "session_id": "test-session-123",
            "workflow_stage": "initialized",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "last_updated": datetime.utcnow().isoformat() + "Z",
            "current_agent": None,
            "agent_history": [],
            "dataset_info": None,
            "metadata": None,
            "conversion_results": None,
            "validation_results": None,
            "requires_user_clarification": False,
            "clarification_prompt": None,
        }

        with respx.mock:
            respx.get(
                "http://localhost:3000/internal/sessions/test-session-123/context"
            ).mock(return_value=Response(200, json=session_data))

            context = await agent.get_session_context("test-session-123")

            assert isinstance(context, SessionContext)
            assert context.session_id == "test-session-123"
            assert context.workflow_stage == WorkflowStage.INITIALIZED

    @pytest.mark.asyncio
    async def test_update_session_context_sends_updates_to_server(self) -> None:
        """Test update_session_context sends PATCH request to MCP server."""
        config = AgentConfig(
            agent_name="test_agent",
            agent_type="conversation",
            llm_provider="anthropic",
            llm_model="claude-3-5-sonnet-20241022",
            llm_api_key="sk-ant-test-key",
            temperature=0.7,
            max_tokens=4096,
            mcp_server_url="http://localhost:3000",
            agent_port=3001,
        )

        with patch("agentic_neurodata_conversion.agents.base_agent.AsyncAnthropic"):
            agent = ConcreteAgent(config)

        updates = {
            "workflow_stage": "collecting_metadata",
            "current_agent": "test_agent",
        }

        with respx.mock:
            route = respx.patch(
                "http://localhost:3000/internal/sessions/test-session-123/context"
            ).mock(
                return_value=Response(
                    200, json={"status": "updated", "session_id": "test-session-123"}
                )
            )

            result = await agent.update_session_context("test-session-123", updates)

            assert result["status"] == "updated"
            assert route.called
            # Verify request payload
            request = route.calls.last.request
            import json
            json_data = json.loads(request.content)
            assert json_data["workflow_stage"] == "collecting_metadata"
            assert json_data["current_agent"] == "test_agent"


class TestLLMCalls:
    """Test BaseAgent LLM integration."""

    @pytest.mark.asyncio
    async def test_call_llm_with_anthropic_provider(self) -> None:
        """Test call_llm works with Anthropic provider."""
        config = AgentConfig(
            agent_name="test_agent",
            agent_type="conversation",
            llm_provider="anthropic",
            llm_model="claude-3-5-sonnet-20241022",
            llm_api_key="sk-ant-test-key",
            temperature=0.7,
            max_tokens=4096,
            mcp_server_url="http://localhost:3000",
            agent_port=3001,
        )

        # Mock Anthropic client
        mock_anthropic = Mock()
        mock_messages = AsyncMock()
        mock_anthropic.messages = mock_messages

        # Mock response
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "This is a test response from Claude"
        mock_response.content = [mock_content]
        mock_messages.create.return_value = mock_response

        with patch(
            "agentic_neurodata_conversion.agents.base_agent.AsyncAnthropic",
            return_value=mock_anthropic,
        ):
            agent = ConcreteAgent(config)

            response = await agent.call_llm(
                prompt="Test prompt", system_message="You are a helpful assistant"
            )

            assert response == "This is a test response from Claude"
            mock_messages.create.assert_called_once()
            call_kwargs = mock_messages.create.call_args[1]
            assert call_kwargs["model"] == "claude-3-5-sonnet-20241022"
            assert call_kwargs["max_tokens"] == 4096
            assert call_kwargs["temperature"] == 0.7
            assert call_kwargs["system"] == "You are a helpful assistant"
            assert call_kwargs["messages"][0]["role"] == "user"
            assert call_kwargs["messages"][0]["content"] == "Test prompt"

    @pytest.mark.asyncio
    async def test_call_llm_with_openai_provider(self) -> None:
        """Test call_llm works with OpenAI provider."""
        config = AgentConfig(
            agent_name="test_agent",
            agent_type="conversion",
            llm_provider="openai",
            llm_model="gpt-4-turbo",
            llm_api_key="sk-test-key",
            temperature=0.3,
            max_tokens=8192,
            mcp_server_url="http://localhost:3000",
            agent_port=3002,
        )

        # Mock OpenAI client
        mock_openai = Mock()
        mock_chat = Mock()
        mock_completions = AsyncMock()
        mock_openai.chat = mock_chat
        mock_chat.completions = mock_completions

        # Mock response
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "This is a test response from GPT-4"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_completions.create.return_value = mock_response

        with patch(
            "agentic_neurodata_conversion.agents.base_agent.AsyncOpenAI",
            return_value=mock_openai,
        ):
            agent = ConcreteAgent(config)

            response = await agent.call_llm(
                prompt="Test prompt", system_message="You are a helpful assistant"
            )

            assert response == "This is a test response from GPT-4"
            mock_completions.create.assert_called_once()
            call_kwargs = mock_completions.create.call_args[1]
            assert call_kwargs["model"] == "gpt-4-turbo"
            assert call_kwargs["max_tokens"] == 8192
            assert call_kwargs["temperature"] == 0.3
            assert len(call_kwargs["messages"]) == 2
            assert call_kwargs["messages"][0]["role"] == "system"
            assert call_kwargs["messages"][0]["content"] == "You are a helpful assistant"
            assert call_kwargs["messages"][1]["role"] == "user"
            assert call_kwargs["messages"][1]["content"] == "Test prompt"

    @pytest.mark.asyncio
    async def test_call_llm_retry_logic_for_rate_limits_anthropic(self) -> None:
        """Test call_llm retries with exponential backoff for Anthropic rate limits."""
        config = AgentConfig(
            agent_name="test_agent",
            agent_type="conversation",
            llm_provider="anthropic",
            llm_model="claude-3-5-sonnet-20241022",
            llm_api_key="sk-ant-test-key",
            temperature=0.7,
            max_tokens=4096,
            mcp_server_url="http://localhost:3000",
            agent_port=3001,
        )

        # Mock Anthropic client that fails twice then succeeds
        mock_anthropic = Mock()
        mock_messages = AsyncMock()
        mock_anthropic.messages = mock_messages

        # Mock response
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "Success after retries"
        mock_response.content = [mock_content]

        # Fail twice with rate limit, then succeed
        mock_messages.create.side_effect = [
            AnthropicRateLimitError("Rate limit exceeded", response=Mock(), body=None),
            AnthropicRateLimitError("Rate limit exceeded", response=Mock(), body=None),
            mock_response,
        ]

        with patch(
            "agentic_neurodata_conversion.agents.base_agent.AsyncAnthropic",
            return_value=mock_anthropic,
        ):
            agent = ConcreteAgent(config)

            # Mock asyncio.sleep to speed up test
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                response = await agent.call_llm(prompt="Test prompt")

                assert response == "Success after retries"
                assert mock_messages.create.call_count == 3
                assert mock_sleep.call_count == 2
                # Verify exponential backoff: 2^0=1s, 2^1=2s
                assert mock_sleep.call_args_list[0][0][0] == 1  # 2^0
                assert mock_sleep.call_args_list[1][0][0] == 2  # 2^1

    @pytest.mark.asyncio
    async def test_call_llm_retry_logic_for_rate_limits_openai(self) -> None:
        """Test call_llm retries with exponential backoff for OpenAI rate limits."""
        config = AgentConfig(
            agent_name="test_agent",
            agent_type="conversion",
            llm_provider="openai",
            llm_model="gpt-4-turbo",
            llm_api_key="sk-test-key",
            temperature=0.3,
            max_tokens=8192,
            mcp_server_url="http://localhost:3000",
            agent_port=3002,
        )

        # Mock OpenAI client
        mock_openai = Mock()
        mock_chat = Mock()
        mock_completions = AsyncMock()
        mock_openai.chat = mock_chat
        mock_chat.completions = mock_completions

        # Mock response
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "Success after retries"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        # Fail once with rate limit, then succeed
        mock_completions.create.side_effect = [
            OpenAIRateLimitError(
                "Rate limit exceeded", response=Mock(), body=None
            ),
            mock_response,
        ]

        with patch(
            "agentic_neurodata_conversion.agents.base_agent.AsyncOpenAI",
            return_value=mock_openai,
        ):
            agent = ConcreteAgent(config)

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                response = await agent.call_llm(prompt="Test prompt")

                assert response == "Success after retries"
                assert mock_completions.create.call_count == 2
                assert mock_sleep.call_count == 1
                assert mock_sleep.call_args[0][0] == 1  # 2^0

    @pytest.mark.asyncio
    async def test_call_llm_exponential_backoff(self) -> None:
        """Test call_llm uses exponential backoff for retries."""
        config = AgentConfig(
            agent_name="test_agent",
            agent_type="conversation",
            llm_provider="anthropic",
            llm_model="claude-3-5-sonnet-20241022",
            llm_api_key="sk-ant-test-key",
            temperature=0.7,
            max_tokens=4096,
            mcp_server_url="http://localhost:3000",
            agent_port=3001,
        )

        mock_anthropic = Mock()
        mock_messages = AsyncMock()
        mock_anthropic.messages = mock_messages

        # Fail 4 times, then succeed
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "Success"
        mock_response.content = [mock_content]

        mock_messages.create.side_effect = [
            AnthropicRateLimitError("Rate limit", response=Mock(), body=None),
            AnthropicRateLimitError("Rate limit", response=Mock(), body=None),
            AnthropicRateLimitError("Rate limit", response=Mock(), body=None),
            AnthropicRateLimitError("Rate limit", response=Mock(), body=None),
            mock_response,
        ]

        with patch(
            "agentic_neurodata_conversion.agents.base_agent.AsyncAnthropic",
            return_value=mock_anthropic,
        ):
            agent = ConcreteAgent(config)

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                await agent.call_llm(prompt="Test")

                # Verify exponential backoff: 2^0, 2^1, 2^2, 2^3
                assert mock_sleep.call_count == 4
                assert mock_sleep.call_args_list[0][0][0] == 1   # 2^0
                assert mock_sleep.call_args_list[1][0][0] == 2   # 2^1
                assert mock_sleep.call_args_list[2][0][0] == 4   # 2^2
                assert mock_sleep.call_args_list[3][0][0] == 8   # 2^3

    @pytest.mark.asyncio
    async def test_call_llm_fails_after_max_retries(self) -> None:
        """Test call_llm raises error after max retries exceeded."""
        config = AgentConfig(
            agent_name="test_agent",
            agent_type="conversation",
            llm_provider="anthropic",
            llm_model="claude-3-5-sonnet-20241022",
            llm_api_key="sk-ant-test-key",
            temperature=0.7,
            max_tokens=4096,
            mcp_server_url="http://localhost:3000",
            agent_port=3001,
        )

        mock_anthropic = Mock()
        mock_messages = AsyncMock()
        mock_anthropic.messages = mock_messages

        # Always fail with rate limit
        mock_messages.create.side_effect = AnthropicRateLimitError(
            "Rate limit", response=Mock(), body=None
        )

        with patch(
            "agentic_neurodata_conversion.agents.base_agent.AsyncAnthropic",
            return_value=mock_anthropic,
        ):
            agent = ConcreteAgent(config)

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(AnthropicRateLimitError):
                    await agent.call_llm(prompt="Test", max_retries=3)

                # Should call 3 times (initial + 2 retries for max_retries=3)
                assert mock_messages.create.call_count == 3

    @pytest.mark.asyncio
    async def test_call_llm_linear_backoff_for_api_errors(self) -> None:
        """Test call_llm uses linear backoff for API errors."""
        config = AgentConfig(
            agent_name="test_agent",
            agent_type="conversation",
            llm_provider="anthropic",
            llm_model="claude-3-5-sonnet-20241022",
            llm_api_key="sk-ant-test-key",
            temperature=0.7,
            max_tokens=4096,
            mcp_server_url="http://localhost:3000",
            agent_port=3001,
        )

        mock_anthropic = Mock()
        mock_messages = AsyncMock()
        mock_anthropic.messages = mock_messages

        # Fail with API error, then succeed
        mock_response = Mock()
        mock_content = Mock()
        mock_content.text = "Success"
        mock_response.content = [mock_content]

        # Create mock AnthropicAPIError instances
        # The actual error constructor varies by SDK version, so we use a simple mock
        class MockAnthropicAPIError(AnthropicAPIError):
            def __init__(self, message: str) -> None:
                self.message = message
                super(Exception, self).__init__(message)

        mock_messages.create.side_effect = [
            MockAnthropicAPIError("API Error 1"),
            MockAnthropicAPIError("API Error 2"),
            mock_response,
        ]

        with patch(
            "agentic_neurodata_conversion.agents.base_agent.AsyncAnthropic",
            return_value=mock_anthropic,
        ):
            agent = ConcreteAgent(config)

            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                await agent.call_llm(prompt="Test")

                # Verify linear backoff: 1+0=1s, 1+1=2s
                assert mock_sleep.call_count == 2
                assert mock_sleep.call_args_list[0][0][0] == 1  # 1 + 0
                assert mock_sleep.call_args_list[1][0][0] == 2  # 1 + 1


class TestAgentHTTPServer:
    """Test BaseAgent HTTP server creation."""

    def test_create_agent_server_creates_fastapi_app(self) -> None:
        """Test create_agent_server returns FastAPI application."""
        config = AgentConfig(
            agent_name="test_agent",
            agent_type="conversation",
            llm_provider="anthropic",
            llm_model="claude-3-5-sonnet-20241022",
            llm_api_key="sk-ant-test-key",
            temperature=0.7,
            max_tokens=4096,
            mcp_server_url="http://localhost:3000",
            agent_port=3001,
        )

        with patch("agentic_neurodata_conversion.agents.base_agent.AsyncAnthropic"):
            agent = ConcreteAgent(config)

        app = agent.create_agent_server()

        assert app is not None
        assert app.title == "test_agent HTTP Server"
        assert app.version == "0.1.0"

    def test_agent_http_server_has_mcp_message_endpoint(self) -> None:
        """Test agent HTTP server has /mcp/message endpoint."""
        config = AgentConfig(
            agent_name="test_agent",
            agent_type="conversation",
            llm_provider="anthropic",
            llm_model="claude-3-5-sonnet-20241022",
            llm_api_key="sk-ant-test-key",
            temperature=0.7,
            max_tokens=4096,
            mcp_server_url="http://localhost:3000",
            agent_port=3001,
        )

        with patch("agentic_neurodata_conversion.agents.base_agent.AsyncAnthropic"):
            agent = ConcreteAgent(config)

        app = agent.create_agent_server()
        client = TestClient(app)

        # Send test MCP message
        message_data = {
            "message_id": "test-msg-123",
            "source_agent": "mcp_server",
            "target_agent": "test_agent",
            "session_id": "test-session",
            "message_type": "agent_execute",
            "payload": {"task": "test_task"},
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        response = client.post("/mcp/message", json=message_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["message"] == "Test message handled"

    def test_agent_http_server_has_health_endpoint(self) -> None:
        """Test agent HTTP server has /health endpoint."""
        config = AgentConfig(
            agent_name="test_agent",
            agent_type="conversation",
            llm_provider="anthropic",
            llm_model="claude-3-5-sonnet-20241022",
            llm_api_key="sk-ant-test-key",
            temperature=0.7,
            max_tokens=4096,
            mcp_server_url="http://localhost:3000",
            agent_port=3001,
        )

        with patch("agentic_neurodata_conversion.agents.base_agent.AsyncAnthropic"):
            agent = ConcreteAgent(config)

        app = agent.create_agent_server()
        client = TestClient(app)

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["agent_name"] == "test_agent"
        assert data["agent_type"] == "conversation"


class TestAbstractMethods:
    """Test abstract methods raise NotImplementedError."""

    def test_get_capabilities_is_abstract(self) -> None:
        """Test get_capabilities must be overridden in subclasses."""
        # This is tested by attempting to instantiate BaseAgent directly
        # which should fail because it's abstract
        config = AgentConfig(
            agent_name="test_agent",
            agent_type="conversation",
            llm_provider="anthropic",
            llm_model="claude-3-5-sonnet-20241022",
            llm_api_key="sk-ant-test-key",
            temperature=0.7,
            max_tokens=4096,
            mcp_server_url="http://localhost:3000",
            agent_port=3001,
        )

        with (
            patch("agentic_neurodata_conversion.agents.base_agent.AsyncAnthropic"),
            pytest.raises(TypeError, match="Can't instantiate abstract class"),
        ):
            # Cannot instantiate BaseAgent directly due to abstract methods
            BaseAgent(config)  # type: ignore

    def test_handle_message_is_abstract(self) -> None:
        """Test handle_message must be overridden in subclasses."""
        # Same as above - attempting to instantiate BaseAgent should fail
        config = AgentConfig(
            agent_name="test_agent",
            agent_type="conversation",
            llm_provider="anthropic",
            llm_model="claude-3-5-sonnet-20241022",
            llm_api_key="sk-ant-test-key",
            temperature=0.7,
            max_tokens=4096,
            mcp_server_url="http://localhost:3000",
            agent_port=3001,
        )

        with (
            patch("agentic_neurodata_conversion.agents.base_agent.AsyncAnthropic"),
            pytest.raises(TypeError, match="Can't instantiate abstract class"),
        ):
            BaseAgent(config)  # type: ignore
