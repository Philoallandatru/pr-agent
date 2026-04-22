"""
Tests for Code Review Metrics Collector
"""

import pytest
from datetime import datetime, timezone, timedelta
from pr_agent.metrics import (
    MetricsCollector,
    ReviewMetrics,
    TimeRange,
)


@pytest.fixture
def collector(tmp_path):
    """Create metrics collector with temp storage"""
    return MetricsCollector(storage_path=str(tmp_path))


class TestReviewMetrics:
    """Test ReviewMetrics data class"""

    def test_create_review_metrics(self):
        """Test creating review metrics"""
        metrics = ReviewMetrics(
            review_id="rev-1",
            pr_id="PR-123",
            repository="test/repo",
            author="alice",
            reviewers=["bob", "charlie"],
            created_at=datetime.now(timezone.utc).isoformat(),
            lines_added=100,
            lines_deleted=50,
            files_changed=5
        )

        assert metrics.review_id == "rev-1"
        assert metrics.pr_id == "PR-123"
        assert len(metrics.reviewers) == 2


class TestMetricsCollector:
    """Test MetricsCollector"""

    def test_record_review(self, collector):
        """Test recording a review"""
        metrics = ReviewMetrics(
            review_id="rev-1",
            pr_id="PR-123",
            repository="test/repo",
            author="alice",
            reviewers=["bob"],
            created_at=datetime.now(timezone.utc).isoformat(),
            first_response_time_minutes=30.0,
            total_review_time_minutes=120.0,
            lines_added=100,
            lines_deleted=50,
            files_changed=5,
            comments_count=10,
            issues_found=3,
            suggestions_made=5,
            approved=True,
            merged=True
        )

        collector.record_review(metrics)
        assert "rev-1" in collector.reviews

    def test_update_review(self, collector):
        """Test updating review metrics"""
        metrics = ReviewMetrics(
            review_id="rev-1",
            pr_id="PR-123",
            repository="test/repo",
            author="alice",
            reviewers=["bob"],
            created_at=datetime.now(timezone.utc).isoformat()
        )

        collector.record_review(metrics)
        collector.update_review("rev-1", merged=True, time_to_merge_minutes=240.0)

        updated = collector.reviews["rev-1"]
        assert updated.merged is True
        assert updated.time_to_merge_minutes == 240.0

    def test_get_metrics_summary(self, collector):
        """Test getting metrics summary"""
        # Record multiple reviews
        for i in range(3):
            metrics = ReviewMetrics(
                review_id=f"rev-{i}",
                pr_id=f"PR-{i}",
                repository="test/repo",
                author="alice",
                reviewers=["bob"],
                created_at=datetime.now(timezone.utc).isoformat(),
                first_response_time_minutes=30.0 + i * 10,
                total_review_time_minutes=120.0 + i * 20,
                lines_added=100,
                lines_deleted=50,
                files_changed=5,
                comments_count=10 + i,
                issues_found=3 + i,
                suggestions_made=5,
                approved=True,
                merged=True
            )
            collector.record_review(metrics)

        summary = collector.get_metrics_summary(TimeRange.WEEK)

        assert summary.process.total_reviews == 3
        assert summary.efficiency.avg_first_response_time_minutes > 0
        assert summary.quality.avg_comments_per_review > 0
        assert summary.team.total_reviewers == 1

    def test_get_reviewer_metrics(self, collector):
        """Test getting reviewer-specific metrics"""
        # Record reviews for specific reviewer
        for i in range(2):
            metrics = ReviewMetrics(
                review_id=f"rev-{i}",
                pr_id=f"PR-{i}",
                repository="test/repo",
                author="alice",
                reviewers=["bob"],
                created_at=datetime.now(timezone.utc).isoformat(),
                first_response_time_minutes=30.0,
                comments_count=10,
                issues_found=3,
                approved=True
            )
            collector.record_review(metrics)

        stats = collector.get_reviewer_metrics("bob", TimeRange.WEEK)

        assert stats["reviewer"] == "bob"
        assert stats["reviews_count"] == 2
        assert stats["avg_response_time"] == 30.0
        assert stats["avg_comments"] == 10.0

    def test_get_author_metrics(self, collector):
        """Test getting author-specific metrics"""
        metrics = ReviewMetrics(
            review_id="rev-1",
            pr_id="PR-123",
            repository="test/repo",
            author="alice",
            reviewers=["bob"],
            created_at=datetime.now(timezone.utc).isoformat(),
            time_to_merge_minutes=240.0,
            iterations=2,
            lines_added=100,
            lines_deleted=50,
            files_changed=5,
            merged=True,
            issues_found=3
        )
        collector.record_review(metrics)

        stats = collector.get_author_metrics("alice", TimeRange.WEEK)

        assert stats["author"] == "alice"
        assert stats["prs_count"] == 1
        assert stats["avg_time_to_merge"] == 240.0
        assert stats["avg_iterations"] == 2.0

    def test_get_repository_metrics(self, collector):
        """Test getting repository-specific metrics"""
        for i in range(3):
            metrics = ReviewMetrics(
                review_id=f"rev-{i}",
                pr_id=f"PR-{i}",
                repository="test/repo",
                author=f"author{i}",
                reviewers=[f"reviewer{i}"],
                created_at=datetime.now(timezone.utc).isoformat(),
                total_review_time_minutes=120.0,
                lines_added=100,
                lines_deleted=50,
                merged=True
            )
            collector.record_review(metrics)

        stats = collector.get_repository_metrics("test/repo", TimeRange.WEEK)

        assert stats["repository"] == "test/repo"
        assert stats["reviews_count"] == 3
        assert stats["active_authors"] == 3
        assert stats["active_reviewers"] == 3

    def test_compare_periods(self, collector):
        """Test comparing metrics between periods"""
        # Record old reviews
        old_time = datetime.now(timezone.utc) - timedelta(days=60)
        for i in range(2):
            metrics = ReviewMetrics(
                review_id=f"old-{i}",
                pr_id=f"PR-old-{i}",
                repository="test/repo",
                author="alice",
                reviewers=["bob"],
                created_at=old_time.isoformat(),
                first_response_time_minutes=60.0,
                total_review_time_minutes=180.0,
                comments_count=5,
                issues_found=2,
                approved=True
            )
            collector.record_review(metrics)

        # Record recent reviews
        for i in range(2):
            metrics = ReviewMetrics(
                review_id=f"new-{i}",
                pr_id=f"PR-new-{i}",
                repository="test/repo",
                author="alice",
                reviewers=["bob"],
                created_at=datetime.now(timezone.utc).isoformat(),
                first_response_time_minutes=30.0,
                total_review_time_minutes=120.0,
                comments_count=10,
                issues_found=4,
                approved=True
            )
            collector.record_review(metrics)

        comparison = collector.compare_periods(TimeRange.QUARTER, TimeRange.MONTH)

        assert "efficiency" in comparison
        assert "quality" in comparison
        assert "team" in comparison

    def test_persistence(self, collector):
        """Test metrics persistence"""
        metrics = ReviewMetrics(
            review_id="rev-1",
            pr_id="PR-123",
            repository="test/repo",
            author="alice",
            reviewers=["bob"],
            created_at=datetime.now(timezone.utc).isoformat(),
            comments_count=10
        )

        collector.record_review(metrics)

        # Create new collector with same storage
        new_collector = MetricsCollector(storage_path=str(collector.storage_path))

        assert "rev-1" in new_collector.reviews
        assert new_collector.reviews["rev-1"].comments_count == 10

    def test_empty_metrics(self, collector):
        """Test handling empty metrics"""
        summary = collector.get_metrics_summary(TimeRange.WEEK)

        assert summary.process.total_reviews == 0
        assert summary.efficiency.avg_first_response_time_minutes == 0
        assert summary.quality.avg_comments_per_review == 0

    def test_filter_by_repository(self, collector):
        """Test filtering by repository"""
        # Record reviews for different repos
        for repo in ["repo1", "repo2"]:
            metrics = ReviewMetrics(
                review_id=f"rev-{repo}",
                pr_id=f"PR-{repo}",
                repository=repo,
                author="alice",
                reviewers=["bob"],
                created_at=datetime.now(timezone.utc).isoformat()
            )
            collector.record_review(metrics)

        summary = collector.get_metrics_summary(TimeRange.WEEK, repository="repo1")
        assert summary.process.total_reviews == 1

    def test_filter_by_author(self, collector):
        """Test filtering by author"""
        for author in ["alice", "bob"]:
            metrics = ReviewMetrics(
                review_id=f"rev-{author}",
                pr_id=f"PR-{author}",
                repository="test/repo",
                author=author,
                reviewers=["charlie"],
                created_at=datetime.now(timezone.utc).isoformat()
            )
            collector.record_review(metrics)

        summary = collector.get_metrics_summary(TimeRange.WEEK, author="alice")
        assert summary.process.total_reviews == 1

    def test_filter_by_reviewer(self, collector):
        """Test filtering by reviewer"""
        metrics1 = ReviewMetrics(
            review_id="rev-1",
            pr_id="PR-1",
            repository="test/repo",
            author="alice",
            reviewers=["bob"],
            created_at=datetime.now(timezone.utc).isoformat()
        )
        metrics2 = ReviewMetrics(
            review_id="rev-2",
            pr_id="PR-2",
            repository="test/repo",
            author="alice",
            reviewers=["charlie"],
            created_at=datetime.now(timezone.utc).isoformat()
        )

        collector.record_review(metrics1)
        collector.record_review(metrics2)

        summary = collector.get_metrics_summary(TimeRange.WEEK, reviewer="bob")
        assert summary.process.total_reviews == 1


