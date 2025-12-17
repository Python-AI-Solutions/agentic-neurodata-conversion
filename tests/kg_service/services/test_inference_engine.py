"""Unit tests for InferenceEngine.

Tests the species consistency inference rule with various evidence scenarios.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from agentic_neurodata_conversion.kg_service.services.inference_engine import InferenceEngine


@pytest.fixture
def mock_neo4j_connection():
    """Mock Neo4j connection for testing."""
    conn = Mock()
    conn.execute_read = AsyncMock()
    return conn


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_species_sufficient_evidence(mock_neo4j_connection):
    """Test inference with ≥2 observations and 100% agreement.

    Should return:
    - has_suggestion: True
    - confidence: 0.8
    - suggested_value: species label
    - ontology_term_id: NCBITaxon ID
    """
    # Mock: 2 observations, all agree on Mus musculus
    mock_neo4j_connection.execute_read = AsyncMock(
        return_value=[
            {
                "suggested_value": "Mus musculus",
                "ontology_term_id": "NCBITaxon:10090",
                "evidence_count": 2,
            }
        ]
    )

    engine = InferenceEngine(mock_neo4j_connection)

    result = await engine.infer_species(subject_id="subject_001", target_file="session_C.nwb")

    assert result["has_suggestion"] is True
    assert result["suggested_value"] == "Mus musculus"
    assert result["ontology_term_id"] == "NCBITaxon:10090"
    assert result["confidence"] == 0.8
    assert result["requires_confirmation"] is True
    assert "2 prior observations" in result["reasoning"]
    assert "100% agreement" in result["reasoning"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_species_three_observations(mock_neo4j_connection):
    """Test inference with 3 observations (more than minimum).

    Should still return confidence 0.8 with 3 observations.
    """
    mock_neo4j_connection.execute_read = AsyncMock(
        return_value=[
            {
                "suggested_value": "Rattus norvegicus",
                "ontology_term_id": "NCBITaxon:10116",
                "evidence_count": 3,
            }
        ]
    )

    engine = InferenceEngine(mock_neo4j_connection)

    result = await engine.infer_species(subject_id="subject_002", target_file="new_session.nwb")

    assert result["has_suggestion"] is True
    assert result["confidence"] == 0.8
    assert "3 prior observations" in result["reasoning"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_species_insufficient_evidence_single_observation(mock_neo4j_connection):
    """Test inference with only 1 observation (insufficient).

    Should return:
    - has_suggestion: False
    - confidence: 0.0
    - reasoning explains insufficient evidence
    """
    # Mock: Only 1 observation (needs ≥2)
    mock_neo4j_connection.execute_read = AsyncMock(return_value=[])

    engine = InferenceEngine(mock_neo4j_connection)

    result = await engine.infer_species(subject_id="subject_003", target_file="test.nwb")

    assert result["has_suggestion"] is False
    assert result["suggested_value"] is None
    assert result["ontology_term_id"] is None
    assert result["confidence"] == 0.0
    assert result["requires_confirmation"] is False
    assert "Insufficient evidence" in result["reasoning"]
    assert "≥2 observations" in result["reasoning"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_species_no_observations(mock_neo4j_connection):
    """Test inference with no observations at all.

    Should return no suggestion.
    """
    mock_neo4j_connection.execute_read = AsyncMock(return_value=[])

    engine = InferenceEngine(mock_neo4j_connection)

    result = await engine.infer_species(subject_id="subject_new", target_file="first_session.nwb")

    assert result["has_suggestion"] is False
    assert result["confidence"] == 0.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_species_conflicting_evidence(mock_neo4j_connection):
    """Test inference with conflicting observations (not 100% agreement).

    If observations disagree, Cypher query returns no results
    because WHERE size(all_species) = 1 fails.

    Should return no suggestion.
    """
    # Mock: Conflicting evidence - query returns empty because of disagreement
    mock_neo4j_connection.execute_read = AsyncMock(return_value=[])

    engine = InferenceEngine(mock_neo4j_connection)

    result = await engine.infer_species(subject_id="subject_conflicted", target_file="session_D.nwb")

    assert result["has_suggestion"] is False
    assert result["confidence"] == 0.0
    assert "Insufficient evidence" in result["reasoning"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_species_excludes_target_file(mock_neo4j_connection):
    """Test that inference excludes observations from target file.

    The target_file parameter should be passed to query to exclude
    observations from the current file being processed.
    """
    mock_neo4j_connection.execute_read = AsyncMock(
        return_value=[
            {
                "suggested_value": "Homo sapiens",
                "ontology_term_id": "NCBITaxon:9606",
                "evidence_count": 2,
            }
        ]
    )

    engine = InferenceEngine(mock_neo4j_connection)

    target_file = "subject_001_session_C.nwb"
    result = await engine.infer_species(subject_id="subject_001", target_file=target_file)

    # Verify execute_read was called with correct parameters
    mock_neo4j_connection.execute_read.assert_called_once()
    call_args = mock_neo4j_connection.execute_read.call_args
    params = call_args[0][1]  # Second argument is params dict

    assert params["target_file"] == target_file
    assert params["subject_id"] == "subject_001"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_field_species(mock_neo4j_connection):
    """Test infer_field routing to infer_species."""
    mock_neo4j_connection.execute_read = AsyncMock(
        return_value=[
            {
                "suggested_value": "Mus musculus",
                "ontology_term_id": "NCBITaxon:10090",
                "evidence_count": 2,
            }
        ]
    )

    engine = InferenceEngine(mock_neo4j_connection)

    result = await engine.infer_field(field_path="subject.species", subject_id="subject_001", target_file="test.nwb")

    assert result["has_suggestion"] is True
    assert result["suggested_value"] == "Mus musculus"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_field_unsupported_field(mock_neo4j_connection):
    """Test infer_field with field that has no observations.

    Should return no suggestion with insufficient evidence reasoning.
    Note: infer_field now supports all fields, but returns no suggestion
    if there's insufficient historical data.
    """
    # Mock no observations found for subject.age
    mock_neo4j_connection.execute_read = AsyncMock(return_value=[])

    engine = InferenceEngine(mock_neo4j_connection)

    result = await engine.infer_field(field_path="subject.age", subject_id="subject_001", target_file="test.nwb")

    assert result["has_suggestion"] is False
    assert result["confidence"] == 0.0
    assert "Insufficient evidence" in result["reasoning"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_species_database_error(mock_neo4j_connection):
    """Test inference when database query raises exception.

    Should propagate the exception to caller.
    """
    mock_neo4j_connection.execute_read = AsyncMock(side_effect=Exception("Database connection error"))

    engine = InferenceEngine(mock_neo4j_connection)

    with pytest.raises(Exception, match="Database connection error"):
        await engine.infer_species(subject_id="subject_001", target_file="test.nwb")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_species_query_structure(mock_neo4j_connection):
    """Test that Cypher query has correct structure.

    Verifies:
    - Query filters by field_path='subject.species'
    - Query checks is_active=true
    - Query requires evidence_count >= 2
    - Query requires size(all_species) = 1 (100% agreement)
    - Query joins with OntologyTerm
    """
    mock_neo4j_connection.execute_read = AsyncMock(
        return_value=[
            {
                "suggested_value": "Mus musculus",
                "ontology_term_id": "NCBITaxon:10090",
                "evidence_count": 2,
            }
        ]
    )

    engine = InferenceEngine(mock_neo4j_connection)

    await engine.infer_species(subject_id="subject_001", target_file="target.nwb")

    # Get the query that was executed
    call_args = mock_neo4j_connection.execute_read.call_args
    query = call_args[0][0]  # First argument is query string

    # Verify key requirements in query
    assert "field_path: 'subject.species'" in query
    assert "is_active = true" in query
    assert "evidence_count >= 2" in query
    assert "size(all_species) = 1" in query
    assert "MATCH (term:OntologyTerm)" in query
    # Verify subject_id property access (extracted from provenance_json for efficient querying)
    assert "obs.subject_id = $subject_id" in query
    assert "AND obs.source_file <> $target_file" in query


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_species_returns_all_required_fields(mock_neo4j_connection):
    """Test that inference result contains all required fields."""
    mock_neo4j_connection.execute_read = AsyncMock(
        return_value=[
            {
                "suggested_value": "Mus musculus",
                "ontology_term_id": "NCBITaxon:10090",
                "evidence_count": 2,
            }
        ]
    )

    engine = InferenceEngine(mock_neo4j_connection)

    result = await engine.infer_species(subject_id="subject_001", target_file="test.nwb")

    # Verify all required fields are present
    required_fields = [
        "has_suggestion",
        "suggested_value",
        "ontology_term_id",
        "confidence",
        "requires_confirmation",
        "reasoning",
    ]

    for field in required_fields:
        assert field in result, f"Missing required field: {field}"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_species_empty_subject_id(mock_neo4j_connection):
    """Test inference with empty subject_id.

    Should query database but likely return no results.
    """
    mock_neo4j_connection.execute_read = AsyncMock(return_value=[])

    engine = InferenceEngine(mock_neo4j_connection)

    result = await engine.infer_species(subject_id="", target_file="test.nwb")

    assert result["has_suggestion"] is False
    # Verify query was still executed with empty subject_id
    mock_neo4j_connection.execute_read.assert_called_once()


# ===========================
# Phase 4: Semantic Reasoning Tests (NEW)
# ===========================


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_field_with_semantic_context(mock_neo4j_connection):
    """Test that inference includes semantic hierarchy context in reasoning.

    Phase 4: When ontology_term_id is present, reasoning should include
    ancestor hierarchy from ontology.
    """
    mock_neo4j_connection.execute_read = AsyncMock(
        return_value=[
            {
                "suggested_value": "Mus musculus",
                "ontology_term_id": "NCBITaxon:10090",
                "evidence_count": 2,
                "contributing_sessions": [
                    {"source_file": "session_A.nwb", "created_at": "2024-08-15T10:30:00"},
                    {"source_file": "session_B.nwb", "created_at": "2024-08-20T14:22:00"},
                ],
            }
        ]
    )

    engine = InferenceEngine(mock_neo4j_connection)

    # Mock semantic_reasoner.find_ancestors to return hierarchy
    engine.semantic_reasoner.find_ancestors = AsyncMock(
        return_value=[
            {"term_id": "NCBITaxon:10088", "label": "Mus", "distance": 1},
            {"term_id": "NCBITaxon:10066", "label": "Muridae", "distance": 2},
            {"term_id": "NCBITaxon:9989", "label": "Rodentia", "distance": 3},
            {"term_id": "NCBITaxon:40674", "label": "Mammalia", "distance": 4},
            {"term_id": "NCBITaxon:7742", "label": "Vertebrata", "distance": 5},
        ]
    )

    result = await engine.infer_field(field_path="subject.species", subject_id="subject_001", target_file="test.nwb")

    # Verify suggestion is present
    assert result["has_suggestion"] is True
    assert result["suggested_value"] == "Mus musculus"

    # Verify semantic context is included in reasoning
    assert "Term hierarchy:" in result["reasoning"]
    assert "Mus" in result["reasoning"]
    assert "Muridae" in result["reasoning"]
    assert "Rodentia" in result["reasoning"]
    assert "Mammalia" in result["reasoning"]
    assert "Vertebrata" in result["reasoning"]

    # Verify hierarchy is formatted with " > " separator
    assert "Mus > Muridae > Rodentia > Mammalia > Vertebrata" in result["reasoning"]

    # Verify find_ancestors was called with correct term_id
    engine.semantic_reasoner.find_ancestors.assert_called_once_with("NCBITaxon:10090", max_depth=10)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_field_semantic_context_error_graceful_degradation(mock_neo4j_connection):
    """Test graceful degradation when semantic context fetch fails.

    Phase 4: If hierarchy traversal fails, inference should continue
    without semantic context (log warning but don't fail).
    """
    mock_neo4j_connection.execute_read = AsyncMock(
        return_value=[
            {
                "suggested_value": "Rattus norvegicus",
                "ontology_term_id": "NCBITaxon:10116",
                "evidence_count": 3,
                "contributing_sessions": [{"source_file": "session.nwb", "created_at": "2024-08-15T10:30:00"}],
            }
        ]
    )

    engine = InferenceEngine(mock_neo4j_connection)

    # Mock semantic_reasoner.find_ancestors to raise an exception
    engine.semantic_reasoner.find_ancestors = AsyncMock(side_effect=Exception("Neo4j connection error"))

    result = await engine.infer_field(field_path="subject.species", subject_id="subject_002", target_file="test.nwb")

    # Verify inference still succeeds despite semantic context failure
    assert result["has_suggestion"] is True
    assert result["suggested_value"] == "Rattus norvegicus"
    assert result["confidence"] == 0.8

    # Verify reasoning is present but WITHOUT semantic context
    assert "Based on 3 prior observations with 100% agreement" in result["reasoning"]
    assert "Term hierarchy:" not in result["reasoning"]  # Semantic context should be absent

    # Verify find_ancestors was attempted
    engine.semantic_reasoner.find_ancestors.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_infer_field_no_semantic_context_for_non_ontology_field(mock_neo4j_connection):
    """Test that non-ontology fields don't attempt to fetch semantic context.

    Phase 4: Fields without ontology_term_id (e.g., experimenter, institution)
    should not try to fetch hierarchy.
    """
    mock_neo4j_connection.execute_read = AsyncMock(
        return_value=[
            {
                "suggested_value": "John Doe",
                "ontology_term_id": None,  # No ontology term for experimenter field
                "evidence_count": 4,
                "contributing_sessions": [{"source_file": "session.nwb", "created_at": "2024-08-15T10:30:00"}],
            }
        ]
    )

    engine = InferenceEngine(mock_neo4j_connection)

    # Mock semantic_reasoner.find_ancestors (should NOT be called)
    engine.semantic_reasoner.find_ancestors = AsyncMock()

    result = await engine.infer_field(field_path="experimenter", subject_id="subject_001", target_file="test.nwb")

    # Verify inference succeeds
    assert result["has_suggestion"] is True
    assert result["suggested_value"] == "John Doe"

    # Verify reasoning is present but WITHOUT semantic context
    assert "Based on 4 prior observations with 100% agreement" in result["reasoning"]
    assert "Term hierarchy:" not in result["reasoning"]

    # Verify find_ancestors was NOT called (no ontology term)
    engine.semantic_reasoner.find_ancestors.assert_not_called()
