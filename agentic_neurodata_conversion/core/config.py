"""Configuration management for the agentic neurodata conversion system.

This module provides a comprehensive configuration system using Pydantic Settings
with support for environment variables, nested configurations, and validation.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerConfig(BaseModel):
    """MCP Server configuration settings."""
    
    host: str = Field(default="127.0.0.1", description="Server host address")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port number")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    cors_origins: List[str] = Field(
        default=["*"], 
        description="Allowed CORS origins for web interface"
    )
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is supported."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()
    
    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v: List[str]) -> List[str]:
        """Validate CORS origins format."""
        if not v:
            return ["*"]
        return v


class AgentConfig(BaseModel):
    """Configuration for internal agents."""
    
    conversation_model: str = Field(
        default="gpt-4", 
        description="LLM model for conversation agent"
    )
    conversion_timeout: int = Field(
        default=300, 
        ge=30, 
        le=3600, 
        description="Conversion timeout in seconds"
    )
    evaluation_strict: bool = Field(
        default=True, 
        description="Enable strict evaluation mode"
    )
    knowledge_graph_format: str = Field(
        default="ttl", 
        description="Knowledge graph output format"
    )
    
    # LLM API Configuration
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_org_id: Optional[str] = Field(default=None, description="OpenAI organization ID")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    
    # Local model configuration
    local_model_url: Optional[str] = Field(
        default=None, 
        description="URL for local model server"
    )
    local_model_name: Optional[str] = Field(
        default=None, 
        description="Name of local model to use"
    )
    
    @field_validator("knowledge_graph_format")
    @classmethod
    def validate_kg_format(cls, v: str) -> str:
        """Validate knowledge graph format."""
        valid_formats = {"ttl", "rdf", "jsonld", "nt"}
        if v.lower() not in valid_formats:
            raise ValueError(f"Knowledge graph format must be one of: {valid_formats}")
        return v.lower()


class DataConfig(BaseModel):
    """Data processing configuration."""
    
    output_dir: str = Field(default="outputs", description="Output directory path")
    temp_dir: str = Field(default="temp", description="Temporary files directory")
    cache_dir: str = Field(default="cache", description="Cache directory path")
    
    max_file_size: int = Field(
        default=1024 * 1024 * 1024,  # 1GB
        ge=1024 * 1024,  # Minimum 1MB
        description="Maximum file size in bytes"
    )
    max_processing_time: int = Field(
        default=3600,  # 1 hour
        ge=60,  # Minimum 1 minute
        description="Maximum processing time in seconds"
    )
    
    supported_formats: List[str] = Field(
        default=["open_ephys", "spikeglx", "neuralynx", "blackrock", "intan"],
        description="Supported data formats for conversion"
    )
    
    @field_validator("output_dir", "temp_dir", "cache_dir")
    @classmethod
    def validate_directories(cls, v: str) -> str:
        """Validate and create directories if they don't exist."""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return str(path.resolve())
    
    @field_validator("supported_formats")
    @classmethod
    def validate_formats(cls, v: List[str]) -> List[str]:
        """Validate supported formats list."""
        if not v:
            raise ValueError("At least one supported format must be specified")
        return [fmt.lower() for fmt in v]


class DatabaseConfig(BaseModel):
    """Database configuration for state persistence."""
    
    url: Optional[str] = Field(
        default="sqlite:///./agentic_converter.db",
        description="Database connection URL"
    )
    echo: bool = Field(default=False, description="Enable SQL query logging")
    pool_size: int = Field(default=5, ge=1, description="Connection pool size")
    max_overflow: int = Field(default=10, ge=0, description="Maximum pool overflow")
    
    # Redis configuration for caching
    redis_url: Optional[str] = Field(default=None, description="Redis connection URL")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_db: int = Field(default=0, ge=0, le=15, description="Redis database number")


