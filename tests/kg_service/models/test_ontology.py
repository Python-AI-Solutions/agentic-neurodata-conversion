"""Ontology Model Tests.

Tests for OntologyTerm Pydantic model.
Validates model creation, defaults, and field types.
"""

from agentic_neurodata_conversion.kg_service.models.ontology import OntologyTerm


def test_ontology_term_creation():
    """Verify OntologyTerm model creation with all fields."""
    term = OntologyTerm(
        term_id="NCBITaxon:10090",
        label="Mus musculus",
        definition="House mouse",
        synonyms=["mouse", "house mouse"],
        ontology_name="NCBITaxonomy",
        parent_terms=["NCBITaxon:10088"],
    )

    assert term.term_id == "NCBITaxon:10090"
    assert term.label == "Mus musculus"
    assert term.definition == "House mouse"
    assert len(term.synonyms) == 2
    assert "mouse" in term.synonyms
    assert term.ontology_name == "NCBITaxonomy"
    assert len(term.parent_terms) == 1


def test_ontology_term_defaults():
    """Verify default values for optional fields."""
    term = OntologyTerm(term_id="NCBITaxon:10090", label="Mus musculus", ontology_name="NCBITaxonomy")

    assert term.definition is None
    assert term.synonyms == []
    assert term.parent_terms == []
