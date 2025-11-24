"""Conversion helper utilities module.

Handles:
- Metadata structure mapping (flat to nested NWB format)
- File checksums (SHA256)
- Progress narration (LLM-powered)
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agentic_neurodata_conversion.services.llm_service import LLMService

from agentic_neurodata_conversion.models import GlobalState, LogLevel
from agentic_neurodata_conversion.utils.file_versioning import compute_sha256

logger = logging.getLogger(__name__)


class ConversionHelpers:
    """Utility functions for conversion operations."""

    def __init__(self, llm_service: "LLMService | None" = None):
        """Initialize conversion helpers.

        Args:
            llm_service: Optional LLM service for progress narration
        """
        self._llm_service = llm_service

    @staticmethod
    def map_flat_to_nested_metadata(flat_metadata: dict[str, Any]) -> dict[str, Any]:
        """Map flat user-provided metadata to NWB's nested structure.

        User provides metadata like:
            {"experimenter": "Dr. Smith", "institution": "MIT", "subject_id": "mouse001"}

        NWB expects nested structure like:
            {
                "NWBFile": {
                    "experimenter": ["Dr. Smith"],
                    "institution": "MIT",
                    "session_description": "...",
                    "experiment_description": "...",
                    "keywords": [...]
                },
                "Subject": {
                    "subject_id": "mouse001",
                    "species": "Mus musculus",
                    "age": "P90D"
                }
            }

        Args:
            flat_metadata: Flat metadata dictionary from user

        Returns:
            Nested metadata dictionary matching NWB structure
        """
        # Define the mapping from flat field names to NWB nested structure
        NWBFILE_FIELDS = {
            "experimenter",
            "institution",
            "session_description",
            "experiment_description",
            "keywords",
            "related_publications",
            "session_id",
            "lab",
            "protocol",
            "notes",
        }

        SUBJECT_FIELDS = {
            "subject_id",
            "species",
            "age",
            "sex",
            "description",
            "weight",
            "strain",
            "genotype",
        }

        nested: dict[str, dict[str, Any]] = {}

        # Process standard fields
        for key, value in flat_metadata.items():
            # Skip internal metadata fields
            if key.startswith("_"):
                continue

            if key in NWBFILE_FIELDS:
                if "NWBFile" not in nested:
                    nested["NWBFile"] = {}

                # Handle list fields that NWB expects as lists
                if key in ["experimenter", "keywords", "related_publications"]:
                    # If user provided a string, convert to list
                    if isinstance(value, str):
                        nested["NWBFile"][key] = [value]
                    elif isinstance(value, list):
                        nested["NWBFile"][key] = value
                    else:
                        nested["NWBFile"][key] = [str(value)]
                else:
                    nested["NWBFile"][key] = value

            elif key in SUBJECT_FIELDS:
                if "Subject" not in nested:
                    nested["Subject"] = {}
                nested["Subject"][key] = value

            else:
                # Unknown field - try to place it in NWBFile as a fallback
                if "NWBFile" not in nested:
                    nested["NWBFile"] = {}
                nested["NWBFile"][key] = value

        # Process custom fields if present
        if "_custom_fields" in flat_metadata:
            custom_fields = flat_metadata["_custom_fields"]

            # Create a custom namespace for user-defined fields
            if custom_fields:
                if "NWBFile" not in nested:
                    nested["NWBFile"] = {}

                # Store custom fields in notes or as separate entries
                # NWB allows arbitrary fields in the file
                for custom_key, custom_value in custom_fields.items():
                    # Clean the key name to be NWB-compliant
                    clean_key = custom_key.replace(" ", "_").lower()

                    # Try to intelligently place custom fields
                    if any(term in clean_key for term in ["subject", "animal", "mouse", "rat"]):
                        # Subject-related custom field
                        if "Subject" not in nested:
                            nested["Subject"] = {}
                        nested["Subject"][clean_key] = custom_value
                    else:
                        # General custom field - add to NWBFile
                        nested["NWBFile"][clean_key] = custom_value

                # Also store a summary of custom fields in notes for documentation
                if custom_fields:
                    custom_summary = "Custom metadata fields:\n"
                    for k, v in custom_fields.items():
                        custom_summary += f"  - {k}: {v}\n"

                    existing_notes = nested["NWBFile"].get("notes", "")
                    if existing_notes:
                        nested["NWBFile"]["notes"] = f"{existing_notes}\n\n{custom_summary}"
                    else:
                        nested["NWBFile"]["notes"] = custom_summary

        return nested

    @staticmethod
    def calculate_checksum(file_path: str) -> str:
        """Calculate SHA256 checksum of a file.

        Used for file verification and integrity checking.

        Args:
            file_path: Path to file

        Returns:
            SHA256 hex digest
        """
        result = compute_sha256(Path(file_path))
        return str(result)

    async def narrate_progress(
        self,
        stage: str,
        format_name: str,
        context: dict[str, Any],
        state: GlobalState,
    ) -> str:
        """Generate human-friendly progress narration using LLM.

        Provides clear, friendly updates during conversion to help users
        understand what's happening at each stage.

        Args:
            stage: Current stage (e.g., "starting", "processing", "finalizing")
            format_name: Data format being converted
            context: Additional context (file_size, progress_percent, etc.)
            state: Global state for logging

        Returns:
            Human-friendly narration string
        """
        if not self._llm_service:
            # Fallback to generic messages
            fallback_messages = {
                "starting": f"Starting conversion of {format_name} data...",
                "processing": f"Processing {format_name} data ({context.get('progress_percent', 0)}% complete)...",
                "finalizing": "Finalizing NWB file...",
                "complete": "Conversion complete!",
            }
            return fallback_messages.get(stage, "Processing...")

        system_prompt = """You are a helpful assistant narrating the progress of a neuroscience data conversion.

Your job is to provide clear, friendly updates that help users understand what's happening.

- Be concise (1-2 sentences)
- Use plain language (avoid technical jargon unless necessary)
- Show enthusiasm but stay professional
- Mention specific milestones when relevant"""

        user_prompt = f"""Generate a progress update for this conversion stage:

Stage: {stage}
Format: {format_name}
Context: {context}

Provide a brief, friendly update about what's happening now."""

        try:
            narration = await self._llm_service.generate_completion(
                prompt=user_prompt,
                system_prompt=system_prompt,
            )
            state.add_log(LogLevel.INFO, f"Progress: {narration}")
            return str(narration).strip()
        except Exception as e:
            state.add_log(LogLevel.WARNING, f"Progress narration failed: {e}")
            # Fallback
            return f"Processing {format_name} data at stage: {stage}"
