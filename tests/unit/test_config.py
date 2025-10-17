"""
Unit tests for configuration module.

Tests cover:
- Settings class default values
- Settings loading from environment variables
- Redis URL validation
- AgentConfig for all agent types
- LLM provider validation
- Temperature range validation
- Max tokens validation
- Factory functions for agent configurations
"""

import os
from unittest.mock import patch

from pydantic import ValidationError
import pytest

from agentic_neurodata_conversion.config import (
    AgentConfig,
    Settings,
    get_conversation_agent_config,
    get_conversion_agent_config,
    get_evaluation_agent_config,
)


class TestSettings:
    """Test Settings configuration class."""

    def test_settings_default_values(self) -> None:
        """Test Settings loads default values without .env file."""
        settings = Settings()
        assert settings.mcp_server_host == "0.0.0.0"
        assert settings.mcp_server_port == 3000
        assert settings.redis_url == "redis://localhost:6379/0"
        assert settings.redis_session_ttl == 86400
        assert settings.filesystem_session_base_path == "./sessions"
        assert settings.filesystem_output_base_path == "./output"
        assert settings.conversation_agent_port == 3001
        assert settings.conversion_agent_port == 3002
        assert settings.evaluation_agent_port == 3003

    def test_settings_load_from_environment(self) -> None:
        """Test Settings loads from environment variables."""
        with patch.dict(
            os.environ,
            {
                "MCP_SERVER_HOST": "127.0.0.1",
                "MCP_SERVER_PORT": "4000",
                "REDIS_URL": "redis://redis-server:6379/1",
                "REDIS_SESSION_TTL": "3600",
                "FILESYSTEM_SESSION_BASE_PATH": "/tmp/sessions",
                "FILESYSTEM_OUTPUT_BASE_PATH": "/tmp/output",
                "CONVERSATION_AGENT_PORT": "5001",
                "CONVERSION_AGENT_PORT": "5002",
                "EVALUATION_AGENT_PORT": "5003",
            },
        ):
            settings = Settings()
            assert settings.mcp_server_host == "127.0.0.1"
            assert settings.mcp_server_port == 4000
            assert settings.redis_url == "redis://redis-server:6379/1"
            assert settings.redis_session_ttl == 3600
            assert settings.filesystem_session_base_path == "/tmp/sessions"
            assert settings.filesystem_output_base_path == "/tmp/output"
            assert settings.conversation_agent_port == 5001
            assert settings.conversion_agent_port == 5002
            assert settings.evaluation_agent_port == 5003

    def test_settings_validates_redis_url_format(self) -> None:
        """Test Settings validates Redis URL format."""
        with patch.dict(os.environ, {"REDIS_URL": "http://localhost:6379"}):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "redis_url" in str(exc_info.value)

    def test_settings_accepts_valid_redis_url(self) -> None:
        """Test Settings accepts valid Redis URL formats."""
        valid_urls = [
            "redis://localhost:6379/0",
            "redis://localhost:6379",
            "redis://user:pass@localhost:6379/0",
            "redis://redis-server:6379/1",
        ]
        for url in valid_urls:
            with patch.dict(os.environ, {"REDIS_URL": url}):
                settings = Settings()
                assert settings.redis_url == url


