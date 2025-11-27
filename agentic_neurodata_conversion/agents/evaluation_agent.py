"""Evaluation Agent implementation.

Responsible for:
- NWB file validation using NWB Inspector
- Quality assessment
- Correction analysis (using LLM if available)
- Performance Optimization: Batch parallel LLM calls for quality assessment
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Import Week 5 evaluation modules (extracted from evaluation_agent.py)
from agentic_neurodata_conversion.agents.evaluation import (
    CorrectionAnalyzer,
    FileInspector,
    IssueAnalyzer,
    ReportGenerator,
    ValidationRunner,
)
from agentic_neurodata_conversion.agents.utils.validation_history import ValidationHistoryLearner

# Import intelligent evaluation modules
from agentic_neurodata_conversion.agents.validation.intelligent_analyzer import IntelligentValidationAnalyzer
from agentic_neurodata_conversion.agents.validation.issue_resolution import SmartIssueResolution
from agentic_neurodata_conversion.models import (
    CorrectionContext,
    GlobalState,
    LogEntry,
    LogLevel,
    MCPMessage,
    MCPResponse,
    ValidationOutcome,
    ValidationResult,
    ValidationStatus,
)
from agentic_neurodata_conversion.services import LLMService
from agentic_neurodata_conversion.services.prompt_service import PromptService
from agentic_neurodata_conversion.services.report_service import ReportService


class EvaluationAgent:
    """Evaluation agent for validation and quality assessment.

    This agent validates NWB files and performs quality checks.
    """

    def __init__(self, llm_service: LLMService | None = None):
        """Initialize the evaluation agent.

        Args:
            llm_service: Optional LLM service for correction analysis
        """
        self._llm_service = llm_service
        self._report_service = ReportService()
        self._prompt_service = PromptService()

        # Initialize Week 5 evaluation modules (extracted from evaluation_agent.py)
        self._validation_runner = ValidationRunner()
        self._file_inspector = FileInspector()
        self._issue_analyzer = IssueAnalyzer(llm_service)
        self._correction_analyzer = CorrectionAnalyzer(llm_service)
        self._report_generator = ReportGenerator(llm_service, self._prompt_service)

        # Initialize intelligent evaluation modules
        self._validation_analyzer = IntelligentValidationAnalyzer(llm_service) if llm_service else None
        self._issue_resolution = SmartIssueResolution(llm_service) if llm_service else None
        self._history_learner = ValidationHistoryLearner(llm_service) if llm_service else None

        logger.info("EvaluationAgent initialized with 5 modular components")

    async def handle_run_validation(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """Run NWB Inspector validation on an NWB file.

        Args:
            message: MCP message with context containing 'nwb_path'
            state: Global state

        Returns:
            MCPResponse with validation results
        """
        nwb_path = message.context.get("nwb_path")

        if not nwb_path:
            state.add_log(
                LogLevel.ERROR,
                "Missing nwb_path in validation request",
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="MISSING_NWB_PATH",
                error_message="nwb_path is required for validation",
            )

        # ValidationStatus is for final outcomes, not intermediate states
        # ConversionStatus.VALIDATING is used for the running state
        state.add_log(
            LogLevel.INFO,
            f"Starting NWB validation: {nwb_path}",
            {"nwb_path": nwb_path},
        )

        try:
            validation_result = await self._run_nwb_inspector(nwb_path)

            # WORKFLOW_CONDITION_FLAGS_ANALYSIS.md Fix: Use ValidationOutcome enum
            # Determine overall status for reporting
            if validation_result.is_valid:
                # No critical or error issues
                if len(validation_result.issues) == 0:
                    overall_status = ValidationOutcome.PASSED
                elif validation_result.summary.get("warning", 0) > 0 or validation_result.summary.get("info", 0) > 0:
                    overall_status = ValidationOutcome.PASSED_WITH_ISSUES
                else:
                    overall_status = ValidationOutcome.PASSED
            else:
                # Has critical or error issues
                overall_status = ValidationOutcome.FAILED

            # Bug #2 fix: Store overall_status in state (Story 7.2)
            state.overall_status = overall_status

            # Update state based on validation result
            # Bug #6 fix: Set validation_status to passed_improved if this is a successful improvement
            if validation_result.is_valid and overall_status == ValidationOutcome.PASSED:
                # Check if this is after a correction attempt (Story 8.8 line 957)
                if state.correction_attempt > 0:
                    await state.update_validation_status(ValidationStatus.PASSED_IMPROVED)
                else:
                    await state.update_validation_status(ValidationStatus.PASSED)

                state.add_log(
                    LogLevel.INFO,
                    f"Validation {overall_status.value.lower()}",
                    {
                        "nwb_path": nwb_path,
                        "summary": validation_result.summary,
                        "overall_status": overall_status.value,
                        "validation_status": state.validation_status.value if state.validation_status else None,
                    },
                )
            elif validation_result.is_valid and overall_status == ValidationOutcome.PASSED_WITH_ISSUES:
                # Don't set final validation_status yet - wait for user decision
                state.add_log(
                    LogLevel.INFO,
                    f"Validation {overall_status.value.lower()} (awaiting user decision)",
                    {
                        "nwb_path": nwb_path,
                        "summary": validation_result.summary,
                        "overall_status": overall_status.value,
                    },
                )
            else:
                # FAILED status - don't set validation_status yet, wait for user decision
                state.add_log(
                    LogLevel.WARNING,
                    "Validation failed (awaiting user decision)",
                    {
                        "nwb_path": nwb_path,
                        "summary": validation_result.summary,
                        "issue_count": len(validation_result.issues),
                        "overall_status": overall_status.value,
                    },
                )

            # Create enriched validation result with overall_status
            validation_result_dict = validation_result.model_dump()
            # Serialize enum to string value for JSON response
            validation_result_dict["overall_status"] = overall_status.value

            # Fix issue counts mapping for report generation
            # Map lowercase severity keys to uppercase for report compatibility
            if validation_result.summary:
                validation_result_dict["issue_counts"] = {
                    "CRITICAL": validation_result.summary.get("critical", 0),
                    "ERROR": validation_result.summary.get("error", 0),
                    "WARNING": validation_result.summary.get("warning", 0),
                    "INFO": validation_result.summary.get("info", 0),
                    "BEST_PRACTICE": validation_result.summary.get("best_practice", 0),
                }

            # Use LLM to prioritize and explain issues if available
            if self._llm_service and validation_result.issues:
                try:
                    prioritized_issues = await self._prioritize_and_explain_issues(
                        issues=validation_result.issues,
                        state=state,
                    )
                    validation_result_dict["prioritized_issues"] = prioritized_issues
                    state.add_log(
                        LogLevel.INFO,
                        f"Prioritized {len(prioritized_issues)} validation issues",
                        {
                            "dandi_blocking_count": len(
                                [i for i in prioritized_issues if i.get("priority") == "dandi_blocking"]
                            )
                        },
                    )
                except Exception as e:
                    state.add_log(
                        LogLevel.WARNING,
                        f"Issue prioritization failed: {e}",
                    )

            # 🎯 PRIORITY 3: Quality Scoring System
            if self._llm_service:
                try:
                    quality_score = await self._assess_nwb_quality(
                        nwb_path=nwb_path,
                        validation_result=validation_result,
                        state=state,
                    )
                    validation_result_dict["quality_score"] = quality_score
                    state.add_log(
                        LogLevel.INFO,
                        f"NWB Quality Score: {quality_score.get('score', 0)}/100 (Grade: {quality_score.get('grade', 'N/A')})",
                        {"quality_details": quality_score},
                    )
                except Exception as e:
                    state.add_log(
                        LogLevel.WARNING,
                        f"Quality scoring failed: {e}",
                    )

            # 🎯 NEW: Intelligent Validation Analysis
            if self._validation_analyzer and validation_result.issues:
                try:
                    file_context = {
                        "nwb_path": nwb_path,
                        "file_size_mb": Path(nwb_path).stat().st_size / (1024 * 1024) if Path(nwb_path).exists() else 0,
                        "nwb_version": validation_result_dict.get("file_info", {}).get("nwb_version", "unknown"),
                    }

                    deep_analysis = await self._validation_analyzer.analyze_validation_results(
                        validation_result=validation_result,
                        file_context=file_context,
                        state=state,
                    )
                    validation_result_dict["deep_analysis"] = deep_analysis

                    state.add_log(
                        LogLevel.INFO,
                        f"Deep validation analysis: {len(deep_analysis.get('root_causes', []))} root causes, "
                        f"{len(deep_analysis.get('quick_wins', []))} quick wins",
                        {"analysis_summary": deep_analysis.get("analysis_summary", "")},
                    )
                except Exception as e:
                    state.add_log(
                        LogLevel.WARNING,
                        f"Deep validation analysis failed: {e}",
                    )

            # 🎯 NEW: Smart Resolution Plan
            if self._issue_resolution and validation_result.issues:
                try:
                    file_context = {
                        "nwb_path": nwb_path,
                        "file_size_mb": Path(nwb_path).stat().st_size / (1024 * 1024) if Path(nwb_path).exists() else 0,
                        "nwb_version": validation_result_dict.get("file_info", {}).get("nwb_version", "unknown"),
                    }

                    resolution_plan = await self._issue_resolution.generate_resolution_plan(
                        issues=validation_result.issues,
                        file_context=file_context,
                        existing_metadata=state.metadata,
                        state=state,
                    )
                    validation_result_dict["resolution_plan"] = resolution_plan

                    state.add_log(
                        LogLevel.INFO,
                        f"Generated resolution plan with {len(resolution_plan.get('workflows', []))} workflows",
                    )
                except Exception as e:
                    state.add_log(
                        LogLevel.WARNING,
                        f"Resolution plan generation failed: {e}",
                    )

            # 🎯 NEW: Record to validation history for learning
            if self._history_learner:
                try:
                    file_context = {
                        "format": state.metadata.get("format", "unknown"),
                        "file_size_mb": Path(nwb_path).stat().st_size / (1024 * 1024) if Path(nwb_path).exists() else 0,
                        "nwb_version": validation_result_dict.get("file_info", {}).get("nwb_version", "unknown"),
                    }

                    await self._history_learner.record_validation_session(
                        validation_result=validation_result,
                        file_context=file_context,
                        resolution_actions=None,  # Will be populated if user applies fixes
                        state=state,
                    )
                except Exception as e:
                    state.add_log(
                        LogLevel.DEBUG,
                        f"History recording failed: {e}",
                    )

            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "validation_result": validation_result_dict,
                },
            )

        except Exception as e:
            error_msg = f"Validation failed: {str(e)}"
            state.add_log(
                LogLevel.ERROR,
                error_msg,
                {"nwb_path": nwb_path, "exception": str(e)},
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="VALIDATION_FAILED",
                error_message=error_msg,
                error_context={"exception": str(e)},
            )

    def _extract_file_info(self, nwb_path: str) -> dict[str, Any]:
        """Extract comprehensive file information from NWB file - delegates to FileInspector.

        Args:
            nwb_path: Path to NWB file

        Returns:
            Dictionary with complete file metadata including experimenter,
            institution, subject info, etc.
        """
        return self._file_inspector.extract_file_info(nwb_path)

    async def _prioritize_and_explain_issues(
        self,
        issues: list[Any],
        state: GlobalState,
    ) -> list[dict[str, Any]]:
        """Use LLM to prioritize validation issues - delegates to IssueAnalyzer.

        Args:
            issues: List of validation issues from NWB Inspector
            state: Global state

        Returns:
            List of prioritized issues with explanations and action items
        """
        return await self._issue_analyzer.prioritize_and_explain_issues(issues, state)

    async def _assess_nwb_quality(
        self,
        nwb_path: str,
        validation_result: ValidationResult,
        state: GlobalState,
    ) -> dict[str, Any]:
        """🎯 PRIORITY 3: Quality Scoring System - delegates to IssueAnalyzer.

        Args:
            nwb_path: Path to NWB file
            validation_result: Validation results from NWB Inspector
            state: Global state

        Returns:
            Quality assessment with score, grade, and improvement suggestions
        """
        file_info = self._extract_file_info(nwb_path)
        return await self._issue_analyzer.assess_nwb_quality(nwb_path, validation_result, file_info, state)

    async def _run_nwb_inspector(self, nwb_path: str) -> ValidationResult:
        """Run NWB Inspector validation - delegates to ValidationRunner.

        Args:
            nwb_path: Path to NWB file

        Returns:
            ValidationResult object

        Raises:
            Exception: If validation cannot be run
        """
        return await self._validation_runner.run_nwb_inspector(nwb_path)

    async def handle_analyze_corrections(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """Analyze validation issues and suggest corrections (requires LLM).

        Args:
            message: MCP message with context containing validation results
            state: Global state

        Returns:
            MCPResponse with correction suggestions or error
        """
        if not self._llm_service:
            state.add_log(
                LogLevel.ERROR,
                "LLM service not available for correction analysis",
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="LLM_NOT_AVAILABLE",
                error_message="Correction analysis requires LLM service",
            )

        validation_result_data = message.context.get("validation_result")
        input_metadata = message.context.get("input_metadata", {})
        conversion_parameters = message.context.get("conversion_parameters", {})

        if not validation_result_data:
            state.add_log(
                LogLevel.ERROR,
                "Missing validation_result in correction analysis request",
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="MISSING_VALIDATION_RESULT",
                error_message="validation_result is required",
            )

        state.add_log(
            LogLevel.INFO,
            "Starting correction analysis with LLM",
            {"attempt": state.correction_attempt},
        )

        try:
            # Parse validation result
            validation_result = ValidationResult(**validation_result_data)

            # Create correction context
            correction_context = CorrectionContext(
                validation_result=validation_result,
                input_metadata=input_metadata,
                conversion_parameters=conversion_parameters,
            )

            # Analyze with LLM
            corrections = await self._analyze_with_llm(correction_context, state)

            state.add_log(
                LogLevel.INFO,
                "Correction analysis completed",
                {"corrections_count": len(corrections.get("suggestions", []))},
            )

            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "corrections": corrections,
                },
            )

        except Exception as e:
            error_msg = f"Correction analysis failed: {str(e)}"
            state.add_log(
                LogLevel.ERROR,
                error_msg,
                {"exception": str(e)},
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="ANALYSIS_FAILED",
                error_message=error_msg,
                error_context={"exception": str(e)},
            )

    async def _analyze_with_llm(
        self,
        correction_context: CorrectionContext,
        state: GlobalState,
    ) -> dict[str, Any]:
        """Use LLM to analyze validation issues - delegates to CorrectionAnalyzer.

        Args:
            correction_context: Context for correction analysis
            state: Global state

        Returns:
            Dictionary with correction suggestions
        """
        return await self._correction_analyzer.analyze_with_llm(correction_context, state)

    async def handle_generate_report(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """Generate evaluation report (PDF for PASSED, JSON for FAILED).

        Args:
            message: MCP message with validation_result and optional llm_analysis
            state: Global state

        Returns:
            MCPResponse with report path

        Implements Stories 9.5 and 9.6: Report Generation
        """
        validation_result_data = message.context.get("validation_result")
        llm_analysis = message.context.get("llm_analysis")
        nwb_path = message.context.get("nwb_path")
        final_accepted = message.context.get("final_accepted", False)  # BUG #4 FIX

        if not validation_result_data:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="MISSING_VALIDATION_RESULT",
                error_message="validation_result is required for report generation",
            )

        try:
            # Determine report type based on validation status
            overall_status = validation_result_data.get("overall_status", "UNKNOWN")

            # BUG #4 FIX: If user accepted PASSED_WITH_ISSUES, treat as PASSED for final report generation
            if final_accepted and overall_status == "PASSED_WITH_ISSUES":
                overall_status = "PASSED"
                state.add_log(
                    LogLevel.INFO,
                    "Generating final reports for PASSED_WITH_ISSUES after user acceptance (treating as PASSED)",
                    {"original_status": "PASSED_WITH_ISSUES", "final_status": "PASSED"},
                )

            if nwb_path:
                nwb_path_obj = Path(nwb_path)
                report_base = nwb_path_obj.stem
            else:
                report_base = "evaluation_report"

            # BUG #4 FIX: Only generate final reports for clean PASSED
            # For PASSED_WITH_ISSUES, wait for user decision before generating final reports
            if overall_status == "PASSED":
                # Generate both HTML and text reports (clean pass)
                output_dir = Path(state.output_path).parent if state.output_path else Path("outputs")
                text_report_path = output_dir / f"{report_base}_inspection_report.txt"

                # CRITICAL FIX: Always extract file info directly from NWB file
                # This ensures we get the actual metadata that was written during conversion
                if nwb_path:
                    state.add_log(
                        LogLevel.INFO,
                        f"Extracting metadata from NWB file for report: {nwb_path}",
                    )
                    file_info = self._extract_file_info(nwb_path)

                    # Add provenance information for each metadata field
                    # Track source: user-provided, file-extracted, ai-inferred, or default
                    file_info_with_provenance = self._add_metadata_provenance(
                        file_info=file_info,
                        state=state,
                    )

                    validation_result_data["file_info"] = file_info_with_provenance
                    state.add_log(
                        LogLevel.DEBUG,
                        f"Extracted file metadata: experimenter={file_info.get('experimenter')}, "
                        f"institution={file_info.get('institution')}, "
                        f"subject_id={file_info.get('subject_id')}",
                    )

                # If LLM service available and no analysis provided, generate it
                if self._llm_service and not llm_analysis:
                    llm_analysis = await self._generate_quality_assessment(validation_result_data)

                # Build workflow trace for transparency and reproducibility
                workflow_trace = self._build_workflow_trace(state)

                # Generate HTML report (interactive with embedded CSS/JS)
                html_report_path = output_dir / f"{report_base}_evaluation_report.html"
                self._report_service.generate_html_report(
                    html_report_path, validation_result_data, llm_analysis, workflow_trace
                )

                # Save workflow_trace to JSON for later retrieval
                workflow_trace_path = output_dir / f"{report_base}_workflow_trace.json"
                with open(workflow_trace_path, "w") as f:
                    json.dump(workflow_trace, f, indent=2, default=str)
                state.add_log(LogLevel.DEBUG, f"Saved workflow trace to {workflow_trace_path}")

                # Generate text report (NWB Inspector style with LLM analysis and workflow trace)
                self._report_service.generate_text_report(
                    text_report_path, validation_result_data, llm_analysis, workflow_trace
                )

                state.add_log(
                    LogLevel.INFO,
                    "Generated evaluation reports: HTML and text",
                    {
                        "html_report": str(html_report_path),
                        "text_report": str(text_report_path),
                        "status": overall_status,
                    },
                )

                return MCPResponse.success_response(
                    reply_to=message.message_id,
                    result={
                        "report_path": str(html_report_path),  # Primary report (HTML for interactivity)
                        "html_report_path": str(html_report_path),
                        "text_report_path": str(text_report_path),
                        "report_type": "html_and_text",
                    },
                )

            elif overall_status == "PASSED_WITH_ISSUES":
                # BUG #4 FIX: For PASSED_WITH_ISSUES, don't generate final reports yet
                # Wait for user decision (improve or accept) before generating final reports
                # Generate a temporary JSON summary for user to review
                output_dir = Path(state.output_path).parent if state.output_path else Path("outputs")
                preview_report_path = output_dir / f"{report_base}_preview.json"

                # CRITICAL FIX: Always extract file info directly from NWB file
                # This ensures we get the actual metadata that was written during conversion
                if nwb_path:
                    state.add_log(
                        LogLevel.INFO,
                        f"Extracting metadata from NWB file for preview report: {nwb_path}",
                    )
                    file_info = self._extract_file_info(nwb_path)

                    # Add provenance information for transparency
                    file_info_with_provenance = self._add_metadata_provenance(
                        file_info=file_info,
                        state=state,
                    )

                    validation_result_data["file_info"] = file_info_with_provenance

                # Build workflow trace
                workflow_trace = self._build_workflow_trace(state)

                # Generate preview JSON report (not final)
                self._report_service.generate_json_report(
                    preview_report_path, validation_result_data, llm_analysis, workflow_trace
                )

                state.add_log(
                    LogLevel.INFO,
                    "Generated preview report for PASSED_WITH_ISSUES (final reports deferred until user accepts)",
                    {"preview_report": str(preview_report_path), "status": overall_status},
                )

                return MCPResponse.success_response(
                    reply_to=message.message_id,
                    result={
                        "report_path": str(preview_report_path),
                        "report_type": "preview_json",
                        "awaiting_user_decision": True,  # Flag to indicate final reports not yet generated
                    },
                )

            else:  # FAILED
                # Generate JSON report
                output_dir = Path(state.output_path).parent if state.output_path else Path("outputs")
                report_path = output_dir / f"{report_base}_correction_context.json"

                # CRITICAL FIX: Always extract file info directly from NWB file
                # Even for FAILED files, we want to show what metadata IS present
                if nwb_path:
                    state.add_log(
                        LogLevel.INFO,
                        f"Extracting metadata from NWB file for correction report: {nwb_path}",
                    )
                    file_info = self._extract_file_info(nwb_path)

                    # Add provenance information even for failed conversions
                    file_info_with_provenance = self._add_metadata_provenance(
                        file_info=file_info,
                        state=state,
                    )

                    validation_result_data["file_info"] = file_info_with_provenance

                # If LLM service available and no analysis provided, generate it
                if self._llm_service and not llm_analysis:
                    llm_analysis = await self._generate_correction_guidance(validation_result_data)

                # Build workflow trace for transparency and reproducibility
                workflow_trace = self._build_workflow_trace(state)

                self._report_service.generate_json_report(
                    report_path, validation_result_data, llm_analysis, workflow_trace
                )

                state.add_log(
                    LogLevel.INFO,
                    f"Generated JSON correction report: {report_path}",
                    {"report_path": str(report_path), "status": overall_status},
                )

                return MCPResponse.success_response(
                    reply_to=message.message_id,
                    result={
                        "report_path": str(report_path),
                        "report_type": "json",
                    },
                )

        except Exception as e:
            error_msg = f"Report generation failed: {str(e)}"
            state.add_log(
                LogLevel.ERROR,
                error_msg,
                {"exception": str(e)},
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="REPORT_GENERATION_FAILED",
                error_message=error_msg,
                error_context={"exception": str(e)},
            )

    def _prepare_logs_for_sequential_view(
        self, logs: list[LogEntry]
    ) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        """Prepare logs for sequential display - delegates to ReportGenerator.

        Args:
            logs: List of log entries

        Returns:
            Tuple of (enhanced_logs, stage_options)
        """
        return self._report_generator.prepare_logs_for_sequential_view(logs)

    def _build_workflow_trace(self, state: GlobalState) -> dict[str, Any]:
        """Build workflow trace - delegates to ReportGenerator.

        Args:
            state: Global state

        Returns:
            Dictionary containing complete workflow trace
        """
        return self._report_generator.build_workflow_trace(state)

    def _add_metadata_provenance(self, file_info: dict[str, Any], state: GlobalState) -> dict[str, Any]:
        """Add metadata provenance - delegates to ReportGenerator.

        Args:
            file_info: File info dictionary
            state: Global state

        Returns:
            Dictionary with provenance information
        """
        return self._report_generator.add_metadata_provenance(file_info, state)

    async def _generate_quality_assessment(self, validation_result: dict[str, Any]) -> dict[str, Any] | None:
        """Generate quality assessment - delegates to ReportGenerator.

        Args:
            validation_result: Validation result dictionary

        Returns:
            Quality assessment or None
        """
        return await self._report_generator.generate_quality_assessment(validation_result)

    async def _generate_correction_guidance(self, validation_result: dict[str, Any]) -> dict[str, Any] | None:
        """Generate correction guidance - delegates to ReportGenerator.

        Args:
            validation_result: Validation result dictionary

        Returns:
            Correction guidance or None
        """
        return await self._report_generator.generate_correction_guidance(validation_result)


def register_evaluation_agent(
    mcp_server,
    llm_service: LLMService | None = None,
) -> EvaluationAgent:
    """Register Evaluation Agent handlers with MCP server.

    Args:
        mcp_server: MCP server instance
        llm_service: Optional LLM service for correction analysis

    Returns:
        EvaluationAgent instance
    """
    agent = EvaluationAgent(llm_service=llm_service)

    mcp_server.register_handler(
        "evaluation",
        "run_validation",
        agent.handle_run_validation,
    )

    mcp_server.register_handler(
        "evaluation",
        "analyze_corrections",
        agent.handle_analyze_corrections,
    )

    mcp_server.register_handler(
        "evaluation",
        "generate_report",
        agent.handle_generate_report,
    )

    return agent
