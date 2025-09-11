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

"""Configuration loading utilities for different deployment scenarios.

This module provides utilities for loading configuration from various sources
and setting up the application for different environments.
"""

import logging
import os
from pathlib import Path
from typing import Optional, Union

from .config import (
    ConfigurationError,
    ConfigurationManager,
    CoreConfig,
    Environment,
    configure_logging,
)


def load_config_for_environment(
    environment: Optional[Union[str, Environment]] = None,
    config_file: Optional[Union[str, Path]] = None,
) -> CoreConfig:
    """Load configuration for a specific environment.

    Args:
        environment: Target environment (development, testing, staging, production)
        config_file: Optional path to configuration file

    Returns:
        Loaded configuration for the environment.

    Raises:
        ConfigurationError: If configuration cannot be loaded.
    """
    # Determine environment
    if environment is None:
        environment = os.getenv("ANC_ENVIRONMENT", "development")

    if isinstance(environment, str):
        try:
            environment = Environment(environment.lower())
        except ValueError:
            raise ConfigurationError(f"Invalid environment: {environment}") from None

    # Determine config file path
    if config_file is None:
        # Look for environment-specific config file
        config_dir = Path("config")
        env_config_file = config_dir / f"{environment.value}.json"

        if env_config_file.exists():
            config_file = env_config_file
        else:
            # Fall back to default config
            default_config_file = config_dir / "default.json"
            if default_config_file.exists():
                config_file = default_config_file

    # Load configuration
    config_manager = ConfigurationManager(config_file)
    config = config_manager.load_config()

    # Override environment if specified
    if config.environment != environment:
        config.environment = environment

    return config


def setup_application_config(
    environment: Optional[str] = None,
    config_file: Optional[str] = None,
    log_level: Optional[str] = None,
) -> CoreConfig:
    """Set up application configuration and logging.

    This is the main entry point for configuring the application.

    Args:
        environment: Target environment
        config_file: Optional path to configuration file
        log_level: Optional log level override

    Returns:
        Configured application settings.
    """
    try:
        # Load configuration
        config = load_config_for_environment(environment, config_file)

        # Override log level if specified
        if log_level:
            config.logging.level = log_level.upper()

        # Configure logging
        configure_logging(config.logging)

        # Log configuration summary
        logger = logging.getLogger(__name__)
        logger.info(
            f"Application configured for environment: {config.environment.value}"
        )
        logger.info(f"Debug mode: {config.debug}")
        logger.info(f"Data directory: {config.data_directory}")
        logger.info(f"HTTP server: {config.http.host}:{config.http.port}")
        logger.info(f"MCP transport: {config.mcp.transport_type}")

        return config

    except Exception as e:
        # Use basic logging if configuration fails
        logging.basicConfig(level=logging.ERROR)
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to configure application: {e}")
        raise


def get_config_for_mcp() -> CoreConfig:
    """Get configuration optimized for MCP usage.

    Returns:
        Configuration with MCP-specific optimizations.
    """
    config = load_config_for_environment()

    # MCP-specific optimizations
    config.performance.enable_compression = config.mcp.enable_message_compression
    config.logging.enable_structured_logging = False  # MCP prefers simple logging

    return config


def get_config_for_http() -> CoreConfig:
    """Get configuration optimized for HTTP usage.

    Returns:
        Configuration with HTTP-specific optimizations.
    """
    config = load_config_for_environment()

    # HTTP-specific optimizations
    config.performance.enable_compression = True  # HTTP benefits from compression
    config.logging.enable_structured_logging = True  # HTTP can use structured logs

    return config


def create_development_config() -> CoreConfig:
    """Create a development configuration with sensible defaults.

    Returns:
        Development configuration.
    """
    config = CoreConfig()
    config.environment = Environment.DEVELOPMENT
    config.debug = True

    # Development-friendly settings
    config.logging.level = "DEBUG"
    config.logging.enable_file_logging = False
    config.agents.timeout_seconds = 120
    config.tools.default_timeout_seconds = 60
    config.sessions.max_active_sessions = 10
    config.security.enable_authentication = False
    config.performance.enable_profiling = True
    config.performance.profiling_sample_rate = 0.1

    # HTTP settings for development
    config.http.host = "127.0.0.1"
    config.http.port = 8000
    config.http.enable_openapi = True
    config.http.enable_request_logging = True

    # MCP settings for development
    config.mcp.transport_type = "stdio"
    config.mcp.enable_heartbeat = False

    return config


