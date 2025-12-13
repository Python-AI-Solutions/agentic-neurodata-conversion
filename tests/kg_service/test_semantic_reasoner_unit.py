"""Unit tests for SemanticReasoner class.

Tests core functionality with mocked Neo4j connection.
"""

from unittest.mock import AsyncMock

import pytest

from agentic_neurodata_conversion.kg_service.services.semantic_reasoner import SemanticReasoner


@pytest.fixture
def mock_neo4j_conn():
    """Create mock Neo4j connection."""
    mock_conn = AsyncMock()
    return mock_conn


@pytest.fixture
def semantic_reasoner(mock_neo4j_conn):
    """Create SemanticReasoner instance with mock connection."""
    return SemanticReasoner(mock_neo4j_conn)


class TestFindAncestors:
    """Test find_ancestors() method."""

    @pytest.mark.asyncio
    async def test_find_ancestors_success(self, semantic_reasoner, mock_neo4j_conn):
        """Test successful ancestor retrieval."""
        # Mock Neo4j response
        mock_neo4j_conn.execute_read.return_value = [
            {"term_id": "UBERON:0002421", "label": "hippocampal formation", "distance": 1},
            {"term_id": "UBERON:0000956", "label": "cerebral cortex", "distance": 2},
            {"term_id": "UBERON:0000955", "label": "brain", "distance": 3},
        ]

        result = await semantic_reasoner.find_ancestors("UBERON:0001954")

        assert len(result) == 3
        assert result[0]["label"] == "hippocampal formation"
        assert result[0]["distance"] == 1
        assert result[2]["label"] == "brain"
        assert result[2]["distance"] == 3
        mock_neo4j_conn.execute_read.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_ancestors_no_results(self, semantic_reasoner, mock_neo4j_conn):
        """Test with no ancestors found."""
        mock_neo4j_conn.execute_read.return_value = []

        result = await semantic_reasoner.find_ancestors("NCBITaxon:10090")

        assert result == []
        mock_neo4j_conn.execute_read.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_ancestors_max_depth(self, semantic_reasoner, mock_neo4j_conn):
        """Test max_depth parameter."""
        mock_neo4j_conn.execute_read.return_value = [
            {"term_id": "UBERON:0000956", "label": "cerebral cortex", "distance": 1},
        ]

        result = await semantic_reasoner.find_ancestors("UBERON:0001954", max_depth=2)

        assert len(result) == 1
        # Verify query contains correct max_depth
        call_args = mock_neo4j_conn.execute_read.call_args
        assert "*1..2" in call_args[0][0]  # Query should have *1..2


