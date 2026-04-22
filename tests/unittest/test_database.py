"""
Unit tests for Database
"""

import os
import tempfile
import unittest
from pathlib import Path

from pr_agent.storage.database import Database


class TestDatabase(unittest.TestCase):
    """Test cases for Database"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        self.temp_file.close()
        self.db = Database(db_path=self.temp_file.name)

    def tearDown(self):
        """Clean up test fixtures"""
        self.db.close()
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_add_repository(self):
        """Test adding a repository"""
        repo_id = self.db.add_repository(
            project_key="PROJ",
            repo_slug="test-repo",
            polling_enabled=True,
            polling_interval=300
        )
        self.assertIsNotNone(repo_id)
        self.assertGreater(repo_id, 0)

    def test_get_repository(self):
        """Test getting a repository"""
        repo_id = self.db.add_repository("PROJ", "test-repo")
        repo = self.db.get_repository(repo_id)

        self.assertIsNotNone(repo)
        self.assertEqual(repo['project_key'], "PROJ")
        self.assertEqual(repo['repo_slug'], "test-repo")

    def test_get_all_repositories(self):
        """Test getting all repositories"""
        self.db.add_repository("PROJ1", "repo1")
        self.db.add_repository("PROJ2", "repo2")

        repos = self.db.get_all_repositories()
        self.assertEqual(len(repos), 2)

    def test_update_repository(self):
        """Test updating repository"""
        repo_id = self.db.add_repository("PROJ", "test-repo", polling_interval=300)

        self.db.update_repository(repo_id, polling_interval=600)

        repo = self.db.get_repository(repo_id)
        self.assertEqual(repo['polling_interval'], 600)

    def test_delete_repository(self):
        """Test deleting repository"""
        repo_id = self.db.add_repository("PROJ", "test-repo")
        self.db.delete_repository(repo_id)

        repo = self.db.get_repository(repo_id)
        self.assertIsNone(repo)

    def test_add_pr_review(self):
        """Test adding PR review"""
        repo_id = self.db.add_repository("PROJ", "test-repo")
        review_id = self.db.add_pr_review(
            repository_id=repo_id,
            pr_id=123,
            pr_title="Test PR",
            pr_author="user",
            pr_url="https://example.com/pr/123",
            commands_run=["/review", "/describe"]
        )

        self.assertIsNotNone(review_id)
        self.assertGreater(review_id, 0)

    def test_get_pr_review(self):
        """Test getting PR review"""
        repo_id = self.db.add_repository("PROJ", "test-repo")
        review_id = self.db.add_pr_review(
            repository_id=repo_id,
            pr_id=123,
            pr_title="Test PR",
            pr_author="user",
            pr_url="https://example.com/pr/123",
            commands_run=["/review"]
        )

        review = self.db.get_pr_review(review_id)
        self.assertIsNotNone(review)
        self.assertEqual(review['pr_id'], 123)
        self.assertEqual(review['pr_title'], "Test PR")

    def test_update_pr_review(self):
        """Test updating PR review"""
        repo_id = self.db.add_repository("PROJ", "test-repo")
        review_id = self.db.add_pr_review(
            repository_id=repo_id,
            pr_id=123,
            pr_title="Test PR",
            pr_author="user",
            pr_url="https://example.com/pr/123",
            commands_run=["/review"]
        )

        self.db.update_pr_review(
            review_id=review_id,
            status="completed",
            review_result={"score": 8}
        )

        review = self.db.get_pr_review(review_id)
        self.assertEqual(review['status'], "completed")

    def test_get_pr_reviews_with_filters(self):
        """Test getting PR reviews with filters"""
        repo_id = self.db.add_repository("PROJ", "test-repo")

        # Add multiple reviews
        self.db.add_pr_review(repo_id, 1, "PR 1", "user", "url1", ["/review"], "completed")
        self.db.add_pr_review(repo_id, 2, "PR 2", "user", "url2", ["/review"], "pending")
        self.db.add_pr_review(repo_id, 3, "PR 3", "user", "url3", ["/review"], "completed")

        # Filter by status
        completed_reviews = self.db.get_pr_reviews(status="completed")
        self.assertEqual(len(completed_reviews), 2)

        # Filter by repository
        repo_reviews = self.db.get_pr_reviews(repository_id=repo_id)
        self.assertEqual(len(repo_reviews), 3)

    def test_add_log(self):
        """Test adding system log"""
        self.db.add_log("INFO", "Test message", {"key": "value"})

        logs = self.db.get_logs(limit=1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]['level'], "INFO")
        self.assertEqual(logs[0]['message'], "Test message")

    def test_add_prompt_template(self):
        """Test adding prompt template"""
        template_id = self.db.add_prompt_template(
            command="review",
            template="Custom review prompt"
        )

        self.assertIsNotNone(template_id)
        self.assertGreater(template_id, 0)

    def test_get_prompt_templates(self):
        """Test getting prompt templates"""
        self.db.add_prompt_template("review", "Template 1")
        self.db.add_prompt_template("describe", "Template 2")

        templates = self.db.get_prompt_templates()
        self.assertEqual(len(templates), 2)

        # Filter by command
        review_templates = self.db.get_prompt_templates(command="review")
        self.assertEqual(len(review_templates), 1)

    def test_get_statistics(self):
        """Test getting statistics"""
        repo_id = self.db.add_repository("PROJ", "test-repo")
        self.db.add_pr_review(repo_id, 1, "PR 1", "user", "url", ["/review"], "completed")
        self.db.add_pr_review(repo_id, 2, "PR 2", "user", "url", ["/review"], "pending")

        stats = self.db.get_statistics()

        self.assertEqual(stats['total_repositories'], 1)
        self.assertEqual(stats['total_reviews'], 2)
        self.assertIn('completed', stats['reviews_by_status'])
        self.assertIn('pending', stats['reviews_by_status'])


if __name__ == "__main__":
    unittest.main()
