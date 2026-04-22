"""
Unit tests for rate limiter.
"""

import unittest
import time
import tempfile
import os
from pr_agent.ratelimit.limiter import RateLimiter, RateLimitExceeded


class TestRateLimiter(unittest.TestCase):
    """Test cases for RateLimiter"""

    def setUp(self):
        """Set up test rate limiter"""
        self.limiter = RateLimiter(
            redis_client=None,  # Use memory backend
            default_limit=5,
            default_window=1,
            strategy="fixed_window"
        )

    def test_fixed_window_allows_requests(self):
        """Test fixed window allows requests within limit"""
        key = "test_user_1"

        for i in range(5):
            allowed, info = self.limiter.check_rate_limit(key)
            self.assertTrue(allowed)
            self.assertEqual(info["limit"], 5)
            self.assertEqual(info["remaining"], 5 - i - 1)

    def test_fixed_window_blocks_excess(self):
        """Test fixed window blocks requests over limit"""
        key = "test_user_2"

        # Use up the limit
        for _ in range(5):
            allowed, _ = self.limiter.check_rate_limit(key)
            self.assertTrue(allowed)

        # Next request should be blocked
        allowed, info = self.limiter.check_rate_limit(key)
        self.assertFalse(allowed)
        self.assertEqual(info["remaining"], 0)
        self.assertGreater(info["retry_after"], 0)

    def test_fixed_window_resets(self):
        """Test fixed window resets after window expires"""
        key = "test_user_3"

        # Use up the limit
        for _ in range(5):
            self.limiter.check_rate_limit(key)

        # Should be blocked
        allowed, _ = self.limiter.check_rate_limit(key)
        self.assertFalse(allowed)

        # Wait for window to reset
        time.sleep(1.1)

        # Should be allowed again
        allowed, info = self.limiter.check_rate_limit(key)
        self.assertTrue(allowed)
        self.assertEqual(info["remaining"], 4)

    def test_different_keys_independent(self):
        """Test different keys have independent limits"""
        key1 = "user_1"
        key2 = "user_2"

        # Use up limit for key1
        for _ in range(5):
            self.limiter.check_rate_limit(key1)

        # key1 should be blocked
        allowed, _ = self.limiter.check_rate_limit(key1)
        self.assertFalse(allowed)

        # key2 should still be allowed
        allowed, info = self.limiter.check_rate_limit(key2)
        self.assertTrue(allowed)
        self.assertEqual(info["remaining"], 4)

    def test_custom_limits(self):
        """Test custom limits per request"""
        key = "test_user_4"

        # Use custom limit of 10
        for i in range(10):
            allowed, info = self.limiter.check_rate_limit(key, limit=10)
            self.assertTrue(allowed)
            self.assertEqual(info["limit"], 10)

        # 11th request should be blocked
        allowed, _ = self.limiter.check_rate_limit(key, limit=10)
        self.assertFalse(allowed)

    def test_reset_key(self):
        """Test resetting rate limit for a key"""
        key = "test_user_5"

        # Use up the limit
        for _ in range(5):
            self.limiter.check_rate_limit(key)

        # Should be blocked
        allowed, _ = self.limiter.check_rate_limit(key)
        self.assertFalse(allowed)

        # Reset the key
        self.limiter.reset(key)

        # Should be allowed again
        allowed, info = self.limiter.check_rate_limit(key)
        self.assertTrue(allowed)
        self.assertEqual(info["remaining"], 4)

    def test_get_limits(self):
        """Test getting current limits without incrementing"""
        key = "test_user_6"

        # Make some requests
        for _ in range(3):
            self.limiter.check_rate_limit(key)

        # Get limits without incrementing
        info = self.limiter.get_limits(key)
        self.assertEqual(info["limit"], 5)
        self.assertEqual(info["remaining"], 2)

        # Verify it didn't increment
        info2 = self.limiter.get_limits(key)
        self.assertEqual(info2["remaining"], 2)


class TestSlidingWindow(unittest.TestCase):
    """Test cases for sliding window strategy"""

    def setUp(self):
        """Set up sliding window limiter"""
        self.limiter = RateLimiter(
            redis_client=None,
            default_limit=5,
            default_window=2,
            strategy="sliding_window"
        )

    def test_sliding_window_basic(self):
        """Test sliding window allows requests"""
        key = "test_user_1"

        for i in range(5):
            allowed, info = self.limiter.check_rate_limit(key)
            self.assertTrue(allowed)
            self.assertEqual(info["remaining"], 5 - i - 1)

    def test_sliding_window_blocks_excess(self):
        """Test sliding window blocks excess requests"""
        key = "test_user_2"

        # Use up limit
        for _ in range(5):
            self.limiter.check_rate_limit(key)

        # Should be blocked
        allowed, _ = self.limiter.check_rate_limit(key)
        self.assertFalse(allowed)

    def test_sliding_window_gradual_reset(self):
        """Test sliding window gradually allows requests as old ones expire"""
        key = "test_user_3"

        # Make 5 requests
        for _ in range(5):
            self.limiter.check_rate_limit(key)

        # Should be blocked
        allowed, _ = self.limiter.check_rate_limit(key)
        self.assertFalse(allowed)

        # Wait for first request to expire (2 second window)
        time.sleep(2.1)

        # Should allow new requests as old ones expired
        allowed, info = self.limiter.check_rate_limit(key)
        self.assertTrue(allowed)


class TestTokenBucket(unittest.TestCase):
    """Test cases for token bucket strategy"""

    def setUp(self):
        """Set up token bucket limiter"""
        self.limiter = RateLimiter(
            redis_client=None,
            default_limit=5,
            default_window=1,
            strategy="token_bucket"
        )

    def test_token_bucket_allows_burst(self):
        """Test token bucket allows burst of requests"""
        key = "test_user_1"

        # Should allow burst up to capacity
        for i in range(5):
            allowed, info = self.limiter.check_rate_limit(key)
            self.assertTrue(allowed)

    def test_token_bucket_blocks_when_empty(self):
        """Test token bucket blocks when tokens exhausted"""
        key = "test_user_2"

        # Use all tokens
        for _ in range(5):
            self.limiter.check_rate_limit(key)

        # Should be blocked
        allowed, _ = self.limiter.check_rate_limit(key)
        self.assertFalse(allowed)

    def test_token_bucket_refills(self):
        """Test token bucket refills over time"""
        key = "test_user_3"

        # Use all tokens
        for _ in range(5):
            self.limiter.check_rate_limit(key)

        # Should be blocked
        allowed, _ = self.limiter.check_rate_limit(key)
        self.assertFalse(allowed)

        # Wait for refill (5 tokens per 1 second = 0.2s per token)
        time.sleep(0.3)

        # Should have refilled at least 1 token
        allowed, _ = self.limiter.check_rate_limit(key)
        self.assertTrue(allowed)


if __name__ == '__main__':
    unittest.main()
