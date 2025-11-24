"""Metadata collection and request generation.

Handles generating dynamic, context-aware metadata requests to users
and validating metadata completeness.
"""

import json
from typing import Any

from agentic_neurodata_conversion.agents.metadata.schema import NWBDANDISchema
from agentic_neurodata_conversion.models import GlobalState, LogLevel
from agentic_neurodata_conversion.services import LLMService


class MetadataCollector:
    """Generates intelligent metadata requests and validates completeness."""

    def __init__(self, llm_service: LLMService | None = None):
        """Initialize metadata collector.

        Args:
            llm_service: Optional LLM service for dynamic message generation
        """
        self._llm_service = llm_service

    async def generate_dynamic_metadata_request(
        self,
        missing_fields: list[str],
        inference_result: dict[str, Any],
        file_info: dict[str, Any],
        state: GlobalState,
    ) -> str:
        """Generate dynamic, file-specific metadata request using LLM.

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

            # Build summary of what we successfully inferred
            inferred_summary = []
            for key, value in inferred_metadata.items():
                conf = confidence_scores.get(key, 0)
                if conf >= 70:  # Only mention high-confidence inferences
                    inferred_summary.append({"field": key, "value": str(value), "confidence": conf})

            # Check conversation history to adapt the message
            conversation_context = ""
            request_count = state.metadata_requests_count
            recent_user_messages = [msg for msg in state.conversation_history if msg.get("role") == "user"]

            if request_count > 0 and recent_user_messages:
                conversation_context = f"""
