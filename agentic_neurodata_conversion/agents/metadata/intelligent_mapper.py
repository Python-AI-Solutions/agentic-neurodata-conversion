"""Intelligent Metadata Mapper using LLM for flexible metadata handling.

This module allows users to input arbitrary metadata in natural language
and intelligently maps it to appropriate NWB schema fields or custom extensions.
"""

import json
import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from agentic_neurodata_conversion.models import GlobalState, LogLevel
from agentic_neurodata_conversion.services import LLMService


class MetadataCategory(Enum):
    """Categories for organizing metadata."""

    EXPERIMENTAL = "experimental"  # Experiment design, protocols
    SUBJECT = "subject"  # Animal/human subject info
    RECORDING = "recording"  # Recording setup, equipment
    ANALYSIS = "analysis"  # Analysis parameters, methods
    BEHAVIORAL = "behavioral"  # Behavioral paradigm, stimuli
    PHARMACOLOGY = "pharmacology"  # Drugs, treatments
    HISTOLOGY = "histology"  # Tissue processing, staining
    CUSTOM = "custom"  # User-defined fields


class MappedField(BaseModel):
    """Represents a mapped metadata field."""

    original_input: str = Field(description="Original user input")
    field_name: str = Field(description="Standardized field name")
    nwb_path: str = Field(description="Path in NWB schema (e.g., /general/experimenter)")
    value: Any = Field(description="Parsed value")
    data_type: str = Field(description="Data type (string, number, datetime, etc.)")
    category: MetadataCategory = Field(description="Field category")
    confidence: float = Field(description="Mapping confidence (0-1)")
    is_standard: bool = Field(description="True if maps to standard NWB field")
    requires_review: bool = Field(description="True if user should review mapping")
    provenance: str = Field(default="user-custom", description="Source of the field")


