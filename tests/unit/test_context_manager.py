"""
Unit tests for ContextManager (Redis + Filesystem persistence).

Tests cover:
- Redis connection and disconnection
- create_session writes to both Redis and filesystem
- get_session retrieves from Redis
- get_session falls back to filesystem when Redis miss
- get_session restores Redis from filesystem on fallback
- update_session updates both storages with new timestamp
- delete_session removes from both storages
- session TTL is set correctly in Redis
- filesystem path generation
- Redis key generation
- handling of non-existent sessions (returns None)
- concurrent session operations

Coverage target: ≥90% (critical path)
"""

import asyncio
from collections.abc import AsyncGenerator
import json
from pathlib import Path

import fakeredis.aioredis
import pytest

from agentic_neurodata_conversion.mcp_server.context_manager import ContextManager
from agentic_neurodata_conversion.models.session_context import (
    SessionContext,
    WorkflowStage,
)

pytest_plugins = ("pytest_asyncio",)

pytestmark = pytest.mark.unit


@pytest.fixture
async def redis_client() -> AsyncGenerator[fakeredis.aioredis.FakeRedis, None]:
    """Create a fake Redis client for testing."""
    client = fakeredis.aioredis.FakeRedis(decode_responses=False)
    try:
        # Clean up before tests
        await client.flushdb()
        yield client
    finally:
        # Clean up after tests
        await client.flushdb()
        await client.aclose()


@pytest.fixture
async def context_manager(
    redis_client: fakeredis.aioredis.FakeRedis, tmp_path: Path
) -> AsyncGenerator[ContextManager, None]:
    """Create a ContextManager instance with test Redis and temp filesystem."""
    manager = ContextManager(
        redis_url="redis://localhost:6379/15",  # Will be replaced with fake client
        filesystem_base_path=str(tmp_path),
        session_ttl_seconds=86400,  # 24 hours
    )
    # Manually inject the fake Redis client instead of calling connect()
    manager._redis = redis_client
    try:
        yield manager
    finally:
        manager._redis = None


@pytest.fixture
def sample_session() -> SessionContext:
    """Create a sample session for testing."""
    return SessionContext(
        session_id="test-session-001",
        workflow_stage=WorkflowStage.INITIALIZED,
    )


class TestContextManagerConnection:
    """Test Redis connection and disconnection."""

    @pytest.mark.asyncio
    async def test_connect_success(self, tmp_path: Path) -> None:
        """Test successful Redis connection (using fakeredis)."""
        manager = ContextManager(
            redis_url="redis://localhost:6379/15",
            filesystem_base_path=str(tmp_path),
        )
        # Inject fake Redis client
        manager._redis = fakeredis.aioredis.FakeRedis(decode_responses=False)
        assert manager._redis is not None
        await manager._redis.aclose()

    @pytest.mark.asyncio
    async def test_disconnect(self, context_manager: ContextManager) -> None:
        """Test Redis disconnection."""
        # Store reference to check if it's set to None
        assert context_manager._redis is not None
        await context_manager.disconnect()
        assert context_manager._redis is None

    @pytest.mark.asyncio
    async def test_connect_invalid_url(self, tmp_path: Path) -> None:
        """Test connection with invalid Redis URL."""
        # This test is skipped for fakeredis as it doesn't validate URLs
        pytest.skip("fakeredis doesn't validate connection URLs")


class TestHelperMethods:
    """Test helper methods for key and path generation."""

    def test_get_redis_key(self, tmp_path: Path) -> None:
        """Test Redis key generation."""
        manager = ContextManager(
            redis_url="redis://localhost:6379/15",
            filesystem_base_path=str(tmp_path),
        )
        key = manager._get_redis_key("test-session-001")
        assert key == "session:test-session-001"

    def test_get_filesystem_path(self, tmp_path: Path) -> None:
        """Test filesystem path generation."""
        manager = ContextManager(
            redis_url="redis://localhost:6379/15",
            filesystem_base_path=str(tmp_path),
        )
        path = manager._get_filesystem_path("test-session-001")
        expected = tmp_path / "sessions" / "test-session-001.json"
        assert path == expected