class TestAgentConfig:
    """Test AgentConfig class."""

    def test_agent_config_conversation_agent(self) -> None:
        """Test AgentConfig for conversation agent."""
        config = AgentConfig(
            agent_name="conversation_agent",
            agent_type="conversation",
            llm_provider="anthropic",
            llm_model="claude-3-5-sonnet-20241022",
            llm_api_key="sk-ant-test-key",
            temperature=0.7,
            max_tokens=4096,
            mcp_server_url="http://localhost:3000",
            agent_port=3001,
        )
        assert config.agent_name == "conversation_agent"
        assert config.agent_type == "conversation"
        assert config.llm_provider == "anthropic"
        assert config.temperature == 0.7
        assert config.max_tokens == 4096

    def test_agent_config_conversion_agent(self) -> None:
        """Test AgentConfig for conversion agent."""
        config = AgentConfig(
            agent_name="conversion_agent",
            agent_type="conversion",
            llm_provider="anthropic",
            llm_model="claude-3-5-sonnet-20241022",
            llm_api_key="sk-ant-test-key",
            temperature=0.3,
            max_tokens=8192,
            mcp_server_url="http://localhost:3000",
            agent_port=3002,
        )
        assert config.agent_name == "conversion_agent"
        assert config.agent_type == "conversion"
        assert config.temperature == 0.3
        assert config.max_tokens == 8192

    def test_agent_config_evaluation_agent(self) -> None:
        """Test AgentConfig for evaluation agent."""
        config = AgentConfig(
            agent_name="evaluation_agent",
            agent_type="evaluation",
            llm_provider="openai",
            llm_model="gpt-4-turbo",
            llm_api_key="sk-test-key",
            temperature=0.4,
            max_tokens=4096,
            mcp_server_url="http://localhost:3000",
            agent_port=3003,
        )
        assert config.agent_name == "evaluation_agent"
        assert config.agent_type == "evaluation"
        assert config.llm_provider == "openai"
        assert config.llm_model == "gpt-4-turbo"
        assert config.temperature == 0.4

    def test_agent_config_validates_llm_provider_anthropic(self) -> None:
        """Test LLM provider validation accepts 'anthropic'."""
        config = AgentConfig(
            agent_name="test_agent",
            agent_type="conversation",
            llm_provider="anthropic",
            llm_model="claude-3-5-sonnet-20241022",
            llm_api_key="sk-ant-test",
            temperature=0.5,
            max_tokens=2048,
            agent_port=3001,
        )
        assert config.llm_provider == "anthropic"

    def test_agent_config_validates_llm_provider_openai(self) -> None:
        """Test LLM provider validation accepts 'openai'."""
        config = AgentConfig(
            agent_name="test_agent",
            agent_type="conversation",
            llm_provider="openai",
            llm_model="gpt-4-turbo",
            llm_api_key="sk-test",
            temperature=0.5,
            max_tokens=2048,
            agent_port=3001,
        )
        assert config.llm_provider == "openai"

    def test_agent_config_rejects_invalid_llm_provider(self) -> None:
        """Test LLM provider validation rejects invalid providers."""
        with pytest.raises(ValidationError) as exc_info:
            AgentConfig(
                agent_name="test_agent",
                agent_type="conversation",
                llm_provider="invalid_provider",  # type: ignore
                llm_model="some-model",
                llm_api_key="sk-test",
                temperature=0.5,
                max_tokens=2048,
                agent_port=3001,
            )
        assert "llm_provider" in str(exc_info.value)

    def test_agent_config_temperature_minimum(self) -> None:
        """Test temperature validation accepts 0.0."""
        config = AgentConfig(
            agent_name="test_agent",
            agent_type="conversion",
            llm_provider="anthropic",
            llm_model="claude-3-5-sonnet-20241022",
            llm_api_key="sk-ant-test",
            temperature=0.0,
            max_tokens=2048,
            agent_port=3002,
        )
        assert config.temperature == 0.0

    def test_agent_config_temperature_maximum(self) -> None:
        """Test temperature validation accepts 1.0."""
        config = AgentConfig(
            agent_name="test_agent",
            agent_type="conversation",
            llm_provider="anthropic",
            llm_model="claude-3-5-sonnet-20241022",
            llm_api_key="sk-ant-test",
            temperature=1.0,
            max_tokens=2048,
            agent_port=3001,
        )
        assert config.temperature == 1.0

    def test_agent_config_temperature_below_minimum(self) -> None:
        """Test temperature validation rejects values below 0.0."""
        with pytest.raises(ValidationError) as exc_info:
            AgentConfig(
                agent_name="test_agent",
                agent_type="conversation",
                llm_provider="anthropic",
                llm_model="claude-3-5-sonnet-20241022",
                llm_api_key="sk-ant-test",
                temperature=-0.1,
                max_tokens=2048,
                agent_port=3001,
            )
        assert "temperature" in str(exc_info.value)

    def test_agent_config_temperature_above_maximum(self) -> None:
        """Test temperature validation rejects values above 1.0."""
        with pytest.raises(ValidationError) as exc_info:
            AgentConfig(
                agent_name="test_agent",
                agent_type="conversation",
                llm_provider="anthropic",
                llm_model="claude-3-5-sonnet-20241022",
                llm_api_key="sk-ant-test",
                temperature=1.1,
                max_tokens=2048,
                agent_port=3001,
            )
        assert "temperature" in str(exc_info.value)

    def test_agent_config_max_tokens_positive(self) -> None:
        """Test max_tokens validation accepts positive integers."""
        config = AgentConfig(
            agent_name="test_agent",
            agent_type="conversation",
            llm_provider="anthropic",
            llm_model="claude-3-5-sonnet-20241022",
            llm_api_key="sk-ant-test",
            temperature=0.5,
            max_tokens=1000,
            agent_port=3001,
        )
        assert config.max_tokens == 1000

    def test_agent_config_max_tokens_rejects_zero(self) -> None:
        """Test max_tokens validation rejects zero."""
        with pytest.raises(ValidationError) as exc_info:
            AgentConfig(
                agent_name="test_agent",
                agent_type="conversation",
                llm_provider="anthropic",
                llm_model="claude-3-5-sonnet-20241022",
                llm_api_key="sk-ant-test",
                temperature=0.5,
                max_tokens=0,
                agent_port=3001,
            )
        assert "max_tokens" in str(exc_info.value)

    def test_agent_config_max_tokens_rejects_negative(self) -> None:
        """Test max_tokens validation rejects negative values."""
        with pytest.raises(ValidationError) as exc_info:
            AgentConfig(
                agent_name="test_agent",
                agent_type="conversation",
                llm_provider="anthropic",
                llm_model="claude-3-5-sonnet-20241022",
                llm_api_key="sk-ant-test",
                temperature=0.5,
                max_tokens=-100,
                agent_port=3001,
            )
        assert "max_tokens" in str(exc_info.value)

    def test_agent_config_rejects_invalid_agent_type(self) -> None:
        """Test agent_type validation rejects invalid types."""
        with pytest.raises(ValidationError) as exc_info:
            AgentConfig(
                agent_name="test_agent",
                agent_type="invalid_type",  # type: ignore
                llm_provider="anthropic",
                llm_model="claude-3-5-sonnet-20241022",
                llm_api_key="sk-ant-test",
                temperature=0.5,
                max_tokens=2048,
                agent_port=3001,
            )
        assert "agent_type" in str(exc_info.value)