**Previous Conversation Context:**
This is NOT the first time asking. Previous request count: {request_count}
Recent user responses: {json.dumps([msg.get("content", "")[:100] for msg in recent_user_messages[-2:]], indent=2)}

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
- Name: {file_info.get("name", "unknown")}
- Format: {file_info.get("format", "unknown")}
- Size: {file_info.get("size_mb", 0):.1f} MB

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
                        "description": "The personalized metadata request message (2-4 paragraphs max)",
                    },
                    "context_highlights": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key file details mentioned in the message",
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
                "Generated dynamic metadata request based on file analysis",
                {
                    "inferred_fields_count": len(inferred_summary),
                    "missing_fields_count": len(missing_fields),
                    "context_highlights": response.get("context_highlights", []),
                },
            )

            return str(response.get("message", ""))

        except Exception as e:
            state.add_log(
                LogLevel.WARNING,
                f"Failed to generate dynamic metadata request, using fallback: {e}",
            )
            # Fallback with some file context
            return f"""🔍 **File Analysis Complete**

I've analyzed your {file_info.get("format", "unknown")} file: `{file_info.get("name", "file")}`

To create a DANDI-compatible NWB file, I need:
{chr(10).join(f"• **{field.replace('_', ' ').title()}**" for field in missing_fields)}

Please provide these details, or say "skip for now" to proceed with minimal metadata."""

    async def generate_missing_metadata_message(
        self,
        missing_fields: list[str],
        metadata: dict[str, Any],
        state: GlobalState,
    ) -> str:
        """Generate user-friendly message for missing required metadata using LLM.

        Args:
            missing_fields: List of missing required fields
            metadata: Current metadata (what we have)
            state: Global state

        Returns:
            User-friendly message explaining what's needed
        """
        if not self._llm_service:
            return self._generate_fallback_missing_metadata_message(missing_fields)

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
            response = await self._llm_service.generate_completion(
                prompt=user_prompt,
                system_prompt=system_prompt,
            )
            return str(response)
        except Exception as e:
            state.add_log(LogLevel.WARNING, f"Failed to generate LLM metadata message, using fallback: {e}")
            return self._generate_fallback_missing_metadata_message(missing_fields)

    @staticmethod
    def _generate_fallback_missing_metadata_message(missing_fields: list[str]) -> str:
        """Generate basic message for missing metadata (fallback without LLM).

        Args:
            missing_fields: List of missing required fields

        Returns:
            Basic message explaining what's needed
        """
        field_descriptions = {
            # Session-level metadata
            "experimenter": "experimenter name(s) in DANDI format: 'LastName, FirstName'",
            "institution": "institution where experiment was performed",
            "experiment_description": "brief description of the experiment purpose and methods",
            "session_description": "brief description of this specific recording session",
            "session_start_time": "when the recording session started (ISO 8601 format: YYYY-MM-DDTHH:MM:SS±HH:MM)",
            # Subject-level metadata
            "subject_id": "unique identifier for the experimental subject",
            "species": "species of the subject (use scientific name, e.g., 'Mus musculus' for mouse)",
            "sex": "subject's sex (M/F/U)",
            "subject.sex": "subject's sex in subject metadata (M/F/U)",
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

    async def generate_metadata_review_message(
        self, metadata: dict[str, Any], format_name: str, state: GlobalState
    ) -> str:
        """Generate a metadata review message before starting conversion.

        Shows all collected metadata and asks if user wants to add anything.

        Args:
            metadata: Collected metadata
            format_name: Detected data format
            state: Global state

        Returns:
            Formatted review message
        """
        # Check for missing fields (but don't block conversion)
        is_valid, missing_fields = self.validate_required_nwb_metadata(metadata)

        if not self._llm_service:
            # Fallback message without LLM
            message = f"""## 📋 Metadata Review

**Format Detected:** {format_name}

**Metadata Collected:**
"""
            for key, value in metadata.items():
                if not key.startswith("_"):  # Skip internal fields
                    message += f"• **{key.replace('_', ' ').title()}**: {value}\n"

            if missing_fields:
                message += f"""

**Note:** Some recommended fields are missing: {", ".join(missing_fields)}
These are not required but would improve DANDI compatibility.
"""

            message += """

**Would you like to add any additional metadata before conversion?**

Options:
• Type any additional metadata you want to add
• Say "add [field]: [value]" to add specific fields
• Say "proceed" or "no" to start conversion with current metadata
"""
            return message

        try:
            # Use LLM for dynamic review message
            system_prompt = """You are helping review metadata before NWB conversion.
Generate a friendly, clear review message that:
1. Shows what metadata has been collected
2. Notes any missing recommended fields (without blocking)
3. Gives the option to add more metadata
4. Makes it clear they can proceed as-is"""

            # Format metadata for display
            metadata_summary = {}
            for key, value in metadata.items():
                if not key.startswith("_"):  # Skip internal fields
                    if isinstance(value, (list, dict)):
                        metadata_summary[key] = json.dumps(value)[:50] + "..."
                    else:
                        metadata_summary[key] = str(value)[:100]

            user_prompt = f"""Generate a metadata review message.

Format: {format_name}
Collected metadata: {json.dumps(metadata_summary, indent=2)}
Missing recommended fields: {missing_fields if missing_fields else "None"}

Create a clear, friendly message that:
1. Shows what we have
2. Notes missing fields (if any) as optional
3. Asks if they want to add anything before conversion
4. Makes it clear they can proceed as-is"""

            output_schema = {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]}

            response = await self._llm_service.generate_structured_output(
                prompt=user_prompt, output_schema=output_schema, system_prompt=system_prompt
            )

            return str(response.get("message", ""))

        except Exception as e:
            state.add_log(LogLevel.WARNING, f"Failed to generate review message, using fallback: {e}")
            return """## 📋 Metadata Review

**Metadata collected.** Would you like to add anything before conversion?

• Type additional metadata or say "proceed" to continue."""

    async def generate_custom_metadata_prompt(
        self, format_name: str, metadata: dict[str, Any], state: GlobalState
    ) -> str:
        """Generate a friendly prompt asking if user wants to add custom metadata.

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
            system_prompt = "You are helping collect custom metadata for neuroscience data conversion."

            user_prompt = f"""Generate a friendly message asking if the user wants to add custom metadata.

Format detected: {format_name}
Already collected: {", ".join(metadata.keys())}

Suggest relevant metadata they might want to add based on the file format.
Be encouraging about adding custom fields - anything they think is important.
Make it clear they can add ANY metadata, not just standard fields.
End with clear instructions on how to provide it or skip."""

            output_schema = {"type": "object", "properties": {"message": {"type": "string"}}, "required": ["message"]}

            response = await self._llm_service.generate_structured_output(
                prompt=user_prompt, output_schema=output_schema, system_prompt=system_prompt
            )

            return str(response.get("message", ""))

        except Exception as e:
            state.add_log(LogLevel.WARNING, f"Failed to generate custom prompt: {e}")
            return """## 🎯 Ready to Convert!

Would you like to add any custom metadata? Say "no" to proceed."""

    @staticmethod
    def validate_required_nwb_metadata(metadata: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate that all required NWB metadata fields are present BEFORE conversion.

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
