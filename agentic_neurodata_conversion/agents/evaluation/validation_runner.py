"""Validation runner module for evaluation agent.

Handles:
- NWB Inspector execution
- Validation result processing
- Inspector version tracking
"""

import logging

from agentic_neurodata_conversion.models import ValidationResult

logger = logging.getLogger(__name__)


class ValidationRunner:
    """Handles NWB Inspector validation execution.

    Manages the core validation workflow:
    - Running NWBInspector on NWB files
    - Converting inspector results to internal format
    - Tracking inspector version for reproducibility
    """

    def __init__(self):
        """Initialize validation runner."""
        pass

    async def run_nwb_inspector(self, nwb_path: str) -> ValidationResult:
        """Run NWB Inspector validation.

        Executes NWBInspector on the specified NWB file and converts
        the results to our internal ValidationResult format.

        Args:
            nwb_path: Path to NWB file

        Returns:
            ValidationResult object containing:
            - is_valid: Whether file passes validation
            - issues: List of validation issues
            - summary: Counts by severity level
            - inspector_version: Version of NWBInspector used

        Raises:
            Exception: If validation cannot be run (file not found,
                      inspector error, etc.)
        """
        from nwbinspector import __version__ as inspector_version
        from nwbinspector import inspect_nwbfile

        logger.info(f"Running NWB Inspector (v{inspector_version}) on: {nwb_path}")

        # Run NWB Inspector
        results = list(inspect_nwbfile(nwbfile_path=nwb_path))

        logger.debug(f"NWB Inspector found {len(results)} check results")

        # Convert to our format
        inspector_results = []
        for check_result in results:
            inspector_results.append(
                {
                    "severity": check_result.severity.name.lower(),
                    "message": check_result.message,
                    "location": str(check_result.location) if hasattr(check_result, "location") else None,
                    "check_function_name": check_result.check_function_name,
                }
            )

        # Create ValidationResult from inspector output
        validation_result = ValidationResult.from_inspector_output(
            inspector_results,
            inspector_version,
        )

        logger.info(f"Validation complete: {validation_result.summary} (valid: {validation_result.is_valid})")

        return validation_result
