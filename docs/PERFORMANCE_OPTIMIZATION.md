# Performance Optimization System

## Overview

The Performance Optimization System provides comprehensive tools for improving code review system performance through caching, batch processing, asynchronous task execution, and performance monitoring.

## Features

### 1. Memory Cache

Multi-strategy caching system with TTL support:

```python
from pr_agent.performance import MemoryCache, CacheStrategy

# Create LRU cache
cache = MemoryCache(
    max_size=1000,
    strategy=CacheStrategy.LRU,
    ttl=3600  # 1 hour
)

# Basic operations
cache.set("key", "value")
value = cache.get("key")
cache.delete("key")
cache.clear()

# Get statistics
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']:.2%}")
```

**Supported Strategies:**
- `LRU` (Least Recently Used)
- `LFU` (Least Frequently Used)
- `FIFO` (First In First Out)

### 2. Query Optimizer

Automatic query result caching:

```python
from pr_agent.performance import QueryOptimizer

optimizer = QueryOptimizer(cache_ttl=300)

# Execute query with caching
result = optimizer.execute_query(
    query="SELECT * FROM reviews WHERE status = ?",
    params=("pending",)
)

# Get query statistics
stats = optimizer.get_query_stats()
for query, info in stats.items():
    print(f"{query}: {info['executions']} executions, {info['cache_hits']} hits")
```

### 3. Batch Processor

Efficient batch processing with automatic flushing:

```python
from pr_agent.performance import BatchProcessor

def process_batch(items):
    # Process multiple items at once
    print(f"Processing {len(items)} items")

processor = BatchProcessor(
    batch_size=100,
    flush_interval=5.0,  # seconds
    processor_func=process_batch
)

# Add items (automatically batched)
for item in items:
    processor.add(item)

# Manual flush if needed
processor.flush()
```

### 4. Async Task Queue

Background task execution:

```python
from pr_agent.performance import AsyncTaskQueue

queue = AsyncTaskQueue(max_workers=4)

# Submit task
task_id = queue.submit_task(
    func=expensive_operation,
    args=(arg1, arg2),
    kwargs={"option": "value"}
)

# Check status
status = queue.get_task_status(task_id)
if status["status"] == "completed":
    result = status["result"]
```

### 5. Performance Monitor

Track and analyze performance metrics:

```python
from pr_agent.performance import PerformanceMonitor

monitor = PerformanceMonitor()

# Record metrics
monitor.record_metric("api_latency", 0.125)
monitor.record_metric("db_query_time", 0.050)

# Set alert thresholds
monitor.set_threshold("api_latency", 0.5)

# Get statistics
stats = monitor.get_stats("api_latency")
print(f"Average: {stats['avg']:.3f}s")
print(f"P95: {stats['p95']:.3f}s")

# Get alerts
alerts = monitor.get_alerts()
```

### 6. Performance Decorators

Convenient decorators for common patterns:

```python
from pr_agent.performance import cache_result, measure_time

@cache_result(ttl=300)
def expensive_computation(x, y):
    # Result will be cached for 5 minutes
    return x ** y

@measure_time("computation")
def timed_function():
    # Execution time will be recorded
    pass
```

## Web API

### Cache Management

```bash
# Get cache statistics
GET /api/performance/cache/stats

# Clear cache
POST /api/performance/cache/clear

# Set cache entry
POST /api/performance/cache/set
{
  "key": "my_key",
  "value": "my_value",
  "ttl": 3600
}

# Get cache entry
GET /api/performance/cache/get?key=my_key
```

### Performance Monitoring

```bash
# Get performance metrics
GET /api/performance/metrics

# Get specific metric stats
GET /api/performance/metrics/api_latency

# Get performance alerts
GET /api/performance/alerts
```

### Batch Processing

```bash
# Submit batch job
POST /api/performance/batch/submit
{
  "items": [...],
  "batch_size": 100
}

# Get batch status
GET /api/performance/batch/{job_id}
```

## Configuration

Configure performance settings in `configuration.toml`:

```toml
[performance]
# Cache settings
cache_max_size = 10000
cache_strategy = "lru"
cache_default_ttl = 3600

# Batch processing
batch_size = 100
batch_flush_interval = 5.0

# Async tasks
async_max_workers = 4
async_queue_size = 1000

# Monitoring
monitor_enabled = true
monitor_alert_threshold = 0.5
```

## Best Practices

### 1. Cache Strategy Selection

- **LRU**: Best for time-based access patterns (recent items more likely to be accessed)
- **LFU**: Best for frequency-based patterns (popular items accessed repeatedly)
- **FIFO**: Simple and predictable, good for queue-like access

### 2. TTL Configuration

- Short TTL (< 5 min): Frequently changing data
- Medium TTL (5-60 min): Semi-static data
- Long TTL (> 1 hour): Rarely changing data

### 3. Batch Size Tuning

- Small batches (10-50): Low latency, more overhead
- Medium batches (50-200): Balanced
- Large batches (200+): High throughput, higher latency

### 4. Monitoring Thresholds

Set thresholds based on SLA requirements:
- API latency: 95th percentile < 500ms
- Database queries: Average < 100ms
- Cache hit rate: > 80%

## Performance Metrics

### Cache Metrics

- **Hit Rate**: Percentage of cache hits
- **Miss Rate**: Percentage of cache misses
- **Eviction Rate**: Number of evictions per time period
- **Memory Usage**: Current cache size

### Query Metrics

- **Execution Time**: Time to execute query
- **Cache Hits**: Number of cached results used
- **Query Count**: Total number of executions

### System Metrics

- **Throughput**: Operations per second
- **Latency**: Response time distribution (avg, p50, p95, p99)
- **Error Rate**: Percentage of failed operations

## Troubleshooting

### High Cache Miss Rate

1. Check if TTL is too short
2. Verify cache size is adequate
3. Review access patterns
4. Consider different cache strategy

### Slow Query Performance

1. Enable query caching
2. Optimize query structure
3. Add database indexes
4. Use batch processing for multiple queries

### Memory Issues

1. Reduce cache max_size
2. Lower TTL values
3. Use more aggressive eviction strategy
4. Monitor memory usage metrics

## Examples

### Complete Optimization Pipeline

```python
from pr_agent.performance import (
    MemoryCache,
    QueryOptimizer,
    BatchProcessor,
    PerformanceMonitor,
    cache_result,
    measure_time
)

# Setup
cache = MemoryCache(max_size=1000, strategy=CacheStrategy.LRU)
optimizer = QueryOptimizer(cache_ttl=300)
monitor = PerformanceMonitor()

@cache_result(ttl=600)
@measure_time("review_analysis")
def analyze_review(review_id):
    # Cached and monitored
    review = optimizer.execute_query(
        "SELECT * FROM reviews WHERE id = ?",
        (review_id,)
    )
    return process_review(review)

# Batch processing
processor = BatchProcessor(
    batch_size=50,
    processor_func=lambda items: [analyze_review(r) for r in items]
)

for review_id in review_ids:
    processor.add(review_id)

processor.flush()

# Check performance
stats = monitor.get_stats("review_analysis")
print(f"Average time: {stats['avg']:.3f}s")
print(f"Cache hit rate: {cache.get_stats()['hit_rate']:.2%}")
```

## Related Documentation

- [Metrics Collection](METRICS_COLLECTION.md)
- [Report Generator](REPORT_GENERATOR.md)
- [Integration Testing](INTEGRATION_TESTING.md)
