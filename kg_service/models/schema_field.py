"""Schema Field Model.

Represents an NWB metadata field and its validation rules.
Defines which fields require ontology validation and which ontologies to use.

Schema fields map NWB metadata paths (e.g., subject.species) to their validation
requirements, including whether they're required, ontology-governed, and what
types of values are expected.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class SchemaField(BaseModel):
    """NWB schema field with ontology governance info.

    Defines metadata field validation requirements for NWB files. Fields can be
    marked as ontology-governed, which requires values to match terms from the
    specified ontology for validation to pass.

    Attributes:
        field_path: Dot-notation path to field in NWB structure
        description: Human-readable description of the field
        required: Whether this field must be present in valid NWB files
        ontology_governed: Whether values must match ontology terms
        ontology: Which ontology to use for validation (if ontology_governed=True)
        value_type: Expected data type (string, array[string], datetime, etc.)
        examples: Example valid values for this field
    """

    field_path: str = Field(
        ...,
        description="Dot-notation path to field (e.g., subject.species)",
        examples=["subject.species", "subject.sex", "general.surgery"]
    )
    description: str = Field(
        ...,
        description="Human-readable description of the field"
    )
    required: bool = Field(
        ...,
        description="Whether this field is required in NWB files"
    )
    ontology_governed: bool = Field(
        ...,
        description="Whether this field should be validated against an ontology"
    )
    ontology: Optional[str] = Field(
        None,
        description="Which ontology to use for validation",
        examples=["NCBITaxonomy", "UBERON", "PATO"]
    )
    value_type: str = Field(
        ...,
        description="Expected value type",
        examples=["string", "array[string]", "datetime"]
    )
    examples: List[str] = Field(
        default_factory=list,
        description="Example values for this field"
    )

    class Config:
        """Pydantic model configuration with example."""
        json_schema_extra = {
            "example": {
                "field_path": "subject.species",
                "description": "Species of experimental subject",
                "required": True,
                "ontology_governed": True,
                "ontology": "NCBITaxonomy",
                "value_type": "string",
                "examples": ["Mus musculus", "Rattus norvegicus"]
            }
        }
