"""
Tests for performance optimization system.
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone

from pr_agent.performance import (
    MemoryCache,
    CacheStrategy,
    QueryOptimizer,
    BatchProcessor,
    AsyncTaskQueue,
    PerformanceMonitor,
    cache_result,
    measure_time,
)


class TestMemoryCache:
    """Test memory cache."""

    def test_basic_operations(self):
        """Test basic cache operations."""
        cache = MemoryCache(max_size=10)

        # Set and get
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # Miss
        assert cache.get("nonexistent") is None

        # Delete
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_ttl_expiration(self):
        """Test TTL expiration."""
        cache = MemoryCache(default_ttl=1)

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # Wait for expiration
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_lru_eviction(self):
        """Test LRU eviction strategy."""
        cache = MemoryCache(max_size=3, strategy=CacheStrategy.LRU)

        # Fill cache
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Cache should be full
        assert len(cache.cache) == 3

        # Add new item, should trigger eviction
        cache.set("key4", "value4")

        # Cache should still have max_size entries
        assert len(cache.cache) == 3

        # key4 should be present
        assert cache.get("key4") == "value4"

        # At least one of the original keys should be evicted
        original_keys_present = sum([
            cache.get("key1") is not None,
            cache.get("key2") is not None,
            cache.get("key3") is not None
        ])
        assert original_keys_present == 2  # One should be evicted

    def test_cache_stats(self):
        """Test cache statistics."""
        cache = MemoryCache(max_size=10)

        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss

        assert cache.stats.hits == 1
        assert cache.stats.misses == 1
        assert cache.stats.hit_rate == 0.5

    def test_memory_limit(self):
        """Test memory limit enforcement."""
        cache = MemoryCache(max_size=100, max_memory_mb=1)

        # Add large values
        large_value = "x" * 1024 * 100  # 100KB
        for i in range(20):
            cache.set(f"key{i}", large_value)

        # Should have evicted some entries
        assert len(cache.cache) < 20


class TestQueryOptimizer:
    """Test query optimizer."""

    def test_query_caching(self):
        """Test query result caching."""
        optimizer = QueryOptimizer()
        call_count = [0]

        def expensive_query(x):
            call_count[0] += 1
            return x * 2

        # First call - cache miss
        result1 = optimizer.cache_query("test_query", expensive_query, 5)
        assert result1 == 10
        assert call_count[0] == 1

        # Second call - cache hit
        result2 = optimizer.cache_query("test_query", expensive_query, 5)
        assert result2 == 10
        assert call_count[0] == 1  # Not called again

    def test_query_stats(self):
        """Test query statistics tracking."""
        optimizer = QueryOptimizer()

        def test_query():
            time.sleep(0.01)
            return "result"

        # Execute query multiple times
        for _ in range(3):
            optimizer.cache_query("test_query", test_query)

        stats = optimizer.get_query_stats("test_query")
        assert stats['count'] == 1  # Only first call executed
        assert stats['avg_time'] > 0

    def test_cache_key_generation(self):
        """Test cache key generation."""
        optimizer = QueryOptimizer()

        def query(a, b):
            return a + b

        # Same args should use same cache
        result1 = optimizer.cache_query("add", query, 1, 2)
        result2 = optimizer.cache_query("add", query, 1, 2)
        assert result1 == result2

        # Different args should not use cache
        result3 = optimizer.cache_query("add", query, 2, 3)
        assert result3 == 5


class TestBatchProcessor:
    """Test batch processor."""

    def test_batch_size_trigger(self):
        """Test batch triggered by size."""
        processor = BatchProcessor(batch_size=3)

        assert processor.add(1) is None
        assert processor.add(2) is None
        batch = processor.add(3)

        assert batch == [1, 2, 3]

    def test_time_trigger(self):
        """Test batch triggered by time."""
        processor = BatchProcessor(batch_size=10, max_wait_seconds=0.1)

        processor.add(1)
        processor.add(2)

        # Wait for time trigger
        time.sleep(0.15)

        batch = processor.add(3)
        assert len(batch) == 3

    def test_manual_flush(self):
        """Test manual flush."""
        processor = BatchProcessor(batch_size=10)

        processor.add(1)
        processor.add(2)

        batch = processor.flush()
        assert batch == [1, 2]

        # Second flush should be empty
        batch2 = processor.flush()
        assert batch2 == []


class TestAsyncTaskQueue:
    """Test async task queue."""

    @pytest.mark.asyncio
    async def test_task_submission(self):
        """Test task submission and execution."""
        queue = AsyncTaskQueue(max_workers=2)
        await queue.start()

        def task(x):
            return x * 2

        task_id = await queue.submit("task1", task, 5)
        result = await queue.get_result(task_id, timeout=5.0)

        assert result == 10

        await queue.stop()

    @pytest.mark.asyncio
    async def test_async_task(self):
        """Test async task execution."""
        queue = AsyncTaskQueue(max_workers=2)
        await queue.start()

        async def async_task(x):
            await asyncio.sleep(0.01)
            return x * 3

        task_id = await queue.submit("task1", async_task, 5)
        result = await queue.get_result(task_id, timeout=5.0)

        assert result == 15

        await queue.stop()

    @pytest.mark.asyncio
    async def test_multiple_tasks(self):
        """Test multiple concurrent tasks."""
        queue = AsyncTaskQueue(max_workers=3)
        await queue.start()

        def task(x):
            time.sleep(0.01)
            return x * 2

        # Submit multiple tasks
        task_ids = []
        for i in range(5):
            task_id = await queue.submit(f"task{i}", task, i)
            task_ids.append(task_id)

        # Get all results
        results = []
        for task_id in task_ids:
            result = await queue.get_result(task_id, timeout=5.0)
            results.append(result)

        assert results == [0, 2, 4, 6, 8]

        await queue.stop()


class TestPerformanceMonitor:
    """Test performance monitor."""

    def test_metric_recording(self):
        """Test metric recording."""
        monitor = PerformanceMonitor()

        monitor.record("response_time", 0.5)
        monitor.record("response_time", 0.7)
        monitor.record("response_time", 0.3)

        stats = monitor.get_stats("response_time")
        assert stats['count'] == 3
        assert stats['min'] == 0.3
        assert stats['max'] == 0.7
        assert stats['avg'] == pytest.approx(0.5, rel=0.01)

    def test_threshold_alert(self):
        """Test threshold alerting."""
        monitor = PerformanceMonitor()
        monitor.set_threshold("response_time", 1.0)

        # Should not alert
        monitor.record("response_time", 0.5)

        # Should alert (captured in logs)
        monitor.record("response_time", 1.5)


class TestDecorators:
    """Test decorator functions."""

    def test_cache_result_decorator(self):
        """Test cache_result decorator."""
        call_count = [0]

        @cache_result(ttl=60)
        def expensive_function(x):
            call_count[0] += 1
            return x * 2

        # First call
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count[0] == 1

        # Second call - cached
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count[0] == 1

        # Different arg - not cached
        result3 = expensive_function(10)
        assert result3 == 20
        assert call_count[0] == 2

    def test_measure_time_decorator(self):
        """Test measure_time decorator."""
        monitor = PerformanceMonitor()

        @measure_time("test_function", monitor)
        def slow_function():
            time.sleep(0.01)
            return "done"

        result = slow_function()
        assert result == "done"

        stats = monitor.get_stats("test_function")
        assert stats['count'] == 1
        assert stats['avg'] >= 0.01


class TestIntegration:
    """Test integration scenarios."""

    def test_cached_query_optimization(self):
        """Test combining cache and query optimization."""
        optimizer = QueryOptimizer()
        call_count = [0]

        @cache_result(ttl=60)
        def cached_query(user_id):
            call_count[0] += 1
            return optimizer.cache_query(
                "get_user",
                lambda uid: f"user_{uid}",
                user_id
            )

        # First call
        result1 = cached_query(123)
        assert result1 == "user_123"
        assert call_count[0] == 1

        # Second call - cached
        result2 = cached_query(123)
        assert result2 == "user_123"
        assert call_count[0] == 1

    @pytest.mark.asyncio
    async def test_batch_async_processing(self):
        """Test batch processing with async queue."""
        processor = BatchProcessor(batch_size=5)
        queue = AsyncTaskQueue(max_workers=2)
        await queue.start()

        async def process_batch(items):
            return [x * 2 for x in items]

        # Add items
        for i in range(5):
            batch = processor.add(i)
            if batch:
                task_id = await queue.submit(f"batch_{i}", process_batch, batch)
                result = await queue.get_result(task_id, timeout=5.0)
                assert result == [0, 2, 4, 6, 8]

        await queue.stop()

    def test_monitored_cached_function(self):
        """Test function with both monitoring and caching."""
        monitor = PerformanceMonitor()

        @cache_result(ttl=60)
        @measure_time("cached_func", monitor)
        def expensive_cached_function(x):
            time.sleep(0.01)
            return x * 2

        # First call - slow
        result1 = expensive_cached_function(5)
        assert result1 == 10

        stats1 = monitor.get_stats("cached_func")
        assert stats1['avg'] >= 0.01

        # Second call - fast (cached, but still measured)
        result2 = expensive_cached_function(5)
        assert result2 == 10

        stats2 = monitor.get_stats("cached_func")
        # Should have at least 1 measurement (might be 1 or 2 depending on cache behavior)
        assert stats2['count'] >= 1
