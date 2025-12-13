"""Async Neo4j Connection Wrapper.

Provides async/await interface to Neo4j database with connection pooling,
health checks, and transaction management.

This module follows the async patterns used throughout the agentic-neurodata-conversion
codebase and provides a clean interface for executing Cypher queries.

Example:
    >>> from agentic_neurodata_conversion.kg_service.db.neo4j_connection import get_neo4j_connection
    >>> conn = get_neo4j_connection(uri, user, password)
    >>> await conn.connect()
    >>> result = await conn.execute_read("MATCH (n:OntologyTerm) RETURN count(n) as count")
    >>> await conn.close()
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncSession
from neo4j.exceptions import ServiceUnavailable

logger = logging.getLogger(__name__)


class AsyncNeo4jConnection:
    """Async wrapper for Neo4j driver.

    Provides connection management, health checks, and transaction execution
    using async/await patterns. Implements singleton pattern for global connection.

    Attributes:
        uri: Neo4j connection URI (e.g., bolt://localhost:7687)
        user: Neo4j username
        password: Neo4j password
        database: Neo4j database name
    """

    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j") -> None:
        """Initialize Neo4j connection parameters.

        Args:
            uri: Neo4j connection URI
            user: Neo4j username
            password: Neo4j password
            database: Neo4j database name (default: 'neo4j')
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        """Establish connection to Neo4j.

        Creates async Neo4j driver with connection pooling and verifies connectivity.
        Connection pool settings are optimized for FastAPI async workloads.

        Raises:
            ServiceUnavailable: If Neo4j is not accessible
        """
        try:
            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_pool_size=50,
                connection_timeout=5.0,
                max_connection_lifetime=3600,
            )
            # Verify connectivity
            await self._driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {self.uri}")
        except ServiceUnavailable as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    async def close(self) -> None:
        """Close Neo4j driver and connection pool.

        Gracefully shuts down all connections in the pool.
        Should be called during application shutdown.
        """
        if self._driver:
            await self._driver.close()
            logger.info("Neo4j connection closed")

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Context manager for Neo4j sessions.

        Provides async context manager for Neo4j sessions with automatic cleanup.
        Sessions are borrowed from the connection pool and returned after use.

        Yields:
            AsyncSession: Neo4j async session

        Raises:
            RuntimeError: If driver not connected

        Example:
            >>> async with conn.session() as session:
            ...     result = await session.run("MATCH (n) RETURN count(n)")
            ...     records = await result.data()
        """
        if not self._driver:
            raise RuntimeError("Driver not connected. Call connect() first.")

        async with self._driver.session(database=self.database) as session:
            yield session

    async def execute_read(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute read transaction.

        Executes a Cypher query in a read transaction. Use for SELECT/MATCH queries
        that do not modify the database.

        Args:
            query: Cypher query string
            params: Optional query parameters

        Returns:
            List of record dictionaries

        Example:
            >>> result = await conn.execute_read(
            ...     "MATCH (t:OntologyTerm {term_id: $id}) RETURN t",
            ...     {"id": "NCBITaxon:10090"}
            ... )
        """
        async with self.session() as session:
            result = await session.run(query, params or {})
            records: list[dict[str, Any]] = await result.data()
            return records

    async def execute_write(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Execute write transaction.

        Executes a Cypher query in a write transaction. Use for CREATE/MERGE/SET/DELETE
        queries that modify the database.

        Args:
            query: Cypher query string
            params: Optional query parameters

        Returns:
            List of record dictionaries

        Example:
            >>> result = await conn.execute_write(
            ...     "CREATE (t:OntologyTerm {term_id: $id, label: $label}) RETURN t",
            ...     {"id": "NCBITaxon:10090", "label": "Mus musculus"}
            ... )
        """
        async with self.session() as session:
            result = await session.run(query, params or {})
            records: list[dict[str, Any]] = await result.data()
            return records

    async def health_check(self) -> bool:
        """Check if Neo4j is accessible.

        Executes a simple query to verify database connectivity and responsiveness.
        Used by FastAPI health endpoints and monitoring.

        Returns:
            bool: True if Neo4j is healthy, False otherwise

        Example:
            >>> is_healthy = await conn.health_check()
            >>> if not is_healthy:
            ...     logger.error("Neo4j is down!")
        """
        try:
            result = await self.execute_read("RETURN 1 AS health")
            return len(result) > 0 and result[0].get("health") == 1
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# Global instance (singleton pattern)
_neo4j_connection: AsyncNeo4jConnection | None = None


def get_neo4j_connection(uri: str, user: str, password: str, database: str = "neo4j") -> AsyncNeo4jConnection:
    """Get global Neo4j connection instance.

    Implements singleton pattern to reuse connection across the application.
    The connection instance is created once and reused for all requests.

    Args:
        uri: Neo4j connection URI
        user: Neo4j username
        password: Neo4j password
        database: Neo4j database name (default: 'neo4j')

    Returns:
        AsyncNeo4jConnection: Global connection instance

    Example:
        >>> from agentic_neurodata_conversion.kg_service.config import get_settings
        >>> settings = get_settings()
        >>> conn = get_neo4j_connection(
        ...     settings.neo4j_uri,
        ...     settings.neo4j_user,
        ...     settings.neo4j_password,
        ...     settings.neo4j_database
        ... )
        >>> await conn.connect()
    """
    global _neo4j_connection
    if _neo4j_connection is None:
        _neo4j_connection = AsyncNeo4jConnection(uri, user, password, database)
    return _neo4j_connection


def reset_neo4j_connection() -> None:
    """Reset the global Neo4j connection instance.

    Primarily used for testing to reset the connection between test cases.
    Should not be used in production code.

    Example:
        >>> reset_neo4j_connection()  # Force new connection on next get
        >>> conn = get_neo4j_connection(uri, user, password)
    """
    global _neo4j_connection
    _neo4j_connection = None
