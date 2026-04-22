"""
Code Review Quality Scoring System.

This module provides functionality to evaluate and score the quality of code reviews.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
import statistics


class ScoreCategory(Enum):
    """Review quality score categories."""
    EXCELLENT = "excellent"  # 90-100
    GOOD = "good"  # 75-89
    FAIR = "fair"  # 60-74
    POOR = "poor"  # 0-59


class QualityMetric(Enum):
    """Quality metrics for review scoring."""
    COVERAGE = "coverage"  # How much of the code was reviewed
    DEPTH = "depth"  # How thorough the review was
    TIMELINESS = "timeliness"  # How quickly the review was completed
    EFFECTIVENESS = "effectiveness"  # How useful the review was
    ENGAGEMENT = "engagement"  # Level of interaction and discussion


@dataclass
class ReviewScore:
    """Score for a single review."""
    review_id: str
    reviewer_id: str
    overall_score: float
    metric_scores: Dict[str, float]
    category: ScoreCategory
    timestamp: str
    feedback: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate score values."""
        if not 0 <= self.overall_score <= 100:
            raise ValueError("Overall score must be between 0 and 100")
        for metric, score in self.metric_scores.items():
            if not 0 <= score <= 100:
                raise ValueError(f"Metric score for {metric} must be between 0 and 100")


@dataclass
class ReviewerRating:
    """Rating for a reviewer."""
    reviewer_id: str
    average_score: float
    total_reviews: int
    metric_averages: Dict[str, float]
    category: ScoreCategory
    rank: Optional[int] = None
    percentile: Optional[float] = None
    trend: Optional[str] = None  # "improving", "stable", "declining"


@dataclass
class QualityTrend:
    """Quality trend analysis."""
    metric: str
    period: str  # "daily", "weekly", "monthly"
    data_points: List[Dict[str, Any]]
    average: float
    trend_direction: str  # "up", "down", "stable"
    change_percentage: float


