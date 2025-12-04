"""Tests for load_ontologies.py script."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from agentic_neurodata_conversion.kg_service.scripts.load_ontologies import (
    create_constraints_and_indexes,
    create_is_a_relationships,
    load_ontology_file,
    main,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_constraints_and_indexes():
    """Test creating constraints and indexes."""
    mock_conn = Mock()
    mock_conn.execute_write = AsyncMock()

    await create_constraints_and_indexes(mock_conn)

    # Should call execute_write 3 times (constraint + 2 indexes)
    assert mock_conn.execute_write.call_count == 3

    # Verify constraint creation
    calls = [str(call) for call in mock_conn.execute_write.call_args_list]
    assert any("ontology_term_id" in str(call) for call in calls)
    assert any("ontology_term_label" in str(call) for call in calls)
    assert any("ontology_term_ontology" in str(call) for call in calls)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_ontology_file(tmp_path):
    """Test loading a single ontology file."""
    # Create test JSON file
    test_data = {
        "ontology": "TestOntology",
        "terms": [
            {
                "term_id": "TEST:001",
                "label": "test term 1",
                "definition": "Test definition",
                "synonyms": ["syn1", "syn2"],
                "parent_terms": [],
            },
            {
                "term_id": "TEST:002",
                "label": "test term 2",
                "definition": "Test definition 2",
                "synonyms": [],
                "parent_terms": ["TEST:001"],
            },
        ],
    }

    test_file = tmp_path / "test_ontology.json"
    with open(test_file, "w") as f:
        json.dump(test_data, f)

    # Mock connection
    mock_conn = Mock()
    mock_conn.execute_write = AsyncMock()

    # Load file
    count = await load_ontology_file(mock_conn, test_file)

    # Verify results
    assert count == 2
    assert mock_conn.execute_write.call_count == 2

    # Verify parameters passed to execute_write
    first_call_args = mock_conn.execute_write.call_args_list[0]
    assert "term_id" in str(first_call_args)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_ontology_file_missing_optional_fields(tmp_path):
    """Test loading ontology file with missing optional fields."""
    test_data = {
        "ontology": "TestOntology",
        "terms": [
            {
                "term_id": "TEST:001",
                "label": "test term",
                # No definition, synonyms, or parent_terms
            }
        ],
    }

    test_file = tmp_path / "test_ontology.json"
    with open(test_file, "w") as f:
        json.dump(test_data, f)

    mock_conn = Mock()
    mock_conn.execute_write = AsyncMock()

    count = await load_ontology_file(mock_conn, test_file)

    assert count == 1
    # Should handle missing fields gracefully
    call_args = mock_conn.execute_write.call_args_list[0]
    params = call_args[0][1]  # Second argument is params dict
    assert params["synonyms"] == []
    assert params["parent_terms"] == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_is_a_relationships():
    """Test creating IS_A relationships."""
    mock_conn = Mock()
    mock_conn.execute_write = AsyncMock(return_value=[{"relationships_created": 5}])

    await create_is_a_relationships(mock_conn)

    # Should call execute_write once
    assert mock_conn.execute_write.call_count == 1

    # Verify query contains IS_A and parent_terms
    call_args = mock_conn.execute_write.call_args_list[0]
    query = call_args[0][0]
    assert "IS_A" in query
    assert "parent_terms" in query


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_is_a_relationships_no_result():
    """Test creating IS_A relationships when query returns no result."""
    mock_conn = Mock()
    mock_conn.execute_write = AsyncMock(return_value=[])

    await create_is_a_relationships(mock_conn)

    # Should handle empty result gracefully
    assert mock_conn.execute_write.call_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
@patch("agentic_neurodata_conversion.kg_service.scripts.load_ontologies.get_settings")
@patch("agentic_neurodata_conversion.kg_service.scripts.load_ontologies.get_neo4j_connection")
@patch("agentic_neurodata_conversion.kg_service.scripts.load_ontologies.create_constraints_and_indexes")
@patch("agentic_neurodata_conversion.kg_service.scripts.load_ontologies.load_ontology_file")
@patch("agentic_neurodata_conversion.kg_service.scripts.load_ontologies.create_is_a_relationships")
async def test_main_success(
    mock_create_rels, mock_load_file, mock_create_constraints, mock_get_conn, mock_get_settings, tmp_path
):
    """Test main function success path."""
    # Mock settings
    mock_settings = Mock()
    mock_settings.neo4j_uri = "bolt://localhost:7687"
    mock_settings.neo4j_user = "neo4j"
    mock_settings.neo4j_password = "password"
    mock_get_settings.return_value = mock_settings

    # Mock connection
    mock_conn = Mock()
    mock_conn.connect = AsyncMock()
    mock_conn.close = AsyncMock()
    mock_get_conn.return_value = mock_conn

    # Mock file loading
    mock_load_file.return_value = 10

    # Create dummy ontology files
    ontology_dir = tmp_path / "ontologies"
    ontology_dir.mkdir()
    (ontology_dir / "ncbi_taxonomy_subset.json").write_text("{}")
    (ontology_dir / "uberon_subset.json").write_text("{}")
    (ontology_dir / "pato_sex_subset.json").write_text("{}")

    # Patch Path to use tmp_path
    with patch("agentic_neurodata_conversion.kg_service.scripts.load_ontologies.Path") as mock_path:
        mock_file = Mock()
        mock_file.parent.parent = tmp_path
        mock_path.return_value = mock_file

        # Run main
        await main()

    # Verify connection lifecycle
    mock_conn.connect.assert_called_once()
    mock_conn.close.assert_called_once()

    # Verify functions called
    mock_create_constraints.assert_called_once_with(mock_conn)
    mock_create_rels.assert_called_once_with(mock_conn)


@pytest.mark.unit
@pytest.mark.asyncio
@patch("agentic_neurodata_conversion.kg_service.scripts.load_ontologies.get_settings")
@patch("agentic_neurodata_conversion.kg_service.scripts.load_ontologies.get_neo4j_connection")
async def test_main_connection_cleanup_on_error(mock_get_conn, mock_get_settings):
    """Test main function cleans up connection on error."""
    # Mock settings
    mock_settings = Mock()
    mock_settings.neo4j_uri = "bolt://localhost:7687"
    mock_settings.neo4j_user = "neo4j"
    mock_settings.neo4j_password = "password"
    mock_get_settings.return_value = mock_settings

    # Mock connection that raises error during operations
    mock_conn = Mock()
    mock_conn.connect = AsyncMock()
    mock_conn.close = AsyncMock()
    mock_conn.execute_write = AsyncMock(side_effect=Exception("Database error"))
    mock_get_conn.return_value = mock_conn

    # Run main and expect error
    with pytest.raises(Exception, match="Database error"):
        await main()

    # Verify connection was still closed
    mock_conn.close.assert_called_once()
