"""Normalization API Endpoint.

POST /api/v1/normalize - Normalize metadata field value
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from agentic_neurodata_conversion.kg_service.config import get_settings
from agentic_neurodata_conversion.kg_service.db.neo4j_connection import get_neo4j_connection
from agentic_neurodata_conversion.kg_service.models.requests import NormalizeRequest, NormalizeResponse
from agentic_neurodata_conversion.kg_service.services.kg_service import AsyncKGService, get_kg_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["normalization"])


def get_kg_service_instance() -> AsyncKGService:
    """Dependency to get KG service instance."""
    settings = get_settings()
    neo4j_conn = get_neo4j_connection(
        uri=settings.neo4j_uri, user=settings.neo4j_user, password=settings.neo4j_password
    )
    return get_kg_service(neo4j_conn)


@router.post("/normalize", response_model=NormalizeResponse)
async def normalize_endpoint(request: NormalizeRequest, kg_service: AsyncKGService = Depends(get_kg_service_instance)):
    """Normalize a metadata field value.

    Runs 3-stage normalization:
    1. Exact match (confidence 1.0)
    2. Synonym match (confidence 0.95)
    3. Needs review (confidence 0.0)
    """
    try:
        result = await kg_service.normalize_field(
            field_path=request.field_path, value=request.value, context=request.context
        )
        return NormalizeResponse(**result)

    except Exception as e:
        logger.error(f"Normalization error: {e}")
        raise HTTPException(status_code=500, detail=f"Normalization failed: {str(e)}")
