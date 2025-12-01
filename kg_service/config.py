"""Knowledge Graph Service Configuration.

This module provides configuration management for the KG service using Pydantic Settings.
Configuration is loaded from environment variables defined in .env file.

Environment Variables:
    NEO4J_URI: Neo4j database connection URI (default: bolt://localhost:7687)
    NEO4J_USER: Neo4j username (default: neo4j)
    NEO4J_PASSWORD: Neo4j password (required)
    KG_SERVICE_URL: KG service endpoint URL (default: http://localhost:8001)
    KG_SERVICE_ENABLED: Enable/disable KG service (default: true)
    KG_SERVICE_TIMEOUT: Request timeout in seconds (default: 5.0)
    KG_MAX_RETRIES: Maximum retry attempts (default: 2)
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class KGServiceSettings(BaseSettings):
    """Knowledge Graph Service configuration settings.

    Uses pydantic-settings to load configuration from environment variables.
    Follows the same pattern as the main application configuration.

    Attributes:
        neo4j_uri: Neo4j database connection URI
        neo4j_user: Neo4j authentication username
        neo4j_password: Neo4j authentication password
        kg_service_url: URL where KG service is running
        kg_service_enabled: Whether KG service integration is enabled
        kg_service_timeout: Timeout for KG service requests in seconds
        kg_max_retries: Maximum number of retry attempts for failed requests
    """

    # Neo4j Database Configuration
    neo4j_uri: str = Field(
        default="bolt://localhost:7687",
        description="Neo4j database connection URI"
    )
    neo4j_user: str = Field(
        default="neo4j",
        description="Neo4j authentication username"
    )
    neo4j_password: str = Field(
        ...,
        description="Neo4j authentication password (required)"
    )

    # KG Service Configuration
    kg_service_url: str = Field(
        default="http://localhost:8001",
        description="URL where KG service is running"
    )
    kg_service_enabled: bool = Field(
        default=True,
        description="Enable/disable KG service integration"
    )
    kg_service_timeout: float = Field(
        default=5.0,
        ge=0.1,
        le=30.0,
        description="Timeout for KG service requests in seconds"
    )
    kg_max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Maximum number of retry attempts for failed requests"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore extra fields from .env
    )


# Global settings instance
# This is initialized once and reused throughout the application
_settings: KGServiceSettings | None = None


def get_settings() -> KGServiceSettings:
    """Get or create the global settings instance.

    This function implements lazy initialization of settings to avoid
    loading environment variables at import time. It creates a singleton
    settings instance that is reused across the application.

    Returns:
        KGServiceSettings: The global settings instance

    Example:
        >>> settings = get_settings()
        >>> print(settings.neo4j_uri)
        bolt://localhost:7687
    """
    global _settings
    if _settings is None:
        _settings = KGServiceSettings()
    return _settings


def reset_settings() -> None:
    """Reset the global settings instance.

    This function is primarily used for testing to reset the settings
    instance between test cases. It should not be used in production code.

    Example:
        >>> reset_settings()  # Force reload of settings from environment
        >>> settings = get_settings()  # Gets fresh settings instance
    """
    global _settings
    _settings = None
