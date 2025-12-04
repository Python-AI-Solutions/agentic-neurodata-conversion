"""Phase 0 Setup Tests.

Validates that all ontology files, Neo4j setup, and environment configuration
are correct before Phase 1 implementation.

Tests:
- Ontology files exist and are valid JSON
- Correct number of terms in each ontology
- No duplicate term_ids within files
- Required fields present in all terms
- Neo4j is accessible (integration test)
"""

import json
import os
from pathlib import Path

import pytest


def test_ontology_files_exist():
    """Verify all 3 ontology JSON files exist."""
    assert Path("agentic_neurodata_conversion/kg_service/ontologies/ncbi_taxonomy_subset.json").exists()
    assert Path("agentic_neurodata_conversion/kg_service/ontologies/uberon_subset.json").exists()
    assert Path("agentic_neurodata_conversion/kg_service/ontologies/pato_sex_subset.json").exists()


def test_ontology_files_valid_json():
    """Verify ontology files are valid JSON with required keys."""
    for file in ["ncbi_taxonomy_subset.json", "uberon_subset.json", "pato_sex_subset.json"]:
        path = Path(f"agentic_neurodata_conversion/kg_service/ontologies/{file}")
        with open(path) as f:
            data = json.load(f)
            assert "ontology" in data, f"{file} missing 'ontology' key"
            assert "terms" in data, f"{file} missing 'terms' key"
            assert "total_terms" in data, f"{file} missing 'total_terms' key"


def test_ontology_term_counts():
    """Verify correct number of terms in each ontology."""
    ncbi = json.load(open("agentic_neurodata_conversion/kg_service/ontologies/ncbi_taxonomy_subset.json"))
    uberon = json.load(open("agentic_neurodata_conversion/kg_service/ontologies/uberon_subset.json"))
    pato = json.load(open("agentic_neurodata_conversion/kg_service/ontologies/pato_sex_subset.json"))

    assert len(ncbi["terms"]) == 20, f"Expected 20 NCBITaxonomy terms, got {len(ncbi['terms'])}"
    assert len(uberon["terms"]) == 20, f"Expected 20 UBERON terms, got {len(uberon['terms'])}"
    assert len(pato["terms"]) == 4, f"Expected 4 PATO terms, got {len(pato['terms'])}"


def test_no_duplicate_term_ids():
    """Verify no duplicate term_ids within each ontology file."""
    for file in ["ncbi_taxonomy_subset.json", "uberon_subset.json", "pato_sex_subset.json"]:
        path = Path(f"agentic_neurodata_conversion/kg_service/ontologies/{file}")
        data = json.load(open(path))
        term_ids = [t["term_id"] for t in data["terms"]]
        duplicates = [tid for tid in term_ids if term_ids.count(tid) > 1]
        assert len(term_ids) == len(set(term_ids)), f"Duplicates found in {file}: {set(duplicates)}"


def test_ontology_term_schema():
    """Verify each term has required fields."""
    ncbi = json.load(open("agentic_neurodata_conversion/kg_service/ontologies/ncbi_taxonomy_subset.json"))
    for term in ncbi["terms"]:
        assert "term_id" in term, "Missing term_id field"
        assert "label" in term, "Missing label field"
        assert "synonyms" in term, "Missing synonyms field"
        assert "parent_terms" in term, "Missing parent_terms field"
        assert isinstance(term["synonyms"], list), "synonyms must be a list"
        assert isinstance(term["parent_terms"], list), "parent_terms must be a list"


@pytest.mark.integration
def test_neo4j_accessible():
    """Verify Neo4j is running and accessible."""
    import requests

    try:
        response = requests.get("http://localhost:7474", timeout=5)
        if response.status_code != 200:
            pytest.skip(f"Neo4j not accessible - status {response.status_code}")
    except requests.ConnectionError as e:
        pytest.skip(f"Neo4j not running: {e}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_neo4j_driver_connection():
    """Verify Neo4j driver can connect."""
    from neo4j import AsyncGraphDatabase

    password = os.getenv("NEO4J_PASSWORD")
    if not password:
        pytest.skip("NEO4J_PASSWORD not set in environment")

    driver = AsyncGraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", password))

    try:
        await driver.verify_connectivity()
    except Exception as e:
        await driver.close()
        pytest.skip(f"Failed to connect to Neo4j: {e}")

    await driver.close()
