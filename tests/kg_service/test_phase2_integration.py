"""Phase 2 Integration Tests.

End-to-end tests for Phase 2 normalization and validation endpoints.
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

    from agentic_neurodata_conversion.kg_service.config import get_settings, reset_settings
    from agentic_neurodata_conversion.kg_service.db.neo4j_connection import get_neo4j_connection, reset_neo4j_connection
    from agentic_neurodata_conversion.kg_service.main import app
    from agentic_neurodata_conversion.kg_service.services.kg_service import reset_kg_service

    # Reset all singletons to avoid state pollution between tests
    reset_settings()
    reset_neo4j_connection()
    reset_kg_service()

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
async def test_health_endpoint(kg_service_client):
    """Test health check endpoint."""
    response = await kg_service_client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "neo4j" in data
    assert "version" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_root_endpoint(kg_service_client):
    """Test root endpoint."""
    response = await kg_service_client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["service"] == "NWB Knowledge Graph"
    assert "endpoints" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_normalize_exact_match(kg_service_client):
    """Test /api/v1/normalize endpoint with exact match."""
    response = await kg_service_client.post(
        "/api/v1/normalize", json={"field_path": "subject.species", "value": "Mus musculus"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["field_path"] == "subject.species"
    assert data["raw_value"] == "Mus musculus"
    assert data["status"] == "validated"
    assert data["match_type"] == "exact"
    assert data["confidence"] == 1.0
    assert data["normalized_value"] == "Mus musculus"
    assert data["ontology_term_id"] == "NCBITaxon:10090"
    assert data["action_required"] is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_normalize_synonym_match(kg_service_client):
    """Test synonym matching through API."""
    response = await kg_service_client.post(
        "/api/v1/normalize", json={"field_path": "subject.species", "value": "mouse"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "validated"
    assert data["match_type"] == "synonym"
    assert data["confidence"] == 0.95
    assert data["normalized_value"] == "Mus musculus"
    assert data["ontology_term_id"] == "NCBITaxon:10090"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_normalize_case_insensitive(kg_service_client):
    """Test case-insensitive matching."""
    response = await kg_service_client.post(
        "/api/v1/normalize", json={"field_path": "subject.species", "value": "MUS MUSCULUS"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "validated"
    assert data["match_type"] == "exact"
    assert data["normalized_value"] == "Mus musculus"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_normalize_needs_review(kg_service_client):
    """Test normalization when no match found."""
    response = await kg_service_client.post(
        "/api/v1/normalize", json={"field_path": "subject.species", "value": "unicorn"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "needs_review"
    assert data["confidence"] == 0.0
    assert data["match_type"] is None
    assert data["normalized_value"] is None
    assert data["action_required"] is True
    assert len(data["warnings"]) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_normalize_brain_region(kg_service_client):
    """Test UBERON brain region normalization."""
    response = await kg_service_client.post(
        "/api/v1/normalize", json={"field_path": "ecephys.ElectrodeGroup.location", "value": "hippocampus"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "validated"
    assert "UBERON:" in data["ontology_term_id"]
    # hippocampus matches to Ammon's horn (UBERON:0001954) via synonym
    assert data["ontology_term_id"] == "UBERON:0001954"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_normalize_with_context(kg_service_client):
    """Test normalization with context."""
    response = await kg_service_client.post(
        "/api/v1/normalize",
        json={
            "field_path": "subject.species",
            "value": "Mus musculus",
            "context": {"source_file": "test.nwb", "user_id": "test_user"},
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "validated"
    assert data["confidence"] == 1.0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_normalize_not_ontology_governed(kg_service_client):
    """Test normalization for non-ontology-governed field."""
    response = await kg_service_client.post(
        "/api/v1/normalize", json={"field_path": "subject.subject_id", "value": "ABC123"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "not_applicable"
    assert data["confidence"] == 0.0  # Not ontology-governed fields have 0.0 confidence
    assert data["action_required"] is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_validate_valid(kg_service_client):
    """Test /api/v1/validate endpoint with valid value."""
    response = await kg_service_client.post(
        "/api/v1/validate", json={"field_path": "subject.species", "value": "Mus musculus"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["is_valid"] is True
    assert data["confidence"] == 1.0
    assert len(data["warnings"]) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_validate_invalid(kg_service_client):
    """Test validation endpoint with invalid value."""
    response = await kg_service_client.post(
        "/api/v1/validate", json={"field_path": "subject.species", "value": "unicorn"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["is_valid"] is False
    assert data["confidence"] == 0.0
    assert len(data["warnings"]) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_validate_synonym(kg_service_client):
    """Test validation with synonym (still valid)."""
    response = await kg_service_client.post(
        "/api/v1/validate", json={"field_path": "subject.species", "value": "mouse"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["is_valid"] is True
    assert data["confidence"] == 0.95


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_normalize_rat(kg_service_client):
    """Test normalization for rat species."""
    response = await kg_service_client.post(
        "/api/v1/normalize", json={"field_path": "subject.species", "value": "Rattus norvegicus"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "validated"
    assert data["match_type"] == "exact"
    assert data["ontology_term_id"] == "NCBITaxon:10116"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_normalize_human(kg_service_client):
    """Test normalization for human species."""
    response = await kg_service_client.post(
        "/api/v1/normalize", json={"field_path": "subject.species", "value": "Homo sapiens"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "validated"
    assert data["ontology_term_id"] == "NCBITaxon:9606"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_normalize_multiple_brain_regions(kg_service_client):
    """Test normalization for multiple brain regions."""
    # hippocampus matches to Ammon's horn (UBERON:0001954) via synonym
    brain_regions = [("hippocampus", "UBERON:0001954"), ("thalamus", "UBERON:0001869"), ("neocortex", "UBERON:0001950")]

    for region, expected_id in brain_regions:
        response = await kg_service_client.post(
            "/api/v1/normalize", json={"field_path": "ecephys.ElectrodeGroup.location", "value": region}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "validated"
        assert data["ontology_term_id"] == expected_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_normalize_whitespace_handling(kg_service_client):
    """Test that extra whitespace is handled correctly."""
    response = await kg_service_client.post(
        "/api/v1/normalize", json={"field_path": "subject.species", "value": "  Mus musculus  "}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "validated"
    assert data["normalized_value"] == "Mus musculus"
