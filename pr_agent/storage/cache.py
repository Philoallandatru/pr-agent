"""
Redis Cache Manager

Provides caching layer for PR-Agent to improve performance.
Supports Redis and in-memory fallback.
"""

import json
import time
from typing import Any, Optional, Dict, List
from datetime import timedelta
import hashlib

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from pr_agent.config_loader import get_settings
from pr_agent.log import get_logger


class CacheManager:
    """
    Unified cache manager with Redis backend and in-memory fallback.

    Features:
    - Automatic serialization/deserialization
    - TTL support
    - Key namespacing
    - Cache statistics
    - Fallback to in-memory cache
    """

    def __init__(self, namespace: str = "pr-agent"):
        """
        Initialize cache manager.

        Args:
            namespace: Prefix for all cache keys
        """
        self.namespace = namespace
        self.logger = get_logger()
        self._memory_cache: Dict[str, tuple] = {}  # key -> (value, expiry)
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0
        }

        # Initialize Redis connection
        self.redis_client = None
        self.use_redis = False

        if REDIS_AVAILABLE:
            try:
                settings = get_settings()
                redis_config = settings.get("cache", {})

                if redis_config.get("enabled", False):
                    self.redis_client = redis.Redis(
                        host=redis_config.get("redis_host", "localhost"),
                        port=redis_config.get("redis_port", 6379),
                        db=redis_config.get("redis_db", 0),
                        password=redis_config.get("redis_password"),
                        decode_responses=True,
                        socket_timeout=redis_config.get("timeout", 5),
                        socket_connect_timeout=redis_config.get("timeout", 5)
                    )

                    # Test connection
                    self.redis_client.ping()
                    self.use_redis = True
                    self.logger.info("Redis cache initialized successfully")
            except Exception as e:
                self.logger.warning(f"Redis not available, using in-memory cache: {e}")
                self.redis_client = None
                self.use_redis = False
        else:
            self.logger.info("Redis library not installed, using in-memory cache")

    def _make_key(self, key: str) -> str:
        """Create namespaced cache key."""
        return f"{self.namespace}:{key}"

    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string."""
        return json.dumps(value, default=str)

    def _deserialize(self, value: str) -> Any:
        """Deserialize JSON string to value."""
        try:
            return json.loads(value)
        except:
            return value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache.

        Args:
            key: Cache key
            default: Default value if key not found

        Returns:
            Cached value or default
        """
        full_key = self._make_key(key)

        try:
            if self.use_redis:
                value = self.redis_client.get(full_key)
                if value is not None:
                    self._stats["hits"] += 1
                    return self._deserialize(value)
            else:
                # In-memory cache
                if full_key in self._memory_cache:
                    value, expiry = self._memory_cache[full_key]
                    if expiry is None or expiry > time.time():
                        self._stats["hits"] += 1
                        return value
                    else:
                        # Expired
                        del self._memory_cache[full_key]

            self._stats["misses"] += 1
            return default

        except Exception as e:
            self._stats["errors"] += 1
            self.logger.error(f"Cache get error for key {key}: {e}")
            return default

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None = no expiry)

        Returns:
            True if successful
        """
        full_key = self._make_key(key)

        try:
            if self.use_redis:
                serialized = self._serialize(value)
                if ttl:
                    self.redis_client.setex(full_key, ttl, serialized)
                else:
                    self.redis_client.set(full_key, serialized)
            else:
                # In-memory cache
                expiry = time.time() + ttl if ttl else None
                self._memory_cache[full_key] = (value, expiry)

            self._stats["sets"] += 1
            return True

        except Exception as e:
            self._stats["errors"] += 1
            self.logger.error(f"Cache set error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if successful
        """
        full_key = self._make_key(key)

        try:
            if self.use_redis:
                self.redis_client.delete(full_key)
            else:
                self._memory_cache.pop(full_key, None)

            self._stats["deletes"] += 1
            return True

        except Exception as e:
            self._stats["errors"] += 1
            self.logger.error(f"Cache delete error for key {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        full_key = self._make_key(key)

        try:
            if self.use_redis:
                return self.redis_client.exists(full_key) > 0
            else:
                if full_key in self._memory_cache:
                    _, expiry = self._memory_cache[full_key]
                    if expiry is None or expiry > time.time():
                        return True
                    else:
                        del self._memory_cache[full_key]
                return False
        except Exception as e:
            self.logger.error(f"Cache exists error for key {key}: {e}")
            return False

    def clear(self, pattern: Optional[str] = None) -> int:
        """
        Clear cache keys matching pattern.

        Args:
            pattern: Key pattern (None = clear all in namespace)

        Returns:
            Number of keys deleted
        """
        try:
            if self.use_redis:
                if pattern:
                    full_pattern = self._make_key(pattern)
                else:
                    full_pattern = f"{self.namespace}:*"

                keys = self.redis_client.keys(full_pattern)
                if keys:
                    return self.redis_client.delete(*keys)
                return 0
            else:
                # In-memory cache
                if pattern:
                    # Convert glob pattern to prefix match
                    # e.g., "user:*" -> "test:user:"
                    pattern_without_wildcard = pattern.rstrip('*')
                    full_pattern = self._make_key(pattern_without_wildcard)
                    keys_to_delete = [k for k in self._memory_cache.keys()
                                     if k.startswith(full_pattern)]
                else:
                    keys_to_delete = [k for k in self._memory_cache.keys()
                                     if k.startswith(f"{self.namespace}:")]

                for key in keys_to_delete:
                    del self._memory_cache[key]

                return len(keys_to_delete)

        except Exception as e:
            self.logger.error(f"Cache clear error: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0

        stats = {
            "backend": "redis" if self.use_redis else "memory",
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": hit_rate,
            "sets": self._stats["sets"],
            "deletes": self._stats["deletes"],
            "errors": self._stats["errors"]
        }

        if self.use_redis:
            try:
                info = self.redis_client.info("stats")
                stats["redis_keys"] = self.redis_client.dbsize()
                stats["redis_memory"] = info.get("used_memory_human")
            except:
                pass
        else:
            stats["memory_keys"] = len(self._memory_cache)

        return stats

    def cache_key_for_pr(self, repository: str, pr_number: int,
                         operation: str) -> str:
        """Generate cache key for PR operation."""
        return f"pr:{repository}:{pr_number}:{operation}"

    def cache_key_for_file(self, repository: str, file_path: str,
                          commit_sha: str) -> str:
        """Generate cache key for file content."""
        # Use hash for long file paths
        path_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
        return f"file:{repository}:{commit_sha}:{path_hash}"


# Global cache instance
_cache_manager: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """Get global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


# Decorator for caching function results
def cached(ttl: int = 300, key_prefix: str = "func"):
    """
    Decorator to cache function results.

    Args:
        ttl: Time to live in seconds
        key_prefix: Prefix for cache key

    Example:
        @cached(ttl=600, key_prefix="repo")
        def get_repository(repo_id: int):
            return db.get_repository(repo_id)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache = get_cache()

            # Generate cache key from function name and arguments
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)

            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result

            # Call function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)

            return result

        return wrapper
    return decorator
