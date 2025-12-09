"""Integration tests for SemanticReasoner with real Neo4j database.

Requires Neo4j running with test data loaded.
"""

import os

import pytest

from agentic_neurodata_conversion.kg_service.db.neo4j_connection import (
    get_neo4j_connection,
    reset_neo4j_connection,
)
from agentic_neurodata_conversion.kg_service.services.semantic_reasoner import (
    get_semantic_reasoner,
    reset_semantic_reasoner,
)


@pytest.fixture
async def neo4j_conn():
    """Create real Neo4j connection for integration tests."""
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")

    if not neo4j_password:
        pytest.skip("NEO4J_PASSWORD not set - skipping integration tests")

    reset_neo4j_connection()
    conn = get_neo4j_connection(neo4j_uri, neo4j_user, neo4j_password)

    # Try to connect - skip if Neo4j is not available
    try:
        await conn.connect()
    except Exception as e:
        pytest.skip(f"Neo4j not available - skipping integration tests: {e}")

    # Verify Neo4j is accessible
    health = await conn.health_check()
    if not health:
        await conn.close()
        pytest.skip("Neo4j not accessible - skipping integration tests")

    yield conn

    await conn.close()
    reset_neo4j_connection()


@pytest.fixture
def semantic_reasoner(neo4j_conn):
    """Create SemanticReasoner with real Neo4j connection."""
    reset_semantic_reasoner()
    return get_semantic_reasoner(neo4j_conn)


@pytest.mark.integration
@pytest.mark.asyncio
class TestFindAncestorsIntegration:
    """Integration tests for find_ancestors()."""

    async def test_uberon_hierarchy_traversal(self, semantic_reasoner):
        """Test hierarchy traversal for UBERON terms (real data)."""
        # Ammon's horn should have ancestors: hippocampal formation → cerebral cortex → brain → CNS
        result = await semantic_reasoner.find_ancestors("UBERON:0001954")

        assert len(result) > 0, "Should find ancestors for Ammon's horn"
        assert any(a["label"] == "hippocampal formation" for a in result)
        assert any(a["label"] == "brain" for a in result)

        # Verify distances are correct
        distances = {a["label"]: a["distance"] for a in result}
        assert distances["hippocampal formation"] < distances["brain"]

    async def test_ncbi_taxonomy_hierarchies(self, semantic_reasoner):
        """Test NCBITaxonomy terms now have hierarchies (Phase 1.5 fix)."""
        # Mus musculus should return ancestors: Mus → Muridae → Rodentia → Mammalia → Vertebrata
        result = await semantic_reasoner.find_ancestors("NCBITaxon:10090")

        assert len(result) > 0, "NCBITaxonomy should have hierarchies in Phase 1.5"
        # Check for key taxonomic ancestors
        ancestor_labels = {a["label"] for a in result}
        assert "Mammalia" in ancestor_labels, "Should find Mammalia ancestor"
        assert "Vertebrata" in ancestor_labels or "Rodentia" in ancestor_labels, (
            "Should find high-level taxonomic ancestors"
        )

    async def test_root_term_no_ancestors(self, semantic_reasoner):
        """Test root term returns no ancestors."""
        # Central nervous system is root or near-root
        result = await semantic_reasoner.find_ancestors("UBERON:0001017")

        # Should have 0 or very few ancestors
        assert len(result) <= 1, "Root term should have few/no ancestors"

    async def test_max_depth_parameter(self, semantic_reasoner):
        """Test max_depth parameter limits traversal."""
        result_depth_2 = await semantic_reasoner.find_ancestors("UBERON:0001954", max_depth=2)
        result_depth_5 = await semantic_reasoner.find_ancestors("UBERON:0001954", max_depth=5)

        # More ancestors should be found with greater depth
        assert len(result_depth_2) <= len(result_depth_5)

        # All results from depth_2 should be within 2 hops
        for ancestor in result_depth_2:
            assert ancestor["distance"] <= 2

    async def test_ncbi_taxonomy_vertebrate_hierarchy(self, semantic_reasoner):
        """Test vertebrate species hierarchy traversal."""
        # Homo sapiens should have ancestors: Homo → Hominidae → Primates → Mammalia → Vertebrata
        result = await semantic_reasoner.find_ancestors("NCBITaxon:9606")

        assert len(result) >= 3, "Human should have multiple taxonomic ancestors"
        ancestor_labels = {a["label"] for a in result}

        # Check for vertebrate markers
        assert any(label in ancestor_labels for label in ["Mammalia", "Vertebrata", "Primates"]), (
            "Human should have vertebrate taxonomic ancestors"
        )

    async def test_ncbi_taxonomy_invertebrate_hierarchy(self, semantic_reasoner):
        """Test invertebrate species hierarchy traversal."""
        # C. elegans should have ancestors: Caenorhabditis → Nematoda → Protostomia
        result = await semantic_reasoner.find_ancestors("NCBITaxon:6239")

        assert len(result) >= 1, "C. elegans should have taxonomic ancestors"
        ancestor_labels = {a["label"] for a in result}

        # Check for invertebrate markers
        assert any(label in ancestor_labels for label in ["Nematoda", "Protostomia"]), (
            "C. elegans should have invertebrate taxonomic ancestors"
        )


