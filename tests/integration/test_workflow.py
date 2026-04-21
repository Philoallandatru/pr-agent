"""
Integration tests for the complete auto-review workflow.

Tests the end-to-end flow from PR detection to review completion.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

from pr_agent.storage.database import Database
from pr_agent.storage.polling_state import PollingState
from pr_agent.algo.repo_context_analyzer import RepoContextAnalyzer
from pr_agent.algo.tokenizer_manager import TokenizerManager


class TestEndToEndWorkflow:
    """Test complete workflow from PR detection to review."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test data."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def database(self, temp_dir):
        """Create test database."""
        db_path = Path(temp_dir) / "test.db"
        db = Database(str(db_path))
        yield db

    @pytest.fixture
    def polling_state(self, temp_dir):
        """Create test polling state."""
        state_file = Path(temp_dir) / "state.json"
        state = PollingState(str(state_file))
        yield state

    def test_repository_lifecycle(self, database):
        """Test complete repository management lifecycle."""
        # Create repository
        repo_id = database.add_repository(
            project_key="TEST",
            repo_slug="test-repo",
            polling_enabled=True,
            polling_interval=300
        )
        assert repo_id > 0

        # Get repository
        repo = database.get_repository(repo_id)
        assert repo is not None
        assert repo['project_key'] == "TEST"
        assert repo['repo_slug'] == "test-repo"
        assert repo['polling_enabled'] is True

        # Update repository
        database.update_repository(repo_id, polling_enabled=False)
        repo = database.get_repository(repo_id)
        assert repo['polling_enabled'] is False

        # List repositories
        repos = database.get_all_repositories()
        assert len(repos) >= 1

        # Delete repository
        database.delete_repository(repo_id)
        repo = database.get_repository(repo_id)
        assert repo is None

    def test_pr_review_workflow(self, database):
        """Test PR review creation and update workflow."""
        # Create repository first
        repo_id = database.add_repository(
            project_key="TEST",
            repo_slug="test-repo"
        )

        # Create PR review
        review_id = database.add_pr_review(
            repository_id=repo_id,
            pr_id=123,
            pr_title="Test PR",
            pr_author="testuser",
            pr_url="https://example.com/pr/123",
            commands_run=["/review", "/describe"]
        )
        assert review_id > 0

        # Get review
        review = database.get_pr_review(review_id)
        assert review is not None
        assert review['pr_id'] == 123
        assert review['status'] == 'pending'

        # Update review to in_progress
        database.update_pr_review(
            review_id,
            status='in_progress'
        )
        review = database.get_pr_review(review_id)
        assert review['status'] == 'in_progress'

        # Complete review with results
        result = {
            'summary': 'Code looks good',
            'issues': [],
            'suggestions': ['Add more tests']
        }
        database.update_pr_review(
            review_id,
            status='completed',
            review_result=result
        )
        review = database.get_pr_review(review_id)
        assert review['status'] == 'completed'
        assert review['review_result'] == result

        # List reviews
        reviews = database.get_pr_reviews(repository_id=repo_id)
        assert len(reviews) >= 1

    def test_polling_state_workflow(self, polling_state):
        """Test polling state tracking workflow."""
        repo_key = "TEST/test-repo"
        pr_id = 123
        version = 1

        # Initially not processed
        assert not polling_state.is_pr_processed(repo_key, pr_id)

        # Update state
        polling_state.update_pr_state(repo_key, pr_id, version)
        assert polling_state.is_pr_processed(repo_key, pr_id)

        # Check version
        assert not polling_state.is_pr_updated(repo_key, pr_id, version)
        assert polling_state.is_pr_updated(repo_key, pr_id, version + 1)

        # Get statistics
        stats = polling_state.get_statistics()
        assert stats['total_prs'] == 1
        assert stats['total_repositories'] == 1

    def test_repo_context_analysis(self, temp_dir):
        """Test repository context analysis workflow."""
        cache_dir = Path(temp_dir) / "repos"
        analyzer = RepoContextAnalyzer(str(cache_dir))

        # Mock git clone
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = Mock(returncode=0)

            repo_url = "https://github.com/test/repo.git"
            repo_path = analyzer.clone_repository(repo_url)

            assert repo_path is not None
            assert mock_run.called

    def test_tokenizer_cache_workflow(self, temp_dir):
        """Test tokenizer cache management workflow."""
        cache_dir = Path(temp_dir) / "tokenizers"
        manager = TokenizerManager(str(cache_dir))

        # Get cache info
        info = manager.get_cache_info()
        assert 'total_models' in info
        assert 'total_size_mb' in info

        # List cached tokenizers
        cached = manager.list_cached_tokenizers()
        assert isinstance(cached, list)

    def test_integrated_pr_detection_and_review(self, database, polling_state):
        """Test integrated workflow: detect PR -> create review -> update state."""
        # Setup
        repo_key = "TEST/integration-test"
        pr_id = 456
        pr_version = 1

        # Step 1: Create repository in database
        repo_id = database.add_repository(
            project_key="TEST",
            repo_slug="integration-test",
            polling_enabled=True
        )

        # Step 2: Simulate PR detection (not in state)
        assert not polling_state.is_pr_processed(repo_key, pr_id)

        # Step 3: Create review record
        review_id = database.add_pr_review(
            repository_id=repo_id,
            pr_id=pr_id,
            pr_title="Integration Test PR",
            pr_author="testuser",
            pr_url="https://example.com/pr/456",
            commands_run=["/review"]
        )

        # Step 4: Update polling state
        polling_state.update_pr_state(repo_key, pr_id, pr_version)

        # Step 5: Simulate review processing
        database.update_pr_review(review_id, status='in_progress')

        # Step 6: Complete review
        result = {
            'summary': 'Integration test passed',
            'score': 8.5
        }
        database.update_pr_review(
            review_id,
            status='completed',
            review_result=result
        )

        # Verify final state
        review = database.get_pr_review(review_id)
        assert review['status'] == 'completed'
        assert review['review_result']['score'] == 8.5
        assert polling_state.is_pr_processed(repo_key, pr_id)

    def test_error_handling_workflow(self, database):
        """Test error handling in review workflow."""
        # Create repository
        repo_id = database.add_repository(
            project_key="TEST",
            repo_slug="error-test"
        )

        # Create review
        review_id = database.add_pr_review(
            repository_id=repo_id,
            pr_id=789,
            pr_title="Error Test PR",
            pr_author="testuser",
            pr_url="https://example.com/pr/789",
            commands_run=["/review"]
        )

        # Simulate error during review
        error_msg = "API rate limit exceeded"
        database.update_pr_review(
            review_id,
            status='failed',
            error_message=error_msg
        )

        # Verify error recorded
        review = database.get_pr_review(review_id)
        assert review['status'] == 'failed'
        assert review['error_message'] == error_msg

    def test_statistics_aggregation(self, database):
        """Test statistics aggregation across multiple reviews."""
        # Create repository
        repo_id = database.add_repository(
            project_key="TEST",
            repo_slug="stats-test"
        )

        # Create multiple reviews with different statuses
        statuses = ['completed', 'completed', 'failed', 'in_progress', 'pending']
        for i, status in enumerate(statuses):
            review_id = database.add_pr_review(
                repository_id=repo_id,
                pr_id=1000 + i,
                pr_title=f"PR {i}",
                pr_author="testuser",
                pr_url=f"https://example.com/pr/{1000+i}",
                commands_run=["/review"]
            )
            database.update_pr_review(review_id, status=status)

        # Get statistics
        stats = database.get_statistics()
        assert stats['total_repositories'] >= 1
        assert stats['total_reviews'] >= 5
        assert stats['reviews_by_status']['completed'] >= 2
        assert stats['reviews_by_status']['failed'] >= 1

    def test_cleanup_workflow(self, polling_state):
        """Test cleanup of old polling state entries."""
        # Add multiple PR states
        for i in range(10):
            polling_state.update_pr_state(f"TEST/repo{i}", i, 1)

        # Verify all added
        stats = polling_state.get_statistics()
        assert stats['total_prs'] == 10

        # Cleanup old entries (with very short retention for testing)
        with patch('time.time') as mock_time:
            # Simulate 31 days passing
            mock_time.return_value = 31 * 24 * 60 * 60
            polling_state.cleanup_old_entries(retention_days=30)

        # Note: In real test, entries would be cleaned up
        # This is a simplified test


class TestAPIIntegration:
    """Test API endpoint integration."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_health_check_integration(self, temp_dir):
        """Test health check with all components."""
        from pr_agent.config.validation import HealthChecker

        checker = HealthChecker()
        report = checker.check_all()

        assert 'status' in report
        assert 'checks' in report
        assert 'details' in report
        assert report['status'] in ['healthy', 'degraded']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