class ExternalServicesConfig(BaseModel):
    """Configuration for external service integrations."""
    
    # NeuroConv configuration
    neuroconv_backend: str = Field(default="auto", description="NeuroConv backend")
    neuroconv_compression: str = Field(default="gzip", description="NWB compression method")
    neuroconv_chunk_size: int = Field(
        default=1024, 
        ge=64, 
        description="Chunk size for data processing"
    )
    
    # NWB Inspector configuration
    nwb_inspector_strict_mode: bool = Field(
        default=False, 
        description="Enable NWB Inspector strict mode"
    )
    nwb_inspector_check_completeness: bool = Field(
        default=True, 
        description="Check NWB file completeness"
    )
    
    # LinkML configuration
    linkml_schema_path: str = Field(default="schemas/", description="LinkML schema directory")
    linkml_validation_level: str = Field(
        default="error", 
        description="LinkML validation level"
    )
    
    # DANDI Archive integration
    dandi_api_key: Optional[str] = Field(default=None, description="DANDI API key")
    dandi_staging: bool = Field(default=False, description="Use DANDI staging server")
    
    @field_validator("linkml_validation_level")
    @classmethod
    def validate_linkml_level(cls, v: str) -> str:
        """Validate LinkML validation level."""
        valid_levels = {"error", "warning", "info"}
        if v.lower() not in valid_levels:
            raise ValueError(f"LinkML validation level must be one of: {valid_levels}")
        return v.lower()


class SecurityConfig(BaseModel):
    """Security and authentication configuration."""
    
    secret_key: Optional[str] = Field(default=None, description="Secret key for JWT tokens")
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    jwt_expiration_hours: int = Field(
        default=24, 
        ge=1, 
        description="JWT token expiration in hours"
    )
    
    allowed_hosts: List[str] = Field(
        default=["localhost", "127.0.0.1"], 
        description="Allowed host names"
    )
    trusted_proxies: List[str] = Field(
        default=[], 
        description="Trusted proxy addresses"
    )


class PerformanceConfig(BaseModel):
    """Performance and resource management configuration."""
    
    max_workers: int = Field(default=4, ge=1, description="Maximum worker processes")
    max_concurrent_conversions: int = Field(
        default=2, 
        ge=1, 
        description="Maximum concurrent conversions"
    )
    worker_timeout: int = Field(
        default=1800,  # 30 minutes
        ge=60, 
        description="Worker timeout in seconds"
    )
    
    max_memory_usage: int = Field(
        default=8 * 1024 * 1024 * 1024,  # 8GB
        ge=1024 * 1024 * 1024,  # Minimum 1GB
        description="Maximum memory usage in bytes"
    )
    memory_check_interval: int = Field(
        default=60, 
        ge=10, 
        description="Memory check interval in seconds"
    )
    
    min_free_disk_space: int = Field(
        default=5 * 1024 * 1024 * 1024,  # 5GB
        ge=1024 * 1024 * 1024,  # Minimum 1GB
        description="Minimum free disk space in bytes"
    )
    cleanup_temp_files: bool = Field(
        default=True, 
        description="Automatically cleanup temporary files"
    )
    temp_file_retention_hours: int = Field(
        default=24, 
        ge=1, 
        description="Temporary file retention in hours"
    )


class MonitoringConfig(BaseModel):
    """Monitoring and observability configuration."""
    
    enable_metrics: bool = Field(default=False, description="Enable metrics collection")
    metrics_port: int = Field(
        default=9090, 
        ge=1024, 
        le=65535, 
        description="Metrics server port"
    )
    metrics_path: str = Field(default="/metrics", description="Metrics endpoint path")
    
    health_check_interval: int = Field(
        default=30, 
        ge=5, 
        description="Health check interval in seconds"
    )
    health_check_timeout: int = Field(
        default=10, 
        ge=1, 
        description="Health check timeout in seconds"
    )
    
    # Sentry configuration
    sentry_dsn: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    sentry_environment: str = Field(default="development", description="Sentry environment")
    sentry_traces_sample_rate: float = Field(
        default=0.1, 
        ge=0.0, 
        le=1.0, 
        description="Sentry traces sample rate"
    )


class FeatureFlagsConfig(BaseModel):
    """Feature flags configuration."""
    
    enable_web_interface: bool = Field(default=True, description="Enable web interface")
    enable_api_docs: bool = Field(default=True, description="Enable API documentation")
    enable_knowledge_graph: bool = Field(default=True, description="Enable knowledge graph")
    enable_evaluation_reports: bool = Field(
        default=True, 
        description="Enable evaluation reports"
    )
    enable_batch_processing: bool = Field(
        default=False, 
        description="Enable batch processing"
    )
    enable_real_time_monitoring: bool = Field(
        default=False, 
        description="Enable real-time monitoring"
    )
    
    # Experimental features
    enable_experimental_agents: bool = Field(
        default=False, 
        description="Enable experimental agents"
    )
    enable_advanced_validation: bool = Field(
        default=False, 
        description="Enable advanced validation"
    )
    enable_ml_optimization: bool = Field(
        default=False, 
        description="Enable ML optimization features"
    )


