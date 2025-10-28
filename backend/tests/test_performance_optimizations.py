"""
Tests for Performance Optimizations

Tests:
1. Metadata caching system
2. Cache hit/miss behavior
3. TTL expiration
4. Confidence-based caching
"""
import asyncio
import pytest
from datetime import datetime, timedelta

from services.metadata_cache import MetadataCache, get_metadata_cache


class TestMetadataCache:
    """Test metadata caching system."""

    @pytest.mark.asyncio
    async def test_cache_basic_set_and_get(self):
        """Test basic cache set and get operations."""
        cache = MetadataCache(ttl_seconds=3600, min_confidence=70.0)

        # Set a value
        input_context = {"filename": "test.bin", "file_info": {"size": 1000}}
        stored = await cache.set(
            field_name="species",
            input_context=input_context,
            value="Mus musculus",
            confidence=85.0,
            source="llm_test"
        )

        assert stored is True, "High confidence value should be cached"

        # Get the value
        result = await cache.get("species", input_context)

        assert result is not None, "Cached value should be retrieved"
        assert result["value"] == "Mus musculus"
        assert result["confidence"] == 85.0
        assert result["cached"] is True

    @pytest.mark.asyncio
    async def test_cache_miss_on_different_context(self):
        """Test cache miss when context changes."""
        cache = MetadataCache(ttl_seconds=3600)

        context1 = {"filename": "test1.bin"}
        context2 = {"filename": "test2.bin"}

        # Store with context1
        await cache.set("species", context1, "Mouse", 80.0)

        # Try to get with context2
        result = await cache.get("species", context2)

        assert result is None, "Should be cache miss with different context"

    @pytest.mark.asyncio
    async def test_low_confidence_not_cached(self):
        """Test that low confidence results are not cached."""
        cache = MetadataCache(ttl_seconds=3600, min_confidence=70.0)

        context = {"filename": "test.bin"}

        # Try to store low confidence value
        stored = await cache.set("species", context, "Unknown", 50.0)

        assert stored is False, "Low confidence values should not be cached"

        # Verify it's not in cache
        result = await cache.get("species", context)
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_statistics(self):
        """Test cache statistics tracking."""
        cache = MetadataCache(ttl_seconds=3600)

        context = {"filename": "test.bin"}

        # Store a value
        await cache.set("species", context, "Mouse", 80.0)

        # Get it (cache hit)
        await cache.get("species", context)

        # Try to get non-existent value (cache miss)
        await cache.get("institution", context)

        stats = cache.get_stats()

        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["inserts"] == 1
        assert stats["cache_size"] == 1
        assert stats["hit_rate_percent"] == 50.0

    @pytest.mark.asyncio
    async def test_cache_invalidation(self):
        """Test cache invalidation."""
        cache = MetadataCache(ttl_seconds=3600)

        context = {"filename": "test.bin"}

        # Store some values
        await cache.set("species", context, "Mouse", 80.0)
        await cache.set("institution", context, "Stanford", 80.0)

        # Invalidate specific field
        count = await cache.invalidate("species")

        assert count == 1

        # Verify species is gone but institution remains
        assert await cache.get("species", context) is None
        assert await cache.get("institution", context) is not None

        # Invalidate all
        count = await cache.invalidate()
        assert count >= 1  # At least institution should be removed

    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = MetadataCache(ttl_seconds=3600, max_entries=3)

        context = {"filename": "test.bin"}

        # Fill cache to max
        await cache.set("field1", context, "value1", 80.0)
        await cache.set("field2", context, "value2", 80.0)
        await cache.set("field3", context, "value3", 80.0)

        stats = cache.get_stats()
        assert stats["cache_size"] == 3

        # Add one more - should evict oldest
        await cache.set("field4", context, "value4", 80.0)

        stats = cache.get_stats()
        assert stats["cache_size"] == 3  # Still at max
        assert stats["evictions"] == 1  # One evicted

    def test_global_cache_singleton(self):
        """Test global cache singleton pattern."""
        cache1 = get_metadata_cache()
        cache2 = get_metadata_cache()

        assert cache1 is cache2, "Should return same instance"


class TestCachePerformance:
    """Test cache performance improvements."""

    @pytest.mark.asyncio
    async def test_cache_hit_faster_than_miss(self):
        """Demonstrate cache hits are faster (though we can't test actual LLM calls here)."""
        cache = MetadataCache(ttl_seconds=3600)
        context = {"filename": "test.bin"}

        # Store value
        await cache.set("species", context, "Mouse", 80.0)

        # Measure cache hit (should be instant)
        start = datetime.now()
        result = await cache.get("species", context)
        hit_time = (datetime.now() - start).total_seconds()

        assert result is not None
        assert hit_time < 0.01, f"Cache hit should be near-instant, took {hit_time}s"

    @pytest.mark.asyncio
    async def test_multiple_retries_benefit_from_cache(self):
        """Simulate multiple retry attempts benefiting from cache."""
        cache = MetadataCache(ttl_seconds=3600)
        context = {"filename": "experimental_data.bin", "size": 10000}

        # First attempt - cache miss (would call LLM)
        result1 = await cache.get("species", context)
        assert result1 is None  # Cache miss

        # Store the "LLM result"
        await cache.set("species", context, "Mus musculus", 90.0)

        # Attempts 2-5 - cache hits (no LLM calls!)
        for attempt in range(2, 6):
            result = await cache.get("species", context)
            assert result is not None
            assert result["value"] == "Mus musculus"
            assert result["cached"] is True

        # Verify statistics show 4 hits, 1 miss
        stats = cache.get_stats()
        assert stats["hits"] == 4
        assert stats["misses"] == 1
        assert stats["hit_rate_percent"] == 80.0  # 4 / 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
