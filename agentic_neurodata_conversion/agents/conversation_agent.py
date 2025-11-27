"""Conversation Agent implementation.

Responsible for:
- All user interactions
- Orchestrating conversion workflows
- Managing retry logic
- Gathering user input
"""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

from agentic_neurodata_conversion.agents.conversation import (
    ConversationalWorkflow,
    ImprovementWorkflow,
    MetadataCollector,
    MetadataParser,
    ProvenanceTracker,
    QueryHandler,
    RetryManager,
    RetryWorkflow,
    WorkflowOrchestrator,
)
from agentic_neurodata_conversion.agents.error_handling.adaptive_retry import AdaptiveRetryStrategy
from agentic_neurodata_conversion.agents.error_handling.autocorrect import SmartAutoCorrectionSystem
from agentic_neurodata_conversion.agents.error_handling.recovery import IntelligentErrorRecovery
from agentic_neurodata_conversion.agents.metadata.inference import MetadataInferenceEngine
from agentic_neurodata_conversion.agents.metadata.intelligent_mapper import IntelligentMetadataMapper
from agentic_neurodata_conversion.agents.metadata.predictive import PredictiveMetadataSystem
from agentic_neurodata_conversion.agents.utils.conversational_handler import ConversationalHandler
from agentic_neurodata_conversion.models import (
    ConversationPhase,
    ConversionStatus,
    GlobalState,
    LogLevel,
    MCPMessage,
    MCPResponse,
    ValidationOutcome,
    ValidationStatus,
)
from agentic_neurodata_conversion.models.workflow_state_manager import WorkflowStateManager
from agentic_neurodata_conversion.services import LLMService, MCPServer

# Maximum number of correction attempts allowed
# Maximum attempts for LLM to generate correction prompts (not conversion retries)
MAX_CORRECTION_ATTEMPTS = 3


