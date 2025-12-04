"""Tests for verify_phase1.py script."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from agentic_neurodata_conversion.kg_service.scripts.verify_phase1 import (
    main,
    verify_constraints,
    verify_indexes,
    verify_ontology_terms,
    verify_relationships,
    verify_sample_queries,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_ontology_terms_success():
    """Test verifying ontology terms with correct counts."""
    mock_conn = Mock()
    mock_conn.execute_read = AsyncMock(
        side_effect=[
            # First query: count by ontology
            [
                {"ontology": "NCBITaxonomy", "term_count": 20},
                {"ontology": "PATO", "term_count": 4},
                {"ontology": "UBERON", "term_count": 20},
            ],
            # Second query: total count
            [{"total": 44}],
        ]
    )

    result = await verify_ontology_terms(mock_conn)

    assert result is True
    assert mock_conn.execute_read.call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_ontology_terms_wrong_counts():
    """Test verifying ontology terms with wrong counts."""
    mock_conn = Mock()
    mock_conn.execute_read = AsyncMock(
        side_effect=[
            # Wrong counts
            [
                {"ontology": "NCBITaxonomy", "term_count": 15},  # Should be 20
                {"ontology": "PATO", "term_count": 4},
                {"ontology": "UBERON", "term_count": 20},
            ],
            [{"total": 39}],  # Wrong total
        ]
    )

    result = await verify_ontology_terms(mock_conn)

    assert result is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_constraints_found():
    """Test verifying constraints when constraint exists."""
    mock_conn = Mock()
    mock_conn.execute_read = AsyncMock(
        return_value=[
            {"name": "ontology_term_id", "type": "UNIQUENESS"},
        ]
    )

    result = await verify_constraints(mock_conn)

    assert result is True
    mock_conn.execute_read.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_constraints_not_found():
    """Test verifying constraints when constraint is missing."""
    mock_conn = Mock()
    mock_conn.execute_read = AsyncMock(
        return_value=[
            {"name": "some_other_constraint", "type": "UNIQUENESS"},
        ]
    )

    result = await verify_constraints(mock_conn)

    assert result is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_indexes_found():
    """Test verifying indexes when indexes exist."""
    mock_conn = Mock()
    mock_conn.execute_read = AsyncMock(
        return_value=[
            {"name": "ontology_term_label", "type": "BTREE"},
            {"name": "ontology_term_ontology", "type": "BTREE"},
        ]
    )

    result = await verify_indexes(mock_conn)

    assert result is True
    mock_conn.execute_read.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_indexes_missing():
    """Test verifying indexes when some are missing."""
    mock_conn = Mock()
    mock_conn.execute_read = AsyncMock(
        return_value=[
            {"name": "ontology_term_label", "type": "BTREE"},
            # Missing ontology_term_ontology index
        ]
    )

    result = await verify_indexes(mock_conn)

    assert result is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_sample_queries_all_pass():
    """Test verifying sample queries when all pass."""
    mock_conn = Mock()
    mock_conn.execute_read = AsyncMock(
        side_effect=[
            # Query 1: Mus musculus
            [{"term_id": "NCBITaxon:10090", "synonyms": ["mouse", "house mouse", "laboratory mouse"]}],
            # Query 2: hippocampus
            [{"term_id": "UBERON:0001954", "label": "Ammon's horn"}],
            # Query 3: male sex
            [{"label": "male"}],
        ]
    )

    result = await verify_sample_queries(mock_conn)

    assert result is True
    assert mock_conn.execute_read.call_count == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_sample_queries_mus_musculus_wrong_id():
    """Test verifying sample queries with wrong term ID."""
    mock_conn = Mock()
    mock_conn.execute_read = AsyncMock(
        return_value=[
            {"term_id": "NCBITaxon:99999", "synonyms": []}  # Wrong ID
        ]
    )

    result = await verify_sample_queries(mock_conn)

    assert result is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_sample_queries_no_results():
    """Test verifying sample queries when query returns no results."""
    mock_conn = Mock()
    mock_conn.execute_read = AsyncMock(return_value=[])

    result = await verify_sample_queries(mock_conn)

    assert result is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_relationships_success():
    """Test verifying IS_A relationships when they exist."""
    mock_conn = Mock()
    mock_conn.execute_read = AsyncMock(return_value=[{"relationship_count": 42}])

    result = await verify_relationships(mock_conn)

    assert result is True
    mock_conn.execute_read.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_verify_relationships_none_found():
    """Test verifying IS_A relationships when none exist."""
    mock_conn = Mock()
    mock_conn.execute_read = AsyncMock(return_value=[{"relationship_count": 0}])

    result = await verify_relationships(mock_conn)

    assert result is False


@pytest.mark.unit
@pytest.mark.asyncio
@patch("agentic_neurodata_conversion.kg_service.scripts.verify_phase1.get_settings")
@patch("agentic_neurodata_conversion.kg_service.scripts.verify_phase1.get_neo4j_connection")
@patch("agentic_neurodata_conversion.kg_service.scripts.verify_phase1.verify_ontology_terms")
@patch("agentic_neurodata_conversion.kg_service.scripts.verify_phase1.verify_constraints")
@patch("agentic_neurodata_conversion.kg_service.scripts.verify_phase1.verify_indexes")
@patch("agentic_neurodata_conversion.kg_service.scripts.verify_phase1.verify_sample_queries")
@patch("agentic_neurodata_conversion.kg_service.scripts.verify_phase1.verify_relationships")
async def test_main_all_checks_pass(
    mock_verify_rels,
    mock_verify_queries,
    mock_verify_indexes,
    mock_verify_constraints,
    mock_verify_terms,
    mock_get_conn,
    mock_get_settings,
):
    """Test main function when all checks pass."""
    # Mock settings
    mock_settings = Mock()
    mock_settings.neo4j_uri = "bolt://localhost:7687"
    mock_settings.neo4j_user = "neo4j"
    mock_settings.neo4j_password = "password"
    mock_get_settings.return_value = mock_settings

    # Mock connection with successful health check
    mock_conn = Mock()
    mock_conn.connect = AsyncMock()
    mock_conn.close = AsyncMock()
    mock_conn.health_check = AsyncMock(return_value=True)
    mock_get_conn.return_value = mock_conn

    # All checks pass
    mock_verify_terms.return_value = True
    mock_verify_constraints.return_value = True
    mock_verify_indexes.return_value = True
    mock_verify_queries.return_value = True
    mock_verify_rels.return_value = True

    # Run main
    await main()

    # Verify all checks were called
    mock_verify_terms.assert_called_once_with(mock_conn)
    mock_verify_constraints.assert_called_once_with(mock_conn)
    mock_verify_indexes.assert_called_once_with(mock_conn)
    mock_verify_queries.assert_called_once_with(mock_conn)
    mock_verify_rels.assert_called_once_with(mock_conn)

    # Verify connection lifecycle
    mock_conn.connect.assert_called_once()
    mock_conn.close.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
@patch("agentic_neurodata_conversion.kg_service.scripts.verify_phase1.get_settings")
@patch("agentic_neurodata_conversion.kg_service.scripts.verify_phase1.get_neo4j_connection")
async def test_main_health_check_fails(mock_get_conn, mock_get_settings):
    """Test main function when health check fails."""
    # Mock settings
    mock_settings = Mock()
    mock_settings.neo4j_uri = "bolt://localhost:7687"
    mock_settings.neo4j_user = "neo4j"
    mock_settings.neo4j_password = "password"
    mock_get_settings.return_value = mock_settings

    # Mock connection with failed health check
    mock_conn = Mock()
    mock_conn.connect = AsyncMock()
    mock_conn.close = AsyncMock()
    mock_conn.health_check = AsyncMock(return_value=False)
    mock_get_conn.return_value = mock_conn

    # Run main
    await main()

    # Verify connection was still closed
    mock_conn.close.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
@patch("agentic_neurodata_conversion.kg_service.scripts.verify_phase1.get_settings")
@patch("agentic_neurodata_conversion.kg_service.scripts.verify_phase1.get_neo4j_connection")
@patch("agentic_neurodata_conversion.kg_service.scripts.verify_phase1.verify_ontology_terms")
@patch("agentic_neurodata_conversion.kg_service.scripts.verify_phase1.verify_constraints")
@patch("agentic_neurodata_conversion.kg_service.scripts.verify_phase1.verify_indexes")
@patch("agentic_neurodata_conversion.kg_service.scripts.verify_phase1.verify_sample_queries")
@patch("agentic_neurodata_conversion.kg_service.scripts.verify_phase1.verify_relationships")
async def test_main_some_checks_fail(
    mock_verify_rels,
    mock_verify_queries,
    mock_verify_indexes,
    mock_verify_constraints,
    mock_verify_terms,
    mock_get_conn,
    mock_get_settings,
):
    """Test main function when some checks fail."""
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
    mock_conn.health_check = AsyncMock(return_value=True)
    mock_get_conn.return_value = mock_conn

    # Some checks pass, some fail
    mock_verify_terms.return_value = True
    mock_verify_constraints.return_value = False  # Fail
    mock_verify_indexes.return_value = True
    mock_verify_queries.return_value = False  # Fail
    mock_verify_rels.return_value = True

    # Run main
    await main()

    # Verify all checks were still called
    assert mock_verify_terms.call_count == 1
    assert mock_verify_constraints.call_count == 1
    assert mock_verify_indexes.call_count == 1
    assert mock_verify_queries.call_count == 1
    assert mock_verify_rels.call_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
@patch("agentic_neurodata_conversion.kg_service.scripts.verify_phase1.get_settings")
@patch("agentic_neurodata_conversion.kg_service.scripts.verify_phase1.get_neo4j_connection")
async def test_main_connection_cleanup_on_error(mock_get_conn, mock_get_settings):
    """Test main function cleans up connection on error."""
    # Mock settings
    mock_settings = Mock()
    mock_settings.neo4j_uri = "bolt://localhost:7687"
    mock_settings.neo4j_user = "neo4j"
    mock_settings.neo4j_password = "password"
    mock_get_settings.return_value = mock_settings

    # Mock connection that raises error during health check
    mock_conn = Mock()
    mock_conn.connect = AsyncMock()
    mock_conn.close = AsyncMock()
    mock_conn.health_check = AsyncMock(side_effect=Exception("Connection error"))
    mock_get_conn.return_value = mock_conn

    # Run main and expect error
    with pytest.raises(Exception, match="Connection error"):
        await main()

    # Verify connection was still closed
    mock_conn.close.assert_called_once()