@pytest.mark.integration
@pytest.mark.asyncio
class TestValidateWithHierarchyIntegration:
    """Integration tests for validate_with_hierarchy()."""

    async def test_stage1_exact_match(self, semantic_reasoner):
        """Test Stage 1: exact match."""
        result = await semantic_reasoner.validate_with_hierarchy(
            "ecephys.ElectrodeGroup.location", "hippocampal formation"
        )

        assert result["status"] == "validated"
        assert result["match_type"] == "exact"
        assert result["confidence"] == 1.0
        assert result["normalized_value"] == "hippocampal formation"
        assert result["ontology_term_id"] == "UBERON:0002421"

    async def test_stage2_synonym_match(self, semantic_reasoner):
        """Test Stage 2: synonym match (if synonyms exist)."""
        # Try partial match that might hit synonym or semantic stage
        result = await semantic_reasoner.validate_with_hierarchy("ecephys.ElectrodeGroup.location", "cortex")

        assert result["status"] == "validated"
        assert result["match_type"] in ["synonym", "semantic"]
        assert result["confidence"] >= 0.85
        assert result["normalized_value"] is not None

    async def test_stage3_semantic_search(self, semantic_reasoner):
        """Test Stage 3: semantic search with partial match."""
        result = await semantic_reasoner.validate_with_hierarchy("ecephys.ElectrodeGroup.location", "Ammon")

        assert result["status"] == "validated"
        assert result["match_type"] in ["semantic", "synonym", "exact"]
        assert result["normalized_value"] == "Ammon's horn"

    async def test_stage3_with_hierarchy_constraint(self, semantic_reasoner):
        """Test Stage 3 with hierarchy validation."""
        result = await semantic_reasoner.validate_with_hierarchy(
            "ecephys.ElectrodeGroup.location", "Ammon", required_ancestor="brain"
        )

        assert result["status"] == "validated"
        assert result["normalized_value"] == "Ammon's horn"
        # Should have semantic_info with ancestors
        if result["match_type"] == "semantic":
            assert "semantic_info" in result
            assert "ancestors" in result["semantic_info"]

    async def test_stage4_no_match(self, semantic_reasoner):
        """Test Stage 4: no match."""
        result = await semantic_reasoner.validate_with_hierarchy(
            "ecephys.ElectrodeGroup.location", "invalid_brain_region_xyz"
        )

        assert result["status"] == "needs_review"
        assert result["match_type"] is None
        assert result["confidence"] == 0.0
        assert result["action_required"] is True
        assert len(result["warnings"]) > 0

    async def test_hierarchy_constraint_rejection(self, semantic_reasoner):
        """Test hierarchy constraint rejects invalid ancestors."""
        # cerebral cortex is NOT under cerebellum
        result = await semantic_reasoner.validate_with_hierarchy(
            "ecephys.ElectrodeGroup.location", "cerebral cortex", required_ancestor="cerebellum"
        )

        # Should either not match or have lower confidence
        if result["match_type"] is not None:
            assert result["confidence"] < 1.0
        else:
            assert result["status"] == "needs_review"

    async def test_non_ontology_field(self, semantic_reasoner):
        """Test non-ontology-governed field."""
        result = await semantic_reasoner.validate_with_hierarchy("general.session_id", "session_001")

        assert result["status"] == "not_applicable"
        assert "not ontology-governed" in result["warnings"][0]