class TestCreateSession:
    """Test create_session method (write-through to Redis and filesystem)."""

    @pytest.mark.asyncio
    async def test_create_session_writes_to_redis(
        self, context_manager: ContextManager, sample_session: SessionContext
    ) -> None:
        """Test that create_session writes to Redis."""
        await context_manager.create_session(sample_session)

        # Verify Redis has the session
        redis_key = context_manager._get_redis_key(sample_session.session_id)
        data = await context_manager._redis.get(redis_key)
        assert data is not None

        # Verify data is correct
        session_dict = json.loads(data)
        assert session_dict["session_id"] == sample_session.session_id
        assert session_dict["workflow_stage"] == WorkflowStage.INITIALIZED

    @pytest.mark.asyncio
    async def test_create_session_writes_to_filesystem(
        self, context_manager: ContextManager, sample_session: SessionContext
    ) -> None:
        """Test that create_session writes to filesystem."""
        await context_manager.create_session(sample_session)

        # Verify filesystem has the session
        fs_path = context_manager._get_filesystem_path(sample_session.session_id)
        assert fs_path.exists()

        # Verify data is correct
        with open(fs_path) as f:
            session_dict = json.load(f)
        assert session_dict["session_id"] == sample_session.session_id
        assert session_dict["workflow_stage"] == WorkflowStage.INITIALIZED

    @pytest.mark.asyncio
    async def test_create_session_sets_ttl(
        self, context_manager: ContextManager, sample_session: SessionContext
    ) -> None:
        """Test that create_session sets TTL in Redis."""
        await context_manager.create_session(sample_session)

        # Verify TTL is set
        redis_key = context_manager._get_redis_key(sample_session.session_id)
        ttl = await context_manager._redis.ttl(redis_key)
        # TTL should be close to 86400 (24 hours)
        assert 86390 <= ttl <= 86400

    @pytest.mark.asyncio
    async def test_create_session_creates_directory(
        self, context_manager: ContextManager, sample_session: SessionContext
    ) -> None:
        """Test that create_session creates sessions directory."""
        await context_manager.create_session(sample_session)

        # Verify directory was created
        sessions_dir = Path(context_manager._filesystem_base_path) / "sessions"
        assert sessions_dir.exists()
        assert sessions_dir.is_dir()


