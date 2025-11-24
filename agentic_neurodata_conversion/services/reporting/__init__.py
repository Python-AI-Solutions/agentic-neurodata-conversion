"""Report generation services.

Modular report generation for NWB evaluation results.
Supports HTML, JSON, and Text formats.
"""

from .formatters import ReportFormatters
from .html_generator import HTMLReportGenerator
from .json_generator import JSONReportGenerator
from .text_generator import TextReportGenerator

__all__ = [
    "ReportFormatters",
    "HTMLReportGenerator",
    "JSONReportGenerator",
    "TextReportGenerator",
]
