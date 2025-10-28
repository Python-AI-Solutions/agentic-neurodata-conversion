"""
Conversation Agent implementation.

Responsible for:
- All user interactions
- Orchestrating conversion workflows
- Managing retry logic
- Gathering user input
"""
import json
from typing import Any, Dict, List, Optional

from models import (
    ConversionStatus,
    GlobalState,
    LogLevel,
    MCPMessage,
    MCPResponse,
    ValidationStatus,
    ValidationOutcome,
    ConversationPhase,
    MetadataRequestPolicy,
)
from models.workflow_state_manager import WorkflowStateManager
from services import LLMService, MCPServer
from agents.conversational_handler import ConversationalHandler
from agents.metadata_inference import MetadataInferenceEngine
from agents.adaptive_retry import AdaptiveRetryStrategy
from agents.error_recovery import IntelligentErrorRecovery
from agents.predictive_metadata import PredictiveMetadataSystem
from agents.intelligent_metadata_mapper import IntelligentMetadataMapper
from agents.smart_autocorrect import SmartAutoCorrectionSystem
from agents.nwb_dandi_schema import NWBDANDISchema


class ConversationAgent:
    """
    Conversation agent for user interaction and workflow orchestration.

    This agent coordinates the conversion workflow by sending messages
    to other agents through the MCP server.
    """

    def __init__(
        self,
        mcp_server: MCPServer,
        llm_service: Optional[LLMService] = None,
    ):
        """
        Initialize the conversation agent.

        Args:
            mcp_server: MCP server for agent communication
            llm_service: Optional LLM service for enhanced interactions
        """
        self._mcp_server = mcp_server
        self._llm_service = llm_service
        self._conversational_handler = (
            ConversationalHandler(llm_service) if llm_service else None
        )
        self._metadata_inference_engine = (
            MetadataInferenceEngine(llm_service) if llm_service else None
        )
        self._adaptive_retry_strategy = (
            AdaptiveRetryStrategy(llm_service) if llm_service else None
        )
        self._error_recovery = (
            IntelligentErrorRecovery(llm_service) if llm_service else None
        )
        self._predictive_metadata = (
            PredictiveMetadataSystem(llm_service) if llm_service else None
        )
        self._smart_autocorrect = (
            SmartAutoCorrectionSystem(llm_service) if llm_service else None
        )
        self._metadata_mapper = (
            IntelligentMetadataMapper(llm_service) if llm_service else None
        )
        self._workflow_manager = WorkflowStateManager()
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
        raw_input: Optional[str] = None,
    ) -> None:
        """
        Track provenance for a metadata field.

        This is a central method for recording the source, confidence, and origin
        of every metadata field for scientific transparency and DANDI compliance.

        Args:
            state: Global state
            field_name: Metadata field name
            value: The metadata value
            provenance_type: Type of provenance (user-specified, ai-parsed, etc.)
            confidence: Confidence score (0-100)
            source: Human-readable description of source
            needs_review: Whether this field needs user review
            raw_input: Original input that led to this value
        """
        from models import ProvenanceInfo, MetadataProvenance
        from datetime import datetime

        # Create provenance info
        provenance_info = ProvenanceInfo(
            value=value,
            provenance=MetadataProvenance(provenance_type),
            confidence=confidence,
            source=source,
            timestamp=datetime.now(),
            needs_review=needs_review,
            raw_input=raw_input,
        )

        # Store in state
        state.metadata_provenance[field_name] = provenance_info

        state.add_log(
            LogLevel.DEBUG,
            f"Tracked provenance for {field_name}: {provenance_type} (confidence: {confidence}%)",
            {
                "field": field_name,
                "provenance": provenance_type,
                "confidence": confidence,
                "needs_review": needs_review,
            },
        )

    def _track_user_provided_metadata(
        self,
        state: GlobalState,
        field_name: str,
        value: Any,
        confidence: float = 100.0,
        source: str = "User explicitly provided",
        raw_input: Optional[str] = None,
    ) -> None:
        """
        Track provenance for user-provided metadata.

        Args:
            state: Global state
            field_name: Metadata field name
            value: The metadata value
            confidence: Confidence score (default 100% for explicit user input)
            source: Description of how user provided it
            raw_input: Original user input
        """
        self._track_metadata_provenance(
            state=state,
            field_name=field_name,
            value=value,
            provenance_type="user-specified",
            confidence=confidence,
            source=source,
            needs_review=False,
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
        """
        Track provenance for AI-parsed metadata from natural language.

        Args:
            state: Global state
            field_name: Metadata field name
            value: The parsed value
            confidence: Confidence score from parser
            raw_input: Original natural language input
            reasoning: LLM's reasoning for the parsing
        """
        needs_review = confidence < 70  # Low confidence needs review

        source = f"AI parsed from: '{raw_input[:100]}'"
        if reasoning:
            source += f" | Reasoning: {reasoning[:100]}"

        self._track_metadata_provenance(
            state=state,
            field_name=field_name,
            value=value,
            provenance_type="ai-parsed",
            confidence=confidence,
            source=source,
            needs_review=needs_review,
            raw_input=raw_input,
        )

    def _track_auto_corrected_metadata(
        self,
        state: GlobalState,
        field_name: str,
        value: Any,
        source: str,
    ) -> None:
        """
        Track provenance for auto-corrected metadata during error correction.

        Args:
            state: Global state
            field_name: Metadata field name
            value: The corrected value
            source: Description of the correction
        """
        self._track_metadata_provenance(
            state=state,
            field_name=field_name,
            value=value,
            provenance_type="auto-corrected",
            confidence=70.0,  # Medium confidence for auto-corrections
            source=source,
            needs_review=True,  # Always recommend review for auto-corrections
            raw_input=None,
        )

    async def _generate_dynamic_metadata_request(
        self,
        missing_fields: List[str],
        inference_result: Dict[str, Any],
        file_info: Dict[str, Any],
        state: GlobalState,
    ) -> str:
        """
        Generate dynamic, file-specific metadata request using LLM.

        Instead of a fixed template, this creates personalized questions that:
        1. Acknowledge what was learned from file analysis
        2. Show file-specific context
        3. Only ask for what's actually missing
        4. Provide relevant examples based on the file type

        Args:
            missing_fields: List of required fields that are missing
            inference_result: Results from metadata inference engine
            file_info: Basic file information (name, format, size)
            state: Global state

        Returns:
            Customized message asking for missing metadata
        """
        if not self._llm_service:
            # Fallback to basic template if no LLM
            return f"""📋 **DANDI Metadata Collection**

To create a comprehensive NWB file for the DANDI archive, I'd like to collect the following metadata:
{chr(10).join(f"• **{field.replace('_', ' ').title()}**" for field in missing_fields)}

**All fields are optional!** You can:
- Provide any/all fields you have
- Skip individual fields: "skip experimenter"
- Skip all: "skip all" or "proceed with minimal metadata"

Please provide what you're comfortable sharing, or skip to proceed."""

        try:
            inferred_metadata = inference_result.get("inferred_metadata", {})
            confidence_scores = inference_result.get("confidence_scores", {})
            suggestions = inference_result.get("suggestions", [])

            # Build summary of what we successfully inferred
            inferred_summary = []
            for key, value in inferred_metadata.items():
                conf = confidence_scores.get(key, 0)
                if conf >= 70:  # Only mention high-confidence inferences
                    inferred_summary.append({
                        "field": key,
                        "value": str(value),
                        "confidence": conf
                    })

            # Check conversation history to adapt the message
            conversation_context = ""
            request_count = state.metadata_requests_count
            recent_user_messages = [msg for msg in state.conversation_history if msg.get('role') == 'user']

            if request_count > 0 and recent_user_messages:
                conversation_context = f"""
**Previous Conversation Context:**
This is NOT the first time asking. Previous request count: {request_count}
Recent user responses: {json.dumps([msg.get('content', '')[:100] for msg in recent_user_messages[-2:]], indent=2)}

IMPORTANT: Adapt your message to acknowledge their previous responses. Don't repeat the exact same format.
If they've already provided some information, acknowledge it specifically.
If this is a follow-up, be more concise and focused on ONLY what's still missing."""

            system_prompt = f"""You are a friendly, intelligent NWB conversion assistant.

Generate a personalized metadata request that:
1. Warmly acknowledges what was learned from analyzing the file
2. Shows you actually analyzed THIS specific file
3. Only asks for what's truly missing
4. Uses file-specific context in examples
5. Maintains an encouraging, conversational tone (like Claude.ai)
6. Makes the user feel their file is understood
7. ADAPTS based on conversation history - don't repeat yourself!

Be specific, contextual, and helpful - not generic.
{f"CRITICAL: This is request #{request_count + 1}. Vary your approach and be more concise." if request_count > 0 else ""}"""

            user_prompt = f"""Generate a metadata request message for this specific file.

**File Information:**
- Name: {file_info.get('name', 'unknown')}
- Format: {file_info.get('format', 'unknown')}
- Size: {file_info.get('size_mb', 0):.1f} MB

**What I Successfully Inferred from Analysis:**
{json.dumps(inferred_summary, indent=2) if inferred_summary else "Limited automatic inference"}

**What I Still Need to Ask User:**
{json.dumps(missing_fields, indent=2)}

{conversation_context}

**Create a friendly, file-specific message that:**
1. Starts by acknowledging the file analysis ("I've analyzed your [format] file...")
2. Mentions 2-3 specific things you discovered (probe type, format, possible species, etc.)
3. Explains you'd like to collect comprehensive DANDI metadata for better discoverability
4. Asks for the missing fields with clear explanations
5. Provides file-relevant examples (e.g., if it's a mouse recording, use mouse examples)
6. CLEARLY states that ALL fields are optional - users can skip individual fields or skip all
7. Makes it easy to skip: "You can skip any field by typing 'skip [field]' or 'skip all'"
{"8. BE CONCISE - this is a follow-up, not the first request!" if request_count > 0 else ""}

Keep it warm, conversational, and emphasize that skipping is totally fine.
{"VARY YOUR WORDING - don't use the exact same phrasing as before!" if request_count > 0 else ""}"""

            output_schema = {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The personalized metadata request message (2-4 paragraphs max)"
                    },
                    "context_highlights": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key file details mentioned in the message"
                    }
                },
                "required": ["message"]
            }

            response = await self._llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            state.add_log(
                LogLevel.INFO,
                "Generated dynamic metadata request based on file analysis",
                {
                    "inferred_fields_count": len(inferred_summary),
                    "missing_fields_count": len(missing_fields),
                    "context_highlights": response.get("context_highlights", [])
                }
            )

            return response.get("message", "")

        except Exception as e:
            state.add_log(
                LogLevel.WARNING,
                f"Failed to generate dynamic metadata request, using fallback: {e}",
            )
            # Fallback with some file context
            return f"""🔍 **File Analysis Complete**

I've analyzed your {file_info.get('format', 'unknown')} file: `{file_info.get('name', 'file')}`

To create a DANDI-compatible NWB file, I need:
{chr(10).join(f"• **{field.replace('_', ' ').title()}**" for field in missing_fields)}

Please provide these details, or say "skip for now" to proceed with minimal metadata."""

    async def handle_start_conversion(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """
        Start the conversion workflow.

        Args:
            message: MCP message with context containing conversion parameters
            state: Global state

        Returns:
            MCPResponse indicating workflow started
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
                    key: value
                    for key, value in inferred_metadata.items()
                    if confidence_scores.get(key, 0) >= 80
                }

                if high_confidence_inferences:
                    # CRITICAL: Store auto-extracted metadata SEPARATELY from user-provided
                    # This allows us to track provenance and avoid asking users for auto-detectable info
                    state.auto_extracted_metadata.update(high_confidence_inferences)

                    # Merge: auto-extracted + user-provided (user takes priority)
                    for key, value in high_confidence_inferences.items():
                        if not metadata.get(key):  # Only fill if not already provided by user
                            metadata[key] = value

                    state.add_log(
                        LogLevel.INFO,
                        "Auto-extracted metadata from file analysis (stored separately)",
                        {
                            "auto_extracted_fields": list(high_confidence_inferences.keys()),
                            "confidence_scores": {k: confidence_scores.get(k, 0) for k in high_confidence_inferences.keys()},
                            "suggestions": inference_result.get("suggestions", []),
                        }
                    )

                    # PROVENANCE TRACKING: Track auto-extracted metadata from file analysis
                    from pathlib import Path
                    for field_name, value in high_confidence_inferences.items():
                        confidence = confidence_scores.get(field_name, 80.0)
                        self._track_metadata_provenance(
                            state=state,
                            field_name=field_name,
                            value=value,
                            provenance_type="auto-extracted",
                            confidence=confidence,
                            source=f"Automatically extracted from file analysis of {Path(input_path).name}",
                            needs_review=confidence < 95,  # High confidence extractions don't need review
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
            # Check for ALL 7 essential DANDI fields (session + subject metadata)
            # These are recommended for DANDI archive compatibility
            required_fields = {
                # Session-level metadata (critical for DANDI)
                "experimenter": metadata.get("experimenter"),
                "institution": metadata.get("institution"),
                "experiment_description": metadata.get("experiment_description") or metadata.get("session_description"),

                # Subject-level metadata (highly recommended for DANDI)
                "subject_id": metadata.get("subject_id"),
                "species": metadata.get("species"),
                "sex": metadata.get("sex"),
                "age": metadata.get("age"),
            }

            # Filter out fields the user already declined OR already provided/asked
            # This prevents re-asking for the same fields in a loop
            # Track which fields we've already asked about in this session
            if not hasattr(state, 'already_asked_fields'):
                state.already_asked_fields = set()

            missing_fields = [
                field for field, value in required_fields.items()
                if not value and field not in state.user_declined_fields and field not in state.already_asked_fields
            ]

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
                }
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
                from pathlib import Path
                message_text = await self._generate_dynamic_metadata_request(
                    missing_fields=missing_fields,
                    inference_result=getattr(state, 'inference_result', {}),
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
                    {"already_asked_fields": list(state.already_asked_fields)}
                )

                # Store input_path for later use when resuming conversion after skip
                state.pending_conversion_input_path = input_path
                state.add_log(
                    LogLevel.DEBUG,
                    "Stored pending_conversion_input_path for metadata conversation",
                    {"input_path": input_path}
                )

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

        # Step 1.6: Proactive Issue Detection (OPTIONAL - can be disabled)
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
                    f"Proactive analysis detected risks (can proceed anyway)",
                    {"risk_level": prediction["risk_level"], "success_probability": prediction.get("success_probability")},
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
        is_standard_complete, missing = self._validate_required_nwb_metadata(state.metadata)

        # Only proceed to custom metadata if:
        # 1. Standard metadata is complete OR user has explicitly declined all missing fields
        # 2. We haven't already asked about custom metadata
        # 3. We're not in the middle of collecting standard metadata
        # 4. We're not in ASK_ALL policy (piece by piece mode)

        # Check if user has declined ALL missing fields
        all_missing_declined = all(
            field in state.user_declined_fields
            for field in missing
        ) if missing else False

        should_ask_custom = (
            (is_standard_complete or all_missing_declined) and  # Standard complete OR all declined
            not state.metadata.get('_custom_metadata_prompted', False) and  # Haven't asked yet
            state.conversation_phase != ConversationPhase.METADATA_COLLECTION and  # Not collecting standard
            state.metadata_policy != MetadataRequestPolicy.ASK_ALL and  # Not in piece-by-piece mode
            not state.user_wants_sequential  # Not in sequential questioning mode
        )

        if should_ask_custom:
            state.metadata['_custom_metadata_prompted'] = True
            state.conversation_type = "custom_metadata_collection"

            # Generate friendly message about custom metadata
            custom_metadata_prompt = await self._generate_custom_metadata_prompt(
                detected_format,
                metadata,
                state
            )

            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "status": "need_user_input",
                    "message": custom_metadata_prompt,
                    "conversation_type": "custom_metadata_collection",
                },
            )

        # Step 3: Run conversion (after all metadata collection is complete)
        return await self._run_conversion(
            message.message_id,
            input_path,
            detected_format,
            metadata,
            state,
        )

    async def _explain_error_to_user(
        self,
        error: Dict[str, Any],
        context: Dict[str, Any],
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Use LLM to explain errors in user-friendly terms.

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
- Message: {error.get('message', 'Unknown error')}
- Code: {error.get('code', 'UNKNOWN')}
- Context: {error.get('context', {})}

Conversion Context:
- Format: {context.get('format', 'unknown')}
- Input file: {context.get('input_path', 'unknown')}
- What was happening: {context.get('operation', 'conversion')}

Provide:
1. Simple explanation of what went wrong (no technical jargon)
2. Likely cause (why this might have happened)
3. Specific actions the user can take
4. Whether this issue is fixable

Respond in JSON format."""

            output_schema = {
                "type": "object",
                "properties": {
                    "explanation": {
                        "type": "string",
                        "description": "Simple, clear explanation of what went wrong"
                    },
                    "likely_cause": {
                        "type": "string",
                        "description": "Why this error probably occurred"
                    },
                    "suggested_actions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific steps user can take to fix or work around the issue"
                    },
                    "is_recoverable": {
                        "type": "boolean",
                        "description": "Whether this error can be fixed by user action"
                    },
                    "help_url": {
                        "type": "string",
                        "description": "Optional URL to relevant documentation"
                    }
                },
                "required": ["explanation", "likely_cause", "suggested_actions", "is_recoverable"]
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

            return explanation

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
        missing_fields: List[str],
        metadata: Dict[str, Any],
        state: GlobalState,
    ) -> str:
        """
        Generate user-friendly message for missing required metadata using LLM.

        Args:
            missing_fields: List of missing required fields
            metadata: Current metadata (what we have)
            state: Global state

        Returns:
            User-friendly message explaining what's needed
        """
        system_prompt = """You are a helpful NWB conversion assistant.
Explain to users what metadata is missing and why it's needed, in a friendly, non-technical way."""

        user_prompt = f"""The user tried to convert their data to NWB format, but some required metadata is missing.

Missing fields: {missing_fields}
Current metadata provided: {list(metadata.keys())}

Generate a friendly, conversational message that:
1. Explains what specific information is missing
2. Why it's required by the NWB format
3. Gives a clear example of what to provide
4. Encourages them to provide it

Be warm, specific, and actionable. Keep it concise (2-3 sentences)."""

        try:
            response = await self._llm_service.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
            )
            return response
        except Exception:
            return self._generate_fallback_missing_metadata_message(missing_fields)

    def _generate_fallback_missing_metadata_message(
        self,
        missing_fields: List[str],
    ) -> str:
        """
        Generate basic message for missing metadata (fallback without LLM).

        Args:
            missing_fields: List of missing required fields

        Returns:
            Basic message explaining what's needed
        """
        field_descriptions = {
            "sex": "subject's sex (M/F/U)",
            "subject.sex": "subject's sex in subject metadata (M/F/U)",
            "session_start_time": "when the recording session started (ISO 8601 format)",
            "session_description": "brief description of this recording session",
        }

        explanations = []
        for field in missing_fields:
            desc = field_descriptions.get(field, field)
            explanations.append(f"- {desc}")

        return f"""Cannot start conversion - missing required NWB metadata:

{chr(10).join(explanations)}

Please provide this information before conversion can proceed. For example:
- sex: "M" (for male), "F" (for female), or "U" (for unknown)

You can provide this via the chat interface."""

    async def _proactive_issue_detection(
        self,
        input_path: str,
        format_name: str,
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Use LLM to analyze file BEFORE conversion and predict potential issues.

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
        import os

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
- Filename: {file_info['filename']}
- Size: {file_info['size_mb']} MB
- Format: {file_info['format']}
- Sibling files: {file_info['sibling_files']}
- Has metadata: {file_info['has_metadata_file']}

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

            return prediction

        except Exception as e:
            state.add_log(LogLevel.WARNING, f"Proactive analysis failed: {e}")
            return {"risk_level": "unknown", "should_proceed": True}

    async def _decide_next_action(
        self,
        current_state: str,
        context: Dict[str, Any],
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Use LLM to decide the next best action based on current state.

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

            return response

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
        context: Dict[str, Any],
        state: GlobalState,
    ) -> str:
        """
        Use LLM to generate contextual, engaging status messages.

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

            return response.get("message", fallback_messages.get(status, "Operation completed"))

        except Exception as e:
            state.add_log(
                LogLevel.WARNING,
                f"Failed to generate LLM status message: {e}",
            )
            return fallback_messages.get(status, "Operation completed")

    async def _generate_custom_metadata_prompt(
        self,
        format_name: str,
        metadata: Dict[str, Any],
        state: GlobalState
    ) -> str:
        """
        Generate a friendly prompt asking if user wants to add custom metadata.

        Args:
            format_name: Detected data format
            metadata: Already collected metadata
            state: Global state

        Returns:
            User-friendly prompt message
        """
        if not self._llm_service:
            # Fallback message without LLM
            return """## 🎯 Ready to Convert!

I have collected the standard NWB metadata. Before we start the conversion:

**Would you like to add any additional metadata?**

You can add ANY custom information that's important for your experiment, such as:
- Experimental protocols or procedures
- Equipment settings or parameters
- Drug treatments or concentrations
- Behavioral task details
- Analysis notes or parameters
- Custom identifiers or tags
- Anything else relevant to your data!

Just type your additional metadata in a natural way. For example:
- "The recording was done at room temperature (22°C) with a 30 kHz sampling rate"
- "We used optogenetic stimulation with blue light at 470nm, 5mW power"
- "stimulus_duration: 500ms, inter-trial interval: 2 seconds"

**Type your additional metadata, or say "no" to proceed with conversion.**
"""

        try:
            # Use LLM to generate personalized prompt
            system_prompt = "You are helping collect custom metadata for neuroscience data conversion."

            # Get suggestions for metadata based on file type
            suggestions = []
            if self._metadata_mapper:
                suggestions = await self._metadata_mapper.suggest_missing_metadata(
                    metadata, format_name
                )

            user_prompt = f"""Generate a friendly message asking if the user wants to add custom metadata.

Format detected: {format_name}
Already collected: {', '.join(metadata.keys())}

Suggest relevant metadata they might want to add based on the file format.
Be encouraging about adding custom fields - anything they think is important.
Make it clear they can add ANY metadata, not just standard fields.
End with clear instructions on how to provide it or skip."""

            output_schema = {
                "type": "object",
                "properties": {
                    "message": {"type": "string"}
                }
            }

            response = await self._llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt
            )

            return response.get("message", self._generate_custom_metadata_prompt.__doc__)

        except Exception as e:
            state.add_log(LogLevel.WARNING, f"Failed to generate custom prompt: {e}")
            return self._generate_custom_metadata_prompt.__doc__

    async def _handle_custom_metadata_response(
        self,
        user_input: str,
        state: GlobalState
    ) -> Dict[str, Any]:
        """
        Process user's custom metadata input using intelligent mapping.

        Args:
            user_input: User's natural language metadata
            state: Global state

        Returns:
            Parsed and mapped metadata
        """
        if not self._metadata_mapper:
            state.add_log(LogLevel.WARNING, "Metadata mapper not available")
            return {}

        try:
            # Parse custom metadata using LLM
            parsed_metadata = await self._metadata_mapper.parse_custom_metadata(
                user_input=user_input,
                existing_metadata=state.metadata,
                state=state
            )

            # Update state metadata with parsed fields
            if parsed_metadata.get('standard_fields'):
                state.metadata.update(parsed_metadata['standard_fields'])
                for field, value in parsed_metadata['standard_fields'].items():
                    self._track_ai_parsed_metadata(
                        state=state,
                        field_name=field,
                        value=value,
                        confidence=90,
                        raw_input=user_input,
                        reasoning="Parsed from custom metadata input"
                    )

            # Store custom fields separately for special handling
            if parsed_metadata.get('custom_fields'):
                if '_custom_fields' not in state.metadata:
                    state.metadata['_custom_fields'] = {}
                state.metadata['_custom_fields'].update(parsed_metadata['custom_fields'])

            # Store mapping report for display
            if parsed_metadata.get('mapping_report'):
                state.metadata['_mapping_report'] = parsed_metadata['mapping_report']

            state.add_log(
                LogLevel.INFO,
                "Processed custom metadata",
                {
                    "standard_fields_count": len(parsed_metadata.get('standard_fields', {})),
                    "custom_fields_count": len(parsed_metadata.get('custom_fields', {}))
                }
            )

            return parsed_metadata

        except Exception as e:
            state.add_log(LogLevel.ERROR, f"Failed to parse custom metadata: {e}")
            return {}

    async def _finalize_with_minimal_metadata(
        self,
        original_message_id: str,
        output_path: str,
        validation_result: Dict[str, Any],
        format_name: str,
        input_path: str,
        state: GlobalState,
    ) -> MCPResponse:
        """
        Complete conversion with minimal metadata and create informative report.

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
        metadata: Dict[str, Any],
    ) -> tuple[bool, List[str]]:
        """
        Validate that all required NWB metadata fields are present BEFORE conversion.

        This prevents conversion failures mid-process and provides early feedback.
        Uses the NWB/DANDI schema to dynamically validate all required fields.

        Args:
            metadata: Metadata dictionary to validate

        Returns:
            Tuple of (is_valid, list_of_missing_fields)
        """
        # Use schema-driven validation instead of hardcoded field lists
        is_valid, missing_fields = NWBDANDISchema.validate_metadata(metadata)

        return is_valid, missing_fields

    async def _run_conversion(
        self,
        original_message_id: str,
        input_path: str,
        format_name: str,
        metadata: Dict[str, Any],
        state: GlobalState,
    ) -> MCPResponse:
        """
        Run the conversion and validation steps.

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

        # BUG FIX #2: Validate required metadata BEFORE starting conversion
        # This prevents mid-conversion failures and provides early feedback
        is_valid, missing_fields = self._validate_required_nwb_metadata(metadata)

        if not is_valid:
            state.add_log(
                LogLevel.WARNING,
                f"Cannot proceed with conversion - missing required NWB metadata: {missing_fields}",
                {"missing_fields": missing_fields}
            )

            # Generate user-friendly explanation
            if self._llm_service:
                try:
                    explanation = await self._generate_missing_metadata_message(
                        missing_fields=missing_fields,
                        metadata=metadata,
                        state=state,
                    )
                except Exception:
                    explanation = self._generate_fallback_missing_metadata_message(missing_fields)
            else:
                explanation = self._generate_fallback_missing_metadata_message(missing_fields)

            await state.update_status(ConversionStatus.AWAITING_USER_INPUT)

            return MCPResponse.error_response(
                reply_to=original_message_id,
                error_code="MISSING_REQUIRED_METADATA",
                error_message=explanation,
                error_context={
                    "missing_fields": missing_fields,
                    "provided_metadata": list(metadata.keys()),
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
                    "file_size_mb": Path(output_path).stat().st_size / (1024 * 1024) if Path(output_path).exists() else 0,
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
                issue_parts.append(f"{best_practice_count} best practice suggestion{'s' if best_practice_count != 1 else ''}")
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
                        role="assistant",
                        content=llm_analysis.get("message", ""),
                        context=llm_analysis
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
                    "file_size_mb": Path(output_path).stat().st_size / (1024 * 1024) if Path(output_path).exists() else 0,
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
        """
        Handle user's manual format selection.

        Args:
            message: MCP message with selected format
            state: Global state

        Returns:
            MCPResponse with conversion workflow continuation
        """
        selected_format = message.context.get("format")

        if not selected_format:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="MISSING_FORMAT",
                error_message="format selection is required",
            )

        if state.status != ConversionStatus.AWAITING_USER_INPUT:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="INVALID_STATE",
                error_message=f"Cannot accept format selection in state: {state.status}",
            )

        state.add_log(
            LogLevel.INFO,
            f"User selected format: {selected_format}",
            {"format": selected_format},
        )

        # Continue with conversion
        return await self._run_conversion(
            message.message_id,
            state.input_path,
            selected_format,
            state.metadata,
            state,
        )

    async def handle_retry_decision(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """
        Handle user's retry approval/rejection.

        Args:
            message: MCP message with user decision
            state: Global state

        Returns:
            MCPResponse with next steps
        """
        decision = message.context.get("decision")

        if decision not in ["approve", "reject", "accept"]:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="INVALID_DECISION",
                error_message="decision must be 'approve', 'reject', or 'accept'",
            )

        if state.status != ConversionStatus.AWAITING_RETRY_APPROVAL:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="INVALID_STATE",
                error_message=f"Cannot accept retry decision in state: {state.status}",
            )

        # Bug #3 fix: Handle "accept" for PASSED_WITH_ISSUES
        if decision == "accept":
            # Only valid for PASSED_WITH_ISSUES (has warnings but no critical errors)
            # Use enum comparison
            try:
                status_enum = ValidationOutcome(state.overall_status) if isinstance(state.overall_status, str) else state.overall_status
            except (ValueError, AttributeError):
                status_enum = state.overall_status

            if status_enum != ValidationOutcome.PASSED_WITH_ISSUES:
                return MCPResponse.error_response(
                    reply_to=message.message_id,
                    error_code="INVALID_DECISION",
                    error_message="'accept' decision only valid for PASSED_WITH_ISSUES status",
                )

            # Set validation_status to passed_accepted (Story 8.3a line 840)
            state.validation_status = ValidationStatus.PASSED_ACCEPTED
            await state.update_status(ConversionStatus.COMPLETED)
            state.add_log(
                LogLevel.INFO,
                "User accepted file with warnings (validation_status=passed_accepted)",
            )

            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "status": "completed",
                    "validation_status": "passed_accepted",
                    "message": "File accepted with warnings. Download ready.",
                },
            )

        if decision == "reject":
            # Bug #7 fix: Set validation_status to failed_user_declined (Story 8.8 line 958)
            state.validation_status = ValidationStatus.FAILED_USER_DECLINED
            await state.update_status(ConversionStatus.FAILED)
            state.add_log(
                LogLevel.INFO,
                "User rejected retry (validation_status=failed_user_declined)",
            )
            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "status": "failed",
                    "validation_status": "failed_user_declined",
                    "message": "Conversion terminated by user",
                },
            )

        # User approved retry
        state.increment_retry()
        state.add_log(
            LogLevel.INFO,
            f"User approved retry (attempt {state.correction_attempt})",
        )

        # Get the most recent validation result from state
        # Note: In a production system, we'd store this more robustly
        validation_result_data = None
        for log in reversed(state.logs):
            if "validation" in log.context:
                validation_result_data = log.context.get("validation")
                break

        # Bug #11 fix: Detect "no progress" before starting retry (Story 4.7 lines 461-466)
        if validation_result_data:
            current_issues = validation_result_data.get("issues", [])

            # Check if we're making no progress
            if state.detect_no_progress(current_issues):
                state.add_log(
                    LogLevel.WARNING,
                    "No progress detected - same validation errors with no changes applied",
                    {
                        "correction_attempt": state.correction_attempt,
                        "issue_count": len(current_issues),
                    },
                )

                # Warn user and ask for confirmation
                warning_message = (
                    f"⚠️ No changes detected since last attempt (attempt #{state.correction_attempt}).\n\n"
                    f"The same {len(current_issues)} validation errors still exist because:\n"
                    f"- No user input was provided\n"
                    f"- No automatic corrections were applied\n\n"
                    f"Retrying with no changes will likely produce the same errors.\n\n"
                    f"**Recommended actions:**\n"
                    f"1. Provide additional information when prompted\n"
                    f"2. Check if the source data files have the required information\n"
                    f"3. Consider declining this retry if data cannot be corrected\n\n"
                    f"Would you still like to proceed with retry?"
                )

                # For now, log the warning and continue (actual UI confirmation can be added later)
                state.add_log(
                    LogLevel.WARNING,
                    "Proceeding with retry despite no progress warning",
                )

            # Store current issues for next iteration's comparison
            state.previous_validation_issues = current_issues

            # Reset the "changes made" flags for this new attempt
            state.user_provided_input_this_attempt = False
            state.auto_corrections_applied_this_attempt = False

        # Use adaptive retry strategy to determine best approach
        if self._adaptive_retry_strategy and validation_result_data:
            state.add_log(
                LogLevel.INFO,
                "Running adaptive retry analysis",
            )

            try:
                retry_recommendation = await self._adaptive_retry_strategy.analyze_and_recommend_strategy(
                    state=state,
                    current_validation_result=validation_result_data,
                )

                state.add_log(
                    LogLevel.INFO,
                    "Adaptive retry recommendation",
                    {
                        "should_retry": retry_recommendation.get("should_retry"),
                        "strategy": retry_recommendation.get("strategy"),
                        "approach": retry_recommendation.get("approach"),
                    }
                )

                # Check if we should ask user for help instead of retrying
                if retry_recommendation.get("ask_user"):
                    await state.update_status(ConversionStatus.AWAITING_USER_INPUT)

                    user_message = retry_recommendation.get("message", "We need your help to fix these issues.")

                    # Add specific questions if provided
                    questions = retry_recommendation.get("questions_for_user", [])
                    if questions:
                        user_message += "\n\n" + "\n".join(f"• {q}" for q in questions)

                    state.add_log(
                        LogLevel.INFO,
                        "Asking user for help based on adaptive retry analysis",
                    )

                    return MCPResponse.success_response(
                        reply_to=message.message_id,
                        result={
                            "status": "awaiting_user_input",
                            "message": user_message,
                            "needs_user_input": True,
                            "retry_recommendation": retry_recommendation,
                        },
                    )

                # If recommended not to retry, inform user
                if not retry_recommendation.get("should_retry"):
                    state.validation_status = ValidationStatus.FAILED_PERSISTENT
                    await state.update_status(ConversionStatus.FAILED)

                    state.add_log(
                        LogLevel.INFO,
                        "Adaptive retry recommends stopping attempts",
                    )

                    return MCPResponse.success_response(
                        reply_to=message.message_id,
                        result={
                            "status": "failed",
                            "validation_status": "failed_persistent",
                            "message": retry_recommendation.get("message"),
                            "retry_recommendation": retry_recommendation,
                        },
                    )

                # Store the recommended approach for use during retry
                state.metadata["_retry_approach"] = retry_recommendation.get("approach")
                state.metadata["_retry_reasoning"] = retry_recommendation.get("reasoning", "")

            except Exception as e:
                state.add_log(
                    LogLevel.WARNING,
                    f"Adaptive retry analysis failed (non-critical): {e}",
                )
                # Continue with normal retry if analysis fails

        # Analyze corrections with LLM if available
        if self._llm_service:
            await state.update_status(ConversionStatus.CONVERTING)
            state.add_log(
                LogLevel.INFO,
                "Analyzing validation issues with LLM for corrections",
            )

            if validation_result_data:
                # Send message to evaluation agent to analyze corrections
                analysis_response = await self._mcp_server.send_message(
                    MCPMessage(
                        target_agent="evaluation",
                        action="analyze_corrections",
                        context={
                            "validation_result": validation_result_data,
                            "input_metadata": state.metadata,
                            "conversion_parameters": {},
                        },
                    )
                )

                if analysis_response.success:
                    corrections = analysis_response.result.get("corrections", {})
                    state.add_log(
                        LogLevel.INFO,
                        "LLM correction analysis completed",
                        {
                            "analysis": corrections.get("analysis", ""),
                            "suggestions_count": len(corrections.get("suggestions", [])),
                            "recommended_action": corrections.get("recommended_action", ""),
                        },
                    )

                    # Extract automatic fixes from LLM suggestions
                    auto_fixes = self._extract_auto_fixes(corrections)

                    # Check if there are non-fixable issues requiring user input
                    user_input_required = self._identify_user_input_required(corrections)

                    if user_input_required:
                        # Some issues need user input - transition to AWAITING_USER_INPUT state
                        await state.update_status(ConversionStatus.AWAITING_USER_INPUT)
                        state.add_log(
                            LogLevel.INFO,
                            f"User input required for {len(user_input_required)} issues",
                            {"required_fields": user_input_required},
                        )
                        return MCPResponse.success_response(
                            reply_to=message.message_id,
                            result={
                                "status": "awaiting_user_input",
                                "required_fields": user_input_required,
                                "auto_fixes": auto_fixes,
                                "message": "Additional user input required to complete correction",
                            },
                        )

                    # Send corrections to conversion agent
                    # Bug #11 fix: Mark if auto-corrections are being applied
                    if auto_fixes:
                        state.auto_corrections_applied_this_attempt = True

                    correction_response = await self._mcp_server.send_message(
                        MCPMessage(
                            target_agent="conversion",
                            action="apply_corrections",
                            context={
                                "correction_context": corrections,
                                "auto_fixes": auto_fixes,
                                "user_input": {},
                            },
                        )
                    )

                    if correction_response.success:
                        state.add_log(
                            LogLevel.INFO,
                            "Corrections applied and reconversion successful",
                        )

                        # Re-run validation on corrected file
                        validation_response = await self._mcp_server.send_message(
                            MCPMessage(
                                target_agent="evaluation",
                                action="run_validation",
                                context={"nwb_path": state.output_path},
                            )
                        )

                        if validation_response.success:
                            # Generate report after validation
                            report_response = await self._mcp_server.send_message(
                                MCPMessage(
                                    target_agent="evaluation",
                                    action="generate_report",
                                    context={
                                        "validation_result": validation_response.result.get("validation_result"),
                                        "nwb_path": state.output_path,
                                    },
                                )
                            )

                            if report_response.success:
                                state.add_log(
                                    LogLevel.INFO,
                                    f"Report generated: {report_response.result.get('report_path')}",
                                )

                        return MCPResponse.success_response(
                            reply_to=message.message_id,
                            result={
                                "status": "reconversion_completed",
                                "output_path": state.output_path,
                                "attempt": state.correction_attempt,
                            },
                        )
                    else:
                        state.add_log(
                            LogLevel.ERROR,
                            f"Correction application failed: {correction_response.error.get('message', 'Unknown error')}",
                        )
                        return correction_response
                else:
                    state.add_log(
                        LogLevel.WARNING,
                        f"LLM analysis failed: {analysis_response.error.get('message', 'Unknown error')}",
                    )

            # If no LLM analysis, just restart without corrections
            # ✅ FIX: Use pending_conversion_input_path with fallback
            conversion_path = state.pending_conversion_input_path or state.input_path
            if not conversion_path or str(conversion_path) == "None":
                state.add_log(
                    LogLevel.ERROR,
                    "Cannot restart conversion - input_path not available",
                    {
                        "pending_conversion_input_path": str(state.pending_conversion_input_path) if state.pending_conversion_input_path else "None",
                        "input_path": str(state.input_path) if state.input_path else "None"
                    }
                )
                return MCPResponse.error_response(
                    reply_to=message.message_id,
                    error_code="INVALID_STATE",
                    error_message="Cannot proceed with retry. The file path is not available. Please try uploading the file again.",
                )

            restart_response = await self.handle_start_conversion(
                MCPMessage(
                    target_agent="conversation",
                    action="start_conversion",
                    context={
                        "input_path": str(conversion_path),
                        "metadata": state.metadata,
                    },
                ),
                state,
            )
            return restart_response
        else:
            # No LLM available - ask user for manual corrections
            await state.update_status(ConversionStatus.AWAITING_USER_INPUT)
            state.add_log(
                LogLevel.WARNING,
                "No LLM service available - cannot auto-analyze corrections",
            )
            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "status": "awaiting_corrections",
                    "message": "Please provide corrections manually (LLM not configured)",
                },
            )

    def _identify_user_input_required(self, corrections: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify issues that require user input to fix.

        Implements Story 8.6: User Input Request

        Args:
            corrections: LLM correction analysis

        Returns:
            List of required user input fields with metadata
        """
        required_fields = []
        suggestions = corrections.get("suggestions", [])

        for suggestion in suggestions:
            # Check if this issue requires user input (not actionable by system)
            if suggestion.get("actionable", False):
                # Skip actionable suggestions - they can be auto-fixed
                continue

            issue = suggestion.get("issue", "").lower()
            suggestion_text = suggestion.get("suggestion", "").lower()

            # Identify specific fields that need user input
            if "subject_id" in issue and ("missing" in issue or "empty" in issue):
                required_fields.append({
                    "field_name": "subject_id",
                    "label": "Subject ID",
                    "type": "text",
                    "required": True,
                    "help_text": "Unique identifier for the experimental subject",
                    "reason": suggestion.get("issue", ""),
                })

            elif "session_description" in issue and "too short" in suggestion_text:
                required_fields.append({
                    "field_name": "session_description",
                    "label": "Session Description",
                    "type": "textarea",
                    "required": True,
                    "help_text": "Detailed description of the experimental session (minimum 20 characters)",
                    "reason": suggestion.get("issue", ""),
                })

            elif "experimenter" in issue and ("missing" in issue or "empty" in issue):
                required_fields.append({
                    "field_name": "experimenter",
                    "label": "Experimenter Name(s)",
                    "type": "text",
                    "required": True,
                    "help_text": "Name(s) of experimenter(s) who conducted the session (comma-separated)",
                    "reason": suggestion.get("issue", ""),
                })

            elif "institution" in issue and "empty" not in suggestion_text:
                required_fields.append({
                    "field_name": "institution",
                    "label": "Institution",
                    "type": "text",
                    "required": False,
                    "help_text": "Institution where the experiment was conducted",
                    "reason": suggestion.get("issue", ""),
                })

        return required_fields

    def _extract_auto_fixes(self, corrections: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract automatically fixable corrections from LLM analysis.

        Implements Story 8.5: Automatic Issue Correction

        Args:
            corrections: LLM correction analysis

        Returns:
            Dictionary of auto-fixable metadata fields
        """
        auto_fixes = {}

        suggestions = corrections.get("suggestions", [])

        for suggestion in suggestions:
            if not suggestion.get("actionable", False):
                continue

            issue = suggestion.get("issue", "").lower()
            suggestion_text = suggestion.get("suggestion", "").lower()

            # Parse common fixable issues
            # Note: This is a simple heuristic-based approach
            # In production, would use more sophisticated NLP or structured LLM output

            # Empty/missing fields that can have defaults
            if "subject_id" in issue and "subject_id" in suggestion_text:
                if "unknown" not in suggestion_text:
                    # Extract suggested value (simple parsing)
                    continue  # Skip for now - needs user input

            # Species defaults
            if "species" in issue:
                if "mouse" in suggestion_text or "mus musculus" in suggestion_text:
                    auto_fixes["species"] = "Mus musculus"
                elif "rat" in suggestion_text or "rattus" in suggestion_text:
                    auto_fixes["species"] = "Rattus norvegicus"

            # Session description minimum length
            if "session_description" in issue and "too short" in suggestion_text:
                # Can't auto-fix - needs actual description
                pass

            # Experimenter format
            if "experimenter" in issue and "format" in suggestion_text:
                # Can't auto-fix without knowing actual name
                pass

            # Institution/lab empty values
            if ("institution" in issue or "lab" in issue) and "empty" in suggestion_text:
                if "remove" in suggestion_text:
                    # Mark for removal (set to None)
                    if "institution" in issue:
                        auto_fixes["institution"] = None
                    if "lab" in issue:
                        auto_fixes["lab"] = None

        return auto_fixes

    async def handle_conversational_response(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """
        Handle user's conversational response to LLM questions.

        This enables natural, flowing conversation where the LLM analyzes
        user responses and decides next steps dynamically.

        Args:
            message: MCP message with user's response
            state: Global state

        Returns:
            MCPResponse with next conversation turn or action
        """
        user_message = message.context.get("message", "")

        if not user_message:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="MISSING_MESSAGE",
                error_message="User message is required",
            )

        # Input validation: check message length
        if len(user_message) > 10000:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="MESSAGE_TOO_LONG",
                error_message="Message too long. Please keep your message under 10,000 characters.",
            )

        # Strip excessive whitespace
        user_message = user_message.strip()
        if not user_message:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="EMPTY_MESSAGE",
                error_message="Message cannot be empty or whitespace only.",
            )

        # Add user message to conversation history
        state.add_conversation_message(role="user", content=user_message)

        state.add_log(
            LogLevel.INFO,
            f"Processing conversational response from user",
            {"message_preview": user_message[:100]},
        )

        # Bug #8 fix: Check for explicit cancellation (Story 8.8 line 959)
        if user_message.lower() in ["cancel", "quit", "stop", "abort", "exit"]:
            state.validation_status = ValidationStatus.FAILED_USER_ABANDONED
            await state.update_status(ConversionStatus.FAILED)
            state.add_log(
                LogLevel.INFO,
                "User abandoned correction loop (validation_status=failed_user_abandoned)",
                {"message": user_message},
            )

            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "status": "failed",
                    "validation_status": "failed_user_abandoned",
                    "message": "Conversion cancelled by user",
                },
            )

        # Handle auto-fix approval conversation type
        if state.conversation_type == "auto_fix_approval":
            return await self._handle_auto_fix_approval_response(
                user_message,
                message.message_id,
                state
            )

        # Handle metadata review conversation type
        if state.conversation_type == "metadata_review":
            # Check if user wants to proceed or add more metadata
            if user_message.lower() in ["no", "proceed", "continue", "skip", "start"]:
                state.add_log(LogLevel.INFO, "User chose to proceed with current metadata")
                state.conversation_type = None  # Reset conversation type

                # Proceed with conversion
                if state.input_path:
                    return await self._run_conversion(
                        message.message_id,
                        str(state.input_path),
                        state.metadata.get("format", "unknown"),
                        state.metadata,
                        state,
                    )
                else:
                    return MCPResponse.error_response(
                        reply_to=message.message_id,
                        error_code="INVALID_STATE",
                        error_message="Cannot proceed with conversion. File path not found.",
                    )

            # Check if user expresses intent to add but hasn't provided data yet
            if self._user_expresses_intent_to_add_more(user_message):
                state.add_log(
                    LogLevel.INFO,
                    "User expressed intent to add metadata without providing concrete data"
                )
                return MCPResponse.success_response(
                    reply_to=message.message_id,
                    result={
                        "status": "awaiting_metadata_fields",
                        "message": (
                            "Great! What would you like to add? You can provide:\n\n"
                            "• **Specific fields:** 'age: P90D, description: Visual cortex recording'\n"
                            "• **Natural language:** 'The session lasted 2 hours in the morning'\n"
                            "• **Or say 'proceed'** to continue with current metadata"
                        ),
                        "conversation_type": "metadata_review",  # Stay in same state
                    },
                )

            # User wants to add more metadata - parse it
            # Try to extract metadata from the message
            additional_metadata = {}

            # Simple pattern matching for "field: value" format
            import re
            pattern = r'(\w+)\s*[:=]\s*(.+?)(?=\w+\s*[:=]|$)'
            matches = re.findall(pattern, user_message)
            for field, value in matches:
                field = field.lower().replace(' ', '_')
                additional_metadata[field] = value.strip()

            # If no pattern matches, try to parse with metadata mapper if available
            if not additional_metadata and self._metadata_mapper:
                parsed = await self._metadata_mapper.parse_custom_metadata(
                    user_input=user_message,
                    existing_metadata=state.metadata,
                    state=state
                )
                if parsed.get('standard_fields'):
                    additional_metadata.update(parsed['standard_fields'])
                if parsed.get('custom_fields'):
                    additional_metadata.update(parsed['custom_fields'])

            if additional_metadata:
                # Update metadata
                state.metadata.update(additional_metadata)

                # Track provenance - but don't overwrite if already set by parser
                for field, value in additional_metadata.items():
                    if field not in state.metadata_provenance:
                        self._track_user_provided_metadata(
                            state=state,
                            field_name=field,
                            value=value,
                            confidence=100.0,
                            source="Added during metadata review",
                            raw_input=user_message[:200]
                        )

                state.add_log(
                    LogLevel.INFO,
                    f"Added {len(additional_metadata)} fields during metadata review",
                    {"fields": list(additional_metadata.keys())}
                )

                confirmation = f"Added {len(additional_metadata)} metadata field(s). Starting conversion..."

                state.conversation_type = None  # Reset for conversion

                # Proceed with conversion with updated metadata
                if state.input_path:
                    return await self._run_conversion(
                        message.message_id,
                        str(state.input_path),
                        state.metadata.get("format", "unknown"),
                        state.metadata,
                        state,
                    )
                else:
                    return MCPResponse.error_response(
                        reply_to=message.message_id,
                        error_code="INVALID_STATE",
                        error_message="Cannot proceed with conversion. File path not found.",
                    )
            else:
                # No metadata detected - ask for clarification instead of converting
                state.add_log(
                    LogLevel.INFO,
                    "No metadata detected in user message - asking for clarification"
                )
                return MCPResponse.success_response(
                    reply_to=message.message_id,
                    result={
                        "status": "metadata_review",
                        "message": (
                            "I didn't detect any metadata fields in your message. "
                            "Please provide metadata in one of these formats:\n\n"
                            "• **Field format:** 'age: P90D'\n"
                            "• **Multiple fields:** 'age: P90D, description: Visual cortex recording'\n"
                            "• **Natural language:** 'The mouse was 3 months old'\n\n"
                            "Or say **'proceed'** to continue with your current metadata."
                        ),
                        "conversation_type": "metadata_review",  # Stay in state, don't convert
                    },
                )

        # Handle custom metadata collection conversation type
        if state.conversation_type == "custom_metadata_collection":
            # Check if user wants to skip custom metadata
            if user_message.lower() in ["no", "skip", "none", "proceed", "continue"]:
                state.add_log(LogLevel.INFO, "User declined to add custom metadata")
                state.conversation_type = None  # Reset conversation type

                # Proceed with conversion
                if state.input_path:
                    return await self.handle_start_conversion(
                        MCPMessage(
                            target_agent="conversation",
                            action="start_conversion",
                            context={
                                "input_path": str(state.input_path),
                                "metadata": state.metadata,
                            },
                        ),
                        state,
                    )
                else:
                    return MCPResponse.error_response(
                        reply_to=message.message_id,
                        error_code="INVALID_STATE",
                        error_message="Cannot proceed with conversion. File path not found.",
                    )

            # Process custom metadata
            parsed_metadata = await self._handle_custom_metadata_response(
                user_message,
                state
            )

            # Generate confirmation message
            if self._metadata_mapper and parsed_metadata.get('mapping_report'):
                confirmation = self._metadata_mapper.format_metadata_for_display(
                    state.metadata,
                    parsed_metadata.get('mapping_report', [])
                )
            else:
                confirmation = f"Added {len(parsed_metadata.get('standard_fields', {}))} standard fields and {len(parsed_metadata.get('custom_fields', {}))} custom fields."

            state.conversation_type = None  # Reset conversation type
            state.add_log(LogLevel.INFO, "Custom metadata collected, proceeding with conversion")

            # Proceed with conversion with updated metadata
            if state.input_path:
                return await self.handle_start_conversion(
                    MCPMessage(
                        target_agent="conversation",
                        action="start_conversion",
                        context={
                            "input_path": str(state.input_path),
                            "metadata": state.metadata,
                        },
                    ),
                    state,
                )
            else:
                return MCPResponse.error_response(
                    reply_to=message.message_id,
                    error_code="INVALID_STATE",
                    error_message="Cannot proceed with conversion. File path not found.",
                )

        if not self._conversational_handler:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="NO_LLM",
                error_message="LLM service not configured for conversational responses",
            )

        # CHECK IF USER IS DECLINING TO PROVIDE METADATA
        # Use LLM-based detection for better understanding of user intent
        conversation_context = "\n".join([
            f"{msg['role']}: {msg['content'][:100]}"
            for msg in state.conversation_history[-3:]  # Last 3 exchanges for context
        ]) if state.conversation_history else ""

        skip_type = await self._conversational_handler.detect_skip_type_with_llm(
            user_message,
            conversation_context
        )

        state.add_log(
            LogLevel.INFO,
            f"User intent detected: {skip_type}",
            {"user_message": user_message[:100], "skip_type": skip_type}
        )

        if skip_type == "global":
            # User wants to skip ALL remaining questions
            # Use WorkflowStateManager to update metadata policy
            self._workflow_manager.update_metadata_policy_after_user_declined(state)
            # Mark all DANDI fields as declined
            state.user_declined_fields.update(["experimenter", "institution", "experiment_description"])

            # DETAILED DEBUG LOGGING
            state.add_log(
                LogLevel.INFO,
                "User requested to skip all remaining questions - proceeding with minimal conversion",
                {
                    "message": user_message[:100],
                    "user_wants_minimal": state.user_wants_minimal,
                    "metadata_requests_count": state.metadata_requests_count,
                    "user_declined_fields": list(state.user_declined_fields),
                },
            )

            # Add assistant response to history
            decline_message = "Understood! I'll complete the conversion with the data you've provided. The NWB file will be created, though it may not include all recommended metadata fields."
            state.add_conversation_message(role="assistant", content=decline_message)

            state.add_log(
                LogLevel.DEBUG,
                "About to restart conversion after global skip",
                {
                    "user_wants_minimal": state.user_wants_minimal,
                    "metadata_requests_count": state.metadata_requests_count,
                    "status_before": state.status.value,
                }
            )

            # ✅ FIX: Validate that we have a valid input_path before proceeding
            # Use pending_conversion_input_path if available, fallback to input_path
            # This prevents 500 errors when state.input_path is None or invalid
            conversion_path = state.pending_conversion_input_path or state.input_path
            if not conversion_path or str(conversion_path) == "None":
                state.add_log(
                    LogLevel.ERROR,
                    "Cannot restart conversion - input_path not available",
                    {
                        "pending_conversion_input_path": str(state.pending_conversion_input_path) if state.pending_conversion_input_path else "None",
                        "input_path": str(state.input_path) if state.input_path else "None"
                    }
                )
                return MCPResponse.error_response(
                    reply_to=message.message_id,
                    error_code="INVALID_STATE",
                    error_message="Cannot proceed with conversion. The file path is not available. Please try uploading the file again.",
                )

            # Restart conversion WITHOUT asking for more metadata
            return await self.handle_start_conversion(
                MCPMessage(
                    target_agent="conversation",
                    action="start_conversion",
                    context={
                        "input_path": str(conversion_path),
                        "metadata": state.metadata,  # Use existing metadata only
                    },
                ),
                state,
            )

        elif skip_type == "field":
            # User wants to skip THIS specific field only
            # Get the current field being asked from conversation context
            last_context = (
                state.conversation_history[-1].get("context", {})
                if len(state.conversation_history) >= 1
                else {}
            )

            current_field = last_context.get("field")
            if current_field:
                state.user_declined_fields.add(current_field)
                state.add_log(
                    LogLevel.INFO,
                    f"User skipped field: {current_field}",
                    {"message": user_message[:100]},
                )

                # Add assistant response acknowledging the skip
                skip_ack_message = f"No problem! Skipping {current_field}."
                state.add_conversation_message(role="assistant", content=skip_ack_message)

                # ✅ FIX: Validate input_path before restarting
                # Use pending_conversion_input_path if available, fallback to input_path
                conversion_path = state.pending_conversion_input_path or state.input_path
                if not conversion_path or str(conversion_path) == "None":
                    state.add_log(
                        LogLevel.ERROR,
                        "Cannot restart conversion - input_path not available",
                        {
                            "pending_conversion_input_path": str(state.pending_conversion_input_path) if state.pending_conversion_input_path else "None",
                            "input_path": str(state.input_path) if state.input_path else "None"
                        }
                    )
                    return MCPResponse.error_response(
                        reply_to=message.message_id,
                        error_code="INVALID_STATE",
                        error_message="Cannot proceed with conversion. Please upload a file first.",
                    )

                # Restart conversion to ask for next field
                return await self.handle_start_conversion(
                    MCPMessage(
                        target_agent="conversation",
                        action="start_conversion",
                        context={
                            "input_path": str(conversion_path),
                            "metadata": state.metadata,
                        },
                    ),
                    state,
                )

        elif skip_type == "sequential":
            # User wants to answer questions one by one (for batch requests)
            state.add_log(
                LogLevel.INFO,
                "User requested sequential questioning",
            )

            # Save the sequential preference in state (THIS IS THE FIX!)
            state.user_wants_sequential = True

            # This will be handled by the strategy on next round
            # For now, acknowledge and restart
            sequential_ack = "Sure! I'll ask one question at a time."
            state.add_conversation_message(role="assistant", content=sequential_ack)

            # ✅ FIX: Validate input_path before restarting
            # Use pending_conversion_input_path if available, fallback to input_path
            conversion_path = state.pending_conversion_input_path or state.input_path
            if not conversion_path or str(conversion_path) == "None":
                state.add_log(
                    LogLevel.ERROR,
                    "Cannot restart conversion - input_path not available",
                    {
                        "pending_conversion_input_path": str(state.pending_conversion_input_path) if state.pending_conversion_input_path else "None",
                        "input_path": str(state.input_path) if state.input_path else "None"
                    }
                )
                return MCPResponse.error_response(
                    reply_to=message.message_id,
                    error_code="INVALID_STATE",
                    error_message="Cannot proceed with conversion. Please upload a file first.",
                )

            return await self.handle_start_conversion(
                MCPMessage(
                    target_agent="conversation",
                    action="start_conversion",
                    context={
                        "input_path": str(conversion_path),
                        "metadata": state.metadata,
                    },
                ),
                state,
            )

        try:
            # Build conversation context
            last_context = (
                state.conversation_history[-2].get("context", {})
                if len(state.conversation_history) >= 2
                else {}
            )

            context = {
                "validation_result": last_context.get("validation_result", {}),
                "issues": last_context.get("suggested_fixes", []),
                "conversation_history": state.conversation_history,
            }

            # Process user response with LLM
            response = await self._conversational_handler.process_user_response(
                user_message=user_message,
                context=context,
                state=state,
            )

            # Add assistant response to conversation history
            state.add_conversation_message(
                role="assistant",
                content=response.get("follow_up_message", ""),
                context=response
            )

            # ✅ FIX: ALWAYS persist extracted metadata incrementally, even if not ready to proceed
            # This allows multi-turn metadata collection conversations
            extracted_metadata = response.get("extracted_metadata", {})
            if extracted_metadata:
                # CRITICAL: Track user-provided metadata separately
                state.user_provided_metadata.update(extracted_metadata)

                # Merge: auto-extracted + user-provided (user takes priority)
                combined_metadata = {**state.auto_extracted_metadata, **state.user_provided_metadata}
                state.metadata = combined_metadata

                # PROVENANCE TRACKING: Record provenance, but don't overwrite if already set by IntelligentMetadataParser
                # IntelligentMetadataParser already sets correct provenance (AI_PARSED, AI_INFERRED)
                # Only track as user-specified if provenance wasn't already set by the parser
                for field_name, value in extracted_metadata.items():
                    if field_name not in state.metadata_provenance:
                        self._track_user_provided_metadata(
                            state=state,
                            field_name=field_name,
                            value=value,
                            confidence=100.0,
                            source=f"User explicitly provided in conversation",
                            raw_input=user_message[:200],  # Store original message
                        )

                state.add_log(
                    LogLevel.INFO,
                    "User-provided metadata extracted and persisted incrementally (with provenance)",
                    {
                        "user_provided_fields": list(extracted_metadata.keys()),
                        "total_metadata_fields": list(combined_metadata.keys()),
                    },
                )

            # Check if we're ready to proceed with fixes
            if response.get("ready_to_proceed", False):

                # Bug #11 fix: Mark that user provided input for "no progress" detection
                # Mark true regardless of whether metadata was extracted - user engaged with the system
                state.user_provided_input_this_attempt = True

                # Reset conversation phase since standard metadata collection is complete
                if state.conversation_phase == ConversationPhase.METADATA_COLLECTION:
                    state.conversation_phase = ConversationPhase.IDLE
                    state.conversation_type = None

                state.add_log(
                    LogLevel.INFO,
                    "User indicated ready to proceed, checking next steps",
                    {"has_extracted_metadata": bool(extracted_metadata)},
                )

                # ✅ FIX: Use pending_conversion_input_path with fallback
                # This ensures we use the correct path when user provides metadata
                conversion_path = state.pending_conversion_input_path or state.input_path
                if not conversion_path or str(conversion_path) == "None":
                    state.add_log(
                        LogLevel.ERROR,
                        "Cannot restart conversion - input_path not available",
                        {
                            "pending_conversion_input_path": str(state.pending_conversion_input_path) if state.pending_conversion_input_path else "None",
                            "input_path": str(state.input_path) if state.input_path else "None"
                        }
                    )
                    return MCPResponse.error_response(
                        reply_to=message.message_id,
                        error_code="INVALID_STATE",
                        error_message="Cannot proceed with conversion. The file path is not available. Please try uploading the file again.",
                    )

                # Restart conversion with updated metadata (even if none extracted, user said proceed)
                return await self.handle_start_conversion(
                    MCPMessage(
                        target_agent="conversation",
                        action="start_conversion",
                        context={
                            "input_path": str(conversion_path),
                            "metadata": state.metadata,
                        },
                    ),
                    state,
                )

            # Continue conversation
            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "status": "conversation_continues",
                    "message": response.get("follow_up_message"),
                    "needs_more_info": response.get("needs_more_info", True),
                    "extracted_metadata": response.get("extracted_metadata", {}),
                },
            )

        except Exception as e:
            state.add_log(
                LogLevel.ERROR,
                f"Failed to process conversational response: {e}",
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="CONVERSATION_FAILED",
                error_message=str(e),
            )

    async def handle_general_query(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """
        Handle general user questions at ANY time, in ANY state.

        This makes the system feel like Claude.ai - always ready to help.
        Users can ask about NWB format, how to use the system, or get
        contextual help based on their current conversion status.

        Args:
            message: MCP message with user query
            state: Global state with conversion context

        Returns:
            MCPResponse with intelligent answer
        """
        user_query = message.context.get("query", "")

        if not user_query:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="MISSING_QUERY",
                error_message="No query provided",
            )

        state.add_log(
            LogLevel.INFO,
            f"Processing general query: {user_query[:100]}...",
        )

        if not self._llm_service:
            # Fallback to basic responses if no LLM
            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "answer": "I'm here to help with NWB file conversion. Please upload a file to get started.",
                    "type": "general_query_response",
                },
            )

        try:
            # Build rich context from current state
            context_info = {
                "current_status": state.status.value,
                "has_input_file": state.input_path is not None,
                "input_path": str(state.input_path) if state.input_path else None,
                "detected_format": state.metadata.get("format"),
                "validation_status": state.validation_status.value if state.validation_status else None,
                "correction_attempt": state.correction_attempt,
                "can_retry": True,  # Bug #14 fix: Always allow retry
                "output_path": str(state.output_path) if state.output_path else None,
            }

            # Recent conversation history for context
            recent_history = "\n".join([
                f"{msg['role']}: {msg['content'][:100]}"
                for msg in state.conversation_history[-3:]  # Last 3 exchanges
            ]) if state.conversation_history else "No previous conversation"

            system_prompt = """You are an expert NWB (Neurodata Without Borders) conversion assistant.

You help neuroscientists convert their electrophysiology data to NWB format.

Your role:
- Answer questions about NWB format, structure, metadata requirements
- Explain the conversion process and current status
- Provide guidance on fixing validation issues
- Be conversational, helpful, and educational like Claude.ai
- Reference the user's current conversion state when relevant

You should:
- Be friendly and encouraging
- Explain technical concepts clearly
- Provide specific, actionable advice
- Acknowledge what stage they're at in the process
- Offer next steps when appropriate"""

            user_prompt = f"""User question: "{user_query}"

Current conversion context:
- Status: {context_info['current_status']}
- Has file uploaded: {context_info['has_input_file']}
- File path: {context_info['input_path'] or 'None'}
- Format detected: {context_info['detected_format'] or 'Not yet detected'}
- Validation status: {context_info['validation_status'] or 'Not yet validated'}
- Correction attempt: {context_info['correction_attempt']}
- Can retry: {context_info['can_retry']}

Recent conversation:
{recent_history}

Provide a helpful, contextual answer. Be conversational and reference their current state if relevant.
Respond in JSON format."""

            output_schema = {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "Conversational answer to the user's question"
                    },
                    "follow_up_suggestions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional suggestions for next steps or related questions"
                    },
                    "relevant_action": {
                        "type": "string",
                        "description": "Optional action the user might want to take (e.g., 'upload_file', 'start_conversion')"
                    }
                },
                "required": ["answer"]
            }

            response = await self._llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            # Add to conversation history
            state.add_conversation_message(role="user", content=user_query)
            state.add_conversation_message(role="assistant", content=response.get("answer", ""))

            state.add_log(
                LogLevel.INFO,
                "General query answered successfully",
                {"query_preview": user_query[:50]},
            )

            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "type": "general_query_response",
                    "answer": response.get("answer"),
                    "suggestions": response.get("follow_up_suggestions", []),
                    "suggested_action": response.get("relevant_action"),
                },
            )

        except Exception as e:
            state.add_log(
                LogLevel.ERROR,
                f"Failed to process general query: {e}",
            )
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="QUERY_PROCESSING_FAILED",
                error_message=f"Failed to process your question: {str(e)}",
            )


    async def handle_improvement_decision(
        self,
        message: MCPMessage,
        state: GlobalState,
    ) -> MCPResponse:
        """
        Handle user decision for PASSED_WITH_ISSUES validation.

        When validation passes but has warnings, user chooses:
        - "improve" - Enter correction loop to fix warnings
        - "accept" - Accept file as-is and finalize

        Args:
            message: MCP message with context containing 'decision'
            state: Global state

        Returns:
            MCPResponse with result
        """
        decision = message.context.get("decision")

        if decision == "accept":
            # User accepts file with warnings - finalize
            state.add_log(
                LogLevel.INFO,
                "User accepted file with warnings (PASSED_WITH_ISSUES)",
                {"validation_status": "passed_accepted"},
            )

            # Set final validation status
            await state.update_validation_status(ValidationStatus.PASSED_ACCEPTED)
            await state.update_status(ConversionStatus.COMPLETED)

            # Generate final message
            state.llm_message = (
                "✅ File accepted as-is with warnings. "
                "Your NWB file is ready for download. "
                "You can view the warnings in the validation report."
            )

            return MCPResponse.success_response(
                reply_to=message.message_id,
                result={
                    "status": "completed",
                    "message": state.llm_message,
                    "validation_status": "passed_accepted",
                },
            )

        elif decision == "improve":
            # User wants to improve - enter correction loop
            state.add_log(
                LogLevel.INFO,
                "User chose to improve warnings (PASSED_WITH_ISSUES)",
                {"entering_correction_loop": True},
            )

            # Increment correction attempt
            state.increment_correction_attempt()

            # Get correction context from evaluation agent
            # This will categorize issues and prepare for reconversion
            eval_msg = MCPMessage(
                target_agent="evaluation",
                action="analyze_corrections",
                context={
                    "validation_result": state.metadata.get("last_validation_result", {}),
                    "correction_attempt": state.correction_attempt,
                },
            )

            eval_response = await self._mcp_server.send_message(eval_msg)

            if not eval_response.success:
                return MCPResponse.error_response(
                    reply_to=message.message_id,
                    error_code="CORRECTION_ANALYSIS_FAILED",
                    error_message="Failed to analyze corrections",
                )

            correction_context = eval_response.result.get("correction_context", {})

            # Categorize issues
            auto_fixable = correction_context.get("auto_fixable_issues", [])
            user_input_required = correction_context.get("user_input_required", [])

            # If user input is needed, request it
            if user_input_required:
                # Generate smart prompts for missing data
                if self._llm_service:
                    prompt_msg = await self._generate_correction_prompts(
                        user_input_required,
                        state,
                    )
                else:
                    prompt_msg = self._generate_basic_correction_prompts(
                        user_input_required
                    )

                state.llm_message = prompt_msg
                await state.update_status(ConversionStatus.AWAITING_USER_INPUT)
                state.conversation_type = "correction_input"

                return MCPResponse.success_response(
                    reply_to=message.message_id,
                    result={
                        "status": "awaiting_user_input",
                        "message": prompt_msg,
                        "auto_fixable_count": len(auto_fixable),
                        "user_input_required_count": len(user_input_required),
                    },
                )

            # If only auto-fixable issues, ask user before auto-correcting
            else:
                state.add_log(
                    LogLevel.INFO,
                    f"Found {len(auto_fixable)} auto-fixable issues, asking user for approval",
                )

                # Store correction context for when user approves
                state.correction_context = correction_context

                # Generate summary of auto-fixable issues
                issue_summary = self._generate_auto_fix_summary(auto_fixable)

                # Ask user for approval
                approval_message = (
                    f"I found {len(auto_fixable)} issue(s) that I can fix automatically:\n\n"
                    f"{issue_summary}\n\n"
                    f"Would you like me to:\n"
                    f"• **Apply fixes automatically** - I'll fix these issues and reconvert the file\n"
                    f"• **Show details first** - See exactly what will be changed\n"
                    f"• **Cancel** - Keep the file as-is\n\n"
                    f"Please respond with 'apply', 'show details', or 'cancel'."
                )

                state.llm_message = approval_message
                await state.update_status(ConversionStatus.AWAITING_USER_INPUT)
                state.conversation_type = "auto_fix_approval"

                return MCPResponse.success_response(
                    reply_to=message.message_id,
                    result={
                        "status": "awaiting_user_input",
                        "message": approval_message,
                        "auto_fixable_count": len(auto_fixable),
                        "needs_approval": True,
                    },
                )

        else:
            return MCPResponse.error_response(
                reply_to=message.message_id,
                error_code="INVALID_DECISION",
                error_message=f"Invalid decision: {decision}. Must be 'improve' or 'accept'.",
            )

    async def _generate_correction_prompts(
        self,
        issues: List[Dict[str, Any]],
        state: GlobalState,
    ) -> str:
        """
        Generate smart prompts for correction issues using LLM.

        Args:
            issues: List of issues requiring user input
            state: Global state

        Returns:
            Formatted prompt message
        """
        # Use LLM to generate contextual prompts with examples
        system_prompt = """You are helping a user fix validation warnings in their NWB file.
Generate clear, specific prompts for each issue with helpful examples."""

        user_prompt = f"""The NWB file has {len(issues)} warnings that need user input:

Issues:
{json.dumps(issues, indent=2)}

Generate a friendly message asking for the missing information. Include:
1. What needs to be fixed
2. Why it matters
3. Specific examples for each field

Return JSON with a 'message' field."""

        output_schema = {
            "type": "object",
            "properties": {
                "message": {"type": "string"}
            },
            "required": ["message"]
        }

        try:
            response = await self._llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )
            return response.get("message", self._generate_basic_correction_prompts(issues))
        except Exception:
            return self._generate_basic_correction_prompts(issues)

    async def _handle_auto_fix_approval_response(
        self,
        user_message: str,
        reply_to: str,
        state: GlobalState
    ) -> MCPResponse:
        """
        Handle user's response to auto-fix approval request.

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
                {"fixes": auto_fixes}
            )

            # PROVENANCE TRACKING: Track auto-corrected metadata
            for field_name, value in auto_fixes.items():
                issue_desc = next(
                    (issue.get('message', '') for issue in auto_fixable_issues
                     if issue.get('field_name') == field_name or field_name.lower() in issue.get('message', '').lower()),
                    f"Auto-fix for validation issue"
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
                check_name = issue.get('check_name', 'Unknown')
                message = issue.get('message', 'No details')
                severity = issue.get('severity', 'warning')
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

            state.llm_message = (
                "Understood! I'll keep the file as-is. "
                "Your NWB file is ready for download with the existing warnings."
            )
            state.conversation_type = None  # Clear conversation type

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

    def _generate_auto_fix_summary(self, issues: List[Dict[str, Any]]) -> str:
        """
        Generate summary of auto-fixable issues.

        Args:
            issues: List of auto-fixable issues

        Returns:
            Formatted summary message
        """
        summary = ""
        for i, issue in enumerate(issues, 1):
            issue_name = issue.get('check_name', 'Unknown issue')
            issue_msg = issue.get('message', 'No details available')
            # Truncate long messages
            if len(issue_msg) > 100:
                issue_msg = issue_msg[:97] + "..."
            summary += f"{i}. **{issue_name}**: {issue_msg}\n"
        return summary.strip()

    def _extract_fixes_from_issues(
        self,
        auto_fixable_issues: List[Dict[str, Any]],
        state: GlobalState
    ) -> Dict[str, Any]:
        """
        PRIORITY 2 FIX: Extract metadata fixes from auto-fixable issues.

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
            suggested_fix = issue.get('suggested_fix')
            field_name = issue.get('field_name')

            if suggested_fix and field_name:
                # Direct field/value mapping available
                auto_fixes[field_name] = suggested_fix
                state.add_log(
                    LogLevel.DEBUG,
                    f"Extracted fix: {field_name} = {suggested_fix}",
                    {"issue": issue.get('check_name')}
                )
            else:
                # Try to infer fix from issue message
                inferred_fix = self._infer_fix_from_issue(issue, state)
                if inferred_fix:
                    auto_fixes.update(inferred_fix)

        return auto_fixes

    def _infer_fix_from_issue(
        self,
        issue: Dict[str, Any],
        state: GlobalState
    ) -> Optional[Dict[str, Any]]:
        """
        Infer metadata fix from validation issue message.

        Args:
            issue: Validation issue dict
            state: Global state

        Returns:
            Dictionary with inferred fix, or None if unable to infer
        """
        message = issue.get('message', '').lower()
        check_name = issue.get('check_name', '').lower()

        # Common patterns for missing metadata
        if 'experimenter' in message or 'experimenter' in check_name:
            # Use existing metadata if available, otherwise use placeholder
            return {'experimenter': state.metadata.get('experimenter', 'Unknown')}

        elif 'institution' in message or 'institution' in check_name:
            return {'institution': state.metadata.get('institution', 'Unknown')}

        elif 'session_description' in message or 'session_description' in check_name:
            # Generate from experiment_description if available
            exp_desc = state.metadata.get('experiment_description')
            return {'session_description': exp_desc if exp_desc else 'Electrophysiology recording session'}

        elif 'subject_id' in message or 'subject_id' in check_name:
            return {'subject_id': state.metadata.get('subject_id', 'subject_001')}

        # Unable to infer fix
        state.add_log(
            LogLevel.DEBUG,
            f"Could not infer fix for issue: {check_name}",
            {"message": message[:100]}
        )
        return None

    def _generate_basic_correction_prompts(self, issues: List[Dict[str, Any]]) -> str:
        """
        Generate basic correction prompts without LLM.

        Args:
            issues: List of issues requiring user input

        Returns:
            Formatted prompt message
        """
        prompt = f"⚠️ Found {len(issues)} warnings that need your input:\n\n"
        for i, issue in enumerate(issues, 1):
            prompt += f"{i}. **{issue.get('check_name', 'Unknown')}**: {issue.get('message', '')}\n"
        prompt += "\nPlease provide the requested information to continue."
        return prompt


def register_conversation_agent(
    mcp_server: MCPServer,
    llm_service: Optional[LLMService] = None,
) -> ConversationAgent:
    """
    Register Conversation Agent handlers with MCP server.

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
