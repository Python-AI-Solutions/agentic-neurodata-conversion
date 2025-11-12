"""Strict Pydantic validation for NWB metadata.

This module provides strict validation for all metadata fields before conversion,
catching errors immediately with helpful messages instead of failing during conversion.
"""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NWBMetadata(BaseModel):
    """Strict validation for NWB metadata fields.

    Ensures all metadata meets NWB specification and DANDI requirements
    BEFORE conversion starts, providing immediate, helpful error messages.
    """

    # ============================================================
    # REQUIRED FIELDS (by DANDI archive)
    # NOTE: Made Optional to allow partial metadata during upload
    # Full validation happens before conversion in conversation_agent
    # ============================================================

    session_description: str | None = Field(
        None,
        min_length=10,
        max_length=1000,
        description="Description of what was recorded in this session (required before conversion)",
        examples=["Recording of V1 neurons during visual stimulation with oriented gratings"],
    )

    experimenter: list[str] | None = Field(
        None,
        min_length=1,
        max_length=10,
        description="Names of people who performed the experiment (required before conversion)",
    )

    institution: str | None = Field(
        None,
        min_length=2,
        max_length=200,
        description="Institution where experiment was performed (required before conversion)",
        examples=["Massachusetts Institute of Technology", "MIT"],
    )

    # ============================================================
    # OPTIONAL BUT RECOMMENDED FIELDS
    # ============================================================

    lab: str | None = Field(
        None,
        max_length=200,
        description="Lab where experiment was performed",
        examples=["Smith Lab", "Neural Systems Lab"],
    )

    session_start_time: datetime | None = Field(
        None, description="When the session started (ISO 8601 format)", examples=["2024-03-15T14:30:00-05:00"]
    )

    experiment_description: str | None = Field(
        None,
        max_length=2000,
        description="General description of the experiment",
        examples=["Investigation of orientation selectivity in mouse V1"],
    )

    session_id: str | None = Field(None, max_length=100, description="Unique identifier for this session")

    keywords: list[str] = Field(default_factory=list, max_length=20, description="Keywords describing the experiment")

    related_publications: list[str] = Field(
        default_factory=list, max_length=10, description="DOIs or URLs of related publications"
    )

    protocol: str | None = Field(None, max_length=500, description="Experimental protocol")

    notes: str | None = Field(None, max_length=2000, description="Additional notes about the session")

    # ============================================================
    # SUBJECT METADATA
    # ============================================================

    subject_id: str | None = Field(
        None,
        min_length=1,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Unique identifier for the subject",
        examples=["mouse001", "rat-123", "subject_A1"],
    )

    species: str | None = Field(
        None,
        max_length=100,
        description="Species in binomial nomenclature (Genus species)",
        examples=["Mus musculus", "Rattus norvegicus", "Homo sapiens"],
    )

    age: str | None = Field(
        None,
        pattern=r"^P(\d+[DWMY])+$",
        description="Age in ISO 8601 duration format",
        examples=["P90D", "P3M", "P2Y6M"],
    )

    sex: str | None = Field(None, pattern=r"^[MFUO]$", description="Sex: M (male), F (female), U (unknown), O (other)")

    weight: str | None = Field(
        None, pattern=r"^\d+(\.\d+)?\s*(g|kg)$", description="Weight with units", examples=["25.5 g", "0.5 kg"]
    )

    description: str | None = Field(None, max_length=500, description="Additional description of the subject")

    strain: str | None = Field(
        None, max_length=100, description="Strain of the subject", examples=["C57BL/6J", "Sprague Dawley"]
    )

    genotype: str | None = Field(None, max_length=200, description="Genotype of the subject")

    # ============================================================
    # CUSTOM VALIDATORS
    # ============================================================

    @field_validator("experimenter", mode="before")
    @classmethod
    def validate_experimenter(cls, v):
        """Convert single string to list, validate each name, remove XSS."""
        if v is None:
            return None  # Allow None during upload

        if isinstance(v, str):
            v = [v]

        if not isinstance(v, list):
            raise ValueError("experimenter must be a string or list of strings")

        validated = []
        for name in v:
            name = str(name).strip()
            if not name:
                raise ValueError("Experimenter name cannot be empty")
            if len(name) > 100:
                raise ValueError(f"Experimenter name too long (max 100 chars): {name[:50]}...")
            # Security: Remove potential XSS/injection
            if any(char in name for char in ["<", ">", "script", "javascript:", "onerror="]):
                raise ValueError(f"Invalid characters in experimenter name: {name}")
            validated.append(name)

        if not validated:
            raise ValueError("At least one experimenter is required")

        return validated

    @field_validator("species")
    @classmethod
    def validate_species_format(cls, v):
        """Ensure species is in binomial nomenclature."""
        if v is None:
            return v

        v = v.strip()

        # Check for common mistakes (common names instead of binomial)
        common_names = {
            "mouse": "Mus musculus",
            "rat": "Rattus norvegicus",
            "human": "Homo sapiens",
            "monkey": "Macaca mulatta",
            "macaque": "Macaca mulatta",
            "fly": "Drosophila melanogaster",
            "worm": "Caenorhabditis elegans",
            "zebrafish": "Danio rerio",
            "cat": "Felis catus",
            "dog": "Canis familiaris",
        }

        if v.lower() in common_names:
            suggestion = common_names[v.lower()]
            raise ValueError(
                f"Species must be in binomial nomenclature (Genus species), not common name. '{v}' → '{suggestion}'"
            )

        # Check format (two words)
        if " " not in v:
            raise ValueError(
                f"Species must be binomial nomenclature (two words): '{v}' is invalid. Example: 'Mus musculus'"
            )

        parts = v.split()
        if len(parts) != 2:
            raise ValueError(f"Species must be exactly two words (Genus species): '{v}' has {len(parts)} words")

        genus, species_name = parts
        if not genus[0].isupper():
            raise ValueError(f"Genus must be capitalized: '{genus}' → '{genus.capitalize()} {species_name}'")

        if not species_name[0].islower():
            raise ValueError(f"Species must be lowercase: '{genus} {species_name}' → '{genus} {species_name.lower()}'")

        return v

    @field_validator("age")
    @classmethod
    def validate_age_format(cls, v):
        """Validate ISO 8601 duration format and provide helpful error."""
        if v is None:
            return v

        v = v.strip().upper()  # Normalize to uppercase

        # Check format
        if not v.startswith("P"):
            raise ValueError(
                f"Age must be ISO 8601 duration starting with 'P': '{v}' is invalid. "
                f"Examples: 'P90D' (90 days), 'P3M' (3 months), 'P2Y' (2 years)"
            )

        # Validate pattern
        pattern = r"^P(\d+[DWMY])+$"
        if not re.match(pattern, v):
            raise ValueError(
                f"Age format invalid: '{v}'. Use ISO 8601 duration format. "
                f"Examples: 'P90D' (days), 'P12W' (weeks), 'P3M' (months), 'P2Y6M' (years+months)"
            )

        return v

    @field_validator("session_description")
    @classmethod
    def validate_session_description(cls, v):
        """Ensure description is meaningful, not placeholder text."""
        if v is None:
            return None  # Allow None during upload

        v = v.strip()

        # Check for placeholder text
        placeholders = ["test", "testing", "asdf", "lorem ipsum", "todo", "fix me", "tbd", "xxx"]
        if any(placeholder in v.lower() for placeholder in placeholders):
            raise ValueError(
                f"Session description appears to be placeholder text: '{v}'. "
                f"Please provide a meaningful description. "
                f"Example: 'Recording of V1 neurons during visual stimulation'"
            )

        # Check minimum words (at least 3)
        words = v.split()
        if len(words) < 3:
            raise ValueError(
                f"Session description too short: '{v}' (only {len(words)} words). "
                f"Please provide at least 3 words. "
                f"Example: 'Recording of mouse V1 neurons'"
            )

        return v

    @field_validator("keywords", mode="before")
    @classmethod
    def validate_keywords(cls, v):
        """Parse and validate keywords list."""
        if v is None:
            return []

        # Allow comma-separated string
        if isinstance(v, str):
            v = [kw.strip() for kw in v.split(",")]

        if not isinstance(v, list):
            raise ValueError("keywords must be a list or comma-separated string")

        validated = []
        for kw in v:
            kw = str(kw).strip()
            if not kw:
                continue
            if len(kw) > 50:
                raise ValueError(f"Keyword too long (max 50 chars): {kw[:50]}...")
            # Security check
            if any(char in kw for char in ["<", ">", "script"]):
                raise ValueError(f"Invalid characters in keyword: {kw}")
            validated.append(kw)

        return validated

    @field_validator("sex")
    @classmethod
    def validate_sex(cls, v):
        """Normalize sex value."""
        if v is None:
            return v

        v = v.strip().upper()

        if v not in ["M", "F", "U", "O"]:
            raise ValueError(f"Sex must be M (male), F (female), U (unknown), or O (other). Got: '{v}'")

        return v

    @field_validator("weight")
    @classmethod
    def validate_weight(cls, v):
        """Validate weight format."""
        if v is None:
            return v

        v = v.strip()

        # Parse number and unit
        pattern = r"^(\d+(?:\.\d+)?)\s*(g|kg)$"
        match = re.match(pattern, v, re.IGNORECASE)

        if not match:
            raise ValueError(
                f"Weight must be in format '<number> g' or '<number> kg'. Got: '{v}'. Examples: '25.5 g', '0.5 kg'"
            )

        number, unit = match.groups()
        number = float(number)
        unit = unit.lower()

        # Sanity checks
        if unit == "g" and number > 100000:
            raise ValueError(f"Weight seems too large: {number} g. Did you mean kg?")

        if unit == "kg" and number > 1000:
            raise ValueError(f"Weight seems too large: {number} kg")

        if number <= 0:
            raise ValueError(f"Weight must be positive: {number} {unit}")

        return v

    # ============================================================
    # MODEL CONFIGURATION
    # ============================================================

    model_config = ConfigDict(
        # Security: Prevent extra fields
        extra="forbid",
        # Strip whitespace from strings
        str_strip_whitespace=True,
        # Use enum values
        use_enum_values=True,
        # Example for API docs
        json_schema_extra={
            "examples": [
                {
                    "session_description": "Recording of V1 neurons during visual stimulation with oriented gratings",
                    "experimenter": ["Dr. Jane Smith", "Dr. John Doe"],
                    "institution": "Massachusetts Institute of Technology",
                    "lab": "Neural Systems Lab",
                    "session_start_time": "2024-03-15T14:30:00-05:00",
                    "keywords": ["visual cortex", "V1", "electrophysiology", "neuropixels"],
                    "subject_id": "mouse001",
                    "species": "Mus musculus",
                    "age": "P90D",
                    "sex": "M",
                    "weight": "25.5 g",
                }
            ]
        },
    )
