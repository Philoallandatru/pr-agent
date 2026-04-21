"""
Unit tests for database query optimizer.
"""

import pytest
import tempfile
import os
from pathlib import Path

from pr_agent.storage.database import Database
from pr_agent.storage.db_optimizer import QueryOptimizer, CachedDatabase


class TestQueryOptimizer:
    """Test QueryOptimizer functionality."""

    @pytest.fixture
    def db(self):
        """Create temporary database."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
            db_path = f.name

        database = Database(db_path)
        yield database

        database.close()
        os.unlink(db_path)

    @pytest.fixture
    def optimizer(self, db):
        """Create query optimizer."""
        return QueryOptimizer(db)

    def test_query_stats_tracking(self, optimizer):
        """Test query performance tracking."""
        # Simulate some queries
        optimizer._track_query("get_repository", 0.1)
        optimizer._track_query("get_repository", 0.2)
        optimizer._track_query("get_pr_reviews", 0.5)

        stats = optimizer.get_query_stats()

        assert "get_repository" in stats
        assert stats["get_repository"]["count"] == 2
        assert stats["get_repository"]["min_time"] == 0.1
        assert stats["get_repository"]["max_time"] == 0.2
        assert abs(stats["get_repository"]["avg_time"] - 0.15) < 0.001

        assert "get_pr_reviews" in stats
        assert stats["get_pr_reviews"]["count"] == 1

    def test_analyze_indexes(self, optimizer):
        """Test index analysis."""
        suggestions = optimizer.analyze_indexes()
        assert isinstance(suggestions, list)

    def test_add_missing_indexes(self, optimizer):
        """Test adding performance indexes."""
        optimizer.add_missing_indexes()

        # Verify indexes were created
        cursor = optimizer.db.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]

        # Check for some expected indexes
        assert "idx_pr_reviews_pr_id" in indexes
        assert "idx_pr_reviews_created_at" in indexes
        assert "idx_system_logs_level" in indexes

    def test_optimize_database(self, optimizer):
        """Test database optimization."""
        # Should not raise any errors
        optimizer.optimize_database()


class TestCachedDatabase:
    """Test CachedDatabase wrapper."""

    @pytest.fixture
    def db(self):
        """Create temporary database."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
            db_path = f.name

        database = Database(db_path)
        yield database

        database.close()
        os.unlink(db_path)

    @pytest.fixture
    def cached_db(self, db):
        """Create cached database wrapper."""
        return CachedDatabase(db)

    def test_cached_get_repository(self, cached_db):
        """Test cached repository retrieval."""
        # Add a repository
        repo_id = cached_db.add_repository("PROJ", "repo1")

        # First call - from database
        repo1 = cached_db.get_repository(repo_id)
        assert repo1 is not None
        assert repo1["project_key"] == "PROJ"

        # Second call - from cache
        repo2 = cached_db.get_repository(repo_id)
        assert repo2 == repo1

    def test_cached_get_all_repositories(self, cached_db):
        """Test cached repository list."""
        # Add repositories
        cached_db.add_repository("PROJ1", "repo1")
        cached_db.add_repository("PROJ2", "repo2")

        # First call
        repos1 = cached_db.get_all_repositories()
        assert len(repos1) == 2

        # Second call - from cache
        repos2 = cached_db.get_all_repositories()
        assert repos2 == repos1

    def test_cached_get_statistics(self, cached_db):
        """Test cached statistics."""
        # Add some data
        repo_id = cached_db.add_repository("PROJ", "repo1")
        cached_db.add_pr_review(
            repo_id, 1, "Test PR", "author", "http://url",
            ["review"], "pending"
        )

        # First call
        stats1 = cached_db.get_statistics()
        assert stats1["total_repositories"] == 1
        assert stats1["total_reviews"] == 1

        # Second call - from cache
        stats2 = cached_db.get_statistics()
        assert stats2 == stats1

    def test_invalidate_repository_cache(self, cached_db):
        """Test cache invalidation for repositories."""
        repo_id = cached_db.add_repository("PROJ", "repo1")

        # Cache the repository
        cached_db.get_repository(repo_id)

        # Update repository
        cached_db.update_repository(repo_id, polling_enabled=False)

        # Invalidate cache
        cached_db.invalidate_repository_cache(repo_id)

        # Next call should fetch fresh data
        repo = cached_db.get_repository(repo_id)
        assert repo["polling_enabled"] == 0  # SQLite stores bool as int

    def test_invalidate_reviews_cache(self, cached_db):
        """Test cache invalidation for reviews."""
        repo_id = cached_db.add_repository("PROJ", "repo1")

        # Cache reviews
        cached_db.get_pr_reviews(repository_id=repo_id)

        # Add new review
        cached_db.add_pr_review(
            repo_id, 1, "Test PR", "author", "http://url",
            ["review"], "pending"
        )

        # Invalidate cache
        cached_db.invalidate_reviews_cache(repo_id)

        # Next call should fetch fresh data
        reviews = cached_db.get_pr_reviews(repository_id=repo_id)
        assert len(reviews) == 1

    def test_invalidate_stats_cache(self, cached_db):
        """Test cache invalidation for statistics."""
        # Cache statistics
        cached_db.get_statistics()

        # Add new data
        cached_db.add_repository("PROJ", "repo1")

        # Invalidate cache
        cached_db.invalidate_stats_cache()

        # Next call should fetch fresh data
        stats = cached_db.get_statistics()
        assert stats["total_repositories"] == 1

    def test_delegate_methods(self, cached_db):
        """Test that unknown methods are delegated to underlying database."""
        # These methods should work through delegation
        repo_id = cached_db.add_repository("PROJ", "repo1")
        cached_db.delete_repository(repo_id)

        repos = cached_db.get_all_repositories()
        assert len(repos) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
