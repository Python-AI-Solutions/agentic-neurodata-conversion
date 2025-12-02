"""API Request/Response Models.

Pydantic models for KG service API endpoints.
"""

from typing import Any

from pydantic import BaseModel, Field


class NormalizeRequest(BaseModel):
    """Request for normalization endpoint."""

    field_path: str = Field(
        ..., description="NWB field path (e.g., subject.species)", examples=["subject.species", "subject.sex"]
    )
    value: str = Field(..., description="Raw input value to normalize", examples=["mouse", "Mus musculus", "male"])
    context: dict[str, Any] | None = Field(None, description="Optional context (source_file, etc.)")


class NormalizeResponse(BaseModel):
    """Response from normalization endpoint."""

    field_path: str = Field(..., description="Field path that was normalized")
    raw_value: str = Field(..., description="Original input value")
    normalized_value: str | None = Field(None, description="Normalized value")
    ontology_term_id: str | None = Field(None, description="Ontology term ID")
    match_type: str | None = Field(None, description="Type of match (exact/synonym)")
    confidence: float = Field(..., description="Confidence score (0.0-1.0)")
    status: str = Field(..., description="Status (validated/needs_review/not_applicable)")
    action_required: bool = Field(..., description="Whether user action needed")
    warnings: list[str] = Field(default_factory=list, description="Warning messages")


class ValidateRequest(BaseModel):
    """Request for validation endpoint."""

    field_path: str = Field(..., description="NWB field path")
    value: str = Field(..., description="Value to validate")


class ValidateResponse(BaseModel):
    """Response from validation endpoint."""

    is_valid: bool = Field(..., description="Whether value is valid")
    confidence: float = Field(..., description="Confidence score")
    warnings: list[str] = Field(default_factory=list, description="Warnings")
