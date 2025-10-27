"""
Intelligent Metadata Parser with Natural Language Understanding

Accepts user input in natural language and converts to NWB/DANDI-compliant formats
with confidence-based auto-application when user skips confirmation.
"""
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime
import re

from models import GlobalState, LogLevel
from services import LLMService
from agents.nwb_dandi_schema import NWBDANDISchema, MetadataFieldSchema


class ConfidenceLevel(str, Enum):
    """Confidence level for parsed metadata."""
    HIGH = "high"      # ≥80% - Auto-apply silently
    MEDIUM = "medium"  # 50-79% - Auto-apply with note
    LOW = "low"        # <50% - Auto-apply with warning flag


class ParsedField:
    """Represents a parsed metadata field with confidence."""

    def __init__(
        self,
        field_name: str,
        raw_input: str,
        parsed_value: Any,
        confidence: float,
        reasoning: str,
        nwb_compliant: bool,
        needs_review: bool = False,
        alternatives: Optional[List[str]] = None,
    ):
        self.field_name = field_name
        self.raw_input = raw_input
        self.parsed_value = parsed_value
        self.confidence = confidence
        self.reasoning = reasoning
        self.nwb_compliant = nwb_compliant
        self.needs_review = needs_review
        self.alternatives = alternatives or []

    @property
    def confidence_level(self) -> ConfidenceLevel:
        """Get confidence level category."""
        if self.confidence >= 80:
            return ConfidenceLevel.HIGH
        elif self.confidence >= 50:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "field_name": self.field_name,
            "raw_input": self.raw_input,
            "parsed_value": self.parsed_value,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level.value,
            "reasoning": self.reasoning,
            "nwb_compliant": self.nwb_compliant,
            "needs_review": self.needs_review,
            "alternatives": self.alternatives,
        }


class IntelligentMetadataParser:
    """
    Parse natural language metadata input and normalize to NWB/DANDI formats.

    Features:
    - Natural language understanding
    - Schema-driven validation
    - Confidence-based auto-application
    - Piece-by-piece or batch processing
    - User confirmation with edit capability
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm_service = llm_service
        self.schema = NWBDANDISchema()
        self.field_schemas = {
            field.name: field
            for field in self.schema.get_all_fields()
        }

    async def parse_natural_language_batch(
        self,
        user_input: str,
        state: GlobalState,
    ) -> List[ParsedField]:
        """
        Parse natural language input containing multiple metadata fields.

        Example inputs:
        - "I'm Dr. Jane Smith from MIT studying 8 week old mice"
        - "experimenter: John Doe, institution: Stanford, subject: male mouse"

        Args:
            user_input: Natural language text from user
            state: Global state for logging

        Returns:
            List of ParsedField objects
        """
        if not self.llm_service:
            # Fallback to simple pattern matching
            return self._fallback_parse_batch(user_input, state)

        state.add_log(
            LogLevel.INFO,
            "Parsing natural language metadata input with LLM",
        )

        # Build schema context for LLM
        schema_context = self._build_schema_context()

        system_prompt = f"""You are an expert at extracting neuroscience metadata from natural language.

Your job is to:
1. Identify all metadata fields mentioned in the user's text
2. Extract their values
3. Normalize to NWB/DANDI-compliant formats
4. Provide confidence scores (0-100)

Available fields and their formats:
{schema_context}

Important normalization rules:
- Experimenter: "LastName, FirstName" format (e.g., "Smith, Jane")
- Institution: Full official name (expand abbreviations like MIT → Massachusetts Institute of Technology)
- Age: ISO 8601 duration format (e.g., "P56D" for 8 weeks, "P90D" for 90 days)
- Sex: Single letter code ("M", "F", "U" for unknown)
- Species: Scientific name (e.g., "Mus musculus" for mouse, "Rattus norvegicus" for rat)

Be conservative with confidence:
- High (80-100): Explicitly stated, clear format
- Medium (50-79): Implied or needs minor interpretation
- Low (0-49): Vague, ambiguous, or guessed
"""

        user_prompt = f"""Extract all metadata fields from this text:

"{user_input}"

