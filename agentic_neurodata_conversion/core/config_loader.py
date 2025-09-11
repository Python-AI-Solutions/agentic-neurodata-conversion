"""Configuration loader utilities for environment-specific configuration management.

This module provides utilities for loading configuration files based on environment
variables and deployment contexts, making it easy to switch between different
configurations for development, testing, staging, and production environments.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Union, Dict, Any

from .config import ConfigurationManager, CoreConfig, Environment


class EnvironmentConfigLoader:
    """Loads configuration based on environment variables and deployment context."""
    
    def __init__(self, config_dir: Optional[Union[str, Path]] = None):
        """Initialize environment config loader.
        
        Args:
            config_dir: Directory containing configuration files (defaults to ./config)
        """
        self.config_dir = Path(config_dir) if config_dir else Path("config")
        self.logger = logging.getLogger(__name__)
    
    def load_for_environment(self, environment: Optional[str] = None) -> CoreConfig:
        """Load configuration for specified environment.
        
        Args:
            environment: Environment name (development, testing, staging, production).
                        If None, uses ANC_ENVIRONMENT env var or defaults to development.
        
        Returns:
            Loaded configuration for the environment.
        """
        # Determine environment
        env = environment or os.getenv("ANC_ENVIRONMENT", "development")
        
        try:
            # Validate environment
            env_enum = Environment(env.lower())
        except ValueError:
            self.logger.warning(f"Invalid environment '{env}', defaulting to development")
            env_enum = Environment.DEVELOPMENT
            env = "development"
        
        # Load configuration file for environment
        config_file = self.config_dir / f"{env}.json"
        
        if not config_file.exists():
            self.logger.warning(f"Configuration file not found: {config_file}")
            # Fall back to default configuration
            config_file = self.config_dir / "default.json"
            
            if not config_file.exists():
                self.logger.warning("Default configuration file not found, using built-in defaults")
                config_file = None
        
        # Create configuration manager and load config
        config_manager = ConfigurationManager(config_file)
        config = config_manager.load_config()
        
        # Ensure environment is set correctly
        config.environment = env_enum
        
        self.logger.info(f"Loaded configuration for environment: {env}")
        return config
    
    def get_available_environments(self) -> Dict[str, bool]:
        """Get list of available environment configurations.
        
        Returns:
            Dictionary mapping environment names to whether config file exists.
        """
        environments = {}
        
        for env in Environment:
            config_file = self.config_dir / f"{env.value}.json"
            environments[env.value] = config_file.exists()
        
        return environments
    
    def validate_environment_configs(self) -> Dict[str, Dict[str, Any]]:
        """Validate all environment configuration files.
        
        Returns:
            Dictionary with validation results for each environment.
        """
        results = {}
        
        for env in Environment:
            config_file = self.config_dir / f"{env.value}.json"
            
            if not config_file.exists():
                results[env.value] = {
                    "exists": False,
                    "valid": False,
                    "error": "Configuration file not found"
                }
                continue
            
            try:
                config_manager = ConfigurationManager(config_file)
                config = config_manager.load_config()
                
                results[env.value] = {
                    "exists": True,
                    "valid": True,
                    "environment": config.environment.value,
                    "debug": config.debug,
                    "agents_timeout": config.agents.timeout_seconds,
                    "http_port": config.http.port,
                    "mcp_transport": config.mcp.transport_type
                }
                
            except Exception as e:
                results[env.value] = {
                    "exists": True,
                    "valid": False,
                    "error": str(e)
                }
        
        return results


class DeploymentConfigManager:
    """Manages configuration for different deployment scenarios."""
    
    def __init__(self):
        """Initialize deployment config manager."""
        self.logger = logging.getLogger(__name__)
    
    def get_docker_config(self) -> CoreConfig:
        """Get configuration optimized for Docker deployment.
        
        Returns:
            Configuration suitable for Docker containers.
        """
        loader = EnvironmentConfigLoader()
        config = loader.load_for_environment("production")
        
        # Docker-specific overrides
        config.data_directory = "/app/data"
        config.temp_directory = "/tmp"
        config.logging.enable_file_logging = False  # Use stdout in containers
        config.http.host = "0.0.0.0"  # Bind to all interfaces
        config.mcp.transport_type = "stdio"  # Prefer stdio in containers
        
        self.logger.info("Applied Docker-specific configuration overrides")
        return config
    
    def get_kubernetes_config(self) -> CoreConfig:
        """Get configuration optimized for Kubernetes deployment.
        
        Returns:
            Configuration suitable for Kubernetes pods.
        """
        loader = EnvironmentConfigLoader()
        config = loader.load_for_environment("production")
        
        # Kubernetes-specific overrides
        config.data_directory = "/data"  # Mounted volume
        config.temp_directory = "/tmp"
        config.logging.enable_file_logging = False  # Use stdout
        config.logging.enable_structured_logging = True  # Better for log aggregation
        config.http.host = "0.0.0.0"
        config.sessions.enable_persistence = False  # Use external storage
        config.performance.enable_profiling = False  # Reduce overhead
        
        # Use environment variables for sensitive config
        if api_key_header := os.getenv("API_KEY_HEADER"):
            config.security.api_key_header = api_key_header
        
        if allowed_origins := os.getenv("ALLOWED_ORIGINS"):
            config.security.allowed_origins = allowed_origins.split(",")
        
        self.logger.info("Applied Kubernetes-specific configuration overrides")
        return config
    
    def get_serverless_config(self) -> CoreConfig:
        """Get configuration optimized for serverless deployment.
        
        Returns:
            Configuration suitable for serverless functions.
        """
        loader = EnvironmentConfigLoader()
        config = loader.load_for_environment("production")
        
        # Serverless-specific overrides
        config.agents.timeout_seconds = 60  # Shorter timeouts
        config.tools.default_timeout_seconds = 30
        config.sessions.max_active_sessions = 10  # Limited concurrency
        config.sessions.enable_persistence = False  # Stateless
        config.performance.worker_pool_size = 1  # Single worker
        config.performance.enable_async_processing = False  # Simpler execution
        config.logging.enable_file_logging = False
        config.logging.enable_structured_logging = True
        
        self.logger.info("Applied serverless-specific configuration overrides")
        return config
    
    def get_development_config(self, enable_debug: bool = True) -> CoreConfig:
        """Get configuration optimized for local development.
        
        Args:
            enable_debug: Whether to enable debug mode.
        
        Returns:
            Configuration suitable for development.
        """
        loader = EnvironmentConfigLoader()
        config = loader.load_for_environment("development")
        
        if enable_debug:
            config.debug = True
            config.logging.level = "DEBUG"
            config.http.enable_openapi = True
            config.performance.enable_profiling = True
            config.performance.profiling_sample_rate = 0.1
        
        self.logger.info("Applied development-specific configuration")
        return config


# Convenience functions for common use cases
def load_config_for_environment(environment: Optional[str] = None) -> CoreConfig:
    """Load configuration for specified environment.
    
    Args:
        environment: Environment name or None to use ANC_ENVIRONMENT env var.
    
    Returns:
        Loaded configuration.
    """
    loader = EnvironmentConfigLoader()
    return loader.load_for_environment(environment)


def load_config_for_deployment(deployment_type: str = "docker") -> CoreConfig:
    """Load configuration for specified deployment type.
    
    Args:
        deployment_type: Type of deployment (docker, kubernetes, serverless, development).
    
    Returns:
        Configuration optimized for deployment type.
    """
    manager = DeploymentConfigManager()
    
    if deployment_type == "docker":
        return manager.get_docker_config()
    elif deployment_type == "kubernetes":
        return manager.get_kubernetes_config()
    elif deployment_type == "serverless":
        return manager.get_serverless_config()
    elif deployment_type == "development":
        return manager.get_development_config()
    else:
        raise ValueError(f"Unknown deployment type: {deployment_type}")


def validate_all_configs() -> Dict[str, Dict[str, Any]]:
    """Validate all environment configuration files.
    
    Returns:
        Validation results for all environments.
    """
    loader = EnvironmentConfigLoader()
    return loader.validate_environment_configs()


def get_config_summary(config: CoreConfig) -> Dict[str, Any]:
    """Get a summary of key configuration settings.
    
    Args:
        config: Configuration to summarize.
    
    Returns:
        Dictionary with key configuration values.
    """
    return {
        "environment": config.environment.value,
        "debug": config.debug,
        "data_directory": config.data_directory,
        "agents": {
            "timeout_seconds": config.agents.timeout_seconds,
            "max_concurrent_tasks": config.agents.max_concurrent_tasks,
            "enable_caching": config.agents.enable_caching
        },
        "http": {
            "host": config.http.host,
            "port": config.http.port,
            "enable_websockets": config.http.enable_websockets,
            "enable_openapi": config.http.enable_openapi
        },
        "mcp": {
            "transport_type": config.mcp.transport_type,
            "enable_heartbeat": config.mcp.enable_heartbeat
        },
        "logging": {
            "level": config.logging.level.value,
            "enable_file_logging": config.logging.enable_file_logging,
            "enable_structured_logging": config.logging.enable_structured_logging
        },
        "security": {
            "enable_authentication": config.security.enable_authentication,
            "enable_cors": config.security.enable_cors,
            "rate_limit_requests_per_minute": config.security.rate_limit_requests_per_minute
        }
    }