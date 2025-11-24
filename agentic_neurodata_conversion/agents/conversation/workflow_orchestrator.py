"""Workflow orchestrator module for conversation agent.

Handles:
- Main conversion workflow (start_conversion)
- Step-by-step orchestration through workflow phases
- Format detection coordination
- Metadata collection workflow
- Conversion execution and validation
- Error handling and user guidance
- Intelligent decision-making with LLM

This module is the primary workflow coordinator, delegating to:
- ConversionAgent: Format detection and conversion
- EvaluationAgent: Validation and quality assessment
- MetadataCollector: Metadata collection and validation
- ConversationalHandler: LLM-powered user interactions
- MetadataInferenceEngine: Intelligent metadata inference
"""

import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from agentic_neurodata_conversion.models import (
    ConversationPhase,
    ConversionStatus,
    GlobalState,
    LogLevel,
    MCPMessage,
    MCPResponse,
    ValidationOutcome,
)

if TYPE_CHECKING:
    from agentic_neurodata_conversion.agents.conversation import (
        MetadataCollector,
        MetadataParser,
        ProvenanceTracker,
    )
    from agentic_neurodata_conversion.agents.metadata.inference import MetadataInferenceEngine
    from agentic_neurodata_conversion.agents.utils.conversational_handler import ConversationalHandler
    from agentic_neurodata_conversion.models.workflow_state_manager import WorkflowStateManager
    from agentic_neurodata_conversion.services import LLMService, MCPServer

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """Orchestrates the complete conversion workflow from start to finish.

    This class manages the entire conversion lifecycle:
    - Format detection and validation
    - Intelligent metadata inference from files
    - User metadata collection (required fields)
    - Custom metadata handling
    - Metadata review and confirmation
    - Conversion execution via ConversionAgent
    - Validation via EvaluationAgent
    - Retry and improvement workflows
    - Error handling and user guidance

    The workflow follows these main phases:
    1. Format Detection
    2. Metadata Inference (optional, if LLM available)
    3. Required Metadata Collection
    4. Custom Metadata Collection (optional)
    5. Metadata Review
    6. Conversion Execution
    7. Validation
    8. Results or Retry/Improvement

    Features:
    - LLM-powered proactive issue detection
    - Intelligent error explanations
    - Dynamic metadata requests based on file analysis
    - Graceful degradation when LLM unavailable
    - Comprehensive provenance tracking
    """

    def __init__(
        self,
        mcp_server: "MCPServer",
        metadata_collector: "MetadataCollector",
        metadata_parser: "MetadataParser",
        provenance_tracker: "ProvenanceTracker",
        workflow_manager: "WorkflowStateManager",
        conversational_handler: Optional["ConversationalHandler"] = None,
        metadata_inference_engine: Optional["MetadataInferenceEngine"] = None,
        llm_service: Optional["LLMService"] = None,
    ):
        """Initialize workflow orchestrator.

        Args:
            mcp_server: MCP server for agent communication
            metadata_collector: Metadata collection and validation
            metadata_parser: Metadata parsing utilities
            provenance_tracker: Provenance tracking
            workflow_manager: Workflow state management
            conversational_handler: Optional conversational AI handler
            metadata_inference_engine: Optional metadata inference engine
            llm_service: Optional LLM service for intelligent features
        """
        self._mcp_server = mcp_server
        self._metadata_collector = metadata_collector
        self._metadata_parser = metadata_parser
        self._provenance_tracker = provenance_tracker
        self._workflow_manager = workflow_manager
        self._conversational_handler = conversational_handler
        self._metadata_inference_engine = metadata_inference_engine
        self._llm_service = llm_service

        logger.info("WorkflowOrchestrator initialized")

    async def handle_start_conversion(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """Start the conversion workflow.

        This is the main entry point for the conversion workflow. It orchestrates
        all phases from format detection through final validation.

        Workflow steps:
        1. Validate input and extract parameters
        2. Run format detection via ConversionAgent
        3. Run intelligent metadata inference (if available)
        4. Check for required DANDI metadata
        5. Request missing metadata from user (if needed)
        6. Run proactive issue detection (if enabled)
        7. Handle custom metadata collection
        8. Show metadata review
        9. Execute conversion and validation

        Args:
            message: MCP message with context containing conversion parameters
            state: Global state

        Returns:
            MCPResponse indicating workflow started or awaiting user input
        """
        input_path = message.context.get("input_path")
        metadata = message.context.get("metadata", {})

        if not input_path:
            state.add_log(
                LogLevel.ERROR,
                "Missing input_path in start_conversion request",
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="MISSING_INPUT_PATH",
                error_message="input_path is required",
            )

        state.input_path = input_path
        state.metadata = metadata

        state.add_log(
            LogLevel.INFO,
            "Starting conversion workflow",
            {"input_path": input_path},
        )

        # Step 1: Detect format
        detect_msg = MCPMessage(
            target_agent="conversion",
            action="detect_format",
            context={"input_path": input_path},
            reply_to=message.message_id,
        )

        detect_response = await self._mcp_server.send_message(detect_msg)

        if not detect_response.success:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="DETECTION_FAILED",
                error_message="Format detection failed",
                error_context=detect_response.error,
            )

        detected_format = detect_response.result.get("format")
        confidence = detect_response.result.get("confidence")

        # BUG FIX: Store detected format in BOTH metadata and auto_extracted_metadata
        # It must be in auto_extracted_metadata because metadata gets reconstructed
        # from auto_extracted_metadata + user_provided_metadata later
        if detected_format:
            state.metadata["format"] = detected_format
            state.auto_extracted_metadata["format"] = detected_format

        # Handle ambiguous format detection
        if confidence == "ambiguous" or not detected_format:
            await state.update_status(ConversionStatus.AWAITING_USER_INPUT)
            state.add_log(
                LogLevel.INFO,
                "Format detection ambiguous - awaiting user input",
                {"supported_formats": detect_response.result.get("supported_formats", [])},
            )
            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "status": "awaiting_format_selection",
                    "supported_formats": detect_response.result.get("supported_formats", []),
                    "message": "Please select the data format",
                },
            )

        # Step 1.5: Intelligent Metadata Inference from File
        # Try to automatically infer metadata to reduce user burden
        if self._metadata_inference_engine:
            state.add_log(
                LogLevel.INFO,
                "Running intelligent metadata inference from file",
            )

            try:
                inference_result = await self._metadata_inference_engine.infer_metadata(
                    input_path=input_path,
                    state=state,
                )

                inferred_metadata = inference_result.get("inferred_metadata", {})
                confidence_scores = inference_result.get("confidence_scores", {})

                # Pre-fill metadata with high-confidence inferences (>= 80% confidence)
                high_confidence_inferences = {
                    key: value for key, value in inferred_metadata.items() if confidence_scores.get(key, 0) >= 80
                }

                if high_confidence_inferences:
                    # CRITICAL: Store auto-extracted metadata SEPARATELY from user-provided
                    # This allows us to track provenance and avoid asking users for auto-detectable info
                    state.auto_extracted_metadata.update(high_confidence_inferences)

                    state.add_log(
                        LogLevel.INFO,
                        "Auto-extracted metadata from file analysis (stored separately)",
                        {
                            "auto_extracted_fields": list(high_confidence_inferences.keys()),
                            "confidence_scores": {k: confidence_scores.get(k, 0) for k in high_confidence_inferences},
                            "suggestions": inference_result.get("suggestions", []),
                        },
                    )

                    # PROVENANCE TRACKING: Track auto-extracted metadata from file analysis
                    for field_name, value in high_confidence_inferences.items():
                        confidence_score = confidence_scores.get(field_name, 80.0)
                        self._provenance_tracker.track_metadata_provenance(
                            state=state,
                            field_name=field_name,
                            value=value,
                            provenance_type="auto-extracted",
                            confidence=confidence_score,
                            source=f"Automatically extracted from file analysis of {Path(input_path).name}",
                            needs_review=confidence_score < 95,  # High confidence extractions don't need review
                            raw_input=f"File: {Path(input_path).name}",
                        )

                    # Update combined metadata
                    state.metadata.update(metadata)

                    # Store full inference result separately (not in metadata that goes to NWB)
                    # This is internal diagnostic info, not part of the NWB schema
                    state.inference_result = inference_result

            except Exception as e:
                state.add_log(
                    LogLevel.WARNING,
                    f"Metadata inference failed (non-critical): {e}",
                )
                # Continue without inference - not critical

        # Step 1.6: Check for DANDI-required metadata BEFORE conversion
        # This prevents the bug where we convert first, then ask for metadata after
        #
        # USER REQUIREMENT: Ask for ALL 7 essential DANDI fields
        # Users can skip any fields they don't want to provide
        # This ensures comprehensive metadata collection while respecting user choice
        if self._conversational_handler:
            # Check for ALL 8 REQUIRED NWB/DANDI fields per nwb_dandi_schema.py
            # These are REQUIRED for NWB compliance (not just recommended)
            required_fields = {
                # Session-level metadata (REQUIRED by NWB spec)
                "experimenter": metadata.get("experimenter"),
                "institution": metadata.get("institution"),
                "experiment_description": metadata.get("experiment_description"),
                "session_description": metadata.get("session_description"),
                "session_start_time": metadata.get("session_start_time"),
                # Subject-level metadata (REQUIRED by NWB spec)
                "subject_id": metadata.get("subject_id"),
                "species": metadata.get("species"),
                "sex": metadata.get("sex"),
            }

            # Filter out fields the user already declined OR already provided/asked
            # This prevents re-asking for the same fields in a loop
            # Track which fields we've already asked about in this session
            if not hasattr(state, "already_asked_fields"):
                state.already_asked_fields = set()

            # CRITICAL FIX: Check BOTH state.metadata AND user_provided_metadata for field presence
            # After user provides metadata, it's stored in user_provided_metadata before being merged
            # We should NOT re-ask for fields that exist in EITHER location
            missing_fields = []
            for field, value in required_fields.items():
                # Skip if field has value in metadata
                if value:
                    continue
                # Skip if field is in user_provided_metadata (just provided but not yet merged)
                if field in state.user_provided_metadata and state.user_provided_metadata[field]:
                    continue
                # Skip if user declined this field
                if field in state.user_declined_fields:
                    continue
                # Skip if we already asked for this field
                if field in state.already_asked_fields:
                    continue
                # This field is truly missing - add to list
                missing_fields.append(field)

            # WORKFLOW_CONDITION_FLAGS_ANALYSIS.md Fix: Use centralized WorkflowStateManager
            # Replaces complex 4-condition check with single source of truth
            state.add_log(
                LogLevel.DEBUG,
                "Metadata check conditions",
                {
                    "missing_fields": missing_fields,
                    "metadata_policy": state.metadata_policy.value,
                    "conversation_phase": state.conversation_phase.value,
                    "status": state.status.value,
                    "conversation_history_length": len(state.conversation_history),
                },
            )

            if self._workflow_manager.should_request_metadata(state):
                await state.update_status(ConversionStatus.AWAITING_USER_INPUT)
                # Use new enums instead of strings
                state.conversation_phase = ConversationPhase.METADATA_COLLECTION
                state.conversation_type = state.conversation_phase.value  # Backward compatibility
                # Update metadata policy using WorkflowStateManager
                self._workflow_manager.update_metadata_policy_after_request(state)
                state.add_log(
                    LogLevel.INFO,
                    f"Missing DANDI-required metadata ({', '.join(missing_fields)}) - requesting from user before conversion",
                    {"missing_fields": missing_fields, "metadata_policy": state.metadata_policy.value},
                )

                # Generate DYNAMIC, file-specific message asking for required metadata
                message_text = await self._generate_dynamic_metadata_request(
                    missing_fields=missing_fields,
                    inference_result=getattr(state, "inference_result", {}),
                    file_info={
                        "name": Path(input_path).name,
                        "format": detected_format,
                        "size_mb": Path(input_path).stat().st_size / (1024 * 1024) if Path(input_path).exists() else 0,
                    },
                    state=state,
                )

                # INFINITE LOOP FIX: Add this assistant message to conversation history
                # This is critical - without this, the conversation history check at line 148 will always fail
                state.add_conversation_message(role="assistant", content=message_text)

                # INCREMENTAL METADATA FIX: Mark these fields as already asked
                # This prevents re-asking for the same fields when user confirms partial metadata
                state.already_asked_fields.update(missing_fields)
                state.add_log(
                    LogLevel.DEBUG,
                    f"Marked {len(missing_fields)} fields as already asked to prevent re-asking",
                    {"already_asked_fields": list(state.already_asked_fields)},
                )

                # Store input_path for later use when resuming conversion after skip
                state.pending_conversion_input_path = input_path
                state.add_log(
                    LogLevel.DEBUG,
                    "Stored pending_conversion_input_path for metadata conversation",
                    {"input_path": input_path},
                )

                # BUG FIX: Set llm_message so the frontend can display it via /api/status
                state.llm_message = message_text

                return MCPResponse.success_response(
                    reply_to=message.message_id,
                    result={
                        "status": "awaiting_user_input",
                        "conversation_type": "required_metadata",
                        "message": message_text,
                        "needs_user_input": True,
                        "required_fields": missing_fields,
                        "can_skip": False,  # These are critical for DANDI
                        "phase": "pre_conversion",
                    },
                )

        # Step 1.7: Proactive Issue Detection (OPTIONAL - can be disabled)
        # Analyze file BEFORE conversion to predict potential issues
        # This feature can have false positives, so allow users to proceed anyway
        enable_proactive_detection = metadata.get("enable_proactive_detection", False)  # Disabled by default

        if self._llm_service and enable_proactive_detection:
            state.add_log(LogLevel.INFO, "Running proactive issue analysis...")

            prediction = await self._proactive_issue_detection(
                input_path=input_path,
                format_name=detected_format,
                state=state,
            )

            # If high risk or low success probability, warn user BUT allow proceeding
            if prediction["risk_level"] == "high" or prediction.get("success_probability", 100) < 70:
                # Log the warning but don't block conversion
                state.add_log(
                    LogLevel.WARNING,
                    "Proactive analysis detected risks (can proceed anyway)",
                    {
                        "risk_level": prediction["risk_level"],
                        "success_probability": prediction.get("success_probability"),
                    },
                )
                # Store warning in metadata for user to see, but continue conversion
                state.metadata["proactive_warning"] = {
                    "risk_level": prediction["risk_level"],
                    "success_probability": prediction.get("success_probability"),
                    "message": prediction.get("warning_message"),
                    "predicted_issues": prediction.get("predicted_issues", []),
                }

        # Step 2: ONLY ask about custom metadata AFTER standard metadata is complete
        # Check if all standard NWB metadata has been collected
        is_standard_complete, missing = self._metadata_collector.validate_required_nwb_metadata(state.metadata)

        # Only proceed to custom metadata if:
        # 1. Standard metadata is complete OR user has explicitly declined all missing fields
        # 2. We haven't already asked about custom metadata
        # 3. We're not in the middle of collecting standard metadata
        # 4. We're not in ASK_ALL policy (piece by piece mode)

        # Check if user has declined ALL missing fields
        all_missing_declined = all(field in state.user_declined_fields for field in missing) if missing else False

        should_ask_custom = (
            (is_standard_complete or all_missing_declined)  # Standard complete OR all declined
            and not state.metadata.get("_custom_metadata_prompted", False)  # Haven't asked yet
            and state.conversation_phase != ConversationPhase.METADATA_COLLECTION  # Not collecting standard
            and not state.user_wants_sequential  # Not in sequential questioning mode
        )

        if should_ask_custom:
            state.metadata["_custom_metadata_prompted"] = True
            state.conversation_type = "custom_metadata_collection"
            await state.update_status(ConversionStatus.AWAITING_USER_INPUT)

            # Generate friendly message about custom metadata
            custom_metadata_prompt = await self._metadata_collector.generate_custom_metadata_prompt(
                detected_format, metadata, state
            )

            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "status": "need_user_input",
                    "message": custom_metadata_prompt,
                    "conversation_type": "custom_metadata_collection",
                },
            )

        # Step 3: Show metadata review before conversion
        # Give user one last chance to add/modify metadata
        if not state.metadata.get("_metadata_review_shown", False):
            state.metadata["_metadata_review_shown"] = True
            state.conversation_type = "metadata_review"
            await state.update_status(ConversionStatus.AWAITING_USER_INPUT)

            # Generate metadata review message
            review_message = await self._metadata_collector.generate_metadata_review_message(
                metadata, detected_format, state
            )

            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "status": "metadata_review",
                    "message": review_message,
                    "conversation_type": "metadata_review",
                    "metadata": metadata,
                },
            )

        # Step 4: Run conversion (after metadata review)
        return await self._run_conversion(
            message.message_id,
            input_path,
            detected_format,
            metadata,
            state,
        )

    async def _generate_dynamic_metadata_request(
        self,
        missing_fields: list[str],
        inference_result: dict[str, Any],
        file_info: dict[str, Any],
        state: GlobalState,
    ) -> str:
        """Generate dynamic, file-specific metadata request using LLM.

        This creates personalized messages based on:
        - What file format was detected
        - What metadata was auto-inferred
        - What specific fields are missing
        - File characteristics (size, name, etc.)

        Args:
            missing_fields: List of missing metadata fields
            inference_result: Results from metadata inference engine
            file_info: File information (name, format, size)
            state: Global state

        Returns:
            Dynamic, context-aware metadata request message
        """
        # Fallback if no LLM
        if not self._llm_service:
            return self._metadata_collector._generate_fallback_missing_metadata_message(missing_fields)

        # Build context-rich prompt
        inferred_metadata = inference_result.get("inferred_metadata", {})
        suggestions = inference_result.get("suggestions", [])

        system_prompt = """You are a helpful AI assistant for neuroscience data conversion.
Generate a friendly, specific request for missing metadata fields.

Be:
- Specific to the file format and data type
- Encouraging and helpful
- Clear about what's needed and why
- Aware of what was auto-detected to avoid redundancy"""

        user_prompt = f"""Generate a metadata request message for the user.

File Information:
- Name: {file_info.get("name")}
- Format: {file_info.get("format")}
- Size: {file_info.get("size_mb", 0):.1f} MB

Auto-detected metadata:
{inferred_metadata}

Suggestions from analysis:
{suggestions}

Missing required fields:
{missing_fields}

Create a friendly message asking for these specific fields. Explain why they're needed for NWB/DANDI compliance."""

        try:
            output_schema = {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Friendly metadata request message",
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
                "Generated dynamic metadata request with LLM",
                {"missing_fields": missing_fields},
            )

            return str(response.get("message", ""))

        except Exception as e:
            state.add_log(
                LogLevel.WARNING,
                f"Failed to generate dynamic metadata request: {e}",
            )
            # Fallback to standard message
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

    async def _run_conversion(
        self,
        original_message_id: str,
        input_path: str,
        format_name: str,
        metadata: dict[str, Any],
        state: GlobalState,
    ) -> MCPResponse:
        """Run the conversion and validation steps.

        This method orchestrates:
        1. Metadata validation (non-blocking warnings)
        2. Auto-fill optional fields from inference
        3. Conversion via ConversionAgent
        4. Validation via EvaluationAgent
        5. Handle three outcomes: PASSED, PASSED_WITH_ISSUES, FAILED

        Args:
            original_message_id: Original message ID for reply
            input_path: Path to input data
            format_name: Data format name
            metadata: Metadata dictionary
            state: Global state

        Returns:
            MCPResponse with conversion and validation results
        """
        # ENHANCED: Make validation non-blocking - warn but proceed
        # Users can choose to continue with whatever metadata they have
        is_valid, missing_fields = self._metadata_collector.validate_required_nwb_metadata(metadata)

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
                    self._provenance_tracker.track_metadata_provenance(
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

    async def continue_conversion_workflow(
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
        is_standard_complete, missing = self._metadata_collector.validate_required_nwb_metadata(metadata)

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

            custom_metadata_prompt = await self._metadata_collector.generate_custom_metadata_prompt(
                detected_format, metadata, state
            )

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

            review_message = await self._metadata_collector.generate_metadata_review_message(
                metadata, detected_format, state
            )

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
