"""
Performance Optimization System for Code Review Platform.

Provides caching, query optimization, batch processing, and async operations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from functools import wraps
import asyncio
import hashlib
import json
import time
from pathlib import Path


class CacheStrategy(Enum):
    """Cache strategy types."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live
    FIFO = "fifo"  # First In First Out


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    size_bytes: int = 0

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl_seconds is None:
            return False
        age = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return age > self.ttl_seconds


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_size_bytes: int = 0
    entry_count: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class MemoryCache:
    """In-memory cache with multiple eviction strategies."""

    def __init__(
        self,
        max_size: int = 1000,
        max_memory_mb: int = 100,
        strategy: CacheStrategy = CacheStrategy.LRU,
        default_ttl: Optional[int] = None
    ):
        """Initialize cache."""
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.strategy = strategy
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.stats = CacheStats()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if key not in self.cache:
            self.stats.misses += 1
            return None

        entry = self.cache[key]

        # Check expiration
        if entry.is_expired():
            self.delete(key)
            self.stats.misses += 1
            return None

        # Update access metadata
        entry.last_accessed = datetime.now(timezone.utc)
        entry.access_count += 1
        self.stats.hits += 1

        return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        # Calculate size
        size = self._estimate_size(value)

        # Check if we need to evict
        while (
            len(self.cache) >= self.max_size or
            self.stats.total_size_bytes + size > self.max_memory_bytes
        ):
            if not self._evict_one():
                return False  # Cannot evict

        # Create entry
        now = datetime.now(timezone.utc)
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=now,
            last_accessed=now,
            ttl_seconds=ttl or self.default_ttl,
            size_bytes=size
        )

        # Remove old entry if exists
        if key in self.cache:
            self.stats.total_size_bytes -= self.cache[key].size_bytes

        # Add new entry
        self.cache[key] = entry
        self.stats.total_size_bytes += size
        self.stats.entry_count = len(self.cache)

        return True

    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        if key not in self.cache:
            return False

        entry = self.cache[key]
        self.stats.total_size_bytes -= entry.size_bytes
        del self.cache[key]
        self.stats.entry_count = len(self.cache)

        return True

    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        self.stats = CacheStats()

    def _evict_one(self) -> bool:
        """Evict one entry based on strategy."""
        if not self.cache:
            return False

        if self.strategy == CacheStrategy.LRU:
            # Evict least recently used
            key = min(self.cache.keys(), key=lambda k: self.cache[k].last_accessed)
        elif self.strategy == CacheStrategy.LFU:
            # Evict least frequently used
            key = min(self.cache.keys(), key=lambda k: self.cache[k].access_count)
        elif self.strategy == CacheStrategy.TTL:
            # Evict oldest
            key = min(self.cache.keys(), key=lambda k: self.cache[k].created_at)
        else:  # FIFO
            # Evict first inserted
            key = next(iter(self.cache))

        self.delete(key)
        self.stats.evictions += 1
        return True

    def _estimate_size(self, value: Any) -> int:
        """Estimate size of value in bytes."""
        try:
            return len(json.dumps(value, default=str).encode('utf-8'))
        except:
            return 1024  # Default estimate


