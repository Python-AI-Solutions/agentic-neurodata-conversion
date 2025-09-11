# Copyright (c) 2025 Agentic Neurodata Conversion Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Configuration management for the agentic neurodata conversion system.

This module provides centralized configuration management that is transport-agnostic
and supports environment-based configuration for different deployment scenarios.
"""

from dataclasses import asdict, dataclass, field
from enum import Enum
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional, Union


class LogLevel(str, Enum):
    """Supported logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Environment(str, Enum):
    """Supported deployment environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class AgentConfig:
    """Configuration for individual agents."""

    timeout_seconds: int = 300
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    max_concurrent_tasks: int = 5
    memory_limit_mb: Optional[int] = None
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600
    custom_parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolConfig:
    """Configuration for tool execution."""

    default_timeout_seconds: int = 120
    max_concurrent_executions: int = 10
    enable_metrics: bool = True
    metrics_retention_days: int = 30
    custom_tool_paths: list[str] = field(default_factory=list)
    tool_parameters: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class SessionConfig:
    """Configuration for session management."""

    max_active_sessions: int = 100
    session_timeout_minutes: int = 60
    cleanup_interval_minutes: int = 10
    enable_persistence: bool = False
    persistence_path: Optional[str] = None
    max_session_history: int = 1000


@dataclass
class LoggingConfig:
    """Configuration for logging."""

    level: LogLevel = LogLevel.INFO
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    enable_file_logging: bool = False
    log_file_path: Optional[str] = None
    max_log_file_size_mb: int = 100
    log_file_backup_count: int = 5
    enable_structured_logging: bool = False
    log_correlation_id: bool = True


@dataclass
class SecurityConfig:
    """Configuration for security settings."""

    enable_authentication: bool = False
    api_key_header: str = "X-API-Key"
    allowed_origins: list[str] = field(default_factory=lambda: ["*"])
    rate_limit_requests_per_minute: int = 100
    enable_request_validation: bool = True
    max_request_size_mb: int = 100
    enable_cors: bool = True


@dataclass
class PerformanceConfig:
    """Configuration for performance optimization."""

    enable_async_processing: bool = True
    worker_pool_size: int = 4
    queue_max_size: int = 1000
    enable_compression: bool = True
    cache_size_mb: int = 256
    enable_profiling: bool = False
    profiling_sample_rate: float = 0.01


@dataclass
class MCPConfig:
    """Configuration specific to MCP adapter."""

    transport_type: str = "stdio"
    socket_path: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    enable_heartbeat: bool = True
    heartbeat_interval_seconds: int = 30
    max_message_size_kb: int = 1024
    enable_message_compression: bool = False


@dataclass
class HTTPConfig:
    """Configuration specific to HTTP adapter."""

    host: str = "0.0.0.0"
    port: int = 8000
    enable_websockets: bool = True
    websocket_path: str = "/ws"
    enable_openapi: bool = True
    openapi_title: str = "Agentic Neurodata Conversion API"
    openapi_version: str = "1.0.0"
    enable_metrics_endpoint: bool = True
    metrics_path: str = "/metrics"
    health_check_path: str = "/health"
    enable_request_logging: bool = True
    cors_allow_credentials: bool = False


@dataclass
class CoreConfig:
    """Core configuration that applies to all components."""

    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    data_directory: str = "./data"
    temp_directory: str = "./temp"
    max_file_size_mb: int = 1000
    supported_formats: list[str] = field(
        default_factory=lambda: ["nwb", "hdf5", "mat", "csv", "json", "yaml", "pickle"]
    )
    enable_format_validation: bool = True
    enable_metadata_extraction: bool = True

    # Sub-configurations
    agents: AgentConfig = field(default_factory=AgentConfig)
    tools: ToolConfig = field(default_factory=ToolConfig)
    sessions: SessionConfig = field(default_factory=SessionConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    http: HTTPConfig = field(default_factory=HTTPConfig)


class ConfigurationManager:
    """Manages configuration loading, validation, and access."""

    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """Initialize configuration manager.

        Args:
            config_path: Path to configuration file. If None, uses environment variables
                        and defaults.
        """
        self._config: Optional[CoreConfig] = None
        self._config_path = Path(config_path) if config_path else None
        self._logger = logging.getLogger(__name__)

    def load_config(self) -> CoreConfig:
        """Load configuration from file and environment variables.

        Returns:
            Loaded and validated configuration.

        Raises:
            ConfigurationError: If configuration is invalid.
        """
        if self._config is not None:
            return self._config

        # Start with default configuration
        config_dict = asdict(CoreConfig())

        # Load from file if specified
        if self._config_path and self._config_path.exists():
            try:
                with open(self._config_path) as f:
                    file_config = json.load(f)
                config_dict = self._merge_configs(config_dict, file_config)
                self._logger.info(f"Loaded configuration from {self._config_path}")
            except Exception as e:
                self._logger.error(
                    f"Failed to load config file {self._config_path}: {e}"
                )
                raise ConfigurationError(f"Invalid configuration file: {e}") from e

        # Override with environment variables
        env_config = self._load_from_environment()
        config_dict = self._merge_configs(config_dict, env_config)

        # Create and validate configuration object
        try:
            self._config = self._dict_to_config(config_dict)
            self._validate_config(self._config)
            self._logger.info(
                f"Configuration loaded for environment: {self._config.environment}"
            )
            return self._config
        except Exception as e:
            self._logger.error(f"Configuration validation failed: {e}")
            raise ConfigurationError(f"Invalid configuration: {e}") from e

    def get_config(self) -> CoreConfig:
        """Get current configuration, loading if necessary.

        Returns:
            Current configuration.
        """
        if self._config is None:
            return self.load_config()
        return self._config

    def reload_config(self) -> CoreConfig:
        """Reload configuration from sources.

        Returns:
            Reloaded configuration.
        """
        self._config = None
        return self.load_config()

    def save_config(
        self, config: CoreConfig, path: Optional[Union[str, Path]] = None
    ) -> None:
        """Save configuration to file.

        Args:
            config: Configuration to save.
            path: Path to save to. If None, uses the original config path.

        Raises:
            ConfigurationError: If save fails.
        """
        save_path = Path(path) if path else self._config_path
        if not save_path:
            raise ConfigurationError("No save path specified")

        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "w") as f:
                json.dump(asdict(config), f, indent=2, default=str)
            self._logger.info(f"Configuration saved to {save_path}")
        except Exception as e:
            self._logger.error(f"Failed to save configuration: {e}")
            raise ConfigurationError(f"Failed to save configuration: {e}") from e

    def _load_from_environment(self) -> dict[str, Any]:
        """Load configuration from environment variables.

        Returns:
            Configuration dictionary from environment variables.
        """
        env_config = {}

        # Core settings
        if env_val := os.getenv("ANC_ENVIRONMENT"):
            env_config["environment"] = env_val
        if env_val := os.getenv("ANC_DEBUG"):
            env_config["debug"] = env_val.lower() in ("true", "1", "yes")
        if env_val := os.getenv("ANC_DATA_DIRECTORY"):
            env_config["data_directory"] = env_val
        if env_val := os.getenv("ANC_TEMP_DIRECTORY"):
            env_config["temp_directory"] = env_val

        # Logging settings
        logging_config = {}
        if env_val := os.getenv("ANC_LOG_LEVEL"):
            logging_config["level"] = env_val.upper()
        if env_val := os.getenv("ANC_LOG_FILE"):
            logging_config["log_file_path"] = env_val
            logging_config["enable_file_logging"] = True
        if logging_config:
            env_config["logging"] = logging_config

        # HTTP settings
        http_config = {}
        if env_val := os.getenv("ANC_HTTP_HOST"):
            http_config["host"] = env_val
        if env_val := os.getenv("ANC_HTTP_PORT"):
            http_config["port"] = int(env_val)
        if env_val := os.getenv("ANC_ENABLE_WEBSOCKETS"):
            http_config["enable_websockets"] = env_val.lower() in ("true", "1", "yes")
        if http_config:
            env_config["http"] = http_config

        # MCP settings
        mcp_config = {}
        if env_val := os.getenv("ANC_MCP_TRANSPORT"):
            mcp_config["transport_type"] = env_val
        if env_val := os.getenv("ANC_MCP_SOCKET_PATH"):
            mcp_config["socket_path"] = env_val
        if env_val := os.getenv("ANC_MCP_HOST"):
            mcp_config["host"] = env_val
        if env_val := os.getenv("ANC_MCP_PORT"):
            mcp_config["port"] = int(env_val)
        if mcp_config:
            env_config["mcp"] = mcp_config

        # Security settings
        security_config = {}
        if env_val := os.getenv("ANC_ENABLE_AUTH"):
            security_config["enable_authentication"] = env_val.lower() in (
                "true",
                "1",
                "yes",
            )
        if env_val := os.getenv("ANC_API_KEY_HEADER"):
            security_config["api_key_header"] = env_val
        if env_val := os.getenv("ANC_ALLOWED_ORIGINS"):
            security_config["allowed_origins"] = env_val.split(",")
        if security_config:
            env_config["security"] = security_config

        return env_config

    def _merge_configs(
        self, base: dict[str, Any], override: dict[str, Any]
    ) -> dict[str, Any]:
        """Recursively merge configuration dictionaries.

        Args:
            base: Base configuration dictionary.
            override: Override configuration dictionary.

        Returns:
            Merged configuration dictionary.
        """
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def _dict_to_config(self, config_dict: dict[str, Any]) -> CoreConfig:
        """Convert configuration dictionary to CoreConfig object.

        Args:
            config_dict: Configuration dictionary.

        Returns:
            CoreConfig object.
        """
        # Convert string enums to proper enum types
        if "environment" in config_dict and isinstance(config_dict["environment"], str):
            config_dict["environment"] = Environment(config_dict["environment"])

        # Convert nested dictionaries to dataclass objects
        if "agents" in config_dict:
            config_dict["agents"] = AgentConfig(**config_dict["agents"])
        if "tools" in config_dict:
            config_dict["tools"] = ToolConfig(**config_dict["tools"])
        if "sessions" in config_dict:
            config_dict["sessions"] = SessionConfig(**config_dict["sessions"])
        if "logging" in config_dict:
            # Handle LogLevel enum conversion
            logging_dict = config_dict["logging"].copy()
            if "level" in logging_dict and isinstance(logging_dict["level"], str):
                logging_dict["level"] = LogLevel(logging_dict["level"])
            config_dict["logging"] = LoggingConfig(**logging_dict)
        if "security" in config_dict:
            config_dict["security"] = SecurityConfig(**config_dict["security"])
        if "performance" in config_dict:
            config_dict["performance"] = PerformanceConfig(**config_dict["performance"])
        if "mcp" in config_dict:
            config_dict["mcp"] = MCPConfig(**config_dict["mcp"])
        if "http" in config_dict:
            config_dict["http"] = HTTPConfig(**config_dict["http"])

        return CoreConfig(**config_dict)

    def _validate_config(self, config: CoreConfig) -> None:
        """Validate configuration values.

        Args:
            config: Configuration to validate.

        Raises:
            ConfigurationError: If configuration is invalid.
        """
        # Validate directories exist or can be created
        for dir_path in [config.data_directory, config.temp_directory]:
            try:
                Path(dir_path).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                raise ConfigurationError(
                    f"Cannot create directory {dir_path}: {e}"
                ) from e

        # Validate port ranges
        if not (1 <= config.http.port <= 65535):
            raise ConfigurationError(f"Invalid HTTP port: {config.http.port}")

        if config.mcp.port and not (1 <= config.mcp.port <= 65535):
            raise ConfigurationError(f"Invalid MCP port: {config.mcp.port}")

        # Validate timeout values
        if config.agents.timeout_seconds <= 0:
            raise ConfigurationError("Agent timeout must be positive")

        if config.tools.default_timeout_seconds <= 0:
            raise ConfigurationError("Tool timeout must be positive")

        # Validate memory limits
        if config.agents.memory_limit_mb and config.agents.memory_limit_mb <= 0:
            raise ConfigurationError("Memory limit must be positive")

        # Validate file size limits
        if config.max_file_size_mb <= 0:
            raise ConfigurationError("Max file size must be positive")

        # Validate session limits
        if config.sessions.max_active_sessions <= 0:
            raise ConfigurationError("Max active sessions must be positive")

        if config.sessions.session_timeout_minutes <= 0:
            raise ConfigurationError("Session timeout must be positive")


class ConfigurationError(Exception):
    """Raised when configuration is invalid or cannot be loaded."""

    pass


# Global configuration manager instance
_config_manager: Optional[ConfigurationManager] = None


def get_config_manager(
    config_path: Optional[Union[str, Path]] = None,
) -> ConfigurationManager:
    """Get the global configuration manager instance.

    Args:
        config_path: Path to configuration file (only used on first call).

    Returns:
        Configuration manager instance.
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager(config_path)
    return _config_manager


def get_config() -> CoreConfig:
    """Get the current configuration.

    Returns:
        Current configuration.
    """
    return get_config_manager().get_config()


def reload_config() -> CoreConfig:
    """Reload configuration from sources.

    Returns:
        Reloaded configuration.
    """
    return get_config_manager().reload_config()


def configure_logging(config: Optional[LoggingConfig] = None) -> None:
    """Configure logging based on configuration.

    Args:
        config: Logging configuration. If None, uses current config.
    """
    if config is None:
        config = get_config().logging

    # Set logging level
    logging.getLogger().setLevel(getattr(logging, config.level.value))

    # Configure formatter
    formatter = logging.Formatter(config.format)

    # Configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logging.getLogger().addHandler(console_handler)

    # Configure file handler if enabled
    if config.enable_file_logging and config.log_file_path:
        from logging.handlers import RotatingFileHandler

        file_handler = RotatingFileHandler(
            config.log_file_path,
            maxBytes=config.max_log_file_size_mb * 1024 * 1024,
            backupCount=config.log_file_backup_count,
        )
        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)
