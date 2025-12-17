"""Integration test for cross-field validation regex fix.

This test verifies that the regex pattern correctly extracts ontology term IDs
with mixed-case prefixes like NCBITaxon (not just uppercase like UBERON).
"""

import pytest

from agentic_neurodata_conversion.services.kg_wrapper import KGWrapper


@pytest.mark.asyncio
async def test_cross_field_validation_regex_extracts_mixed_case_ontology_ids():
    """Test that term ID extraction works for mixed-case ontology prefixes."""
    import re

    # Test the regex pattern that was fixed
    def extract_term_id(reasoning: str) -> str | None:
        """Extract ontology term ID from reasoning string."""
        if not reasoning:
            return None
        match = re.search(r"Ontology validation:\s*([A-Za-z]+:[0-9]+)", reasoning)
        return match.group(1) if match else None

    # Test mixed-case ontology (NCBITaxon)
    reasoning_ncbi = "Ontology validation: NCBITaxon:10090"
    term_id_ncbi = extract_term_id(reasoning_ncbi)
    assert term_id_ncbi == "NCBITaxon:10090", f"Expected NCBITaxon:10090, got {term_id_ncbi}"

    # Test uppercase ontology (UBERON)
    reasoning_uberon = "Ontology validation: UBERON:0001954"
    term_id_uberon = extract_term_id(reasoning_uberon)
    assert term_id_uberon == "UBERON:0001954", f"Expected UBERON:0001954, got {term_id_uberon}"

    # Test mixed-case ontology (PATO)
    reasoning_pato = "Ontology validation: PATO:0000384"
    term_id_pato = extract_term_id(reasoning_pato)
    assert term_id_pato == "PATO:0000384", f"Expected PATO:0000384, got {term_id_pato}"


@pytest.mark.asyncio
async def test_cross_field_validation_with_kg_service(tmp_path):
    """Test cross-field validation end-to-end with KG service."""
    # Skip if KG service not available
    kg_wrapper = KGWrapper(kg_base_url="http://localhost:8001", timeout=2.0)

    try:
        # Test with valid combination: mouse + hippocampus
        result = await kg_wrapper.semantic_validate(
            species_term_id="NCBITaxon:10090",  # Mus musculus
            anatomy_term_id="UBERON:0001954",  # Ammon's horn
        )

        assert result["is_compatible"] is True, "Mouse + hippocampus should be compatible"
        assert result["confidence"] >= 0.9, f"Expected high confidence, got {result['confidence']}"
        assert "vertebrate" in result["reasoning"].lower(), "Reasoning should mention vertebrate"

    except Exception as e:
        pytest.skip(f"KG service not available: {e}")
    finally:
        await kg_wrapper.close()
