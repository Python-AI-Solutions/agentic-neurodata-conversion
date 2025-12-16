"""Tests for load_schema_fields.py script."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from agentic_neurodata_conversion.kg_service.scripts.load_schema_fields import (
    load_schema_fields,
    main,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_schema_fields(tmp_path):
    """Test loading schema fields from JSON."""
    # Create test schema fields JSON in proper directory structure
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    test_file = config_dir / "schema_fields.json"

    test_data = {
        "fields": [
            {
                "field_path": "subject.species",
                "description": "Species of subject",
                "required": True,
                "ontology_governed": True,
                "ontology": "NCBITaxonomy",
                "value_type": "string",
                "examples": ["Mus musculus", "Rattus norvegicus"],
            },
            {
                "field_path": "subject.subject_id",
                "description": "Unique subject identifier",
                "required": True,
                "ontology_governed": False,
                "value_type": "string",
                "examples": ["sub-001", "sub-002"],
            },
        ]
    }

    with open(test_file, "w") as f:
        json.dump(test_data, f)

    # Mock connection
    mock_conn = Mock()
    mock_conn.execute_write = AsyncMock(return_value=[{"fields_created": 2}])

    # Patch Path to point to tmp_path
    with patch("agentic_neurodata_conversion.kg_service.scripts.load_schema_fields.Path") as mock_path_cls:
        # Make Path(__file__).parent.parent return tmp_path
        mock_instance = Mock()
        mock_instance.parent.parent = tmp_path
        mock_path_cls.return_value = mock_instance

        # Load schema fields
        count = await load_schema_fields(mock_conn)

    # Verify results
    assert count == 2
    # CRITICAL: Should only call execute_write ONCE (batched, not N times)
    assert mock_conn.execute_write.call_count == 1

    # Verify batched query structure
    call_args = mock_conn.execute_write.call_args_list[0]
    query = call_args[0][0]
    params = call_args[0][1]

    # Verify UNWIND syntax for batch processing
    assert "UNWIND $fields_batch" in query
    assert "fields_batch" in params
    assert len(params["fields_batch"]) == 2

    # Verify batch structure for first field
    first_field = params["fields_batch"][0]
    assert first_field["field_path"] == "subject.species"
    assert first_field["ontology_governed"] is True
    assert first_field["ontology_name"] == "NCBITaxonomy"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_schema_fields_no_examples(tmp_path):
    """Test loading schema fields without examples."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    test_file = config_dir / "schema_fields.json"

    test_data = {
        "fields": [
            {
                "field_path": "test.field",
                "description": "Test field",
                "required": False,
                "ontology_governed": False,
                "value_type": "string",
                # No examples field
            }
        ]
    }

    with open(test_file, "w") as f:
        json.dump(test_data, f)

    mock_conn = Mock()
    mock_conn.execute_write = AsyncMock(return_value=[{"fields_created": 1}])

    with patch("agentic_neurodata_conversion.kg_service.scripts.load_schema_fields.Path") as mock_path_cls:
        mock_instance = Mock()
        mock_instance.parent.parent = tmp_path
        mock_path_cls.return_value = mock_instance

        count = await load_schema_fields(mock_conn)

    assert count == 1

    # Verify examples_json is None when no examples (in batch)
    call_params = mock_conn.execute_write.call_args_list[0][0][1]
    first_field = call_params["fields_batch"][0]
    assert first_field["examples_json"] is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_schema_fields_with_nested_examples(tmp_path):
    """Test loading schema fields with nested array examples."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    test_file = config_dir / "schema_fields.json"

    test_data = {
        "fields": [
            {
                "field_path": "test.field",
                "description": "Test field",
                "required": False,
                "ontology_governed": False,
                "value_type": "array",
                "examples": [["value1", "value2"], ["value3"]],
            }
        ]
    }

    with open(test_file, "w") as f:
        json.dump(test_data, f)

    mock_conn = Mock()
    mock_conn.execute_write = AsyncMock(return_value=[{"fields_created": 1}])

    with patch("agentic_neurodata_conversion.kg_service.scripts.load_schema_fields.Path") as mock_path_cls:
        mock_instance = Mock()
        mock_instance.parent.parent = tmp_path
        mock_path_cls.return_value = mock_instance

        count = await load_schema_fields(mock_conn)

    assert count == 1

    # Verify examples are converted to JSON string (in batch)
    call_params = mock_conn.execute_write.call_args_list[0][0][1]
    first_field = call_params["fields_batch"][0]
    assert first_field["examples_json"] is not None
    # Should be able to parse back to original
    parsed = json.loads(first_field["examples_json"])
    assert parsed == [["value1", "value2"], ["value3"]]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_schema_fields_no_ontology(tmp_path):
    """Test loading non-ontology-governed fields."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    test_file = config_dir / "schema_fields.json"

    test_data = {
        "fields": [
            {
                "field_path": "general.session_id",
                "description": "Session identifier",
                "required": True,
                "ontology_governed": False,
                "value_type": "string",
                "examples": [],
            }
        ]
    }

    with open(test_file, "w") as f:
        json.dump(test_data, f)

    mock_conn = Mock()
    mock_conn.execute_write = AsyncMock(return_value=[{"fields_created": 1}])

    with patch("agentic_neurodata_conversion.kg_service.scripts.load_schema_fields.Path") as mock_path_cls:
        mock_instance = Mock()
        mock_instance.parent.parent = tmp_path
        mock_path_cls.return_value = mock_instance

        count = await load_schema_fields(mock_conn)

    assert count == 1

    # Verify ontology_name is None for non-ontology-governed fields (in batch)
    call_params = mock_conn.execute_write.call_args_list[0][0][1]
    first_field = call_params["fields_batch"][0]
    assert first_field["ontology_name"] is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_load_schema_fields_empty_examples(tmp_path):
    """Test loading schema fields with empty examples list."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    test_file = config_dir / "schema_fields.json"

    test_data = {
        "fields": [
            {
                "field_path": "test.field",
                "description": "Test field",
                "required": False,
                "ontology_governed": False,
                "value_type": "string",
                "examples": [],  # Empty list
            }
        ]
    }

    with open(test_file, "w") as f:
        json.dump(test_data, f)

    mock_conn = Mock()
    mock_conn.execute_write = AsyncMock(return_value=[{"fields_created": 1}])

    with patch("agentic_neurodata_conversion.kg_service.scripts.load_schema_fields.Path") as mock_path_cls:
        mock_instance = Mock()
        mock_instance.parent.parent = tmp_path
        mock_path_cls.return_value = mock_instance

        count = await load_schema_fields(mock_conn)

    assert count == 1

    # Empty examples should result in None (in batch)
    call_params = mock_conn.execute_write.call_args_list[0][0][1]
    first_field = call_params["fields_batch"][0]
    assert first_field["examples_json"] is None


@pytest.mark.unit
@pytest.mark.asyncio
@patch("agentic_neurodata_conversion.kg_service.scripts.load_schema_fields.get_settings")
@patch("agentic_neurodata_conversion.kg_service.scripts.load_schema_fields.get_neo4j_connection")
@patch("agentic_neurodata_conversion.kg_service.scripts.load_schema_fields.load_schema_fields", new_callable=AsyncMock)
async def test_main_success(mock_load_fields, mock_get_conn, mock_get_settings):
    """Test main function success path."""
    # Mock settings
    mock_settings = Mock()
    mock_settings.graph_db = Mock()
    mock_settings.graph_db.uri = "bolt://localhost:7687"
    mock_settings.graph_db.user = "neo4j"
    mock_settings.graph_db.password = "password"
    mock_settings.graph_db.database = "neo4j"
    mock_get_settings.return_value = mock_settings

    # Mock connection
    mock_conn = Mock()
    mock_conn.connect = AsyncMock()
    mock_conn.health_check = AsyncMock(return_value=True)
    mock_conn.close = AsyncMock()
    mock_get_conn.return_value = mock_conn

    # Mock load_schema_fields
    mock_load_fields.return_value = 5

    # Run main
    await main()

    # Verify connection lifecycle
    mock_conn.connect.assert_called_once()
    mock_conn.close.assert_called_once()

    # Verify load_schema_fields was called
    mock_load_fields.assert_called_once_with(mock_conn)


@pytest.mark.unit
@pytest.mark.asyncio
@patch("agentic_neurodata_conversion.kg_service.scripts.load_schema_fields.get_settings")
@patch("agentic_neurodata_conversion.kg_service.scripts.load_schema_fields.get_neo4j_connection")
async def test_main_connection_cleanup_on_error(mock_get_conn, mock_get_settings):
    """Test main function cleans up connection on error."""
    # Mock settings
    mock_settings = Mock()
    mock_settings.graph_db = Mock()
    mock_settings.graph_db.uri = "bolt://localhost:7687"
    mock_settings.graph_db.user = "neo4j"
    mock_settings.graph_db.password = "password"
    mock_settings.graph_db.database = "neo4j"
    mock_get_settings.return_value = mock_settings

    # Mock connection that raises error
    mock_conn = Mock()
    mock_conn.connect = AsyncMock()
    mock_conn.health_check = AsyncMock(return_value=True)
    mock_conn.close = AsyncMock()
    mock_get_conn.return_value = mock_conn

    # Patch load_schema_fields to raise error
    with patch(
        "agentic_neurodata_conversion.kg_service.scripts.load_schema_fields.load_schema_fields",
        new_callable=AsyncMock,
        side_effect=Exception("Load error"),
    ):
        with pytest.raises(Exception, match="Load error"):
            await main()

    # Verify connection was still closed
    mock_conn.close.assert_called_once()
