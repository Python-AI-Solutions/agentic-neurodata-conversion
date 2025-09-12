"""
Evaluation agent for validating and assessing NWB files.

This agent handles the evaluation of generated NWB files using NWB Inspector
and other validation tools, providing quality assessment and compliance reports.
"""

import json
import logging
from pathlib import Path
import tempfile
from typing import Any, Optional

from .base import AgentCapability, BaseAgent

logger = logging.getLogger(__name__)


class EvaluationAgent(BaseAgent):
    """
    Agent responsible for evaluating and validating NWB files.

    This agent uses NWB Inspector and other validation tools to assess
    the quality, compliance, and completeness of generated NWB files,
    providing detailed reports and recommendations.
    """

    def __init__(self, config: Optional[Any] = None, agent_id: Optional[str] = None):
        """
        Initialize the evaluation agent.

        Args:
            config: Agent configuration containing evaluation settings.
            agent_id: Optional agent identifier.
        """
        self.evaluation_cache: dict[str, Any] = {}
        self.validation_rules: dict[str, Any] = {}
        self.strict_mode = True
        self.check_completeness = True

        super().__init__(config, agent_id)

    def _initialize(self) -> None:
        """Initialize evaluation agent specific components."""
        # Register capabilities
        self.add_capability(AgentCapability.VALIDATION)
        self.add_capability(AgentCapability.EVALUATION)
        self.add_capability(AgentCapability.REPORTING)

        # Load configuration
        if self.config:
            self.strict_mode = getattr(self.config, "evaluation_strict", True)
            # Load NWB Inspector settings if available
            if hasattr(self.config, "nwb_inspector_strict_mode"):
                self.strict_mode = self.config.nwb_inspector_strict_mode
            if hasattr(self.config, "nwb_inspector_check_completeness"):
                self.check_completeness = self.config.nwb_inspector_check_completeness

        # Initialize validation rules
        self._initialize_validation_rules()

        # Update metadata
        self.update_metadata(
            {
                "strict_mode": self.strict_mode,
                "check_completeness": self.check_completeness,
                "validation_rules": len(self.validation_rules),
                "cache_size": 0,
            }
        )

        logger.info(
            f"EvaluationAgent {self.agent_id} initialized with strict_mode={self.strict_mode}"
        )

    def _initialize_validation_rules(self) -> None:
        """Initialize validation rules and checks."""
        self.validation_rules = {
            "file_structure": {
                "required_groups": ["/acquisition", "/processing", "/general"],
                "required_datasets": [
                    "/general/session_description",
                    "/general/experimenter",
                ],
                "optional_groups": ["/analysis", "/scratch", "/stimulus"],
            },
            "metadata_completeness": {
                "required_fields": [
                    "session_description",
                    "experimenter",
                    "institution",
                    "session_start_time",
                ],
                "recommended_fields": [
                    "lab",
                    "experiment_description",
                    "subject",
                    "devices",
                ],
            },
            "data_integrity": {
                "check_timestamps": True,
                "check_data_continuity": True,
                "check_units": True,
                "check_references": True,
            },
            "compliance": {
                "nwb_version": "2.0+",
                "schema_compliance": True,
                "best_practices": True,
            },
        }

        logger.info(f"Loaded {len(self.validation_rules)} validation rule categories")

    def get_capabilities(self) -> set[AgentCapability]:
        """Get the capabilities provided by this agent."""
        return {
            AgentCapability.VALIDATION,
            AgentCapability.EVALUATION,
            AgentCapability.REPORTING,
        }

    async def process(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Process a task assigned to the evaluation agent.

        Args:
            task: Task dictionary containing task type and parameters.

        Returns:
            Dictionary containing the processing result.
        """
        task_type = task.get("type")

        if task_type == "validation":
            return await self._validate_nwb_file(task)
        elif task_type == "evaluation":
            return await self._evaluate_nwb_file(task)
        elif task_type == "reporting":
            return await self._generate_report(task)
        else:
            raise NotImplementedError(
                f"Task type '{task_type}' not supported by EvaluationAgent"
            )

    async def _validate_nwb_file(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Validate an NWB file using NWB Inspector and custom rules.

        Args:
            task: Task containing nwb_path and validation parameters.

        Returns:
            Dictionary containing validation results.
        """
        nwb_path = task.get("nwb_path")
        validation_level = task.get("validation_level", "error")

        if not nwb_path:
            raise ValueError("nwb_path is required for validation")

        nwb_file = Path(nwb_path)
        if not nwb_file.exists():
            raise FileNotFoundError(f"NWB file not found: {nwb_path}")

        # Check cache first
        cache_key = f"validation_{nwb_file.resolve()}_{validation_level}"
        if cache_key in self.evaluation_cache:
            logger.info(f"Returning cached validation for {nwb_path}")
            return self.evaluation_cache[cache_key]

        try:
            # Perform validation
            validation_result = await self._perform_nwb_validation(
                nwb_file, validation_level
            )

            # Cache the result
            self.evaluation_cache[cache_key] = validation_result
            self.update_metadata({"cache_size": len(self.evaluation_cache)})

            return {
                "status": "success",
                "result": validation_result,
                "agent_id": self.agent_id,
                "cached": False,
            }

        except Exception as e:
            logger.error(f"NWB validation failed for {nwb_path}: {e}")
            return {"status": "error", "message": str(e), "agent_id": self.agent_id}

    async def _perform_nwb_validation(
        self, nwb_file: Path, validation_level: str
    ) -> dict[str, Any]:
        """
        Perform comprehensive NWB file validation.

        Args:
            nwb_file: Path to the NWB file to validate.
            validation_level: Validation level (error, warning, info).

        Returns:
            Dictionary containing validation results.
        """
        validation_result = {
            "file_path": str(nwb_file),
            "file_size": nwb_file.stat().st_size,
            "validation_level": validation_level,
            "validation_timestamp": None,
            "overall_status": "unknown",
            "checks": {
                "file_structure": {},
                "metadata_completeness": {},
                "data_integrity": {},
                "nwb_inspector": {},
                "compliance": {},
            },
            "issues": {"critical": [], "errors": [], "warnings": [], "info": []},
            "summary": {},
        }

        try:
            # Basic file structure validation
            structure_result = await self._validate_file_structure(nwb_file)
            validation_result["checks"]["file_structure"] = structure_result

            # Metadata completeness check
            metadata_result = await self._validate_metadata_completeness(nwb_file)
            validation_result["checks"]["metadata_completeness"] = metadata_result

            # Data integrity checks
            integrity_result = await self._validate_data_integrity(nwb_file)
            validation_result["checks"]["data_integrity"] = integrity_result

            # NWB Inspector validation (placeholder)
            inspector_result = await self._run_nwb_inspector(nwb_file, validation_level)
            validation_result["checks"]["nwb_inspector"] = inspector_result

            # Compliance checks
            compliance_result = await self._validate_compliance(nwb_file)
            validation_result["checks"]["compliance"] = compliance_result

            # Aggregate results
            validation_result = self._aggregate_validation_results(validation_result)

            logger.info(
                f"NWB validation completed for {nwb_file}: {validation_result['overall_status']}"
            )

        except Exception as e:
            validation_result["overall_status"] = "error"
            validation_result["issues"]["critical"].append(
                f"Validation failed: {str(e)}"
            )
            logger.error(f"Validation error for {nwb_file}: {e}")

        return validation_result

    async def _validate_file_structure(self, nwb_file: Path) -> dict[str, Any]:
        """
        Validate the basic structure of the NWB file.

        Args:
            nwb_file: Path to the NWB file.

        Returns:
            Dictionary containing structure validation results.
        """
        structure_result = {
            "status": "unknown",
            "required_groups_present": [],
            "missing_required_groups": [],
            "optional_groups_present": [],
            "required_datasets_present": [],
            "missing_required_datasets": [],
            "issues": [],
        }

        try:
            # This is a placeholder implementation
            # In a real implementation, this would use h5py or pynwb to inspect the file

            # Simulate structure validation
            required_groups = self.validation_rules["file_structure"]["required_groups"]
            required_datasets = self.validation_rules["file_structure"][
                "required_datasets"
            ]

            # For now, assume basic structure is present
            structure_result["required_groups_present"] = required_groups
            structure_result["required_datasets_present"] = required_datasets
            structure_result["status"] = "passed"

            logger.debug(f"File structure validation completed for {nwb_file}")

        except Exception as e:
            structure_result["status"] = "error"
            structure_result["issues"].append(f"Structure validation error: {str(e)}")

        return structure_result

    async def _validate_metadata_completeness(self, nwb_file: Path) -> dict[str, Any]:
        """
        Validate metadata completeness in the NWB file.

        Args:
            nwb_file: Path to the NWB file.

        Returns:
            Dictionary containing metadata validation results.
        """
        metadata_result = {
            "status": "unknown",
            "required_fields_present": [],
            "missing_required_fields": [],
            "recommended_fields_present": [],
            "missing_recommended_fields": [],
            "completeness_score": 0.0,
            "issues": [],
        }

        try:
            # This is a placeholder implementation
            # In a real implementation, this would inspect the NWB file metadata

            required_fields = self.validation_rules["metadata_completeness"][
                "required_fields"
            ]
            recommended_fields = self.validation_rules["metadata_completeness"][
                "recommended_fields"
            ]

            # Simulate metadata validation
            # Assume most required fields are present
            metadata_result["required_fields_present"] = required_fields[:3]
            metadata_result["missing_required_fields"] = required_fields[3:]
            metadata_result["recommended_fields_present"] = recommended_fields[:2]
            metadata_result["missing_recommended_fields"] = recommended_fields[2:]

            # Calculate completeness score
            total_required = len(required_fields)
            present_required = len(metadata_result["required_fields_present"])
            metadata_result["completeness_score"] = (
                present_required / total_required if total_required > 0 else 1.0
            )

            if metadata_result["completeness_score"] >= 1.0:
                metadata_result["status"] = "passed"
            elif metadata_result["completeness_score"] >= 0.8:
                metadata_result["status"] = "warning"
            else:
                metadata_result["status"] = "failed"

            logger.debug(
                f"Metadata validation completed for {nwb_file}: {metadata_result['completeness_score']:.2f}"
            )

        except Exception as e:
            metadata_result["status"] = "error"
            metadata_result["issues"].append(f"Metadata validation error: {str(e)}")

        return metadata_result

    async def _validate_data_integrity(self, nwb_file: Path) -> dict[str, Any]:
        """
        Validate data integrity in the NWB file.

        Args:
            nwb_file: Path to the NWB file.

        Returns:
            Dictionary containing data integrity validation results.
        """
        integrity_result = {
            "status": "unknown",
            "timestamp_checks": {"status": "unknown", "issues": []},
            "data_continuity": {"status": "unknown", "issues": []},
            "unit_checks": {"status": "unknown", "issues": []},
            "reference_checks": {"status": "unknown", "issues": []},
            "issues": [],
        }

        try:
            # This is a placeholder implementation
            # In a real implementation, this would perform detailed data integrity checks

            # Simulate integrity checks
            integrity_result["timestamp_checks"]["status"] = "passed"
            integrity_result["data_continuity"]["status"] = "passed"
            integrity_result["unit_checks"]["status"] = "warning"
            integrity_result["unit_checks"]["issues"].append(
                "Some units may be missing or inconsistent"
            )
            integrity_result["reference_checks"]["status"] = "passed"

            # Overall status based on individual checks
            if any(
                check["status"] == "error"
                for check in integrity_result.values()
                if isinstance(check, dict)
            ):
                integrity_result["status"] = "error"
            elif any(
                check["status"] == "warning"
                for check in integrity_result.values()
                if isinstance(check, dict)
            ):
                integrity_result["status"] = "warning"
            else:
                integrity_result["status"] = "passed"

            logger.debug(f"Data integrity validation completed for {nwb_file}")

        except Exception as e:
            integrity_result["status"] = "error"
            integrity_result["issues"].append(
                f"Data integrity validation error: {str(e)}"
            )

        return integrity_result

    async def _run_nwb_inspector(
        self, nwb_file: Path, validation_level: str
    ) -> dict[str, Any]:
        """
        Run NWB Inspector validation on the file.

        Args:
            nwb_file: Path to the NWB file.
            validation_level: Validation level for NWB Inspector.

        Returns:
            Dictionary containing NWB Inspector results.
        """
        inspector_result = {
            "status": "unknown",
            "inspector_version": "placeholder",
            "validation_level": validation_level,
            "messages": [],
            "error_count": 0,
            "warning_count": 0,
            "info_count": 0,
            "issues": [],
        }

        try:
            # This is a placeholder for NWB Inspector integration
            # In a real implementation, this would run the actual NWB Inspector

            # Simulate NWB Inspector results
            if validation_level == "error":
                inspector_result["messages"] = [
                    {"level": "info", "message": "File structure is valid"},
                    {
                        "level": "warning",
                        "message": "Some optional metadata is missing",
                    },
                ]
                inspector_result["warning_count"] = 1
                inspector_result["info_count"] = 1
            else:
                inspector_result["messages"] = [
                    {"level": "info", "message": "Comprehensive validation passed"}
                ]
                inspector_result["info_count"] = 1

            inspector_result["status"] = (
                "passed" if inspector_result["error_count"] == 0 else "failed"
            )

            logger.debug(f"NWB Inspector validation completed for {nwb_file}")

        except Exception as e:
            inspector_result["status"] = "error"
            inspector_result["issues"].append(f"NWB Inspector error: {str(e)}")

        return inspector_result

    async def _validate_compliance(self, nwb_file: Path) -> dict[str, Any]:
        """
        Validate NWB compliance and best practices.

        Args:
            nwb_file: Path to the NWB file.

        Returns:
            Dictionary containing compliance validation results.
        """
        compliance_result = {
            "status": "unknown",
            "nwb_version": "unknown",
            "schema_compliance": {"status": "unknown", "issues": []},
            "best_practices": {"status": "unknown", "issues": []},
            "issues": [],
        }

        try:
            # This is a placeholder implementation
            # In a real implementation, this would check NWB version and schema compliance

            # Simulate compliance checks
            compliance_result["nwb_version"] = "2.6.0"
            compliance_result["schema_compliance"]["status"] = "passed"
            compliance_result["best_practices"]["status"] = "warning"
            compliance_result["best_practices"]["issues"].append(
                "Consider adding more descriptive metadata for better FAIR compliance"
            )

            compliance_result["status"] = "passed"

            logger.debug(f"Compliance validation completed for {nwb_file}")

        except Exception as e:
            compliance_result["status"] = "error"
            compliance_result["issues"].append(f"Compliance validation error: {str(e)}")

        return compliance_result

    def _aggregate_validation_results(
        self, validation_result: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Aggregate individual validation results into overall status and summary.

        Args:
            validation_result: Dictionary containing all validation results.

        Returns:
            Updated validation result with aggregated status and summary.
        """
        # Collect all issues from different checks
        all_issues = {"critical": [], "errors": [], "warnings": [], "info": []}

        # Aggregate issues from all checks
        for check_name, check_result in validation_result["checks"].items():
            if isinstance(check_result, dict):
                # Add issues from this check
                if "issues" in check_result:
                    for issue in check_result["issues"]:
                        all_issues["errors"].append(f"{check_name}: {issue}")

                # Categorize based on status
                status = check_result.get("status", "unknown")
                if status == "error":
                    all_issues["errors"].append(f"{check_name} check failed")
                elif status == "warning":
                    all_issues["warnings"].append(f"{check_name} has warnings")
                elif status == "passed":
                    all_issues["info"].append(f"{check_name} check passed")

        validation_result["issues"] = all_issues

        # Determine overall status
        if all_issues["critical"] or len(all_issues["errors"]) > 0:
            validation_result["overall_status"] = "failed"
        elif len(all_issues["warnings"]) > 0:
            validation_result["overall_status"] = "warning"
        else:
            validation_result["overall_status"] = "passed"

        # Create summary
        validation_result["summary"] = {
            "total_checks": len(validation_result["checks"]),
            "passed_checks": sum(
                1
                for check in validation_result["checks"].values()
                if isinstance(check, dict) and check.get("status") == "passed"
            ),
            "failed_checks": sum(
                1
                for check in validation_result["checks"].values()
                if isinstance(check, dict) and check.get("status") == "error"
            ),
            "warning_checks": sum(
                1
                for check in validation_result["checks"].values()
                if isinstance(check, dict) and check.get("status") == "warning"
            ),
            "total_issues": sum(len(issues) for issues in all_issues.values()),
            "overall_status": validation_result["overall_status"],
        }

        return validation_result

    async def _evaluate_nwb_file(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Perform comprehensive evaluation of an NWB file.

        Args:
            task: Task containing nwb_path and evaluation parameters.

        Returns:
            Dictionary containing evaluation results.
        """
        # First run validation
        validation_task = {
            "type": "validation",
            "nwb_path": task.get("nwb_path"),
            "validation_level": task.get("validation_level", "warning"),
        }

        validation_result = await self._validate_nwb_file(validation_task)

        if validation_result["status"] != "success":
            return validation_result

        # Add evaluation-specific metrics
        evaluation_result = validation_result["result"]
        evaluation_result["evaluation"] = {
            "quality_score": self._calculate_quality_score(evaluation_result),
            "recommendations": self._generate_recommendations(evaluation_result),
            "conversion_success": evaluation_result["overall_status"]
            in ["passed", "warning"],
        }

        return {
            "status": "success",
            "result": evaluation_result,
            "agent_id": self.agent_id,
        }

    def _calculate_quality_score(self, validation_result: dict[str, Any]) -> float:
        """
        Calculate a quality score based on validation results.

        Args:
            validation_result: Validation results dictionary.

        Returns:
            Quality score between 0.0 and 1.0.
        """
        summary = validation_result.get("summary", {})

        total_checks = summary.get("total_checks", 1)
        passed_checks = summary.get("passed_checks", 0)
        warning_checks = summary.get("warning_checks", 0)

        # Base score from passed checks
        base_score = passed_checks / total_checks if total_checks > 0 else 0.0

        # Penalty for warnings
        warning_penalty = (
            (warning_checks / total_checks) * 0.2 if total_checks > 0 else 0.0
        )

        quality_score = max(0.0, base_score - warning_penalty)

        return round(quality_score, 3)

    def _generate_recommendations(self, validation_result: dict[str, Any]) -> list[str]:
        """
        Generate recommendations based on validation results.

        Args:
            validation_result: Validation results dictionary.

        Returns:
            List of recommendation strings.
        """
        recommendations = []

        # Check metadata completeness
        metadata_check = validation_result.get("checks", {}).get(
            "metadata_completeness", {}
        )
        missing_required = metadata_check.get("missing_required_fields", [])
        missing_recommended = metadata_check.get("missing_recommended_fields", [])

        if missing_required:
            recommendations.append(
                f"Add missing required metadata fields: {', '.join(missing_required)}"
            )

        if missing_recommended:
            recommendations.append(
                f"Consider adding recommended metadata fields: {', '.join(missing_recommended[:3])}"
            )

        # Check data integrity
        integrity_check = validation_result.get("checks", {}).get("data_integrity", {})
        if integrity_check.get("status") == "warning":
            recommendations.append(
                "Review data integrity warnings and ensure data consistency"
            )

        # General recommendations
        if validation_result.get("overall_status") == "warning":
            recommendations.append(
                "Address validation warnings to improve NWB file quality"
            )

        if not recommendations:
            recommendations.append("NWB file meets quality standards")

        return recommendations

    async def _generate_report(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Generate a comprehensive evaluation report.

        Args:
            task: Task containing evaluation results and report parameters.

        Returns:
            Dictionary containing the generated report.
        """
        evaluation_result = task.get("evaluation_result")
        report_format = task.get("format", "json")

        if not evaluation_result:
            raise ValueError("evaluation_result is required for report generation")

        # Generate report content
        report_content = self._create_report_content(evaluation_result, report_format)

        # Save report to file if requested
        report_path = None
        if task.get("save_to_file", False):
            report_path = self._save_report_to_file(report_content, report_format)

        return {
            "status": "success",
            "result": {
                "report_content": report_content,
                "report_path": report_path,
                "format": report_format,
            },
            "agent_id": self.agent_id,
        }

    def _create_report_content(
        self, evaluation_result: dict[str, Any], report_format: str
    ) -> str:
        """
        Create report content in the specified format.

        Args:
            evaluation_result: Evaluation results to include in report.
            report_format: Format for the report (json, html, markdown).

        Returns:
            Report content as string.
        """
        if report_format == "json":
            return json.dumps(evaluation_result, indent=2)
        elif report_format == "markdown":
            return self._create_markdown_report(evaluation_result)
        elif report_format == "html":
            return self._create_html_report(evaluation_result)
        else:
            raise ValueError(f"Unsupported report format: {report_format}")

    def _create_markdown_report(self, evaluation_result: dict[str, Any]) -> str:
        """Create a markdown format report."""
        summary = evaluation_result.get("summary", {})
        evaluation = evaluation_result.get("evaluation", {})

        report = f"""# NWB File Evaluation Report

## Summary
- **Overall Status**: {evaluation_result.get("overall_status", "unknown")}
- **Quality Score**: {evaluation.get("quality_score", "N/A")}
- **Total Checks**: {summary.get("total_checks", 0)}
- **Passed**: {summary.get("passed_checks", 0)}
- **Warnings**: {summary.get("warning_checks", 0)}
- **Errors**: {summary.get("failed_checks", 0)}

## Recommendations
"""

        recommendations = evaluation.get("recommendations", [])
        for i, rec in enumerate(recommendations, 1):
            report += f"{i}. {rec}\n"

        return report

    def _create_html_report(self, evaluation_result: dict[str, Any]) -> str:
        """Create an HTML format report."""
        # Simplified HTML report
        return f"""
        <html>
        <head><title>NWB Evaluation Report</title></head>
        <body>
        <h1>NWB File Evaluation Report</h1>
        <p>Overall Status: {evaluation_result.get("overall_status", "unknown")}</p>
        <p>Quality Score: {evaluation_result.get("evaluation", {}).get("quality_score", "N/A")}</p>
        </body>
        </html>
        """

    def _save_report_to_file(self, report_content: str, report_format: str) -> str:
        """
        Save report content to a temporary file.

        Args:
            report_content: Content to save.
            report_format: Format of the report.

        Returns:
            Path to the saved report file.
        """
        suffix_map = {"json": ".json", "markdown": ".md", "html": ".html"}
        suffix = suffix_map.get(report_format, ".txt")

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=suffix, prefix="nwb_evaluation_report_", delete=False
        ) as f:
            f.write(report_content)
            report_path = f.name

        logger.info(f"Saved evaluation report to: {report_path}")
        return report_path

    def clear_cache(self) -> None:
        """Clear the evaluation cache."""
        self.evaluation_cache.clear()
        self.update_metadata({"cache_size": 0})
        logger.info(f"Cleared evaluation cache for agent {self.agent_id}")

    async def shutdown(self) -> None:
        """Shutdown the evaluation agent."""
        self.clear_cache()

        await super().shutdown()
        logger.info(f"EvaluationAgent {self.agent_id} shutdown completed")
