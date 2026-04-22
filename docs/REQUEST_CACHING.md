# Request Caching Guide

Intelligent caching layer for AI model requests to reduce API calls and costs.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Quick Start](#quick-start)
- [Cache Policies](#cache-policies)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Cache Statistics](#cache-statistics)
- [Best Practices](#best-practices)
- [API Reference](#api-reference)

## Overview

The request cache provides intelligent caching of AI model responses with:

- **Multiple eviction policies**: LRU, LFU, TTL-based
- **Semantic key generation**: Consistent hashing of requests
- **TTL support**: Automatic expiration of stale entries
- **Statistics tracking**: Monitor cache performance
- **Cache warming**: Pre-populate cache with common requests

## Features

### Multi-Level Caching

- **LRU (Least Recently Used)**: Evicts oldest accessed entries
- **LFU (Least Frequently Used)**: Evicts least accessed entries
- **TTL (Time To Live)**: Evicts based on age

### Smart Key Generation

- Consistent hashing of model ID, prompt, and parameters
- Parameter normalization (order-independent)
- Whitespace normalization

### Performance Monitoring

- Hit/miss rate tracking
- Eviction and expiration counters
- Cache size monitoring

## Quick Start

### Basic Usage

```python
from pr_agent.cache import get_cache

# Get global cache instance
cache = get_cache()

# Try to get cached response
response = cache.get("gpt-4", "Review this code")

if response is None:
    # Cache miss - call API
    response = call_ai_model("gpt-4", "Review this code")
    
    # Cache the response
    cache.set("gpt-4", "Review this code", response)

# Use response
print(response)
```

### With Parameters

```python
# Cache with additional parameters
params = {"temperature": 0.7, "max_tokens": 1000}

response = cache.get("gpt-4", "Review this code", params=params)

if response is None:
    response = call_ai_model("gpt-4", "Review this code", **params)
    cache.set("gpt-4", "Review this code", response, params=params)
```

## Cache Policies

### LRU (Least Recently Used)

Evicts the entry that was accessed longest ago.

```python
from pr_agent.cache import RequestCache, CachePolicy

cache = RequestCache(
    max_size=1000,
    policy=CachePolicy.LRU
)
```

**Best for**: General-purpose caching where recent requests are more likely to repeat.

### LFU (Least Frequently Used)

Evicts the entry with the lowest access count.

```python
cache = RequestCache(
    max_size=1000,
    policy=CachePolicy.LFU
)
```

**Best for**: Workloads with hot/cold data patterns where some requests are much more common.

### TTL (Time To Live)

Evicts based on entry age, oldest first.

```python
cache = RequestCache(
    max_size=1000,
    policy=CachePolicy.TTL,
    default_ttl=3600  # 1 hour
)
```

**Best for**: Time-sensitive data where freshness is critical.

## Configuration

### Global Configuration

```python
from pr_agent.cache import configure_cache, CachePolicy

configure_cache(
    max_size=5000,
    policy=CachePolicy.LRU,
    default_ttl=7200  # 2 hours
)
```

### Per-Entry TTL

```python
# Override default TTL for specific entry
cache.set(
    "gpt-4",
    "Review this code",
    response,
    ttl=300  # 5 minutes
)
```

### Configuration File

Add to `configuration.toml`:

```toml
[cache]
enabled = true
max_size = 5000
policy = "lru"  # lru, lfu, or ttl
default_ttl = 7200  # seconds
enable_stats = true
```

## Usage Examples

### Basic Caching

```python
from pr_agent.cache import get_cache

cache = get_cache()

# Cache miss
response = cache.get("gpt-4", "Hello world")
assert response is None

# Store response
cache.set("gpt-4", "Hello world", "Hi there!")

# Cache hit
response = cache.get("gpt-4", "Hello world")
assert response == "Hi there!"
```

### With Metadata

```python
# Store with metadata
cache.set(
    "gpt-4",
    "Review PR #123",
    response,
    metadata={
        "pr_number": 123,
        "repo": "owner/repo",
        "timestamp": datetime.now()
    }
)
```

### Cache Warming

Pre-populate cache with common requests:

```python
# Prepare common requests
common_requests = [
    ("gpt-4", "Review this code", "Code looks good!", None),
    ("gpt-4", "Summarize changes", "Added new feature", None),
    ("claude-3", "Find bugs", "No issues found", {"temperature": 0.5}),
]

# Warm cache
cache.warm_cache(common_requests)
```

### Cache Invalidation

```python
# Clear all entries
cache.invalidate()

# Clear entries for specific model
cache.invalidate(model_id="gpt-4")

# Clear entries matching pattern
cache.invalidate(pattern="review")
```

### Cleanup Expired Entries

```python
# Remove all expired entries
cache.cleanup_expired()

# Schedule periodic cleanup
import schedule

schedule.every(1).hour.do(cache.cleanup_expired)
```

## Cache Statistics

### Get Statistics

```python
stats = cache.get_stats()

print(f"Hit rate: {stats['hit_rate']}%")
print(f"Total requests: {stats['total_requests']}")
print(f"Hits: {stats['hits']}")
print(f"Misses: {stats['misses']}")
print(f"Evictions: {stats['evictions']}")
print(f"Cache size: {stats['size']}/{stats['max_size']}")
```

### Monitor Performance

```python
import time

# Before
stats_before = cache.get_stats()

# Run workload
for i in range(1000):
    response = cache.get("gpt-4", f"Request {i % 100}")
    if response is None:
        response = f"Response {i}"
        cache.set("gpt-4", f"Request {i % 100}", response)

# After
stats_after = cache.get_stats()

# Calculate improvement
requests = stats_after['total_requests'] - stats_before['total_requests']
hits = stats_after['hits'] - stats_before['hits']
hit_rate = (hits / requests * 100) if requests > 0 else 0

print(f"Hit rate: {hit_rate:.2f}%")
print(f"API calls saved: {hits}")
```

## Best Practices

### 1. Choose the Right Policy

- **LRU**: Default choice for most workloads
- **LFU**: When you have clear hot/cold patterns
- **TTL**: When data freshness is critical

### 2. Set Appropriate TTL

```python
# Short TTL for dynamic data
cache.set("gpt-4", "Latest news", response, ttl=300)  # 5 minutes

# Long TTL for static data
cache.set("gpt-4", "Explain Python", response, ttl=86400)  # 24 hours

# No TTL for permanent data
cache.set("gpt-4", "What is 2+2?", response, ttl=None)
```

### 3. Monitor Cache Performance

```python
# Log statistics periodically
import logging

logger = logging.getLogger(__name__)

def log_cache_stats():
    stats = cache.get_stats()
    logger.info(
        f"Cache stats: hit_rate={stats['hit_rate']}%, "
        f"size={stats['size']}/{stats['max_size']}"
    )

# Call periodically
schedule.every(5).minutes.do(log_cache_stats)
```

### 4. Handle Cache Misses Gracefully

```python
def get_ai_response(model_id: str, prompt: str, **params):
    """Get AI response with caching."""
    # Try cache first
    response = cache.get(model_id, prompt, params)
    
    if response is not None:
        logger.debug("Cache hit")
        return response
    
    # Cache miss - call API
    logger.debug("Cache miss - calling API")
    try:
        response = call_ai_api(model_id, prompt, **params)
        
        # Cache successful response
        cache.set(model_id, prompt, response, params)
        
        return response
    except Exception as e:
        logger.error(f"API call failed: {e}")
        raise
```

### 5. Invalidate on Model Updates

```python
# When switching models, invalidate old cache
def switch_active_model(new_model_id: str):
    # Invalidate cache for old model
    old_model_id = get_active_model_id()
    cache.invalidate(model_id=old_model_id)
    
    # Set new model
    set_active_model(new_model_id)
```

### 6. Size the Cache Appropriately

```python
# Estimate cache size based on workload
avg_response_size = 1000  # bytes
max_memory = 100 * 1024 * 1024  # 100 MB
max_entries = max_memory // avg_response_size

cache = RequestCache(max_size=max_entries)
```

### 7. Use Cache Warming for Common Requests

```python
# Warm cache on startup
def warm_cache_on_startup():
    common_prompts = [
        "Review this code",
        "Find bugs",
        "Suggest improvements",
        "Explain this function",
    ]
    
    for prompt in common_prompts:
        # Generate sample response or load from file
        response = generate_sample_response(prompt)
        cache.set("gpt-4", prompt, response)
```

## API Reference

### RequestCache

```python
class RequestCache:
    def __init__(
        self,
        max_size: int = 1000,
        policy: CachePolicy = CachePolicy.LRU,
        default_ttl: Optional[int] = 3600,
        enable_stats: bool = True
    )
```

### Methods

#### get()

```python
def get(
    self,
    model_id: str,
    prompt: str,
    params: Optional[Dict[str, Any]] = None
) -> Optional[Any]
```

Get cached response.

#### set()

```python
def set(
    self,
    model_id: str,
    prompt: str,
    response: Any,
    params: Optional[Dict[str, Any]] = None,
    ttl: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None
)
```

Store response in cache.

#### invalidate()

```python
def invalidate(
    self,
    model_id: Optional[str] = None,
    pattern: Optional[str] = None
)
```

Invalidate cache entries.

#### get_stats()

```python
def get_stats(self) -> Dict[str, Any]
```

Get cache statistics.

#### warm_cache()

```python
def warm_cache(
    self,
    entries: List[Tuple[str, str, Any, Optional[Dict]]]
)
```

Pre-populate cache with entries.

#### cleanup_expired()

```python
def cleanup_expired(self)
```

Remove all expired entries.

## Troubleshooting

### Low Hit Rate

**Problem**: Cache hit rate is below 50%

**Solutions**:
- Increase cache size
- Adjust TTL (may be too short)
- Check if requests are truly repeating
- Verify parameter normalization is working

### High Memory Usage

**Problem**: Cache consuming too much memory

**Solutions**:
- Reduce max_size
- Decrease default_ttl
- Run cleanup_expired() more frequently
- Switch to TTL policy

### Stale Data

**Problem**: Getting outdated responses

**Solutions**:
- Reduce TTL
- Invalidate cache on data updates
- Use TTL policy instead of LRU/LFU

## Additional Resources

- [Model Management](./MODEL_MANAGEMENT.md)
- [Performance Optimization](./PERFORMANCE.md)
- [Monitoring Guide](./MONITORING.md)