class TestFactoryFunctions:
    """Test factory functions for agent configurations."""

    def test_get_conversation_agent_config_with_anthropic(self) -> None:
        """Test get_conversation_agent_config() factory returns correct config."""
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "sk-ant-test-key",
                "CONVERSATION_LLM_MODEL": "claude-3-5-sonnet-20241022",
            },
        ):
            config = get_conversation_agent_config()
            assert config.agent_name == "conversation_agent"
            assert config.agent_type == "conversation"
            assert config.llm_provider == "anthropic"
            assert config.llm_model == "claude-3-5-sonnet-20241022"
            assert config.llm_api_key == "sk-ant-test-key"
            assert config.temperature == 0.7
            assert config.mcp_server_url == "http://0.0.0.0:3000"
            assert config.agent_port == 3001

    def test_get_conversation_agent_config_with_openai(self) -> None:
        """Test get_conversation_agent_config() with OpenAI."""
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "sk-openai-test-key",
                "CONVERSATION_LLM_MODEL": "gpt-4-turbo",
            },
        ):
            config = get_conversation_agent_config()
            assert config.llm_provider == "openai"
            assert config.llm_model == "gpt-4-turbo"
            assert config.llm_api_key == "sk-openai-test-key"

    def test_get_conversation_agent_config_defaults(self) -> None:
        """Test get_conversation_agent_config() uses default model if not specified."""
        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "sk-ant-test-key"},
            clear=True,
        ):
            config = get_conversation_agent_config()
            assert config.llm_model == "claude-3-5-sonnet-20241022"

    def test_get_conversion_agent_config_with_anthropic(self) -> None:
        """Test get_conversion_agent_config() factory returns correct config."""
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "sk-ant-test-key",
                "CONVERSION_LLM_MODEL": "claude-3-5-sonnet-20241022",
            },
        ):
            config = get_conversion_agent_config()
            assert config.agent_name == "conversion_agent"
            assert config.agent_type == "conversion"
            assert config.llm_provider == "anthropic"
            assert config.temperature == 0.3
            assert config.agent_port == 3002

    def test_get_conversion_agent_config_with_openai(self) -> None:
        """Test get_conversion_agent_config() with OpenAI."""
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "sk-openai-test-key",
                "CONVERSION_LLM_MODEL": "gpt-4-turbo",
            },
        ):
            config = get_conversion_agent_config()
            assert config.llm_provider == "openai"
            assert config.llm_model == "gpt-4-turbo"

    def test_get_evaluation_agent_config_with_anthropic(self) -> None:
        """Test get_evaluation_agent_config() factory returns correct config."""
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "sk-ant-test-key",
                "EVALUATION_LLM_MODEL": "claude-3-5-sonnet-20241022",
            },
        ):
            config = get_evaluation_agent_config()
            assert config.agent_name == "evaluation_agent"
            assert config.agent_type == "evaluation"
            assert config.llm_provider == "anthropic"
            assert config.temperature == 0.4
            assert config.agent_port == 3003

    def test_get_evaluation_agent_config_with_openai(self) -> None:
        """Test get_evaluation_agent_config() with OpenAI."""
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "sk-openai-test-key",
                "EVALUATION_LLM_MODEL": "gpt-4-turbo",
            },
        ):
            config = get_evaluation_agent_config()
            assert config.llm_provider == "openai"
            assert config.llm_model == "gpt-4-turbo"

    def test_factory_functions_raise_error_without_api_key(self) -> None:
        """Test factory functions raise error when no API key is provided."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                get_conversation_agent_config()
            assert "API key" in str(exc_info.value)

    def test_factory_functions_prefer_anthropic_when_both_keys_present(self) -> None:
        """Test factory functions prefer Anthropic when both API keys are present."""
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "sk-ant-test",
                "OPENAI_API_KEY": "sk-openai-test",
            },
        ):
            config = get_conversation_agent_config()
            assert config.llm_provider == "anthropic"
