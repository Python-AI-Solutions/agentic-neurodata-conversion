"""
Metadata processing utilities for the agentic neurodata conversion system.

This module provides functionality for processing, normalizing, and validating
metadata used in neuroscience data conversion workflows.
"""

from datetime import datetime, timezone
import logging
import re
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)


class MetadataProcessor:
    """
    Utility class for processing and normalizing metadata.

    Provides methods for metadata validation, normalization, merging,
    and conversion between different metadata formats used in neuroscience.
    """

    # Standard NWB metadata fields and their types
    NWB_METADATA_SCHEMA = {
        "NWBFile": {
            "session_description": str,
            "identifier": str,
            "session_start_time": datetime,
            "experimenter": list,
            "lab": str,
            "institution": str,
            "experiment_description": str,
            "session_id": str,
            "subject": dict,
            "keywords": list,
        },
        "Subject": {
            "subject_id": str,
            "age": str,
            "description": str,
            "genotype": str,
            "sex": str,
            "species": str,
            "strain": str,
            "weight": str,
        },
        "Device": {"name": str, "description": str, "manufacturer": str},
    }

    def __init__(self):
        """Initialize metadata processor."""
        self._validation_cache = {}

    def normalize_metadata(
        self, raw_metadata: dict[str, Any], source_format: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Normalize metadata to NWB-compatible format.

        Args:
            raw_metadata: Raw metadata dictionary
            source_format: Optional source format identifier

        Returns:
            Normalized metadata dictionary
        """
        logger.info("Normalizing metadata to NWB format")

        normalized = {"NWBFile": {}, "Subject": {}, "Device": []}

        try:
            # Normalize NWBFile metadata
            normalized["NWBFile"] = self._normalize_nwbfile_metadata(raw_metadata)

            # Normalize Subject metadata
            normalized["Subject"] = self._normalize_subject_metadata(raw_metadata)

            # Normalize Device metadata
            normalized["Device"] = self._normalize_device_metadata(raw_metadata)

            # Add source format information
            if source_format:
                normalized["NWBFile"]["source_format"] = source_format

            logger.info("Metadata normalization completed successfully")
            return normalized

        except Exception as e:
            logger.error(f"Metadata normalization failed: {e}")
            raise

    def _normalize_nwbfile_metadata(
        self, raw_metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Normalize NWBFile-specific metadata.

        Args:
            raw_metadata: Raw metadata dictionary

        Returns:
            Normalized NWBFile metadata
        """
        nwbfile_metadata = {}

        # Required fields with defaults
        nwbfile_metadata["session_description"] = self._extract_field(
            raw_metadata,
            ["session_description", "description", "experiment_description"],
            default="Neuroscience recording session",
        )

        nwbfile_metadata["identifier"] = self._extract_field(
            raw_metadata,
            ["identifier", "session_id", "recording_id", "file_id"],
            default=self._generate_identifier(),
        )

        # Session start time
        session_start_time = self._extract_session_start_time(raw_metadata)
        if session_start_time:
            nwbfile_metadata["session_start_time"] = session_start_time

        # Optional fields
        experimenter = self._extract_field(
            raw_metadata,
            ["experimenter", "experimenters", "researcher", "investigator"],
        )
        if experimenter:
            if isinstance(experimenter, str):
                nwbfile_metadata["experimenter"] = [experimenter]
            elif isinstance(experimenter, list):
                nwbfile_metadata["experimenter"] = experimenter

        # Institution and lab
        lab = self._extract_field(raw_metadata, ["lab", "laboratory", "lab_name"])
        if lab:
            nwbfile_metadata["lab"] = lab

        institution = self._extract_field(
            raw_metadata, ["institution", "university", "organization"]
        )
        if institution:
            nwbfile_metadata["institution"] = institution

        # Experiment description
        experiment_description = self._extract_field(
            raw_metadata, ["experiment_description", "protocol", "procedure"]
        )
        if experiment_description:
            nwbfile_metadata["experiment_description"] = experiment_description

        # Session ID
        session_id = self._extract_field(
            raw_metadata, ["session_id", "recording_session", "session_name"]
        )
        if session_id:
            nwbfile_metadata["session_id"] = str(session_id)

        # Keywords
        keywords = self._extract_field(raw_metadata, ["keywords", "tags", "categories"])
        if keywords:
            if isinstance(keywords, str):
                nwbfile_metadata["keywords"] = [keywords]
            elif isinstance(keywords, list):
                nwbfile_metadata["keywords"] = keywords

        return nwbfile_metadata

    def _normalize_subject_metadata(
        self, raw_metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Normalize Subject-specific metadata.

        Args:
            raw_metadata: Raw metadata dictionary

        Returns:
            Normalized Subject metadata
        """
        subject_metadata = {}

        # Look for subject information in various locations
        subject_data = raw_metadata.get("subject", raw_metadata.get("Subject", {}))
        if not subject_data:
            # Try to extract from top-level fields
            subject_data = raw_metadata

        # Subject ID
        subject_id = self._extract_field(
            subject_data, ["subject_id", "animal_id", "id", "name"]
        )
        if subject_id:
            subject_metadata["subject_id"] = str(subject_id)

        # Age
        age = self._extract_field(subject_data, ["age", "age_days", "age_weeks"])
        if age:
            subject_metadata["age"] = self._normalize_age(age)

        # Sex
        sex = self._extract_field(subject_data, ["sex", "gender"])
        if sex:
            subject_metadata["sex"] = self._normalize_sex(sex)

        # Species
        species = self._extract_field(
            subject_data, ["species", "organism", "animal_type"]
        )
        if species:
            subject_metadata["species"] = str(species)

        # Strain
        strain = self._extract_field(subject_data, ["strain", "genotype_strain"])
        if strain:
            subject_metadata["strain"] = str(strain)

        # Weight
        weight = self._extract_field(subject_data, ["weight", "body_weight"])
        if weight:
            subject_metadata["weight"] = str(weight)

        # Description
        description = self._extract_field(
            subject_data, ["description", "notes", "comments"]
        )
        if description:
            subject_metadata["description"] = str(description)

        # Genotype
        genotype = self._extract_field(subject_data, ["genotype", "genetic_line"])
        if genotype:
            subject_metadata["genotype"] = str(genotype)

        return subject_metadata

    def _normalize_device_metadata(
        self, raw_metadata: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Normalize Device metadata.

        Args:
            raw_metadata: Raw metadata dictionary

        Returns:
            List of normalized Device metadata dictionaries
        """
        devices = []

        # Look for device information
        device_data = raw_metadata.get("devices", raw_metadata.get("Device", []))

        if not device_data:
            # Try to extract from recording system info
            recording_system = self._extract_field(
                raw_metadata, ["recording_system", "acquisition_system", "hardware"]
            )
            if recording_system:
                device_data = [
                    {"name": "recording_system", "description": recording_system}
                ]

        if isinstance(device_data, dict):
            device_data = [device_data]
        elif not isinstance(device_data, list):
            device_data = []

        for device_info in device_data:
            if isinstance(device_info, dict):
                device = {}

                # Device name
                name = self._extract_field(
                    device_info, ["name", "device_name", "model"]
                )
                if name:
                    device["name"] = str(name)

                # Description
                description = self._extract_field(
                    device_info, ["description", "details", "specifications"]
                )
                if description:
                    device["description"] = str(description)

                # Manufacturer
                manufacturer = self._extract_field(
                    device_info, ["manufacturer", "company", "vendor"]
                )
                if manufacturer:
                    device["manufacturer"] = str(manufacturer)

                if device:  # Only add if we have some device information
                    devices.append(device)

        return devices

    def _extract_field(
        self, data: dict[str, Any], field_names: list[str], default: Any = None
    ) -> Any:
        """
        Extract field value from data using multiple possible field names.

        Args:
            data: Data dictionary to search
            field_names: List of possible field names to try
            default: Default value if no field found

        Returns:
            Field value or default
        """
        for field_name in field_names:
            if field_name in data and data[field_name] is not None:
                return data[field_name]

        return default

    def _extract_session_start_time(
        self, raw_metadata: dict[str, Any]
    ) -> Optional[datetime]:
        """
        Extract and normalize session start time.

        Args:
            raw_metadata: Raw metadata dictionary

        Returns:
            Normalized datetime object or None
        """
        time_fields = [
            "session_start_time",
            "start_time",
            "recording_start_time",
            "timestamp",
            "datetime",
            "date_time",
        ]

        for field in time_fields:
            if field in raw_metadata:
                time_value = raw_metadata[field]

                if isinstance(time_value, datetime):
                    return time_value
                elif isinstance(time_value, str):
                    return self._parse_datetime_string(time_value)

        return None

    def _parse_datetime_string(self, datetime_str: str) -> Optional[datetime]:
        """
        Parse datetime string into datetime object.

        Args:
            datetime_str: String representation of datetime

        Returns:
            Parsed datetime object or None
        """
        # Common datetime formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y/%m/%d %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%Y-%m-%d",
            "%d-%m-%Y",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(datetime_str, fmt)
                # Add timezone info if not present
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except ValueError:
                continue

        logger.warning(f"Could not parse datetime string: {datetime_str}")
        return None

    def _normalize_age(self, age: Union[str, int, float]) -> str:
        """
        Normalize age to standard format.

        Args:
            age: Age value in various formats

        Returns:
            Normalized age string
        """
        if isinstance(age, (int, float)):
            return f"P{int(age)}D"  # ISO 8601 duration format (days)

        age_str = str(age).strip().lower()

        # Extract number and unit
        match = re.match(r"(\d+(?:\.\d+)?)\s*([a-z]*)", age_str)
        if match:
            number, unit = match.groups()
            number = float(number)

            if unit in ["d", "day", "days"]:
                return f"P{int(number)}D"
            elif unit in ["w", "week", "weeks"]:
                return f"P{int(number)}W"
            elif unit in ["m", "month", "months"]:
                return f"P{int(number)}M"
            elif unit in ["y", "year", "years"]:
                return f"P{int(number)}Y"
            else:
                # Default to days if no unit specified
                return f"P{int(number)}D"

        return str(age)  # Return as-is if can't parse

    def _normalize_sex(self, sex: Union[str, Any]) -> str:
        """
        Normalize sex to standard values.

        Args:
            sex: Sex value in various formats

        Returns:
            Normalized sex string
        """
        sex_str = str(sex).strip().lower()

        if sex_str in ["m", "male", "man"]:
            return "M"
        elif sex_str in ["f", "female", "woman"]:
            return "F"
        elif sex_str in ["u", "unknown", "na", "n/a", ""]:
            return "U"
        else:
            return "U"  # Default to unknown

    def _generate_identifier(self) -> str:
        """
        Generate unique identifier for NWB file.

        Returns:
            Unique identifier string
        """
        import uuid

        return str(uuid.uuid4())

    def validate_metadata(
        self, metadata: dict[str, Any], strict: bool = False
    ) -> dict[str, Any]:
        """
        Validate metadata against NWB schema requirements.

        Args:
            metadata: Metadata dictionary to validate
            strict: Whether to use strict validation

        Returns:
            Validation results with errors and warnings
        """
        logger.info("Validating metadata against NWB schema")

        validation_results = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "missing_required": [],
            "invalid_types": [],
        }

        try:
            # Validate NWBFile metadata
            nwbfile_metadata = metadata.get("NWBFile", {})
            self._validate_section(
                nwbfile_metadata,
                self.NWB_METADATA_SCHEMA["NWBFile"],
                "NWBFile",
                validation_results,
                strict,
            )

            # Validate Subject metadata
            subject_metadata = metadata.get("Subject", {})
            self._validate_section(
                subject_metadata,
                self.NWB_METADATA_SCHEMA["Subject"],
                "Subject",
                validation_results,
                strict,
            )

            # Check for required fields
            required_fields = ["session_description", "identifier"]
            for field in required_fields:
                if field not in nwbfile_metadata:
                    validation_results["missing_required"].append(f"NWBFile.{field}")
                    validation_results["valid"] = False

            logger.info(f"Metadata validation completed: {validation_results}")
            return validation_results

        except Exception as e:
            logger.error(f"Metadata validation failed: {e}")
            validation_results["valid"] = False
            validation_results["errors"].append(f"Validation error: {str(e)}")
            return validation_results

    def _validate_section(
        self,
        data: dict[str, Any],
        schema: dict[str, type],
        section_name: str,
        results: dict[str, Any],
        strict: bool,
    ) -> None:
        """
        Validate a metadata section against its schema.

        Args:
            data: Data to validate
            schema: Schema definition
            section_name: Name of the section being validated
            results: Results dictionary to update
            strict: Whether to use strict validation
        """
        for field_name, expected_type in schema.items():
            if field_name in data:
                value = data[field_name]

                # Type checking
                if not isinstance(value, expected_type):
                    if expected_type == datetime and isinstance(value, str):
                        # Try to parse datetime string
                        parsed_dt = self._parse_datetime_string(value)
                        if parsed_dt is None:
                            results["invalid_types"].append(
                                f"{section_name}.{field_name}: expected {expected_type.__name__}, got {type(value).__name__}"
                            )
                            if strict:
                                results["valid"] = False
                    else:
                        results["invalid_types"].append(
                            f"{section_name}.{field_name}: expected {expected_type.__name__}, got {type(value).__name__}"
                        )
                        if strict:
                            results["valid"] = False

    def merge_metadata(
        self, *metadata_dicts: dict[str, Any], strategy: str = "update"
    ) -> dict[str, Any]:
        """
        Merge multiple metadata dictionaries.

        Args:
            *metadata_dicts: Variable number of metadata dictionaries
            strategy: Merge strategy ('update', 'deep_merge')

        Returns:
            Merged metadata dictionary
        """
        if not metadata_dicts:
            return {}

        if strategy == "deep_merge":
            return self._deep_merge_metadata(*metadata_dicts)
        else:
            # Simple update strategy
            merged = {}
            for metadata in metadata_dicts:
                merged.update(metadata)
            return merged

    def _deep_merge_metadata(self, *metadata_dicts: dict[str, Any]) -> dict[str, Any]:
        """
        Deep merge metadata dictionaries.

        Args:
            *metadata_dicts: Metadata dictionaries to merge

        Returns:
            Deep merged metadata dictionary
        """

        def deep_merge(dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
            result = dict1.copy()

            for key, value in dict2.items():
                if (
                    key in result
                    and isinstance(result[key], dict)
                    and isinstance(value, dict)
                ):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value

            return result

        merged = {}
        for metadata in metadata_dicts:
            merged = deep_merge(merged, metadata)

        return merged