class TestHelperMethods:
    """Test helper methods."""

    @pytest.mark.asyncio
    async def test_get_schema_field_success(self, semantic_reasoner, mock_neo4j_conn):
        """Test _get_schema_field with valid field."""
        mock_neo4j_conn.execute_read.return_value = [
            {
                "field_path": "ecephys.ElectrodeGroup.location",
                "ontology_governed": True,
                "ontology_name": "UBERON",
            }
        ]

        result = await semantic_reasoner._get_schema_field("ecephys.ElectrodeGroup.location")

        assert result is not None
        assert result["ontology_governed"] is True
        assert result["ontology_name"] == "UBERON"

    @pytest.mark.asyncio
    async def test_get_schema_field_not_found(self, semantic_reasoner, mock_neo4j_conn):
        """Test _get_schema_field with invalid field."""
        mock_neo4j_conn.execute_read.return_value = []

        result = await semantic_reasoner._get_schema_field("invalid.field")

        assert result is None

    @pytest.mark.asyncio
    async def test_exact_match_found(self, semantic_reasoner, mock_neo4j_conn):
        """Test _exact_match with matching term."""
        mock_neo4j_conn.execute_read.return_value = [
            {
                "term_id": "UBERON:0002421",
                "label": "hippocampal formation",
                "ontology_name": "UBERON",
            }
        ]

        result = await semantic_reasoner._exact_match(
            "ecephys.ElectrodeGroup.location", "hippocampal formation", "UBERON"
        )

        assert result is not None
        assert result["term_id"] == "UBERON:0002421"
        assert result["label"] == "hippocampal formation"

    @pytest.mark.asyncio
    async def test_synonym_match_found(self, semantic_reasoner, mock_neo4j_conn):
        """Test _synonym_match with matching synonym."""
        mock_neo4j_conn.execute_read.return_value = [
            {
                "term_id": "UBERON:0001954",
                "label": "Ammon's horn",
                "ontology_name": "UBERON",
            }
        ]

        result = await semantic_reasoner._synonym_match("ecephys.ElectrodeGroup.location", "CA1", "UBERON")

        assert result is not None
        assert result["term_id"] == "UBERON:0001954"

    @pytest.mark.asyncio
    async def test_verify_hierarchy_constraint_valid(self, semantic_reasoner, mock_neo4j_conn):
        """Test _verify_hierarchy_constraint with valid ancestor."""
        # Mock find_ancestors
        mock_neo4j_conn.execute_read.return_value = [
            {"term_id": "UBERON:0002421", "label": "hippocampal formation", "distance": 1},
            {"term_id": "UBERON:0000956", "label": "cerebral cortex", "distance": 2},
            {"term_id": "UBERON:0000955", "label": "brain", "distance": 3},
        ]

        result = await semantic_reasoner._verify_hierarchy_constraint("UBERON:0001954", "brain")

        assert result is True

    @pytest.mark.asyncio
    async def test_verify_hierarchy_constraint_invalid(self, semantic_reasoner, mock_neo4j_conn):
        """Test _verify_hierarchy_constraint with invalid ancestor."""
        mock_neo4j_conn.execute_read.return_value = [
            {"term_id": "UBERON:0002421", "label": "hippocampal formation", "distance": 1},
        ]

        result = await semantic_reasoner._verify_hierarchy_constraint("UBERON:0001954", "cerebellum")

        assert result is False

    def test_build_validation_response(self, semantic_reasoner):
        """Test _build_validation_response structure."""
        result = semantic_reasoner._build_validation_response(
            field_path="ecephys.ElectrodeGroup.location",
            raw_value="hippocampus",
            normalized_value="hippocampal formation",
            ontology_term_id="UBERON:0002421",
            match_type="exact",
            confidence=1.0,
            status="validated",
            action_required=False,
        )

        assert result["field_path"] == "ecephys.ElectrodeGroup.location"
        assert result["raw_value"] == "hippocampus"
        assert result["normalized_value"] == "hippocampal formation"
        assert result["ontology_term_id"] == "UBERON:0002421"
        assert result["match_type"] == "exact"
        assert result["confidence"] == 1.0
        assert result["status"] == "validated"
        assert result["action_required"] is False
        assert result["warnings"] == []


