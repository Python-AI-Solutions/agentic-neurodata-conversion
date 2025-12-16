"""
Observations API Endpoint.

POST /api/v1/observations - Store observation
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from agentic_neurodata_conversion.kg_service.config import get_settings
from agentic_neurodata_conversion.kg_service.db.neo4j_connection import get_neo4j_connection
from agentic_neurodata_conversion.kg_service.models.observation import (
    Observation,
    ObservationCreateRequest,
    ObservationResponse,
)
from agentic_neurodata_conversion.kg_service.services.observation_service import ObservationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["observations"])


def get_observation_service() -> ObservationService:
    """Dependency to get observation service."""
    settings = get_settings()
    if not settings.graph_db.password:
        raise HTTPException(
            status_code=503, detail="KG service not configured: missing GRAPH_DB__PASSWORD/NEO4J_PASSWORD"
        )
    neo4j_conn = get_neo4j_connection(
        uri=settings.graph_db.uri,
        user=settings.graph_db.user,
        password=settings.graph_db.password,
        database=settings.graph_db.database,
    )
    return ObservationService(neo4j_conn)


@router.post("/observations", response_model=ObservationResponse)
async def create_observation(
    request: ObservationCreateRequest, service: ObservationService = Depends(get_observation_service)
):
    """Store an observation in Neo4j."""
    try:
        obs = Observation(**request.dict())
        observation_id = await service.store_observation(obs)
        return ObservationResponse(observation_id=observation_id, status="stored")
    except ValueError as e:
        # Validation errors (e.g., invalid ontology term)
        logger.warning(f"Validation error creating observation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Unexpected errors (e.g., database connection issues)
        logger.error(f"Failed to create observation: {e}")
        raise HTTPException(status_code=500, detail=f"Observation creation failed: {str(e)}")
