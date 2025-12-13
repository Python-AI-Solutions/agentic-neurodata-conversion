"""Validation API Endpoint.

POST /api/v1/validate - Quick validation check
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from agentic_neurodata_conversion.kg_service.config import get_settings
from agentic_neurodata_conversion.kg_service.db.neo4j_connection import get_neo4j_connection
from agentic_neurodata_conversion.kg_service.models.requests import ValidateRequest, ValidateResponse
from agentic_neurodata_conversion.kg_service.services.kg_service import AsyncKGService, get_kg_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["validation"])


def get_kg_service_instance() -> AsyncKGService:
    """Dependency to get KG service instance."""
    settings = get_settings()
    neo4j_conn = get_neo4j_connection(
        uri=settings.neo4j_uri,
        user=settings.neo4j_user,
        password=settings.neo4j_password,
        database=settings.neo4j_database,
    )
    return get_kg_service(neo4j_conn)


@router.post("/validate", response_model=ValidateResponse)
async def validate_endpoint(request: ValidateRequest, kg_service: AsyncKGService = Depends(get_kg_service_instance)):
    """Quick validation check for a metadata field value.

    Returns simple is_valid boolean without full normalization.
    """
    try:
        result = await kg_service.validate_field(field_path=request.field_path, value=request.value)
        return ValidateResponse(**result)

    except Exception as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=500, detail=f"Validation failed: {str(e)}")
