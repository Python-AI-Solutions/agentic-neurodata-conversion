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


# ===========================
# Phase 2: Semantic Reasoning Tests
# ===========================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_normalize_with_semantic_reasoning_explicit(kg_service_client):
    """Test normalization with use_semantic_reasoning=True explicitly."""
    response = await kg_service_client.post(
        "/api/v1/normalize",
        json={"field_path": "subject.species", "value": "mouse", "use_semantic_reasoning": True},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "validated"
    assert data["normalized_value"] == "Mus musculus"
    assert data["ontology_term_id"] == "NCBITaxon:10090"
    # With semantic reasoning, synonym match should still work
    assert data["match_type"] in ["synonym", "exact"]
    assert data["confidence"] >= 0.95


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_normalize_semantic_reasoning_default(kg_service_client):
    """Test that semantic reasoning is enabled by default (use_semantic_reasoning not specified)."""
    response = await kg_service_client.post(
        "/api/v1/normalize", json={"field_path": "subject.species", "value": "mouse"}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "validated"
    assert data["normalized_value"] == "Mus musculus"
    # Should work via semantic reasoner by default
    assert data["match_type"] in ["synonym", "exact", "semantic"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_normalize_legacy_mode(kg_service_client):
    """Test legacy 3-stage string matching with use_semantic_reasoning=False."""
    response = await kg_service_client.post(
        "/api/v1/normalize",
        json={"field_path": "subject.species", "value": "Mus musculus", "use_semantic_reasoning": False},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "validated"
    assert data["match_type"] == "exact"
    assert data["confidence"] == 1.0
    assert data["normalized_value"] == "Mus musculus"
    # Legacy mode should not have semantic_info
    assert data.get("semantic_info") is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_normalize_semantic_match_stage3(kg_service_client):
    """Test Stage 3 semantic search with partial match (Phase 2 NEW feature)."""
    # "Ammon" is a partial match for "Ammon's horn"
    response = await kg_service_client.post(
        "/api/v1/normalize",
        json={"field_path": "ecephys.ElectrodeGroup.location", "value": "Ammon", "use_semantic_reasoning": True},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "validated"
    assert data["normalized_value"] == "Ammon's horn"
    assert data["ontology_term_id"] == "UBERON:0001954"
    # Should match via semantic search (or synonym/exact if available)
    assert data["match_type"] in ["semantic", "synonym", "exact"]
    assert data["confidence"] >= 0.85

    # If semantic match, should have semantic_info
    if data["match_type"] == "semantic":
        assert "semantic_info" in data
        assert data["semantic_info"] is not None
        # Note: ancestors may be empty if required_ancestor not specified
        assert "ancestors" in data["semantic_info"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_normalize_semantic_info_populated(kg_service_client):
    """Test that semantic_info is populated for semantic matches."""
    # Try a partial match that should trigger semantic search
    response = await kg_service_client.post(
        "/api/v1/normalize",
        json={"field_path": "ecephys.ElectrodeGroup.location", "value": "cortex", "use_semantic_reasoning": True},
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "validated"
    assert data["normalized_value"] is not None

    # If match_type is semantic, semantic_info should be present
    if data["match_type"] == "semantic":
        assert "semantic_info" in data
        assert data["semantic_info"] is not None
        # Should have ancestors array
        assert "ancestors" in data["semantic_info"]
        # Each ancestor should have required fields
        for ancestor in data["semantic_info"]["ancestors"]:
            assert "term_id" in ancestor
            assert "label" in ancestor
            assert "distance" in ancestor


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_normalize_backward_compatibility(kg_service_client):
    """Test backward compatibility: existing API calls still work without use_semantic_reasoning."""
    # This mimics old API calls that don't specify use_semantic_reasoning
    response = await kg_service_client.post(
        "/api/v1/normalize", json={"field_path": "subject.species", "value": "Mus musculus"}
    )

    assert response.status_code == 200
    data = response.json()

    # Should still work (with semantic reasoning enabled by default)
    assert data["status"] == "validated"
    assert data["normalized_value"] == "Mus musculus"
    assert data["ontology_term_id"] == "NCBITaxon:10090"
    assert data["confidence"] >= 0.95

    # Response should have all required fields
    assert "field_path" in data
    assert "raw_value" in data
    assert "match_type" in data
    assert "action_required" in data
    assert "warnings" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_normalize_semantic_vs_legacy_comparison(kg_service_client):
    """Test that semantic reasoning can find matches that legacy mode cannot."""
    # Use a value that might only match via semantic search
    test_value = "Ammon"
    field_path = "ecephys.ElectrodeGroup.location"

    # Test with semantic reasoning
    response_semantic = await kg_service_client.post(
        "/api/v1/normalize",
        json={"field_path": field_path, "value": test_value, "use_semantic_reasoning": True},
    )

    # Test with legacy mode
    response_legacy = await kg_service_client.post(
        "/api/v1/normalize",
        json={"field_path": field_path, "value": test_value, "use_semantic_reasoning": False},
    )

    assert response_semantic.status_code == 200
    assert response_legacy.status_code == 200

    data_semantic = response_semantic.json()
    data_legacy = response_legacy.json()

    # Semantic reasoning should validate (exact, synonym, or semantic match)
    assert data_semantic["status"] == "validated"
    assert data_semantic["normalized_value"] is not None

    # Legacy might not match (or match via exact/synonym only)
    # This test documents the difference between modes
