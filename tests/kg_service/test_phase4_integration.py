"""Phase 4 Integration Tests.

End-to-end tests for Phase 4 species inference functionality.
Tests the full inference workflow with Neo4j backend.
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

    # Clean up test observations before each test
    await neo4j_conn.execute_write(
        "MATCH (obs:Observation) WHERE obs.subject_id STARTS WITH 'subject_phase4_' DETACH DELETE obs"
    )

    # Create HTTP client with ASGI transport
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Cleanup
    await neo4j_conn.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_infer_species_sufficient_evidence(kg_service_client):
    """Test inference with ≥2 observations with 100% agreement.

    Workflow:
    1. Store 2 observations for subject_phase4_001 with species "Mus musculus"
    2. Call /infer for same subject with different file
    3. Verify suggestion is returned with confidence 0.8
    """
    subject_id = "subject_phase4_001"

    # Store first observation
    response1 = await kg_service_client.post(
        "/api/v1/observations",
        json={
            "field_path": "subject.species",
            "raw_value": "Mus musculus",
            "normalized_value": "Mus musculus",
            "ontology_term_id": "NCBITaxon:10090",
            "source_type": "user",
            "source_file": f"{subject_id}_session_A.nwb",
            "confidence": 1.0,
            "provenance_json": {"subject_id": subject_id, "user_id": "test_user", "session_id": "test_session"},
        },
    )
    assert response1.status_code == 200

    # Store second observation
    response2 = await kg_service_client.post(
        "/api/v1/observations",
        json={
            "field_path": "subject.species",
            "raw_value": "Mus musculus",
            "normalized_value": "Mus musculus",
            "ontology_term_id": "NCBITaxon:10090",
            "source_type": "user",
            "source_file": f"{subject_id}_session_B.nwb",
            "confidence": 1.0,
            "provenance_json": {"subject_id": subject_id, "user_id": "test_user", "session_id": "test_session"},
        },
    )
    assert response2.status_code == 200

    # Call inference endpoint for new session
    infer_response = await kg_service_client.post(
        "/api/v1/infer",
        json={
            "field_path": "subject.species",
            "source_file": f"{subject_id}_session_C.nwb",
            "subject_id": subject_id,
        },
    )

    assert infer_response.status_code == 200
    data = infer_response.json()

    assert data["has_suggestion"] is True
    assert data["suggested_value"] == "Mus musculus"
    assert data["ontology_term_id"] == "NCBITaxon:10090"
    assert data["confidence"] == 0.8
    assert data["requires_confirmation"] is True
    assert "2 prior observations" in data["reasoning"]
    assert "100% agreement" in data["reasoning"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_infer_species_insufficient_evidence_single_observation(kg_service_client):
    """Test inference with only 1 observation (insufficient).

    Should return no suggestion.
    """
    subject_id = "subject_phase4_002"

    # Store only one observation
    response1 = await kg_service_client.post(
        "/api/v1/observations",
        json={
            "field_path": "subject.species",
            "raw_value": "Rattus norvegicus",
            "normalized_value": "Rattus norvegicus",
            "ontology_term_id": "NCBITaxon:10116",
            "source_type": "user",
            "source_file": f"{subject_id}_session_A.nwb",
            "confidence": 1.0,
            "provenance_json": {"subject_id": subject_id, "user_id": "test_user", "session_id": "test_session"},
        },
    )
    assert response1.status_code == 200

    # Call inference endpoint
    infer_response = await kg_service_client.post(
        "/api/v1/infer",
        json={
            "field_path": "subject.species",
            "source_file": f"{subject_id}_session_B.nwb",
            "subject_id": subject_id,
        },
    )

    assert infer_response.status_code == 200
    data = infer_response.json()

    assert data["has_suggestion"] is False
    assert data["suggested_value"] is None
    assert data["ontology_term_id"] is None
    assert data["confidence"] == 0.0
    assert data["requires_confirmation"] is False
    assert "Insufficient evidence" in data["reasoning"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_infer_species_no_observations(kg_service_client):
    """Test inference for subject with no historical observations.

    Should return no suggestion.
    """
    subject_id = "subject_phase4_never_seen"

    # Call inference without storing any observations
    infer_response = await kg_service_client.post(
        "/api/v1/infer",
        json={
            "field_path": "subject.species",
            "source_file": f"{subject_id}_first_session.nwb",
            "subject_id": subject_id,
        },
    )

    assert infer_response.status_code == 200
    data = infer_response.json()

    assert data["has_suggestion"] is False
    assert data["confidence"] == 0.0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_infer_species_three_observations(kg_service_client):
    """Test inference with 3 observations (more than minimum).

    Should still return confidence 0.8.
    """
    subject_id = "subject_phase4_003"

    # Store three observations
    for session in ["A", "B", "C"]:
        response = await kg_service_client.post(
            "/api/v1/observations",
            json={
                "field_path": "subject.species",
                "raw_value": "Homo sapiens",
                "normalized_value": "Homo sapiens",
                "ontology_term_id": "NCBITaxon:9606",
                "source_type": "user",
                "source_file": f"{subject_id}_session_{session}.nwb",
                "confidence": 1.0,
                "provenance_json": {"subject_id": subject_id, "user_id": "test_user", "session_id": "test_session"},
            },
        )
        assert response.status_code == 200

    # Call inference for new session
    infer_response = await kg_service_client.post(
        "/api/v1/infer",
        json={
            "field_path": "subject.species",
            "source_file": f"{subject_id}_session_D.nwb",
            "subject_id": subject_id,
        },
    )

    assert infer_response.status_code == 200
    data = infer_response.json()

    assert data["has_suggestion"] is True
    assert data["suggested_value"] == "Homo sapiens"
    assert data["confidence"] == 0.8
    assert "3 prior observations" in data["reasoning"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_infer_species_conflicting_observations(kg_service_client):
    """Test inference with conflicting observations (not 100% agreement).

    Should return no suggestion.
    """
    subject_id = "subject_phase4_004"

    # Store observation for Mus musculus
    response1 = await kg_service_client.post(
        "/api/v1/observations",
        json={
            "field_path": "subject.species",
            "raw_value": "Mus musculus",
            "normalized_value": "Mus musculus",
            "ontology_term_id": "NCBITaxon:10090",
            "source_type": "user",
            "source_file": f"{subject_id}_session_A.nwb",
            "confidence": 1.0,
            "provenance_json": {"subject_id": subject_id, "user_id": "test_user", "session_id": "test_session"},
        },
    )
    assert response1.status_code == 200

    # Store conflicting observation for Rattus norvegicus
    response2 = await kg_service_client.post(
        "/api/v1/observations",
        json={
            "field_path": "subject.species",
            "raw_value": "Rattus norvegicus",
            "normalized_value": "Rattus norvegicus",
            "ontology_term_id": "NCBITaxon:10116",
            "source_type": "user",
            "source_file": f"{subject_id}_session_B.nwb",
            "confidence": 1.0,
            "provenance_json": {"subject_id": subject_id, "user_id": "test_user", "session_id": "test_session"},
        },
    )
    assert response2.status_code == 200

    # Call inference - should return no suggestion due to conflict
    infer_response = await kg_service_client.post(
        "/api/v1/infer",
        json={
            "field_path": "subject.species",
            "source_file": f"{subject_id}_session_C.nwb",
            "subject_id": subject_id,
        },
    )

    assert infer_response.status_code == 200
    data = infer_response.json()

    assert data["has_suggestion"] is False
    assert data["confidence"] == 0.0
    assert "Insufficient evidence" in data["reasoning"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_infer_species_excludes_target_file(kg_service_client):
    """Test that inference excludes observations from target file.

    Ensures we don't use the current file's data to infer for itself.
    """
    subject_id = "subject_phase4_005"

    # Store observation in target file
    response1 = await kg_service_client.post(
        "/api/v1/observations",
        json={
            "field_path": "subject.species",
            "raw_value": "Mus musculus",
            "normalized_value": "Mus musculus",
            "ontology_term_id": "NCBITaxon:10090",
            "source_type": "user",
            "source_file": f"{subject_id}_session_TARGET.nwb",
            "confidence": 1.0,
        },
    )
    assert response1.status_code == 200

    # Call inference for the same file - should have insufficient evidence
    infer_response = await kg_service_client.post(
        "/api/v1/infer",
        json={
            "field_path": "subject.species",
            "source_file": f"{subject_id}_session_TARGET.nwb",
            "subject_id": subject_id,
        },
    )

    assert infer_response.status_code == 200
    data = infer_response.json()

    # Should have no suggestion because target file is excluded
    assert data["has_suggestion"] is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_infer_unsupported_field(kg_service_client):
    """Test inference for unsupported field path.

    Currently only subject.species is supported.
    """
    subject_id = "subject_phase4_006"

    infer_response = await kg_service_client.post(
        "/api/v1/infer",
        json={
            "field_path": "subject.age",
            "source_file": f"{subject_id}_session_A.nwb",
            "subject_id": subject_id,
        },
    )

    assert infer_response.status_code == 200
    data = infer_response.json()

    assert data["has_suggestion"] is False
    assert data["confidence"] == 0.0
    assert "not supported" in data["reasoning"]
    assert "subject.age" in data["reasoning"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_infer_species_from_inferred_observations(kg_service_client):
    """Test inference works with observations that were themselves inferred.

    This tests the full loop where inference results can be stored
    as observations and used for future inferences.
    """
    subject_id = "subject_phase4_007"

    # Store observations marked as "inferred"
    for session in ["A", "B"]:
        response = await kg_service_client.post(
            "/api/v1/observations",
            json={
                "field_path": "subject.species",
                "raw_value": "Mus musculus",
                "normalized_value": "Mus musculus",
                "ontology_term_id": "NCBITaxon:10090",
                "source_type": "inferred",
                "source_file": f"{subject_id}_session_{session}.nwb",
                "confidence": 0.8,
                "provenance_json": {"subject_id": subject_id, "inference_rule": "species_consistency"},
            },
        )
        assert response.status_code == 200

    # Infer for new session - should work with inferred observations
    infer_response = await kg_service_client.post(
        "/api/v1/infer",
        json={
            "field_path": "subject.species",
            "source_file": f"{subject_id}_session_C.nwb",
            "subject_id": subject_id,
        },
    )

    assert infer_response.status_code == 200
    data = infer_response.json()

    assert data["has_suggestion"] is True
    assert data["suggested_value"] == "Mus musculus"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_infer_species_multiple_subjects_isolation(kg_service_client):
    """Test that inference correctly isolates observations by subject.

    Subject A and Subject B should not influence each other's inferences.
    """
    subject_a = "subject_phase4_008a"
    subject_b = "subject_phase4_008b"

    # Store observations for Subject A (Mus musculus)
    for session in ["A", "B"]:
        response = await kg_service_client.post(
            "/api/v1/observations",
            json={
                "field_path": "subject.species",
                "raw_value": "Mus musculus",
                "normalized_value": "Mus musculus",
                "ontology_term_id": "NCBITaxon:10090",
                "source_type": "user",
                "source_file": f"{subject_a}_session_{session}.nwb",
                "confidence": 1.0,
                "provenance_json": {"subject_id": subject_a, "user_id": "test_user", "session_id": "test_session"},
            },
        )
        assert response.status_code == 200

    # Store observations for Subject B (Rattus norvegicus)
    for session in ["A", "B"]:
        response = await kg_service_client.post(
            "/api/v1/observations",
            json={
                "field_path": "subject.species",
                "raw_value": "Rattus norvegicus",
                "normalized_value": "Rattus norvegicus",
                "ontology_term_id": "NCBITaxon:10116",
                "source_type": "user",
                "source_file": f"{subject_b}_session_{session}.nwb",
                "confidence": 1.0,
                "provenance_json": {"subject_id": subject_b, "user_id": "test_user", "session_id": "test_session"},
            },
        )
        assert response.status_code == 200

    # Infer for Subject A - should get Mus musculus
    infer_a = await kg_service_client.post(
        "/api/v1/infer",
        json={
            "field_path": "subject.species",
            "source_file": f"{subject_a}_session_C.nwb",
            "subject_id": subject_a,
        },
    )
    assert infer_a.status_code == 200
    data_a = infer_a.json()
    assert data_a["suggested_value"] == "Mus musculus"

    # Infer for Subject B - should get Rattus norvegicus
    infer_b = await kg_service_client.post(
        "/api/v1/infer",
        json={
            "field_path": "subject.species",
            "source_file": f"{subject_b}_session_C.nwb",
            "subject_id": subject_b,
        },
    )
    assert infer_b.status_code == 200
    data_b = infer_b.json()
    assert data_b["suggested_value"] == "Rattus norvegicus"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_infer_with_inactive_observations(kg_service_client):
    """Test that inference only uses active observations.

    Inactive observations should be excluded from inference.
    """
    subject_id = "subject_phase4_009"

    # Store 2 active observations
    for session in ["A", "B"]:
        response = await kg_service_client.post(
            "/api/v1/observations",
            json={
                "field_path": "subject.species",
                "raw_value": "Mus musculus",
                "normalized_value": "Mus musculus",
                "ontology_term_id": "NCBITaxon:10090",
                "source_type": "user",
                "source_file": f"{subject_id}_session_{session}.nwb",
                "confidence": 1.0,
                "provenance_json": {"subject_id": subject_id, "user_id": "test_user", "session_id": "test_session"},
            },
        )
        assert response.status_code == 200

    # Infer - should work
    infer_response = await kg_service_client.post(
        "/api/v1/infer",
        json={
            "field_path": "subject.species",
            "source_file": f"{subject_id}_session_C.nwb",
            "subject_id": subject_id,
        },
    )
    assert infer_response.status_code == 200
    data = infer_response.json()
    assert data["has_suggestion"] is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_inference_workflow(kg_service_client):
    """Test complete inference workflow: normalize -> observe -> infer.

    This tests the integration of all phases working together.
    """
    subject_id = "subject_phase4_010"

    # Step 1: Normalize species values
    normalize_response = await kg_service_client.post(
        "/api/v1/normalize",
        json={
            "field_path": "subject.species",
            "value": "mouse",
        },
    )
    assert normalize_response.status_code == 200
    norm_data = normalize_response.json()

    # Step 2: Store normalized observations for two sessions
    for session in ["A", "B"]:
        observe_response = await kg_service_client.post(
            "/api/v1/observations",
            json={
                "field_path": "subject.species",
                "raw_value": "mouse",
                "normalized_value": norm_data["normalized_value"],
                "ontology_term_id": norm_data["ontology_term_id"],
                "source_type": "user",
                "source_file": f"{subject_id}_session_{session}.nwb",
                "confidence": norm_data["confidence"],
                "provenance_json": {"subject_id": subject_id, "user_id": "test_user", "session_id": "test_session"},
            },
        )
        assert observe_response.status_code == 200

    # Step 3: Infer species for new session
    infer_response = await kg_service_client.post(
        "/api/v1/infer",
        json={
            "field_path": "subject.species",
            "source_file": f"{subject_id}_session_C.nwb",
            "subject_id": subject_id,
        },
    )
    assert infer_response.status_code == 200
    infer_data = infer_response.json()

    # Step 4: Verify inference result
    assert infer_data["has_suggestion"] is True
    assert infer_data["suggested_value"] == "Mus musculus"
    assert infer_data["ontology_term_id"] == "NCBITaxon:10090"
    assert infer_data["confidence"] == 0.8
    assert infer_data["requires_confirmation"] is True

    # Step 5: Store inferred observation (completing the loop)
    final_observe_response = await kg_service_client.post(
        "/api/v1/observations",
        json={
            "field_path": "subject.species",
            "raw_value": infer_data["suggested_value"],
            "normalized_value": infer_data["suggested_value"],
            "ontology_term_id": infer_data["ontology_term_id"],
            "source_type": "inferred",
            "source_file": f"{subject_id}_session_C.nwb",
            "confidence": infer_data["confidence"],
            "provenance_json": {
                "subject_id": subject_id,
                "inference_rule": "species_consistency",
                "reasoning": infer_data["reasoning"],
            },
        },
    )
    assert final_observe_response.status_code == 200
