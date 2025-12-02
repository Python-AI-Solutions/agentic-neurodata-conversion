"""Unit Tests for KG Service.

Tests for kg_service/services/kg_service.py normalization logic.
"""

from unittest.mock import AsyncMock, Mock

import pytest

from agentic_neurodata_conversion.kg_service.services.kg_service import AsyncKGService


@pytest.mark.unit
def test_preprocess_value():
    """Test value preprocessing (lowercase, strip, unicode normalize)."""
    service = AsyncKGService(Mock())

    # Test basic normalization
    assert service._preprocess("  Mus musculus  ") == "mus musculus"
    assert service._preprocess("MOUSE") == "mouse"
    assert service._preprocess("MoUsE") == "mouse"

    # Test unicode normalization (NFC)
    assert service._preprocess("café") == "café"

    # Test empty string
    assert service._preprocess("") == ""
    assert service._preprocess("   ") == ""


@pytest.mark.unit
def test_preprocess_edge_cases():
    """Test edge cases in value preprocessing."""
    service = AsyncKGService(Mock())

    # Multiple spaces
    assert service._preprocess("  multiple   spaces  ") == "multiple   spaces"

    # Special characters
    assert service._preprocess("C57BL/6J") == "c57bl/6j"

    # Numbers
    assert service._preprocess("  123  ") == "123"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_schema_field_found():
    """Test getting schema field information when field exists."""
    mock_conn = Mock()
    mock_conn.execute_read = AsyncMock(
        return_value=[{"field_path": "subject.species", "ontology_governed": True, "ontology_name": "NCBITaxonomy"}]
    )

    service = AsyncKGService(mock_conn)
    result = await service._get_schema_field("subject.species")

    assert result is not None
    assert result["field_path"] == "subject.species"
    assert result["ontology_governed"] is True
    assert result["ontology_name"] == "NCBITaxonomy"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_schema_field_not_found():
    """Test getting schema field information when field doesn't exist."""
    mock_conn = Mock()
    mock_conn.execute_read = AsyncMock(return_value=[])

    service = AsyncKGService(mock_conn)
    result = await service._get_schema_field("nonexistent.field")

    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_exact_match_success():
    """Test exact label matching - success case."""
    mock_conn = Mock()

    # Single query that joins SchemaField and OntologyTerm
    mock_conn.execute_read = AsyncMock(
        return_value=[{"term_id": "NCBITaxon:10090", "label": "Mus musculus", "ontology_name": "NCBITaxonomy"}]
    )

    service = AsyncKGService(mock_conn)
    result = await service._exact_match("subject.species", "Mus musculus")

    assert result is not None
    assert result["term_id"] == "NCBITaxon:10090"
    assert result["label"] == "Mus musculus"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_exact_match_no_match():
    """Test exact label matching - no match."""
    mock_conn = Mock()
    mock_conn.execute_read = AsyncMock(return_value=[])

    service = AsyncKGService(mock_conn)
    result = await service._exact_match("subject.species", "unicorn")

    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_synonym_match_success():
    """Test synonym matching - success case."""
    mock_conn = Mock()
    mock_conn.execute_read = AsyncMock(
        return_value=[{"term_id": "NCBITaxon:10090", "label": "Mus musculus", "ontology_name": "NCBITaxonomy"}]
    )

    service = AsyncKGService(mock_conn)
    result = await service._synonym_match("subject.species", "mouse")

    assert result is not None
    assert result["term_id"] == "NCBITaxon:10090"
    assert result["label"] == "Mus musculus"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_synonym_match_no_match():
    """Test synonym matching - no match."""
    mock_conn = Mock()
    mock_conn.execute_read = AsyncMock(return_value=[])

    service = AsyncKGService(mock_conn)
    result = await service._synonym_match("subject.species", "unicorn")

    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_field_exact_match():
    """Test full normalization pipeline - exact match path."""
    mock_conn = Mock()
    mock_conn.execute_read = AsyncMock(
        side_effect=[
            # Schema field lookup
            [{"field_path": "subject.species", "ontology_governed": True, "ontology_name": "NCBITaxonomy"}],
            # Exact match
            [{"term_id": "NCBITaxon:10090", "label": "Mus musculus", "ontology_name": "NCBITaxonomy"}],
        ]
    )

    service = AsyncKGService(mock_conn)
    result = await service.normalize_field(field_path="subject.species", value="Mus musculus")

    assert result["status"] == "validated"
    assert result["match_type"] == "exact"
    assert result["confidence"] == 1.0
    assert result["normalized_value"] == "Mus musculus"
    assert result["ontology_term_id"] == "NCBITaxon:10090"
    assert result["action_required"] is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_field_synonym_match():
    """Test full normalization pipeline - synonym match path."""
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
    result = await service.normalize_field(field_path="subject.species", value="mouse")

    assert result["status"] == "validated"
    assert result["match_type"] == "synonym"
    assert result["confidence"] == 0.95
    assert result["normalized_value"] == "Mus musculus"
    assert result["ontology_term_id"] == "NCBITaxon:10090"
    assert result["action_required"] is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_field_needs_review():
    """Test normalization when no match found."""
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
    result = await service.normalize_field(field_path="subject.species", value="unicorn")

    assert result["status"] == "needs_review"
    assert result["confidence"] == 0.0
    assert result["match_type"] is None
    assert result["normalized_value"] is None
    assert result["ontology_term_id"] is None
    assert result["action_required"] is True
    assert len(result["warnings"]) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_field_not_ontology_governed():
    """Test normalization for non-ontology-governed field."""
    mock_conn = Mock()
    mock_conn.execute_read = AsyncMock(
        return_value=[{"field_path": "subject.subject_id", "ontology_governed": False, "ontology_name": None}]
    )

    service = AsyncKGService(mock_conn)
    result = await service.normalize_field(field_path="subject.subject_id", value="ABC123")

    assert result["status"] == "not_applicable"
    assert result["confidence"] == 0.0
    assert result["match_type"] is None
    assert result["action_required"] is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_field_unknown_field():
    """Test normalization for unknown field."""
    mock_conn = Mock()
    mock_conn.execute_read = AsyncMock(return_value=[])

    service = AsyncKGService(mock_conn)
    result = await service.normalize_field(field_path="unknown.field", value="test")

    assert result["status"] == "not_applicable"
    assert result["confidence"] == 0.0
    assert "not ontology-governed" in result["warnings"][0]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_field_valid():
    """Test validation endpoint - valid value."""
    mock_conn = Mock()
    mock_conn.execute_read = AsyncMock(
        side_effect=[
            [{"field_path": "subject.species", "ontology_governed": True, "ontology_name": "NCBITaxonomy"}],
            [{"term_id": "NCBITaxon:10090", "label": "Mus musculus", "ontology_name": "NCBITaxonomy"}],
        ]
    )

    service = AsyncKGService(mock_conn)
    result = await service.validate_field(field_path="subject.species", value="Mus musculus")

    assert result["is_valid"] is True
    assert result["confidence"] == 1.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_validate_field_invalid():
    """Test validation endpoint - invalid value."""
    mock_conn = Mock()
    mock_conn.execute_read = AsyncMock(
        side_effect=[
            [{"field_path": "subject.species", "ontology_governed": True, "ontology_name": "NCBITaxonomy"}],
            [],
            [],
        ]
    )

    service = AsyncKGService(mock_conn)
    result = await service.validate_field(field_path="subject.species", value="unicorn")

    assert result["is_valid"] is False
    assert result["confidence"] == 0.0
    assert len(result["warnings"]) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_normalize_with_context():
    """Test normalization with context parameter."""
    mock_conn = Mock()
    mock_conn.execute_read = AsyncMock(
        side_effect=[
            [{"field_path": "subject.species", "ontology_governed": True, "ontology_name": "NCBITaxonomy"}],
            [{"term_id": "NCBITaxon:10090", "label": "Mus musculus", "ontology_name": "NCBITaxonomy"}],
        ]
    )

    service = AsyncKGService(mock_conn)
    context = {"source_file": "test.nwb", "user_id": "test_user"}
    result = await service.normalize_field(field_path="subject.species", value="Mus musculus", context=context)

    assert result["status"] == "validated"
    assert result["confidence"] == 1.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_case_insensitive_matching():
    """Test that matching is case-insensitive."""
    mock_conn = Mock()
    mock_conn.execute_read = AsyncMock(
        side_effect=[
            [{"field_path": "subject.species", "ontology_governed": True, "ontology_name": "NCBITaxonomy"}],
            [{"term_id": "NCBITaxon:10090", "label": "Mus musculus", "ontology_name": "NCBITaxonomy"}],
        ]
    )

    service = AsyncKGService(mock_conn)
    result = await service.normalize_field(field_path="subject.species", value="MUS MUSCULUS")

    assert result["status"] == "validated"
    assert result["match_type"] == "exact"
    assert result["normalized_value"] == "Mus musculus"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_whitespace_handling():
    """Test that extra whitespace is handled correctly."""
    mock_conn = Mock()
    mock_conn.execute_read = AsyncMock(
        side_effect=[
            [{"field_path": "subject.species", "ontology_governed": True, "ontology_name": "NCBITaxonomy"}],
            [{"term_id": "NCBITaxon:10090", "label": "Mus musculus", "ontology_name": "NCBITaxonomy"}],
        ]
    )

    service = AsyncKGService(mock_conn)
    result = await service.normalize_field(field_path="subject.species", value="  Mus musculus  ")

    assert result["status"] == "validated"
    assert result["normalized_value"] == "Mus musculus"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_brain_region_normalization():
    """Test UBERON brain region normalization."""
    mock_conn = Mock()
    mock_conn.execute_read = AsyncMock(
        side_effect=[
            [{"field_path": "ecephys.ElectrodeGroup.location", "ontology_governed": True, "ontology_name": "UBERON"}],
            [{"term_id": "UBERON:0002421", "label": "hippocampus", "ontology_name": "UBERON"}],
        ]
    )

    service = AsyncKGService(mock_conn)
    result = await service.normalize_field(field_path="ecephys.ElectrodeGroup.location", value="hippocampus")

    assert result["status"] == "validated"
    assert result["ontology_term_id"] == "UBERON:0002421"
    assert "UBERON:" in result["ontology_term_id"]
