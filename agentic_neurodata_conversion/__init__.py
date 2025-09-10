"""
Agentic Neurodata Conversion Package

A multi-agent system for converting neuroscience data to NWB format using MCP server architecture.
The system orchestrates dataset analysis, conversion, and validation through specialized agents.
"""

__version__ = "0.1.0"
__author__ = "Agentic Neurodata Conversion Team"
__email__ = "contact@example.com"

# Core imports for package-level access
from .core.config import settings
from .core.exceptions import (
    AgenticConverterError,
    ConfigurationError,
    ConversionError,
    ValidationError
)

__all__ = [
    "settings",
    "AgenticConverterError",
    "ConfigurationError", 
    "ConversionError",
    "ValidationError",
    "__version__"
]