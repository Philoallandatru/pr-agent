"""
Rate limiting and quota management for API endpoints.

Supports multiple strategies:
- Fixed window: Simple counter per time window
- Sliding window: More accurate rate limiting
- Token bucket: Burst handling with refill rate
- Leaky bucket: Smooth rate limiting

Storage backends:
- Redis: Distributed rate limiting
- Memory: Single-instance rate limiting
"""

import time
import hashlib
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import threading


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(self, limit: int, window: int, retry_after: int):
        self.limit = limit
        self.window = window
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit exceeded: {limit} requests per {window}s. "
            f"Retry after {retry_after}s"
        )


class RateLimiter:
    """
    Rate limiter with multiple strategies and storage backends.

    Supports:
    - Fixed window rate limiting
    - Sliding window rate limiting
    - Token bucket algorithm
    - Per-user and per-organization limits
    - Redis and in-memory storage
    """

    def __init__(
        self,
        redis_client=None,
        default_limit: int = 100,
        default_window: int = 60,
        strategy: str = "fixed_window"
    ):
        """
        Initialize rate limiter.

        Args:
            redis_client: Optional Redis client for distributed limiting
            default_limit: Default requests per window
            default_window: Default time window in seconds
            strategy: Rate limiting strategy (fixed_window, sliding_window, token_bucket)
        """
        self.redis = redis_client
        self.default_limit = default_limit
        self.default_window = default_window
        self.strategy = strategy

        # In-memory storage (fallback when Redis unavailable)
        self._memory_store: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._lock = threading.Lock()

    def check_rate_limit(
        self,
        key: str,
        limit: Optional[int] = None,
        window: Optional[int] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is within rate limit.

        Args:
            key: Unique identifier (user_id, org_id, ip_address, etc.)
            limit: Max requests per window (uses default if None)
            window: Time window in seconds (uses default if None)

        Returns:
            Tuple of (allowed: bool, info: dict)
            info contains: limit, remaining, reset_time, retry_after
        """
        limit = limit or self.default_limit
        window = window or self.default_window

        if self.strategy == "fixed_window":
            return self._fixed_window(key, limit, window)
        elif self.strategy == "sliding_window":
            return self._sliding_window(key, limit, window)
        elif self.strategy == "token_bucket":
            return self._token_bucket(key, limit, window)
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")

    def _fixed_window(
        self,
        key: str,
        limit: int,
        window: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Fixed window rate limiting."""
        now = int(time.time())
        window_key = f"{key}:{now // window}"

        if self.redis:
            return self._fixed_window_redis(window_key, limit, window, now)
        else:
            return self._fixed_window_memory(window_key, limit, window, now)

    def _fixed_window_redis(
        self,
        window_key: str,
        limit: int,
        window: int,
        now: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Fixed window with Redis backend."""
        try:
            # Increment counter
            count = self.redis.incr(window_key)

            # Set expiry on first request
            if count == 1:
                self.redis.expire(window_key, window)

            # Get TTL for reset time
            ttl = self.redis.ttl(window_key)
            reset_time = now + ttl

            remaining = max(0, limit - count)
            allowed = count <= limit

            info = {
                "limit": limit,
                "remaining": remaining,
                "reset": reset_time,
                "retry_after": 0 if allowed else ttl
            }

            return allowed, info

        except Exception as e:
            # Fallback to memory on Redis error
            return self._fixed_window_memory(window_key, limit, window, now)

    def _fixed_window_memory(
        self,
        window_key: str,
        limit: int,
        window: int,
        now: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Fixed window with in-memory backend."""
        with self._lock:
            if window_key not in self._memory_store:
                self._memory_store[window_key] = {
                    "count": 0,
                    "reset": now + window
                }

            data = self._memory_store[window_key]

            # Reset if window expired
            if now >= data["reset"]:
                data["count"] = 0
                data["reset"] = now + window

            data["count"] += 1
            count = data["count"]
            reset_time = data["reset"]

            remaining = max(0, limit - count)
            allowed = count <= limit

            info = {
                "limit": limit,
                "remaining": remaining,
                "reset": reset_time,
                "retry_after": 0 if allowed else (reset_time - now)
            }

            return allowed, info

    def _sliding_window(
        self,
        key: str,
        limit: int,
        window: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Sliding window rate limiting (more accurate)."""
        now = time.time()
        window_start = now - window

        if self.redis:
            return self._sliding_window_redis(key, limit, window, now, window_start)
        else:
            return self._sliding_window_memory(key, limit, window, now, window_start)

    def _sliding_window_redis(
        self,
        key: str,
        limit: int,
        window: int,
        now: float,
        window_start: float
    ) -> Tuple[bool, Dict[str, Any]]:
        """Sliding window with Redis (using sorted set)."""
        try:
            # Remove old entries
            self.redis.zremrangebyscore(key, 0, window_start)

            # Count requests in window
            count = self.redis.zcard(key)

            allowed = count < limit

            if allowed:
                # Add current request
                self.redis.zadd(key, {str(now): now})
                self.redis.expire(key, window)
                count += 1

            remaining = max(0, limit - count)

            # Calculate retry_after from oldest request
            oldest = self.redis.zrange(key, 0, 0, withscores=True)
            retry_after = 0
            if oldest and not allowed:
                oldest_time = oldest[0][1]
                retry_after = int(oldest_time + window - now)

            info = {
                "limit": limit,
                "remaining": remaining,
                "reset": int(now + window),
                "retry_after": max(0, retry_after)
            }

            return allowed, info

        except Exception:
            return self._sliding_window_memory(key, limit, window, now, window_start)

    def _sliding_window_memory(
        self,
        key: str,
        limit: int,
        window: int,
        now: float,
        window_start: float
    ) -> Tuple[bool, Dict[str, Any]]:
        """Sliding window with in-memory backend."""
        with self._lock:
            if key not in self._memory_store:
                self._memory_store[key] = {"requests": []}

            data = self._memory_store[key]

            # Remove old requests
            data["requests"] = [
                ts for ts in data["requests"]
                if ts > window_start
            ]

            count = len(data["requests"])
            allowed = count < limit

            if allowed:
                data["requests"].append(now)
                count += 1

            remaining = max(0, limit - count)

            # Calculate retry_after
            retry_after = 0
            if data["requests"] and not allowed:
                oldest = min(data["requests"])
                retry_after = int(oldest + window - now)

            info = {
                "limit": limit,
                "remaining": remaining,
                "reset": int(now + window),
                "retry_after": max(0, retry_after)
            }

            return allowed, info

    def _token_bucket(
        self,
        key: str,
        limit: int,
        window: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Token bucket algorithm (allows bursts)."""
        now = time.time()
        refill_rate = limit / window  # tokens per second

        if self.redis:
            return self._token_bucket_redis(key, limit, refill_rate, now)
        else:
            return self._token_bucket_memory(key, limit, refill_rate, now)

    def _token_bucket_redis(
        self,
        key: str,
        capacity: int,
        refill_rate: float,
        now: float
    ) -> Tuple[bool, Dict[str, Any]]:
        """Token bucket with Redis."""
        try:
            bucket_key = f"bucket:{key}"

            # Get current bucket state
            data = self.redis.hgetall(bucket_key)

            if not data:
                # Initialize bucket
                tokens = capacity - 1
                last_refill = now
                self.redis.hset(bucket_key, mapping={
                    "tokens": tokens,
                    "last_refill": last_refill
                })
                self.redis.expire(bucket_key, int(capacity / refill_rate) + 60)

                info = {
                    "limit": capacity,
                    "remaining": int(tokens),
                    "reset": int(now + (capacity / refill_rate)),
                    "retry_after": 0
                }
                return True, info

            # Refill tokens
            tokens = float(data[b"tokens"])
            last_refill = float(data[b"last_refill"])

            elapsed = now - last_refill
            tokens = min(capacity, tokens + elapsed * refill_rate)

            allowed = tokens >= 1

            if allowed:
                tokens -= 1
                self.redis.hset(bucket_key, mapping={
                    "tokens": tokens,
                    "last_refill": now
                })

            remaining = int(tokens)
            retry_after = 0 if allowed else int((1 - tokens) / refill_rate)

            info = {
                "limit": capacity,
                "remaining": remaining,
                "reset": int(now + ((capacity - tokens) / refill_rate)),
                "retry_after": retry_after
            }

            return allowed, info

        except Exception:
            return self._token_bucket_memory(key, capacity, refill_rate, now)

    def _token_bucket_memory(
        self,
        key: str,
        capacity: int,
        refill_rate: float,
        now: float
    ) -> Tuple[bool, Dict[str, Any]]:
        """Token bucket with in-memory backend."""
        with self._lock:
            if key not in self._memory_store:
                self._memory_store[key] = {
                    "tokens": capacity - 1,
                    "last_refill": now
                }

                info = {
                    "limit": capacity,
                    "remaining": capacity - 1,
                    "reset": int(now + (capacity / refill_rate)),
                    "retry_after": 0
                }
                return True, info

            data = self._memory_store[key]

            # Refill tokens
            elapsed = now - data["last_refill"]
            data["tokens"] = min(capacity, data["tokens"] + elapsed * refill_rate)
            data["last_refill"] = now

            allowed = data["tokens"] >= 1

            if allowed:
                data["tokens"] -= 1

            remaining = int(data["tokens"])
            retry_after = 0 if allowed else int((1 - data["tokens"]) / refill_rate)

            info = {
                "limit": capacity,
                "remaining": remaining,
                "reset": int(now + ((capacity - data["tokens"]) / refill_rate)),
                "retry_after": retry_after
            }

            return allowed, info

    def reset(self, key: str):
        """Reset rate limit for a key."""
        if self.redis:
            # Delete all related keys
            for pattern in [key, f"{key}:*", f"bucket:{key}"]:
                keys = self.redis.keys(pattern)
                if keys:
                    self.redis.delete(*keys)
        else:
            with self._lock:
                # Remove from memory store
                keys_to_remove = [
                    k for k in self._memory_store.keys()
                    if k.startswith(key)
                ]
                for k in keys_to_remove:
                    del self._memory_store[k]

    def get_limits(self, key: str) -> Dict[str, Any]:
        """Get current rate limit status without incrementing."""
        if self.strategy == "fixed_window":
            now = int(time.time())
            window_key = f"{key}:{now // self.default_window}"

            if self.redis:
                count = int(self.redis.get(window_key) or 0)
                ttl = self.redis.ttl(window_key)
            else:
                with self._lock:
                    data = self._memory_store.get(window_key, {"count": 0, "reset": now})
                    count = data["count"]
                    ttl = data["reset"] - now

            return {
                "limit": self.default_limit,
                "remaining": max(0, self.default_limit - count),
                "reset": now + ttl,
                "retry_after": 0 if count < self.default_limit else ttl
            }

        # For other strategies, would need to implement similar logic
        return {
            "limit": self.default_limit,
            "remaining": self.default_limit,
            "reset": int(time.time() + self.default_window),
            "retry_after": 0
        }
