"""Cross-Field Semantic Validation API Endpoint.

Phase 3: POST /api/v1/semantic-validate - Validate field compatibility using hierarchy traversal
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from agentic_neurodata_conversion.kg_service.config import get_settings
from agentic_neurodata_conversion.kg_service.db.neo4j_connection import get_neo4j_connection
from agentic_neurodata_conversion.kg_service.models.requests import SemanticValidateRequest, SemanticValidateResponse
from agentic_neurodata_conversion.kg_service.services.semantic_reasoner import SemanticReasoner, get_semantic_reasoner

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["semantic-validation"])


def get_semantic_reasoner_instance() -> SemanticReasoner:
    """Dependency to get SemanticReasoner instance."""
    settings = get_settings()
    neo4j_conn = get_neo4j_connection(
        uri=settings.neo4j_uri, user=settings.neo4j_user, password=settings.neo4j_password
    )
    return get_semantic_reasoner(neo4j_conn)


@router.post("/semantic-validate", response_model=SemanticValidateResponse)
async def semantic_validate_endpoint(
    request: SemanticValidateRequest, reasoner: SemanticReasoner = Depends(get_semantic_reasoner_instance)
):
    """Validate cross-field compatibility using semantic reasoning.

    Phase 3: Cross-field validation using ontology hierarchies.

    This endpoint checks if two ontology terms are semantically compatible
    by traversing their hierarchies. Primary use case is validating that
    anatomical structures are appropriate for a given species.

    Example:
        Valid: species=Mus musculus (mouse) + anatomy=hippocampus
        - Mouse IS_A Vertebrata
        - Hippocampus IS_A brain structure
        - Both are compatible (mammals have hippocampus)

        Invalid: species=Drosophila melanogaster (fly) + anatomy=hippocampus
        - Fly IS_A Arthropoda (invertebrate)
        - Hippocampus only exists in vertebrate brains
        - Incompatible combination

    Args:
        request: SemanticValidateRequest with species_term_id and anatomy_term_id
        reasoner: SemanticReasoner instance (injected dependency)

    Returns:
        SemanticValidateResponse with compatibility status and reasoning

    Raises:
        HTTPException: If validation fails due to service error
    """
    try:
        logger.info(f"Cross-field validation: species={request.species_term_id}, anatomy={request.anatomy_term_id}")

        # Call semantic reasoner's cross-field compatibility check
        result = await reasoner.check_cross_field_compatibility(
            species_term_id=request.species_term_id, anatomy_term_id=request.anatomy_term_id
        )

        # Convert result to response format
        # The reasoner returns: {is_compatible, confidence, reasoning, species_ancestors, anatomy_ancestors}
        return SemanticValidateResponse(
            is_compatible=result["is_compatible"],
            confidence=result["confidence"],
            reasoning=result["reasoning"],
            species_ancestors=result.get("species_ancestors", []),
            anatomy_ancestors=result.get("anatomy_ancestors", []),
            warnings=result.get("warnings", []),
        )

    except KeyError as e:
        logger.error(f"Invalid reasoner response format: missing key {e}")
        raise HTTPException(
            status_code=500, detail=f"Semantic validation failed: invalid response format (missing {e})"
        )
    except Exception as e:
        logger.error(f"Semantic validation error: {e}")
        raise HTTPException(status_code=500, detail=f"Semantic validation failed: {str(e)}")
