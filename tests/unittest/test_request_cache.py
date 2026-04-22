"""Tests for request cache."""

import time
from datetime import datetime, timedelta
import pytest

from pr_agent.cache import RequestCache, CachePolicy


class TestRequestCache:
    """Test request cache functionality."""

    def test_basic_cache_operations(self):
        """Test basic get/set operations."""
        cache = RequestCache(max_size=10)

        # Cache miss
        result = cache.get("gpt-4", "Hello world")
        assert result is None

        # Cache set
        cache.set("gpt-4", "Hello world", "Hi there!")

        # Cache hit
        result = cache.get("gpt-4", "Hello world")
        assert result == "Hi there!"

    def test_cache_key_generation(self):
        """Test cache key generation is consistent."""
        cache = RequestCache()

        # Same inputs should generate same key
        cache.set("gpt-4", "test", "response1")
        result = cache.get("gpt-4", "test")
        assert result == "response1"

        # Different prompts should generate different keys
        cache.set("gpt-4", "test2", "response2")
        result = cache.get("gpt-4", "test2")
        assert result == "response2"

        # Original should still be cached
        result = cache.get("gpt-4", "test")
        assert result == "response1"

    def test_cache_with_params(self):
        """Test caching with additional parameters."""
        cache = RequestCache()

        # Cache with params
        cache.set("gpt-4", "test", "response1", params={"temperature": 0.7})
        result = cache.get("gpt-4", "test", params={"temperature": 0.7})
        assert result == "response1"

        # Different params should be different cache entry
        result = cache.get("gpt-4", "test", params={"temperature": 0.9})
        assert result is None

        # Cache second variant
        cache.set("gpt-4", "test", "response2", params={"temperature": 0.9})
        result = cache.get("gpt-4", "test", params={"temperature": 0.9})
        assert result == "response2"

    def test_ttl_expiration(self):
        """Test TTL-based expiration."""
        cache = RequestCache(default_ttl=1)  # 1 second TTL

        cache.set("gpt-4", "test", "response")

        # Should be cached immediately
        result = cache.get("gpt-4", "test")
        assert result == "response"

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired
        result = cache.get("gpt-4", "test")
        assert result is None

    def test_lru_eviction(self):
        """Test LRU eviction policy."""
        cache = RequestCache(max_size=3, policy=CachePolicy.LRU)

        # Fill cache
        cache.set("gpt-4", "prompt1", "response1")
        cache.set("gpt-4", "prompt2", "response2")
        cache.set("gpt-4", "prompt3", "response3")

        # All should be cached
        assert cache.get("gpt-4", "prompt1") == "response1"
        assert cache.get("gpt-4", "prompt2") == "response2"
        assert cache.get("gpt-4", "prompt3") == "response3"

        # Add one more, should evict oldest (prompt1)
        cache.set("gpt-4", "prompt4", "response4")

        # prompt1 should be evicted
        assert cache.get("gpt-4", "prompt1") is None
        assert cache.get("gpt-4", "prompt2") == "response2"
        assert cache.get("gpt-4", "prompt3") == "response3"
        assert cache.get("gpt-4", "prompt4") == "response4"

    def test_lfu_eviction(self):
        """Test LFU eviction policy."""
        cache = RequestCache(max_size=3, policy=CachePolicy.LFU)

        # Fill cache
        cache.set("gpt-4", "prompt1", "response1")
        cache.set("gpt-4", "prompt2", "response2")
        cache.set("gpt-4", "prompt3", "response3")

        # Access prompt1 and prompt3 multiple times
        for _ in range(5):
            cache.get("gpt-4", "prompt1")
            cache.get("gpt-4", "prompt3")

        # Access prompt2 once
        cache.get("gpt-4", "prompt2")

        # Add one more, should evict least frequently used (prompt2)
        cache.set("gpt-4", "prompt4", "response4")

        # prompt2 should be evicted
        assert cache.get("gpt-4", "prompt1") == "response1"
        assert cache.get("gpt-4", "prompt2") is None
        assert cache.get("gpt-4", "prompt3") == "response3"
        assert cache.get("gpt-4", "prompt4") == "response4"

    def test_cache_statistics(self):
        """Test cache statistics tracking."""
        cache = RequestCache(enable_stats=True)

        # Initial stats
        stats = cache.get_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["total_requests"] == 0

        # Cache miss
        cache.get("gpt-4", "test")
        stats = cache.get_stats()
        assert stats["misses"] == 1
        assert stats["total_requests"] == 1

        # Cache set and hit
        cache.set("gpt-4", "test", "response")
        cache.get("gpt-4", "test")
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["total_requests"] == 2
        assert stats["hit_rate"] == 50.0

    def test_cache_invalidation(self):
        """Test cache invalidation."""
        cache = RequestCache()

        # Add entries
        cache.set("gpt-4", "test1", "response1")
        cache.set("gpt-4", "test2", "response2")
        cache.set("claude", "test3", "response3")

        # Verify all cached
        assert cache.get("gpt-4", "test1") == "response1"
        assert cache.get("gpt-4", "test2") == "response2"
        assert cache.get("claude", "test3") == "response3"

        # Clear all
        cache.invalidate()

        # All should be gone
        assert cache.get("gpt-4", "test1") is None
        assert cache.get("gpt-4", "test2") is None
        assert cache.get("claude", "test3") is None

    def test_cache_warming(self):
        """Test cache warming."""
        cache = RequestCache()

        # Warm cache
        entries = [
            ("gpt-4", "prompt1", "response1", None),
            ("gpt-4", "prompt2", "response2", {"temperature": 0.7}),
            ("claude", "prompt3", "response3", None),
        ]
        cache.warm_cache(entries)

        # All should be cached
        assert cache.get("gpt-4", "prompt1") == "response1"
        assert cache.get("gpt-4", "prompt2", {"temperature": 0.7}) == "response2"
        assert cache.get("claude", "prompt3") == "response3"

    def test_cleanup_expired(self):
        """Test cleanup of expired entries."""
        cache = RequestCache(default_ttl=1)

        # Add entries
        cache.set("gpt-4", "test1", "response1")
        cache.set("gpt-4", "test2", "response2")

        # Wait for expiration
        time.sleep(1.1)

        # Add fresh entry
        cache.set("gpt-4", "test3", "response3")

        # Cleanup
        cache.cleanup_expired()

        # Expired should be gone, fresh should remain
        assert cache.get("gpt-4", "test1") is None
        assert cache.get("gpt-4", "test2") is None
        assert cache.get("gpt-4", "test3") == "response3"

    def test_cache_metadata(self):
        """Test cache entry metadata."""
        cache = RequestCache()

        # Set with metadata
        cache.set(
            "gpt-4",
            "test",
            "response",
            metadata={"model_id": "gpt-4", "version": "2024-01"}
        )

        # Get and verify
        result = cache.get("gpt-4", "test")
        assert result == "response"

    def test_param_normalization(self):
        """Test parameter normalization for consistent keys."""
        cache = RequestCache()

        # Different param orders should generate same key
        cache.set("gpt-4", "test", "response", params={"a": 1, "b": 2})
        result = cache.get("gpt-4", "test", params={"b": 2, "a": 1})
        assert result == "response"

        # Complex params should be normalized
        cache.set("gpt-4", "test2", "response2", params={"list": [1, 2, 3]})
        result = cache.get("gpt-4", "test2", params={"list": [1, 2, 3]})
        assert result == "response2"

    def test_whitespace_normalization(self):
        """Test prompt whitespace normalization."""
        cache = RequestCache()

        # Leading/trailing whitespace should be normalized
        cache.set("gpt-4", "  test  ", "response")
        result = cache.get("gpt-4", "test")
        assert result == "response"

        # Should work in reverse too
        cache.set("gpt-4", "test2", "response2")
        result = cache.get("gpt-4", "  test2  ")
        assert result == "response2"
