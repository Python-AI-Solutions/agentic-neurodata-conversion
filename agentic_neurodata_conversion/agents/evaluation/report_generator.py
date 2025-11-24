"""Report generation utilities for evaluation agent.

Handles:
- Workflow trace building for transparency
- Log preparation for sequential display
- Metadata provenance tracking (6-tag system)
- Quality assessment report generation
- Correction guidance report generation
"""

import logging
import os
from datetime import datetime
from typing import TYPE_CHECKING, Any

from agentic_neurodata_conversion.models import GlobalState, LogEntry, LogLevel

if TYPE_CHECKING:
    from agentic_neurodata_conversion.services import LLMService, PromptService

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Handles report generation utilities for evaluation.

    Features:
    - Workflow transparency with complete trace
    - Sequential log display with stage tags
    - 6-tag provenance system for metadata
    - LLM-powered quality assessments
    - LLM-powered correction guidance
    """

    def __init__(self, llm_service: "LLMService | None" = None, prompt_service: "PromptService | None" = None):
        """Initialize report generator.

        Args:
            llm_service: Optional LLM service for quality/correction reports
            prompt_service: Optional prompt service for LLM report templates
        """
        self._llm_service = llm_service
        self._prompt_service = prompt_service

    def prepare_logs_for_sequential_view(
        self, logs: list[LogEntry]
    ) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        """Prepare logs for sequential chronological display with stage tags.

        This method organizes logs in chronological order while tagging each with its
        workflow stage for filtering. This preserves the natural flow of events while
        still allowing users to filter by specific stages.

        Args:
            logs: List of log entries from GlobalState in chronological order

        Returns:
            Tuple of (enhanced_logs, stage_options) where:
            - enhanced_logs: List of log dicts with stage tags in chronological order
            - stage_options: List of stage display names for the filter dropdown
        """
        # Define workflow stages and their associated keywords
        stage_keywords = {
            "initialization": ["reset", "initialized", "starting", "session", "global state"],
            "upload": ["upload", "file received", "checksum"],
            "format_detection": ["detecting format", "detected format", "format detection", "llm format"],
            "metadata_extraction": ["extracting metadata", "metadata extracted", "inference", "metadata check"],
            "metadata_collection": [
                "user input",
                "metadata collection",
                "awaiting user",
                "conversation",
                "conversational",
                "parse",
                "natural language",
            ],
            "conversion": [
                "converting",
                "conversion",
                "neuroconv",
                "creating nwb",
                "nwb conversion",
                "spikeglx",
                "writing nwb",
            ],
            "validation": ["validating", "validation", "nwb inspector", "checking", "validation session"],
            "completion": ["metadata inference completed"],
        }

        # Human-readable stage display names
        stage_display_names = {
            "initialization": "Initialization",
            "upload": "Upload",
            "format_detection": "Format Detection",
            "metadata_extraction": "Metadata Extraction",
            "metadata_collection": "Metadata Collection",
            "conversion": "Conversion",
            "validation": "Validation",
            "completion": "Completion",
            "general": "General",
        }

        # Stage icons for visual identification
        stage_icons = {
            "initialization": "🚀",
            "upload": "📤",
            "format_detection": "🔍",
            "metadata_extraction": "🧠",
            "metadata_collection": "💬",
            "conversion": "⚙️",
            "validation": "✅",
            "completion": "🎉",
            "general": "📝",
        }

        enhanced_logs = []
        for log in logs:
            message_lower = log.message.lower()

            # Determine stage for this log
            stage = "general"  # default
            for stage_name, keywords in stage_keywords.items():
                if any(keyword in message_lower for keyword in keywords):
                    stage = stage_name
                    break

            enhanced_logs.append(
                {
                    "timestamp": log.timestamp.isoformat(),
                    "level": log.level.value.upper(),
                    "message": log.message,
                    "context": log.context if log.context else None,
                    "stage": stage,  # For filtering (e.g., "initialization")
                    "stage_display": stage_display_names[stage],  # For display (e.g., "Initialization")
                    "stage_icon": stage_icons[stage],  # For visual identification
                }
            )

        # Return enhanced logs and stage options for the dropdown
        stage_options = [
            {"value": "initialization", "label": "🚀 Initialization"},
            {"value": "upload", "label": "📤 Upload"},
            {"value": "format_detection", "label": "🔍 Format Detection"},
            {"value": "metadata_extraction", "label": "🧠 Metadata Extraction"},
            {"value": "metadata_collection", "label": "💬 Metadata Collection"},
            {"value": "conversion", "label": "⚙️ Conversion"},
            {"value": "validation", "label": "✅ Validation"},
            {"value": "completion", "label": "🎉 Completion"},
            {"value": "general", "label": "📝 General"},
        ]

        return enhanced_logs, stage_options

    def build_workflow_trace(self, state: GlobalState) -> dict[str, Any]:
        """Build a comprehensive workflow trace from the state for transparency and reproducibility.

        Args:
            state: The global state containing logs and workflow information

        Returns:
            Dictionary containing complete workflow trace with:
            - summary: Start time, end time, duration, input format
            - technologies: List of technologies used
            - steps: Workflow steps with timestamps
            - provenance: Data provenance information
            - user_interactions: User actions during workflow
            - metadata_provenance: 6-tag provenance for each field
            - detailed_logs_sequential: Chronological logs with stage tags
            - stage_options: Filter dropdown options
            - log_file_path: Path to detailed log file
        """
        # Calculate duration
        start_time = None
        end_time = datetime.now()
        if state.logs:
            start_time = state.logs[0].timestamp
            duration_seconds = (end_time - start_time).total_seconds()
            duration = f"{duration_seconds:.2f} seconds"
        else:
            duration = "N/A"

        # Build summary
        summary = {
            "start_time": start_time.isoformat() if start_time else "N/A",
            "end_time": end_time.isoformat(),
            "duration": duration,
            "input_format": state.metadata.get("detected_format", "Unknown"),
        }

        # Technologies used
        technologies = [
            "NWB (Neurodata Without Borders) 2.0+ Standard",
            "NeuroConv - Unified conversion framework",
            "NWB Inspector - Validation tool",
            "SpikeInterface - Electrophysiology data processing",
            "PyNWB - Python NWB API",
            "HDF5 - Hierarchical data format",
            "Claude AI (Anthropic) - Metadata assistance and quality assessment",
            "FastAPI - Backend API framework",
            "Python 3.14 - Programming language",
        ]

        # Build workflow steps from logs
        steps = []
        step_mapping = {
            "detecting_format": {
                "name": "Format Detection",
                "description": "Automatically detected the input data format using intelligent pattern matching",
            },
            "awaiting_user_input": {
                "name": "Metadata Collection",
                "description": "Collected required NWB metadata from user with AI-assisted suggestions",
            },
            "converting": {
                "name": "Data Conversion",
                "description": "Converted electrophysiology data to NWB format using NeuroConv",
            },
            "validating": {
                "name": "Validation",
                "description": "Validated NWB file against standards using NWB Inspector",
            },
            "completed": {
                "name": "Completion",
                "description": "Conversion and validation completed successfully",
            },
        }

        # Extract steps from logs
        seen_statuses = set()
        for log in state.logs:
            if log.level == LogLevel.INFO and "Status changed to" in log.message:
                status = log.context.get("status", "")
                if status and status not in seen_statuses:
                    seen_statuses.add(status)
                    step_info = step_mapping.get(
                        status,
                        {
                            "name": status.replace("_", " ").title(),
                            "description": f"Pipeline stage: {status}",
                        },
                    )
                    steps.append(
                        {
                            "name": step_info["name"],
                            "status": "completed",
                            "description": step_info["description"],
                            "timestamp": log.timestamp.isoformat(),
                        }
                    )

        # Data provenance
        provenance = {
            "original_file": state.input_path or "N/A",
            "conversion_method": "NeuroConv with AI-assisted metadata collection",
            "metadata_sources": [
                "User-provided metadata",
                "File header extraction",
                "AI-assisted inference",
            ],
            "agent_versions": "Multi-agent system: ConversationAgent, ConversionAgent, EvaluationAgent",
        }

        # User interactions
        user_interactions = []
        for log in state.logs:
            if "chat" in log.message.lower() or "user" in log.message.lower():
                user_interactions.append(
                    {
                        "timestamp": log.timestamp.isoformat(),
                        "action": log.message,
                    }
                )

        # Include metadata_provenance from state for HTML report
        # This preserves original provenance (AI-parsed, user-specified, etc.)
        # without storing it in the NWB file (which would violate DANDI compliance)
        metadata_provenance_dict = {}
        if state.metadata_provenance:
            for field_name, prov_info in state.metadata_provenance.items():
                metadata_provenance_dict[field_name] = {
                    "provenance": prov_info.provenance.value,
                    "confidence": prov_info.confidence,
                    "source": prov_info.source,
                    "needs_review": prov_info.needs_review,
                    "timestamp": prov_info.timestamp.isoformat(),
                }

        # Build detailed logs for sequential view with stage tags for scientific transparency
        detailed_logs_sequential, stage_options = self.prepare_logs_for_sequential_view(state.logs)

        return {
            "summary": summary,
            "technologies": technologies,
            "steps": steps,
            "provenance": provenance,
            "user_interactions": user_interactions if user_interactions else None,
            "metadata_provenance": metadata_provenance_dict,
            "detailed_logs_sequential": detailed_logs_sequential,  # New: chronological logs with stage tags
            "stage_options": stage_options,  # New: options for the stage filter dropdown
            "log_file_path": state.log_file_path,
        }

    def add_metadata_provenance(self, file_info: dict[str, Any], state: GlobalState) -> dict[str, Any]:
        """Add provenance information to metadata fields for transparency and reproducibility.

        Tracks the source of each metadata value with 6 provenance types:
        - user-specified: User directly provided value
        - file-extracted: Automatically extracted from file headers (includes source filename)
        - ai-parsed: AI parsed from unstructured text with high confidence
        - ai-inferred: AI inferred from available context
        - schema-default: NWB schema default value
        - system-default: System fallback value (N/A or Unknown)

        Args:
            file_info: Dictionary of metadata extracted from NWB file
            state: Global state containing metadata provenance tracking

        Returns:
            Dictionary with provenance information added for each field
        """
        # Get provenance tracking from state metadata (if available)
        metadata_provenance = state.metadata.get("_provenance", {})

        # Get source file information from state
        source_files = state.metadata.get("_source_files", {})
        primary_source_file = state.metadata.get("primary_data_file", "")

        # Create a copy with provenance information
        file_info_with_prov = dict(file_info)

        # Define which fields to track provenance for
        tracked_fields = [
            "experimenter",
            "institution",
            "lab",
            "session_description",
            "experiment_description",
            "session_id",
            "subject_id",
            "species",
            "sex",
            "age",
            "description",
            "genotype",
            "strain",
            "date_of_birth",
            "weight",
            "keywords",
            "pharmacology",
            "protocol",
            "surgery",
            "virus",
            "stimulus_notes",
            "data_collection",
        ]

        # Add provenance dict if not exists
        if "_provenance" not in file_info_with_prov:
            file_info_with_prov["_provenance"] = {}

        if "_source_files" not in file_info_with_prov:
            file_info_with_prov["_source_files"] = {}

        for field in tracked_fields:
            value = file_info.get(field)
            provenance_info = {}

            # Determine provenance source using complete 6-tag system
            if field in metadata_provenance:
                # Use tracked provenance from metadata collection
                prov_type = metadata_provenance[field]

                # Map old provenance types to new system
                if prov_type == "user-provided":
                    provenance_info["type"] = "user-specified"
                elif prov_type == "ai-parsed":
                    provenance_info["type"] = "ai-parsed"
                elif prov_type == "ai-inferred":
                    provenance_info["type"] = "ai-inferred"
                elif prov_type == "file-extracted":
                    provenance_info["type"] = "file-extracted"
                    # Add source filename if available
                    if field in source_files:
                        provenance_info["source_file"] = source_files[field]
                    elif primary_source_file:
                        provenance_info["source_file"] = os.path.basename(primary_source_file)
                elif prov_type == "default":
                    # Distinguish between schema defaults and system defaults
                    if value in ["N/A", "Unknown", "Not specified", ""]:
                        provenance_info["type"] = "system-default"
                    else:
                        provenance_info["type"] = "schema-default"
                else:
                    provenance_info["type"] = prov_type

            elif value and value not in ["N/A", "Unknown", "Not specified", [], "", None]:
                # Has a real value but no tracking
                # Check if it matches NWB schema defaults
                nwb_defaults = {"species": "Mus musculus", "genotype": "Wild-type", "strain": "C57BL/6J"}

                if field in nwb_defaults and value == nwb_defaults[field]:
                    provenance_info["type"] = "schema-default"
                else:
                    # Assume file-extracted with primary source file
                    provenance_info["type"] = "file-extracted"
                    if primary_source_file:
                        provenance_info["source_file"] = os.path.basename(primary_source_file)
            else:
                # System default value
                provenance_info["type"] = "system-default"

            # Store provenance information
            file_info_with_prov["_provenance"][field] = provenance_info["type"]

            # Store source file information if available
            if "source_file" in provenance_info:
                file_info_with_prov["_source_files"][field] = provenance_info["source_file"]

        state.add_log(
            LogLevel.DEBUG,
            f"Added metadata provenance for {len(file_info_with_prov['_provenance'])} fields with 6-tag system",
        )

        return file_info_with_prov

    async def generate_quality_assessment(self, validation_result: dict[str, Any]) -> dict[str, Any] | None:
        """Generate LLM-powered quality assessment for PASSED/PASSED_WITH_ISSUES files.

        Args:
            validation_result: Validation result dictionary with file_info and issues

        Returns:
            Quality assessment dictionary or None if LLM not available
        """
        if not self._llm_service or not self._prompt_service:
            return None

        # Create prompt using template
        prompt_data = self._prompt_service.create_llm_prompt(
            "evaluation_passed",
            {
                "file_info": validation_result.get("file_info", {}),
                "overall_status": validation_result.get("overall_status", "UNKNOWN"),
                "issues": validation_result.get("issues", []),
                "issue_counts": validation_result.get("issue_counts", {}),
            },
        )

        # Call LLM with structured output
        result = await self._llm_service.generate_structured_output(
            prompt=prompt_data["prompt"],
            output_schema=prompt_data["output_schema"],
            system_prompt=prompt_data["system_role"],
        )

        return dict(result)  # Cast Any to dict

    async def generate_correction_guidance(self, validation_result: dict[str, Any]) -> dict[str, Any] | None:
        """Generate LLM-powered correction guidance for FAILED files.

        Args:
            validation_result: Validation result dictionary with issues

        Returns:
            Correction guidance dictionary or None if LLM not available
        """
        if not self._llm_service or not self._prompt_service:
            return None

        # Create prompt using template
        prompt_data = self._prompt_service.create_llm_prompt(
            "evaluation_failed",
            {
                "nwb_file_path": validation_result.get("nwb_file_path", "unknown"),
                "issues": validation_result.get("issues", []),
                "issue_counts": validation_result.get("issue_counts", {}),
                "input_metadata": {},  # Could be passed from context
                "conversion_parameters": {},  # Could be passed from context
            },
        )

        # Call LLM with structured output
        result = await self._llm_service.generate_structured_output(
            prompt=prompt_data["prompt"],
            output_schema=prompt_data["output_schema"],
            system_prompt=prompt_data["system_role"],
        )

        return dict(result)  # Cast Any to dict
