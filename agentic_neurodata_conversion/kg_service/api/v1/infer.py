"""Inference API Endpoint.

POST /api/v1/infer - Infer metadata value based on historical observations
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from agentic_neurodata_conversion.kg_service.config import get_settings
from agentic_neurodata_conversion.kg_service.db.neo4j_connection import get_neo4j_connection
from agentic_neurodata_conversion.kg_service.services.inference_engine import InferenceEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["inference"])


class InferRequest(BaseModel):
    """Request model for inference endpoint.

    Attributes:
        field_path: Metadata field path (e.g., "subject.species")
        source_file: Current file being processed
        subject_id: Subject identifier to look up historical observations
    """

    field_path: str = Field(..., description="Metadata field path (e.g., 'subject.species')")
    source_file: str = Field(..., description="Current file being processed")
    subject_id: str = Field(..., description="Subject identifier for historical lookup")


class InferResponse(BaseModel):
    """Response model for inference endpoint.

    Attributes:
        has_suggestion: Whether a suggestion is available
        suggested_value: Suggested value (null if no suggestion)
        ontology_term_id: Ontology term ID (null if no suggestion)
        confidence: Confidence score (0.8 for suggestions, 0.0 otherwise)
        requires_confirmation: Whether user confirmation is required
        reasoning: Explanation of inference result
        evidence_count: Number of supporting observations (only if has_suggestion=True)
        contributing_sessions: List of sessions that contributed evidence (only if has_suggestion=True)
        subject_id: Subject identifier used for historical lookup (only if has_suggestion=True)
    """

    has_suggestion: bool
    suggested_value: str | None
    ontology_term_id: str | None
    confidence: float
    requires_confirmation: bool
    reasoning: str
    evidence_count: int | None = None
    contributing_sessions: list[dict] | None = None
    subject_id: str | None = None


def get_inference_engine() -> InferenceEngine:
    """Dependency to get InferenceEngine instance.

    Creates a new InferenceEngine with Neo4j connection based on
    current settings.

    Returns:
        InferenceEngine: Configured inference engine instance
    """
    settings = get_settings()
    neo4j_conn = get_neo4j_connection(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
    )
    return InferenceEngine(neo4j_conn)


@router.post("/infer", response_model=InferResponse)
async def infer_endpoint(request: InferRequest, engine: InferenceEngine = Depends(get_inference_engine)):
    """Infer metadata value based on historical observations.

    Analyzes historical observations for the same subject across
    different files to suggest a value for the requested field.

    Currently supports:
    - subject.species: Requires ≥2 observations with 100% agreement

    Args:
        request: InferRequest with field_path, source_file, subject_id
        engine: InferenceEngine instance (injected dependency)

    Returns:
        InferResponse with suggestion and reasoning

    Raises:
        HTTPException: 500 if inference fails

    Example:
        >>> POST /api/v1/infer
        >>> {
        >>>   "field_path": "subject.species",
        >>>   "source_file": "subject_001_session_C.nwb",
        >>>   "subject_id": "subject_001"
        >>> }
        >>>
        >>> Response:
        >>> {
        >>>   "has_suggestion": true,
        >>>   "suggested_value": "Mus musculus",
        >>>   "ontology_term_id": "NCBITaxon:10090",
        >>>   "confidence": 0.8,
        >>>   "requires_confirmation": true,
        >>>   "reasoning": "Based on 2 prior observations with 100% agreement"
        >>> }
    """
    try:
        logger.info(
            f"Inference request: field_path={request.field_path}, "
            f"subject_id={request.subject_id}, source_file={request.source_file}"
        )

        # Route to appropriate inference method based on field_path
        result = await engine.infer_field(
            field_path=request.field_path, subject_id=request.subject_id, target_file=request.source_file
        )

        logger.info(f"Inference result: has_suggestion={result['has_suggestion']}, confidence={result['confidence']}")

        return InferResponse(**result)

    except Exception as e:
        logger.error(f"Inference error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")