class ConversationAgent:
    """Conversation agent for user interaction and workflow orchestration.

    This agent coordinates the conversion workflow by sending messages
    to other agents through the MCP server.
    """

    def __init__(
        self,
        mcp_server: MCPServer,
        llm_service: LLMService | None = None,
    ):
        """Initialize the conversation agent.

        Args:
            mcp_server: MCP server for agent communication
            llm_service: Optional LLM service for enhanced interactions
        """
        self._mcp_server = mcp_server
        self._llm_service = llm_service
        self._conversational_handler = ConversationalHandler(llm_service) if llm_service else None
        self._metadata_inference_engine = MetadataInferenceEngine(llm_service) if llm_service else None
        self._adaptive_retry_strategy = AdaptiveRetryStrategy(llm_service) if llm_service else None
        self._error_recovery = IntelligentErrorRecovery(llm_service) if llm_service else None
        self._predictive_metadata = PredictiveMetadataSystem(llm_service) if llm_service else None
        self._smart_autocorrect = SmartAutoCorrectionSystem(llm_service) if llm_service else None
        self._metadata_mapper = IntelligentMetadataMapper(llm_service) if llm_service else None
        self._workflow_manager = WorkflowStateManager()

        # Initialize Week 2 utility modules
        self._provenance_tracker = ProvenanceTracker()
        self._metadata_collector = MetadataCollector(llm_service)
        self._metadata_parser = MetadataParser(self._conversational_handler, self._metadata_mapper)
        self._retry_manager = RetryManager(llm_service, self._metadata_mapper)

        # Initialize Week 2 workflow modules (extracted from conversation_agent.py)
        self._workflow_orchestrator = WorkflowOrchestrator(
            mcp_server=mcp_server,
            metadata_collector=self._metadata_collector,
            metadata_parser=self._metadata_parser,
            provenance_tracker=self._provenance_tracker,
            workflow_manager=self._workflow_manager,
            conversational_handler=self._conversational_handler,
            metadata_inference_engine=self._metadata_inference_engine,
            llm_service=llm_service,
        )
        self._retry_workflow = RetryWorkflow(
            mcp_server=mcp_server,
            adaptive_retry_strategy=self._adaptive_retry_strategy,
            llm_service=llm_service,
        )
        self._conversational_workflow = ConversationalWorkflow(
            metadata_collector=self._metadata_collector,
            metadata_parser=self._metadata_parser,
            provenance_tracker=self._provenance_tracker,
            workflow_manager=self._workflow_manager,
            conversational_handler=self._conversational_handler,
            llm_service=llm_service,
        )
        self._improvement_workflow = ImprovementWorkflow(
            mcp_server=mcp_server,
            llm_service=llm_service,
        )
        self._query_handler = QueryHandler()

        logger.info("ConversationAgent initialized with 9 modular components (4 utilities + 5 workflows)")

        # Conversation history now managed in GlobalState to prevent memory leaks

    def _track_metadata_provenance(
        self,
        state: GlobalState,
        field_name: str,
        value: Any,
        provenance_type: str,
        confidence: float = 100.0,
        source: str = "",
        needs_review: bool = False,
        raw_input: str | None = None,
    ) -> None:
        """Track provenance for a metadata field - delegates to ProvenanceTracker."""
        self._provenance_tracker.track_metadata_provenance(
            state=state,
            field_name=field_name,
            value=value,
            provenance_type=provenance_type,
            confidence=confidence,
            source=source,
            needs_review=needs_review,
            raw_input=raw_input,
        )

    def _track_user_provided_metadata(
        self,
        state: GlobalState,
        field_name: str,
        value: Any,
        confidence: float = 100.0,
        source: str = "User explicitly provided",
        raw_input: str | None = None,
    ) -> None:
        """Track provenance for user-provided metadata - delegates to ProvenanceTracker."""
        self._provenance_tracker.track_user_provided_metadata(
            state=state,
            field_name=field_name,
            value=value,
            confidence=confidence,
            source=source,
            raw_input=raw_input,
        )

    def _track_ai_parsed_metadata(
        self,
        state: GlobalState,
        field_name: str,
        value: Any,
        confidence: float,
        raw_input: str,
        reasoning: str = "",
    ) -> None:
        """Track provenance for AI-parsed metadata - delegates to ProvenanceTracker."""
        self._provenance_tracker.track_ai_parsed_metadata(
            state=state,
            field_name=field_name,
            value=value,
            confidence=confidence,
            raw_input=raw_input,
            reasoning=reasoning,
        )

    def _track_auto_corrected_metadata(
        self,
        state: GlobalState,
        field_name: str,
        value: Any,
        source: str,
    ) -> None:
        """Track provenance for auto-corrected metadata - delegates to ProvenanceTracker."""
        self._provenance_tracker.track_auto_corrected_metadata(
            state=state,
            field_name=field_name,
            value=value,
            source=source,
        )

    async def _generate_dynamic_metadata_request(
        self,
        missing_fields: list[str],
        inference_result: dict[str, Any],
        file_info: dict[str, Any],
        state: GlobalState,
    ) -> str:
        """Generate dynamic metadata request - delegates to MetadataCollector."""
        return await self._metadata_collector.generate_dynamic_metadata_request(
            missing_fields=missing_fields,
            inference_result=inference_result,
            file_info=file_info,
            state=state,
        )

    async def handle_start_conversion(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """Start the conversion workflow - delegates to WorkflowOrchestrator.

        Args:
            message: MCP message with context containing conversion parameters
            state: Global state

        Returns:
            MCPResponse indicating workflow started
        """
        return await self._workflow_orchestrator.handle_start_conversion(message, state)

    async def _explain_error_to_user(
        self,
        error: dict[str, Any],
        context: dict[str, Any],
        state: GlobalState,
    ) -> dict[str, Any]:
        """Use LLM to explain errors in user-friendly terms.

        Transforms technical error messages into actionable guidance.
        This makes errors understandable and helps users know what to do next.

        Args:
            error: Error details from failed operation
            context: Context about what was being attempted
            state: Global state with conversion details

        Returns:
            Dict with user-friendly explanation and suggested actions
        """
        if not self._llm_service:
            # Fallback to basic explanation without LLM
            return {
                "explanation": error.get("message", "An error occurred during conversion"),
                "likely_cause": "Unknown",
                "suggested_actions": ["Check the logs for more details", "Try uploading a different file"],
                "is_recoverable": False,
            }

        try:
            system_prompt = """You are an expert at explaining technical errors in simple, helpful terms.

Your role is to help neuroscientists understand what went wrong during data conversion and guide them toward a solution.

Be:
- Clear and non-technical (avoid jargon)
- Empathetic and encouraging
- Actionable (tell them what to do next)
- Honest about whether the issue is fixable"""

            user_prompt = f"""A data conversion error occurred. Help the user understand what happened and what to do next.

Error Details:
- Message: {error.get("message", "Unknown error")}
- Code: {error.get("code", "UNKNOWN")}
- Context: {error.get("context", {})}

Conversion Context:
- Format: {context.get("format", "unknown")}
- Input file: {context.get("input_path", "unknown")}
- What was happening: {context.get("operation", "conversion")}

Provide:
1. Simple explanation of what went wrong (no technical jargon)
2. Likely cause (why this might have happened)
3. Specific actions the user can take
4. Whether this issue is fixable

Respond in JSON format."""

            output_schema = {
                "type": "object",
                "properties": {
                    "explanation": {"type": "string", "description": "Simple, clear explanation of what went wrong"},
                    "likely_cause": {"type": "string", "description": "Why this error probably occurred"},
                    "suggested_actions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific steps user can take to fix or work around the issue",
                    },
                    "is_recoverable": {
                        "type": "boolean",
                        "description": "Whether this error can be fixed by user action",
                    },
                    "help_url": {"type": "string", "description": "Optional URL to relevant documentation"},
                },
                "required": ["explanation", "likely_cause", "suggested_actions", "is_recoverable"],
            }

            explanation = await self._llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            state.add_log(
                LogLevel.INFO,
                "Generated user-friendly error explanation",
                {"error_code": error.get("code")},
            )

            return dict(explanation)  # Cast Any to dict

        except Exception as e:
            state.add_log(
                LogLevel.ERROR,
                f"Failed to generate error explanation: {e}",
            )
            # Fallback to basic explanation
            return {
                "explanation": error.get("message", "An error occurred during conversion"),
                "likely_cause": "See logs for technical details",
                "suggested_actions": ["Check the error logs", "Contact support if the issue persists"],
                "is_recoverable": False,
            }

    async def _generate_missing_metadata_message(
        self,
        missing_fields: list[str],
        metadata: dict[str, Any],
        state: GlobalState,
    ) -> str:
        """Generate missing metadata message - delegates to MetadataCollector."""
        return await self._metadata_collector.generate_missing_metadata_message(missing_fields, metadata, state)

    def _generate_fallback_missing_metadata_message(
        self,
        missing_fields: list[str],
    ) -> str:
        """Generate fallback message - delegates to MetadataCollector."""
        return self._metadata_collector._generate_fallback_missing_metadata_message(missing_fields)

    async def _proactive_issue_detection(
        self,
        input_path: str,
        format_name: str,
        state: GlobalState,
    ) -> dict[str, Any]:
        """Use LLM to analyze file BEFORE conversion and predict potential issues.

        This proactive approach prevents wasted time on conversions that will likely fail.

        Args:
            input_path: Path to input file
            format_name: Detected format name
            state: Global state

        Returns:
            Dictionary with risk_level, predicted_issues, suggested_fixes, success_probability
        """
        # Skip if no LLM
        if not self._llm_service:
            return {"risk_level": "unknown", "should_proceed": True}

        from pathlib import Path

        # Gather file characteristics
        try:
            file_path = Path(input_path)
            file_size_mb = file_path.stat().st_size / (1024 * 1024) if file_path.exists() else 0

            # Check for companion files
            parent_dir = file_path.parent
            sibling_files = [f.name for f in parent_dir.iterdir() if f.is_file()][:20]

            file_info = {
                "filename": file_path.name,
                "size_mb": round(file_size_mb, 2),
                "format": format_name,
                "sibling_files": sibling_files,
                "has_metadata_file": any(".meta" in f or ".json" in f for f in sibling_files),
            }
        except Exception as e:
            state.add_log(LogLevel.WARNING, f"Could not gather file info: {e}")
            return {"risk_level": "unknown", "should_proceed": True}

        system_prompt = """You are an expert in neuroscience data conversion with deep knowledge of:
- NWB format requirements
- Common data format pitfalls
- File structure issues
- Metadata requirements for DANDI

Analyze files BEFORE conversion to predict issues and prevent failures."""

        user_prompt = f"""Analyze this {format_name} file for potential NWB conversion issues:

File Information:
- Filename: {file_info["filename"]}
- Size: {file_info["size_mb"]} MB
- Format: {file_info["format"]}
- Sibling files: {file_info["sibling_files"]}
- Has metadata: {file_info["has_metadata_file"]}

Predict:
1. Likely validation issues
2. Missing metadata problems
3. File structure concerns
4. Success probability (0-100%)
5. Risk level (low/medium/high)

Be specific and actionable."""

        output_schema = {
            "type": "object",
            "properties": {
                "success_probability": {
                    "type": "number",
                    "description": "Probability of successful conversion (0-100)",
                },
                "risk_level": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "Overall risk assessment",
                },
                "predicted_issues": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "issue": {"type": "string"},
                            "severity": {"type": "string", "enum": ["info", "warning", "error"]},
                            "likelihood": {"type": "string", "enum": ["likely", "possible", "unlikely"]},
                        },
                    },
                    "description": "Potential issues that may occur",
                },
                "suggested_fixes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Actions user can take before conversion",
                },
                "warning_message": {
                    "type": "string",
                    "description": "User-friendly warning message if risks detected",
                },
                "should_proceed": {
                    "type": "boolean",
                    "description": "Whether conversion should proceed",
                },
            },
            "required": ["success_probability", "risk_level", "should_proceed"],
        }

        try:
            prediction = await self._llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            state.add_log(
                LogLevel.INFO,
                f"Proactive analysis: {prediction['risk_level']} risk, {prediction['success_probability']}% success probability",
                {
                    "risk_level": prediction["risk_level"],
                    "success_probability": prediction["success_probability"],
                    "predicted_issues_count": len(prediction.get("predicted_issues", [])),
                },
            )

            return dict(prediction)  # Cast Any to dict

        except Exception as e:
            state.add_log(LogLevel.WARNING, f"Proactive analysis failed: {e}")
            return {"risk_level": "unknown", "should_proceed": True}

    async def _decide_next_action(
        self,
        current_state: str,
        context: dict[str, Any],
        state: GlobalState,
    ) -> dict[str, Any]:
        """Use LLM to decide the next best action based on current state.

        This reduces hardcoded orchestration logic by having the LLM analyze
        the situation and suggest the optimal next step.

        Args:
            current_state: Current conversion state
            context: Context information
            state: Global state

        Returns:
            Dictionary with next_action, target_agent, reasoning
        """
        # Fallback if no LLM
        if not self._llm_service:
            return {
                "next_action": "continue",
                "target_agent": None,
                "reasoning": "No LLM available for decision-making",
            }

        system_prompt = """You are an intelligent agent orchestrator for NWB data conversion.
Analyze the current state and decide the best next action.

Consider:
- What just happened?
- What should happen next?
- Which agent should handle it?
- Are there any risks or blockers?

Be strategic and autonomous."""

        recent_logs = [log.message for log in state.logs[-5:]]

        user_prompt = f"""Current state: {current_state}
Context: {context}
Recent activity: {recent_logs}

What should happen next? Which agent should handle it?"""

        output_schema = {
            "type": "object",
            "properties": {
                "next_action": {
                    "type": "string",
                    "enum": [
                        "detect_format",
                        "run_conversion",
                        "validate",
                        "ask_user",
                        "retry",
                        "complete",
                        "fail",
                    ],
                },
                "target_agent": {
                    "type": "string",
                    "description": "Which agent should handle it (conversion/evaluation/conversation)",
                },
                "reasoning": {
                    "type": "string",
                    "description": "Why this is the best next step",
                },
                "should_notify_user": {
                    "type": "boolean",
                    "description": "Whether to notify user about this decision",
                },
            },
            "required": ["next_action", "target_agent", "reasoning"],
        }

        try:
            response = await self._llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            state.add_log(
                LogLevel.INFO,
                f"LLM decided next action: {response.get('next_action')} via {response.get('target_agent')}",
                {"reasoning": response.get("reasoning")},
            )

            return dict(response)  # Cast Any to dict

        except Exception as e:
            state.add_log(
                LogLevel.WARNING,
                f"Failed to get LLM decision: {e}",
            )
            return {
                "next_action": "continue",
                "target_agent": None,
                "reasoning": "Fallback to manual orchestration",
            }

    async def _generate_status_message(
        self,
        status: str,
        context: dict[str, Any],
        state: GlobalState,
    ) -> str:
        """Use LLM to generate contextual, engaging status messages.

        Replaces hardcoded templates with intelligent summaries that:
        - Acknowledge what happened
        - Highlight key information
        - Suggest next actions
        - Use friendly, conversational tone

        Args:
            status: Status type (e.g., "success", "failed", "retry_available")
            context: Context information (file paths, validation results, etc.)
            state: Global state

        Returns:
            LLM-generated status message
        """
        # Fallback message if LLM unavailable
        fallback_messages = {
            "success": "Conversion successful - NWB file is valid",
            "failed": "Conversion failed",
            "retry_available": "Validation failed - retry available",
            "completed_with_issues": "Conversion completed but has validation issues",
        }

        # If no LLM service, use fallback
        if not self._llm_service:
            return fallback_messages.get(status, "Operation completed")

        # Build context-rich prompt
        system_prompt = """You are a friendly, helpful AI assistant for neuroscience data conversion.
Generate concise, informative status messages that:
1. Clearly state what happened (success/failure)
2. Highlight key information (file size, format, validation results)
3. Suggest what the user can do next
4. Use a warm, encouraging tone
5. Keep it to 2-3 sentences max

Be specific and helpful, not generic."""

        # Extract relevant context
        format_name = context.get("format", "unknown")
        file_size_mb = context.get("file_size_mb", 0)
        validation_summary = context.get("validation_summary", {})
        output_path = context.get("output_path")
        input_filename = context.get("input_filename", "file")

        user_prompt = f"""Generate a status message for the user.

Status: {status}
Input file: {input_filename}
Format: {format_name}
File size: {file_size_mb:.1f}MB
Validation: {validation_summary}
Output: {output_path}

Create a friendly, informative message."""

        try:
            output_schema = {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The status message (2-3 sentences)",
                    },
                    "next_actions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional suggested next actions",
                    },
                },
                "required": ["message"],
            }

            response = await self._llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            state.add_log(
                LogLevel.INFO,
                "Generated LLM-powered status message",
                {"status": status},
            )

            return str(response.get("message", fallback_messages.get(status, "Operation completed")))  # Cast Any to str

        except Exception as e:
            state.add_log(
                LogLevel.WARNING,
                f"Failed to generate LLM status message: {e}",
            )
            return fallback_messages.get(status, "Operation completed")

    async def _generate_metadata_review_message(
        self, metadata: dict[str, Any], format_name: str, state: GlobalState
    ) -> str:
        """Generate metadata review message - delegates to MetadataCollector."""
        return await self._metadata_collector.generate_metadata_review_message(metadata, format_name, state)

    def _user_expresses_intent_to_add_more(self, user_message: str) -> bool:
        """Detect if user wants to add metadata but hasn't provided concrete data yet.

        This distinguishes between:
        - "I want to add some more" (intent only, no data) → Returns True
        - "age: P90D" (concrete data) → Returns False
        - "proceed" (wants to continue) → Returns False

        Args:
            user_message: User's message

        Returns:
            True if message expresses intent to add without providing concrete data
        """
        intent_phrases = [
            "want to add",
            "like to add",
            "add more",
            "add some",
            "yes",
            "sure",
            "i'll add",
            "let me add",
            "can i add",
        ]

        msg_lower = user_message.lower().strip()

        # Check if message expresses intent
        has_intent = any(phrase in msg_lower for phrase in intent_phrases)

        # Check if message contains concrete data (field: value format)
        has_concrete_data = ":" in user_message or "=" in user_message

        # Check if message is short (likely just expressing intent, not providing data)
        is_short_message = len(user_message.split()) < 10

        # Return True only if: has intent AND no concrete data AND short message
        return has_intent and not has_concrete_data and is_short_message

    async def _continue_conversion_workflow(
        self,
        message_id: str,
        input_path: str,
        detected_format: str,
        metadata: dict[str, Any],
        state: GlobalState,
    ) -> MCPResponse:
        """Continue the conversion workflow after metadata collection is complete.

        This skips format detection and metadata inference (already done) and proceeds
        directly to: Step 2 (custom metadata) → Step 3 (metadata review) → Step 4 (conversion)

        Args:
            message_id: Original message ID
            input_path: Path to input file
            detected_format: Already detected format
            metadata: Collected metadata
            state: Global state

        Returns:
            MCP response
        """
        state.add_log(
            LogLevel.INFO,
            "Continuing conversion workflow after metadata collection",
            {"format": detected_format, "metadata_fields": list(metadata.keys())},
        )

        # Step 2: Check for custom metadata
        is_standard_complete, missing = self._validate_required_nwb_metadata(metadata)

        all_missing_declined = all(field in state.user_declined_fields for field in missing) if missing else False

        should_ask_custom = (
            (is_standard_complete or all_missing_declined)
            and not metadata.get("_custom_metadata_prompted", False)
            and state.conversation_phase != ConversationPhase.METADATA_COLLECTION
            and not state.user_wants_sequential
        )

        if should_ask_custom:
            state.metadata["_custom_metadata_prompted"] = True
            state.conversation_type = "custom_metadata_collection"
            await state.update_status(ConversionStatus.AWAITING_USER_INPUT)

            custom_metadata_prompt = await self._generate_custom_metadata_prompt(detected_format, metadata, state)

            return MCPResponse.success_response(
                reply_to=message_id,
                result={
                    "status": "need_user_input",
                    "message": custom_metadata_prompt,
                    "conversation_type": "custom_metadata_collection",
                },
            )

        # Step 3: Show metadata review before conversion
        if not metadata.get("_metadata_review_shown", False):
            state.metadata["_metadata_review_shown"] = True
            state.conversation_type = "metadata_review"
            await state.update_status(ConversionStatus.AWAITING_USER_INPUT)

            review_message = await self._generate_metadata_review_message(metadata, detected_format, state)

            return MCPResponse.success_response(
                reply_to=message_id,
                result={
                    "status": "metadata_review",
                    "message": review_message,
                    "conversation_type": "metadata_review",
                    "metadata": metadata,
                },
            )

        # Step 4: Run conversion
        return await self._run_conversion(
            message_id,
            input_path,
            detected_format,
            metadata,
            state,
        )

    async def _generate_custom_metadata_prompt(
        self, format_name: str, metadata: dict[str, Any], state: GlobalState
    ) -> str:
        """Generate custom metadata prompt - delegates to MetadataCollector."""
        return await self._metadata_collector.generate_custom_metadata_prompt(format_name, metadata, state)

    async def _handle_custom_metadata_response(self, user_input: str, state: GlobalState) -> dict[str, Any]:
        """Process user's custom metadata input - delegates parsing to MetadataParser."""
        # Delegate parsing to MetadataParser
        parsed_metadata = await self._metadata_parser.handle_custom_metadata_response(user_input, state)

        if not parsed_metadata:
            return {}

        # Handle provenance tracking and state updates (orchestration logic)
        if parsed_metadata.get("standard_fields"):
            state.metadata.update(parsed_metadata["standard_fields"])
            for field, value in parsed_metadata["standard_fields"].items():
                self._track_ai_parsed_metadata(
                    state=state,
                    field_name=field,
                    value=value,
                    confidence=90,
                    raw_input=user_input,
                    reasoning="Parsed from custom metadata input",
                )

        if parsed_metadata.get("custom_fields"):
            if "_custom_fields" not in state.metadata:
                state.metadata["_custom_fields"] = {}
            state.metadata["_custom_fields"].update(parsed_metadata["custom_fields"])

        if parsed_metadata.get("mapping_report"):
            state.metadata["_mapping_report"] = parsed_metadata["mapping_report"]

        return parsed_metadata

    async def _finalize_with_minimal_metadata(
        self,
        original_message_id: str,
        output_path: str,
        validation_result: dict[str, Any],
        format_name: str,
        input_path: str,
        state: GlobalState,
    ) -> MCPResponse:
        """Complete conversion with minimal metadata and create informative report.

        This is called when user declines to provide additional metadata.
        Instead of looping infinitely asking for metadata, we:
        1. Accept the conversion as-is
        2. Generate a comprehensive report showing what's missing
        3. Provide guidance on how to add metadata later if needed

        Args:
            original_message_id: Original message ID for reply
            output_path: Path to generated NWB file
            validation_result: Validation result with issues
            format_name: Data format name
            input_path: Input file path
            state: Global state

        Returns:
            MCPResponse with completion status and guidance
        """
        from pathlib import Path

        state.add_log(
            LogLevel.INFO,
            "Finalizing conversion with minimal metadata",
            {"output_path": output_path},
        )

        # Generate evaluation report (even with warnings)
        report_msg = MCPMessage(
            target_agent="evaluation",
            action="generate_report",
            context={
                "validation_result": validation_result,
                "nwb_path": output_path,
            },
        )

        report_response = await self._mcp_server.send_message(report_msg)
        report_path = None
        if report_response.success:
            report_path = report_response.result.get("report_path")

        # Extract missing fields from validation issues
        missing_fields = []
        for issue in validation_result.get("issues", []):
            issue_msg = issue.get("message", "").lower()
            if "missing" in issue_msg or "not found" in issue_msg:
                # Extract field name from message
                for field in ["experimenter", "institution", "keywords", "subject", "session_description"]:
                    if field in issue_msg:
                        missing_fields.append(field)

        # Generate helpful completion message
        completion_message = f"""Conversion complete! Your NWB file has been created at: {Path(output_path).name}

**Status:** Completed with warnings

**What was created:**
- Valid NWB file structure ✓
- Your {format_name} data successfully converted ✓
- File size: {Path(output_path).stat().st_size / (1024 * 1024):.1f} MB

**Missing recommended metadata:**
{chr(10).join(f"- {field}" for field in missing_fields) if missing_fields else "- Some metadata fields"}

**What this means:**
- Your file is technically valid and can be used for analysis
- It may not meet requirements for data sharing (e.g., DANDI archive)
- You can add metadata later if needed

**How to add metadata later:**
1. Use PyNWB to programmatically update the file
2. Re-run conversion with metadata when available
3. Contact support for assistance

The conversion report has been generated with full details."""

        return MCPResponse.success_response(
            reply_to=original_message_id,
            result={
                "status": "completed_with_warnings",
                "output_path": output_path,
                "validation": validation_result,
                "report_path": report_path,
                "message": completion_message,
                "missing_fields": list(set(missing_fields)),
                "user_declined_metadata": True,
            },
        )

    def _validate_required_nwb_metadata(
        self,
        metadata: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """Validate required NWB metadata - delegates to MetadataCollector."""
        return self._metadata_collector.validate_required_nwb_metadata(metadata)

    async def _run_conversion(
        self,
        original_message_id: str,
        input_path: str,
        format_name: str,
        metadata: dict[str, Any],
        state: GlobalState,
    ) -> MCPResponse:
        """Run the conversion and validation steps.

        Args:
            original_message_id: Original message ID for reply
            input_path: Path to input data
            format_name: Data format name
            metadata: Metadata dictionary
            state: Global state

        Returns:
            MCPResponse with conversion and validation results
        """
        import tempfile
        from pathlib import Path

        # ENHANCED: Make validation non-blocking - warn but proceed
        # Users can choose to continue with whatever metadata they have
        is_valid, missing_fields = self._validate_required_nwb_metadata(metadata)

        if not is_valid:
            state.add_log(
                LogLevel.WARNING,
                f"Some recommended NWB metadata fields are missing: {missing_fields}",
                {"missing_fields": missing_fields},
            )

            # Store missing fields info for potential later use
            # But DO NOT block conversion - users should have the choice
            state.metadata["_missing_fields_warning"] = {
                "fields": missing_fields,
                "message": f"Note: Some recommended fields are missing ({', '.join(missing_fields)}). The conversion will proceed with available metadata.",
                "timestamp": datetime.now().isoformat(),
            }

        # ENHANCEMENT: Auto-fill optional fields from inference if not provided by user
        # This ensures NWB Inspector validation passes for recommended fields
        inference_result = getattr(state, "inference_result", {})
        if inference_result:
            inferred_metadata = inference_result.get("inferred_metadata", {})
            confidence_scores = inference_result.get("confidence_scores", {})

            # Fields to auto-fill if missing (NWB Inspector checks these)
            optional_fields_to_infer = ["keywords", "experiment_description", "session_description"]

            for field_name in optional_fields_to_infer:
                # Only add if:
                # 1. Not already in metadata (user didn't provide it)
                # 2. Was inferred with reasonable confidence (>= 60%)
                # 3. Inference result has this field
                if (
                    not metadata.get(field_name)
                    and field_name in inferred_metadata
                    and confidence_scores.get(field_name, 0) >= 60
                ):
                    inferred_value = inferred_metadata[field_name]
                    confidence = confidence_scores.get(field_name, 60)

                    # Add to metadata
                    metadata[field_name] = inferred_value
                    state.metadata[field_name] = inferred_value

                    # Track provenance as AI-inferred
                    self._track_metadata_provenance(
                        state=state,
                        field_name=field_name,
                        value=inferred_value,
                        provenance_type="ai-inferred",
                        confidence=confidence,
                        source=f"Inferred from file analysis: {Path(input_path).name}",
                        needs_review=True,  # AI inferences should be reviewed
                        raw_input=f"Automatically inferred from: {Path(input_path).name}",
                    )

                    state.add_log(
                        LogLevel.INFO,
                        f"Auto-filled {field_name} from AI inference (confidence: {confidence}%)",
                        {
                            "field": field_name,
                            "value": str(inferred_value)[:100],  # Truncate for logging
                            "confidence": confidence,
                            "provenance": "ai-inferred",
                        },
                    )

        # Generate output path
        output_dir = Path(tempfile.gettempdir()) / "nwb_conversions"
        output_dir.mkdir(exist_ok=True)
        output_path = str(output_dir / f"converted_{Path(input_path).stem}.nwb")

        # Run conversion
        convert_msg = MCPMessage(
            target_agent="conversion",
            action="run_conversion",
            context={
                "input_path": input_path,
                "output_path": output_path,
                "format": format_name,
                "metadata": metadata,
            },
        )

        convert_response = await self._mcp_server.send_message(convert_msg)

        if not convert_response.success:
            await state.update_status(ConversionStatus.FAILED)

            # Use LLM to explain the error in user-friendly terms
            error_explanation = await self._explain_error_to_user(
                error=convert_response.error,
                context={
                    "format": format_name,
                    "input_path": input_path,
                    "operation": "NWB conversion",
                },
                state=state,
            )

            return MCPResponse.error_response(
                reply_to=original_message_id,
                error_code="CONVERSION_FAILED",
                error_message=error_explanation["explanation"],
                error_context={
                    "technical_error": convert_response.error,
                    "user_friendly": error_explanation,
                },
            )

        # Step 3: Run validation
        validate_msg = MCPMessage(
            target_agent="evaluation",
            action="run_validation",
            context={"nwb_path": output_path},
        )

        validate_response = await self._mcp_server.send_message(validate_msg)

        if not validate_response.success:
            await state.update_status(ConversionStatus.FAILED)

            # Use LLM to explain validation failure
            error_explanation = await self._explain_error_to_user(
                error=validate_response.error,
                context={
                    "format": format_name,
                    "input_path": input_path,
                    "operation": "NWB validation",
                },
                state=state,
            )

            return MCPResponse.error_response(
                reply_to=original_message_id,
                error_code="VALIDATION_FAILED",
                error_message=error_explanation["explanation"],
                error_context={
                    "technical_error": validate_response.error,
                    "user_friendly": error_explanation,
                },
            )

        validation_result = validate_response.result.get("validation_result")
        overall_status_str = validation_result.get("overall_status", "UNKNOWN")

        # WORKFLOW_CONDITION_FLAGS_ANALYSIS.md Fix: Use ValidationOutcome enum
        # Convert string to enum for type-safe comparisons
        try:
            overall_status = ValidationOutcome(overall_status_str)
        except ValueError:
            # Fallback for unknown values
            overall_status = overall_status_str

        # Handle the three validation outcomes as per requirements (Story 8.1-8.3)
        # 1. PASSED - No issues at all
        # 2. PASSED_WITH_ISSUES - Has warnings/best practice issues
        # 3. FAILED - Has critical/error issues

        if overall_status == ValidationOutcome.PASSED:
            await state.update_status(ConversionStatus.COMPLETED)
            state.add_log(
                LogLevel.INFO,
                "Conversion completed successfully with valid NWB file",
            )

            # Generate evaluation report
            report_msg = MCPMessage(
                target_agent="evaluation",
                action="generate_report",
                context={
                    "validation_result": validation_result,
                    "nwb_path": output_path,
                },
            )

            report_response = await self._mcp_server.send_message(report_msg)

            report_path = None
            if report_response.success:
                report_path = report_response.result.get("report_path")
                state.add_log(
                    LogLevel.INFO,
                    f"Evaluation report generated: {report_path}",
                )

            # Generate LLM-powered status message
            from pathlib import Path

            status_message = await self._generate_status_message(
                status="success",
                context={
                    "format": format_name,
                    "file_size_mb": (
                        Path(output_path).stat().st_size / (1024 * 1024) if Path(output_path).exists() else 0
                    ),
                    "validation_summary": validation_result.get("summary", {}),
                    "output_path": output_path,
                    "input_filename": Path(input_path).name,
                },
                state=state,
            )

            return MCPResponse.success_response(
                reply_to=original_message_id,
                result={
                    "status": "completed",
                    "output_path": output_path,
                    "validation": validation_result,
                    "report_path": report_path,
                    "message": status_message,  # LLM-POWERED!
                },
            )

        elif overall_status == ValidationOutcome.PASSED_WITH_ISSUES:
            # Validation passed but has warnings - user chooses IMPROVE or ACCEPT
            # (Requirements Story 8.3, lines 837-848)

            # Generate report with warnings highlighted
            report_msg = MCPMessage(
                target_agent="evaluation",
                action="generate_report",
                context={
                    "validation_result": validation_result,
                    "nwb_path": output_path,
                },
            )

            report_response = await self._mcp_server.send_message(report_msg)
            report_path = None
            if report_response.success:
                report_path = report_response.result.get("report_path")

            # Store validation result for improvement decision handler
            state.metadata["last_validation_result"] = validation_result

            # Generate user-friendly message about warnings
            warnings_summary = validation_result.get("summary", {})
            warning_count = warnings_summary.get("warning", 0)
            best_practice_count = warnings_summary.get("best_practice", 0)
            info_count = warnings_summary.get("info", 0)

            # Build issue summary message (FIX: Include INFO issues)
            issue_parts = []
            if warning_count > 0:
                issue_parts.append(f"{warning_count} warning{'s' if warning_count != 1 else ''}")
            if best_practice_count > 0:
                issue_parts.append(
                    f"{best_practice_count} best practice suggestion{'s' if best_practice_count != 1 else ''}"
                )
            if info_count > 0:
                issue_parts.append(f"{info_count} informational issue{'s' if info_count != 1 else ''}")

            issue_summary = ", ".join(issue_parts) if issue_parts else "some issues"

            # Build detailed issue list to show user WHAT the problems are
            issues_list = validation_result.get("issues", [])
            issue_details = []
            for idx, issue in enumerate(issues_list[:5], 1):  # Show top 5 issues
                severity = issue.get("severity", "INFO")
                message_text = issue.get("message", "Unknown issue")
                issue_details.append(f"  {idx}. [{severity}] {message_text}")

            if len(issues_list) > 5:
                issue_details.append(f"  ... and {len(issues_list) - 5} more issues")

            issue_details_text = "\n".join(issue_details) if issue_details else "  (No details available)"

            message = (
                f"✅ Your NWB file passed validation, but has {issue_summary}.\n\n"
                "**Issues found:**\n"
                f"{issue_details_text}\n\n"
                "The file is technically valid and can be used, but fixing these issues "
                "will improve data quality and DANDI archive compatibility.\n\n"
                "Would you like to improve the file by fixing these issues, or accept it as-is?"
            )

            state.llm_message = message
            await state.update_status(ConversionStatus.AWAITING_USER_INPUT)
            # Use enum instead of string
            state.conversation_phase = ConversationPhase.IMPROVEMENT_DECISION
            state.conversation_type = state.conversation_phase.value  # Backward compatibility

            state.add_log(
                LogLevel.INFO,
                "Validation PASSED_WITH_ISSUES - awaiting user decision (improve or accept)",
                {
                    "warnings": warning_count,
                    "best_practice": best_practice_count,
                    "info": info_count,
                    "overall_status": overall_status,
                },
            )

            return MCPResponse.success_response(
                reply_to=original_message_id,
                result={
                    "status": "awaiting_user_input",
                    "conversation_type": "improvement_decision",
                    "overall_status": overall_status,
                    "message": message,
                    "output_path": output_path,
                    "validation": validation_result,
                    "report_path": report_path,
                },
            )

        else:
            # Validation FAILED - has critical or error issues
            # Use LLM to analyze and respond intelligently
            # Bug #14 fix: Always allow retry (unlimited with user permission)
            if self._conversational_handler:
                await state.update_status(ConversionStatus.AWAITING_USER_INPUT)
                state.add_log(
                    LogLevel.INFO,
                    "Using LLM to analyze validation issues and engage user",
                )

                try:
                    # Get intelligent LLM analysis of validation issues
                    llm_analysis = await self._conversational_handler.analyze_validation_and_respond(
                        validation_result=validation_result,
                        nwb_file_path=output_path,
                        state=state,
                    )

                    # CHECK IF WE SHOULD PROCEED WITH MINIMAL METADATA
                    if llm_analysis.get("proceed_with_minimal", False):
                        await state.update_status(ConversionStatus.COMPLETED)
                        state.add_log(
                            LogLevel.INFO,
                            "User wants minimal conversion - completing with warnings",
                        )

                        # Generate completion report with warnings
                        return await self._finalize_with_minimal_metadata(
                            original_message_id=original_message_id,
                            output_path=output_path,
                            validation_result=validation_result,
                            format_name=format_name,
                            input_path=input_path,
                            state=state,
                        )

                    # Add to conversation history
                    state.add_conversation_message(
                        role="assistant", content=llm_analysis.get("message", ""), context=llm_analysis
                    )

                    # Store conversational state for frontend
                    state.conversation_phase = ConversationPhase.VALIDATION_ANALYSIS
                    state.conversation_type = state.conversation_phase.value  # Backward compatibility
                    state.llm_message = llm_analysis.get("message")

                    return MCPResponse.success_response(
                        reply_to=original_message_id,
                        result={
                            "status": "awaiting_user_input",
                            "conversation_type": "validation_analysis",
                            "message": llm_analysis.get("message"),
                            "needs_user_input": llm_analysis.get("needs_user_input", True),
                            "suggested_fixes": llm_analysis.get("suggested_fixes", []),
                            "required_fields": llm_analysis.get("required_fields", []),  # Smart metadata fields
                            "suggestions": llm_analysis.get("suggestions", []),  # LLM suggestions
                            "detected_data_type": llm_analysis.get("detected_data_type"),  # Inferred data type
                            "severity": llm_analysis.get("severity", "medium"),
                            "validation": validation_result,
                            "can_retry": True,
                        },
                    )
                except Exception as e:
                    state.add_log(
                        LogLevel.ERROR,
                        f"LLM analysis failed, falling back to standard flow: {e}",
                    )
                    # Fallback to original rigid behavior
                    pass

            # Bug #14 fix: Always allow retry - unlimited attempts with user permission
            # (Story 8.7 line 933, Story 8.8 line 953)
            await state.update_status(ConversionStatus.AWAITING_RETRY_APPROVAL)
            state.add_log(
                LogLevel.WARNING,
                "Validation failed - awaiting retry approval",
            )

            # Generate LLM-powered retry message
            retry_message = await self._generate_status_message(
                status="retry_available",
                context={
                    "format": format_name,
                    "file_size_mb": (
                        Path(output_path).stat().st_size / (1024 * 1024) if Path(output_path).exists() else 0
                    ),
                    "validation_summary": validation_result.get("summary", {}),
                    "output_path": output_path,
                    "input_filename": Path(input_path).name,
                    "retry_count": state.correction_attempt,
                },
                state=state,
            )

            return MCPResponse.success_response(
                reply_to=original_message_id,
                result={
                    "status": "awaiting_retry_approval",
                    "validation": validation_result,
                    "can_retry": True,
                    "message": retry_message,  # LLM-POWERED!
                },
            )

    async def handle_user_format_selection(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """Handle format selection - delegates to QueryHandler.

        Args:
            message: MCP message with selected format
            state: Global state

        Returns:
            MCPResponse with conversion workflow continuation
        """
        return await self._query_handler.handle_user_format_selection(
            message, state, self._workflow_orchestrator._run_conversion
        )

    async def handle_retry_decision(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """Handle user's retry approval/rejection - delegates to RetryWorkflow.

        Args:
            message: MCP message with user decision
            state: Global state

        Returns:
            MCPResponse with next steps
        """
        return await self._retry_workflow.handle_retry_decision(message, state, self.handle_start_conversion)

    async def handle_conversational_response(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """Handle conversational response - delegates to ConversationalWorkflow.

        Args:
            message: MCP message with user's response
            state: Global state

        Returns:
            MCPResponse with next conversation turn or action
        """
        return await self._conversational_workflow.handle_conversational_response(
            message,
            state,
            self.handle_start_conversion,
            self._workflow_orchestrator.continue_conversion_workflow,
            self._workflow_orchestrator._run_conversion,
        )

    async def handle_general_query(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """Handle general query - delegates to ConversationalWorkflow.

        Args:
            message: MCP message with user query
            state: Global state with conversion context

        Returns:
            MCPResponse with intelligent answer
        """
        return await self._conversational_workflow.handle_general_query(message, state)

    async def handle_improvement_decision(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """Handle improvement decision - delegates to ImprovementWorkflow.

        Args:
            message: MCP message with context containing 'decision'
            state: Global state

        Returns:
            MCPResponse with result
        """
        return await self._improvement_workflow.handle_improvement_decision(message, state)

    async def _handle_auto_fix_approval_response(
        self, user_message: str, reply_to: str, state: GlobalState
    ) -> MCPResponse:
        """Handle user's response to auto-fix approval request.

        Args:
            user_message: User's message
            reply_to: Message ID to reply to
            state: Global state

        Returns:
            MCPResponse with result
        """
        user_msg_lower = user_message.lower().strip()

        # Option 1: User approves auto-fix
        if any(keyword in user_msg_lower for keyword in ["apply", "yes", "fix", "proceed", "go ahead", "do it"]):
            state.add_log(
                LogLevel.INFO,
                "User approved auto-fixes, applying corrections",
            )

            # Get stored correction context
            correction_context = state.correction_context
            if not correction_context:
                # Clear stale state
                state.llm_message = None
                state.conversation_type = None

                return MCPResponse.error_response(
                    reply_to=reply_to,
                    error_code="NO_CORRECTION_CONTEXT",
                    error_message="Cannot find correction context. Please try again.",
                )

            # PRIORITY 2 FIX: Extract auto-fixable issues and convert to metadata fixes
            auto_fixable_issues = correction_context.get("auto_fixable_issues", [])
            auto_fixes = self._extract_fixes_from_issues(auto_fixable_issues, state)

            state.add_log(
                LogLevel.INFO,
                f"Extracted {len(auto_fixes)} automatic fixes from {len(auto_fixable_issues)} issues",
                {"fixes": auto_fixes},
            )

            # PROVENANCE TRACKING: Track auto-corrected metadata
            for field_name, value in auto_fixes.items():
                issue_desc = next(
                    (
                        issue.get("message", "")
                        for issue in auto_fixable_issues
                        if issue.get("field_name") == field_name
                        or field_name.lower() in issue.get("message", "").lower()
                    ),
                    "Auto-fix for validation issue",
                )
                self._track_auto_corrected_metadata(
                    state=state,
                    field_name=field_name,
                    value=value,
                    source=f"Automatic correction during error recovery: {issue_desc[:100]}",
                )

            # Apply corrections and reconvert
            reconvert_msg = MCPMessage(
                target_agent="conversion",
                action="apply_corrections",
                context={
                    "input_path": str(state.input_path),
                    "correction_context": correction_context,
                    "auto_fixes": auto_fixes,  # Pass extracted fixes
                    "metadata": state.metadata,
                },
            )

            await self._mcp_server.send_message(reconvert_msg)

            # Update state
            state.llm_message = "Applying automatic corrections and reconverting..."
            await state.update_status(ConversionStatus.CONVERTING)
            state.conversation_type = None  # Clear conversation type

            return MCPResponse.success_response(
                reply_to=reply_to,
                result={
                    "status": "reconverting",
                    "message": "Applying automatic corrections and reconverting...",
                    "fixes_applied": len(auto_fixes),
                },
            )

        # Option 2: User wants to see details first
        elif any(keyword in user_msg_lower for keyword in ["show", "detail", "what", "which", "list"]):
            state.add_log(
                LogLevel.INFO,
                "User requested detailed view of auto-fixable issues",
            )

            # Get correction context
            correction_context = state.correction_context
            if not correction_context:
                return MCPResponse.error_response(
                    reply_to=reply_to,
                    error_code="NO_CORRECTION_CONTEXT",
                    error_message="Cannot find correction context. Please try again.",
                )

            auto_fixable = correction_context.get("auto_fixable_issues", [])

            # Generate detailed list
            detailed_list = "Here are the issues I can fix automatically:\n\n"
            for i, issue in enumerate(auto_fixable, 1):
                check_name = issue.get("check_name", "Unknown")
                message = issue.get("message", "No details")
                severity = issue.get("severity", "warning")
                detailed_list += f"{i}. **{check_name}** ({severity})\n   {message}\n\n"

            detailed_list += "\nWould you like me to apply these fixes? (respond with 'apply' or 'cancel')"

            state.llm_message = detailed_list
            # Keep conversation_type as "auto_fix_approval" for next turn

            return MCPResponse.success_response(
                reply_to=reply_to,
                result={
                    "status": "awaiting_user_input",
                    "message": detailed_list,
                },
            )

        # Option 3: User cancels
        elif any(keyword in user_msg_lower for keyword in ["cancel", "no", "keep", "don't", "skip"]):
            state.add_log(
                LogLevel.INFO,
                "User cancelled auto-fixes, accepting file as-is",
            )

            # Accept file with warnings - finalize
            await state.update_validation_status(ValidationStatus.PASSED_ACCEPTED)
            await state.update_status(ConversionStatus.COMPLETED)

            # Clear all correction state
            state.correction_context = None
            state.conversation_type = None

            state.llm_message = (
                "Understood! I'll keep the file as-is. Your NWB file is ready for download with the existing warnings."
            )

            return MCPResponse.success_response(
                reply_to=reply_to,
                result={
                    "status": "completed",
                    "message": state.llm_message,
                    "validation_status": "passed_accepted",
                },
            )

        # User didn't give a clear answer - ask again
        else:
            clarification_msg = (
                "I didn't understand your response. Please respond with:\n"
                "• **'apply'** - to automatically fix the issues\n"
                "• **'show details'** - to see exactly what will be changed\n"
                "• **'cancel'** - to keep the file as-is"
            )

            state.llm_message = clarification_msg

            return MCPResponse.success_response(
                reply_to=reply_to,
                result={
                    "status": "awaiting_user_input",
                    "message": clarification_msg,
                },
            )

    def _extract_fixes_from_issues(
        self, auto_fixable_issues: list[dict[str, Any]], state: GlobalState
    ) -> dict[str, Any]:
        """PRIORITY 2 FIX: Extract metadata fixes from auto-fixable issues.

        Converts validation issues into concrete metadata field updates.

        Args:
            auto_fixable_issues: List of issues that can be automatically fixed
            state: Global state for logging

        Returns:
            Dictionary mapping field names to their corrected values
        """
        auto_fixes = {}

        for issue in auto_fixable_issues:
            # Get suggested fix from issue analysis
            suggested_fix = issue.get("suggested_fix")
            field_name = issue.get("field_name")

            if suggested_fix and field_name:
                # Direct field/value mapping available
                auto_fixes[field_name] = suggested_fix
                state.add_log(
                    LogLevel.DEBUG, f"Extracted fix: {field_name} = {suggested_fix}", {"issue": issue.get("check_name")}
                )
            else:
                # Try to infer fix from issue message
                inferred_fix = self._infer_fix_from_issue(issue, state)
                if inferred_fix:
                    auto_fixes.update(inferred_fix)

        return auto_fixes

    def _infer_fix_from_issue(self, issue: dict[str, Any], state: GlobalState) -> dict[str, Any] | None:
        """Infer metadata fix from validation issue message.

        Args:
            issue: Validation issue dict
            state: Global state

        Returns:
            Dictionary with inferred fix, or None if unable to infer
        """
        message = issue.get("message", "").lower()
        check_name = issue.get("check_name", "").lower()

        # Common patterns for missing metadata
        if "experimenter" in message or "experimenter" in check_name:
            # Use existing metadata if available, otherwise use placeholder
            return {"experimenter": state.metadata.get("experimenter", "Unknown")}

        elif "institution" in message or "institution" in check_name:
            return {"institution": state.metadata.get("institution", "Unknown")}

        elif "session_description" in message or "session_description" in check_name:
            # Generate from experiment_description if available
            exp_desc = state.metadata.get("experiment_description")
            return {"session_description": exp_desc if exp_desc else "Electrophysiology recording session"}

        elif "subject_id" in message or "subject_id" in check_name:
            return {"subject_id": state.metadata.get("subject_id", "subject_001")}

        # Unable to infer fix
        state.add_log(LogLevel.DEBUG, f"Could not infer fix for issue: {check_name}", {"message": message[:100]})
        return None

    async def _extract_metadata_from_message(self, user_message: str, state: GlobalState) -> dict[str, Any]:
        """Extract metadata from user's message - delegates to MetadataParser."""
        return await self._metadata_parser.extract_metadata_from_message(user_message, state)

    def _validate_metadata_format(self, metadata: dict[str, Any]) -> dict[str, str]:
        """Validate metadata format - delegates to MetadataParser."""
        return self._metadata_parser.validate_metadata_format(metadata)

    def _extract_auto_fixes(self, corrections: dict[str, Any]) -> dict[str, Any]:
        """Extract auto-fixable issues - delegates to RetryWorkflow."""
        return self._retry_workflow._extract_auto_fixes(corrections)

    def _identify_user_input_required(self, corrections: dict[str, Any]) -> list[dict[str, Any]]:
        """Identify issues requiring user input - delegates to RetryWorkflow."""
        return self._retry_workflow._identify_user_input_required(corrections)

    def _generate_auto_fix_summary(self, auto_fixable: list[dict[str, Any]]) -> str:
        """Generate summary of auto-fixable issues - delegates to ImprovementWorkflow."""
        return self._improvement_workflow._generate_auto_fix_summary(auto_fixable)

    def _generate_basic_correction_prompts(self, issues: list[dict[str, Any]]) -> str:
        """Generate basic correction prompts - delegates to ImprovementWorkflow."""
        return self._improvement_workflow._generate_basic_correction_prompts(issues)

    async def _generate_correction_prompts(self, issues: list[dict[str, Any]], state: GlobalState) -> str:
        """Generate correction prompts with LLM - delegates to ImprovementWorkflow."""
        return await self._improvement_workflow._generate_correction_prompts(issues, state)

    def _is_valid_date_format(self, value: str) -> bool:
        """Check if a date string is in valid format.

        Args:
            value: Date string to check

        Returns:
            True if valid format
        """
        import re

        # ISO format check
        iso_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        if re.match(iso_pattern, str(value)):
            return True

        # Try parsing with dateutil
        try:
            from dateutil import parser

            parser.parse(str(value))
            return True
        except (ValueError, TypeError, AttributeError, ImportError):
            # ValueError: Invalid date format
            # TypeError: value is None or wrong type
            # AttributeError: parser module issue
            # ImportError: dateutil not installed
            # Silently return False as this is a validation check
            return False


def register_conversation_agent(
    mcp_server: MCPServer,
    llm_service: LLMService | None = None,
) -> ConversationAgent:
    """Register Conversation Agent handlers with MCP server.

    Args:
        mcp_server: MCP server instance
        llm_service: Optional LLM service

    Returns:
        ConversationAgent instance
    """
    agent = ConversationAgent(
        mcp_server=mcp_server,
        llm_service=llm_service,
    )

    mcp_server.register_handler(
        "conversation",
        "start_conversion",
        agent.handle_start_conversion,
    )

    mcp_server.register_handler(
        "conversation",
        "user_format_selection",
        agent.handle_user_format_selection,
    )

    mcp_server.register_handler(
        "conversation",
        "retry_decision",
        agent.handle_retry_decision,
    )

    mcp_server.register_handler(
        "conversation",
        "improvement_decision",
        agent.handle_improvement_decision,
    )

    mcp_server.register_handler(
        "conversation",
        "conversational_response",
        agent.handle_conversational_response,
    )

    mcp_server.register_handler(
        "conversation",
        "general_query",
        agent.handle_general_query,
    )

    return agent
