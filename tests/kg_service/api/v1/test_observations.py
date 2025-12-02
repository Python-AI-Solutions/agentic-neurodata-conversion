"""Unit Tests for Observations API.

Tests for kg_service/api/v1/observations.py.
"""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from agentic_neurodata_conversion.kg_service.api.v1.observations import create_observation
from agentic_neurodata_conversion.kg_service.models.observation import ObservationCreateRequest


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_observation_success():
    """Test successful observation creation via API."""
    mock_service = Mock()
    mock_service.store_observation = AsyncMock(return_value="obs-123")

    request = ObservationCreateRequest(
        field_path="subject.species",
        raw_value="mouse",
        normalized_value="Mus musculus",
        ontology_term_id="NCBITaxon:10090",
        source_type="user",
        source_file="test.nwb",
        confidence=0.95,
        provenance_json={"user_id": "test_user"},
    )

    response = await create_observation(request, mock_service)

    assert response.observation_id == "obs-123"
    assert response.status == "stored"
    assert mock_service.store_observation.called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_observation_minimal():
    """Test observation creation with minimal fields."""
    mock_service = Mock()
    mock_service.store_observation = AsyncMock(return_value="obs-456")

    request = ObservationCreateRequest(
        field_path="subject.species", raw_value="mouse", source_type="user", confidence=0.8
    )

    response = await create_observation(request, mock_service)

    assert response.observation_id == "obs-456"
    assert response.status == "stored"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_observation_error():
    """Test error handling in observation creation."""
    mock_service = Mock()
    mock_service.store_observation = AsyncMock(side_effect=Exception("Database connection failed"))

    request = ObservationCreateRequest(
        field_path="subject.species", raw_value="mouse", source_type="user", confidence=0.95
    )

    with pytest.raises(HTTPException) as exc_info:
        await create_observation(request, mock_service)

    assert exc_info.value.status_code == 500
    assert "Observation creation failed" in exc_info.value.detail


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_observation_brain_region():
    """Test creating observation for brain region."""
    mock_service = Mock()
    mock_service.store_observation = AsyncMock(return_value="obs-789")

    request = ObservationCreateRequest(
        field_path="ecephys.ElectrodeGroup.location",
        raw_value="hippocampus",
        normalized_value="hippocampus",
        ontology_term_id="UBERON:0002421",
        source_type="user",
        confidence=1.0,
    )

    response = await create_observation(request, mock_service)

    assert response.observation_id == "obs-789"
    assert response.status == "stored"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_observation_with_provenance():
    """Test observation creation with full provenance."""
    mock_service = Mock()
    mock_service.store_observation = AsyncMock(return_value="obs-999")

    request = ObservationCreateRequest(
        field_path="subject.species",
        raw_value="Rattus norvegicus",
        normalized_value="Rattus norvegicus",
        ontology_term_id="NCBITaxon:10116",
        source_type="user",
        source_file="session_001.nwb",
        confidence=1.0,
        provenance_json={"user_id": "user123", "session_id": "sess_456", "timestamp": "2025-12-02T10:00:00Z"},
    )

    response = await create_observation(request, mock_service)

    assert response.observation_id == "obs-999"
    assert response.status == "stored"