class QueryOptimizer:
    """Optimize database queries and data access patterns."""

    def __init__(self):
        """Initialize optimizer."""
        self.query_cache = MemoryCache(max_size=500, default_ttl=300)
        self.query_stats: Dict[str, Dict[str, Any]] = {}

    def cache_query(
        self,
        query_key: str,
        query_func: Callable,
        *args,
        ttl: Optional[int] = None,
        **kwargs
    ) -> Any:
        """Cache query results."""
        # Generate cache key
        cache_key = self._generate_cache_key(query_key, args, kwargs)

        # Check cache
        cached = self.query_cache.get(cache_key)
        if cached is not None:
            return cached

        # Execute query
        start_time = time.time()
        result = query_func(*args, **kwargs)
        execution_time = time.time() - start_time

        # Update stats
        if query_key not in self.query_stats:
            self.query_stats[query_key] = {
                'count': 0,
                'total_time': 0.0,
                'avg_time': 0.0
            }

        stats = self.query_stats[query_key]
        stats['count'] += 1
        stats['total_time'] += execution_time
        stats['avg_time'] = stats['total_time'] / stats['count']

        # Cache result
        self.query_cache.set(cache_key, result, ttl=ttl)

        return result

    def _generate_cache_key(self, query_key: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key from query parameters."""
        key_data = {
            'query': query_key,
            'args': args,
            'kwargs': kwargs
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()

    def get_query_stats(self, query_key: Optional[str] = None) -> Dict[str, Any]:
        """Get query statistics."""
        if query_key:
            return self.query_stats.get(query_key, {})
        return self.query_stats


class BatchProcessor:
    """Process items in batches for better performance."""

    def __init__(self, batch_size: int = 100, max_wait_seconds: float = 1.0):
        """Initialize batch processor."""
        self.batch_size = batch_size
        self.max_wait_seconds = max_wait_seconds
        self.pending_items: List[Any] = []
        self.last_flush = time.time()

    def add(self, item: Any) -> Optional[List[Any]]:
        """Add item to batch. Returns processed batch if ready."""
        self.pending_items.append(item)

        # Check if batch is ready
        if self._should_flush():
            return self.flush()

        return None

    def flush(self) -> List[Any]:
        """Flush pending items."""
        if not self.pending_items:
            return []

        items = self.pending_items.copy()
        self.pending_items.clear()
        self.last_flush = time.time()

        return items

    def _should_flush(self) -> bool:
        """Check if batch should be flushed."""
        if len(self.pending_items) >= self.batch_size:
            return True

        time_since_last = time.time() - self.last_flush
        if time_since_last >= self.max_wait_seconds and self.pending_items:
            return True

        return False


class AsyncTaskQueue:
    """Asynchronous task queue for background processing."""

    def __init__(self, max_workers: int = 5):
        """Initialize task queue."""
        self.max_workers = max_workers
        self.queue: asyncio.Queue = asyncio.Queue()
        self.workers: List[asyncio.Task] = []
        self.results: Dict[str, Any] = {}
        self.running = False

    async def start(self):
        """Start worker tasks."""
        self.running = True
        self.workers = [
            asyncio.create_task(self._worker(i))
            for i in range(self.max_workers)
        ]

    async def stop(self):
        """Stop worker tasks."""
        self.running = False
        await self.queue.join()
        for worker in self.workers:
            worker.cancel()
        await asyncio.gather(*self.workers, return_exceptions=True)

    async def submit(self, task_id: str, func: Callable, *args, **kwargs) -> str:
        """Submit task for async execution."""
        await self.queue.put((task_id, func, args, kwargs))
        return task_id

    async def get_result(self, task_id: str, timeout: Optional[float] = None) -> Any:
        """Get task result."""
        start_time = time.time()

        while task_id not in self.results:
            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(f"Task {task_id} timed out")
            await asyncio.sleep(0.1)

        return self.results.pop(task_id)

    async def _worker(self, worker_id: int):
        """Worker coroutine."""
        while self.running:
            try:
                task_id, func, args, kwargs = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=1.0
                )

                # Execute task
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # Store result
                self.results[task_id] = result

                self.queue.task_done()

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                # Store error as result
                if 'task_id' in locals():
                    self.results[task_id] = e


def cache_result(ttl: Optional[int] = None, key_func: Optional[Callable] = None):
    """Decorator to cache function results."""
    cache = MemoryCache(default_ttl=ttl)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{args}:{kwargs}"

            # Check cache
            cached = cache.get(cache_key)
            if cached is not None:
                return cached

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            cache.set(cache_key, result)

            return result

        # Add cache management methods
        wrapper.cache = cache
        wrapper.clear_cache = cache.clear

        return wrapper

    return decorator


class PerformanceMonitor:
    """Monitor and track performance metrics."""

    def __init__(self):
        """Initialize monitor."""
        self.metrics: Dict[str, List[float]] = {}
        self.thresholds: Dict[str, float] = {}

    def record(self, metric_name: str, value: float):
        """Record a metric value."""
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []

        self.metrics[metric_name].append(value)

        # Check threshold
        if metric_name in self.thresholds:
            if value > self.thresholds[metric_name]:
                self._alert(metric_name, value)

    def set_threshold(self, metric_name: str, threshold: float):
        """Set alert threshold for metric."""
        self.thresholds[metric_name] = threshold

    def get_stats(self, metric_name: str) -> Dict[str, float]:
        """Get statistics for metric."""
        if metric_name not in self.metrics:
            return {}

        values = self.metrics[metric_name]
        return {
            'count': len(values),
            'min': min(values),
            'max': max(values),
            'avg': sum(values) / len(values),
            'latest': values[-1] if values else 0.0
        }

    def _alert(self, metric_name: str, value: float):
        """Handle threshold alert."""
        # In production, this would send notifications
        print(f"ALERT: {metric_name} = {value} exceeds threshold {self.thresholds[metric_name]}")


def measure_time(metric_name: str, monitor: Optional[PerformanceMonitor] = None):
    """Decorator to measure function execution time."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            if monitor:
                monitor.record(metric_name, execution_time)

            return result

        return wrapper

    return decorator


class ConnectionPool:
    """Connection pool for resource management."""

    def __init__(self, max_connections: int = 10, timeout: float = 30.0):
        """Initialize connection pool."""
        self.max_connections = max_connections
        self.timeout = timeout
        self.available: List[Any] = []
        self.in_use: List[Any] = []
        self.lock = asyncio.Lock()

    async def acquire(self) -> Any:
        """Acquire connection from pool."""
        async with self.lock:
            # Try to get available connection
            if self.available:
                conn = self.available.pop()
                self.in_use.append(conn)
                return conn

            # Create new connection if under limit
            if len(self.in_use) < self.max_connections:
                conn = await self._create_connection()
                self.in_use.append(conn)
                return conn

        # Wait for available connection
        start_time = time.time()
        while time.time() - start_time < self.timeout:
            await asyncio.sleep(0.1)
            async with self.lock:
                if self.available:
                    conn = self.available.pop()
                    self.in_use.append(conn)
                    return conn

        raise TimeoutError("Connection pool timeout")

    async def release(self, conn: Any):
        """Release connection back to pool."""
        async with self.lock:
            if conn in self.in_use:
                self.in_use.remove(conn)
                self.available.append(conn)

    async def _create_connection(self) -> Any:
        """Create new connection."""
        # Override in subclass
        return object()


# Global instances
_default_cache = MemoryCache()
_default_optimizer = QueryOptimizer()
_default_monitor = PerformanceMonitor()


def get_cache() -> MemoryCache:
    """Get default cache instance."""
    return _default_cache


def get_optimizer() -> QueryOptimizer:
    """Get default query optimizer."""
    return _default_optimizer


def get_monitor() -> PerformanceMonitor:
    """Get default performance monitor."""
    return _default_monitor
