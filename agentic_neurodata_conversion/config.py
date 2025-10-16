"""Configuration module for MCP conversion pipeline."""

import os
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Server configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # MCP Server settings
    mcp_server_host: str = "0.0.0.0"
    mcp_server_port: int = 3000

    # Redis settings
    redis_url: str = "redis://localhost:6379/0"
    redis_session_ttl: int = 86400  # 24 hours in seconds

    # Filesystem settings
    filesystem_session_base_path: str = "./sessions"
    filesystem_output_base_path: str = "./output"

    # Agent port settings
    conversation_agent_port: int = 3001
    conversion_agent_port: int = 3002
    evaluation_agent_port: int = 3003

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL format."""
        if not v.startswith("redis://"):
            raise ValueError("redis_url must start with 'redis://'")
        return v


class AgentConfig(BaseModel):
    """Agent configuration model."""

    agent_name: str
    agent_type: Literal["conversation", "conversion", "evaluation"]
    llm_provider: Literal["anthropic", "openai"]
    llm_model: str
    llm_api_key: str
    temperature: float = Field(ge=0.0, le=1.0)
    max_tokens: int = Field(gt=0)
    mcp_server_url: str = "http://0.0.0.0:3000"
    agent_port: int


# Global settings instance
settings = Settings()


def get_conversation_agent_config() -> AgentConfig:
    """Get conversation agent configuration from environment."""
    # Check for API keys
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not anthropic_key and not openai_key:
        raise ValueError(
            "No LLM API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY."
        )

    # Prefer Anthropic if both are present
    if anthropic_key:
        provider = "anthropic"
        api_key = anthropic_key
        default_model = "claude-3-5-sonnet-20241022"
    else:
        provider = "openai"
        api_key = openai_key
        default_model = "gpt-4-turbo"

    model = os.getenv("CONVERSATION_LLM_MODEL", default_model)

    return AgentConfig(
        agent_name="conversation_agent",
        agent_type="conversation",
        llm_provider=provider,  # type: ignore
        llm_model=model,
        llm_api_key=api_key,
        temperature=0.7,
        max_tokens=4096,
        mcp_server_url=f"http://{settings.mcp_server_host}:{settings.mcp_server_port}",
        agent_port=settings.conversation_agent_port,
    )


def get_conversion_agent_config() -> AgentConfig:
    """Get conversion agent configuration from environment."""
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not anthropic_key and not openai_key:
        raise ValueError(
            "No LLM API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY."
        )

    if anthropic_key:
        provider = "anthropic"
        api_key = anthropic_key
        default_model = "claude-3-5-sonnet-20241022"
    else:
        provider = "openai"
        api_key = openai_key
        default_model = "gpt-4-turbo"

    model = os.getenv("CONVERSION_LLM_MODEL", default_model)

    return AgentConfig(
        agent_name="conversion_agent",
        agent_type="conversion",
        llm_provider=provider,  # type: ignore
        llm_model=model,
        llm_api_key=api_key,
        temperature=0.3,
        max_tokens=8192,
        mcp_server_url=f"http://{settings.mcp_server_host}:{settings.mcp_server_port}",
        agent_port=settings.conversion_agent_port,
    )


def get_evaluation_agent_config() -> AgentConfig:
    """Get evaluation agent configuration from environment."""
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not anthropic_key and not openai_key:
        raise ValueError(
            "No LLM API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY."
        )

    if anthropic_key:
        provider = "anthropic"
        api_key = anthropic_key
        default_model = "claude-3-5-sonnet-20241022"
    else:
        provider = "openai"
        api_key = openai_key
        default_model = "gpt-4-turbo"

    model = os.getenv("EVALUATION_LLM_MODEL", default_model)

    return AgentConfig(
        agent_name="evaluation_agent",
        agent_type="evaluation",
        llm_provider=provider,  # type: ignore
        llm_model=model,
        llm_api_key=api_key,
        temperature=0.4,
        max_tokens=4096,
        mcp_server_url=f"http://{settings.mcp_server_host}:{settings.mcp_server_port}",
        agent_port=settings.evaluation_agent_port,
    )
