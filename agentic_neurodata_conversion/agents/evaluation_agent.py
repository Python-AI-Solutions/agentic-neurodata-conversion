"""EvaluationAgent for NWB file validation using NWB Inspector."""

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from nwbinspector import inspect_nwbfile

from agentic_neurodata_conversion.agents.base_agent import BaseAgent
from agentic_neurodata_conversion.config import settings
from agentic_neurodata_conversion.models.mcp_message import MCPMessage
from agentic_neurodata_conversion.models.session_context import (
    ValidationIssue,
    ValidationResults,
    WorkflowStage,
)


class EvaluationAgent(BaseAgent):
    """Evaluation agent for NWB file validation using NWB Inspector."""

    def get_capabilities(self) -> list[str]:
        """
        Return evaluation agent capabilities.

        Returns:
            List of capability strings
        """
        return ["validate_nwb"]

    async def handle_message(self, message: MCPMessage) -> dict[str, Any]:
        """
        Handle incoming MCP message.

        Routes to appropriate handler based on action type.

        Args:
            message: MCP message to handle

        Returns:
            Result dictionary with status and any relevant data
        """
        action = message.payload.get("action", "")

        if action == "validate_nwb":
            return await self._validate_nwb_full(message.session_id or "unknown")
        else:
            return {
                "status": "error",
                "message": f"Unknown action: {action}",
                "session_id": message.session_id or "unknown",
            }

    async def _validate_nwb(
        self, nwb_file_path: str
    ) -> tuple[str, dict[str, int], list[ValidationIssue]]:
        """
        Validate NWB file using NWB Inspector.

        Args:
            nwb_file_path: Path to NWB file to validate

        Returns:
            Tuple of (overall_status, issue_count, issues)
            - overall_status: "passed", "passed_with_warnings", or "failed"
            - issue_count: Dictionary with counts by severity
            - issues: List of ValidationIssue objects

        Raises:
            FileNotFoundError: If NWB file does not exist
            Exception: If NWB file is corrupt or invalid
        """
        # Check if file exists
        nwb_path = Path(nwb_file_path)
        if not nwb_path.exists():
            raise FileNotFoundError(f"NWB file not found: {nwb_file_path}")

        # Run NWB Inspector validation
        inspector_issues = list(inspect_nwbfile(nwbfile_path=nwb_file_path))

        # Initialize counters
        issue_count = {
            "CRITICAL": 0,
            "BEST_PRACTICE_VIOLATION": 0,
            "BEST_PRACTICE_SUGGESTION": 0,
        }

        # Convert inspector issues to ValidationIssue objects
        issues: list[ValidationIssue] = []
        for inspector_issue in inspector_issues:
            severity = str(inspector_issue.severity)
            issue = ValidationIssue(
                severity=severity,
                message=inspector_issue.message,
                location=inspector_issue.location if hasattr(inspector_issue, 'location') else None,
                check_name=inspector_issue.check_function_name,
            )
            issues.append(issue)

            # Count by severity
            if severity in issue_count:
                issue_count[severity] += 1

        # Determine overall status
        if issue_count["CRITICAL"] > 0:
            overall_status = "failed"
        elif issue_count["BEST_PRACTICE_VIOLATION"] > 0 or issue_count["BEST_PRACTICE_SUGGESTION"] > 0:
            overall_status = "passed_with_warnings"
        else:
            overall_status = "passed"

        return overall_status, issue_count, issues

    async def _generate_report(
        self,
        session_id: str,
        overall_status: str,
        issue_count: dict[str, int],
        issues: list[ValidationIssue],
        metadata_score: float,
        best_practices_score: float,
    ) -> str:
        """
        Generate validation report as JSON file.

        Args:
            session_id: Session identifier
            overall_status: Overall validation status
            issue_count: Dictionary with counts by severity
            issues: List of ValidationIssue objects
            metadata_score: Metadata completeness score (0-100)
            best_practices_score: Best practices score (0-100)

        Returns:
            Path to generated report file
        """
        # Create reports directory using configured base path
        reports_dir = Path(settings.filesystem_output_base_path) / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        # Generate report path
        report_path = reports_dir / f"{session_id}_validation.json"

        # Create report data
        report_data = {
            "session_id": session_id,
            "overall_status": overall_status,
            "issue_count": issue_count,
            "issues": [
                {
                    "severity": issue.severity,
                    "message": issue.message,
                    "location": issue.location,
                    "check_name": issue.check_name,
                }
                for issue in issues
            ],
            "metadata_completeness_score": metadata_score,
            "best_practices_score": best_practices_score,
            "generated_at": datetime.utcnow().isoformat(),
        }

        # Write JSON to file
        with open(report_path, "w") as f:
            json.dump(report_data, f, indent=2)

        return str(report_path.absolute())

    def _calculate_metadata_score(self, metadata: dict[str, Any]) -> float:
        """
        Calculate metadata completeness score (0-100).

        Args:
            metadata: Dictionary of metadata fields

        Returns:
            Score from 0-100 based on metadata completeness
        """
        # Define critical metadata fields
        critical_fields = [
            "subject_id",
            "species",
            "session_start_time",
            "session_description",
            "experimenter",
        ]

        # Count how many critical fields are present and non-empty
        present_count = 0
        for field in critical_fields:
            if field in metadata and metadata[field]:
                present_count += 1

        # Calculate score as percentage of critical fields present
        score = (present_count / len(critical_fields)) * 100.0
        return score

    def _calculate_best_practices_score(self, issue_count: dict[str, int]) -> float:
        """
        Calculate best practices score (0-100) based on issue counts.

        Args:
            issue_count: Dictionary with counts by severity

        Returns:
            Score from 0-100 based on issues (weighted by severity)
        """
        # Start with perfect score
        score = 100.0

        # Deduct points for each issue (weighted by severity)
        # Critical issues: -15 points each
        # Violations: -5 points each
        # Suggestions: -2 points each
        score -= issue_count.get("CRITICAL", 0) * 15
        score -= issue_count.get("BEST_PRACTICE_VIOLATION", 0) * 5
        score -= issue_count.get("BEST_PRACTICE_SUGGESTION", 0) * 2

        # Ensure score doesn't go below 0
        return max(0.0, score)

    async def _generate_validation_summary(
        self,
        overall_status: str,
        issue_count: dict[str, int],
        issues: list[ValidationIssue],
        metadata: dict[str, Any],
    ) -> str:
        """
        Generate LLM-based validation summary.

        Args:
            overall_status: Overall validation status
            issue_count: Dictionary with counts by severity
            issues: List of ValidationIssue objects
            metadata: NWB file metadata

        Returns:
            Concise validation summary (under 150 words)
        """
        # Create prompt with validation results
        issues_summary = ""
        if issues:
            # Include up to first 20 issues with details
            issues_to_show = issues[:20]
            issues_summary = "\n".join([
                f"- [{issue.severity}] {issue.message} (at {issue.location})"
                for issue in issues_to_show
            ])
            if len(issues) > 20:
                issues_summary += f"\n... and {len(issues) - 20} more issues"
        else:
            issues_summary = "No issues found."

        prompt = f"""Generate a concise validation summary (under 150 words) for this NWB file validation.

Overall Status: {overall_status}

Issue Counts:
- Critical: {issue_count.get('CRITICAL', 0)}
- Best Practice Violations: {issue_count.get('BEST_PRACTICE_VIOLATION', 0)}
- Best Practice Suggestions: {issue_count.get('BEST_PRACTICE_SUGGESTION', 0)}

Issues:
{issues_summary}

Metadata: {json.dumps(metadata, indent=2)}

Provide:
1. Overall assessment
2. Highlight critical issues (if any)
3. Actionable recommendations
4. Whether the file is ready for use

Keep it under 150 words and make it actionable."""

        # Call LLM with temperature 0.4 for balanced output
        summary = await self.call_llm(prompt)
        return summary

    async def _validate_nwb_full(self, session_id: str) -> dict[str, Any]:
        """
        Complete validation workflow: validate NWB, generate report and summary.

        This is the main entry point for validation that orchestrates all steps:
        1. Get session context
        2. Update workflow stage to EVALUATING
        3. Validate NWB file using NWB Inspector
        4. Calculate metadata and best practices scores
        5. Generate validation report JSON file
        6. Generate LLM validation summary
        7. Update session context with results
        8. Set workflow stage to COMPLETED
        9. Clear current_agent

        Args:
            session_id: Session identifier

        Returns:
            Result dictionary with status and session_id
        """
        try:
            # 1. Get session context
            session = await self.get_session_context(session_id)

            # 2. Update workflow stage to EVALUATING
            await self.update_session_context(
                session_id,
                {"workflow_stage": WorkflowStage.EVALUATING},
            )

            # Get NWB file path from conversion results
            if not session.conversion_results or not session.conversion_results.nwb_file_path:
                raise ValueError("No NWB file path found in session context")

            nwb_file_path = session.conversion_results.nwb_file_path

            # 3. Validate NWB file using NWB Inspector
            overall_status, issue_count, issues = await self._validate_nwb(nwb_file_path)

            # 4. Calculate metadata and best practices scores
            metadata_dict = {}
            if session.metadata:
                metadata_dict = session.metadata.model_dump(exclude_none=True)

            metadata_score = self._calculate_metadata_score(metadata_dict)
            best_practices_score = self._calculate_best_practices_score(issue_count)

            # 5. Generate validation report JSON file
            report_path = await self._generate_report(
                session_id=session_id,
                overall_status=overall_status,
                issue_count=issue_count,
                issues=issues,
                metadata_score=metadata_score,
                best_practices_score=best_practices_score,
            )

            # 6. Generate LLM validation summary
            llm_summary = await self._generate_validation_summary(
                overall_status=overall_status,
                issue_count=issue_count,
                issues=issues,
                metadata=metadata_dict,
            )

            # 7. Create ValidationResults object
            validation_results = ValidationResults(
                overall_status=overall_status,
                issue_count=issue_count,
                issues=issues,
                metadata_completeness_score=metadata_score,
                best_practices_score=best_practices_score,
                validation_report_path=report_path,
                llm_validation_summary=llm_summary,
            )

            # 8. Update session context with results, set COMPLETED, and clear agent
            await self.update_session_context(
                session_id,
                {
                    "validation_results": validation_results.model_dump(),
                    "workflow_stage": WorkflowStage.COMPLETED,
                    "current_agent": None,
                },
            )

            return {
                "status": "success",
                "session_id": session_id,
                "overall_status": overall_status,
                "report_path": report_path,
            }

        except FileNotFoundError as e:
            # Handle missing NWB file gracefully
            error_msg = f"NWB file not found: {str(e)}"
            await self.update_session_context(
                session_id,
                {
                    "workflow_stage": WorkflowStage.FAILED,
                    "current_agent": None,
                },
            )
            return {
                "status": "error",
                "session_id": session_id,
                "error": error_msg,
            }

        except Exception as e:
            # Handle any other errors gracefully
            error_msg = f"Validation failed: {str(e)}"
            await self.update_session_context(
                session_id,
                {
                    "workflow_stage": WorkflowStage.FAILED,
                    "current_agent": None,
                },
            )
            return {
                "status": "error",
                "session_id": session_id,
                "error": error_msg,
            }
