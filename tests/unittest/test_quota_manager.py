"""
Unit tests for quota manager.
"""

import unittest
import tempfile
import os
from datetime import datetime, timezone
from pr_agent.ratelimit.quota import QuotaManager, QuotaExceeded, QuotaInfo


class TestQuotaManager(unittest.TestCase):
    """Test cases for QuotaManager"""

    def setUp(self):
        """Set up test quota manager"""
        self.db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_path = self.db_file.name
        self.db_file.close()
        self.manager = QuotaManager(self.db_path)

    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_set_and_get_quota(self):
        """Test setting and getting quota"""
        org_id = 1
        self.manager.set_quota(org_id, "api_calls", 1000, "monthly")

        quota = self.manager.get_quota(org_id, "api_calls")
        self.assertIsNotNone(quota)
        self.assertEqual(quota.quota_type, "api_calls")
        self.assertEqual(quota.limit, 1000)
        self.assertEqual(quota.used, 0)
        self.assertEqual(quota.remaining, 1000)

    def test_increment_quota(self):
        """Test incrementing quota usage"""
        org_id = 1
        self.manager.set_quota(org_id, "reviews", 100, "monthly")

        # Increment by 1
        quota = self.manager.increment_quota(org_id, "reviews")
        self.assertEqual(quota.used, 1)
        self.assertEqual(quota.remaining, 99)

        # Increment by 5
        quota = self.manager.increment_quota(org_id, "reviews", amount=5)
        self.assertEqual(quota.used, 6)
        self.assertEqual(quota.remaining, 94)

    def test_quota_exceeded(self):
        """Test quota exceeded exception"""
        org_id = 1
        self.manager.set_quota(org_id, "repositories", 5, "never")

        # Use up quota
        for _ in range(5):
            self.manager.increment_quota(org_id, "repositories")

        # Next increment should raise exception
        with self.assertRaises(QuotaExceeded) as context:
            self.manager.increment_quota(org_id, "repositories")

        self.assertEqual(context.exception.quota_type, "repositories")
        self.assertEqual(context.exception.limit, 5)
        self.assertEqual(context.exception.current, 6)

    def test_check_quota(self):
        """Test checking quota availability"""
        org_id = 1
        self.manager.set_quota(org_id, "users", 10, "never")

        # Should allow
        self.assertTrue(self.manager.check_quota(org_id, "users", 5))

        # Use 8
        self.manager.increment_quota(org_id, "users", amount=8, check_limit=False)

        # Should allow 2 more
        self.assertTrue(self.manager.check_quota(org_id, "users", 2))

        # Should not allow 3 more
        self.assertFalse(self.manager.check_quota(org_id, "users", 3))

    def test_decrement_quota(self):
        """Test decrementing quota (e.g., when deleting resources)"""
        org_id = 1
        self.manager.set_quota(org_id, "repositories", 10, "never")

        # Add 5
        self.manager.increment_quota(org_id, "repositories", amount=5, check_limit=False)

        quota = self.manager.get_quota(org_id, "repositories")
        self.assertEqual(quota.used, 5)

        # Remove 2
        quota = self.manager.decrement_quota(org_id, "repositories", amount=2)
        self.assertEqual(quota.used, 3)
        self.assertEqual(quota.remaining, 7)

    def test_decrement_below_zero(self):
        """Test decrement doesn't go below zero"""
        org_id = 1
        self.manager.set_quota(org_id, "users", 10, "never")

        # Add 2
        self.manager.increment_quota(org_id, "users", amount=2, check_limit=False)

        # Try to remove 5 (should only go to 0)
        quota = self.manager.decrement_quota(org_id, "users", amount=5)
        self.assertEqual(quota.used, 0)

    def test_get_all_quotas(self):
        """Test getting all quotas for an organization"""
        org_id = 1

        # Set multiple quotas
        self.manager.set_quota(org_id, "api_calls", 1000, "monthly")
        self.manager.set_quota(org_id, "reviews", 100, "monthly")
        self.manager.set_quota(org_id, "repositories", 50, "never")

        # Use some
        self.manager.increment_quota(org_id, "api_calls", amount=100, check_limit=False)
        self.manager.increment_quota(org_id, "reviews", amount=10, check_limit=False)

        # Get all
        quotas = self.manager.get_all_quotas(org_id)
        self.assertEqual(len(quotas), 3)

        # Check values
        api_quota = next(q for q in quotas if q.quota_type == "api_calls")
        self.assertEqual(api_quota.used, 100)
        self.assertEqual(api_quota.remaining, 900)

        review_quota = next(q for q in quotas if q.quota_type == "reviews")
        self.assertEqual(review_quota.used, 10)
        self.assertEqual(review_quota.remaining, 90)

    def test_reset_quota(self):
        """Test manually resetting quota"""
        org_id = 1
        self.manager.set_quota(org_id, "api_calls", 1000, "monthly")

        # Use some
        self.manager.increment_quota(org_id, "api_calls", amount=500, check_limit=False)

        quota = self.manager.get_quota(org_id, "api_calls")
        self.assertEqual(quota.used, 500)

        # Reset
        self.manager.reset_quota(org_id, "api_calls")

        quota = self.manager.get_quota(org_id, "api_calls")
        self.assertEqual(quota.used, 0)
        self.assertEqual(quota.remaining, 1000)

    def test_no_quota_defined(self):
        """Test behavior when no quota is defined (unlimited)"""
        org_id = 1

        # Check quota that doesn't exist
        self.assertTrue(self.manager.check_quota(org_id, "undefined_quota", 999999))

        # Increment should work
        quota = self.manager.increment_quota(org_id, "undefined_quota", amount=100, check_limit=False)
        self.assertEqual(quota.limit, 0)  # 0 means unlimited
        self.assertEqual(quota.used, 100)

    def test_quota_percentage(self):
        """Test quota percentage calculation"""
        org_id = 1
        self.manager.set_quota(org_id, "reviews", 100, "monthly")

        # Use 75
        self.manager.increment_quota(org_id, "reviews", amount=75, check_limit=False)

        quota = self.manager.get_quota(org_id, "reviews")
        self.assertEqual(quota.percentage_used, 75.0)
        self.assertFalse(quota.is_exceeded)

        # Use 26 more (total 101, over limit)
        self.manager.increment_quota(org_id, "reviews", amount=26, check_limit=False)

        quota = self.manager.get_quota(org_id, "reviews")
        self.assertGreater(quota.percentage_used, 100.0)
        self.assertTrue(quota.is_exceeded)

    def test_alert_threshold(self):
        """Test quota alert thresholds"""
        org_id = 1
        self.manager.set_quota(org_id, "api_calls", 1000, "monthly")
        self.manager.set_alert_threshold(org_id, "api_calls", 80)

        # Use 750 (75%)
        self.manager.increment_quota(org_id, "api_calls", amount=750, check_limit=False)

        # Should not trigger alert yet
        alerts = self.manager.check_alerts(org_id)
        self.assertEqual(len(alerts), 0)

        # Use 100 more (85%)
        self.manager.increment_quota(org_id, "api_calls", amount=100, check_limit=False)

        # Should trigger alert
        alerts = self.manager.check_alerts(org_id)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["quota_type"], "api_calls")
        self.assertEqual(alerts[0]["threshold"], 80)
        self.assertGreaterEqual(alerts[0]["current_percentage"], 80)

    def test_different_reset_periods(self):
        """Test different reset periods"""
        org_id = 1

        # Daily
        self.manager.set_quota(org_id, "daily_quota", 100, "daily")
        quota = self.manager.get_quota(org_id, "daily_quota")
        self.assertIsNotNone(quota.reset_date)

        # Monthly
        self.manager.set_quota(org_id, "monthly_quota", 1000, "monthly")
        quota = self.manager.get_quota(org_id, "monthly_quota")
        self.assertIsNotNone(quota.reset_date)

        # Never
        self.manager.set_quota(org_id, "permanent_quota", 50, "never")
        quota = self.manager.get_quota(org_id, "permanent_quota")
        self.assertIsNone(quota.reset_date)

    def test_update_quota_limit(self):
        """Test updating quota limit"""
        org_id = 1
        self.manager.set_quota(org_id, "reviews", 100, "monthly")

        # Use some
        self.manager.increment_quota(org_id, "reviews", amount=50, check_limit=False)

        # Update limit
        self.manager.set_quota(org_id, "reviews", 200, "monthly")

        quota = self.manager.get_quota(org_id, "reviews")
        self.assertEqual(quota.limit, 200)
        self.assertEqual(quota.used, 50)  # Usage preserved
        self.assertEqual(quota.remaining, 150)

    def test_multiple_organizations(self):
        """Test quota isolation between organizations"""
        org1 = 1
        org2 = 2

        # Set same quota for both
        self.manager.set_quota(org1, "reviews", 100, "monthly")
        self.manager.set_quota(org2, "reviews", 100, "monthly")

        # Use different amounts
        self.manager.increment_quota(org1, "reviews", amount=30, check_limit=False)
        self.manager.increment_quota(org2, "reviews", amount=70, check_limit=False)

        # Check isolation
        quota1 = self.manager.get_quota(org1, "reviews")
        quota2 = self.manager.get_quota(org2, "reviews")

        self.assertEqual(quota1.used, 30)
        self.assertEqual(quota2.used, 70)


if __name__ == '__main__':
    unittest.main()
