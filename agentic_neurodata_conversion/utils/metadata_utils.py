"""
Metadata utility functions for the agentic neurodata conversion system.

This module provides utilities for processing, validating, and transforming
metadata used in the neuroscience data conversion pipeline.
"""

from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)


class MetadataUtils:
    """
    Utility class for metadata processing and validation.

    Provides methods for metadata normalization, validation, and transformation
    commonly needed in the conversion pipeline.
    """

    @staticmethod
    def normalize_metadata(
        raw_metadata: dict[str, Any], target_schema: str = "nwb"
    ) -> dict[str, Any]:
        """
        Normalize metadata to a target schema format.

        Args:
            raw_metadata: Raw metadata dictionary
            target_schema: Target schema format ("nwb", "bids", etc.)

        Returns:
            Normalized metadata dictionary
        """
        logger.info(f"Normalizing metadata to {target_schema} schema")

        if target_schema == "nwb":
            return MetadataUtils._normalize_to_nwb(raw_metadata)
        elif target_schema == "bids":
            return MetadataUtils._normalize_to_bids(raw_metadata)
        else:
            logger.warning(
                f"Unknown target schema: {target_schema}, returning raw metadata"
            )
            return raw_metadata.copy()

    @staticmethod
    def _normalize_to_nwb(raw_metadata: dict[str, Any]) -> dict[str, Any]:
        """Normalize metadata to NWB format."""
        nwb_metadata = {
            "NWBFile": {},
            "Subject": {},
            "Behavior": {},
            "Ecephys": {},
            "Ophys": {},
            "Icephys": {},
        }

        # Map common fields to NWB structure
        field_mappings = {
            # NWBFile fields
            "session_description": [
                "session_description",
                "description",
                "experiment_description",
            ],
            "identifier": ["identifier", "session_id", "id"],
            "session_start_time": ["session_start_time", "start_time", "timestamp"],
            "experimenter": ["experimenter", "researcher", "investigator"],
            "lab": ["lab", "laboratory", "institution_lab"],
            "institution": ["institution", "university", "organization"],
            "experiment_description": ["experiment_description", "description"],
            "session_id": ["session_id", "identifier", "id"],
            # Subject fields
            "subject_id": ["subject_id", "animal_id", "mouse_id"],
            "age": ["age", "subject_age"],
            "sex": ["sex", "gender"],
            "species": ["species", "organism"],
            "strain": ["strain", "genotype"],
            "weight": ["weight", "body_weight"],
        }

        # Apply field mappings
        for nwb_field, possible_keys in field_mappings.items():
            value = MetadataUtils._find_field_value(raw_metadata, possible_keys)
            if value is not None:
                if nwb_field in [
                    "subject_id",
                    "age",
                    "sex",
                    "species",
                    "strain",
                    "weight",
                ]:
                    nwb_metadata["Subject"][nwb_field] = value
                else:
                    nwb_metadata["NWBFile"][nwb_field] = value

        # Handle special cases
        MetadataUtils._handle_datetime_fields(nwb_metadata)
        MetadataUtils._add_default_nwb_fields(nwb_metadata)

        logger.info("Metadata normalized to NWB format")
        return nwb_metadata

    @staticmethod
    def _normalize_to_bids(raw_metadata: dict[str, Any]) -> dict[str, Any]:
        """Normalize metadata to BIDS format."""
        bids_metadata = {"dataset_description": {}, "participants": {}, "sessions": {}}

        # Basic BIDS field mappings (placeholder)
        field_mappings = {
            "participant_id": ["subject_id", "participant_id", "id"],
            "age": ["age", "subject_age"],
            "sex": ["sex", "gender"],
            "session_id": ["session_id", "session", "ses"],
        }

        for bids_field, possible_keys in field_mappings.items():
            value = MetadataUtils._find_field_value(raw_metadata, possible_keys)
            if value is not None:
                if bids_field == "participant_id":
                    bids_metadata["participants"][bids_field] = value
                else:
                    bids_metadata["sessions"][bids_field] = value

        logger.info("Metadata normalized to BIDS format")
        return bids_metadata

    @staticmethod
    def _find_field_value(
        metadata: dict[str, Any], possible_keys: list[str]
    ) -> Optional[Any]:
        """Find a field value using multiple possible key names."""
        for key in possible_keys:
            # Check exact match
            if key in metadata:
                return metadata[key]

            # Check case-insensitive match
            for meta_key, meta_value in metadata.items():
                if meta_key.lower() == key.lower():
                    return meta_value

        return None

    @staticmethod
    def _handle_datetime_fields(metadata: dict[str, Any]) -> None:
        """Handle datetime field formatting for NWB."""
        datetime_fields = ["session_start_time", "timestamp", "start_time"]

        for section in metadata.values():
            if isinstance(section, dict):
                for field in datetime_fields:
                    if field in section:
                        section[field] = MetadataUtils._normalize_datetime(
                            section[field]
                        )

    @staticmethod
    def _normalize_datetime(datetime_value: Any) -> str:
        """Normalize datetime value to ISO format string."""
        if isinstance(datetime_value, str):
            try:
                # Try to parse and reformat
                dt = datetime.fromisoformat(datetime_value.replace("Z", "+00:00"))
                return dt.isoformat()
            except ValueError:
                logger.warning(f"Could not parse datetime: {datetime_value}")
                return str(datetime_value)
        elif isinstance(datetime_value, datetime):
            return datetime_value.isoformat()
        else:
            logger.warning(f"Unexpected datetime type: {type(datetime_value)}")
            return str(datetime_value)

    @staticmethod
    def _add_default_nwb_fields(metadata: dict[str, Any]) -> None:
        """Add default required NWB fields if missing."""
        nwb_file = metadata.get("NWBFile", {})

        # Add default identifier if missing
        if "identifier" not in nwb_file:
            nwb_file["identifier"] = (
                f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )

        # Add default session_description if missing
        if "session_description" not in nwb_file:
            nwb_file["session_description"] = "Converted neuroscience session"

        # Add default session_start_time if missing
        if "session_start_time" not in nwb_file:
            nwb_file["session_start_time"] = datetime.now().isoformat()

    @staticmethod
    def validate_required_fields(
        metadata: dict[str, Any], schema: str = "nwb"
    ) -> dict[str, Any]:
        """
        Validate that required fields are present in metadata.

        Args:
            metadata: Metadata dictionary to validate
            schema: Schema to validate against ("nwb", "bids")

        Returns:
            Validation result dictionary
        """
        logger.info(f"Validating required fields for {schema} schema")

        validation_result = {
            "schema": schema,
            "status": "valid",
            "missing_fields": [],
            "invalid_fields": [],
            "warnings": [],
        }

        if schema == "nwb":
            required_fields = {
                "NWBFile": ["session_description", "identifier", "session_start_time"],
                "Subject": [],  # Subject fields are optional but recommended
            }

            for section, fields in required_fields.items():
                section_data = metadata.get(section, {})
                for field in fields:
                    if field not in section_data or section_data[field] is None:
                        validation_result["missing_fields"].append(f"{section}.{field}")

        elif schema == "bids":
            # BIDS validation (placeholder)
            required_fields = ["participant_id"]
            participants_data = metadata.get("participants", {})

            for field in required_fields:
                if field not in participants_data:
                    validation_result["missing_fields"].append(f"participants.{field}")

        # Update status based on missing fields
        if validation_result["missing_fields"]:
            validation_result["status"] = "invalid"

        logger.info(f"Validation completed: {validation_result['status']}")
        return validation_result

    @staticmethod
    def merge_metadata(
        base_metadata: dict[str, Any],
        override_metadata: dict[str, Any],
        merge_strategy: str = "override",
    ) -> dict[str, Any]:
        """
        Merge two metadata dictionaries.

        Args:
            base_metadata: Base metadata dictionary
            override_metadata: Metadata to merge in
            merge_strategy: Strategy for merging ("override", "merge", "preserve")

        Returns:
            Merged metadata dictionary
        """
        logger.info(f"Merging metadata with strategy: {merge_strategy}")

        merged = base_metadata.copy()

        if merge_strategy == "override":
            # Override base with new values
            for key, value in override_metadata.items():
                if (
                    isinstance(value, dict)
                    and key in merged
                    and isinstance(merged[key], dict)
                ):
                    merged[key].update(value)
                else:
                    merged[key] = value

        elif merge_strategy == "merge":
            # Deep merge dictionaries
            merged = MetadataUtils._deep_merge(merged, override_metadata)

        elif merge_strategy == "preserve":
            # Only add new fields, don't override existing
            for key, value in override_metadata.items():
                if key not in merged:
                    merged[key] = value
                elif isinstance(value, dict) and isinstance(merged[key], dict):
                    # Recursively preserve for nested dicts
                    merged[key] = MetadataUtils.merge_metadata(
                        merged[key], value, "preserve"
                    )

        logger.info("Metadata merge completed")
        return merged

    @staticmethod
    def _deep_merge(dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
        """Deep merge two dictionaries."""
        result = dict1.copy()

        for key, value in dict2.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = MetadataUtils._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    @staticmethod
    def extract_metadata_from_file(
        file_path: Union[str, Path], file_format: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Extract metadata from a file based on its format.

        Args:
            file_path: Path to the file
            file_format: Optional format hint

        Returns:
            Extracted metadata dictionary
        """
        file_path = Path(file_path)
        logger.info(f"Extracting metadata from: {file_path}")

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        metadata = {
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_size": file_path.stat().st_size,
            "extraction_timestamp": datetime.now().isoformat(),
        }

        # Extract based on file extension or format hint
        file_format = file_format or file_path.suffix.lower()

        if file_format in [".json"]:
            metadata.update(MetadataUtils._extract_from_json(file_path))
        elif file_format in [".yaml", ".yml"]:
            metadata.update(MetadataUtils._extract_from_yaml(file_path))
        elif file_format in [".meta"]:  # SpikeGLX meta files
            metadata.update(MetadataUtils._extract_from_spikeglx_meta(file_path))
        else:
            logger.warning(f"No specific extraction method for format: {file_format}")

        return metadata

    @staticmethod
    def _extract_from_json(file_path: Path) -> dict[str, Any]:
        """Extract metadata from JSON file."""
        try:
            with open(file_path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to extract JSON metadata: {e}")
            return {"error": str(e)}

    @staticmethod
    def _extract_from_yaml(file_path: Path) -> dict[str, Any]:
        """Extract metadata from YAML file."""
        try:
            import yaml

            with open(file_path) as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            logger.warning("PyYAML not available for YAML metadata extraction")
            return {"error": "PyYAML not available"}
        except Exception as e:
            logger.error(f"Failed to extract YAML metadata: {e}")
            return {"error": str(e)}

    @staticmethod
    def _extract_from_spikeglx_meta(file_path: Path) -> dict[str, Any]:
        """Extract metadata from SpikeGLX .meta file."""
        metadata = {}

        try:
            with open(file_path) as f:
                for line in f:
                    line = line.strip()
                    if "=" in line:
                        key, value = line.split("=", 1)
                        # Try to convert to appropriate type
                        try:
                            if "." in value:
                                metadata[key] = float(value)
                            else:
                                metadata[key] = int(value)
                        except ValueError:
                            metadata[key] = value
        except Exception as e:
            logger.error(f"Failed to extract SpikeGLX metadata: {e}")
            return {"error": str(e)}

        return metadata

    @staticmethod
    def save_metadata(
        metadata: dict[str, Any],
        output_path: Union[str, Path],
        format_type: str = "json",
    ) -> Path:
        """
        Save metadata to file.

        Args:
            metadata: Metadata dictionary to save
            output_path: Output file path
            format_type: Output format ("json", "yaml")

        Returns:
            Path to saved file
        """
        output_path = Path(output_path)
        logger.info(f"Saving metadata to: {output_path}")

        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format_type == "json":
            with open(output_path, "w") as f:
                json.dump(metadata, f, indent=2, default=str)
        elif format_type == "yaml":
            try:
                import yaml

                with open(output_path, "w") as f:
                    yaml.dump(metadata, f, default_flow_style=False)
            except ImportError:
                logger.error("PyYAML not available for YAML output")
                raise ImportError("PyYAML required for YAML output")
        else:
            raise ValueError(f"Unsupported format type: {format_type}")

        logger.info(f"Metadata saved successfully to: {output_path}")
        return output_path
