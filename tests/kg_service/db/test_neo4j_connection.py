"""Neo4j Connection Tests.

Tests for AsyncNeo4jConnection wrapper and singleton pattern.
Validates connection creation and instance management.
"""

import pytest


@pytest.mark.asyncio
async def test_connection_creation():
    """Verify connection object is created correctly."""
    from kg_service.db.neo4j_connection import AsyncNeo4jConnection

    conn = AsyncNeo4jConnection("bolt://localhost:7687", "neo4j", "password")
    assert conn.uri == "bolt://localhost:7687"
    assert conn.user == "neo4j"
    assert conn.password == "password"
    assert conn._driver is None  # Not connected yet


@pytest.mark.asyncio
async def test_singleton_pattern():
    """Verify get_neo4j_connection returns same instance."""
    from kg_service.db.neo4j_connection import get_neo4j_connection, reset_neo4j_connection

    reset_neo4j_connection()
    conn1 = get_neo4j_connection("bolt://localhost:7687", "neo4j", "pass")
    conn2 = get_neo4j_connection("bolt://localhost:7687", "neo4j", "pass")
    assert conn1 is conn2, "get_neo4j_connection should return the same instance"