def create_testing_config() -> CoreConfig:
    """Create a testing configuration with minimal resources.

    Returns:
        Testing configuration.
    """
    config = CoreConfig()
    config.environment = Environment.TESTING
    config.debug = True

    # Testing-optimized settings
    config.logging.level = "WARNING"
    config.logging.enable_file_logging = False
    config.agents.timeout_seconds = 30
    config.agents.max_concurrent_tasks = 2
    config.tools.default_timeout_seconds = 15
    config.tools.enable_metrics = False
    config.sessions.max_active_sessions = 5
    config.sessions.session_timeout_minutes = 2
    config.security.enable_authentication = False
    config.performance.worker_pool_size = 1
    config.performance.cache_size_mb = 32

    # HTTP settings for testing
    config.http.host = "127.0.0.1"
    config.http.port = 8001
    config.http.enable_websockets = False
    config.http.enable_request_logging = False

    # MCP settings for testing
    config.mcp.transport_type = "stdio"
    config.mcp.enable_heartbeat = False
    config.mcp.max_message_size_kb = 256

    return config


def validate_deployment_config(config: CoreConfig) -> list[str]:
    """Validate configuration for deployment readiness.

    Args:
        config: Configuration to validate.

    Returns:
        List of validation warnings/issues.
    """
    issues = []

    # Production environment checks
    if config.environment == Environment.PRODUCTION:
        if config.debug:
            issues.append("Debug mode should be disabled in production")

        if config.logging.level == "DEBUG":
            issues.append("Debug logging should be disabled in production")

        if not config.security.enable_authentication:
            issues.append("Authentication should be enabled in production")

        if "*" in config.security.allowed_origins:
            issues.append("CORS should be restricted in production")

        if not config.logging.enable_file_logging:
            issues.append("File logging should be enabled in production")

        if config.performance.enable_profiling:
            issues.append("Profiling should be disabled in production")

    # Resource limit checks
    if config.agents.memory_limit_mb and config.agents.memory_limit_mb < 256:
        issues.append("Agent memory limit may be too low")

    if config.sessions.max_active_sessions > 1000:
        issues.append("High session limit may impact performance")

    # Security checks
    if config.security.enable_authentication and not config.security.api_key_header:
        issues.append("API key header not configured with authentication enabled")

    # Performance checks
    if config.performance.worker_pool_size > 16:
        issues.append("High worker pool size may cause resource contention")

    return issues


def print_config_summary(config: CoreConfig) -> None:
    """Print a summary of the current configuration.

    Args:
        config: Configuration to summarize.
    """
    print("\n=== Configuration Summary ===")
    print(f"Environment: {config.environment.value}")
    print(f"Debug Mode: {config.debug}")
    print(f"Data Directory: {config.data_directory}")
    print(f"Temp Directory: {config.temp_directory}")
    print("\n--- HTTP Configuration ---")
    print(f"Host: {config.http.host}")
    print(f"Port: {config.http.port}")
    print(f"WebSockets: {config.http.enable_websockets}")
    print(f"OpenAPI: {config.http.enable_openapi}")
    print("\n--- MCP Configuration ---")
    print(f"Transport: {config.mcp.transport_type}")
    print(f"Socket Path: {config.mcp.socket_path or 'N/A'}")
    print(f"Heartbeat: {config.mcp.enable_heartbeat}")
    print("\n--- Agent Configuration ---")
    print(f"Timeout: {config.agents.timeout_seconds}s")
    print(f"Max Concurrent: {config.agents.max_concurrent_tasks}")
    print(f"Memory Limit: {config.agents.memory_limit_mb or 'Unlimited'} MB")
    print("\n--- Security Configuration ---")
    print(f"Authentication: {config.security.enable_authentication}")
    print(f"CORS: {config.security.enable_cors}")
    print(f"Rate Limit: {config.security.rate_limit_requests_per_minute}/min")
    print("\n--- Logging Configuration ---")
    print(f"Level: {config.logging.level.value}")
    print(f"File Logging: {config.logging.enable_file_logging}")
    print(f"Log File: {config.logging.log_file_path or 'N/A'}")
    print("=" * 30)
