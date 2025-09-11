#!/usr/bin/env python3
"""Configuration validation script.

This script validates configuration files for all environments and deployment types,
ensuring they are properly formatted and contain valid values.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agentic_neurodata_conversion.core.config_loader import (
    EnvironmentConfigLoader,
    DeploymentConfigManager,
    validate_all_configs,
    get_config_summary
)
from agentic_neurodata_conversion.core.config import Environment


def validate_environment_configs() -> bool:
    """Validate all environment configuration files.
    
    Returns:
        True if all configurations are valid, False otherwise.
    """
    print("Validating environment configurations...")
    pr