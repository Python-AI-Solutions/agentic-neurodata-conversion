"""Phase 3 Integration Tests.

End-to-end tests for Phase 3 observation storage with provenance.
Tests the full FastAPI application with Neo4j backend.
"""

import os

import httpx
import pytest


@pytest.fixture
async def kg_service_client():
    """Fixture for async HTTP client with FastAPI app."""
    # Skip if NEO4J_PASSWORD not set (e.g., in CI)
    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        pytest.skip("NEO4J_PASSWORD not set - integration tests require local Neo4j instance")

    from agentic_neurodata_conversion.kg_service.config import get_settings
    from agentic_neurodata_conversion.kg_service.db.neo4j_connection import get_neo4j_connection, reset_neo4j_connection
    from agentic_neurodata_conversion.kg_service.main import app

    # Reset connection to avoid singleton issues
    reset_neo4j_connection()

    # Get Neo4j connection and connect
    settings = get_settings()
    neo4j_conn = get_neo4j_connection(
        uri=settings.neo4j_uri, user=settings.neo4j_user, password=settings.neo4j_password
    )

    # Try to connect, skip if Neo4j isn't running
    try:
        await neo4j_conn.connect()
    except Exception as e:
        pytest.skip(f"Neo4j not accessible: {e}")

    # Create HTTP client with ASGI transport
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Cleanup
    await neo4j_conn.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_store_observation_api(kg_service_client):
    """Test POST /api/v1/observations endpoint."""
    response = await kg_service_client.post(
        "/api/v1/observations",
        json={
            "field_path": "subject.species",
            "raw_value": "mouse",
            "normalized_value": "Mus musculus",
            "ontology_term_id": "NCBITaxon:10090",
            "source_type": "user",
            "source_file": "test.nwb",
            "confidence": 0.95,
            "provenance_json": {"user_id": "test_user"},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "observation_id" in data
    assert data["status"] == "stored"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_store_observation_minimal(kg_service_client):
    """Test storing observation with minimal fields."""
    response = await kg_service_client.post(
        "/api/v1/observations",
        json={"field_path": "subject.species", "raw_value": "mouse", "source_type": "user", "confidence": 0.8},
    )

    assert response.status_code == 200
    data = response.json()
    assert "observation_id" in data
    assert data["status"] == "stored"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_store_observation_brain_region(kg_service_client):
    """Test storing observation for brain region."""
    response = await kg_service_client.post(
        "/api/v1/observations",
        json={
            "field_path": "ecephys.ElectrodeGroup.location",
            "raw_value": "hippocampus",
            "normalized_value": "hippocampus",
            "ontology_term_id": "UBERON:0002421",
            "source_type": "user",
            "source_file": "test.nwb",
            "confidence": 1.0,
            "provenance_json": {"user_id": "test_user"},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "observation_id" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_store_observation_with_full_provenance(kg_service_client):
    """Test observation with full provenance metadata."""
    response = await kg_service_client.post(
        "/api/v1/observations",
        json={
            "field_path": "subject.species",
            "raw_value": "Rattus norvegicus",
            "normalized_value": "Rattus norvegicus",
            "ontology_term_id": "NCBITaxon:10116",
            "source_type": "user",
            "source_file": "session_002.nwb",
            "confidence": 1.0,
            "provenance_json": {
                "user_id": "user123",
                "session_id": "sess_456",
                "timestamp": "2025-12-02T10:00:00Z",
                "conversion_method": "manual",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "observation_id" in data
    assert data["status"] == "stored"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_store_observation_inferred_source(kg_service_client):
    """Test storing observation with inferred source type."""
    response = await kg_service_client.post(
        "/api/v1/observations",
        json={
            "field_path": "subject.species",
            "raw_value": "mouse",
            "normalized_value": "Mus musculus",
            "ontology_term_id": "NCBITaxon:10090",
            "source_type": "inferred",
            "source_file": "test.nwb",
            "confidence": 0.8,
            "provenance_json": {"inference_rule": "species_consistency"},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "observation_id" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_store_multiple_observations(kg_service_client):
    """Test storing multiple observations sequentially."""
    observations = [
        {
            "field_path": "subject.species",
            "raw_value": "mouse",
            "normalized_value": "Mus musculus",
            "ontology_term_id": "NCBITaxon:10090",
            "source_type": "user",
            "confidence": 0.95,
        },
        {
            "field_path": "ecephys.ElectrodeGroup.location",
            "raw_value": "thalamus",
            "normalized_value": "thalamus",
            "ontology_term_id": "UBERON:0001869",
            "source_type": "user",
            "confidence": 1.0,
        },
        {
            "field_path": "ecephys.ElectrodeGroup.location",
            "raw_value": "neocortex",
            "normalized_value": "neocortex",
            "ontology_term_id": "UBERON:0001950",
            "source_type": "user",
            "confidence": 1.0,
        },
    ]

    observation_ids = []
    for obs_data in observations:
        response = await kg_service_client.post("/api/v1/observations", json=obs_data)
        assert response.status_code == 200
        data = response.json()
        assert "observation_id" in data
        observation_ids.append(data["observation_id"])

    # Verify all IDs are unique
    assert len(observation_ids) == len(set(observation_ids))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_store_observation_different_field_paths(kg_service_client):
    """Test observations for different field paths."""
    field_paths = [
        ("subject.species", "mouse", "Mus musculus", "NCBITaxon:10090"),
        ("subject.sex", "male", "male", None),
        ("ecephys.ElectrodeGroup.location", "hippocampus", "hippocampus", "UBERON:0002421"),
    ]

    for field_path, raw_value, normalized_value, ontology_term_id in field_paths:
        response = await kg_service_client.post(
            "/api/v1/observations",
            json={
                "field_path": field_path,
                "raw_value": raw_value,
                "normalized_value": normalized_value,
                "ontology_term_id": ontology_term_id,
                "source_type": "user",
                "confidence": 1.0,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "observation_id" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_store_observation_empty_provenance(kg_service_client):
    """Test observation with empty provenance JSON."""
    response = await kg_service_client.post(
        "/api/v1/observations",
        json={
            "field_path": "subject.species",
            "raw_value": "mouse",
            "normalized_value": "Mus musculus",
            "ontology_term_id": "NCBITaxon:10090",
            "source_type": "user",
            "confidence": 0.95,
            "provenance_json": {},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "observation_id" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_observation_endpoint_validation():
    """Test that observation endpoint validates required fields."""
    # This test doesn't need the full fixture, just checks validation
    from pydantic import ValidationError

    from agentic_neurodata_conversion.kg_service.models.observation import ObservationCreateRequest

    with pytest.raises(ValidationError):
        ObservationCreateRequest(
            # Missing required fields: field_path, raw_value, source_type, confidence
            field_path="subject.species"
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_store_observation_various_confidence_levels(kg_service_client):
    """Test observations with various confidence levels."""
    confidence_levels = [0.0, 0.5, 0.8, 0.95, 1.0]

    for confidence in confidence_levels:
        response = await kg_service_client.post(
            "/api/v1/observations",
            json={
                "field_path": "subject.species",
                "raw_value": "mouse",
                "normalized_value": "Mus musculus",
                "ontology_term_id": "NCBITaxon:10090",
                "source_type": "user",
                "confidence": confidence,
                "provenance_json": {"confidence_level": str(confidence)},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "observation_id" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_store_observation_different_source_types(kg_service_client):
    """Test observations with different source types."""
    source_types = ["user", "inferred", "nwb_file", "specification"]

    for source_type in source_types:
        response = await kg_service_client.post(
            "/api/v1/observations",
            json={
                "field_path": "subject.species",
                "raw_value": "mouse",
                "normalized_value": "Mus musculus",
                "ontology_term_id": "NCBITaxon:10090",
                "source_type": source_type,
                "confidence": 0.9,
                "provenance_json": {"source_type_test": source_type},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "observation_id" in data
