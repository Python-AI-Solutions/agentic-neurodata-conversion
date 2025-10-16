"""
Configuration module for the multi-agent NWB conversion pipeline.

This module provides type-safe configuration management using pydantic-settings.
It includes:
- Settings: Server and infrastructure configuration
- AgentConfig: LLM agent configuration with validation
- Factory functions: Convenient creation of agent-specific configurations
"""

import os
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Server and infrastructure configuration.

    Loads configuration from environment variables with defaults.
    Supports .env file for local development.
    """

    # Server Configuration
    mcp_server_host: str = "0.0.0.0"
    mcp_server_port: int = 3000

    # Redis Configuration
    redis_url: str = "redis://localhost:6379/0"
    redis_session_ttl: int = 86400  # 24 hours in seconds

    # Filesystem Configuration
    filesystem_session_base_path: str = "./sessions"
    filesystem_output_base_path: str = "./output"

    # Agent Ports
    conversation_agent_port: int = 3001
    conversion_agent_port: int = 3002
    evaluation_agent_port: int = 3003

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate that Redis URL starts with redis://."""
        if not v.startswith("redis://"):
            raise ValueError("Redis URL must start with 'redis://'")
        return v

    class Config:
        """Pydantic settings configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra environment variables


class AgentConfig(BaseModel):
    """
    Configuration for an LLM-powered agent.

    Includes LLM provider settings, model parameters, and connection details.
    """

    agent_name: str
    agent_type: Literal["conversation", "conversion", "evaluation"]
    llm_provider: Literal["anthropic", "openai"]
    llm_model: str
    llm_api_key: str
    temperature: float = Field(ge=0.0, le=1.0)
    max_tokens: int = Field(gt=0)
    mcp_server_url: str = "http://localhost:3000"
    agent_port: int


def get_conversation_agent_config() -> AgentConfig:
    """
    Factory function for conversation agent configuration.

    The conversation agent uses higher temperature (0.7) for more natural,
    friendly interactions with users.

    Returns:
        AgentConfig configured for conversation agent

    Raises:
        ValueError: If no API key is found
    """
    settings = Settings()

    # Check for API keys and determine provider
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not anthropic_key and not openai_key:
        raise ValueError(
            "No API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY "
            "environment variable."
        )

    # Prefer Anthropic if both keys are present
    if anthropic_key:
        llm_provider = "anthropic"
        llm_api_key = anthropic_key
        default_model = "claude-3-5-sonnet-20241022"
    else:
        llm_provider = "openai"
        llm_api_key = openai_key  # type: ignore
        default_model = "gpt-4-turbo"

    # Get model from environment or use default
    llm_model = os.getenv("CONVERSATION_LLM_MODEL", default_model)

    return AgentConfig(
        agent_name="conversation_agent",
        agent_type="conversation",
        llm_provider=llm_provider,  # type: ignore
        llm_model=llm_model,
        llm_api_key=llm_api_key,
        temperature=0.7,  # Friendly, natural conversations
        max_tokens=4096,
        mcp_server_url=f"http://{settings.mcp_server_host}:{settings.mcp_server_port}",
        agent_port=settings.conversation_agent_port,
    )


def get_conversion_agent_config() -> AgentConfig:
    """
    Factory function for conversion agent configuration.

    The conversion agent uses lower temperature (0.3) for more deterministic,
    consistent code generation and data conversion.

    Returns:
        AgentConfig configured for conversion agent

    Raises:
        ValueError: If no API key is found
    """
    settings = Settings()

    # Check for API keys and determine provider
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not anthropic_key and not openai_key:
        raise ValueError(
            "No API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY "
            "environment variable."
        )

    # Prefer Anthropic if both keys are present
    if anthropic_key:
        llm_provider = "anthropic"
        llm_api_key = anthropic_key
        default_model = "claude-3-5-sonnet-20241022"
    else:
        llm_provider = "openai"
        llm_api_key = openai_key  # type: ignore
        default_model = "gpt-4-turbo"

    # Get model from environment or use default
    llm_model = os.getenv("CONVERSION_LLM_MODEL", default_model)

    return AgentConfig(
        agent_name="conversion_agent",
        agent_type="conversion",
        llm_provider=llm_provider,  # type: ignore
        llm_model=llm_model,
        llm_api_key=llm_api_key,
        temperature=0.3,  # Deterministic, consistent conversions
        max_tokens=8192,
        mcp_server_url=f"http://{settings.mcp_server_host}:{settings.mcp_server_port}",
        agent_port=settings.conversion_agent_port,
    )


def get_evaluation_agent_config() -> AgentConfig:
    """
    Factory function for evaluation agent configuration.

    The evaluation agent uses moderate temperature (0.4) for clear,
    readable validation reports and summaries.

    Returns:
        AgentConfig configured for evaluation agent

    Raises:
        ValueError: If no API key is found
    """
    settings = Settings()

    # Check for API keys and determine provider
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not anthropic_key and not openai_key:
        raise ValueError(
            "No API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY "
            "environment variable."
        )

    # Prefer Anthropic if both keys are present
    if anthropic_key:
        llm_provider = "anthropic"
        llm_api_key = anthropic_key
        default_model = "claude-3-5-sonnet-20241022"
    else:
        llm_provider = "openai"
        llm_api_key = openai_key  # type: ignore
        default_model = "gpt-4-turbo"

    # Get model from environment or use default
    llm_model = os.getenv("EVALUATION_LLM_MODEL", default_model)

    return AgentConfig(
        agent_name="evaluation_agent",
        agent_type="evaluation",
        llm_provider=llm_provider,  # type: ignore
        llm_model=llm_model,
        llm_api_key=llm_api_key,
        temperature=0.4,  # Clear, readable reports
        max_tokens=4096,
        mcp_server_url=f"http://{settings.mcp_server_host}:{settings.mcp_server_port}",
        agent_port=settings.evaluation_agent_port,
    )


# Global settings instance for convenient access
settings = Settings()
