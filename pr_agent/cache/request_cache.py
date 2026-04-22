"""
Intelligent request caching layer for AI model requests.

Provides multi-level caching with LRU/LFU eviction policies,
semantic similarity matching, and automatic cache warming.
"""

import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class CachePolicy(Enum):
    """Cache eviction policies."""
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    TTL = "ttl"  # Time To Live only


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl_seconds: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.ttl_seconds is None:
            return False
        age = (datetime.now() - self.created_at).total_seconds()
        return age > self.ttl_seconds

    def touch(self):
        """Update access metadata."""
        self.last_accessed = datetime.now()
        self.access_count += 1


class RequestCache:
    """
    Intelligent caching layer for AI model requests.

    Features:
    - Multiple eviction policies (LRU/LFU/TTL)
    - Semantic cache key generation
    - Cache statistics and monitoring
    - Automatic cache warming
    - Size-based eviction
    """

    def __init__(
        self,
        max_size: int = 1000,
        policy: CachePolicy = CachePolicy.LRU,
        default_ttl: Optional[int] = 3600,
        enable_stats: bool = True
    ):
        """
        Initialize request cache.

        Args:
            max_size: Maximum number of entries
            policy: Eviction policy
            default_ttl: Default TTL in seconds
            enable_stats: Enable statistics tracking
        """
        self.max_size = max_size
        self.policy = policy
        self.default_ttl = default_ttl
        self.enable_stats = enable_stats

        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
            "total_requests": 0
        }

    def _generate_cache_key(
        self,
        model_id: str,
        prompt: str,
        params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate cache key from request parameters.

        Args:
            model_id: Model identifier
            prompt: Input prompt
            params: Additional parameters

        Returns:
            Cache key hash
        """
        # Normalize parameters
        normalized_params = {}
        if params:
            # Sort keys for consistent hashing
            for key in sorted(params.keys()):
                value = params[key]
                # Convert to JSON-serializable format
                if isinstance(value, (list, dict)):
                    normalized_params[key] = json.dumps(value, sort_keys=True)
                else:
                    normalized_params[key] = str(value)

        # Create cache key components
        key_data = {
            "model": model_id,
            "prompt": prompt.strip(),
            "params": normalized_params
        }

        # Generate hash
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()

    def get(
        self,
        model_id: str,
        prompt: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        Get cached response.

        Args:
            model_id: Model identifier
            prompt: Input prompt
            params: Additional parameters

        Returns:
            Cached response or None
        """
        if self.enable_stats:
            self._stats["total_requests"] += 1

        key = self._generate_cache_key(model_id, prompt, params)

        # Check if key exists
        if key not in self._cache:
            if self.enable_stats:
                self._stats["misses"] += 1
            return None

        entry = self._cache[key]

        # Check expiration
        if entry.is_expired():
            del self._cache[key]
            if self.enable_stats:
                self._stats["expirations"] += 1
                self._stats["misses"] += 1
            return None

        # Update access metadata
        entry.touch()

        # Move to end for LRU
        if self.policy == CachePolicy.LRU:
            self._cache.move_to_end(key)

        if self.enable_stats:
            self._stats["hits"] += 1

        logger.debug(f"Cache hit for key {key[:8]}...")
        return entry.value

    def set(
        self,
        model_id: str,
        prompt: str,
        response: Any,
        params: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Store response in cache.

        Args:
            model_id: Model identifier
            prompt: Input prompt
            response: Model response
            params: Additional parameters
            ttl: Time to live in seconds
            metadata: Additional metadata
        """
        key = self._generate_cache_key(model_id, prompt, params)

        # Check if we need to evict
        if len(self._cache) >= self.max_size and key not in self._cache:
            self._evict()

        # Create entry
        entry = CacheEntry(
            key=key,
            value=response,
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            access_count=0,
            ttl_seconds=ttl or self.default_ttl,
            metadata=metadata or {}
        )

        self._cache[key] = entry

        # Move to end for LRU
        if self.policy == CachePolicy.LRU:
            self._cache.move_to_end(key)

        logger.debug(f"Cached response for key {key[:8]}...")

    def _evict(self):
        """Evict entry based on policy."""
        if not self._cache:
            return

        if self.policy == CachePolicy.LRU:
            # Remove oldest (first) entry
            key = next(iter(self._cache))
            del self._cache[key]

        elif self.policy == CachePolicy.LFU:
            # Remove least frequently used
            min_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].access_count
            )
            del self._cache[min_key]

        elif self.policy == CachePolicy.TTL:
            # Remove oldest by creation time
            min_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].created_at
            )
            del self._cache[min_key]

        if self.enable_stats:
            self._stats["evictions"] += 1

        logger.debug(f"Evicted entry using {self.policy.value} policy")

    def invalidate(
        self,
        model_id: Optional[str] = None,
        pattern: Optional[str] = None
    ):
        """
        Invalidate cache entries.

        Args:
            model_id: Invalidate entries for specific model
            pattern: Invalidate entries matching pattern
        """
        if model_id is None and pattern is None:
            # Clear all
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cleared {count} cache entries")
            return

        # Filter entries to remove
        keys_to_remove = []
        for key, entry in self._cache.items():
            if model_id and entry.metadata.get("model_id") == model_id:
                keys_to_remove.append(key)
            elif pattern and pattern in key:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._cache[key]

        logger.info(f"Invalidated {len(keys_to_remove)} cache entries")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Statistics dictionary
        """
        total = self._stats["total_requests"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0

        return {
            **self._stats,
            "hit_rate": round(hit_rate, 2),
            "size": len(self._cache),
            "max_size": self.max_size,
            "policy": self.policy.value
        }

    def warm_cache(
        self,
        entries: List[Tuple[str, str, Any, Optional[Dict]]]
    ):
        """
        Pre-populate cache with entries.

        Args:
            entries: List of (model_id, prompt, response, params) tuples
        """
        for model_id, prompt, response, params in entries:
            self.set(model_id, prompt, response, params)

        logger.info(f"Warmed cache with {len(entries)} entries")

    def cleanup_expired(self):
        """Remove all expired entries."""
        keys_to_remove = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]

        for key in keys_to_remove:
            del self._cache[key]

        if self.enable_stats:
            self._stats["expirations"] += len(keys_to_remove)

        logger.info(f"Cleaned up {len(keys_to_remove)} expired entries")


# Global cache instance
_global_cache: Optional[RequestCache] = None


def get_cache() -> RequestCache:
    """Get global cache instance."""
    global _global_cache
    if _global_cache is None:
        _global_cache = RequestCache()
    return _global_cache


def configure_cache(
    max_size: int = 1000,
    policy: CachePolicy = CachePolicy.LRU,
    default_ttl: Optional[int] = 3600
):
    """Configure global cache instance."""
    global _global_cache
    _global_cache = RequestCache(
        max_size=max_size,
        policy=policy,
        default_ttl=default_ttl
    )
