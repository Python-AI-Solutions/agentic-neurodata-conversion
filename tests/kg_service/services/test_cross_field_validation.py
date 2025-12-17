"""Phase 3 Unit Tests: Cross-Field Semantic Validation.

Tests for SemanticReasoner.check_cross_field_compatibility() method.
"""

from unittest.mock import AsyncMock

import pytest

from agentic_neurodata_conversion.kg_service.services.semantic_reasoner import SemanticReasoner


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cross_field_valid_vertebrate_brain():
    """Test valid combination: vertebrate species + brain structure."""
    mock_conn = AsyncMock()
    reasoner = SemanticReasoner(mock_conn)

    # Mock execute_read to return term info
    mock_conn.execute_read = AsyncMock(
        side_effect=[
            # First call: species term lookup
            [{"term_id": "NCBITaxon:10090", "label": "Mus musculus", "ontology_name": "NCBITaxonomy"}],
            # Second call: anatomy term lookup
            [{"term_id": "UBERON:0001954", "label": "Ammon's horn", "ontology_name": "UBERON"}],
        ]
    )

    # Mock find_ancestors to return vertebrate hierarchy
    reasoner.find_ancestors = AsyncMock(
        side_effect=[
            # First call: species ancestors (Mus musculus)
            [
                {"term_id": "NCBITaxon:10088", "label": "Mus", "distance": 1},
                {"term_id": "NCBITaxon:10066", "label": "Muridae", "distance": 2},
                {"term_id": "NCBITaxon:9989", "label": "Rodentia", "distance": 3},
                {"term_id": "NCBITaxon:40674", "label": "Mammalia", "distance": 4},
                {"term_id": "NCBITaxon:7742", "label": "Vertebrata", "distance": 5},
            ],
            # Second call: anatomy ancestors (hippocampus)
            [
                {"term_id": "UBERON:0002421", "label": "hippocampal formation", "distance": 1},
                {"term_id": "UBERON:0000956", "label": "cerebral cortex", "distance": 2},
                {"term_id": "UBERON:0000955", "label": "brain", "distance": 3},
            ],
        ]
    )

    result = await reasoner.check_cross_field_compatibility(
        species_term_id="NCBITaxon:10090", anatomy_term_id="UBERON:0001954"
    )

    assert result["is_compatible"] is True
    assert result["confidence"] == 0.95
    assert "vertebrate" in result["reasoning"].lower()
    assert "Vertebrata" in result["species_ancestors"]
    assert "brain" in result["anatomy_ancestors"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cross_field_invalid_invertebrate_brain():
    """Test invalid combination: invertebrate species + vertebrate brain structure."""
    mock_conn = AsyncMock()
    reasoner = SemanticReasoner(mock_conn)

    # Mock execute_read to return term info
    mock_conn.execute_read = AsyncMock(
        side_effect=[
            # First call: species term lookup
            [{"term_id": "NCBITaxon:6239", "label": "Caenorhabditis elegans", "ontology_name": "NCBITaxonomy"}],
            # Second call: anatomy term lookup
            [{"term_id": "UBERON:0001954", "label": "Ammon's horn", "ontology_name": "UBERON"}],
        ]
    )

    # Mock find_ancestors to return invertebrate hierarchy
    reasoner.find_ancestors = AsyncMock(
        side_effect=[
            # First call: species ancestors (C. elegans - worm)
            [
                {"term_id": "NCBITaxon:6237", "label": "Caenorhabditis", "distance": 1},
                {"term_id": "NCBITaxon:6231", "label": "Nematoda", "distance": 2},
                {"term_id": "NCBITaxon:33317", "label": "Protostomia", "distance": 3},
            ],
            # Second call: anatomy ancestors (hippocampus)
            [
                {"term_id": "UBERON:0002421", "label": "hippocampal formation", "distance": 1},
                {"term_id": "UBERON:0000956", "label": "cerebral cortex", "distance": 2},
                {"term_id": "UBERON:0000955", "label": "brain", "distance": 3},
            ],
        ]
    )

    result = await reasoner.check_cross_field_compatibility(
        species_term_id="NCBITaxon:6239", anatomy_term_id="UBERON:0001954"
    )

    assert result["is_compatible"] is False
    assert result["confidence"] == 0.95
    assert "invertebrate" in result["reasoning"].lower()
    assert "Protostomia" in result["species_ancestors"] or "Nematoda" in result["species_ancestors"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cross_field_valid_human_brain():
    """Test valid combination: human + brain structure."""
    mock_conn = AsyncMock()
    reasoner = SemanticReasoner(mock_conn)

    # Mock execute_read to return term info
    mock_conn.execute_read = AsyncMock(
        side_effect=[
            # First call: species term lookup
            [{"term_id": "NCBITaxon:9606", "label": "Homo sapiens", "ontology_name": "NCBITaxonomy"}],
            # Second call: anatomy term lookup
            [{"term_id": "UBERON:0001950", "label": "neocortex", "ontology_name": "UBERON"}],
        ]
    )

    # Mock find_ancestors to return human (primate) hierarchy
    reasoner.find_ancestors = AsyncMock(
        side_effect=[
            # First call: species ancestors (Homo sapiens)
            [
                {"term_id": "NCBITaxon:9605", "label": "Homo", "distance": 1},
                {"term_id": "NCBITaxon:9604", "label": "Hominidae", "distance": 2},
                {"term_id": "NCBITaxon:9443", "label": "Primates", "distance": 3},
                {"term_id": "NCBITaxon:40674", "label": "Mammalia", "distance": 4},
                {"term_id": "NCBITaxon:7742", "label": "Vertebrata", "distance": 5},
            ],
            # Second call: anatomy ancestors (neocortex)
            [
                {"term_id": "UBERON:0000956", "label": "cerebral cortex", "distance": 1},
                {"term_id": "UBERON:0000955", "label": "brain", "distance": 2},
            ],
        ]
    )

    result = await reasoner.check_cross_field_compatibility(
        species_term_id="NCBITaxon:9606", anatomy_term_id="UBERON:0001950"
    )

    assert result["is_compatible"] is True
    assert result["confidence"] == 0.95
    assert "vertebrate" in result["reasoning"].lower()
    assert "Vertebrata" in result["species_ancestors"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cross_field_invalid_fly_brain():
    """Test invalid combination: Drosophila (fly) + vertebrate brain."""
    mock_conn = AsyncMock()
    reasoner = SemanticReasoner(mock_conn)

    # Mock execute_read to return term info
    mock_conn.execute_read = AsyncMock(
        side_effect=[
            # First call: species term lookup
            [{"term_id": "NCBITaxon:7227", "label": "Drosophila melanogaster", "ontology_name": "NCBITaxonomy"}],
            # Second call: anatomy term lookup
            [{"term_id": "UBERON:0000955", "label": "brain", "ontology_name": "UBERON"}],
        ]
    )

    # Mock find_ancestors to return Drosophila (arthropod) hierarchy
    reasoner.find_ancestors = AsyncMock(
        side_effect=[
            # First call: species ancestors (Drosophila melanogaster)
            [
                {"term_id": "NCBITaxon:7215", "label": "Drosophila", "distance": 1},
                {"term_id": "NCBITaxon:7214", "label": "Drosophilidae", "distance": 2},
                {"term_id": "NCBITaxon:7203", "label": "Diptera", "distance": 3},
                {"term_id": "NCBITaxon:50557", "label": "Insecta", "distance": 4},
                {"term_id": "NCBITaxon:6656", "label": "Arthropoda", "distance": 5},
                {"term_id": "NCBITaxon:33317", "label": "Protostomia", "distance": 6},
            ],
            # Second call: anatomy ancestors (brain)
            [
                {"term_id": "UBERON:0000955", "label": "brain", "distance": 1},
            ],
        ]
    )

    result = await reasoner.check_cross_field_compatibility(
        species_term_id="NCBITaxon:7227", anatomy_term_id="UBERON:0000955"
    )

    assert result["is_compatible"] is False
    assert result["confidence"] == 0.95
    assert "invertebrate" in result["reasoning"].lower()
    assert "Protostomia" in result["species_ancestors"] or "Arthropoda" in result["species_ancestors"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cross_field_unknown_species_term():
    """Test with unknown/invalid species term ID."""
    mock_conn = AsyncMock()
    reasoner = SemanticReasoner(mock_conn)

    # Mock execute_read to return term info
    mock_conn.execute_read = AsyncMock(
        side_effect=[
            # First call: species term lookup (not found)
            [],
            # Second call: anatomy term lookup (valid)
            [{"term_id": "UBERON:0000955", "label": "brain", "ontology_name": "UBERON"}],
        ]
    )

    # Mock find_ancestors to return empty (term not found)
    reasoner.find_ancestors = AsyncMock(
        side_effect=[
            # First call: species ancestors (not found)
            [],
            # Second call: anatomy ancestors (valid)
            [
                {"term_id": "UBERON:0000955", "label": "brain", "distance": 1},
            ],
        ]
    )

    result = await reasoner.check_cross_field_compatibility(
        species_term_id="NCBITaxon:99999", anatomy_term_id="UBERON:0000955"
    )

    assert result["is_compatible"] is False
    assert result["confidence"] == 0.0
    assert "not found" in result["reasoning"].lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cross_field_unknown_anatomy_term():
    """Test with unknown/invalid anatomy term ID."""
    mock_conn = AsyncMock()
    reasoner = SemanticReasoner(mock_conn)

    # Mock execute_read to return term info
    mock_conn.execute_read = AsyncMock(
        side_effect=[
            # First call: species term lookup (valid)
            [{"term_id": "NCBITaxon:10090", "label": "Mus musculus", "ontology_name": "NCBITaxonomy"}],
            # Second call: anatomy term lookup (not found)
            [],
        ]
    )

    # Mock find_ancestors to return empty for anatomy
    reasoner.find_ancestors = AsyncMock(
        side_effect=[
            # First call: species ancestors (valid)
            [
                {"term_id": "NCBITaxon:10088", "label": "Mus", "distance": 1},
                {"term_id": "NCBITaxon:7742", "label": "Vertebrata", "distance": 2},
            ],
            # Second call: anatomy ancestors (not found)
            [],
        ]
    )

    result = await reasoner.check_cross_field_compatibility(
        species_term_id="NCBITaxon:10090", anatomy_term_id="UBERON:99999"
    )

    assert result["is_compatible"] is False
    assert result["confidence"] == 0.0
    assert "not found" in result["reasoning"].lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cross_field_both_terms_unknown():
    """Test with both terms unknown."""
    mock_conn = AsyncMock()
    reasoner = SemanticReasoner(mock_conn)

    # Mock execute_read to return term info
    mock_conn.execute_read = AsyncMock(
        side_effect=[
            # First call: species term lookup (not found)
            [],
            # Second call: anatomy term lookup (not found)
            [],
        ]
    )

    # Mock find_ancestors to return empty for both
    reasoner.find_ancestors = AsyncMock(return_value=[])

    result = await reasoner.check_cross_field_compatibility(
        species_term_id="NCBITaxon:99999", anatomy_term_id="UBERON:99999"
    )

    assert result["is_compatible"] is False
    assert result["confidence"] == 0.0
    assert "not found" in result["reasoning"].lower()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cross_field_valid_rat_brain():
    """Test valid combination: rat + brain structure."""
    mock_conn = AsyncMock()
    reasoner = SemanticReasoner(mock_conn)

    # Mock execute_read to return term info
    mock_conn.execute_read = AsyncMock(
        side_effect=[
            # First call: species term lookup
            [{"term_id": "NCBITaxon:10116", "label": "Rattus norvegicus", "ontology_name": "NCBITaxonomy"}],
            # Second call: anatomy term lookup
            [{"term_id": "UBERON:0001869", "label": "thalamus", "ontology_name": "UBERON"}],
        ]
    )

    # Mock find_ancestors for rat
    reasoner.find_ancestors = AsyncMock(
        side_effect=[
            # First call: species ancestors (Rattus norvegicus)
            [
                {"term_id": "NCBITaxon:10114", "label": "Rattus", "distance": 1},
                {"term_id": "NCBITaxon:10066", "label": "Muridae", "distance": 2},
                {"term_id": "NCBITaxon:9989", "label": "Rodentia", "distance": 3},
                {"term_id": "NCBITaxon:40674", "label": "Mammalia", "distance": 4},
                {"term_id": "NCBITaxon:7742", "label": "Vertebrata", "distance": 5},
            ],
            # Second call: anatomy ancestors (thalamus)
            [
                {"term_id": "UBERON:0001894", "label": "diencephalon", "distance": 1},
                {"term_id": "UBERON:0000955", "label": "brain", "distance": 2},
            ],
        ]
    )

    result = await reasoner.check_cross_field_compatibility(
        species_term_id="NCBITaxon:10116", anatomy_term_id="UBERON:0001869"
    )

    assert result["is_compatible"] is True
    assert result["confidence"] == 0.95
    assert "vertebrate" in result["reasoning"].lower()
    assert "Vertebrata" in result["species_ancestors"]
    assert "brain" in result["anatomy_ancestors"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cross_field_response_structure():
    """Test that response has all required fields."""
    mock_conn = AsyncMock()
    reasoner = SemanticReasoner(mock_conn)

    # Mock execute_read to return term info
    mock_conn.execute_read = AsyncMock(
        side_effect=[
            # First call: species term lookup
            [{"term_id": "NCBITaxon:10090", "label": "Mus musculus", "ontology_name": "NCBITaxonomy"}],
            # Second call: anatomy term lookup
            [{"term_id": "UBERON:0001954", "label": "Ammon's horn", "ontology_name": "UBERON"}],
        ]
    )

    # Mock find_ancestors with minimal data
    reasoner.find_ancestors = AsyncMock(
        side_effect=[
            [{"term_id": "NCBITaxon:7742", "label": "Vertebrata", "distance": 1}],
            [{"term_id": "UBERON:0000955", "label": "brain", "distance": 1}],
        ]
    )

    result = await reasoner.check_cross_field_compatibility(
        species_term_id="NCBITaxon:10090", anatomy_term_id="UBERON:0001954"
    )

    # Verify all required fields are present
    assert "is_compatible" in result
    assert "confidence" in result
    assert "reasoning" in result
    assert "species_ancestors" in result
    assert "anatomy_ancestors" in result

    # Verify types
    assert isinstance(result["is_compatible"], bool)
    assert isinstance(result["confidence"], float)
    assert isinstance(result["reasoning"], str)
    assert isinstance(result["species_ancestors"], list)
    assert isinstance(result["anatomy_ancestors"], list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cross_field_ancestor_lists_populated():
    """Test that ancestor lists are populated correctly."""
    mock_conn = AsyncMock()
    reasoner = SemanticReasoner(mock_conn)

    # Mock execute_read to return term info
    mock_conn.execute_read = AsyncMock(
        side_effect=[
            # First call: species term lookup
            [{"term_id": "NCBITaxon:10090", "label": "Mus musculus", "ontology_name": "NCBITaxonomy"}],
            # Second call: anatomy term lookup
            [{"term_id": "UBERON:0001954", "label": "Ammon's horn", "ontology_name": "UBERON"}],
        ]
    )

    # Mock find_ancestors with specific ancestors
    reasoner.find_ancestors = AsyncMock(
        side_effect=[
            [
                {"term_id": "NCBITaxon:40674", "label": "Mammalia", "distance": 1},
                {"term_id": "NCBITaxon:7742", "label": "Vertebrata", "distance": 2},
            ],
            [
                {"term_id": "UBERON:0000956", "label": "cerebral cortex", "distance": 1},
                {"term_id": "UBERON:0000955", "label": "brain", "distance": 2},
            ],
        ]
    )

    result = await reasoner.check_cross_field_compatibility(
        species_term_id="NCBITaxon:10090", anatomy_term_id="UBERON:0001954"
    )

    # Verify ancestor lists are populated
    assert len(result["species_ancestors"]) > 0
    assert len(result["anatomy_ancestors"]) > 0

    # Verify key ancestors are present
    assert any("Vertebrata" in ancestor or "Mammalia" in ancestor for ancestor in result["species_ancestors"])
    assert any("brain" in ancestor for ancestor in result["anatomy_ancestors"])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cross_field_confidence_scores():
    """Test that confidence scores are set correctly."""
    mock_conn = AsyncMock()
    reasoner = SemanticReasoner(mock_conn)

    # Test valid combination (high confidence)
    # Mock execute_read for first test
    mock_conn.execute_read = AsyncMock(
        side_effect=[
            # First call: species term lookup
            [{"term_id": "NCBITaxon:10090", "label": "Mus musculus", "ontology_name": "NCBITaxonomy"}],
            # Second call: anatomy term lookup
            [{"term_id": "UBERON:0001954", "label": "Ammon's horn", "ontology_name": "UBERON"}],
        ]
    )

    reasoner.find_ancestors = AsyncMock(
        side_effect=[
            [{"term_id": "NCBITaxon:7742", "label": "Vertebrata", "distance": 1}],
            [{"term_id": "UBERON:0000955", "label": "brain", "distance": 1}],
        ]
    )

    result_valid = await reasoner.check_cross_field_compatibility(
        species_term_id="NCBITaxon:10090", anatomy_term_id="UBERON:0001954"
    )

    assert result_valid["confidence"] == 0.95  # High confidence for valid match

    # Test invalid combination (high confidence)
    # Mock execute_read for second test
    mock_conn.execute_read = AsyncMock(
        side_effect=[
            # First call: species term lookup
            [{"term_id": "NCBITaxon:6239", "label": "Caenorhabditis elegans", "ontology_name": "NCBITaxonomy"}],
            # Second call: anatomy term lookup
            [{"term_id": "UBERON:0001954", "label": "Ammon's horn", "ontology_name": "UBERON"}],
        ]
    )

    reasoner.find_ancestors = AsyncMock(
        side_effect=[
            [{"term_id": "NCBITaxon:33317", "label": "Protostomia", "distance": 1}],
            [{"term_id": "UBERON:0000955", "label": "brain", "distance": 1}],
        ]
    )

    result_invalid = await reasoner.check_cross_field_compatibility(
        species_term_id="NCBITaxon:6239", anatomy_term_id="UBERON:0001954"
    )

    assert result_invalid["confidence"] == 0.95  # High confidence for invalid match (certain it's wrong)

    # Test unknown term (low confidence)
    # Mock execute_read for third test
    mock_conn.execute_read = AsyncMock(
        side_effect=[
            # First call: species term lookup (not found)
            [],
            # Second call: anatomy term lookup
            [{"term_id": "UBERON:0001954", "label": "Ammon's horn", "ontology_name": "UBERON"}],
        ]
    )

    reasoner.find_ancestors = AsyncMock(return_value=[])

    result_unknown = await reasoner.check_cross_field_compatibility(
        species_term_id="NCBITaxon:99999", anatomy_term_id="UBERON:0001954"
    )

    assert result_unknown["confidence"] == 0.0  # Low confidence for unknown term
