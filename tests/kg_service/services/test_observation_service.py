"""Unit Tests for ObservationService.

Tests for kg_service/services/observation_service.py.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from agentic_neurodata_conversion.kg_service.models.observation import Observation
from agentic_neurodata_conversion.kg_service.services.observation_service import ObservationService


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_observation():
    """Test observation storage logic."""
    mock_neo4j_connection = Mock()
    mock_neo4j_connection.execute_write = AsyncMock(return_value=[{"observation_id": "obs-123"}])

    service = ObservationService(mock_neo4j_connection)

    obs = Observation(
        field_path="subject.species",
        raw_value="mouse",
        normalized_value="Mus musculus",
        ontology_term_id="NCBITaxon:10090",
        source_type="user",
        source_file="test.nwb",
        confidence=0.95,
        provenance_json={"user_id": "test"},
    )

    result = await service.store_observation(obs)

    assert result == "obs-123"
    assert mock_neo4j_connection.execute_write.called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_observation_with_empty_provenance():
    """Test storing observation with empty provenance."""
    mock_neo4j_connection = Mock()
    mock_neo4j_connection.execute_write = AsyncMock(return_value=[{"observation_id": "obs-456"}])

    service = ObservationService(mock_neo4j_connection)

    obs = Observation(
        field_path="subject.species",
        raw_value="mouse",
        normalized_value="Mus musculus",
        ontology_term_id="NCBITaxon:10090",
        source_type="user",
        confidence=0.95,
        provenance_json={},
    )

    result = await service.store_observation(obs)

    assert result == "obs-456"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_observation_error_handling():
    """Test error handling in observation storage."""
    mock_neo4j_connection = Mock()
    mock_neo4j_connection.execute_write = AsyncMock(side_effect=Exception("Database error"))

    service = ObservationService(mock_neo4j_connection)

    obs = Observation(
        field_path="subject.species",
        raw_value="mouse",
        normalized_value="Mus musculus",
        ontology_term_id="NCBITaxon:10090",
        source_type="user",
        confidence=0.95,
    )

    with pytest.raises(Exception) as exc_info:
        await service.store_observation(obs)

    assert "Database error" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_supersede_observations():
    """Test observation superseding logic."""
    mock_neo4j_connection = Mock()
    mock_neo4j_connection.execute_write = AsyncMock(return_value=[{"count": 3}])

    service = ObservationService(mock_neo4j_connection)
    count = await service.supersede_observations("sess_123", "subject.species")

    assert count == 3
    assert mock_neo4j_connection.execute_write.called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_supersede_observations_no_matches():
    """Test superseding when no observations match."""
    mock_neo4j_connection = Mock()
    mock_neo4j_connection.execute_write = AsyncMock(return_value=[{"count": 0}])

    service = ObservationService(mock_neo4j_connection)
    count = await service.supersede_observations("nonexistent_session", "subject.species")

    assert count == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_supersede_observations_empty_result():
    """Test superseding when execute_write returns empty list."""
    mock_neo4j_connection = Mock()
    mock_neo4j_connection.execute_write = AsyncMock(return_value=[])

    service = ObservationService(mock_neo4j_connection)
    count = await service.supersede_observations("sess_123", "subject.species")

    assert count == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_store_observation_brain_region():
    """Test storing observation for brain region."""
    mock_neo4j_connection = Mock()
    mock_neo4j_connection.execute_write = AsyncMock(return_value=[{"observation_id": "obs-789"}])

    service = ObservationService(mock_neo4j_connection)

    obs = Observation(
        field_path="ecephys.ElectrodeGroup.location",
        raw_value="hippocampus",
        normalized_value="hippocampus",
        ontology_term_id="UBERON:0002421",
        source_type="user",
        source_file="test.nwb",
        confidence=1.0,
        provenance_json={"user_id": "test_user"},
    )

    result = await service.store_observation(obs)

    assert result == "obs-789"
