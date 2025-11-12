"""
Unit tests for LLM service.

Tests the LLM service abstraction layer including:
- Anthropic implementation
- Mock implementation
- Error handling
- Structured output generation
"""

from unittest.mock import AsyncMock, Mock

import pytest
from anthropic.types import TextBlock
from services.llm_service import (
    AnthropicLLMService,
    LLMServiceError,
    MockLLMService,
    create_llm_service,
)


@pytest.mark.unit
class TestMockLLMService:
    """Tests for the mock LLM service used in testing."""

    @pytest.mark.asyncio
    async def test_generate_completion_with_default_response(self):
        """Test mock returns default response."""
        service = MockLLMService()
        result = await service.generate_completion("test prompt")

        assert result == "Mock LLM response"

    @pytest.mark.asyncio
    async def test_generate_completion_with_custom_response(self):
        """Test mock returns custom responses."""
        responses = {
            "hello": "world",
            "test": "response",
        }
        service = MockLLMService(responses=responses)

        result1 = await service.generate_completion("hello")
        result2 = await service.generate_completion("test")
        result3 = await service.generate_completion("unknown")

        assert result1 == "world"
        assert result2 == "response"
        assert result3 == "Mock LLM response"  # Default for unknown

    @pytest.mark.asyncio
    async def test_generate_structured_output(self):
        """Test mock generates structured output."""
        service = MockLLMService()
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "number"},
            },
        }

        result = await service.generate_structured_output(
            prompt="test",
            output_schema=schema,
        )

        assert isinstance(result, dict)
        assert result["mock"] is True
        assert result["schema"] == schema

    def test_set_response(self):
        """Test setting custom responses after initialization."""
        service = MockLLMService()
        service.set_response("key1", "value1")
        service.set_response("key2", "value2")

        assert service._responses["key1"] == "value1"
        assert service._responses["key2"] == "value2"


@pytest.mark.unit
class TestAnthropicLLMService:
    """Tests for the Anthropic Claude implementation."""

    def test_initialization_with_defaults(self):
        """Test service initializes with default model."""
        service = AnthropicLLMService(api_key="test-key")

        assert service._model == "claude-sonnet-4-20250514"
        assert service._client is not None

    def test_initialization_with_custom_model(self):
        """Test service initializes with custom model."""
        service = AnthropicLLMService(
            api_key="test-key",
            model="claude-3-opus-20240229",
        )

        assert service._model == "claude-3-opus-20240229"

    @pytest.mark.asyncio
    async def test_generate_completion_success(self):
        """Test successful text generation."""
        mock_response = Mock()
        mock_content = Mock(spec=TextBlock)
        mock_content.text = "Generated response"
        mock_response.content = [mock_content]

        service = AnthropicLLMService(api_key="test-key")
        service._client.messages.create = AsyncMock(return_value=mock_response)

        result = await service.generate_completion(
            prompt="Test prompt",
            system_prompt="Test system",
        )

        assert result == "Generated response"
        service._client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_completion_with_temperature(self):
        """Test generation with custom temperature."""
        mock_response = Mock()
        mock_content = Mock(spec=TextBlock)
        mock_content.text = "Response"
        mock_response.content = [mock_content]

        service = AnthropicLLMService(api_key="test-key")
        service._client.messages.create = AsyncMock(return_value=mock_response)

        await service.generate_completion(
            prompt="Test",
            temperature=0.5,
            max_tokens=1000,
        )

        call_args = service._client.messages.create.call_args
        assert call_args.kwargs["temperature"] == 0.5
        assert call_args.kwargs["max_tokens"] == 1000

    @pytest.mark.asyncio
    async def test_generate_completion_empty_response(self):
        """Test handling of empty API response."""
        mock_response = Mock()
        mock_response.content = []

        service = AnthropicLLMService(api_key="test-key")
        service._client.messages.create = AsyncMock(return_value=mock_response)

        with pytest.raises(LLMServiceError) as exc_info:
            await service.generate_completion(prompt="Test")

        assert "Empty response from API" in str(exc_info.value)
        assert exc_info.value.provider == "anthropic"

    @pytest.mark.asyncio
    async def test_generate_completion_api_error(self):
        """Test handling of API errors."""
        service = AnthropicLLMService(api_key="test-key")
        service._client.messages.create = AsyncMock(side_effect=Exception("API Error"))

        with pytest.raises(LLMServiceError) as exc_info:
            await service.generate_completion(prompt="Test")

        assert "Failed to generate completion" in str(exc_info.value)
        assert exc_info.value.provider == "anthropic"

    @pytest.mark.asyncio
    async def test_generate_structured_output_json_response(self):
        """Test structured output with clean JSON response."""
        mock_response = Mock()
        mock_content = Mock(spec=TextBlock)
        mock_content.text = '{"name": "Alice", "age": 30}'
        mock_response.content = [mock_content]

        service = AnthropicLLMService(api_key="test-key")
        service._client.messages.create = AsyncMock(return_value=mock_response)

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "number"},
            },
        }

        result = await service.generate_structured_output(
            prompt="Test",
            output_schema=schema,
        )

        assert result == {"name": "Alice", "age": 30}

    @pytest.mark.asyncio
    async def test_generate_structured_output_markdown_wrapped(self):
        """Test structured output wrapped in markdown code blocks."""
        mock_response = Mock()
        mock_content = Mock(spec=TextBlock)
        mock_content.text = '```json\n{"key": "value"}\n```'
        mock_response.content = [mock_content]

        service = AnthropicLLMService(api_key="test-key")
        service._client.messages.create = AsyncMock(return_value=mock_response)

        result = await service.generate_structured_output(
            prompt="Test",
            output_schema={},
        )

        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_generate_structured_output_generic_code_block(self):
        """Test structured output in generic code blocks."""
        mock_response = Mock()
        mock_content = Mock(spec=TextBlock)
        mock_content.text = '```\n{"data": 123}\n```'
        mock_response.content = [mock_content]

        service = AnthropicLLMService(api_key="test-key")
        service._client.messages.create = AsyncMock(return_value=mock_response)

        result = await service.generate_structured_output(
            prompt="Test",
            output_schema={},
        )

        assert result == {"data": 123}

    @pytest.mark.asyncio
    async def test_generate_structured_output_invalid_json(self):
        """Test handling of invalid JSON in response."""
        mock_response = Mock()
        mock_content = Mock(spec=TextBlock)
        mock_content.text = "Not valid JSON {broken"
        mock_response.content = [mock_content]

        service = AnthropicLLMService(api_key="test-key")
        service._client.messages.create = AsyncMock(return_value=mock_response)

        with pytest.raises(LLMServiceError) as exc_info:
            await service.generate_structured_output(
                prompt="Test",
                output_schema={},
            )

        assert "Failed to parse JSON" in str(exc_info.value)
        assert exc_info.value.provider == "anthropic"

    @pytest.mark.asyncio
    async def test_generate_structured_output_uses_lower_temperature(self):
        """Test that structured output uses lower temperature."""
        mock_response = Mock()
        mock_content = Mock(spec=TextBlock)
        mock_content.text = '{"test": true}'
        mock_response.content = [mock_content]

        service = AnthropicLLMService(api_key="test-key")
        service._client.messages.create = AsyncMock(return_value=mock_response)

        await service.generate_structured_output(
            prompt="Test",
            output_schema={},
        )

        # Verify temperature was set to 0.3 (lower for deterministic output)
        call_args = service._client.messages.create.call_args
        assert call_args.kwargs["temperature"] == 0.3


