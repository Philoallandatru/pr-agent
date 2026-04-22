"""Tests for code review quality scoring system."""

import pytest
from datetime import datetime, timezone, timedelta
from pr_agent.quality_scoring import (
    QualityScorer,
    ReviewScore,
    ReviewerRating,
    QualityTrend,
    ScoreCategory,
    QualityMetric
)


@pytest.fixture
def scorer():
    """Create a quality scorer instance."""
    return QualityScorer()


@pytest.fixture
def sample_review_data():
    """Sample review data for testing."""
    return {
        'files_changed': 10,
        'files_reviewed': 8,
        'comments_count': 15,
        'comment_depth': 120,
        'time_to_review': 20,
        'issues_found': 5,
        'issues_resolved': 4,
        'discussion_threads': 3
    }


class TestReviewScore:
    """Test ReviewScore dataclass."""

    def test_create_review_score(self):
        """Test creating a review score."""
        score = ReviewScore(
            review_id="review-1",
            reviewer_id="reviewer-1",
            overall_score=85.5,
            metric_scores={
                'coverage': 80.0,
                'depth': 90.0
            },
            category=ScoreCategory.GOOD,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        assert score.review_id == "review-1"
        assert score.reviewer_id == "reviewer-1"
        assert score.overall_score == 85.5
        assert score.category == ScoreCategory.GOOD

    def test_invalid_overall_score(self):
        """Test that invalid overall scores raise ValueError."""
        with pytest.raises(ValueError, match="Overall score must be between 0 and 100"):
            ReviewScore(
                review_id="review-1",
                reviewer_id="reviewer-1",
                overall_score=150.0,
                metric_scores={},
                category=ScoreCategory.GOOD,
                timestamp=datetime.now(timezone.utc).isoformat()
            )

    def test_invalid_metric_score(self):
        """Test that invalid metric scores raise ValueError."""
        with pytest.raises(ValueError, match="Metric score for .* must be between 0 and 100"):
            ReviewScore(
                review_id="review-1",
                reviewer_id="reviewer-1",
                overall_score=85.0,
                metric_scores={'coverage': 150.0},
                category=ScoreCategory.GOOD,
                timestamp=datetime.now(timezone.utc).isoformat()
            )


class TestQualityScorer:
    """Test QualityScorer class."""

    def test_score_review(self, scorer, sample_review_data):
        """Test scoring a review."""
        score = scorer.score_review(
            review_id="review-1",
            reviewer_id="reviewer-1",
            review_data=sample_review_data
        )

        assert score.review_id == "review-1"
        assert score.reviewer_id == "reviewer-1"
        assert 0 <= score.overall_score <= 100
        assert len(score.metric_scores) == 5
        assert score.category in ScoreCategory
        assert len(score.feedback) > 0

    def test_coverage_score_calculation(self, scorer):
        """Test coverage score calculation."""
        # 100% coverage
        score = scorer._calculate_coverage_score({
            'files_changed': 10,
            'files_reviewed': 10
        })
        assert score == 100.0

        # 50% coverage
        score = scorer._calculate_coverage_score({
            'files_changed': 10,
            'files_reviewed': 5
        })
        assert score == 50.0

        # No files changed
        score = scorer._calculate_coverage_score({
            'files_changed': 0,
            'files_reviewed': 0
        })
        assert score == 100.0

    def test_depth_score_calculation(self, scorer):
        """Test depth score calculation."""
        # Good depth
        score = scorer._calculate_depth_score({
            'comments_count': 10,
            'comment_depth': 150
        })
        assert score > 70

        # Poor depth
        score = scorer._calculate_depth_score({
            'comments_count': 1,
            'comment_depth': 20
        })
        assert score < 30

    def test_timeliness_score_calculation(self, scorer):
        """Test timeliness score calculation."""
        # Very fast (within 24 hours)
        score = scorer._calculate_timeliness_score({'time_to_review': 12})
        assert score == 100.0

        # Moderate (48 hours)
        score = scorer._calculate_timeliness_score({'time_to_review': 48})
        assert score == 80.0

        # Slow (1 week)
        score = scorer._calculate_timeliness_score({'time_to_review': 168})
        assert score == 40.0

        # Very slow (2 weeks)
        score = scorer._calculate_timeliness_score({'time_to_review': 336})
        assert score == 20.0

    def test_effectiveness_score_calculation(self, scorer):
        """Test effectiveness score calculation."""
        # All issues resolved
        score = scorer._calculate_effectiveness_score({
            'issues_found': 5,
            'issues_resolved': 5
        })
        assert score >= 90

        # Half resolved
        score = scorer._calculate_effectiveness_score({
            'issues_found': 10,
            'issues_resolved': 5
        })
        assert 50 < score < 80

        # No issues found
        score = scorer._calculate_effectiveness_score({
            'issues_found': 0,
            'issues_resolved': 0
        })
        assert score == 70.0

    def test_engagement_score_calculation(self, scorer):
        """Test engagement score calculation."""
        # High engagement
        score = scorer._calculate_engagement_score({
            'discussion_threads': 5,
            'comments_count': 20
        })
        assert score > 80

        # Low engagement
        score = scorer._calculate_engagement_score({
            'discussion_threads': 0,
            'comments_count': 1
        })
        assert score < 20

    def test_score_categorization(self, scorer):
        """Test score categorization."""
        assert scorer._categorize_score(95) == ScoreCategory.EXCELLENT
        assert scorer._categorize_score(85) == ScoreCategory.GOOD
        assert scorer._categorize_score(65) == ScoreCategory.FAIR
        assert scorer._categorize_score(45) == ScoreCategory.POOR

    def test_feedback_generation(self, scorer):
        """Test feedback generation."""
        metric_scores = {
            'coverage': 50.0,
            'depth': 90.0,
            'timeliness': 80.0,
            'effectiveness': 70.0,
            'engagement': 60.0
        }

        feedback = scorer._generate_feedback(metric_scores, 70.0)

        assert len(feedback) > 0
        assert any('coverage' in f.lower() for f in feedback)

    def test_multiple_reviews_stored(self, scorer, sample_review_data):
        """Test that multiple reviews are stored correctly."""
        scorer.score_review("review-1", "reviewer-1", sample_review_data)
        scorer.score_review("review-2", "reviewer-1", sample_review_data)
        scorer.score_review("review-3", "reviewer-2", sample_review_data)

        assert len(scorer.reviews) == 3
        assert len(scorer.reviewer_stats["reviewer-1"]) == 2
        assert len(scorer.reviewer_stats["reviewer-2"]) == 1


class TestReviewerRating:
    """Test reviewer rating functionality."""

    def test_get_reviewer_rating(self, scorer, sample_review_data):
        """Test getting reviewer rating."""
        # Score multiple reviews
        for i in range(5):
            scorer.score_review(f"review-{i}", "reviewer-1", sample_review_data)

        rating = scorer.get_reviewer_rating("reviewer-1")

        assert rating is not None
        assert rating.reviewer_id == "reviewer-1"
        assert rating.total_reviews == 5
        assert 0 <= rating.average_score <= 100
        assert len(rating.metric_averages) == 5
        assert rating.category in ScoreCategory
        assert rating.trend in ["improving", "stable", "declining"]

    def test_get_rating_no_reviews(self, scorer):
        """Test getting rating for reviewer with no reviews."""
        rating = scorer.get_reviewer_rating("unknown-reviewer")
        assert rating is None

    def test_trend_calculation_improving(self, scorer):
        """Test trend calculation for improving scores."""
        # Create improving trend
        scores = [60.0, 65.0, 70.0, 75.0, 80.0, 85.0]
        trend = scorer._calculate_trend(scores)
        assert trend == "improving"

    def test_trend_calculation_declining(self, scorer):
        """Test trend calculation for declining scores."""
        # Create declining trend
        scores = [85.0, 80.0, 75.0, 70.0, 65.0, 60.0]
        trend = scorer._calculate_trend(scores)
        assert trend == "declining"

    def test_trend_calculation_stable(self, scorer):
        """Test trend calculation for stable scores."""
        # Create stable trend
        scores = [75.0, 76.0, 74.0, 75.0, 76.0, 75.0]
        trend = scorer._calculate_trend(scores)
        assert trend == "stable"

    def test_trend_calculation_insufficient_data(self, scorer):
        """Test trend calculation with insufficient data."""
        scores = [75.0, 80.0]
        trend = scorer._calculate_trend(scores)
        assert trend == "stable"


class TestReviewerRanking:
    """Test reviewer ranking functionality."""

    def test_rank_reviewers(self, scorer, sample_review_data):
        """Test ranking reviewers."""
        # Create reviews with different quality
        high_quality = {**sample_review_data, 'files_reviewed': 10, 'comments_count': 20}
        medium_quality = sample_review_data
        low_quality = {**sample_review_data, 'files_reviewed': 3, 'comments_count': 2}

        # Score reviews for different reviewers
        for i in range(3):
            scorer.score_review(f"review-h{i}", "reviewer-high", high_quality)
            scorer.score_review(f"review-m{i}", "reviewer-medium", medium_quality)
            scorer.score_review(f"review-l{i}", "reviewer-low", low_quality)

        rankings = scorer.rank_reviewers()

        assert len(rankings) == 3
        assert rankings[0].rank == 1
        assert rankings[1].rank == 2
        assert rankings[2].rank == 3
        assert rankings[0].average_score > rankings[1].average_score
        assert rankings[1].average_score > rankings[2].average_score
        assert rankings[0].percentile > rankings[2].percentile

    def test_rank_empty(self, scorer):
        """Test ranking with no reviewers."""
        rankings = scorer.rank_reviewers()
        assert len(rankings) == 0


class TestQualityTrend:
    """Test quality trend analysis."""

    def test_analyze_quality_trend(self, scorer, sample_review_data):
        """Test analyzing quality trends."""
        # Create reviews over time
        for i in range(10):
            scorer.score_review(f"review-{i}", "reviewer-1", sample_review_data)

        trend = scorer.analyze_quality_trend(
            metric=QualityMetric.COVERAGE,
            period="weekly",
            days=30
        )

        assert trend.metric == QualityMetric.COVERAGE.value
        assert trend.period == "weekly"
        assert len(trend.data_points) == 10
        assert 0 <= trend.average <= 100
        assert trend.trend_direction in ["up", "down", "stable"]

    def test_analyze_trend_no_data(self, scorer):
        """Test analyzing trends with no data."""
        trend = scorer.analyze_quality_trend(
            metric=QualityMetric.DEPTH,
            period="daily",
            days=7
        )

        assert len(trend.data_points) == 0
        assert trend.average == 0.0
        assert trend.trend_direction == "stable"
        assert trend.change_percentage == 0.0

    def test_analyze_trend_upward(self, scorer):
        """Test detecting upward trend."""
        # Create improving scores over time
        for i in range(10):
            data = {
                'files_changed': 10,
                'files_reviewed': 5 + i,  # Increasing coverage
                'comments_count': 10,
                'comment_depth': 100,
                'time_to_review': 24,
                'issues_found': 3,
                'issues_resolved': 3,
                'discussion_threads': 2
            }
            scorer.score_review(f"review-{i}", "reviewer-1", data)

        trend = scorer.analyze_quality_trend(
            metric=QualityMetric.COVERAGE,
            period="daily",
            days=30
        )

        assert trend.trend_direction == "up"
        assert trend.change_percentage > 0


class TestImprovementSuggestions:
    """Test improvement suggestions."""

    def test_get_improvement_suggestions(self, scorer, sample_review_data):
        """Test getting improvement suggestions."""
        # Score some reviews
        for i in range(3):
            scorer.score_review(f"review-{i}", "reviewer-1", sample_review_data)

        suggestions = scorer.get_improvement_suggestions("reviewer-1")

        assert len(suggestions) > 0
        assert isinstance(suggestions[0], str)

    def test_suggestions_no_reviews(self, scorer):
        """Test suggestions for reviewer with no reviews."""
        suggestions = scorer.get_improvement_suggestions("unknown-reviewer")

        assert len(suggestions) == 1
        assert "No review history" in suggestions[0]

    def test_suggestions_low_coverage(self, scorer):
        """Test suggestions for low coverage."""
        data = {
            'files_changed': 10,
            'files_reviewed': 2,  # Low coverage
            'comments_count': 10,
            'comment_depth': 100,
            'time_to_review': 24,
            'issues_found': 3,
            'issues_resolved': 3,
            'discussion_threads': 2
        }

        for i in range(3):
            scorer.score_review(f"review-{i}", "reviewer-1", data)

        suggestions = scorer.get_improvement_suggestions("reviewer-1")

        assert any('coverage' in s.lower() for s in suggestions)

    def test_suggestions_declining_trend(self, scorer):
        """Test suggestions for declining trend."""
        # Create declining scores
        for i in range(6):
            data = {
                'files_changed': 10,
                'files_reviewed': 10 - i,  # Declining
                'comments_count': 15 - i,
                'comment_depth': 120 - i * 10,
                'time_to_review': 24,
                'issues_found': 5,
                'issues_resolved': 4,
                'discussion_threads': 3
            }
            scorer.score_review(f"review-{i}", "reviewer-1", data)

        suggestions = scorer.get_improvement_suggestions("reviewer-1")

        assert any('declining' in s.lower() for s in suggestions)

    def test_suggestions_excellent_performance(self, scorer):
        """Test suggestions for excellent performance."""
        data = {
            'files_changed': 10,
            'files_reviewed': 10,
            'comments_count': 25,
            'comment_depth': 150,
            'time_to_review': 12,
            'issues_found': 8,
            'issues_resolved': 8,
            'discussion_threads': 5
        }

        for i in range(3):
            scorer.score_review(f"review-{i}", "reviewer-1", data)

        suggestions = scorer.get_improvement_suggestions("reviewer-1")

        assert any('excellent' in s.lower() or 'great' in s.lower() for s in suggestions)