For each field found, provide:
1. Field name (exact match from schema)
2. Raw value from text
3. Normalized NWB/DANDI-compliant value
4. Confidence score (0-100)
5. Reasoning for your interpretation
6. Whether review is needed
"""

        output_schema = {
            "type": "object",
            "properties": {
                "fields": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "field_name": {"type": "string"},
                            "raw_value": {"type": "string"},
                            "normalized_value": {
                                "oneOf": [
                                    {"type": "string"},
                                    {"type": "array", "items": {"type": "string"}},
                                    {"type": "number"}
                                ]
                            },
                            "confidence": {"type": "number"},
                            "reasoning": {"type": "string"},
                            "needs_review": {"type": "boolean"},
                            "alternatives": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["field_name", "raw_value", "normalized_value", "confidence", "reasoning"]
                    }
                }
            },
            "required": ["fields"]
        }

        try:
            response = await self.llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            parsed_fields = []
            for field_data in response.get("fields", []):
                parsed_field = ParsedField(
                    field_name=field_data["field_name"],
                    raw_input=field_data["raw_value"],
                    parsed_value=field_data["normalized_value"],
                    confidence=field_data["confidence"],
                    reasoning=field_data["reasoning"],
                    nwb_compliant=True,  # LLM should provide compliant values
                    needs_review=field_data.get("needs_review", False),
                    alternatives=field_data.get("alternatives", []),
                )
                parsed_fields.append(parsed_field)

                state.add_log(
                    LogLevel.INFO,
                    f"Parsed {parsed_field.field_name}: '{parsed_field.raw_input}' → '{parsed_field.parsed_value}' "
                    f"(confidence: {parsed_field.confidence}%)",
                )

            return parsed_fields

        except Exception as e:
            state.add_log(
                LogLevel.WARNING,
                f"LLM parsing failed, using fallback: {e}",
            )
            return self._fallback_parse_batch(user_input, state)

    async def parse_single_field(
        self,
        field_name: str,
        user_input: str,
        state: GlobalState,
    ) -> ParsedField:
        """
        Parse a single metadata field from user input.

        Example:
        - Field: "age", Input: "8 weeks old" → "P56D"
        - Field: "experimenter", Input: "Dr. Jane Smith" → "Smith, Jane"

        Args:
            field_name: The metadata field name
            user_input: User's input for this field
            state: Global state

        Returns:
            ParsedField object
        """
        if not self.llm_service:
            return self._fallback_parse_single(field_name, user_input, state)

        # Get schema for this field
        field_schema = self.field_schemas.get(field_name)
        if not field_schema:
            state.add_log(
                LogLevel.WARNING,
                f"Unknown field: {field_name}",
            )
            return ParsedField(
                field_name=field_name,
                raw_input=user_input,
                parsed_value=user_input,
                confidence=50,
                reasoning="Unknown field, using raw input",
                nwb_compliant=False,
            )

        system_prompt = f"""You are an expert at normalizing neuroscience metadata to NWB/DANDI standards.

Field: {field_schema.name}
Description: {field_schema.description}
Expected format: {field_schema.format or field_schema.field_type.value}
Example: {field_schema.example}

Normalization rules:
{self._get_normalization_rules(field_schema)}

Provide a confidence score (0-100) based on:
- High (80-100): Clear, unambiguous input matching expected format
- Medium (50-79): Requires interpretation or minor assumptions
- Low (0-49): Vague, ambiguous, or requires significant guessing
"""

        user_prompt = f"""Normalize this user input for the '{field_name}' field:

User input: "{user_input}"

