"""API Request/Response Models.

Pydantic models for KG service API endpoints.
"""

from typing import Any

from pydantic import BaseModel, Field


class NormalizeRequest(BaseModel):
    """Request for normalization endpoint.

    Phase 2: Added use_semantic_reasoning parameter for hierarchy-aware validation.
    """

    field_path: str = Field(
        ..., description="NWB field path (e.g., subject.species)", examples=["subject.species", "subject.sex"]
    )
    value: str = Field(..., description="Raw input value to normalize", examples=["mouse", "Mus musculus", "male"])
    context: dict[str, Any] | None = Field(None, description="Optional context (source_file, etc.)")
    use_semantic_reasoning: bool = Field(
        True,
        description="Use 4-stage semantic validation with hierarchy traversal (default: True). "
        "If False, uses legacy 3-stage string matching.",
    )


class NormalizeResponse(BaseModel):
    """Response from normalization endpoint.

    Phase 2: Added semantic_info field for hierarchy details when using semantic reasoning.
    """

    field_path: str = Field(..., description="Field path that was normalized")
    raw_value: str = Field(..., description="Original input value")
    normalized_value: str | None = Field(None, description="Normalized value")
    ontology_term_id: str | None = Field(None, description="Ontology term ID")
    match_type: str | None = Field(None, description="Type of match (exact/synonym/semantic)")
    confidence: float = Field(..., description="Confidence score (0.0-1.0)")
    status: str = Field(..., description="Status (validated/needs_review/not_applicable)")
    action_required: bool = Field(..., description="Whether user action needed")
    warnings: list[str] = Field(default_factory=list, description="Warning messages")
    semantic_info: dict[str, Any] | None = Field(None, description="Optional semantic hierarchy details")


class ValidateRequest(BaseModel):
    """Request for validation endpoint."""

    field_path: str = Field(..., description="NWB field path")
    value: str = Field(..., description="Value to validate")


class ValidateResponse(BaseModel):
    """Response from validation endpoint."""

    is_valid: bool = Field(..., description="Whether value is valid")
    confidence: float = Field(..., description="Confidence score")
    warnings: list[str] = Field(default_factory=list, description="Warnings")


class SemanticValidateRequest(BaseModel):
    """Request for cross-field semantic validation endpoint.

    Phase 3: Cross-field validation using ontology hierarchies.
    """

    species_term_id: str = Field(
        ...,
        description="Species ontology term ID (e.g., NCBITaxon:10090)",
        examples=["NCBITaxon:10090", "NCBITaxon:9606"],
    )
    anatomy_term_id: str = Field(
        ...,
        description="Anatomy ontology term ID (e.g., UBERON:0002421)",
        examples=["UBERON:0002421", "UBERON:0001950"],
    )


class SemanticValidateResponse(BaseModel):
    """Response from cross-field semantic validation endpoint.

    Phase 3: Returns compatibility assessment with semantic reasoning.
    """

    is_compatible: bool = Field(..., description="Whether the field combination is semantically compatible")
    confidence: float = Field(..., description="Confidence score (0.0-1.0)")
    reasoning: str = Field(..., description="Explanation of compatibility decision using hierarchy traversal")
    species_ancestors: list[str] = Field(
        default_factory=list, description="Key taxonomic ancestors found (e.g., Vertebrata, Mammalia)"
    )
    anatomy_ancestors: list[str] = Field(
        default_factory=list, description="Key anatomical ancestors found (e.g., brain, nervous system)"
    )
    warnings: list[str] = Field(default_factory=list, description="Warning messages if any")
