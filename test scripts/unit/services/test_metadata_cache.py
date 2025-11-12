"""
Unit tests for MetadataCache service.

Tests intelligent caching for LLM-inferred metadata.
"""

import asyncio
from datetime import datetime, timedelta

import pytest
from services.metadata_cache import (
    CacheEntry,
    MetadataCache,
    get_metadata_cache,
)


@pytest.mark.unit
@pytest.mark.service
class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_cache_entry_creation(self):
        """Test creating a cache entry."""
        entry = CacheEntry(
            value="test_value",
            confidence=85.0,
            timestamp=datetime.now(),
            input_hash="abc123",
            source="test_source",
        )

        assert entry.value == "test_value"
        assert entry.confidence == 85.0
        assert entry.source == "test_source"
        assert entry.hit_count == 0

    def test_cache_entry_with_hit_count(self):
        """Test cache entry with custom hit count."""
        entry = CacheEntry(
            value="test",
            confidence=90.0,
            timestamp=datetime.now(),
            input_hash="xyz",
            source="llm",
            hit_count=5,
        )

        assert entry.hit_count == 5


@pytest.mark.unit
@pytest.mark.service
class TestMetadataCacheInitialization:
    """Tests for MetadataCache initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        cache = MetadataCache()

        assert cache._ttl == timedelta(seconds=3600)
        assert cache._min_confidence == 70.0
        assert cache._max_entries == 1000
        assert len(cache._cache) == 0

    def test_init_with_custom_parameters(self):
        """Test initialization with custom parameters."""
        cache = MetadataCache(
            ttl_seconds=7200,
            min_confidence=80.0,
            max_entries=500,
        )

        assert cache._ttl == timedelta(seconds=7200)
        assert cache._min_confidence == 80.0
        assert cache._max_entries == 500

    def test_init_creates_empty_stats(self):
        """Test initialization creates empty statistics."""
        cache = MetadataCache()

        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["evictions"] == 0
        assert stats["inserts"] == 0


@pytest.mark.unit
@pytest.mark.service
class TestGenerateCacheKey:
    """Tests for _generate_cache_key method."""

    def test_generate_cache_key_consistent(self):
        """Test cache key generation is consistent."""
        cache = MetadataCache()

        context = {"filename": "test.nwb", "format": "SpikeGLX"}

        key1 = cache._generate_cache_key("species", context)
        key2 = cache._generate_cache_key("species", context)

        assert key1 == key2

    def test_generate_cache_key_different_fields(self):
        """Test different field names generate different keys."""
        cache = MetadataCache()

        context = {"filename": "test.nwb"}

        key1 = cache._generate_cache_key("species", context)
        key2 = cache._generate_cache_key("institution", context)

        assert key1 != key2

    def test_generate_cache_key_different_contexts(self):
        """Test different contexts generate different keys."""
        cache = MetadataCache()

        key1 = cache._generate_cache_key("species", {"filename": "test1.nwb"})
        key2 = cache._generate_cache_key("species", {"filename": "test2.nwb"})

        assert key1 != key2

    def test_generate_cache_key_order_independent(self):
        """Test cache key is independent of dict key order."""
        cache = MetadataCache()

        context1 = {"a": 1, "b": 2, "c": 3}
        context2 = {"c": 3, "a": 1, "b": 2}

        key1 = cache._generate_cache_key("test", context1)
        key2 = cache._generate_cache_key("test", context2)

        assert key1 == key2

    def test_generate_cache_key_format(self):
        """Test cache key has expected format."""
        cache = MetadataCache()

        key = cache._generate_cache_key("species", {"test": "value"})

        assert "species:" in key
        assert len(key) > len("species:")


@pytest.mark.unit
@pytest.mark.service
class TestGetMethod:
    """Tests for get method."""

    @pytest.mark.asyncio
    async def test_get_cache_miss(self):
        """Test get returns None on cache miss."""
        cache = MetadataCache()

        result = await cache.get("species", {"filename": "test.nwb"})

        assert result is None
        assert cache._stats["misses"] == 1
        assert cache._stats["hits"] == 0

    @pytest.mark.asyncio
    async def test_get_cache_hit(self):
        """Test get returns cached value on hit."""
        cache = MetadataCache()

        context = {"filename": "test.nwb"}

        # Set a value
        await cache.set("species", context, "Mus musculus", 85.0, "test")

        # Get the value
        result = await cache.get("species", context)

        assert result is not None
        assert result["value"] == "Mus musculus"
        assert result["confidence"] == 85.0
        assert result["source"] == "test"
        assert result["cached"] is True
        assert cache._stats["hits"] == 1

    @pytest.mark.asyncio
    async def test_get_expired_entry_removed(self):
        """Test get removes and returns None for expired entries."""
        cache = MetadataCache(ttl_seconds=1)

        context = {"filename": "test.nwb"}

        # Set a value
        await cache.set("species", context, "Mus musculus", 85.0)

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Get should return None and remove entry
        result = await cache.get("species", context)

        assert result is None
        assert cache._stats["misses"] == 1
        assert cache._stats["evictions"] == 1
        assert len(cache._cache) == 0

    @pytest.mark.asyncio
    async def test_get_increments_hit_count(self):
        """Test get increments hit count on cache entry."""
        cache = MetadataCache()

        context = {"filename": "test.nwb"}
        await cache.set("species", context, "Mus musculus", 85.0)

        # Get multiple times
        await cache.get("species", context)
        await cache.get("species", context)
        await cache.get("species", context)

        # Check hit count in cache entry
        key = cache._generate_cache_key("species", context)
        assert cache._cache[key].hit_count == 3

    @pytest.mark.asyncio
    async def test_get_returns_cache_age(self):
        """Test get returns cache age in seconds."""
        cache = MetadataCache()

        context = {"filename": "test.nwb"}
        await cache.set("species", context, "Mus musculus", 85.0)

        await asyncio.sleep(0.1)

        result = await cache.get("species", context)

        assert "cache_age_seconds" in result
        assert result["cache_age_seconds"] > 0


@pytest.mark.unit
@pytest.mark.service
class TestSetMethod:
    """Tests for set method."""

    @pytest.mark.asyncio
    async def test_set_stores_value(self):
        """Test set stores value in cache."""
        cache = MetadataCache()

        success = await cache.set("species", {"test": "value"}, "Mus musculus", 85.0, "llm")

        assert success is True
        assert len(cache._cache) == 1
        assert cache._stats["inserts"] == 1

    @pytest.mark.asyncio
    async def test_set_rejects_low_confidence(self):
        """Test set rejects low confidence values."""
        cache = MetadataCache(min_confidence=75.0)

        success = await cache.set("species", {"test": "value"}, "Mus musculus", 60.0)

        assert success is False
        assert len(cache._cache) == 0
        assert cache._stats["inserts"] == 0

    @pytest.mark.asyncio
    async def test_set_accepts_high_confidence(self):
        """Test set accepts high confidence values."""
        cache = MetadataCache(min_confidence=75.0)

        success = await cache.set("species", {"test": "value"}, "Mus musculus", 85.0)

        assert success is True

    @pytest.mark.asyncio
    async def test_set_evicts_oldest_when_full(self):
        """Test set evicts oldest entry when cache is full."""
        cache = MetadataCache(max_entries=2)

        # Fill cache
        await cache.set("field1", {"a": 1}, "value1", 85.0)
        await asyncio.sleep(0.01)  # Ensure different timestamps
        await cache.set("field2", {"b": 2}, "value2", 85.0)

        assert len(cache._cache) == 2

        # Add third entry - should evict oldest
        await cache.set("field3", {"c": 3}, "value3", 85.0)

        assert len(cache._cache) == 2
        assert cache._stats["evictions"] == 1

        # field1 should be evicted
        result = await cache.get("field1", {"a": 1})
        assert result is None

    @pytest.mark.asyncio
    async def test_set_updates_existing_entry(self):
        """Test set updates existing entry instead of evicting."""
        cache = MetadataCache(max_entries=2)

        context = {"test": "value"}

        # Set initial value
        await cache.set("species", context, "Mus musculus", 85.0)

        # Update same key
        await cache.set("species", context, "Rattus norvegicus", 90.0)

        # Should only have one entry
        assert len(cache._cache) == 1

        # Should have new value
        result = await cache.get("species", context)
        assert result["value"] == "Rattus norvegicus"
        assert result["confidence"] == 90.0


@pytest.mark.unit
@pytest.mark.service
class TestInvalidateMethod:
    """Tests for invalidate method."""

    @pytest.mark.asyncio
    async def test_invalidate_all(self):
        """Test invalidating entire cache."""
        cache = MetadataCache()

        # Add multiple entries
        await cache.set("species", {"a": 1}, "value1", 85.0)
        await cache.set("institution", {"b": 2}, "value2", 85.0)
        await cache.set("experimenter", {"c": 3}, "value3", 85.0)

        assert len(cache._cache) == 3

        # Invalidate all
        count = await cache.invalidate()

        assert count == 3
        assert len(cache._cache) == 0

    @pytest.mark.asyncio
    async def test_invalidate_specific_field(self):
        """Test invalidating specific field entries."""
        cache = MetadataCache()

        # Add entries for different fields
        await cache.set("species", {"a": 1}, "value1", 85.0)
        await cache.set("species", {"b": 2}, "value2", 85.0)
        await cache.set("institution", {"c": 3}, "value3", 85.0)

        # Invalidate only species entries
        count = await cache.invalidate("species")

        assert count == 2
        assert len(cache._cache) == 1

        # Institution entry should remain
        result = await cache.get("institution", {"c": 3})
        assert result is not None

    @pytest.mark.asyncio
    async def test_invalidate_nonexistent_field(self):
        """Test invalidating non-existent field returns 0."""
        cache = MetadataCache()

        await cache.set("species", {"a": 1}, "value1", 85.0)

        count = await cache.invalidate("nonexistent_field")

        assert count == 0
        assert len(cache._cache) == 1


@pytest.mark.unit
@pytest.mark.service
class TestGetStats:
    """Tests for get_stats method."""

    def test_get_stats_initial(self):
        """Test getting stats on empty cache."""
        cache = MetadataCache()

        stats = cache.get_stats()

        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["evictions"] == 0
        assert stats["inserts"] == 0
        assert stats["cache_size"] == 0
        assert stats["hit_rate_percent"] == 0.0
        assert stats["total_requests"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_after_operations(self):
        """Test stats tracking after operations."""
        cache = MetadataCache()

        context = {"test": "value"}

        # Miss
        await cache.get("species", context)

        # Insert
        await cache.set("species", context, "Mus musculus", 85.0)

        # Hits
        await cache.get("species", context)
        await cache.get("species", context)

        stats = cache.get_stats()

        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["inserts"] == 1
        assert stats["cache_size"] == 1
        assert stats["total_requests"] == 3
        assert stats["hit_rate_percent"] == pytest.approx(66.67, rel=0.01)


@pytest.mark.unit
@pytest.mark.service
class TestCleanupExpired:
    """Tests for cleanup_expired method."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_removes_old_entries(self):
        """Test cleanup removes expired entries."""
        cache = MetadataCache(ttl_seconds=1)

        # Add entries
        await cache.set("field1", {"a": 1}, "value1", 85.0)
        await cache.set("field2", {"b": 2}, "value2", 85.0)

        # Wait for expiration
        await asyncio.sleep(1.1)

        # Cleanup
        removed = await cache.cleanup_expired()

        assert removed == 2
        assert len(cache._cache) == 0

    @pytest.mark.asyncio
    async def test_cleanup_expired_keeps_fresh_entries(self):
        """Test cleanup keeps non-expired entries."""
        cache = MetadataCache(ttl_seconds=10)

        await cache.set("species", {"test": "value"}, "Mus musculus", 85.0)

        removed = await cache.cleanup_expired()

        assert removed == 0
        assert len(cache._cache) == 1

    @pytest.mark.asyncio
    async def test_cleanup_expired_mixed_entries(self):
        """Test cleanup with mix of expired and fresh entries."""
        cache = MetadataCache(ttl_seconds=1)

        # Add old entry
        await cache.set("field1", {"a": 1}, "value1", 85.0)

        # Wait
        await asyncio.sleep(1.1)

        # Add fresh entry
        await cache.set("field2", {"b": 2}, "value2", 85.0)

        # Cleanup should remove only expired
        removed = await cache.cleanup_expired()

        assert removed == 1
        assert len(cache._cache) == 1