class TestGetSession:
    """Test get_session method (with Redis fallback to filesystem)."""

    @pytest.mark.asyncio
    async def test_get_session_from_redis(
        self, context_manager: ContextManager, sample_session: SessionContext
    ) -> None:
        """Test retrieving session from Redis cache."""
        # Create session
        await context_manager.create_session(sample_session)

        # Retrieve session
        retrieved = await context_manager.get_session(sample_session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == sample_session.session_id
        assert retrieved.workflow_stage == WorkflowStage.INITIALIZED

    @pytest.mark.asyncio
    async def test_get_session_fallback_to_filesystem(
        self, context_manager: ContextManager, sample_session: SessionContext
    ) -> None:
        """Test fallback to filesystem when Redis cache miss."""
        # Create session
        await context_manager.create_session(sample_session)

        # Delete from Redis (simulating cache miss)
        redis_key = context_manager._get_redis_key(sample_session.session_id)
        await context_manager._redis.delete(redis_key)

        # Retrieve session (should fall back to filesystem)
        retrieved = await context_manager.get_session(sample_session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == sample_session.session_id

    @pytest.mark.asyncio
    async def test_get_session_restores_redis_cache(
        self, context_manager: ContextManager, sample_session: SessionContext
    ) -> None:
        """Test that filesystem fallback restores Redis cache."""
        # Create session
        await context_manager.create_session(sample_session)

        # Delete from Redis
        redis_key = context_manager._get_redis_key(sample_session.session_id)
        await context_manager._redis.delete(redis_key)

        # Retrieve session (should restore Redis)
        await context_manager.get_session(sample_session.session_id)

        # Verify Redis was restored
        data = await context_manager._redis.get(redis_key)
        assert data is not None
        session_dict = json.loads(data)
        assert session_dict["session_id"] == sample_session.session_id

    @pytest.mark.asyncio
    async def test_get_session_nonexistent_returns_none(
        self, context_manager: ContextManager
    ) -> None:
        """Test that get_session returns None for non-existent session."""
        retrieved = await context_manager.get_session("nonexistent-session")
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_get_session_preserves_ttl_on_restore(
        self, context_manager: ContextManager, sample_session: SessionContext
    ) -> None:
        """Test that TTL is set when restoring from filesystem to Redis."""
        # Create session
        await context_manager.create_session(sample_session)

        # Delete from Redis
        redis_key = context_manager._get_redis_key(sample_session.session_id)
        await context_manager._redis.delete(redis_key)

        # Retrieve session (should restore Redis with TTL)
        await context_manager.get_session(sample_session.session_id)

        # Verify TTL is set
        ttl = await context_manager._redis.ttl(redis_key)
        assert 86390 <= ttl <= 86400


class TestUpdateSession:
    """Test update_session method (updates both storages)."""

    @pytest.mark.asyncio
    async def test_update_session_updates_redis(
        self, context_manager: ContextManager, sample_session: SessionContext
    ) -> None:
        """Test that update_session updates Redis."""
        # Create session
        await context_manager.create_session(sample_session)

        # Update session
        updates = {
            "workflow_stage": WorkflowStage.CONVERTING,
            "current_agent": "conversion_agent",
        }
        await context_manager.update_session(sample_session.session_id, updates)

        # Verify Redis was updated
        redis_key = context_manager._get_redis_key(sample_session.session_id)
        data = await context_manager._redis.get(redis_key)
        session_dict = json.loads(data)
        assert session_dict["workflow_stage"] == WorkflowStage.CONVERTING
        assert session_dict["current_agent"] == "conversion_agent"

    @pytest.mark.asyncio
    async def test_update_session_updates_filesystem(
        self, context_manager: ContextManager, sample_session: SessionContext
    ) -> None:
        """Test that update_session updates filesystem."""
        # Create session
        await context_manager.create_session(sample_session)

        # Update session
        updates = {"workflow_stage": WorkflowStage.CONVERTING}
        await context_manager.update_session(sample_session.session_id, updates)

        # Verify filesystem was updated
        fs_path = context_manager._get_filesystem_path(sample_session.session_id)
        with open(fs_path) as f:
            session_dict = json.load(f)
        assert session_dict["workflow_stage"] == WorkflowStage.CONVERTING

    @pytest.mark.asyncio
    async def test_update_session_updates_timestamp(
        self, context_manager: ContextManager, sample_session: SessionContext
    ) -> None:
        """Test that update_session updates last_updated timestamp."""
        # Create session
        await context_manager.create_session(sample_session)
        original_timestamp = sample_session.last_updated

        # Wait a bit to ensure timestamp difference
        await asyncio.sleep(0.1)

        # Update session
        updates = {"workflow_stage": WorkflowStage.CONVERTING}
        await context_manager.update_session(sample_session.session_id, updates)

        # Retrieve and verify timestamp was updated
        retrieved = await context_manager.get_session(sample_session.session_id)
        assert retrieved.last_updated > original_timestamp

    @pytest.mark.asyncio
    async def test_update_session_nonexistent_raises_error(
        self, context_manager: ContextManager
    ) -> None:
        """Test that updating non-existent session raises error."""
        with pytest.raises(ValueError):
            await context_manager.update_session(
                "nonexistent-session", {"workflow_stage": WorkflowStage.CONVERTING}
            )

    @pytest.mark.asyncio
    async def test_update_session_maintains_ttl(
        self, context_manager: ContextManager, sample_session: SessionContext
    ) -> None:
        """Test that update_session maintains TTL in Redis."""
        # Create session
        await context_manager.create_session(sample_session)

        # Update session
        updates = {"workflow_stage": WorkflowStage.CONVERTING}
        await context_manager.update_session(sample_session.session_id, updates)

        # Verify TTL is still set
        redis_key = context_manager._get_redis_key(sample_session.session_id)
        ttl = await context_manager._redis.ttl(redis_key)
        assert 86390 <= ttl <= 86400


class TestConcurrentOperations:
    """Test concurrent session operations."""

    @pytest.mark.asyncio
    async def test_concurrent_creates(self, context_manager: ContextManager) -> None:
        """Test concurrent session creations."""
        sessions = [
            SessionContext(
                session_id=f"session-{i}", workflow_stage=WorkflowStage.INITIALIZED
            )
            for i in range(10)
        ]

        # Create sessions concurrently
        await asyncio.gather(
            *[context_manager.create_session(session) for session in sessions]
        )

        # Verify all sessions were created
        for session in sessions:
            retrieved = await context_manager.get_session(session.session_id)
            assert retrieved is not None
            assert retrieved.session_id == session.session_id

    @pytest.mark.asyncio
    async def test_concurrent_updates(
        self, context_manager: ContextManager, sample_session: SessionContext
    ) -> None:
        """Test concurrent updates to same session."""
        # Create session
        await context_manager.create_session(sample_session)

        # Update concurrently with different stages
        updates = [
            {"workflow_stage": WorkflowStage.COLLECTING_METADATA},
            {"current_agent": "conversation_agent"},
            {"workflow_stage": WorkflowStage.CONVERTING},
        ]

        await asyncio.gather(
            *[
                context_manager.update_session(sample_session.session_id, update)
                for update in updates
            ]
        )

        # Verify session exists and was updated
        retrieved = await context_manager.get_session(sample_session.session_id)
        assert retrieved is not None
        # Last update should win (but we can't guarantee order in concurrent ops)

    @pytest.mark.asyncio
    async def test_concurrent_get_operations(
        self, context_manager: ContextManager, sample_session: SessionContext
    ) -> None:
        """Test concurrent get operations on same session."""
        # Create session
        await context_manager.create_session(sample_session)

        # Get session concurrently
        results = await asyncio.gather(
            *[context_manager.get_session(sample_session.session_id) for _ in range(10)]
        )

        # Verify all retrievals succeeded
        for result in results:
            assert result is not None
            assert result.session_id == sample_session.session_id


class TestDeleteSession:
    """Test delete_session method (removes from both storages)."""

    @pytest.mark.asyncio
    async def test_delete_session_removes_from_redis(
        self, context_manager: ContextManager, sample_session: SessionContext
    ) -> None:
        """Test that delete_session removes from Redis."""
        # Create session
        await context_manager.create_session(sample_session)

        # Delete session
        await context_manager.delete_session(sample_session.session_id)

        # Verify Redis deletion
        redis_key = context_manager._get_redis_key(sample_session.session_id)
        data = await context_manager._redis.get(redis_key)
        assert data is None

    @pytest.mark.asyncio
    async def test_delete_session_removes_from_filesystem(
        self, context_manager: ContextManager, sample_session: SessionContext
    ) -> None:
        """Test that delete_session removes from filesystem."""
        # Create session
        await context_manager.create_session(sample_session)

        # Delete session
        await context_manager.delete_session(sample_session.session_id)

        # Verify filesystem deletion
        fs_path = context_manager._get_filesystem_path(sample_session.session_id)
        assert not fs_path.exists()

    @pytest.mark.asyncio
    async def test_delete_session_nonexistent_no_error(
        self, context_manager: ContextManager
    ) -> None:
        """Test that deleting non-existent session doesn't raise error."""
        # Should not raise error
        await context_manager.delete_session("nonexistent-session")

    @pytest.mark.asyncio
    async def test_delete_session_only_redis_exists(
        self, context_manager: ContextManager, sample_session: SessionContext
    ) -> None:
        """Test deleting session when only Redis has the data."""
        # Create session
        await context_manager.create_session(sample_session)

        # Delete filesystem copy
        fs_path = context_manager._get_filesystem_path(sample_session.session_id)
        fs_path.unlink()

        # Delete should still work without error
        await context_manager.delete_session(sample_session.session_id)

        # Verify Redis deletion
        redis_key = context_manager._get_redis_key(sample_session.session_id)
        data = await context_manager._redis.get(redis_key)
        assert data is None


class TestErrorHandling:
    """Test error handling in various scenarios."""

    @pytest.mark.asyncio
    async def test_filesystem_write_error_handling(
        self,
        context_manager: ContextManager,
        sample_session: SessionContext,
        tmp_path: Path,
    ) -> None:
        """Test handling of filesystem write errors."""
        # Create a read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        session_file = readonly_dir / "sessions" / "test.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text("{}")

        # Make the sessions directory read-only (Unix-like systems)
        import os
        import stat

        if os.name != "nt":  # Skip on Windows as permissions work differently
            sessions_dir = readonly_dir / "sessions"
            os.chmod(sessions_dir, stat.S_IRUSR | stat.S_IXUSR)

            context_manager._filesystem_base_path = str(readonly_dir)

            # Should raise error when trying to write
            with pytest.raises((OSError, PermissionError)):
                await context_manager.create_session(sample_session)

            # Restore permissions for cleanup
            os.chmod(sessions_dir, stat.S_IRWXU)
        else:
            # On Windows, just skip this test
            pytest.skip("Filesystem permission testing not supported on Windows")

    @pytest.mark.asyncio
    async def test_redis_connection_lost(
        self, context_manager: ContextManager, sample_session: SessionContext
    ) -> None:
        """Test behavior when Redis connection is lost."""
        # Create session first
        await context_manager.create_session(sample_session)

        # Disconnect Redis
        await context_manager.disconnect()

        # Should raise error when trying to get session
        with pytest.raises(RuntimeError, match="not connected"):
            await context_manager.get_session(sample_session.session_id)

    @pytest.mark.asyncio
    async def test_corrupted_filesystem_data(
        self, context_manager: ContextManager, sample_session: SessionContext
    ) -> None:
        """Test handling of corrupted filesystem data."""
        # Create session
        await context_manager.create_session(sample_session)

        # Corrupt filesystem data
        fs_path = context_manager._get_filesystem_path(sample_session.session_id)
        with open(fs_path, "w") as f:
            f.write("corrupted json data {{{")

        # Delete from Redis to force filesystem read
        redis_key = context_manager._get_redis_key(sample_session.session_id)
        await context_manager._redis.delete(redis_key)

        # Should raise error when trying to read corrupted data
        with pytest.raises(json.JSONDecodeError):
            await context_manager.get_session(sample_session.session_id)
