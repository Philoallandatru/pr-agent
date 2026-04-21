"""
Unit tests for PollingState
"""

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from pr_agent.storage.polling_state import PollingState


class TestPollingState(unittest.TestCase):
    """Test cases for PollingState"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        self.temp_file.close()
        self.state = PollingState(state_file=self.temp_file.name)

    def tearDown(self):
        """Clean up test fixtures"""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_init_creates_empty_state(self):
        """Test that initialization creates empty state"""
        self.assertEqual(self.state.get_all_state(), {})

    def test_update_pr_state(self):
        """Test updating PR state"""
        self.state.update_pr_state(
            repo_key="PROJ/repo",
            pr_id=123,
            version=5,
            commands_run=["/review", "/describe"],
            status="completed"
        )

        pr_state = self.state.get_pr_state("PROJ/repo", 123)
        self.assertIsNotNone(pr_state)
        self.assertEqual(pr_state['version'], 5)
        self.assertEqual(pr_state['commands_run'], ["/review", "/describe"])
        self.assertEqual(pr_state['status'], "completed")

    def test_is_pr_processed(self):
        """Test checking if PR is processed"""
        # Not processed yet
        self.assertFalse(self.state.is_pr_processed("PROJ/repo", 123, 5))

        # Process it
        self.state.update_pr_state("PROJ/repo", 123, 5, ["/review"])

        # Now it's processed
        self.assertTrue(self.state.is_pr_processed("PROJ/repo", 123, 5))

        # Different version not processed
        self.assertFalse(self.state.is_pr_processed("PROJ/repo", 123, 6))

    def test_is_pr_updated(self):
        """Test checking if PR is updated"""
        # Process at version 5
        self.state.update_pr_state("PROJ/repo", 123, 5, ["/review"])

        # Version 6 is an update
        self.assertTrue(self.state.is_pr_updated("PROJ/repo", 123, 6))

        # Version 5 is not an update
        self.assertFalse(self.state.is_pr_updated("PROJ/repo", 123, 5))

        # Version 4 is not an update (older)
        self.assertFalse(self.state.is_pr_updated("PROJ/repo", 123, 4))

    def test_state_persistence(self):
        """Test that state persists across instances"""
        # Update state
        self.state.update_pr_state("PROJ/repo", 123, 5, ["/review"])

        # Create new instance with same file
        new_state = PollingState(state_file=self.temp_file.name)

        # State should be loaded
        pr_state = new_state.get_pr_state("PROJ/repo", 123)
        self.assertIsNotNone(pr_state)
        self.assertEqual(pr_state['version'], 5)

    def test_cleanup_old_entries(self):
        """Test cleanup of old entries"""
        # Add recent entry
        self.state.update_pr_state("PROJ/repo1", 1, 1, ["/review"])

        # Add old entry by manually modifying state
        old_date = (datetime.now() - timedelta(days=35)).isoformat()
        self.state._state["PROJ/repo2"] = {
            "2": {
                "version": 1,
                "last_processed": old_date,
                "commands_run": ["/review"],
                "status": "completed"
            }
        }
        self.state._save_state()

        # Cleanup with 30 day retention
        self.state.cleanup_old_entries(retention_days=30)

        # Recent entry should remain
        self.assertIsNotNone(self.state.get_pr_state("PROJ/repo1", 1))

        # Old entry should be removed
        self.assertIsNone(self.state.get_pr_state("PROJ/repo2", 2))

    def test_clear_state_specific_repo(self):
        """Test clearing state for specific repository"""
        # Add entries for two repos
        self.state.update_pr_state("PROJ/repo1", 1, 1, ["/review"])
        self.state.update_pr_state("PROJ/repo2", 2, 1, ["/review"])

        # Clear repo1
        self.state.clear_state(repo_key="PROJ/repo1")

        # repo1 should be cleared
        self.assertIsNone(self.state.get_pr_state("PROJ/repo1", 1))

        # repo2 should remain
        self.assertIsNotNone(self.state.get_pr_state("PROJ/repo2", 2))

    def test_clear_all_state(self):
        """Test clearing all state"""
        # Add entries
        self.state.update_pr_state("PROJ/repo1", 1, 1, ["/review"])
        self.state.update_pr_state("PROJ/repo2", 2, 1, ["/review"])

        # Clear all
        self.state.clear_state()

        # All should be cleared
        self.assertEqual(self.state.get_all_state(), {})

    def test_get_statistics(self):
        """Test getting statistics"""
        # Add some entries
        self.state.update_pr_state("PROJ/repo1", 1, 1, ["/review"])
        self.state.update_pr_state("PROJ/repo1", 2, 1, ["/review"])
        self.state.update_pr_state("PROJ/repo2", 3, 1, ["/review"])

        stats = self.state.get_statistics()

        self.assertEqual(stats['total_repositories'], 2)
        self.assertEqual(stats['total_prs_tracked'], 3)
        self.assertEqual(stats['prs_processed_last_24h'], 3)
        self.assertTrue(stats['state_file_exists'])


if __name__ == "__main__":
    unittest.main()