class IntelligentMetadataMapper:
    """Maps arbitrary user metadata to NWB schema intelligently."""

    # Standard NWB field mappings with variations
    NWB_FIELD_MAPPINGS = {
        # Experimental metadata
        "experimenter": {
            "paths": ["/general/experimenter"],
            "aliases": [
                "investigator",
                "researcher",
                "pi",
                "principal investigator",
                "scientist",
                "lab member",
                "author",
                "recorded by",
            ],
            "type": "string_list",
            "category": MetadataCategory.EXPERIMENTAL,
        },
        "institution": {
            "paths": ["/general/institution"],
            "aliases": [
                "university",
                "institute",
                "organization",
                "affiliation",
                "research center",
                "facility",
                "school",
            ],
            "type": "string",
            "category": MetadataCategory.EXPERIMENTAL,
        },
        "lab": {
            "paths": ["/general/lab"],
            "aliases": ["laboratory", "research group", "department", "unit"],
            "type": "string",
            "category": MetadataCategory.EXPERIMENTAL,
        },
        "experiment_description": {
            "paths": ["/general/experiment_description"],
            "aliases": [
                "experiment",
                "study description",
                "research description",
                "experimental paradigm",
                "protocol description",
            ],
            "type": "string",
            "category": MetadataCategory.EXPERIMENTAL,
        },
        # Subject metadata
        "subject_id": {
            "paths": ["/general/subject/subject_id"],
            "aliases": [
                "animal id",
                "mouse id",
                "rat id",
                "patient id",
                "participant",
                "subject number",
                "animal number",
            ],
            "type": "string",
            "category": MetadataCategory.SUBJECT,
        },
        "species": {
            "paths": ["/general/subject/species"],
            "aliases": ["organism", "animal type", "animal species"],
            "type": "string",
            "category": MetadataCategory.SUBJECT,
        },
        "strain": {
            "paths": ["/general/subject/strain"],
            "aliases": ["genetic strain", "mouse strain", "rat strain", "genotype"],
            "type": "string",
            "category": MetadataCategory.SUBJECT,
        },
        "sex": {
            "paths": ["/general/subject/sex"],
            "aliases": ["gender", "biological sex", "mouse sex", "animal sex"],
            "type": "string",
            "category": MetadataCategory.SUBJECT,
        },
        "age": {
            "paths": ["/general/subject/age"],
            "aliases": ["animal age", "subject age", "age at recording", "postnatal day", "developmental stage"],
            "type": "string",
            "category": MetadataCategory.SUBJECT,
        },
        "weight": {
            "paths": ["/general/subject/weight"],
            "aliases": ["body weight", "animal weight", "subject weight", "mass"],
            "type": "string",
            "category": MetadataCategory.SUBJECT,
        },
        # Recording metadata
        "session_description": {
            "paths": ["/general/session_description"],
            "aliases": [
                "recording description",
                "session notes",
                "recording notes",
                "experimental session",
                "recording session",
            ],
            "type": "string",
            "category": MetadataCategory.RECORDING,
        },
        "session_id": {
            "paths": ["/session_id"],
            "aliases": ["recording id", "session number", "experiment id", "recording number", "session identifier"],
            "type": "string",
            "category": MetadataCategory.RECORDING,
        },
        "devices": {
            "paths": ["/general/devices"],
            "aliases": ["equipment", "recording equipment", "hardware", "recording device", "amplifier", "microscope"],
            "type": "object",
            "category": MetadataCategory.RECORDING,
        },
        # Behavioral metadata
        "stimulus": {
            "paths": ["/general/stimulus"],
            "aliases": ["stimulation", "stimulus type", "stimulus protocol", "visual stimulus", "auditory stimulus"],
            "type": "string",
            "category": MetadataCategory.BEHAVIORAL,
        },
        "protocol": {
            "paths": ["/general/protocol"],
            "aliases": ["behavioral protocol", "task", "paradigm", "experimental protocol", "procedure"],
            "type": "string",
            "category": MetadataCategory.BEHAVIORAL,
        },
        # Pharmacology
        "pharmacology": {
            "paths": ["/general/pharmacology"],
            "aliases": ["drugs", "drug treatment", "medication", "anesthesia", "pharmaceutical", "chemical treatment"],
            "type": "string",
            "category": MetadataCategory.PHARMACOLOGY,
        },
        # Histology
        "surgery": {
            "paths": ["/general/surgery"],
            "aliases": ["surgical procedure", "surgery notes", "implantation", "surgical protocol", "operation"],
            "type": "string",
            "category": MetadataCategory.HISTOLOGY,
        },
        "virus": {
            "paths": ["/general/virus"],
            "aliases": ["viral injection", "virus type", "viral vector", "optogenetics virus", "AAV"],
            "type": "string",
            "category": MetadataCategory.HISTOLOGY,
        },
    }

    def __init__(self, llm_service: LLMService | None = None):
        """Initialize the mapper with optional LLM service."""
        self.llm_service = llm_service

    async def parse_custom_metadata(
        self, user_input: str, existing_metadata: dict[str, Any], state: GlobalState
    ) -> dict[str, Any]:
        """Parse free-form user input into structured metadata.

        Args:
            user_input: Natural language metadata from user
            existing_metadata: Already collected metadata
            state: Global state

        Returns:
            Dictionary with parsed and mapped metadata
        """
        state.add_log(LogLevel.INFO, "Parsing custom metadata input")

        if not self.llm_service:
            # Fallback to regex parsing
            return self._parse_without_llm(user_input)

        # Use LLM to understand and structure the input
        system_prompt = """You are an expert at understanding neuroscience metadata.
Parse the user's input and extract metadata fields with their values.

Consider these categories:
- Experimental details (protocols, methods)
- Subject information (species, age, conditions)
- Recording setup (equipment, parameters)
- Behavioral paradigm (tasks, stimuli)
- Pharmacology (drugs, doses)
- Analysis methods

Return a structured JSON with extracted fields."""

        user_prompt = f"""Parse this metadata into structured fields:

User Input:
{user_input}

Already collected metadata (don't duplicate):
{json.dumps(existing_metadata, indent=2)[:500]}

Extract ALL metadata mentioned, even if not standard NWB fields.
Use descriptive field names."""

        output_schema = {
            "type": "object",
            "properties": {
                "extracted_fields": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "field_description": {"type": "string"},
                            "suggested_name": {"type": "string"},
                            "value": {"type": "string"},
                            "category": {"type": "string"},
                            "confidence": {"type": "number"},
                        },
                    },
                },
                "interpretation_notes": {"type": "string"},
            },
        }

        try:
            result = await self.llm_service.generate_structured_output(
                prompt=user_prompt, output_schema=output_schema, system_prompt=system_prompt
            )

            # Map extracted fields to NWB schema
            mapped_metadata = await self._map_to_nwb_schema(result.get("extracted_fields", []), state)

            return mapped_metadata

        except Exception as e:
            state.add_log(LogLevel.ERROR, f"LLM parsing failed: {str(e)}")
            return self._parse_without_llm(user_input)

    async def _map_to_nwb_schema(self, extracted_fields: list[dict], state: GlobalState) -> dict[str, Any]:
        """Map extracted fields to NWB schema paths.

        Returns dictionary with:
        - standard_fields: Fields that map to NWB schema
        - custom_fields: Fields to store as custom extensions
        - mapping_report: Details about each mapping
        """
        standard_fields = {}
        custom_fields = {}
        mapping_report = []

        for field in extracted_fields:
            field_name = field.get("suggested_name", "").lower()
            value = field.get("value")
            field.get("category", "custom")

            # Try to match to standard NWB field
            matched = False
            for nwb_field, config in self.NWB_FIELD_MAPPINGS.items():
                config_dict: dict[str, Any] = config  # Cast for type safety
                # Check if field name or description matches aliases
                if (
                    field_name in config_dict["aliases"]
                    or nwb_field in field_name
                    or any(alias in field.get("field_description", "").lower() for alias in config_dict["aliases"])
                ):
                    # Map to standard field
                    standard_fields[nwb_field] = value
                    mapping_report.append(
                        MappedField(
                            original_input=field.get("field_description", ""),
                            field_name=nwb_field,
                            nwb_path=config_dict["paths"][0],
                            value=value,
                            data_type=config_dict["type"],
                            category=config_dict["category"],
                            confidence=field.get("confidence", 0.8),
                            is_standard=True,
                            requires_review=field.get("confidence", 1.0) < 0.7,
                            provenance="user-custom",
                        )
                    )
                    matched = True
                    break

            if not matched:
                # Store as custom field
                clean_name = self._clean_field_name(field_name)
                custom_fields[clean_name] = value
                mapping_report.append(
                    MappedField(
                        original_input=field.get("field_description", ""),
                        field_name=clean_name,
                        nwb_path=f"/general/custom/{clean_name}",
                        value=value,
                        data_type="string",
                        category=MetadataCategory.CUSTOM,
                        confidence=field.get("confidence", 0.9),
                        is_standard=False,
                        requires_review=False,
                        provenance="user-custom",
                    )
                )

        state.add_log(
            LogLevel.INFO, f"Mapped {len(standard_fields)} standard fields, {len(custom_fields)} custom fields"
        )

        return {
            "standard_fields": standard_fields,
            "custom_fields": custom_fields,
            "mapping_report": [m.model_dump() for m in mapping_report],
            "_provenance": dict.fromkeys({**standard_fields, **custom_fields}.keys(), "user-custom"),
        }

    def _parse_without_llm(self, user_input: str) -> dict[str, Any]:
        """Fallback parsing using regex when LLM is not available."""
        metadata = {}

        # Common patterns for key-value pairs
        patterns = [
            r"(\w+):\s*([^,\n]+)",  # key: value
            r"(\w+)\s*=\s*([^,\n]+)",  # key = value
            r"(\w+)\s+is\s+([^,\n]+)",  # key is value
        ]

        for pattern in patterns:
            matches = re.findall(pattern, user_input, re.IGNORECASE)
            for key, value in matches:
                clean_key = self._clean_field_name(key)
                metadata[clean_key] = value.strip()

        return {
            "standard_fields": {},
            "custom_fields": metadata,
            "mapping_report": [],
            "_provenance": dict.fromkeys(metadata.keys(), "user-custom"),
        }

    def _clean_field_name(self, name: str) -> str:
        """Clean field name for use as identifier."""
        # Remove special characters, replace spaces with underscores
        clean = re.sub(r"[^a-zA-Z0-9_\s]", "", name)
        clean = re.sub(r"\s+", "_", clean)
        return clean.lower()

    async def suggest_missing_metadata(self, existing_metadata: dict[str, Any], file_type: str) -> list[str]:
        """Suggest additional metadata fields based on file type and existing data.

        Returns list of suggested fields the user might want to add.
        """
        suggestions = []

        # Check which standard fields are missing
        for field in self.NWB_FIELD_MAPPINGS:
            if field not in existing_metadata or not existing_metadata.get(field):
                suggestions.append(field)

        # File-type specific suggestions
        if "ephys" in file_type.lower() or "spike" in file_type.lower():
            ephys_fields = ["sampling_rate", "filter_settings", "probe_type", "recording_duration", "channel_count"]
            suggestions.extend([f for f in ephys_fields if f not in existing_metadata])

        elif "imaging" in file_type.lower() or "tiff" in file_type.lower():
            imaging_fields = [
                "imaging_rate",
                "imaging_depth",
                "laser_power",
                "objective",
                "pixel_size",
                "field_of_view",
            ]
            suggestions.extend([f for f in imaging_fields if f not in existing_metadata])

        elif "behavior" in file_type.lower():
            behavior_fields = ["task_name", "reward_type", "trial_count", "session_duration", "performance_metric"]
            suggestions.extend([f for f in behavior_fields if f not in existing_metadata])

        return suggestions[:10]  # Return top 10 suggestions

    def format_metadata_for_display(self, metadata: dict[str, Any], mapping_report: list[dict]) -> str:
        """Format metadata and mappings for user review."""
        output = []
        output.append("📋 **Metadata Mapping Summary**\n")

        # Group by category
        by_category: dict[str, list[dict]] = {}
        for report in mapping_report:
            category = report.get("category", "custom")
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(report)

        for category, fields in by_category.items():
            output.append(f"\n**{category.upper()} Fields:**")
            for field in fields:
                confidence = field.get("confidence", 0)
                status = "✅" if confidence > 0.8 else "⚠️" if confidence > 0.5 else "❓"
                standard = "📋" if field.get("is_standard") else "🔧"

                output.append(
                    f"  {status} {standard} {field['field_name']}: {field['value'][:50]}..."
                    if len(str(field["value"])) > 50
                    else f"  {status} {standard} {field['field_name']}: {field['value']}"
                )

                if field.get("requires_review"):
                    output.append("     ⚠️ Please review this mapping")

        return "\n".join(output)
