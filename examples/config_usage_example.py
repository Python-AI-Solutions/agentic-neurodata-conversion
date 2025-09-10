#!/usr/bin/env python3
"""Example demonstrating how to use the configuration system."""

import os
from pathlib import Path

from agentic_neurodata_conversion.core import (
    settings, 
    get_settings, 
    reload_settings,
    validate_settings
)


def main():
    """Demonstrate configuration system usage."""
    print("=== Configuration System Usage Example ===\n")
    
    # 1. Basic configuration access
    print("1. Basic Configuration Access:")
    print(f"   Environment: {settings.environment}")
    print(f"   Debug mode: {settings.debug}")
    print(f"   MCP Server: {settings.mcp_server.host}:{settings.mcp_server.port}")
    print(f"   Log level: {settings.mcp_server.log_level}")
    
    # 2. Nested configuration access
    print("\n2. Nested Configuration Access:")
    print(f"   Agent model: {settings.agents.conversation_model}")
    print(f"   Conversion timeout: {settings.agents.conversion_timeout}s")
    print(f"   Output directory: {settings.data.output_dir}")
    print(f"   Max file size: {settings.data.max_file_size / (1024*1024):.0f}MB")
    
    # 3. Helper methods
    print("\n3. Helper Methods:")
    print(f"   Is development: {settings.is_development()}")
    print(f"   Is production: {settings.is_production()}")
    print(f"   Database URL: {settings.get_database_url()}")
    
    # 4. Log configuration
    print("\n4. Log Configuration:")
    log_config = settings.get_log_config()
    for key, value in log_config.items():
        print(f"   {key}: {value}")
    
    # 5. Environment variable override example
    print("\n5. Environment Variable Override:")
    print("   Setting MCP_SERVER__PORT=9999...")
    os.environ["MCP_SERVER__PORT"] = "9999"
    
    # Reload settings to pick up the change
    new_settings = reload_settings()
    print(f"   New port: {new_settings.mcp_server.port}")
    
    # Clean up
    del os.environ["MCP_SERVER__PORT"]
    reload_settings()  # Reset to original
    
    # 6. Feature flags
    print("\n6. Feature Flags:")
    flags = settings.feature_flags
    print(f"   Web interface: {flags.enable_web_interface}")
    print(f"   Knowledge graph: {flags.enable_knowledge_graph}")
    print(f"   Batch processing: {flags.enable_batch_processing}")
    
    # 7. Performance settings
    print("\n7. Performance Settings:")
    perf = settings.performance
    print(f"   Max workers: {perf.max_workers}")
    print(f"   Max concurrent conversions: {perf.max_concurrent_conversions}")
    print(f"   Memory limit: {perf.max_memory_usage / (1024**3):.1f}GB")
    
    # 8. External services configuration
    print("\n8. External Services:")
    ext = settings.external_services
    print(f"   NeuroConv backend: {ext.neuroconv_backend}")
    print(f"   NWB Inspector strict: {ext.nwb_inspector_strict_mode}")
    print(f"   LinkML validation: {ext.linkml_validation_level}")
    
    # 9. Configuration validation
    print("\n9. Configuration Validation:")
    try:
        validate_settings()
        print("   ✓ Configuration is valid")
    except Exception as e:
        print(f"   ⚠ Configuration issue: {e}")
    
    print("\n=== Example Complete ===")


if __name__ == "__main__":
    main()