"""
Unit tests for cache manager.
"""

import pytest
import time
from pr_agent.storage.cache import CacheManager, cached


class TestCacheManager:
    """Test CacheManager functionality."""

    @pytest.fixture
    def cache(self):
        """Create cache manager instance."""
        return CacheManager(namespace="test")

    def test_set_and_get(self, cache):
        """Test basic set and get operations."""
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_default(self, cache):
        """Test get with default value."""
        assert cache.get("nonexistent", "default") == "default"

    def test_ttl_expiry(self, cache):
        """Test TTL expiration."""
        cache.set("key1", "value1", ttl=1)
        assert cache.get("key1") == "value1"

        # Wait for expiry
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_delete(self, cache):
        """Test delete operation."""
        cache.set("key1", "value1")
        assert cache.exists("key1")

        cache.delete("key1")
        assert not cache.exists("key1")

    def test_exists(self, cache):
        """Test exists check."""
        assert not cache.exists("key1")

        cache.set("key1", "value1")
        assert cache.exists("key1")

    def test_clear_all(self, cache):
        """Test clearing all keys."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        count = cache.clear()
        assert count == 3
        assert not cache.exists("key1")
        assert not cache.exists("key2")

    def test_clear_pattern(self, cache):
        """Test clearing keys by pattern."""
        cache.set("user:1", "data1")
        cache.set("user:2", "data2")
        cache.set("repo:1", "data3")

        count = cache.clear("user:*")
        assert count == 2
        assert not cache.exists("user:1")
        assert cache.exists("repo:1")

    def test_complex_values(self, cache):
        """Test caching complex data types."""
        data = {
            "list": [1, 2, 3],
            "dict": {"a": 1, "b": 2},
            "nested": {"x": [1, 2], "y": {"z": 3}}
        }

        cache.set("complex", data)
        result = cache.get("complex")

        assert result == data
        assert result["list"] == [1, 2, 3]
        assert result["nested"]["y"]["z"] == 3

    def test_get_stats(self, cache):
        """Test cache statistics."""
        cache.set("key1", "value1")
        cache.get("key1")  # hit
        cache.get("key2")  # miss

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["sets"] == 1
        assert stats["hit_rate"] == 0.5

    def test_cache_key_for_pr(self, cache):
        """Test PR cache key generation."""
        key = cache.cache_key_for_pr("PROJ/repo", 123, "review")
        assert key == "pr:PROJ/repo:123:review"

    def test_cache_key_for_file(self, cache):
        """Test file cache key generation."""
        key = cache.cache_key_for_file("PROJ/repo", "src/main.py", "abc123")
        assert "file:PROJ/repo:abc123:" in key


class TestCachedDecorator:
    """Test cached decorator."""

    def test_cached_function(self):
        """Test function result caching."""
        call_count = 0

        @cached(ttl=60, key_prefix="test")
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call - executes function
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # Second call - uses cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Not incremented

        # Different argument - executes function
        result3 = expensive_function(10)
        assert result3 == 20
        assert call_count == 2

    def test_cached_with_kwargs(self):
        """Test caching with keyword arguments."""
        call_count = 0

        @cached(ttl=60, key_prefix="test")
        def function_with_kwargs(a, b=10):
            nonlocal call_count
            call_count += 1
            return a + b

        result1 = function_with_kwargs(5, b=10)
        assert result1 == 15
        assert call_count == 1

        result2 = function_with_kwargs(5, b=10)
        assert result2 == 15
        assert call_count == 1  # Cached

        result3 = function_with_kwargs(5, b=20)
        assert result3 == 25
        assert call_count == 2  # Different kwargs


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
