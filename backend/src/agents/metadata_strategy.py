"""Metadata Request Strategy with Priority-Based Questioning.

This module implements intelligent, priority-based metadata collection that:
1. Asks for CRITICAL fields first (required for DANDI)
2. Asks for RECOMMENDED fields sequentially (one at a time)
3. Offers OPTIONAL fields as a batch
4. Respects user's "skip" preferences at field and global levels
"""

import logging
from enum import Enum
from typing import Any

from models import GlobalState

logger = logging.getLogger(__name__)


class FieldPriority(str, Enum):
    """Priority levels for metadata fields."""

    CRITICAL = "critical"  # Must have for DANDI archive
    RECOMMENDED = "recommended"  # Strongly suggested
    OPTIONAL = "optional"  # Nice to have


class MetadataField:
    """Definition of a metadata field with priority and context."""

    def __init__(
        self,
        name: str,
        display_name: str,
        description: str,
        priority: FieldPriority,
        why_needed: str,
        example: str,
        field_type: str = "text",
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.priority = priority
        self.why_needed = why_needed
        self.example = example
        self.field_type = field_type


# Define all metadata fields with priorities
METADATA_FIELDS = {
    # CRITICAL: Required for DANDI archive submission
    "experimenter": MetadataField(
        name="experimenter",
        display_name="Experimenter Name(s)",
        description="Person(s) who performed the experiment",
        priority=FieldPriority.CRITICAL,
        why_needed="Required by DANDI for attribution and reproducibility",
        example='["Dr. Jane Smith", "Dr. John Doe"]',
        field_type="list",
    ),
    "institution": MetadataField(
        name="institution",
        display_name="Institution",
        description="Institution where experiment was performed",
        priority=FieldPriority.CRITICAL,
        why_needed="Required by DANDI for institutional affiliation",
        example="University of California, Berkeley",
        field_type="text",
    ),
    "experiment_description": MetadataField(
        name="experiment_description",
        display_name="Experiment Description",
        description="Brief description of the experiment",
        priority=FieldPriority.CRITICAL,
        why_needed="Required by DANDI to help others understand your data",
        example="Recording of neural activity in mouse V1 during visual stimulation",
        field_type="text",
    ),
    # RECOMMENDED: Strongly suggested for data quality
    "subject_id": MetadataField(
        name="subject_id",
        display_name="Subject ID",
        description="Unique identifier for the experimental subject",
        priority=FieldPriority.RECOMMENDED,
        why_needed="Helps track and organize data from multiple subjects",
        example="mouse_001",
        field_type="text",
    ),
    "species": MetadataField(
        name="species",
        display_name="Species",
        description="Species of the experimental subject",
        priority=FieldPriority.RECOMMENDED,
        why_needed="Critical biological context for interpreting results",
        example="Mus musculus (house mouse)",
        field_type="text",
    ),
    "session_description": MetadataField(
        name="session_description",
        display_name="Session Description",
        description="What happened in this recording session",
        priority=FieldPriority.RECOMMENDED,
        why_needed="Helps understand the experimental context",
        example="First training session with visual stimuli",
        field_type="text",
    ),
    # OPTIONAL: Nice to have for enhanced searchability
    "keywords": MetadataField(
        name="keywords",
        display_name="Keywords",
        description="Searchable keywords for this dataset",
        priority=FieldPriority.OPTIONAL,
        why_needed="Improves discoverability in data archives",
        example='["electrophysiology", "mouse", "visual cortex", "V1"]',
        field_type="list",
    ),
    "related_publications": MetadataField(
        name="related_publications",
        display_name="Related Publications",
        description="DOIs or URLs of related papers",
        priority=FieldPriority.OPTIONAL,
        why_needed="Links data to published research",
        example='["doi:10.1038/s41586-019-1234-5"]',
        field_type="list",
    ),
    "session_id": MetadataField(
        name="session_id",
        display_name="Session ID",
        description="Internal identifier for this session",
        priority=FieldPriority.OPTIONAL,
        why_needed="Useful for internal lab tracking",
        example="session_20250116_001",
        field_type="text",
    ),
}


class MetadataRequestStrategy:
    """Intelligent metadata request strategy combining priority-based and sequential approaches.

    Flow:
    1. Ask for CRITICAL fields as a batch (with option to go sequential)
    2. Ask for RECOMMENDED fields one at a time (sequential)
    3. Offer OPTIONAL fields as a batch
    4. Respect field-level and global skip preferences
    """

    def __init__(self, llm_service=None, state: GlobalState | None = None):
        self._current_phase: str | None = None
        self._current_field_index: int = 0
        self.llm_service = llm_service
        self.state = state

    def get_next_request(
        self,
        state: GlobalState,
        validation_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Determine the next metadata request based on current state and priorities.

        Args:
            state: Global conversion state
            validation_result: Validation result with issues

        Returns:
            Dict with next action and message
        """
        # Extract missing fields from validation
        missing_fields = self._extract_missing_fields(validation_result)

        # Filter out already declined fields
        available_fields = [f for f in missing_fields if f not in state.user_declined_fields]

        if not available_fields:
            # Nothing left to ask
            return {"action": "proceed", "message": None}

        # Determine current phase
        critical = self._filter_by_priority(available_fields, FieldPriority.CRITICAL)
        recommended = self._filter_by_priority(available_fields, FieldPriority.RECOMMENDED)
        optional = self._filter_by_priority(available_fields, FieldPriority.OPTIONAL)

        # Phase 1: Critical fields (batch)
        if critical:
            return self._request_critical_batch(critical, state)

        # Phase 2: Recommended fields (sequential)
        if recommended:
            return self._request_next_recommended(recommended, state)

        # Phase 3: Optional fields (offer as batch)
        if optional:
            return self._offer_optional_batch(optional, state)

        # All done
        return {"action": "proceed", "message": None}

    def _request_critical_batch(
        self,
        critical_fields: list[str],
        state: GlobalState,
    ) -> dict[str, Any]:
        """Request critical fields (batch or sequential based on user preference)."""
        # Defensive check: ensure critical_fields is not empty
        if not critical_fields:
            return {"action": "proceed", "message": None}

        # If user wants sequential mode, ask one at a time
        if state.user_wants_sequential:
            next_field_name = critical_fields[0]
            field = METADATA_FIELDS[next_field_name]

            remaining = len(critical_fields) - 1
            progress = f"(critical {len(critical_fields) - remaining}/{len(critical_fields)})"

            message = f"""🔴 **{field.display_name}** {progress}

{field.why_needed}

Example: `{field.example}`

You can:
• Provide the information
• Say "skip" to skip just this field (warning: file won't be DANDI-compatible)
• Say "skip all" to skip all remaining questions"""

            return {
                "action": "ask_field",
                "phase": "critical",
                "field": next_field_name,
                "message": message,
                "can_skip": False,  # Warn if skipped
                "priority": "critical",
                "remaining": remaining,
            }

        # Otherwise, ask as batch (default behavior)
        fields_info = [METADATA_FIELDS[f] for f in critical_fields]

        fields_list = "\n".join(
            [f"• **{field.display_name}**: {field.why_needed}\n  Example: {field.example}" for field in fields_info]
        )

        message = f"""🔴 **Critical Information Needed**

To create a DANDI-compatible NWB file, I need {len(critical_fields)} essential field{"s" if len(critical_fields) > 1 else ""}:

{fields_list}

**How would you like to proceed?**
• Provide all at once (e.g., "Dr. Smith, MIT, recording neural activity")
• Answer one by one (say "ask one by one")
• Skip for now (file won't be DANDI-compatible)"""

        return {
            "action": "ask_batch",
            "phase": "critical",
            "fields": critical_fields,
            "message": message,
            "can_skip": False,  # Warn if skipped
            "priority": "critical",
        }

    def _request_next_recommended(
        self,
        recommended_fields: list[str],
        state: GlobalState,
    ) -> dict[str, Any]:
        """Request the next recommended field sequentially."""
        # Defensive check: ensure recommended_fields is not empty
        if not recommended_fields:
            return {"action": "proceed", "message": None}

        next_field_name = recommended_fields[0]
        field = METADATA_FIELDS[next_field_name]

        remaining = len(recommended_fields) - 1
        progress = (
            f"({len(state.user_declined_fields) + 1} of {len(recommended_fields)} recommended fields)"
            if remaining > 0
            else "(last recommended field)"
        )

        message = f"""💡 **{field.display_name}** {progress}

{field.why_needed}

Example: `{field.example}`

You can:
• Provide the information
• Say "skip" to skip just this field
• Say "skip all" to skip all remaining questions"""

        return {
            "action": "ask_field",
            "phase": "recommended",
            "field": next_field_name,
            "message": message,
            "can_skip": True,
            "priority": "recommended",
            "remaining": remaining,
        }

    def _offer_optional_batch(
        self,
        optional_fields: list[str],
        state: GlobalState,
    ) -> dict[str, Any]:
        """Offer optional fields as a batch with easy skip."""
        fields_info = [METADATA_FIELDS[f] for f in optional_fields]

        fields_list = "\n".join([f"• **{field.display_name}**: {field.description}" for field in fields_info])

        message = f"""✨ **Optional Enhancements**

Great! I have all the essential information. I can also add these optional fields to improve searchability:

{fields_list}

Would you like to add any of these? (You can say "skip" to proceed with conversion)"""

        return {
            "action": "offer_optional",
            "phase": "optional",
            "fields": optional_fields,
            "message": message,
            "can_skip": True,
            "priority": "optional",
        }

    def _extract_missing_fields(
        self,
        validation_result: dict[str, Any],
    ) -> list[str]:
        """Extract missing field names from validation issues."""
        missing = []

        issues = validation_result.get("issues", [])
        for issue in issues:
            issue_msg = issue.get("message", "").lower()

            # Check each known field
            for field_name in METADATA_FIELDS:
                # Match field name or variations
                field_variations = [
                    field_name,
                    field_name.replace("_", " "),
                    METADATA_FIELDS[field_name].display_name.lower(),
                ]

                if any(variation in issue_msg for variation in field_variations):
                    if field_name not in missing:
                        missing.append(field_name)

        return missing

    def _filter_by_priority(
        self,
        field_names: list[str],
        priority: FieldPriority,
    ) -> list[str]:
        """Filter fields by priority level."""
        return [name for name in field_names if name in METADATA_FIELDS and METADATA_FIELDS[name].priority == priority]

    async def detect_skip_type_with_llm(self, user_message: str, conversation_context: str = "") -> str:
        """Use LLM to intelligently detect user's intent for skipping metadata questions.

        This is much more robust than keyword matching and can understand:
        - Natural language variations ("maybe later", "not right now")
        - Context-aware responses
        - Subtle differences between skipping one field vs all fields

        Args:
            user_message: User's response
            conversation_context: Recent conversation for context

        Returns:
            "field" - Skip just this one field
            "global" - Skip all remaining questions
            "sequential" - User wants one-by-one questions
            "none" - Not a skip message (user is providing data or asking a question)
        """
        if not self.llm_service:
            # Fallback to keyword-based detection if no LLM available
            return self.detect_skip_type(user_message)

        try:
            system_prompt = """You are an expert at understanding user intent in conversational interfaces.

Your task is to analyze user responses when they're being asked for metadata (like experimenter name, institution, description).

Classify their intent into one of these categories:

1. **"global"** - User wants to skip ALL remaining metadata questions and proceed with conversion
   Examples:
   - "skip for now" → global (wants to skip all questions now)
   - "just proceed" → global (wants to move forward without answering)
   - "do it without metadata" → global (explicitly skipping all)
   - "I'll add that later" → global (deferring all questions)
   - "not right now" → global (temporal skip of all questions)
   - "maybe later" → global (uncertain but wants to proceed)

2. **"field"** - User wants to skip ONLY this specific field but might answer others
   Examples:
   - "skip this one" → field (specifically this field)
   - "not this field" → field (just this one)
   - "I don't have that" → field (missing this specific info)
   - "pass on this" → field (skip this particular question)
   - "skip" → field (simple skip without "all" or "for now")
   - "don't know" → field (can't answer this one)

3. **"sequential"** - User wants to answer questions one-by-one instead of all at once
   Examples:
   - "ask one by one" → sequential (explicit request)
   - "one at a time" → sequential (wants individual questions)
   - "ask separately" → sequential (wants separate questions)
   - "ask individually" → sequential (wants step-by-step)

4. **"none"** - User is NOT trying to skip - they're providing data or asking a question
   Examples:
   - "John Smith, MIT, mouse recording" → none (providing data)
   - "what is institution?" → none (asking clarification)
   - "can you explain?" → none (needs help)
   - "Dr. Smith performed the experiment" → none (answering question)

**Reasoning approach:**
1. Check for explicit "all" or "everything" keywords → likely global
2. Check for "for now" or "later" → likely global (temporal deferral)
3. Check for "this" or "this one" with skip → likely field (specific)
4. Check for question words (what, how, why) → likely none (asking question)
5. Check for name-like patterns, dates, institutions → likely none (providing data)
6. Check for "one by one" or "separately" → sequential

Respond with ONLY the category name: "global", "field", "sequential", or "none"."""

            user_prompt = f"""User message: "{user_message}"

Context (if available): {conversation_context or "No prior context"}

What is the user's intent? Respond with exactly one word: global, field, sequential, or none."""

            output_schema = {
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "enum": ["global", "field", "sequential", "none"],
                        "description": "User's intent category",
                    },
                    "confidence": {"type": "number", "description": "Confidence level 0-100"},
                    "reasoning": {"type": "string", "description": "Brief explanation of classification"},
                },
                "required": ["intent", "confidence"],
            }

            response = await self.llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            intent = response.get("intent", "none")
            confidence = response.get("confidence", 0)
            reasoning = response.get("reasoning", "")

            # Log the LLM's decision for debugging
            logger.debug(f"LLM skip detection: intent={intent}, confidence={confidence}%, reasoning={reasoning}")

            # DETAILED DEBUG LOGGING to state logs
            if self.state:
                from models.state import LogLevel

                self.state.add_log(
                    LogLevel.INFO,
                    "LLM intent detection result",
                    {
                        "intent": intent,
                        "confidence": confidence,
                        "reasoning": reasoning[:200] if reasoning else "",
                        "user_message": user_message[:100],
                    },
                )

            # If confidence is low, fall back to keyword matching
            if confidence < 60:
                fallback = self.detect_skip_type(user_message)
                logger.debug(f"Low confidence ({confidence}%), using keyword fallback: {fallback}")
                if self.state:
                    self.state.add_log(
                        LogLevel.INFO,
                        f"Low LLM confidence ({confidence}%), using keyword fallback",
                        {"llm_intent": intent, "fallback_intent": fallback},
                    )
                return fallback

            return str(intent)  # Cast Any to str

        except Exception as e:
            logger.warning(f"LLM skip detection failed: {e}, falling back to keywords")
            return self.detect_skip_type(user_message)

    def detect_skip_type(self, user_message: str) -> str:
        """Keyword-based skip detection (fallback when LLM is unavailable).

        Returns:
            "field" - Skip just this one field
            "global" - Skip all remaining questions
            "sequential" - User wants one-by-one questions (for batch requests)
            "none" - Not a skip message
        """
        if not user_message:
            return "none"

        message_lower = user_message.lower()

        # Check for "ask one by one" / "sequential" request
        sequential_keywords = [
            "ask one by one",
            "one by one",
            "ask separately",
            "one at a time",
            "ask individually",
            "sequential",
        ]
        if any(kw in message_lower for kw in sequential_keywords):
            return "sequential"

        # Global skip phrases (stop ALL questions)
        # NOTE: These are checked BEFORE field-level skips, so add specific phrases here
        global_keywords = [
            "skip all",
            "skip everything",
            "skip remaining",
            "stop asking",
            "no more questions",
            "just proceed",
            "go ahead",
            "skip asking questions",
            "don't ask anymore",
            "skip the rest",
            "proceed without",
            "skip for now",
            "skip it for now",
            "skip this for now",
            "maybe later",
            "not right now",
            "I'll add that later",
        ]
        if any(kw in message_lower for kw in global_keywords):
            return "global"

        # Field-level skip (just this one question)
        field_keywords = [
            "skip",
            "skip it",
            "skip this",
            "no",
            "nope",
            "i don't have",
            "not available",
            "don't have that",
            "not needed",
            "not now",
            "pass",
        ]
        if any(kw in message_lower for kw in field_keywords):
            return "field"

        return "none"
