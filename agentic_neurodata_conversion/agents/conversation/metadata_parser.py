"""Metadata parsing and validation.

Handles extracting metadata from user messages, validating formats,
and processing custom metadata input.
"""

import re
from typing import Any

from agentic_neurodata_conversion.agents.metadata.intelligent_mapper import IntelligentMetadataMapper
from agentic_neurodata_conversion.agents.metadata.schema import NWBDANDISchema
from agentic_neurodata_conversion.agents.utils.conversational_handler import ConversationalHandler
from agentic_neurodata_conversion.models import GlobalState, LogLevel


class MetadataParser:
    """Parses and validates metadata from user input."""

    def __init__(
        self,
        conversational_handler: ConversationalHandler | None = None,
        metadata_mapper: IntelligentMetadataMapper | None = None,
    ):
        """Initialize metadata parser.

        Args:
            conversational_handler: Optional conversational handler for LLM parsing
            metadata_mapper: Optional metadata mapper for custom metadata
        """
        self._conversational_handler = conversational_handler
        self._metadata_mapper = metadata_mapper

    async def extract_metadata_from_message(self, user_message: str, state: GlobalState) -> dict[str, Any]:
        """Extract metadata from user's message using intelligent parsing.

        Args:
            user_message: User's message
            state: Global state

        Returns:
            Extracted metadata dictionary
        """
        extracted_metadata = {}

        if self._conversational_handler:
            # Use LLM to extract metadata
            context = {
                "conversation_history": state.conversation_history[-3:],
                "expected_fields": [f.name for f in NWBDANDISchema.get_required_fields()],
            }

            response = await self._conversational_handler.process_user_response(
                user_message=user_message,
                context=context,
                state=state,
            )

            extracted_metadata = response.get("extracted_metadata", {})

        else:
            # Fallback to simple pattern matching
            # Pattern for "field: value" format
            pattern = r"(\w+)\s*[:=]\s*(.+?)(?=\w+\s*[:=]|$)"
            matches = re.findall(pattern, user_message)
            for field, value in matches:
                field = field.lower().replace(" ", "_")
                extracted_metadata[field] = value.strip()

        return extracted_metadata

    def validate_metadata_format(self, metadata: dict[str, Any]) -> dict[str, str]:
        """Validate metadata format and return any errors.

        Args:
            metadata: Metadata to validate

        Returns:
            Dictionary of field -> error message
        """
        errors = {}

        for field, value in metadata.items():
            # Get field schema
            field_schema = NWBDANDISchema.get_field_by_name(field)
            if not field_schema:
                continue

            # Validate based on field type
            if field_schema.field_type.value == "date":
                # Check if it's a valid date format
                if not self._is_valid_date_format(value):
                    errors[field] = (
                        "Please provide date in ISO format (YYYY-MM-DDTHH:MM:SS) "
                        "or natural language like 'August 15, 2025 at 10am'"
                    )

            elif field == "sex" and value not in ["M", "F", "U"]:
                errors[field] = "Please use 'M' for male, 'F' for female, or 'U' for unknown"

            elif field == "experimenter" and "," not in str(value):
                errors[field] = "Please use format 'LastName, FirstName'"

            elif field == "species" and not any(
                species in str(value).lower()
                for species in ["mus musculus", "rattus norvegicus", "homo sapiens", "macaca"]
            ):
                errors[field] = (
                    "Please use scientific name (e.g., 'Mus musculus' for mouse, 'Rattus norvegicus' for rat)"
                )

        return errors

    @staticmethod
    def _is_valid_date_format(value: str) -> bool:
        """Check if a date string is in valid format.

        Args:
            value: Date string to check

        Returns:
            True if valid format
        """
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

    async def handle_custom_metadata_response(self, user_input: str, state: GlobalState) -> dict[str, Any]:
        """Process user's custom metadata input using intelligent mapping.

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
                user_input=user_input, existing_metadata=state.metadata, state=state
            )

            # The response contains parsed standard and custom fields
            state.add_log(
                LogLevel.INFO,
                "Processed custom metadata",
                {
                    "standard_fields_count": len(parsed_metadata.get("standard_fields", {})),
                    "custom_fields_count": len(parsed_metadata.get("custom_fields", {})),
                },
            )

            return dict(parsed_metadata)

        except Exception as e:
            state.add_log(LogLevel.ERROR, f"Failed to parse custom metadata: {e}")
            return {}
