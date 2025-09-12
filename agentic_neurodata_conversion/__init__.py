"""
Agentic Neurodata Conversion Package

A multi-agent system for converting neuroscience data to NWB format using MCP server architecture.
The system orchestrates dataset analysis, conversion, and validation through specialized agents.
"""

__version__ = "0.1.0"
__author__ = "Agentic Neurodata Conversion Team"
__email__ = "contact@example.com"

# Core imports for package-level access
from .core.config import get_config
from .core.exceptions import (
    AgenticConverterError,
    ConfigurationError,
    ConversionError,
    ValidationError,
)

# Interface and utility imports
from .interfaces import (
    LinkMLValidatorInterface,
    NeuroConvInterface,
    NWBInspectorInterface,
)
from .utils import FileUtils, FormatDetector, MetadataProcessor

__all__ = [
    # Core functionality
    "get_config",
    "AgenticConverterError",
    "ConfigurationError",
    "ConversionError",
    "ValidationError",
    # Interfaces
    "NeuroConvInterface",
    "NWBInspectorInterface",
    "LinkMLValidatorInterface",
    # Utilities
    "FileUtils",
    "FormatDetector",
    "MetadataProcessor",
    # Package metadata
    "__version__",
]