class TestTimeRanges:
    """Test time range filtering"""

    def test_day_range(self, collector):
        """Test day time range"""
        metrics = ReviewMetrics(
            review_id="rev-1",
            pr_id="PR-1",
            repository="test/repo",
            author="alice",
            reviewers=["bob"],
            created_at=datetime.now(timezone.utc).isoformat()
        )
        collector.record_review(metrics)

        summary = collector.get_metrics_summary(TimeRange.DAY)
        assert summary.process.total_reviews == 1

    def test_week_range(self, collector):
        """Test week time range"""
        metrics = ReviewMetrics(
            review_id="rev-1",
            pr_id="PR-1",
            repository="test/repo",
            author="alice",
            reviewers=["bob"],
            created_at=(datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        )
        collector.record_review(metrics)

        summary = collector.get_metrics_summary(TimeRange.WEEK)
        assert summary.process.total_reviews == 1

    def test_month_range(self, collector):
        """Test month time range"""
        metrics = ReviewMetrics(
            review_id="rev-1",
            pr_id="PR-1",
            repository="test/repo",
            author="alice",
            reviewers=["bob"],
            created_at=(datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
        )
        collector.record_review(metrics)

        summary = collector.get_metrics_summary(TimeRange.MONTH)
        assert summary.process.total_reviews == 1
