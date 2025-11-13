"""
Factory for generating test metadata.

Provides programmatic generation of NWB metadata to eliminate
hardcoded test data and improve test flexibility.
"""

from datetime import datetime
from typing import Any


class MetadataFactory:
    """Factory for generating test metadata."""

    @staticmethod
    def create_minimal_metadata() -> dict[str, Any]:
        """Create minimal valid NWB metadata."""
        return {
            "session_description": "Test session",
            "identifier": "test_session_001",
            "session_start_time": datetime.now().isoformat(),
        }

    @staticmethod
    def create_complete_metadata() -> dict[str, Any]:
        """Create complete NWB metadata with all fields."""
        return {
            "session_description": "Electrophysiology recording of mouse V1 cortex",
            "identifier": "test_session_complete_001",
            "session_start_time": "2025-01-15T10:30:00",
            "experimenter": ["Jane Doe", "John Smith"],
            "lab": "Neural Dynamics Lab",
            "institution": "Example University",
            "experiment_description": "Visual stimulus response experiment",
            "keywords": ["electrophysiology", "visual cortex", "mouse"],
            "subject": {
                "subject_id": "MOUSE_001",
                "age": "P90D",  # 90 days old
                "species": "Mus musculus",
                "sex": "F",
                "weight": "25g",
                "description": "Wild-type C57BL/6 mouse",
            },
        }

    @staticmethod
    def create_metadata_with_missing_fields(missing_fields: list) -> dict[str, Any]:
        """Create metadata missing specified fields."""
        metadata = MetadataFactory.create_complete_metadata()

        for field in missing_fields:
            if "." in field:
                # Handle nested fields like "subject.age"
                parts = field.split(".")
                if parts[0] in metadata and isinstance(metadata[parts[0]], dict):
                    if parts[1] in metadata[parts[0]]:
                        del metadata[parts[0]][parts[1]]
            else:
                if field in metadata:
                    del metadata[field]

        return metadata

    @staticmethod
    def create_metadata_with_invalid_values() -> dict[str, Any]:
        """Create metadata with invalid values for testing validation."""
        return {
            "session_description": "",  # Empty string - invalid
            "identifier": "test_session_001",
            "session_start_time": "invalid_date_format",  # Invalid format
            "subject": {
                "age": "not_a_valid_age",  # Invalid ISO 8601 duration
                "species": "Unknown Species",  # Not a valid species name
            },
        }

    @staticmethod
    def create_spikeglx_metadata() -> dict[str, Any]:
        """Create metadata specific to SpikeGLX recordings."""
        base = MetadataFactory.create_complete_metadata()
        base.update(
            {
                "recording_device": "Neuropixels 2.0",
                "probe_type": "Neuropixels",
                "sampling_rate": 30000,  # Hz
                "num_channels": 384,
            }
        )
        return base

    @staticmethod
    def create_metadata_for_retry_scenario() -> dict[str, Any]:
        """Create metadata for testing retry workflows."""
        return {
            "session_description": "Initial conversion attempt",
            "identifier": "retry_test_001",
            "session_start_time": datetime.now().isoformat(),
            # Missing some recommended fields to trigger warnings
            # But has all required fields so conversion proceeds
        }

    @staticmethod
    def create_partial_metadata() -> dict[str, Any]:
        """Create partially complete metadata (for user input testing)."""
        return {
            "experimenter": "Jane Doe",
            "subject": {"species": "Mus musculus"},
            # Missing session_description, identifier, session_start_time
        }

    @staticmethod
    def create_metadata_with_provenance() -> dict[str, Any]:
        """Create metadata with provenance information."""
        metadata = MetadataFactory.create_complete_metadata()
        metadata["_provenance"] = {
            "source": "user_input",
            "timestamp": datetime.now().isoformat(),
            "method": "conversational_chat",
            "confidence": "high",
        }
        return metadata
