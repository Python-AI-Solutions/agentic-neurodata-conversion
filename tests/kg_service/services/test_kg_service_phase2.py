"""Phase 2 Unit Tests: Semantic Reasoner Integration with KG Service.

Tests the integration of SemanticReasoner into AsyncKGService.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from agentic_neurodata_conversion.kg_service.services.kg_service import AsyncKGService


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_field_with_semantic_reasoning_exact_match():
    """Test normalization with semantic reasoning - exact match."""
    mock_conn = Mock()

    # Mock SemanticReasoner's validate_with_hierarchy response
    mock_semantic_response = {
        "field_path": "subject.species",
        "raw_value": "Mus musculus",
        "normalized_value": "Mus musculus",
        "ontology_term_id": "NCBITaxon:10090",
        "match_type": "exact",
        "confidence": 1.0,
        "status": "validated",
        "action_required": False,
        "warnings": [],
        "semantic_info": None,
    }

    service = AsyncKGService(mock_conn)

    # Mock the semantic_reasoner.validate_with_hierarchy method
    service.semantic_reasoner.validate_with_hierarchy = AsyncMock(return_value=mock_semantic_response)

    result = await service.normalize_field(
        field_path="subject.species", value="Mus musculus", use_semantic_reasoning=True
    )

    assert result["status"] == "validated"
    assert result["match_type"] == "exact"
    assert result["confidence"] == 1.0
    assert result["normalized_value"] == "Mus musculus"
    assert result["ontology_term_id"] == "NCBITaxon:10090"
    assert result["action_required"] is False

    # Verify semantic reasoner was called
    service.semantic_reasoner.validate_with_hierarchy.assert_called_once_with(
        field_path="subject.species", value="Mus musculus", required_ancestor=None
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_field_with_semantic_reasoning_synonym_match():
    """Test normalization with semantic reasoning - synonym match."""
    mock_conn = Mock()

    mock_semantic_response = {
        "field_path": "subject.species",
        "raw_value": "mouse",
        "normalized_value": "Mus musculus",
        "ontology_term_id": "NCBITaxon:10090",
        "match_type": "synonym",
        "confidence": 0.95,
        "status": "validated",
        "action_required": False,
        "warnings": [],
        "semantic_info": None,
    }

    service = AsyncKGService(mock_conn)
    service.semantic_reasoner.validate_with_hierarchy = AsyncMock(return_value=mock_semantic_response)

    result = await service.normalize_field(field_path="subject.species", value="mouse", use_semantic_reasoning=True)

    assert result["status"] == "validated"
    assert result["match_type"] == "synonym"
    assert result["confidence"] == 0.95
    assert result["normalized_value"] == "Mus musculus"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_field_with_semantic_reasoning_semantic_match():
    """Test normalization with semantic reasoning - semantic search (Stage 3)."""
    mock_conn = Mock()

    # Stage 3 semantic match - partial match with hierarchy traversal
    mock_semantic_response = {
        "field_path": "ecephys.ElectrodeGroup.location",
        "raw_value": "Ammon",
        "normalized_value": "Ammon's horn",
        "ontology_term_id": "UBERON:0001954",
        "match_type": "semantic",
        "confidence": 0.85,
        "status": "validated",
        "action_required": False,
        "warnings": [],
        "semantic_info": {
            "ancestors": [
                {"term_id": "UBERON:0002421", "label": "hippocampal formation", "distance": 1},
                {"term_id": "UBERON:0000956", "label": "cerebral cortex", "distance": 2},
            ]
        },
    }

    service = AsyncKGService(mock_conn)
    service.semantic_reasoner.validate_with_hierarchy = AsyncMock(return_value=mock_semantic_response)

    result = await service.normalize_field(
        field_path="ecephys.ElectrodeGroup.location", value="Ammon", use_semantic_reasoning=True
    )

    assert result["status"] == "validated"
    assert result["match_type"] == "semantic"
    assert result["confidence"] == 0.85
    assert result["normalized_value"] == "Ammon's horn"
    assert result["semantic_info"] is not None
    assert len(result["semantic_info"]["ancestors"]) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_field_semantic_reasoning_default_enabled():
    """Test that semantic reasoning is enabled by default."""
    mock_conn = Mock()

    mock_semantic_response = {
        "field_path": "subject.species",
        "raw_value": "rat",
        "normalized_value": "Rattus norvegicus",
        "ontology_term_id": "NCBITaxon:10116",
        "match_type": "synonym",
        "confidence": 0.95,
        "status": "validated",
        "action_required": False,
        "warnings": [],
    }

    service = AsyncKGService(mock_conn)
    service.semantic_reasoner.validate_with_hierarchy = AsyncMock(return_value=mock_semantic_response)

    # Call without use_semantic_reasoning parameter - should default to True
    result = await service.normalize_field(field_path="subject.species", value="rat")

    assert result["status"] == "validated"
    assert result["normalized_value"] == "Rattus norvegicus"

    # Verify semantic reasoner was called (not legacy path)
    service.semantic_reasoner.validate_with_hierarchy.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_field_legacy_path_still_works():
    """Test that legacy 3-stage string matching still works when use_semantic_reasoning=False."""
    mock_conn = Mock()

    # Legacy path mocks (exact match success)
    mock_conn.execute_read = AsyncMock(
        side_effect=[
            # Schema field lookup
            [{"field_path": "subject.species", "ontology_governed": True, "ontology_name": "NCBITaxonomy"}],
            # Exact match
            [{"term_id": "NCBITaxon:10090", "label": "Mus musculus", "ontology_name": "NCBITaxonomy"}],
        ]
    )

    service = AsyncKGService(mock_conn)

    # Explicitly disable semantic reasoning
    result = await service.normalize_field(
        field_path="subject.species", value="Mus musculus", use_semantic_reasoning=False
    )

    assert result["status"] == "validated"
    assert result["match_type"] == "exact"
    assert result["confidence"] == 1.0
    assert result["normalized_value"] == "Mus musculus"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_field_legacy_synonym_match():
    """Test legacy synonym match when semantic reasoning is disabled."""
    mock_conn = Mock()

    mock_conn.execute_read = AsyncMock(
        side_effect=[
            # Schema field lookup
            [{"field_path": "subject.species", "ontology_governed": True, "ontology_name": "NCBITaxonomy"}],
            # Exact match (fails)
            [],
            # Synonym match (succeeds)
            [{"term_id": "NCBITaxon:10090", "label": "Mus musculus", "ontology_name": "NCBITaxonomy"}],
        ]
    )

    service = AsyncKGService(mock_conn)

    result = await service.normalize_field(field_path="subject.species", value="mouse", use_semantic_reasoning=False)

    assert result["status"] == "validated"
    assert result["match_type"] == "synonym"
    assert result["confidence"] == 0.95


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_field_legacy_needs_review():
    """Test legacy needs_review when semantic reasoning is disabled."""
    mock_conn = Mock()

    mock_conn.execute_read = AsyncMock(
        side_effect=[
            # Schema field lookup
            [{"field_path": "subject.species", "ontology_governed": True, "ontology_name": "NCBITaxonomy"}],
            # Exact match (fails)
            [],
            # Synonym match (fails)
            [],
        ]
    )

    service = AsyncKGService(mock_conn)

    result = await service.normalize_field(field_path="subject.species", value="unicorn", use_semantic_reasoning=False)

    assert result["status"] == "needs_review"
    assert result["confidence"] == 0.0
    assert result["match_type"] is None
    assert result["action_required"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_semantic_reasoner_initialized():
    """Test that SemanticReasoner is initialized when AsyncKGService is created."""
    mock_conn = Mock()

    service = AsyncKGService(mock_conn)

    assert hasattr(service, "semantic_reasoner")
    assert service.semantic_reasoner is not None
    assert service.semantic_reasoner.neo4j_conn == mock_conn


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_with_semantic_reasoning_and_context():
    """Test normalization with semantic reasoning and context parameter."""
    mock_conn = Mock()

    mock_semantic_response = {
        "field_path": "subject.species",
        "raw_value": "mouse",
        "normalized_value": "Mus musculus",
        "ontology_term_id": "NCBITaxon:10090",
        "match_type": "synonym",
        "confidence": 0.95,
        "status": "validated",
        "action_required": False,
        "warnings": [],
    }

    service = AsyncKGService(mock_conn)
    service.semantic_reasoner.validate_with_hierarchy = AsyncMock(return_value=mock_semantic_response)

    context = {"source_file": "test.nwb", "session_id": "session123"}
    result = await service.normalize_field(
        field_path="subject.species", value="mouse", context=context, use_semantic_reasoning=True
    )

    assert result["status"] == "validated"
    assert result["confidence"] == 0.95
    # Context is accepted but not currently used by semantic reasoner


@pytest.mark.unit
@pytest.mark.asyncio
async def test_semantic_reasoning_handles_not_applicable():
    """Test that semantic reasoner handles non-ontology-governed fields."""
    mock_conn = Mock()

    mock_semantic_response = {
        "field_path": "subject.subject_id",
        "raw_value": "ABC123",
        "normalized_value": None,
        "ontology_term_id": None,
        "match_type": None,
        "confidence": 0.0,
        "status": "not_applicable",
        "action_required": False,
        "warnings": ["Field subject.subject_id is not ontology-governed"],
    }

    service = AsyncKGService(mock_conn)
    service.semantic_reasoner.validate_with_hierarchy = AsyncMock(return_value=mock_semantic_response)

    result = await service.normalize_field(field_path="subject.subject_id", value="ABC123", use_semantic_reasoning=True)

    assert result["status"] == "not_applicable"
    assert result["confidence"] == 0.0
    assert len(result["warnings"]) > 0
