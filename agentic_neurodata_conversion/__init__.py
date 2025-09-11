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

__all__ = [
    "get_config",
    "AgenticConverterError",
    "ConfigurationError",
    "ConversionError",
    "ValidationError",
    "__version__",
]
