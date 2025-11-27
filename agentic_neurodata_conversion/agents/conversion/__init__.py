"""Conversion agent modules.

Modular components for the conversion agent:
- FormatDetector: Format detection and validation (84+ formats, LLM-first strategy)
- ConversionHelpers: Utilities and metadata mapping
- ConversionErrorHandler: Error explanations and recovery
- ConversionRunner: NeuroConv conversion execution (84+ formats, progress monitoring)

Week 4 Refactoring - COMPLETE:
- 4 of 4 modules implemented (100%)
- 1,836 lines extracted from conversion_agent.py into focused modules
- All modules production-ready with comprehensive documentation
"""

from .conversion_helpers import ConversionHelpers
from .conversion_runner import ConversionRunner
from .error_handling import ConversionErrorHandler
from .format_detection import FormatDetector

__all__ = [
    "FormatDetector",
    "ConversionHelpers",
    "ConversionErrorHandler",
    "ConversionRunner",
]