@pytest.mark.unit
@pytest.mark.service
class TestGlobalCacheInstance:
    """Tests for global cache singleton."""

    def test_get_metadata_cache_creates_instance(self):
        """Test get_metadata_cache creates cache instance."""
        cache = get_metadata_cache()

        assert isinstance(cache, MetadataCache)

    def test_get_metadata_cache_returns_same_instance(self):
        """Test get_metadata_cache returns singleton."""
        cache1 = get_metadata_cache()
        cache2 = get_metadata_cache()

        assert cache1 is cache2

    def test_global_cache_has_default_settings(self):
        """Test global cache has expected default settings."""
        cache = get_metadata_cache()

        assert cache._ttl == timedelta(seconds=3600)
        assert cache._min_confidence == 70.0
        assert cache._max_entries == 1000


@pytest.mark.unit
@pytest.mark.service
class TestMetadataCacheIntegration:
    """Integration tests for complete cache workflows."""

    @pytest.mark.asyncio
    async def test_complete_cache_workflow(self):
        """Test complete cache workflow: set, get, invalidate."""
        cache = MetadataCache()

        context = {"filename": "test.nwb", "format": "SpikeGLX"}

        # Step 1: Cache miss
        result = await cache.get("species", context)
        assert result is None

        # Step 2: Set value
        success = await cache.set("species", context, "Mus musculus", 85.0, "llm_inference")
        assert success is True

        # Step 3: Cache hit
        result = await cache.get("species", context)
        assert result is not None
        assert result["value"] == "Mus musculus"

        # Step 4: Update value
        await cache.set("species", context, "Rattus norvegicus", 90.0, "llm_inference")

        # Step 5: Get updated value
        result = await cache.get("species", context)
        assert result["value"] == "Rattus norvegicus"

        # Step 6: Invalidate
        await cache.invalidate("species")

        # Step 7: Cache miss after invalidation
        result = await cache.get("species", context)
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_with_multiple_fields(self):
        """Test cache handles multiple fields independently."""
        cache = MetadataCache()

        # Cache different fields
        await cache.set("species", {"file": "test.nwb"}, "Mus musculus", 85.0)
        await cache.set("institution", {"file": "test.nwb"}, "MIT", 90.0)
        await cache.set("experimenter", {"file": "test.nwb"}, ["Smith, Jane"], 95.0)

        # All should be retrievable
        species = await cache.get("species", {"file": "test.nwb"})
        institution = await cache.get("institution", {"file": "test.nwb"})
        experimenter = await cache.get("experimenter", {"file": "test.nwb"})

        assert species["value"] == "Mus musculus"
        assert institution["value"] == "MIT"
        assert experimenter["value"] == ["Smith, Jane"]

    @pytest.mark.asyncio
    async def test_cache_respects_confidence_threshold(self):
        """Test cache respects minimum confidence threshold."""
        cache = MetadataCache(min_confidence=80.0)

        context = {"test": "value"}

        # Low confidence - should not cache
        success1 = await cache.set("field1", context, "value1", 75.0)
        assert success1 is False

        # High confidence - should cache
        success2 = await cache.set("field2", context, "value2", 85.0)
        assert success2 is True

        assert len(cache._cache) == 1

    @pytest.mark.asyncio
    async def test_cache_performance_stats(self):
        """Test cache tracks performance statistics."""
        cache = MetadataCache()

        context = {"test": "value"}

        # Generate cache activity
        await cache.get("species", context)  # miss
        await cache.set("species", context, "Mus musculus", 85.0)  # insert
        await cache.get("species", context)  # hit
        await cache.get("species", context)  # hit
        await cache.get("institution", context)  # miss

        stats = cache.get_stats()

        assert stats["hits"] == 2
        assert stats["misses"] == 2
        assert stats["inserts"] == 1
        assert stats["total_requests"] == 4
        assert stats["hit_rate_percent"] == 50.0