@pytest.mark.unit
class TestLLMServiceFactory:
    """Tests for the LLM service factory function."""

    def test_create_anthropic_service(self):
        """Test creating Anthropic service."""
        service = create_llm_service(
            provider="anthropic",
            api_key="test-key",
        )

        assert isinstance(service, AnthropicLLMService)
        assert service._model == "claude-sonnet-4-20250514"

    def test_create_anthropic_service_custom_model(self):
        """Test creating Anthropic service with custom model."""
        service = create_llm_service(
            provider="anthropic",
            api_key="test-key",
            model="claude-3-opus-20240229",
        )

        assert isinstance(service, AnthropicLLMService)
        assert service._model == "claude-3-opus-20240229"

    def test_create_anthropic_service_without_api_key(self):
        """Test that Anthropic requires API key."""
        with pytest.raises(ValueError) as exc_info:
            create_llm_service(provider="anthropic")

        assert "api_key is required" in str(exc_info.value)

    def test_create_mock_service(self):
        """Test creating mock service."""
        service = create_llm_service(provider="mock")

        assert isinstance(service, MockLLMService)

    def test_create_mock_service_with_responses(self):
        """Test creating mock service with custom responses."""
        responses = {"test": "value"}
        service = create_llm_service(
            provider="mock",
            responses=responses,
        )

        assert isinstance(service, MockLLMService)
        assert service._responses == responses

    def test_create_service_unknown_provider(self):
        """Test error for unknown provider."""
        with pytest.raises(ValueError) as exc_info:
            create_llm_service(provider="unknown")

        assert "Unknown LLM provider" in str(exc_info.value)


@pytest.mark.unit
class TestLLMServiceError:
    """Tests for the LLMServiceError exception."""

    def test_error_initialization(self):
        """Test error initializes with message and provider."""
        error = LLMServiceError(
            message="Test error",
            provider="anthropic",
        )

        assert str(error) == "Test error"
        assert error.provider == "anthropic"
        assert error.details == {}

    def test_error_with_details(self):
        """Test error with additional details."""
        details = {"model": "claude-3", "tokens": 1000}
        error = LLMServiceError(
            message="API Error",
            provider="anthropic",
            details=details,
        )

        assert error.details == details
        assert error.details["model"] == "claude-3"
        assert error.details["tokens"] == 1000
