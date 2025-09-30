"""NWB Inspector integration for validation.

This module runs nwbinspector validation and returns structured results.
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from nwbinspector import inspect_nwbfile, Importance


@dataclass
class InspectionMessage:
    """Single inspection message."""
    severity: str
    message: str
    check_name: str
    location: str
    importance: Optional[str] = None


@dataclass
class InspectionResults:
    """Results from NWB Inspector validation."""
    file_path: Path
    messages: list[InspectionMessage] = field(default_factory=list)
    severity_counts: dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        """Initialize severity counts."""
        if not self.severity_counts:
            self.severity_counts = {
                'CRITICAL': 0,
                'ERROR': 0,
                'WARNING': 0,
                'INFO': 0
            }


def run_inspection(nwbfile_path: Path) -> InspectionResults:
    """Run NWB Inspector validation on file.

    Args:
        nwbfile_path: Path to NWB file

    Returns:
        InspectionResults with categorized messages

    Raises:
        FileNotFoundError: If file does not exist
    """
    if not nwbfile_path.exists():
        raise FileNotFoundError(f"NWB file not found: {nwbfile_path}")

    # Run nwbinspector
    messages_iterator = inspect_nwbfile(nwbfile_path=str(nwbfile_path))

    # Convert to our format
    results = InspectionResults(file_path=nwbfile_path)

    for msg in messages_iterator:
        # Map importance to severity
        severity = _map_importance_to_severity(msg.importance)

        inspection_msg = InspectionMessage(
            severity=severity,
            message=msg.message,
            check_name=msg.check_function_name,
            location=msg.location,
            importance=msg.importance.name if msg.importance else None
        )

        results.messages.append(inspection_msg)
        results.severity_counts[severity] += 1

    return results


def _map_importance_to_severity(importance: Importance) -> str:
    """Map nwbinspector Importance to our severity levels.

    Args:
        importance: nwbinspector Importance enum

    Returns:
        Severity string (CRITICAL, ERROR, WARNING, INFO)
    """
    if importance == Importance.CRITICAL:
        return 'CRITICAL'
    elif importance == Importance.ERROR:
        return 'ERROR'
    elif importance == Importance.BEST_PRACTICE_VIOLATION:
        return 'WARNING'
    elif importance == Importance.BEST_PRACTICE_SUGGESTION:
        return 'INFO'
    else:
        return 'INFO'