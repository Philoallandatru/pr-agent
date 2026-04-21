"""
Unit tests for analytics engine.
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta

from pr_agent.storage.database import Database
from pr_agent.analytics.engine import AnalyticsEngine


class TestAnalyticsEngine:
    """Test AnalyticsEngine functionality."""

    @pytest.fixture
    def db(self):
        """Create temporary database with test data."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
            db_path = f.name

        database = Database(db_path)

        # Add test repositories
        repo1_id = database.add_repository("PROJ1", "repo1")
        repo2_id = database.add_repository("PROJ2", "repo2")

        # Add test reviews
        now = datetime.now()
        for i in range(10):
            date = now - timedelta(days=i)
            database.add_pr_review(
                repo1_id,
                100 + i,
                f"Test PR {i}",
                f"author{i % 3}",
                f"http://url/{i}",
                ["/review"],
                "completed" if i % 4 != 0 else "failed"
            )

            # Update completed reviews with completion time
            if i % 4 != 0:
                cursor = database.conn.cursor()
                cursor.execute("""
                    UPDATE pr_reviews
                    SET completed_at = datetime(created_at, '+2 hours')
                    WHERE pr_id = ?
                """, (100 + i,))
                database.conn.commit()

        yield database

        database.close()
        os.unlink(db_path)

    @pytest.fixture
    def engine(self, db):
        """Create analytics engine."""
        return AnalyticsEngine(db)

    def test_get_code_quality_trends(self, engine):
        """Test code quality trends analysis."""
        trends = engine.get_code_quality_trends(days=30)

        assert "period" in trends
        assert "daily_data" in trends
        assert "summary" in trends

        summary = trends["summary"]
        assert summary["total_reviews"] == 10
        assert summary["completed_reviews"] == 7  # 3 failed
        assert summary["failed_reviews"] == 3
        assert 0 <= summary["success_rate"] <= 100

    def test_get_code_quality_trends_with_filter(self, engine, db):
        """Test trends with repository filter."""
        # Get first repository ID
        repos = db.get_all_repositories()
        repo_id = repos[0]["id"]

        trends = engine.get_code_quality_trends(repository_id=repo_id, days=30)

        assert trends["summary"]["total_reviews"] == 10

    def test_get_team_efficiency_metrics(self, engine):
        """Test team efficiency metrics."""
        metrics = engine.get_team_efficiency_metrics(days=30)

        assert "period" in metrics
        assert "summary" in metrics
        assert "top_authors" in metrics
        assert "hourly_distribution" in metrics

        summary = metrics["summary"]
        assert summary["total_reviews"] == 10
        assert summary["unique_authors"] == 3
        assert summary["reviews_per_author"] > 0

    def test_get_review_quality_score(self, engine):
        """Test review quality scoring."""
        score = engine.get_review_quality_score(days=30)

        assert "overall_score" in score
        assert "grade" in score
        assert "components" in score

        assert 0 <= score["overall_score"] <= 100
        assert score["grade"] in ["A", "B", "C", "D", "F"]

        # Check components
        components = score["components"]
        assert "success" in components
        assert "speed" in components
        assert "coverage" in components

        for component in components.values():
            assert "score" in component
            assert "weight" in component
            assert "metrics" in component

    def test_get_repository_comparison(self, engine):
        """Test repository comparison."""
        comparison = engine.get_repository_comparison(days=30)

        assert isinstance(comparison, list)
        assert len(comparison) == 2  # Two repositories

        for repo in comparison:
            assert "repository_id" in repo
            assert "repository" in repo
            assert "total_reviews" in repo
            assert "success_rate" in repo

    def test_generate_custom_report_summary(self, engine):
        """Test summary report generation."""
        report = engine.generate_custom_report("summary", {"days": 30})

        assert report["type"] == "summary"
        assert "generated_at" in report
        assert "quality_trends" in report
        assert "efficiency_metrics" in report
        assert "quality_score" in report

    def test_generate_custom_report_detailed(self, engine):
        """Test detailed report generation."""
        report = engine.generate_custom_report("detailed", {"days": 30})

        assert report["type"] == "detailed"
        assert "repository_comparison" in report

    def test_generate_custom_report_comparison(self, engine):
        """Test comparison report generation."""
        report = engine.generate_custom_report("comparison", {"days": 30})

        assert report["type"] == "comparison"
        assert "repositories" in report
        assert len(report["repositories"]) == 2

    def test_generate_custom_report_invalid_type(self, engine):
        """Test invalid report type."""
        with pytest.raises(ValueError):
            engine.generate_custom_report("invalid_type")

    def test_get_overview(self, engine):
        """Test analytics overview."""
        overview = engine.get_overview(days=30)

        assert "generated_at" in overview
        assert "period_days" in overview
        assert "quality_score" in overview
        assert "efficiency" in overview
        assert "trends" in overview

    def test_get_trends(self, engine):
        """Test trend data extraction."""
        # Test review count trend
        trends = engine.get_trends("review_count", days=30)
        assert trends["metric"] == "review_count"
        assert "data" in trends
        assert len(trends["data"]) > 0

        # Test success rate trend
        trends = engine.get_trends("success_rate", days=30)
        assert trends["metric"] == "success_rate"

        # Test duration trend
        trends = engine.get_trends("duration", days=30)
        assert trends["metric"] == "duration"

    def test_get_trends_invalid_metric(self, engine):
        """Test invalid metric."""
        with pytest.raises(ValueError):
            engine.get_trends("invalid_metric")

    def test_get_repository_analytics(self, engine, db):
        """Test repository-specific analytics."""
        repos = db.get_all_repositories()
        repo_id = repos[0]["id"]

        analytics = engine.get_repository_analytics(repo_id, days=30)

        assert analytics["repository_id"] == repo_id
        assert "generated_at" in analytics
        assert "quality_trends" in analytics
        assert "efficiency_metrics" in analytics
        assert "quality_score" in analytics

    def test_generate_report_json(self, engine):
        """Test JSON report generation."""
        report = engine.generate_report(format="json")

        assert isinstance(report, dict)
        assert report["type"] == "comprehensive"
        assert "period" in report
        assert "quality_trends" in report

    def test_generate_report_csv(self, engine):
        """Test CSV report generation."""
        report = engine.generate_report(format="csv")

        assert isinstance(report, str)
        assert "PR-Agent Analytics Report" in report
        assert "Quality Score" in report

    def test_generate_report_text(self, engine):
        """Test text report generation."""
        report = engine.generate_report(format="text")

        assert isinstance(report, str)
        assert "PR-Agent Analytics Report" in report
        assert "Overall Quality Score" in report
        assert "Summary:" in report

    def test_generate_report_invalid_format(self, engine):
        """Test invalid report format."""
        with pytest.raises(ValueError):
            engine.generate_report(format="invalid")

    def test_generate_report_with_dates(self, engine):
        """Test report generation with custom date range."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        report = engine.generate_report(
            start_date=start_date,
            end_date=end_date,
            format="json"
        )

        assert report["period"]["days"] == 7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