@pytest.mark.integration
@pytest.mark.asyncio
class TestCrossFieldCompatibilityIntegration:
    """Integration tests for check_cross_field_compatibility()."""

    async def test_vertebrate_brain_valid(self, semantic_reasoner):
        """Test valid vertebrate + brain structure."""
        result = await semantic_reasoner.check_cross_field_compatibility(
            "NCBITaxon:10090",  # Mus musculus
            "UBERON:0002421",  # hippocampal formation
        )

        assert result["is_compatible"] is True
        assert result["confidence"] > 0.0
        assert "vertebrate" in result["reasoning"].lower()

    async def test_invertebrate_brain_invalid(self, semantic_reasoner):
        """Test invalid invertebrate + brain structure."""
        result = await semantic_reasoner.check_cross_field_compatibility(
            "NCBITaxon:6239",  # C. elegans (worm)
            "UBERON:0002421",  # hippocampal formation
        )

        assert result["is_compatible"] is False
        assert result["confidence"] == 0.95  # Updated from 0.90 (Phase 1.5 hierarchy-based)
        assert "invertebrate" in result["reasoning"].lower()

    async def test_drosophila_brain_invalid(self, semantic_reasoner):
        """Test Drosophila (fly) cannot have vertebrate brain."""
        result = await semantic_reasoner.check_cross_field_compatibility(
            "NCBITaxon:7227",  # Drosophila
            "UBERON:0000955",  # brain
        )

        assert result["is_compatible"] is False
        assert result["confidence"] == 0.95  # Updated from 0.90 (Phase 1.5 hierarchy-based)

    async def test_vertebrate_hierarchy_detection(self, semantic_reasoner):
        """Test vertebrate detection via hierarchy (Phase 1.5 enhancement)."""
        # Rattus norvegicus (rat) should be detected as vertebrate via hierarchy
        result = await semantic_reasoner.check_cross_field_compatibility(
            "NCBITaxon:10116",  # Rattus norvegicus (rat)
            "UBERON:0000955",  # brain
        )

        assert result["is_compatible"] is True
        assert result["confidence"] == 0.95  # High confidence with hierarchy-based detection
        assert "vertebrate" in result["reasoning"].lower()

    async def test_invertebrate_hierarchy_detection(self, semantic_reasoner):
        """Test invertebrate detection via hierarchy for non-hardcoded species."""
        # Test that any invertebrate (not just C. elegans/Drosophila) is detected
        # This validates that hardcoded list was removed in Phase 1.5
        result = await semantic_reasoner.check_cross_field_compatibility(
            "NCBITaxon:6239",  # C. elegans (should still work)
            "UBERON:0000955",  # brain
        )

        assert result["is_compatible"] is False
        assert result["confidence"] == 0.95
        # Reasoning should mention invertebrate ancestors (not hardcoded)
        assert "invertebrate" in result["reasoning"].lower()
        # Should mention taxonomic ancestors (Nematoda, Protostomia, etc.)
        assert any(term in result["reasoning"] for term in ["Nematoda", "Protostomia", "ancestors"])

    async def test_invalid_species_term(self, semantic_reasoner):
        """Test with invalid species term ID."""
        result = await semantic_reasoner.check_cross_field_compatibility(
            "NCBITaxon:99999",  # Invalid
            "UBERON:0002421",
        )

        assert result["is_compatible"] is False
        assert result["confidence"] == 0.0
        assert "not found" in result["reasoning"].lower()

    async def test_invalid_anatomy_term(self, semantic_reasoner):
        """Test with invalid anatomy term ID."""
        result = await semantic_reasoner.check_cross_field_compatibility(
            "NCBITaxon:10090",
            "UBERON:99999",  # Invalid
        )

        assert result["is_compatible"] is False
        assert result["confidence"] == 0.0
        assert "not found" in result["reasoning"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
class TestEndToEndScenarios:
    """End-to-end integration test scenarios."""

    async def test_complete_validation_workflow(self, semantic_reasoner):
        """Test complete validation workflow from user input to result."""
        # Scenario: User enters "hippocampus" for brain location
        user_input = "hippocampus"
        field_path = "ecephys.ElectrodeGroup.location"

        # Step 1: Validate the input
        result = await semantic_reasoner.validate_with_hierarchy(field_path, user_input)

        assert result["status"] == "validated"
        assert result["normalized_value"] is not None
        assert result["ontology_term_id"] is not None

        # Step 2: Verify it's under "brain" (hierarchy check)
        result_with_constraint = await semantic_reasoner.validate_with_hierarchy(
            field_path, user_input, required_ancestor="brain"
        )

        assert result_with_constraint["status"] == "validated"

    async def test_semantic_search_fallback(self, semantic_reasoner):
        """Test semantic search fallback when exact match fails."""
        # User enters partial/informal term
        user_input = "Ammon"  # Partial match for "Ammon's horn"
        field_path = "ecephys.ElectrodeGroup.location"

        result = await semantic_reasoner.validate_with_hierarchy(field_path, user_input)

        # Should still match via semantic search
        assert result["status"] == "validated"
        assert "ammon" in result["normalized_value"].lower()
        assert result["confidence"] >= 0.85
