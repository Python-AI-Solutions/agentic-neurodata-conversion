"""Evaluation agent modules.

Modular components for the evaluation agent:

Week 5 Modules:
- ValidationRunner: NWB Inspector execution and result processing
- FileInspector: NWB file metadata extraction with provenance
- IssueAnalyzer: LLM-powered issue prioritization and quality scoring
- CorrectionAnalyzer: LLM-powered correction analysis and suggestions
- ReportGenerator: Report generation utilities with workflow transparency
"""

from .correction_analyzer import CorrectionAnalyzer
from .file_inspector import FileInspector
from .issue_analyzer import IssueAnalyzer
from .report_generator import ReportGenerator
from .validation_runner import ValidationRunner

__all__ = [
    # Week 5 Modules
    "ValidationRunner",
    "FileInspector",
    "IssueAnalyzer",
    "CorrectionAnalyzer",
    "ReportGenerator",
]