class QualityScorer:
    """Evaluates and scores code review quality."""

    def __init__(self):
        """Initialize the quality scorer."""
        self.reviews: Dict[str, ReviewScore] = {}
        self.reviewer_stats: Dict[str, List[ReviewScore]] = {}

        # Weights for different metrics (must sum to 1.0)
        self.metric_weights = {
            QualityMetric.COVERAGE.value: 0.25,
            QualityMetric.DEPTH.value: 0.30,
            QualityMetric.TIMELINESS.value: 0.15,
            QualityMetric.EFFECTIVENESS.value: 0.20,
            QualityMetric.ENGAGEMENT.value: 0.10,
        }

    def score_review(
        self,
        review_id: str,
        reviewer_id: str,
        review_data: Dict[str, Any]
    ) -> ReviewScore:
        """
        Score a code review based on multiple quality metrics.

        Args:
            review_id: Unique review identifier
            reviewer_id: Reviewer identifier
            review_data: Review data including:
                - files_changed: Number of files in the PR
                - files_reviewed: Number of files the reviewer commented on
                - comments_count: Number of comments made
                - comment_depth: Average comment length/detail
                - time_to_review: Hours taken to complete review
                - issues_found: Number of issues identified
                - issues_resolved: Number of issues that were fixed
                - discussion_threads: Number of discussion threads

        Returns:
            ReviewScore object with overall and metric scores
        """
        # Calculate individual metric scores
        coverage_score = self._calculate_coverage_score(review_data)
        depth_score = self._calculate_depth_score(review_data)
        timeliness_score = self._calculate_timeliness_score(review_data)
        effectiveness_score = self._calculate_effectiveness_score(review_data)
        engagement_score = self._calculate_engagement_score(review_data)

        metric_scores = {
            QualityMetric.COVERAGE.value: coverage_score,
            QualityMetric.DEPTH.value: depth_score,
            QualityMetric.TIMELINESS.value: timeliness_score,
            QualityMetric.EFFECTIVENESS.value: effectiveness_score,
            QualityMetric.ENGAGEMENT.value: engagement_score,
        }

        # Calculate weighted overall score
        overall_score = sum(
            score * self.metric_weights[metric]
            for metric, score in metric_scores.items()
        )

        # Determine category
        category = self._categorize_score(overall_score)

        # Generate feedback
        feedback = self._generate_feedback(metric_scores, overall_score)

        score = ReviewScore(
            review_id=review_id,
            reviewer_id=reviewer_id,
            overall_score=round(overall_score, 2),
            metric_scores={k: round(v, 2) for k, v in metric_scores.items()},
            category=category,
            timestamp=datetime.now(timezone.utc).isoformat(),
            feedback=feedback
        )

        # Store the score
        self.reviews[review_id] = score
        if reviewer_id not in self.reviewer_stats:
            self.reviewer_stats[reviewer_id] = []
        self.reviewer_stats[reviewer_id].append(score)

        return score

    def _calculate_coverage_score(self, data: Dict[str, Any]) -> float:
        """Calculate coverage score (0-100)."""
        files_changed = data.get('files_changed', 1)
        files_reviewed = data.get('files_reviewed', 0)

        if files_changed == 0:
            return 100.0

        coverage_ratio = files_reviewed / files_changed
        return min(coverage_ratio * 100, 100.0)

    def _calculate_depth_score(self, data: Dict[str, Any]) -> float:
        """Calculate depth score (0-100)."""
        comments_count = data.get('comments_count', 0)
        comment_depth = data.get('comment_depth', 0)  # Average chars per comment

        # Score based on number of comments (0-50 points)
        comment_score = min(comments_count * 5, 50)

        # Score based on comment depth (0-50 points)
        # Assume good comments are 50-200 chars
        if comment_depth >= 50:
            depth_score = min((comment_depth / 200) * 50, 50)
        else:
            depth_score = (comment_depth / 50) * 25

        return min(comment_score + depth_score, 100.0)

    def _calculate_timeliness_score(self, data: Dict[str, Any]) -> float:
        """Calculate timeliness score (0-100)."""
        time_to_review = data.get('time_to_review', 0)  # in hours

        # Ideal review time: within 24 hours
        # Score decreases as time increases
        if time_to_review <= 24:
            return 100.0
        elif time_to_review <= 48:
            return 80.0
        elif time_to_review <= 72:
            return 60.0
        elif time_to_review <= 168:  # 1 week
            return 40.0
        else:
            return 20.0

    def _calculate_effectiveness_score(self, data: Dict[str, Any]) -> float:
        """Calculate effectiveness score (0-100)."""
        issues_found = data.get('issues_found', 0)
        issues_resolved = data.get('issues_resolved', 0)

        if issues_found == 0:
            # No issues found could mean thorough code or superficial review
            # Give moderate score
            return 70.0

        resolution_ratio = issues_resolved / issues_found

        # Score based on issue resolution rate
        effectiveness = resolution_ratio * 100

        # Bonus for finding issues (up to 20 points)
        issue_bonus = min(issues_found * 2, 20)

        return min(effectiveness * 0.8 + issue_bonus, 100.0)

    def _calculate_engagement_score(self, data: Dict[str, Any]) -> float:
        """Calculate engagement score (0-100)."""
        discussion_threads = data.get('discussion_threads', 0)
        comments_count = data.get('comments_count', 0)

        # Score based on discussion threads
        thread_score = min(discussion_threads * 10, 50)

        # Score based on comment interactions
        interaction_score = min(comments_count * 3, 50)

        return min(thread_score + interaction_score, 100.0)

    def _categorize_score(self, score: float) -> ScoreCategory:
        """Categorize a score."""
        if score >= 90:
            return ScoreCategory.EXCELLENT
        elif score >= 75:
            return ScoreCategory.GOOD
        elif score >= 60:
            return ScoreCategory.FAIR
        else:
            return ScoreCategory.POOR

    def _generate_feedback(
        self,
        metric_scores: Dict[str, float],
        overall_score: float
    ) -> List[str]:
        """Generate improvement feedback based on scores."""
        feedback = []

        # Overall feedback
        if overall_score >= 90:
            feedback.append("Excellent review quality! Keep up the great work.")
        elif overall_score >= 75:
            feedback.append("Good review quality with room for improvement.")
        elif overall_score >= 60:
            feedback.append("Fair review quality. Consider the suggestions below.")
        else:
            feedback.append("Review quality needs improvement. Please focus on the areas below.")

        # Metric-specific feedback
        for metric, score in metric_scores.items():
            if score < 60:
                if metric == QualityMetric.COVERAGE.value:
                    feedback.append("• Review more files in the PR to improve coverage")
                elif metric == QualityMetric.DEPTH.value:
                    feedback.append("• Provide more detailed comments and analysis")
                elif metric == QualityMetric.TIMELINESS.value:
                    feedback.append("• Try to complete reviews more quickly")
                elif metric == QualityMetric.EFFECTIVENESS.value:
                    feedback.append("• Focus on identifying actionable issues")
                elif metric == QualityMetric.ENGAGEMENT.value:
                    feedback.append("• Engage more in discussions with the author")

        return feedback

    def get_reviewer_rating(self, reviewer_id: str) -> Optional[ReviewerRating]:
        """Get overall rating for a reviewer."""
        if reviewer_id not in self.reviewer_stats:
            return None

        scores = self.reviewer_stats[reviewer_id]
        if not scores:
            return None

        # Calculate averages
        overall_scores = [s.overall_score for s in scores]
        average_score = statistics.mean(overall_scores)

        # Calculate metric averages
        metric_averages = {}
        for metric in QualityMetric:
            metric_scores = [
                s.metric_scores.get(metric.value, 0)
                for s in scores
            ]
            metric_averages[metric.value] = statistics.mean(metric_scores)

        # Determine trend
        trend = self._calculate_trend(overall_scores)

        return ReviewerRating(
            reviewer_id=reviewer_id,
            average_score=round(average_score, 2),
            total_reviews=len(scores),
            metric_averages={k: round(v, 2) for k, v in metric_averages.items()},
            category=self._categorize_score(average_score),
            trend=trend
        )

    def _calculate_trend(self, scores: List[float]) -> str:
        """Calculate trend direction from score history."""
        if len(scores) < 3:
            return "stable"

        # Compare recent scores to older scores
        recent = scores[-3:]
        older = scores[:-3] if len(scores) > 3 else scores[:3]

        recent_avg = statistics.mean(recent)
        older_avg = statistics.mean(older)

        diff = recent_avg - older_avg

        if diff > 5:
            return "improving"
        elif diff < -5:
            return "declining"
        else:
            return "stable"

    def rank_reviewers(self) -> List[ReviewerRating]:
        """Rank all reviewers by average score."""
        ratings = []
        for reviewer_id in self.reviewer_stats:
            rating = self.get_reviewer_rating(reviewer_id)
            if rating:
                ratings.append(rating)

        # Sort by average score (descending)
        ratings.sort(key=lambda r: r.average_score, reverse=True)

        # Assign ranks and percentiles
        total = len(ratings)
        for i, rating in enumerate(ratings):
            rating.rank = i + 1
            rating.percentile = round(((total - i) / total) * 100, 1)

        return ratings

    def analyze_quality_trend(
        self,
        metric: QualityMetric,
        period: str = "weekly",
        days: int = 30
    ) -> QualityTrend:
        """Analyze quality trends over time."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # Collect relevant scores
        data_points = []
        for review_id, score in self.reviews.items():
            review_time = datetime.fromisoformat(score.timestamp)
            if review_time >= cutoff:
                data_points.append({
                    'timestamp': score.timestamp,
                    'score': score.metric_scores.get(metric.value, 0),
                    'review_id': review_id
                })

        if not data_points:
            return QualityTrend(
                metric=metric.value,
                period=period,
                data_points=[],
                average=0.0,
                trend_direction="stable",
                change_percentage=0.0
            )

        # Calculate average
        scores = [dp['score'] for dp in data_points]
        average = statistics.mean(scores)

        # Calculate trend
        if len(scores) >= 2:
            first_half = scores[:len(scores)//2]
            second_half = scores[len(scores)//2:]

            first_avg = statistics.mean(first_half)
            second_avg = statistics.mean(second_half)

            change = second_avg - first_avg
            change_percentage = (change / first_avg * 100) if first_avg > 0 else 0

            if change_percentage > 5:
                trend_direction = "up"
            elif change_percentage < -5:
                trend_direction = "down"
            else:
                trend_direction = "stable"
        else:
            trend_direction = "stable"
            change_percentage = 0.0

        return QualityTrend(
            metric=metric.value,
            period=period,
            data_points=data_points,
            average=round(average, 2),
            trend_direction=trend_direction,
            change_percentage=round(change_percentage, 2)
        )

    def get_improvement_suggestions(
        self,
        reviewer_id: str
    ) -> List[str]:
        """Get personalized improvement suggestions for a reviewer."""
        rating = self.get_reviewer_rating(reviewer_id)
        if not rating:
            return ["No review history available yet."]

        suggestions = []

        # Overall performance
        if rating.average_score < 75:
            suggestions.append(
                f"Your average score is {rating.average_score:.1f}. "
                "Focus on the specific areas below to improve."
            )

        # Metric-specific suggestions
        for metric, avg_score in rating.metric_averages.items():
            if avg_score < 70:
                if metric == QualityMetric.COVERAGE.value:
                    suggestions.append(
                        "Coverage: Review all changed files, not just the main ones. "
                        "Even small changes can have important implications."
                    )
                elif metric == QualityMetric.DEPTH.value:
                    suggestions.append(
                        "Depth: Provide more detailed feedback. Explain the 'why' "
                        "behind your suggestions, not just the 'what'."
                    )
                elif metric == QualityMetric.TIMELINESS.value:
                    suggestions.append(
                        "Timeliness: Try to review PRs within 24 hours. "
                        "Quick feedback helps maintain development momentum."
                    )
                elif metric == QualityMetric.EFFECTIVENESS.value:
                    suggestions.append(
                        "Effectiveness: Focus on finding meaningful issues. "
                        "Look for bugs, security issues, and design problems."
                    )
                elif metric == QualityMetric.ENGAGEMENT.value:
                    suggestions.append(
                        "Engagement: Participate more in discussions. "
                        "Ask questions and collaborate with the author."
                    )

        # Trend-based suggestions
        if rating.trend == "declining":
            suggestions.append(
                "⚠️ Your review quality has been declining recently. "
                "Consider if you're taking on too many reviews or need more time."
            )
        elif rating.trend == "improving":
            suggestions.append(
                "✓ Great job! Your review quality is improving. Keep it up!"
            )

        return suggestions if suggestions else [
            "Excellent work! Your review quality is consistently high."
        ]
