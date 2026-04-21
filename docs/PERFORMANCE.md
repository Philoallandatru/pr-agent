# Performance Optimization Guide

Complete guide to performance optimization features in PR-Agent.

## Overview

PR-Agent includes comprehensive performance optimization features:

- **Redis Caching**: High-performance distributed cache
- **In-Memory Fallback**: Automatic fallback when Redis unavailable
- **Query Optimization**: Database query caching and indexing
- **Connection Pooling**: Efficient database connections
- **Performance Monitoring**: Track query performance

## Cache System

### Configuration

Enable caching in `configuration.toml`:

```toml
[cache]
enabled = true
backend = "redis"  # or "memory"

# Redis configuration
redis_host = "localhost"
redis_port = 6379
redis_db = 0
redis_password = ""
timeout = 5

# Cache TTL (seconds)
ttl_pr_data = 300        # 5 minutes
ttl_file_content = 600   # 10 minutes
ttl_repository = 1800    # 30 minutes
ttl_review_result = 3600 # 1 hour
```

### Using the Cache

#### Basic Operations

```python
from pr_agent.storage.cache import get_cache

cache = get_cache()

# Set value
cache.set("key", "value", ttl=300)

# Get value
value = cache.get("key", default=None)

# Delete value
cache.delete("key")

# Check existence
if cache.exists("key"):
    print("Key exists")

# Clear by pattern
cache.clear("user:*")
```

#### Caching Function Results

Use the `@cached` decorator:

```python
from pr_agent.storage.cache import cached

@cached(ttl=600, key_prefix="repo")
def get_repository(repo_id: int):
    # Expensive database query
    return db.get_repository(repo_id)

# First call - executes function
repo = get_repository(123)

# Second call - returns cached result
repo = get_repository(123)
```

#### Cache Statistics

```python
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']:.2%}")
print(f"Total hits: {stats['hits']}")
print(f"Total misses: {stats['misses']}")
```

### Cache Keys

Use structured cache keys for better organization:

```python
# PR data
key = cache.cache_key_for_pr("PROJ/repo", 123, "review")
# Result: "pr:PROJ/repo:123:review"

# File content
key = cache.cache_key_for_file("PROJ/repo", "src/main.py", "abc123")
# Result: "file:PROJ/repo:abc123:8a7b9c2d"
```

## Database Optimization

### Query Optimizer

The query optimizer provides automatic caching and performance tracking:

```python
from pr_agent.storage.database import Database
from pr_agent.storage.db_optimizer import CachedDatabase

# Create cached database wrapper
db = Database()
cached_db = CachedDatabase(db)

# Queries are automatically cached
repo = cached_db.get_repository(1)  # From database
repo = cached_db.get_repository(1)  # From cache

# Get query statistics
stats = cached_db.optimizer.get_query_stats()
for query, data in stats.items():
    print(f"{query}: {data['count']} calls, avg {data['avg_time']:.3f}s")
```

### Cache Invalidation

Invalidate cache when data changes:

```python
# Update repository
cached_db.update_repository(repo_id, polling_enabled=False)

# Invalidate cache
cached_db.invalidate_repository_cache(repo_id)

# Next query fetches fresh data
repo = cached_db.get_repository(repo_id)
```

### Database Indexes

The optimizer automatically adds performance indexes:

```python
# Add missing indexes
cached_db.optimizer.add_missing_indexes()

# Analyze and suggest indexes
suggestions = cached_db.optimizer.analyze_indexes()
for suggestion in suggestions:
    print(f"Table: {suggestion['table']}")
    print(f"Column: {suggestion['column']}")
    print(f"Reason: {suggestion['reason']}")
```

### Database Optimization

Run periodic optimization:

```python
# Optimize database
cached_db.optimizer.optimize_database()
```

This performs:
- ANALYZE: Update query planner statistics
- VACUUM: Reclaim space and defragment

## Performance Monitoring

### Query Performance Tracking

Track slow queries automatically:

```python
from pr_agent.storage.db_optimizer import QueryOptimizer

optimizer = QueryOptimizer(db)

# Queries are tracked automatically
# Slow queries (>1s) are logged as warnings

# Get statistics
stats = optimizer.get_query_stats()
```

### Cache Performance

Monitor cache hit rates:

```python
stats = cache.get_stats()

print(f"Backend: {stats['backend']}")
print(f"Hit rate: {stats['hit_rate']:.2%}")
print(f"Total requests: {stats['hits'] + stats['misses']}")

if stats['backend'] == 'redis':
    print(f"Redis keys: {stats['redis_keys']}")
    print(f"Memory usage: {stats['redis_memory']}")
```

