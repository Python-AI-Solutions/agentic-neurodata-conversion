"""Provenance tracking for metadata fields.

Handles tracking the source, confidence, and origin of every metadata field
for scientific transparency and DANDI compliance.
"""

from datetime import datetime
from typing import Any

from agentic_neurodata_conversion.models import (
    GlobalState,
    LogLevel,
    MetadataProvenance,
    ProvenanceInfo,
)


class ProvenanceTracker:
    """Tracks metadata provenance for scientific transparency."""

    @staticmethod
    def track_metadata_provenance(
        state: GlobalState,
        field_name: str,
        value: Any,
        provenance_type: str,
        confidence: float = 100.0,
        source: str = "",
        needs_review: bool = False,
        raw_input: str | None = None,
    ) -> None:
        """Track provenance for a metadata field.

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

    @staticmethod
    def track_user_provided_metadata(
        state: GlobalState,
        field_name: str,
        value: Any,
        confidence: float = 100.0,
        source: str = "User explicitly provided",
        raw_input: str | None = None,
    ) -> None:
        """Track provenance for user-provided metadata.

        Args:
            state: Global state
            field_name: Metadata field name
            value: The metadata value
            confidence: Confidence score (default 100% for explicit user input)
            source: Description of how user provided it
            raw_input: Original user input
        """
        ProvenanceTracker.track_metadata_provenance(
            state=state,
            field_name=field_name,
            value=value,
            provenance_type="user-specified",
            confidence=confidence,
            source=source,
            needs_review=False,
            raw_input=raw_input,
        )

    @staticmethod
    def track_ai_parsed_metadata(
        state: GlobalState,
        field_name: str,
        value: Any,
        confidence: float,
        raw_input: str,
        reasoning: str = "",
    ) -> None:
        """Track provenance for AI-parsed metadata from natural language.

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

        ProvenanceTracker.track_metadata_provenance(
            state=state,
            field_name=field_name,
            value=value,
            provenance_type="ai-parsed",
            confidence=confidence,
            source=source,
            needs_review=needs_review,
            raw_input=raw_input,
        )

    @staticmethod
    def track_auto_corrected_metadata(
        state: GlobalState,
        field_name: str,
        value: Any,
        source: str,
    ) -> None:
        """Track provenance for auto-corrected metadata during error correction.

        Args:
            state: Global state
            field_name: Metadata field name
            value: The corrected value
            source: Description of the correction
        """
        ProvenanceTracker.track_metadata_provenance(
            state=state,
            field_name=field_name,
            value=value,
            provenance_type="auto-corrected",
            confidence=70.0,  # Medium confidence for auto-corrections
            source=source,
            needs_review=True,  # Always recommend review for auto-corrections
            raw_input=None,
        )
