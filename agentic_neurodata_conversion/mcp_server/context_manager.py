"""
Context Manager for Session Persistence.

Implements write-through caching strategy:
- Primary storage: Redis (fast access, TTL support)
- Backup storage: Filesystem (persistence across restarts)

All operations are async and maintain consistency between both storages.
"""

from datetime import datetime
import json
from pathlib import Path
from typing import Any, Optional

from redis.asyncio import Redis

from agentic_neurodata_conversion.models.session_context import SessionContext


class ContextManager:
    """
    Manages session context persistence with write-through Redis + filesystem strategy.

    This class provides async CRUD operations for session context, ensuring that:
    - All writes go to both Redis (cache) and filesystem (backup)
    - Reads prefer Redis but fall back to filesystem on cache miss
    - Filesystem fallback automatically restores Redis cache
    - Sessions have configurable TTL in Redis
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        filesystem_base_path: str = "./sessions",
        session_ttl_seconds: int = 86400,  # 24 hours
    ) -> None:
        """
        Initialize ContextManager.

        Args:
            redis_url: Redis connection URL (default: "redis://localhost:6379/0")
            filesystem_base_path: Base path for filesystem storage (default: "./sessions")
            session_ttl_seconds: TTL for sessions in Redis in seconds (default: 86400 = 24h)
        """
        self._redis_url = redis_url
        self._filesystem_base_path = filesystem_base_path
        self._session_ttl_seconds = session_ttl_seconds
        self._redis: Optional[Redis] = None

    async def connect(self) -> None:
        """
        Connect to Redis.

        Raises:
            Exception: If Redis connection fails
        """
        self._redis = Redis.from_url(
            self._redis_url,
            decode_responses=False,  # We'll handle JSON encoding ourselves
        )
        # Test connection
        await self._redis.ping()

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            try:
                await self._redis.aclose()
            except Exception:
                pass  # Ignore errors during cleanup
            finally:
                self._redis = None

    def _get_redis_key(self, session_id: str) -> str:
        """
        Generate Redis key for a session.

        Args:
            session_id: Session identifier

        Returns:
            Redis key string (format: "session:{session_id}")
        """
        return f"session:{session_id}"

    def _get_filesystem_path(self, session_id: str) -> Path:
        """
        Generate filesystem path for a session.

        Args:
            session_id: Session identifier

        Returns:
            Path object pointing to session JSON file
        """
        return Path(self._filesystem_base_path) / "sessions" / f"{session_id}.json"

    async def create_session(self, session: SessionContext) -> None:
        """
        Create a new session (write-through to both Redis and filesystem).

        Args:
            session: SessionContext to persist

        Raises:
            Exception: If Redis write fails or filesystem write fails
        """
        if self._redis is None:
            raise RuntimeError("ContextManager not connected. Call connect() first.")

        # Serialize session to JSON
        session_dict = session.model_dump(mode="json")
        session_json = json.dumps(session_dict)

        # Write to Redis with TTL
        redis_key = self._get_redis_key(session.session_id)
        await self._redis.setex(
            redis_key,
            self._session_ttl_seconds,
            session_json.encode("utf-8"),
        )

        # Write to filesystem
        fs_path = self._get_filesystem_path(session.session_id)
        fs_path.parent.mkdir(parents=True, exist_ok=True)
        fs_path.write_text(session_json, encoding="utf-8")

    async def get_session(self, session_id: str) -> Optional[SessionContext]:
        """
        Retrieve a session (from Redis, with filesystem fallback).

        Reads from Redis first. If not found, falls back to filesystem and
        restores the Redis cache.

        Args:
            session_id: Session identifier

        Returns:
            SessionContext if found, None otherwise

        Raises:
            Exception: If Redis operation fails or data is corrupted
        """
        if self._redis is None:
            raise RuntimeError("ContextManager not connected. Call connect() first.")

        redis_key = self._get_redis_key(session_id)

        # Try Redis first
        data = await self._redis.get(redis_key)
        if data is not None:
            session_dict = json.loads(data.decode("utf-8"))
            return SessionContext(**session_dict)

        # Fallback to filesystem
        fs_path = self._get_filesystem_path(session_id)
        if not fs_path.exists():
            return None

        # Load from filesystem
        session_json = fs_path.read_text(encoding="utf-8")
        session_dict = json.loads(session_json)
        session = SessionContext(**session_dict)

        # Restore to Redis cache with TTL
        await self._redis.setex(
            redis_key,
            self._session_ttl_seconds,
            session_json.encode("utf-8"),
        )

        return session

    async def update_session(self, session_id: str, updates: dict[str, Any]) -> None:
        """
        Update a session (write-through to both Redis and filesystem).

        Automatically updates the last_updated timestamp.

        Args:
            session_id: Session identifier
            updates: Dictionary of fields to update

        Raises:
            ValueError: If session doesn't exist
            Exception: If Redis or filesystem write fails
        """
        if self._redis is None:
            raise RuntimeError("ContextManager not connected. Call connect() first.")

        # Get existing session
        session = await self.get_session(session_id)
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        # Apply updates
        for key, value in updates.items():
            setattr(session, key, value)

        # Update timestamp
        session.last_updated = datetime.utcnow()

        # Serialize to JSON
        session_dict = session.model_dump(mode="json")
        session_json = json.dumps(session_dict)

        # Write to Redis with TTL
        redis_key = self._get_redis_key(session_id)
        await self._redis.setex(
            redis_key,
            self._session_ttl_seconds,
            session_json.encode("utf-8"),
        )

        # Write to filesystem
        fs_path = self._get_filesystem_path(session_id)
        fs_path.write_text(session_json, encoding="utf-8")

    async def delete_session(self, session_id: str) -> None:
        """
        Delete a session (from both Redis and filesystem).

        Args:
            session_id: Session identifier

        Note:
            Does not raise error if session doesn't exist (idempotent operation)
        """
        if self._redis is None:
            raise RuntimeError("ContextManager not connected. Call connect() first.")

        # Delete from Redis
        redis_key = self._get_redis_key(session_id)
        await self._redis.delete(redis_key)

        # Delete from filesystem
        fs_path = self._get_filesystem_path(session_id)
        if fs_path.exists():
            fs_path.unlink()