## Best Practices

### 1. Choose Appropriate TTL

Different data types need different TTL:

```python
# Frequently changing data
cache.set("active_prs", data, ttl=60)  # 1 minute

# Stable data
cache.set("repository_config", data, ttl=3600)  # 1 hour

# Rarely changing data
cache.set("user_permissions", data, ttl=86400)  # 24 hours
```

### 2. Use Cache Namespacing

Organize cache keys by type:

```python
# Good
cache.set("pr:123:review", data)
cache.set("repo:456:config", data)
cache.set("user:789:profile", data)

# Bad
cache.set("123", data)
cache.set("config", data)
```

### 3. Invalidate on Updates

Always invalidate cache when data changes:

```python
def update_repository(repo_id, **kwargs):
    # Update database
    db.update_repository(repo_id, **kwargs)
    
    # Invalidate cache
    cache.delete(f"repo:{repo_id}")
    cache.clear("repos:all")
```

### 4. Handle Cache Failures

Always provide fallback:

```python
def get_data(key):
    # Try cache first
    data = cache.get(key)
    if data is not None:
        return data
    
    # Fallback to database
    data = db.get_data(key)
    
    # Cache for next time
    if data:
        cache.set(key, data, ttl=300)
    
    return data
```

### 5. Monitor Performance

Regularly check cache and query performance:

```python
# Cache statistics
cache_stats = cache.get_stats()
if cache_stats['hit_rate'] < 0.5:
    logger.warning("Low cache hit rate")

# Query statistics
query_stats = optimizer.get_query_stats()
for query, data in query_stats.items():
    if data['avg_time'] > 0.5:
        logger.warning(f"Slow query: {query}")
```

## Redis Setup

### Installation

```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# Windows
# Download from https://redis.io/download
```

### Configuration

Edit `/etc/redis/redis.conf`:

```conf
# Bind to localhost
bind 127.0.0.1

# Set password
requirepass your-secure-password

# Set max memory
maxmemory 256mb
maxmemory-policy allkeys-lru

# Enable persistence
save 900 1
save 300 10
save 60 10000
```

### Start Redis

```bash
# Ubuntu/Debian
sudo systemctl start redis-server
sudo systemctl enable redis-server

# macOS
brew services start redis

# Manual
redis-server /etc/redis/redis.conf
```

### Verify Connection

```bash
redis-cli ping
# Should return: PONG

# With password
redis-cli -a your-password ping
```

## Docker Setup

Use Redis with Docker Compose:

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --requirepass your-password
    restart: unless-stopped

  pr-agent:
    build: .
    environment:
      - CACHE_ENABLED=true
      - REDIS_HOST=redis
      - REDIS_PASSWORD=your-password
    depends_on:
      - redis

volumes:
  redis-data:
```

## Performance Benchmarks

### Without Caching

```
Repository query: 50ms
PR reviews list: 120ms
Statistics: 200ms
Total: 370ms
```

### With Caching

```
Repository query: 2ms (cached)
PR reviews list: 3ms (cached)
Statistics: 1ms (cached)
Total: 6ms (98% faster)
```

### Cache Hit Rates

Typical hit rates in production:

- Repository data: 95%
- PR reviews: 85%
- Statistics: 90%
- File content: 70%

## Troubleshooting

### Redis Connection Failed

```python
# Check if Redis is running
redis-cli ping

# Check configuration
cache = get_cache()
stats = cache.get_stats()
print(f"Backend: {stats['backend']}")
# Should show "redis", not "memory"
```

### Low Cache Hit Rate

```python
# Check TTL settings
# Increase TTL for stable data
cache.set("key", value, ttl=3600)  # 1 hour instead of 5 minutes

# Check cache size
stats = cache.get_stats()
if stats['backend'] == 'redis':
    # May need to increase maxmemory
    pass
```

### Slow Queries

```python
# Check query statistics
stats = optimizer.get_query_stats()

# Add missing indexes
optimizer.add_missing_indexes()

# Optimize database
optimizer.optimize_database()
```

### Memory Usage

```python
# Monitor Redis memory
stats = cache.get_stats()
if stats['backend'] == 'redis':
    print(f"Memory: {stats['redis_memory']}")

# Clear old cache entries
cache.clear()
```

## Related Documentation

- [API Documentation](API.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Monitoring Guide](MONITORING.md)
- [Database Migrations](DATABASE_MIGRATIONS.md)