Provide:
1. Normalized NWB/DANDI-compliant value
2. Confidence score (0-100)
3. Reasoning for your normalization
4. Whether this needs user review
5. Alternative interpretations (if any)
"""

        output_schema = {
            "type": "object",
            "properties": {
                "normalized_value": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}},
                        {"type": "number"}
                    ]
                },
                "confidence": {"type": "number"},
                "reasoning": {"type": "string"},
                "needs_review": {"type": "boolean"},
                "alternatives": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["normalized_value", "confidence", "reasoning"]
        }

        try:
            response = await self.llm_service.generate_structured_output(
                prompt=user_prompt,
                output_schema=output_schema,
                system_prompt=system_prompt,
            )

            parsed_field = ParsedField(
                field_name=field_name,
                raw_input=user_input,
                parsed_value=response["normalized_value"],
                confidence=response["confidence"],
                reasoning=response["reasoning"],
                nwb_compliant=True,
                needs_review=response.get("needs_review", False),
                alternatives=response.get("alternatives", []),
            )

            state.add_log(
                LogLevel.INFO,
                f"Parsed {field_name}: '{user_input}' → '{parsed_field.parsed_value}' "
                f"(confidence: {parsed_field.confidence}%)",
            )

            return parsed_field

        except Exception as e:
            state.add_log(
                LogLevel.WARNING,
                f"LLM parsing failed for {field_name}, using fallback: {e}",
            )
            return self._fallback_parse_single(field_name, user_input, state)

    def generate_confirmation_message(
        self,
        parsed_fields: List[ParsedField],
    ) -> str:
        """
        Generate user-friendly confirmation message showing parsed results.

        Args:
            parsed_fields: List of parsed fields

        Returns:
            Formatted confirmation message
        """
        lines = ["I understood the following from your input:\n"]

        for field in parsed_fields:
            # Confidence indicator
            if field.confidence >= 80:
                indicator = "✓"
            elif field.confidence >= 50:
                indicator = "⚠️"
            else:
                indicator = "❓"

            # Format the field
            lines.append(
                f"{indicator} **{field.field_name}** = {self._format_value(field.parsed_value)}"
            )

            # Show original if different
            if str(field.parsed_value) != field.raw_input:
                lines.append(f"   (from: \"{field.raw_input}\")")

            # Show confidence and reasoning for non-high confidence
            if field.confidence < 80:
                lines.append(f"   Confidence: {field.confidence}% - {field.reasoning}")

            # Show alternatives if available
            if field.alternatives:
                lines.append(f"   Alternatives: {', '.join(field.alternatives)}")

            lines.append("")

        # Add instructions
        lines.append("\n**What would you like to do?**")
        lines.append("- Press Enter or say 'yes' to accept all")
        lines.append("- Type the field name and new value to correct (e.g., 'age: P90D')")
        lines.append("- Say 'edit' to review each field individually")

        return "\n".join(lines)

    async def apply_with_best_knowledge(
        self,
        parsed_field: ParsedField,
        state: GlobalState,
    ) -> Any:
        """
        Apply metadata using best knowledge when user skips confirmation.

        Three-tier approach:
        - High confidence (≥80%): Apply silently
        - Medium confidence (50-79%): Apply with note
        - Low confidence (<50%): Apply with warning flag

        Args:
            parsed_field: The parsed field
            state: Global state

        Returns:
            The value to apply
        """
        field_name = parsed_field.field_name
        value = parsed_field.parsed_value
        confidence = parsed_field.confidence

        # High confidence: Silent auto-apply
        if confidence >= 80:
            state.add_log(
                LogLevel.INFO,
                f"✓ Auto-applied {field_name} = {self._format_value(value)} "
                f"(high confidence: {confidence}%)",
            )
            return value

        # Medium confidence: Apply with note
        elif confidence >= 50:
            state.add_log(
                LogLevel.WARNING,
                f"⚠️ Auto-applied {field_name} = {self._format_value(value)} "
                f"(medium confidence: {confidence}% - best guess)",
                {"confidence": confidence, "reasoning": parsed_field.reasoning},
            )
            return value

        # Low confidence: Apply with warning flag
        else:
            state.add_log(
                LogLevel.WARNING,
                f"❓ Auto-applied {field_name} = {self._format_value(value)} "
                f"(LOW confidence: {confidence}% - NEEDS REVIEW)",
                {"needs_review": True, "confidence": confidence},
            )

            # Add to metadata warnings for validation report
            if not hasattr(state, 'metadata_warnings'):
                state.metadata_warnings = {}

            state.metadata_warnings[field_name] = {
                "value": value,
                "confidence": confidence,
                "original_input": parsed_field.raw_input,
                "warning": "Low confidence parsing - please review before DANDI submission",
                "alternatives": parsed_field.alternatives,
            }

            return value

    def _build_schema_context(self) -> str:
        """Build schema context for LLM."""
        lines = []
        for field in self.schema.get_all_fields():
            lines.append(
                f"- {field.name} ({field.requirement_level.value}): "
                f"{field.description}\n  Format: {field.format or field.field_type.value}\n  "
                f"Example: {field.example}"
            )
        return "\n".join(lines)

    def _get_normalization_rules(self, field_schema: MetadataFieldSchema) -> str:
        """Get normalization rules for a field."""
        rules = []

        if field_schema.normalization_rules:
            rules.append("Common mappings:")
            for key, value in field_schema.normalization_rules.items():
                rules.append(f"  '{key}' → '{value}'")

        if field_schema.allowed_values:
            rules.append(f"Allowed values: {', '.join(field_schema.allowed_values)}")

        return "\n".join(rules) if rules else "No special rules"

    def _format_value(self, value: Any) -> str:
        """Format value for display."""
        if isinstance(value, list):
            return f"[{', '.join(repr(v) for v in value)}]"
        return repr(value)

    def _fallback_parse_batch(
        self,
        user_input: str,
        state: GlobalState,
    ) -> List[ParsedField]:
        """Fallback parser using regex patterns (no LLM)."""
        parsed_fields = []

        # Simple key:value pattern matching
        pattern = r'(\w+)\s*[:=]\s*([^,\n]+)'
        matches = re.findall(pattern, user_input)

        for field_name, value in matches:
            field_name = field_name.lower().strip()
            value = value.strip()

            parsed_field = self._fallback_parse_single(field_name, value, state)
            parsed_fields.append(parsed_field)

        return parsed_fields

    def _fallback_parse_single(
        self,
        field_name: str,
        user_input: str,
        state: GlobalState,
    ) -> ParsedField:
        """Fallback parser for single field (no LLM)."""
        # Apply basic normalization rules
        field_schema = self.field_schemas.get(field_name)

        if not field_schema:
            return ParsedField(
                field_name=field_name,
                raw_input=user_input,
                parsed_value=user_input,
                confidence=50,
                reasoning="No schema found, using raw input",
                nwb_compliant=False,
            )

        # Apply normalization rules if available
        normalized_value = field_schema.normalization_rules.get(user_input, user_input)

        # Simple heuristic confidence
        confidence = 90 if normalized_value != user_input else 60

        return ParsedField(
            field_name=field_name,
            raw_input=user_input,
            parsed_value=normalized_value,
            confidence=confidence,
            reasoning="Pattern-based normalization (no LLM)",
            nwb_compliant=True,
        )
