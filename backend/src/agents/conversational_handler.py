"""
Conversational Handler for intelligent LLM-driven interactions.

This module enables natural, adaptive conversations with users
instead of rigid predefined workflows.
"""
from typing import Any, Dict, List, Optional
import json

from models import GlobalState, LogLevel, MetadataRequestPolicy
from services import LLMService
from agents.metadata_strategy import MetadataRequestStrategy
from agents.context_manager import ConversationContextManager
from agents.nwb_dandi_schema import NWBDANDISchema
from agents.intelligent_metadata_parser import IntelligentMetadataParser, ParsedField


class ConversationalHandler:
    """
    Handles intelligent, LLM-driven conversations about NWB conversion.

    Instead of hardcoded workflows, this uses the LLM to:
    - Analyze validation results
    - Determine what information is needed
    - Ask natural questions
    - Process user responses adaptively
    """

    def __init__(self, llm_service: LLMService):
        """
        Initialize the conversational handler.

        Args:
            llm_service: LLM service for generating responses
        """
        self.llm_service = llm_service
        # Pass llm_service to metadata_strategy so it can use LLM-based detection
        self.metadata_strategy = MetadataRequestStrategy(llm_service=llm_service)
        # Initialize context manager for smart conversation summarization
        self.context_manager = ConversationContextManager(llm_service=llm_service)
        # Initialize intelligent metadata parser for natural language understanding
        self.metadata_parser = IntelligentMetadataParser(llm_service=llm_service)

    def detect_user_decline(self, user_message: str) -> bool:
        """
        Detect if user is declining to provide information.

        Looks for common decline patterns like "skip", "no", "don't ask", etc.

        Args:
            user_message: User's message text

        Returns:
            True if user is declining/skipping, False otherwise
        """
        skip_type = self.metadata_strategy.detect_skip_type(user_message)
        return skip_type in ["field", "global"]

    async def detect_skip_type_with_llm(self, user_message: str, conversation_context: str = "") -> str:
        """
        Intelligently detect user's skip intent using LLM.

        This understands natural language variations and context better than keyword matching.

        Args:
            user_message: User's message text
            conversation_context: Recent conversation for context

        Returns:
            "field", "global", "sequential", or "none"
        """
        return await self.metadata_strategy.detect_skip_type_with_llm(user_message, conversation_context)

    def detect_skip_type(self, user_message: str) -> str:
        """
        Keyword-based skip detection (fallback method).

        Args:
            user_message: User's message text

        Returns:
            "field", "global", "sequential", or "none"
        """
        return self.metadata_strategy.detect_skip_type(user_message)

    async def analyze_validation_and_respond(
        self,
        validation_result: Dict[str, Any],
        nwb_file_path: str,
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Analyze validation results and generate intelligent response.

        Uses LLM to understand validation issues and determine next steps:
        - Can these be auto-fixed?
        - What information do we need from the user?
        - Should we ask clarifying questions?

        Args:
            validation_result: Validation result from NWB Inspector
            nwb_file_path: Path to the NWB file
            state: Global state

        Returns:
            Dict with response_type and content for the user
        """
        # WORKFLOW_CONDITION_FLAGS_ANALYSIS.md Fix: Use MetadataRequestPolicy enum
        # Check if user declined or we've already asked
        should_skip = (
            state.metadata_policy in [MetadataRequestPolicy.USER_DECLINED, MetadataRequestPolicy.PROCEEDING_MINIMAL] or
            state.metadata_policy == MetadataRequestPolicy.ASKED_ONCE
        )

        if should_skip:
            state.add_log(
                LogLevel.INFO,
                "User wants minimal metadata or exceeded request limit - proceeding without asking",
                {"metadata_policy": state.metadata_policy.value}
            )
            return {
                "type": "proceed_minimal",
                "message": "Understood! I'll complete the conversion with the data I have. The file will be valid but may not meet all recommended standards for data sharing.",
                "needs_user_input": False,
                "proceed_with_minimal": True,
                "severity": "low",
                "validation_result": validation_result,
            }

        state.add_log(
            LogLevel.INFO,
            "Analyzing validation results with LLM",
        )

        # Build context for LLM
        issues_summary = self._format_validation_issues(validation_result)

        system_prompt = """You are an expert neuroscience data curator helping scientists convert their data to NWB (Neurodata Without Borders) format.

Your role is to:
1. Analyze NWB Inspector validation results
2. Determine what information is missing or incorrect
3. Ask the user helpful, specific questions to gather needed information
4. Be conversational, friendly, and educational

When you see validation issues:
- If metadata is missing (experimenter, institution, keywords, subject, etc.), ask the user to provide it
- Be specific about what's needed and why it's important
- Offer guidance on best practices
- Keep responses concise but informative

Format your response as JSON with this structure:
{
    "message": "Your conversational message to the user",
    "needs_user_input": true/false,
    "suggested_fixes": [
        {
            "field": "field_name",
            "description": "What this field is for",
            "example": "Example value"
        }
    ],
    "severity": "low" | "medium" | "high"
}"""

        user_prompt = f"""I've converted a file to NWB format. The NWB Inspector found some issues. Please analyze them and help me understand what needs to be fixed.

File: {nwb_file_path}

Validation Summary:
{json.dumps(validation_result.get('summary', {}), indent=2)}

Issues Found:
{issues_summary}

Please:
1. Explain what these issues mean in simple terms
2. Tell me if they're critical or just recommendations
3. If information is missing, ask me specific questions to gather it
4. Be conversational and helpful

Respond in JSON format as specified."""

        try:
            # Use generate_structured_output for JSON responses
            output_schema = {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "needs_user_input": {"type": "boolean"},
                    "suggested_fixes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "field": {"type": "string"},
                                "description": {"type": "string"},
                                "example": {"type": "string"}
                            }
                        }
                    },
                    "severity": {"type": "string", "enum": ["low", "medium", "high"]}
                },
                "required": ["message", "needs_user_input", "severity"]
            }

            response_data = await self.llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            state.add_log(
                LogLevel.INFO,
                "LLM analysis complete",
                {"needs_user_input": response_data.get("needs_user_input", False)},
            )

            # If user input is needed, use priority-based metadata strategy
            if response_data.get("needs_user_input", False):
                # Update metadata policy to indicate we've asked
                if state.metadata_policy == MetadataRequestPolicy.NOT_ASKED:
                    state.metadata_policy = MetadataRequestPolicy.ASKED_ONCE
                    # Maintain backward compatibility
                    state.metadata_requests_count += 1

                state.add_log(
                    LogLevel.INFO,
                    f"Requesting metadata from user (policy: {state.metadata_policy.value})",
                )

                # Use the new hybrid strategy to determine what to ask
                try:
                    metadata_request = self.metadata_strategy.get_next_request(
                        state=state,
                        validation_result=validation_result,
                    )

                    if metadata_request.get("action") == "proceed":
                        # Nothing left to ask, proceed with minimal
                        return {
                            "type": "proceed_minimal",
                            "message": "I have all the metadata you've provided. Proceeding with conversion!",
                            "needs_user_input": False,
                            "proceed_with_minimal": True,
                            "severity": "low",
                            "validation_result": validation_result,
                        }

                    # Return the strategic request
                    return {
                        "type": "conversational",
                        "message": metadata_request.get("message"),
                        "needs_user_input": True,
                        "phase": metadata_request.get("phase"),
                        "priority": metadata_request.get("priority"),
                        "can_skip": metadata_request.get("can_skip", True),
                        "fields": metadata_request.get("fields", []),
                        "field": metadata_request.get("field"),
                        "suggested_fixes": response_data.get("suggested_fixes", []),
                        "severity": response_data.get("severity", "medium"),
                        "validation_result": validation_result,
                    }

                except Exception as e:
                    state.add_log(
                        LogLevel.WARNING,
                        f"Metadata strategy failed, using fallback: {e}",
                    )
                    # Fallback to simple response
                    return {
                        "type": "conversational",
                        "message": response_data.get("message"),
                        "needs_user_input": True,
                        "suggested_fixes": response_data.get("suggested_fixes", []),
                        "severity": response_data.get("severity", "medium"),
                        "validation_result": validation_result,
                    }

            # No user input needed
            return {
                "type": "conversational",
                "message": response_data.get("message"),
                "needs_user_input": False,
                "suggested_fixes": response_data.get("suggested_fixes", []),
                "severity": response_data.get("severity", "medium"),
                "validation_result": validation_result,
            }

        except Exception as e:
            state.add_log(
                LogLevel.ERROR,
                f"LLM analysis failed: {e}",
            )
            raise

    async def parse_and_confirm_metadata(
        self,
        user_message: str,
        state: GlobalState,
        mode: str = "batch",  # "batch" or "single"
        field_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Parse user metadata input and generate confirmation message.

        This implements the three-scenario system:
        1. User confirms → apply
        2. User edits → apply correction
        3. User skips → auto-apply with best knowledge

        Args:
            user_message: User's natural language input
            state: Global state
            mode: "batch" for multiple fields, "single" for one field
            field_name: Field name if mode="single"

        Returns:
            Dict with:
            - parsed_fields: List of ParsedField objects
            - confirmation_message: Message showing what was understood
            - needs_confirmation: Whether to wait for user confirmation
            - auto_applied_fields: Fields auto-applied (if user skipped)
        """
        # CRITICAL FIX: Check if user is confirming/skipping BEFORE parsing
        # This prevents unnecessary LLM calls and metadata loss
        confirmation_keywords = ["yes", "correct", "ok", "confirm", "accept", "✓", "y", "looks good", "perfect"]
        edit_keywords = ["no", "change", "edit", "wrong", "fix", "incorrect"]
        skip_keywords = ["skip", "pass", "next", ""]  # Empty means Enter key

        # Auto-apply phrases (user wants system to decide)
        auto_apply_phrases = [
            "do it on your own", "do it yourself", "just do it", "apply it",
            "auto apply", "use your best", "go ahead", "proceed", "continue",
            "don't ask", "decide for me", "you choose", "up to you", "just apply"
        ]

        user_lower = user_message.lower().strip()

        state.add_log(
            LogLevel.DEBUG,
            f"parse_and_confirm_metadata called with message: '{user_message[:50]}'",
            {
                "has_pending_fields": hasattr(state, 'pending_parsed_fields') and bool(state.pending_parsed_fields),
                "pending_field_count": len(state.pending_parsed_fields) if hasattr(state, 'pending_parsed_fields') and state.pending_parsed_fields else 0,
            }
        )

        # BUG FIX: Use word boundary matching to prevent false positives
        # e.g., "y" should not match "by" or "laboratory"
        import re
        def contains_keyword(text: str, keywords: list) -> bool:
            """Check if text contains any keyword using word boundaries."""
            for keyword in keywords:
                # Use word boundaries for single-word keywords, substring for phrases
                if ' ' in keyword:
                    # Multi-word phrase - use substring matching
                    if keyword in text:
                        return True
                else:
                    # Single word - use word boundary matching
                    if re.search(r'\b' + re.escape(keyword) + r'\b', text):
                        return True
            return False

        # Scenario 1: User confirmed - retrieve pending fields WITHOUT parsing
        if contains_keyword(user_lower, confirmation_keywords):
            state.add_log(
                LogLevel.INFO,
                "User confirmed parsed metadata",
            )

            # Retrieve the pending_parsed_fields that were stored earlier
            if hasattr(state, 'pending_parsed_fields') and state.pending_parsed_fields:
                state.add_log(
                    LogLevel.INFO,
                    f"Retrieving {len(state.pending_parsed_fields)} pending fields from previous parse",
                    {"fields": list(state.pending_parsed_fields.keys())}
                )
                confirmed = state.pending_parsed_fields.copy()
                # Clear pending fields after confirmation
                state.pending_parsed_fields = {}

                state.add_log(
                    LogLevel.INFO,
                    f"User confirmed {len(confirmed)} metadata fields - RETURNING confirmed result",
                    {"confirmed_fields": list(confirmed.keys())}
                )

                return {
                    "type": "confirmed",
                    "parsed_fields": [],  # No new fields parsed, using confirmed from pending
                    "confirmed_fields": confirmed,
                    "confirmation_message": "✓ Perfect! Applied all confirmed values.",
                    "needs_confirmation": False,
                }
            else:
                # No pending fields - user said "yes" but nothing to confirm
                state.add_log(
                    LogLevel.WARNING,
                    "User confirmed but no pending fields found",
                )
                return {
                    "type": "needs_edit",
                    "parsed_fields": [],
                    "confirmation_message": "I don't have any pending metadata to confirm. Please provide the metadata values.",
                    "needs_confirmation": True,
                }

        # Scenario 2: User wants to edit
        if contains_keyword(user_lower, edit_keywords):
            # User said "no" or "edit" - ask them to provide correction
            return {
                "type": "needs_edit",
                "parsed_fields": [],
                "confirmation_message": "No problem! Please provide the correct information. "
                                       "You can say the field name and value (e.g., 'age: P90D') "
                                       "or describe it naturally.",
                "needs_confirmation": True,
            }

        # Scenario 3: User skipped or wants auto-apply
        if user_lower in skip_keywords or not user_message.strip() or contains_keyword(user_lower, auto_apply_phrases):
            # For skip/auto-apply, we need parsed fields, but only if we have pending ones
            if hasattr(state, 'pending_parsed_fields') and state.pending_parsed_fields:
                # Auto-apply the pending fields
                state.add_log(
                    LogLevel.INFO,
                    "User skipped confirmation - auto-applying pending fields",
                )
                auto_applied = state.pending_parsed_fields.copy()
                state.pending_parsed_fields = {}

                return {
                    "type": "auto_applied",
                    "parsed_fields": [],
                    "auto_applied_fields": auto_applied,
                    "confirmation_message": "✓ Auto-applied all fields using best interpretation.",
                    "needs_confirmation": False,
                }

        # If we reach here, user is providing NEW metadata - NOW we parse
        state.add_log(
            LogLevel.INFO,
            "User is providing NEW metadata (not confirming/editing/skipping) - calling parser",
        )

        if mode == "batch":
            parsed_fields = await self.metadata_parser.parse_natural_language_batch(
                user_message, state
            )
        else:
            if not field_name:
                raise ValueError("field_name required for single mode")
            parsed_field = await self.metadata_parser.parse_single_field(
                field_name, user_message, state
            )
            parsed_fields = [parsed_field]

        # Generate confirmation message and wait for response
        # Pass state to check for missing required fields
        confirmation_msg = self.metadata_parser.generate_confirmation_message(parsed_fields, state)

        # Store parsed fields in state so they can be retrieved when user confirms
        if not hasattr(state, 'pending_parsed_fields'):
            state.pending_parsed_fields = {}

        for field in parsed_fields:
            state.pending_parsed_fields[field.field_name] = field.parsed_value

        state.add_log(
            LogLevel.DEBUG,
            f"Stored {len(parsed_fields)} pending parsed fields awaiting user confirmation",
            {"fields": list(state.pending_parsed_fields.keys())}
        )

        return {
            "type": "awaiting_confirmation",
            "parsed_fields": [f.to_dict() for f in parsed_fields],
            "confirmation_message": confirmation_msg,
            "needs_confirmation": True,
        }

    async def process_user_response(
        self,
        user_message: str,
        context: Dict[str, Any],
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Process user's conversational response using LLM with intelligent parsing and confirmation.

        NEW: Uses IntelligentMetadataParser for:
        - Natural language understanding
        - NWB/DANDI format normalization
        - Confidence-based auto-application
        - User confirmation workflow

        Args:
            user_message: User's message
            context: Conversation context (previous validation, issues, etc.)
            state: Global state

        Returns:
            Dict with extracted information and next steps
        """
        state.add_log(
            LogLevel.INFO,
            f"Processing user message with intelligent parser: {user_message[:100]}...",
        )

        # NEW: Use intelligent metadata parser with confirmation workflow
        try:
            parse_result = await self.parse_and_confirm_metadata(
                user_message=user_message,
                state=state,
                mode="batch",  # Parse all fields at once
            )

            # Handle different result types
            result_type = parse_result.get("type")

            if result_type == "auto_applied":
                # User skipped confirmation - fields auto-applied with best knowledge
                return {
                    "type": "user_response_processed",
                    "extracted_metadata": parse_result.get("auto_applied_fields", {}),
                    "needs_more_info": False,
                    "follow_up_message": parse_result.get("confirmation_message"),
                    "ready_to_proceed": True,
                }

            elif result_type == "confirmed":
                # User confirmed - apply confirmed values
                return {
                    "type": "user_response_processed",
                    "extracted_metadata": parse_result.get("confirmed_fields", {}),
                    "needs_more_info": False,
                    "follow_up_message": parse_result.get("confirmation_message"),
                    "ready_to_proceed": True,
                }

            elif result_type == "needs_edit":
                # User wants to edit - wait for correction
                return {
                    "type": "user_response_processed",
                    "extracted_metadata": {},
                    "needs_more_info": True,
                    "follow_up_message": parse_result.get("confirmation_message"),
                    "ready_to_proceed": False,
                }

            elif result_type == "awaiting_confirmation":
                # Show parsed fields and wait for confirmation
                return {
                    "type": "user_response_processed",
                    "extracted_metadata": {},  # Don't apply yet
                    "needs_more_info": True,
                    "follow_up_message": parse_result.get("confirmation_message"),
                    "ready_to_proceed": False,
                    "parsed_fields": parse_result.get("parsed_fields", []),
                }

            else:
                # Unknown type - fallback to original method
                raise ValueError(f"Unknown parse result type: {result_type}")

        except Exception as e:
            import traceback
            state.add_log(
                LogLevel.ERROR,
                f"Intelligent parser failed, using fallback extraction: {e}",
                {
                    "exception_type": type(e).__name__,
                    "exception_message": str(e),
                    "traceback": traceback.format_exc()
                }
            )

            # CRITICAL FIX: Before falling back, check if user was confirming pending metadata
            # If so, return that instead of falling back to LLM extraction
            confirmation_keywords = ["yes", "correct", "ok", "confirm", "accept", "✓", "y", "looks good", "perfect"]
            user_lower = user_message.lower().strip()

            # BUG FIX: Use word boundary matching to prevent false positives
            import re
            def contains_keyword_fallback(text: str, keywords: list) -> bool:
                """Check if text contains any keyword using word boundaries."""
                for keyword in keywords:
                    if ' ' in keyword:
                        if keyword in text:
                            return True
                    else:
                        if re.search(r'\b' + re.escape(keyword) + r'\b', text):
                            return True
                return False

            if (contains_keyword_fallback(user_lower, confirmation_keywords) and
                hasattr(state, 'pending_parsed_fields') and state.pending_parsed_fields):

                state.add_log(
                    LogLevel.INFO,
                    f"Parser failed but detected confirmation - using pending fields from state",
                    {"fields": list(state.pending_parsed_fields.keys())}
                )

                confirmed_metadata = state.pending_parsed_fields.copy()
                state.pending_parsed_fields = {}  # Clear after use

                return {
                    "type": "user_response_processed",
                    "extracted_metadata": confirmed_metadata,
                    "needs_more_info": False,
                    "follow_up_message": "✓ Perfect! Applied all confirmed values.",
                    "ready_to_proceed": True,
                }

            # Otherwise, fall back to original LLM extraction method
            pass

        # FALLBACK: Original extraction method (if parser fails)
        # Generate system prompt dynamically from NWB/DANDI schema
        # This ensures ALL required and recommended fields are covered
        system_prompt = NWBDANDISchema.generate_llm_extraction_prompt()

        # Build context from previous conversation
        validation_info = context.get("validation_result", {})
        previous_messages = context.get("conversation_history", [])

        # Use context manager to intelligently manage conversation history
        try:
            managed_messages = await self.context_manager.manage_context(
                conversation_history=previous_messages,
                state=state,
            )
            # Use managed context for better LLM understanding
            conversation_history = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in managed_messages
            ])
        except Exception as e:
            # Fallback to simple truncation if context management fails
            state.add_log(
                LogLevel.WARNING,
                f"Context management failed, using fallback: {e}",
            )
            conversation_history = "\n".join([
                f"{msg['role']}: {msg['content']}"
                for msg in previous_messages[-5:]  # Last 5 messages for context
            ])

        # Build context about already-provided metadata to help LLM understand state
        already_provided = []
        if state.user_provided_metadata:
            already_provided.append("\n**Already provided by user in previous messages:**")
            for field, value in state.user_provided_metadata.items():
                already_provided.append(f"  - {field}: {value}")

        already_provided_str = "\n".join(already_provided) if already_provided else ""

        user_prompt = f"""Previous conversation:
{conversation_history}

Missing metadata issues:
{json.dumps(context.get('issues', []), indent=2)}
{already_provided_str}

User's response:
{user_message}

Please extract the metadata from the user's response and determine next steps.
IMPORTANT: If the user is confirming/accepting (saying "yes", "ok", "accept", "proceed"),
and metadata was already provided in previous messages (shown above), set ready_to_proceed=true."""

        try:
            # Use generate_structured_output for JSON responses
            output_schema = {
                "type": "object",
                "properties": {
                    "extracted_metadata": {
                        "type": "object",
                        "description": "Structured metadata extracted from user response"
                    },
                    "needs_more_info": {
                        "type": "boolean",
                        "description": "Whether more information is needed from user"
                    },
                    "follow_up_message": {
                        "type": "string",
                        "description": "Conversational follow-up message or confirmation"
                    },
                    "ready_to_proceed": {
                        "type": "boolean",
                        "description": "Whether we have enough info to proceed with conversion"
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence score 0-100 for the extraction quality"
                    }
                },
                "required": ["extracted_metadata", "needs_more_info", "ready_to_proceed", "follow_up_message"]
            }

            response_data = await self.llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            state.add_log(
                LogLevel.INFO,
                "Extracted metadata from user response",
                {"metadata_fields": list(response_data.get("extracted_metadata", {}).keys())},
            )

            return {
                "type": "user_response_processed",
                "extracted_metadata": response_data.get("extracted_metadata", {}),
                "needs_more_info": response_data.get("needs_more_info", False),
                "follow_up_message": response_data.get("follow_up_message"),
                "ready_to_proceed": response_data.get("ready_to_proceed", False),
            }

        except Exception as e:
            state.add_log(
                LogLevel.ERROR,
                f"Failed to process user response: {e}",
            )
            # Fallback - try to extract basic metadata
            return {
                "type": "user_response_processed",
                "extracted_metadata": {},
                "needs_more_info": True,
                "follow_up_message": "I'm having trouble parsing your response. Could you provide the information in a more structured way?",
                "ready_to_proceed": False,
            }

    def _format_validation_issues(self, validation_result: Dict[str, Any]) -> str:
        """
        Format validation issues into readable text for LLM.

        Args:
            validation_result: Validation result dictionary

        Returns:
            Formatted string of issues
        """
        issues = validation_result.get("issues", [])

        if not issues:
            return "No issues found"

        formatted_issues = []
        for idx, issue in enumerate(issues[:20], 1):  # Limit to first 20 issues
            formatted_issues.append(
                f"{idx}. [{issue.get('severity', 'UNKNOWN')}] "
                f"{issue.get('message', 'No message')}\n"
                f"   Location: {issue.get('location', 'Unknown')}\n"
                f"   Check: {issue.get('check_function_name', 'Unknown')}"
            )

        if len(issues) > 20:
            formatted_issues.append(f"\n... and {len(issues) - 20} more issues")

        return "\n\n".join(formatted_issues)

    async def generate_smart_metadata_requests(
        self,
        validation_result: Dict[str, Any],
        nwb_file_path: str,
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Use LLM to generate contextual, intelligent metadata requests.

        Instead of hardcoded field detection, this analyzes the file and validation
        issues to ask smart, contextual questions that guide the user effectively.

        Args:
            validation_result: Validation result with issues
            nwb_file_path: Path to NWB file for context extraction
            state: Global conversion state

        Returns:
            Dictionary with:
            - message: Conversational message asking for metadata
            - required_fields: List of field definitions with context
            - suggestions: Helpful suggestions based on file analysis
        """
        try:
            # Extract file context
            file_context = await self._extract_file_context(nwb_file_path, state)

            # Format validation issues
            formatted_issues = self._format_validation_issues(validation_result)

            # Build LLM prompt
            system_prompt = """You are an expert NWB metadata assistant.
Your job is to analyze validation issues and file context, then:
1. Generate a friendly, conversational message asking for missing metadata
2. Identify required fields with contextual descriptions
3. Infer likely values from file data when possible
4. Provide helpful examples and suggestions

Be empathetic, clear, and guide users toward providing quality metadata.
Focus on fields that are actually missing or need improvement."""

            user_prompt = f"""Analyze these validation issues and file context:

VALIDATION ISSUES:
{formatted_issues}

FILE CONTEXT:
{json.dumps(file_context, indent=2)}

Generate a metadata request that:
1. Acknowledges what's working well
2. Asks for missing metadata conversationally
3. Provides context about why each field matters
4. Suggests likely values based on file analysis
5. Gives clear examples

Be specific about what the file reveals (recording type, data characteristics, etc.)."""

            output_schema = {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Friendly conversational message to user",
                    },
                    "required_fields": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "field_name": {"type": "string"},
                                "display_name": {"type": "string"},
                                "description": {"type": "string"},
                                "why_needed": {"type": "string"},
                                "inferred_value": {"type": "string"},
                                "example": {"type": "string"},
                                "field_type": {
                                    "type": "string",
                                    "enum": ["text", "list", "date", "nested"],
                                },
                            },
                            "required": ["field_name", "display_name", "description"],
                        },
                    },
                    "suggestions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Helpful tips based on file analysis",
                    },
                    "detected_data_type": {
                        "type": "string",
                        "description": "Type of recording detected (e.g., 'electrophysiology', 'imaging')",
                    },
                },
                "required": ["message", "required_fields"],
            }

            response = await self.llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            return response

        except Exception as e:
            # Fallback to basic request if LLM fails
            return {
                "message": "I found some missing metadata in your NWB file. Could you provide the following information?",
                "required_fields": self._extract_basic_required_fields(validation_result),
                "suggestions": [
                    "Providing complete metadata helps others understand and reuse your data",
                    "Required fields enable submission to DANDI archive",
                ],
            }

    async def _extract_file_context(
        self,
        nwb_file_path: str,
        state: GlobalState,
    ) -> Dict[str, Any]:
        """
        Extract contextual information from NWB file for intelligent metadata requests.

        Args:
            nwb_file_path: Path to NWB file
            state: Global state with conversion info

        Returns:
            Dictionary with file context (format, data types, sizes, etc.)
        """
        import h5py
        from pathlib import Path

        context = {
            "file_size_mb": 0,
            "detected_format": state.metadata.get("format", "unknown"),
            "has_subject_info": False,
            "has_devices": False,
            "has_electrodes": False,
            "data_interfaces": [],
            "acquisition_types": [],
        }

        try:
            if not Path(nwb_file_path).exists():
                return context

            context["file_size_mb"] = round(Path(nwb_file_path).stat().st_size / (1024 * 1024), 2)

            # Quick scan of NWB file structure
            with h5py.File(nwb_file_path, "r") as f:
                # Check for subject info
                if "general/subject" in f:
                    context["has_subject_info"] = True

                # Check for devices
                if "general/devices" in f:
                    context["has_devices"] = True
                    context["device_count"] = len(f["general/devices"].keys())

                # Check for electrodes
                if "general/extracellular_ephys/electrodes" in f:
                    context["has_electrodes"] = True

                # Check acquisition types
                if "acquisition" in f:
                    context["acquisition_types"] = list(f["acquisition"].keys())[:5]

                # Check for common data interfaces
                if "general/intracellular_ephys" in f:
                    context["data_interfaces"].append("intracellular_ephys")
                if "general/extracellular_ephys" in f:
                    context["data_interfaces"].append("extracellular_ephys")
                if "general/optophysiology" in f:
                    context["data_interfaces"].append("optophysiology")

        except Exception:
            # If file reading fails, return basic context
            pass

        return context

    def _extract_basic_required_fields(
        self,
        validation_result: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Fallback method to extract basic required fields from validation issues.

        Used when LLM-based smart generation fails.

        Args:
            validation_result: Validation result with issues

        Returns:
            List of basic field definitions
        """
        fields = []
        seen_fields = set()

        metadata_keywords = {
            "experimenter": {
                "display_name": "Experimenter(s)",
                "description": "Name(s) of person(s) who performed the experiment",
                "field_type": "list",
                "example": '["Jane Doe", "John Smith"]',
            },
            "experiment description": {
                "display_name": "Experiment Description",
                "description": "Brief description of the experiment purpose and methodology",
                "field_type": "text",
                "example": "Recording of neural activity in mouse V1 during visual stimulation",
            },
            "institution": {
                "display_name": "Institution",
                "description": "Institution where experiment was performed",
                "field_type": "text",
                "example": "University of California, Berkeley",
            },
            "keywords": {
                "display_name": "Keywords",
                "description": "Searchable keywords describing the experiment",
                "field_type": "list",
                "example": '["electrophysiology", "mouse", "visual cortex"]',
            },
            "subject": {
                "display_name": "Subject Information",
                "description": "Information about experimental subject",
                "field_type": "nested",
                "example": '{"subject_id": "mouse001", "species": "Mus musculus", "age": "P90D"}',
            },
        }

        issues = validation_result.get("issues", [])
        for issue in issues:
            issue_msg = issue.get("message", "").lower()

            for keyword, field_info in metadata_keywords.items():
                if keyword in issue_msg and keyword not in seen_fields:
                    fields.append(
                        {
                            "field_name": keyword.replace(" ", "_"),
                            "display_name": field_info["display_name"],
                            "description": field_info["description"],
                            "field_type": field_info["field_type"],
                            "example": field_info["example"],
                        }
                    )
                    seen_fields.add(keyword)

        return fields