class TestCheckCrossFieldCompatibility:
    """Test check_cross_field_compatibility() method."""

    @pytest.mark.asyncio
    async def test_vertebrate_brain_valid(self, semantic_reasoner, mock_neo4j_conn):
        """Test valid vertebrate + brain structure combination."""
        # Mock term lookups (execution order: species term, anatomy term, species ancestors, anatomy ancestors)
        mock_neo4j_conn.execute_read.side_effect = [
            [{"term_id": "NCBITaxon:10090", "label": "Mus musculus", "ontology_name": "NCBITaxonomy"}],
            [{"term_id": "UBERON:0002421", "label": "hippocampal formation", "ontology_name": "UBERON"}],
            # Mock find_ancestors call for SPECIES first (line 319 in semantic_reasoner.py)
            [
                {"term_id": "NCBITaxon:10088", "label": "Mus", "distance": 1},
                {"term_id": "NCBITaxon:10066", "label": "Muridae", "distance": 2},
                {"term_id": "NCBITaxon:9989", "label": "Rodentia", "distance": 3},
                {"term_id": "NCBITaxon:40674", "label": "Mammalia", "distance": 4},
                {"term_id": "NCBITaxon:7742", "label": "Vertebrata", "distance": 5},
            ],
            # Mock find_ancestors call for ANATOMY second (line 331 in semantic_reasoner.py)
            [
                {"term_id": "UBERON:0000956", "label": "cerebral cortex", "distance": 1},
                {"term_id": "UBERON:0000955", "label": "brain", "distance": 2},
            ],
        ]

        result = await semantic_reasoner.check_cross_field_compatibility("NCBITaxon:10090", "UBERON:0002421")

        assert result["is_compatible"] is True
        assert result["confidence"] == 0.95  # Updated from 0.85 (Phase 1.5 hierarchy-based)
        assert "vertebrate" in result["reasoning"].lower()
        assert "can have" in result["reasoning"].lower()

    @pytest.mark.asyncio
    async def test_invertebrate_brain_invalid(self, semantic_reasoner, mock_neo4j_conn):
        """Test invalid invertebrate + brain structure combination."""
        # Mock term lookups (execution order: species term, anatomy term, species ancestors, anatomy ancestors)
        mock_neo4j_conn.execute_read.side_effect = [
            [{"term_id": "NCBITaxon:6239", "label": "Caenorhabditis elegans", "ontology_name": "NCBITaxonomy"}],
            [{"term_id": "UBERON:0002421", "label": "hippocampal formation", "ontology_name": "UBERON"}],
            # Mock find_ancestors call for SPECIES first (line 319 in semantic_reasoner.py)
            [
                {"term_id": "NCBITaxon:6237", "label": "Caenorhabditis", "distance": 1},
                {"term_id": "NCBITaxon:6231", "label": "Nematoda", "distance": 2},
                {"term_id": "NCBITaxon:33317", "label": "Protostomia", "distance": 3},
            ],
            # Mock find_ancestors call for ANATOMY second (line 331 in semantic_reasoner.py)
            [
                {"term_id": "UBERON:0000956", "label": "cerebral cortex", "distance": 1},
                {"term_id": "UBERON:0000955", "label": "brain", "distance": 2},
            ],
        ]

        result = await semantic_reasoner.check_cross_field_compatibility("NCBITaxon:6239", "UBERON:0002421")

        assert result["is_compatible"] is False
        assert result["confidence"] == 0.95  # Updated from 0.90 (Phase 1.5 hierarchy-based)
        assert "invertebrate" in result["reasoning"].lower()

    @pytest.mark.asyncio
    async def test_invalid_species_term(self, semantic_reasoner, mock_neo4j_conn):
        """Test with invalid species term ID."""
        mock_neo4j_conn.execute_read.return_value = []

        result = await semantic_reasoner.check_cross_field_compatibility("NCBITaxon:99999", "UBERON:0002421")

        assert result["is_compatible"] is False
        assert result["confidence"] == 0.0
        assert "not found" in result["reasoning"].lower()


class TestGlobalInstance:
    """Test global instance management."""

    def test_get_semantic_reasoner(self, mock_neo4j_conn):
        """Test get_semantic_reasoner returns singleton."""
        from agentic_neurodata_conversion.kg_service.services.semantic_reasoner import (
            get_semantic_reasoner,
            reset_semantic_reasoner,
        )

        # Reset to ensure clean state
        reset_semantic_reasoner()

        reasoner1 = get_semantic_reasoner(mock_neo4j_conn)
        reasoner2 = get_semantic_reasoner(mock_neo4j_conn)

        assert reasoner1 is reasoner2  # Same instance

    def test_reset_semantic_reasoner(self, mock_neo4j_conn):
        """Test reset_semantic_reasoner creates new instance."""
        from agentic_neurodata_conversion.kg_service.services.semantic_reasoner import (
            get_semantic_reasoner,
            reset_semantic_reasoner,
        )

        reasoner1 = get_semantic_reasoner(mock_neo4j_conn)
        reset_semantic_reasoner()
        reasoner2 = get_semantic_reasoner(mock_neo4j_conn)

        assert reasoner1 is not reasoner2  # Different instances