class Settings(BaseSettings):
    """Main application settings with nested configurations."""
    
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )
    
    # Environment and basic settings
    environment: str = Field(default="development", description="Application environment")
    debug: bool = Field(default=True, description="Global debug mode")
    verbose: bool = Field(default=False, description="Verbose logging")
    
    # Nested configuration sections
    mcp_server: ServerConfig = Field(default_factory=ServerConfig)
    agents: AgentConfig = Field(default_factory=AgentConfig)
    data: DataConfig = Field(default_factory=DataConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    external_services: ExternalServicesConfig = Field(default_factory=ExternalServicesConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    feature_flags: FeatureFlagsConfig = Field(default_factory=FeatureFlagsConfig)
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment setting."""
        valid_envs = {"development", "testing", "staging", "production"}
        if v.lower() not in valid_envs:
            raise ValueError(f"Environment must be one of: {valid_envs}")
        return v.lower()
    
    @model_validator(mode='after')
    def validate_configuration_consistency(self) -> 'Settings':
        """Validate configuration consistency across sections."""
        # Ensure debug mode consistency
        if self.debug and self.environment == "production":
            raise ValueError("Debug mode should not be enabled in production")
        
        # Validate security settings for production
        if self.environment == "production":
            if not self.security.secret_key:
                raise ValueError("Secret key is required in production")
        
        return self
    
    def get_log_config(self) -> Dict[str, Any]:
        """Get logging configuration dictionary."""
        return {
            "level": self.mcp_server.log_level,
            "format": "json" if self.environment == "production" else "console",
            "debug": self.debug,
            "verbose": self.verbose
        }
    
    def get_database_url(self) -> str:
        """Get the database connection URL."""
        return self.database.url or "sqlite:///./agentic_converter.db"
    
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"
    
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS origins with environment-specific defaults."""
        if self.is_production():
            # In production, be more restrictive with CORS
            return [origin for origin in self.mcp_server.cors_origins if origin != "*"]
        return self.mcp_server.cors_origins


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance.
    
    This function provides a way to access settings that can be easily
    mocked in tests or overridden in different contexts.
    
    Returns:
        Settings: The global settings instance
    """
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment variables and config files.
    
    This is useful for testing or when configuration changes at runtime.
    
    Returns:
        Settings: The reloaded settings instance
    """
    global settings
    settings = Settings()
    return settings


def validate_settings() -> None:
    """Validate current settings and raise errors if invalid.
    
    This function performs additional validation beyond what Pydantic
    provides, checking for runtime conditions and dependencies.
    
    Raises:
        ValueError: If settings are invalid
        FileNotFoundError: If required files/directories don't exist
    """
    # Validate required directories exist and are writable
    for dir_path in [settings.data.output_dir, settings.data.temp_dir, settings.data.cache_dir]:
        path = Path(dir_path)
        if not path.exists():
            raise FileNotFoundError(f"Required directory does not exist: {dir_path}")
        if not os.access(path, os.W_OK):
            raise PermissionError(f"Directory is not writable: {dir_path}")
    
    # Validate API keys are present if using external services
    if settings.agents.conversation_model.startswith("gpt-") and not settings.agents.openai_api_key:
        raise ValueError("OpenAI API key is required for GPT models")
    
    if settings.agents.conversation_model.startswith("claude-") and not settings.agents.anthropic_api_key:
        raise ValueError("Anthropic API key is required for Claude models")
    
    # Validate database URL format
    db_url = settings.get_database_url()
    if not db_url.startswith(("sqlite://", "postgresql://", "mysql://", "oracle://")):
        raise ValueError(f"Unsupported database URL format: {db_url}")
    
    # Validate port availability (basic check)
    if settings.mcp_server.port == settings.monitoring.metrics_port:
        raise ValueError("MCP server port and metrics port cannot be the same")


# Export commonly used configurations for convenience
__all__ = [
    "Settings",
    "ServerConfig", 
    "AgentConfig",
    "DataConfig",
    "DatabaseConfig",
    "ExternalServicesConfig",
    "SecurityConfig",
    "PerformanceConfig",
    "MonitoringConfig",
    "FeatureFlagsConfig",
    "settings",
    "get_settings",
    "reload_settings",
    "validate_settings"
]