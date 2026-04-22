"""
Code Review Metrics Collection System

Comprehensive metrics collection and analysis for code reviews:
- Review efficiency metrics
- Quality metrics
- Team performance metrics
- Trend analysis
- Benchmarking
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import json
from pathlib import Path
from collections import defaultdict
import statistics


class MetricType(Enum):
    """Type of metric"""
    EFFICIENCY = "efficiency"
    QUALITY = "quality"
    TEAM = "team"
    PROCESS = "process"


class TimeRange(Enum):
    """Time range for metrics"""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    ALL_TIME = "all_time"


@dataclass
class ReviewMetrics:
    """Metrics for a single review"""
    review_id: str
    pr_id: str
    repository: str
    author: str
    reviewers: List[str]

    # Timing metrics
    created_at: str
    first_response_time_minutes: Optional[float] = None
    total_review_time_minutes: Optional[float] = None
    time_to_merge_minutes: Optional[float] = None

    # Size metrics
    lines_added: int = 0
    lines_deleted: int = 0
    files_changed: int = 0

    # Quality metrics
    comments_count: int = 0
    issues_found: int = 0
    suggestions_made: int = 0
    iterations: int = 1

    # Outcome
    approved: bool = False
    merged: bool = False
    rejected: bool = False

    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EfficiencyMetrics:
    """Review efficiency metrics"""
    avg_first_response_time_minutes: float
    avg_total_review_time_minutes: float
    avg_time_to_merge_minutes: float
    median_first_response_time_minutes: float
    median_total_review_time_minutes: float
    reviews_per_day: float
    throughput: float  # reviews completed per day

    # Percentiles
    p50_response_time: float
    p90_response_time: float
    p95_response_time: float


@dataclass
class QualityMetrics:
    """Review quality metrics"""
    avg_comments_per_review: float
    avg_issues_per_review: float
    avg_suggestions_per_review: float
    avg_iterations: float
    approval_rate: float
    rejection_rate: float

    # Quality indicators
    thoroughness_score: float  # comments per 100 lines
    issue_detection_rate: float  # issues per review
    suggestion_rate: float  # suggestions per review


@dataclass
class TeamMetrics:
    """Team performance metrics"""
    total_reviewers: int
    active_reviewers: int
    avg_reviews_per_reviewer: float
    review_distribution: Dict[str, int]  # reviewer -> count

    # Workload balance
    workload_std_dev: float
    max_reviews: int
    min_reviews: int

    # Collaboration
    avg_reviewers_per_pr: float
    cross_team_reviews: int


@dataclass
class ProcessMetrics:
    """Process metrics"""
    total_reviews: int
    completed_reviews: int
    pending_reviews: int
    completion_rate: float

    # Size distribution
    avg_lines_changed: float
    avg_files_changed: float

    # Outcomes
    merged_count: int
    rejected_count: int
    merge_rate: float


@dataclass
class MetricsSummary:
    """Complete metrics summary"""
    time_range: str
    start_date: str
    end_date: str

    efficiency: EfficiencyMetrics
    quality: QualityMetrics
    team: TeamMetrics
    process: ProcessMetrics

    # Trends
    trends: Dict[str, List[float]] = field(default_factory=dict)


class MetricsCollector:
    """Collects and analyzes code review metrics"""

    def __init__(self, storage_path: Optional[str] = None):
        self.reviews: Dict[str, ReviewMetrics] = {}
        self.storage_path = Path(storage_path) if storage_path else Path.home() / ".pr_agent" / "metrics"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Load existing metrics
        self._load_metrics()

    def record_review(self, metrics: ReviewMetrics):
        """Record review metrics"""
        self.reviews[metrics.review_id] = metrics
        self._save_metrics()

    def update_review(
        self,
        review_id: str,
        **updates
    ):
        """Update review metrics"""
        if review_id not in self.reviews:
            raise ValueError(f"Review {review_id} not found")

        review = self.reviews[review_id]
        for key, value in updates.items():
            if hasattr(review, key):
                setattr(review, key, value)

        self._save_metrics()

    def get_metrics_summary(
        self,
        time_range: TimeRange = TimeRange.MONTH,
        repository: Optional[str] = None,
        author: Optional[str] = None,
        reviewer: Optional[str] = None
    ) -> MetricsSummary:
        """Get comprehensive metrics summary"""
        # Filter reviews
        reviews = self._filter_reviews(time_range, repository, author, reviewer)

        if not reviews:
            # Return empty metrics
            return self._empty_summary(time_range)

        # Calculate metrics
        efficiency = self._calculate_efficiency_metrics(reviews)
        quality = self._calculate_quality_metrics(reviews)
        team = self._calculate_team_metrics(reviews)
        process = self._calculate_process_metrics(reviews)

        # Calculate trends
        trends = self._calculate_trends(reviews, time_range)

        # Get time range
        start_date, end_date = self._get_time_range_dates(time_range)

        return MetricsSummary(
            time_range=time_range.value,
            start_date=start_date,
            end_date=end_date,
            efficiency=efficiency,
            quality=quality,
            team=team,
            process=process,
            trends=trends
        )

    def get_reviewer_metrics(
        self,
        reviewer: str,
        time_range: TimeRange = TimeRange.MONTH
    ) -> Dict[str, Any]:
        """Get metrics for specific reviewer"""
        reviews = self._filter_reviews(time_range, reviewer=reviewer)

        if not reviews:
            return {
                "reviewer": reviewer,
                "reviews_count": 0,
                "avg_response_time": 0,
                "avg_comments": 0,
                "avg_issues_found": 0
            }

        response_times = [r.first_response_time_minutes for r in reviews if r.first_response_time_minutes]

        return {
            "reviewer": reviewer,
            "reviews_count": len(reviews),
            "avg_response_time": statistics.mean(response_times) if response_times else 0,
            "median_response_time": statistics.median(response_times) if response_times else 0,
            "avg_comments": statistics.mean([r.comments_count for r in reviews]),
            "avg_issues_found": statistics.mean([r.issues_found for r in reviews]),
            "avg_suggestions": statistics.mean([r.suggestions_made for r in reviews]),
            "approval_rate": sum(1 for r in reviews if r.approved) / len(reviews)
        }

    def get_author_metrics(
        self,
        author: str,
        time_range: TimeRange = TimeRange.MONTH
    ) -> Dict[str, Any]:
        """Get metrics for specific author"""
        reviews = self._filter_reviews(time_range, author=author)

        if not reviews:
            return {
                "author": author,
                "prs_count": 0,
                "avg_time_to_merge": 0,
                "avg_iterations": 0
            }

        merge_times = [r.time_to_merge_minutes for r in reviews if r.time_to_merge_minutes]

        return {
            "author": author,
            "prs_count": len(reviews),
            "avg_time_to_merge": statistics.mean(merge_times) if merge_times else 0,
            "avg_iterations": statistics.mean([r.iterations for r in reviews]),
            "avg_lines_changed": statistics.mean([r.lines_added + r.lines_deleted for r in reviews]),
            "avg_files_changed": statistics.mean([r.files_changed for r in reviews]),
            "merge_rate": sum(1 for r in reviews if r.merged) / len(reviews),
            "avg_issues_per_pr": statistics.mean([r.issues_found for r in reviews])
        }

    def get_repository_metrics(
        self,
        repository: str,
        time_range: TimeRange = TimeRange.MONTH
    ) -> Dict[str, Any]:
        """Get metrics for specific repository"""
        reviews = self._filter_reviews(time_range, repository=repository)

        if not reviews:
            return {
                "repository": repository,
                "reviews_count": 0
            }

        return {
            "repository": repository,
            "reviews_count": len(reviews),
            "active_authors": len(set(r.author for r in reviews)),
            "active_reviewers": len(set(rev for r in reviews for rev in r.reviewers)),
            "avg_review_time": statistics.mean([r.total_review_time_minutes for r in reviews if r.total_review_time_minutes]),
            "avg_pr_size": statistics.mean([r.lines_added + r.lines_deleted for r in reviews]),
            "merge_rate": sum(1 for r in reviews if r.merged) / len(reviews)
        }

    def compare_periods(
        self,
        period1: TimeRange,
        period2: TimeRange
    ) -> Dict[str, Dict[str, float]]:
        """Compare metrics between two time periods"""
        summary1 = self.get_metrics_summary(period1)
        summary2 = self.get_metrics_summary(period2)

        return {
            "efficiency": {
                "response_time_change": self._calculate_change(
                    summary1.efficiency.avg_first_response_time_minutes,
                    summary2.efficiency.avg_first_response_time_minutes
                ),
                "review_time_change": self._calculate_change(
                    summary1.efficiency.avg_total_review_time_minutes,
                    summary2.efficiency.avg_total_review_time_minutes
                ),
                "throughput_change": self._calculate_change(
                    summary1.efficiency.throughput,
                    summary2.efficiency.throughput
                )
            },
            "quality": {
                "comments_change": self._calculate_change(
                    summary1.quality.avg_comments_per_review,
                    summary2.quality.avg_comments_per_review
                ),
                "issues_change": self._calculate_change(
                    summary1.quality.avg_issues_per_review,
                    summary2.quality.avg_issues_per_review
                ),
                "approval_rate_change": self._calculate_change(
                    summary1.quality.approval_rate,
                    summary2.quality.approval_rate
                )
            },
            "team": {
                "active_reviewers_change": self._calculate_change(
                    summary1.team.active_reviewers,
                    summary2.team.active_reviewers
                ),
                "workload_balance_change": self._calculate_change(
                    summary1.team.workload_std_dev,
                    summary2.team.workload_std_dev
                )
            }
        }

    def _filter_reviews(
        self,
        time_range: TimeRange,
        repository: Optional[str] = None,
        author: Optional[str] = None,
        reviewer: Optional[str] = None
    ) -> List[ReviewMetrics]:
        """Filter reviews by criteria"""
        start_date, _ = self._get_time_range_dates(time_range)
        start_dt = datetime.fromisoformat(start_date)

        filtered = []
        for review in self.reviews.values():
            review_dt = datetime.fromisoformat(review.created_at)

            # Time filter
            if review_dt < start_dt:
                continue

            # Repository filter
            if repository and review.repository != repository:
                continue

            # Author filter
            if author and review.author != author:
                continue

            # Reviewer filter
            if reviewer and reviewer not in review.reviewers:
                continue

            filtered.append(review)

        return filtered

    def _calculate_efficiency_metrics(self, reviews: List[ReviewMetrics]) -> EfficiencyMetrics:
        """Calculate efficiency metrics"""
        response_times = [r.first_response_time_minutes for r in reviews if r.first_response_time_minutes]
        review_times = [r.total_review_time_minutes for r in reviews if r.total_review_time_minutes]
        merge_times = [r.time_to_merge_minutes for r in reviews if r.time_to_merge_minutes]

        # Calculate time span
        dates = [datetime.fromisoformat(r.created_at) for r in reviews]
        time_span_days = (max(dates) - min(dates)).days + 1

        return EfficiencyMetrics(
            avg_first_response_time_minutes=statistics.mean(response_times) if response_times else 0,
            avg_total_review_time_minutes=statistics.mean(review_times) if review_times else 0,
            avg_time_to_merge_minutes=statistics.mean(merge_times) if merge_times else 0,
            median_first_response_time_minutes=statistics.median(response_times) if response_times else 0,
            median_total_review_time_minutes=statistics.median(review_times) if review_times else 0,
            reviews_per_day=len(reviews) / time_span_days,
            throughput=sum(1 for r in reviews if r.merged) / time_span_days,
            p50_response_time=statistics.median(response_times) if response_times else 0,
            p90_response_time=self._percentile(response_times, 90) if response_times else 0,
            p95_response_time=self._percentile(response_times, 95) if response_times else 0
        )

    def _calculate_quality_metrics(self, reviews: List[ReviewMetrics]) -> QualityMetrics:
        """Calculate quality metrics"""
        total_lines = sum(r.lines_added + r.lines_deleted for r in reviews)
        total_comments = sum(r.comments_count for r in reviews)

        return QualityMetrics(
            avg_comments_per_review=statistics.mean([r.comments_count for r in reviews]),
            avg_issues_per_review=statistics.mean([r.issues_found for r in reviews]),
            avg_suggestions_per_review=statistics.mean([r.suggestions_made for r in reviews]),
            avg_iterations=statistics.mean([r.iterations for r in reviews]),
            approval_rate=sum(1 for r in reviews if r.approved) / len(reviews),
            rejection_rate=sum(1 for r in reviews if r.rejected) / len(reviews),
            thoroughness_score=(total_comments / total_lines * 100) if total_lines > 0 else 0,
            issue_detection_rate=sum(r.issues_found for r in reviews) / len(reviews),
            suggestion_rate=sum(r.suggestions_made for r in reviews) / len(reviews)
        )

    def _calculate_team_metrics(self, reviews: List[ReviewMetrics]) -> TeamMetrics:
        """Calculate team metrics"""
        all_reviewers = set()
        review_counts = defaultdict(int)

        for review in reviews:
            for reviewer in review.reviewers:
                all_reviewers.add(reviewer)
                review_counts[reviewer] += 1

        counts = list(review_counts.values())

        return TeamMetrics(
            total_reviewers=len(all_reviewers),
            active_reviewers=len([c for c in counts if c > 0]),
            avg_reviews_per_reviewer=statistics.mean(counts) if counts else 0,
            review_distribution=dict(review_counts),
            workload_std_dev=statistics.stdev(counts) if len(counts) > 1 else 0,
            max_reviews=max(counts) if counts else 0,
            min_reviews=min(counts) if counts else 0,
            avg_reviewers_per_pr=statistics.mean([len(r.reviewers) for r in reviews]),
            cross_team_reviews=0  # Placeholder
        )

    def _calculate_process_metrics(self, reviews: List[ReviewMetrics]) -> ProcessMetrics:
        """Calculate process metrics"""
        completed = [r for r in reviews if r.merged or r.rejected]

        return ProcessMetrics(
            total_reviews=len(reviews),
            completed_reviews=len(completed),
            pending_reviews=len(reviews) - len(completed),
            completion_rate=len(completed) / len(reviews) if reviews else 0,
            avg_lines_changed=statistics.mean([r.lines_added + r.lines_deleted for r in reviews]),
            avg_files_changed=statistics.mean([r.files_changed for r in reviews]),
            merged_count=sum(1 for r in reviews if r.merged),
            rejected_count=sum(1 for r in reviews if r.rejected),
            merge_rate=sum(1 for r in reviews if r.merged) / len(reviews) if reviews else 0
        )

    def _calculate_trends(
        self,
        reviews: List[ReviewMetrics],
        time_range: TimeRange
    ) -> Dict[str, List[float]]:
        """Calculate metric trends over time"""
        # Group reviews by time buckets
        buckets = self._group_by_time_buckets(reviews, time_range)

        trends = {
            "response_time": [],
            "review_time": [],
            "comments": [],
            "issues": [],
            "throughput": []
        }

        for bucket_reviews in buckets:
            if not bucket_reviews:
                trends["response_time"].append(0)
                trends["review_time"].append(0)
                trends["comments"].append(0)
                trends["issues"].append(0)
                trends["throughput"].append(0)
                continue

            response_times = [r.first_response_time_minutes for r in bucket_reviews if r.first_response_time_minutes]
            review_times = [r.total_review_time_minutes for r in bucket_reviews if r.total_review_time_minutes]

            trends["response_time"].append(statistics.mean(response_times) if response_times else 0)
            trends["review_time"].append(statistics.mean(review_times) if review_times else 0)
            trends["comments"].append(statistics.mean([r.comments_count for r in bucket_reviews]))
            trends["issues"].append(statistics.mean([r.issues_found for r in bucket_reviews]))
            trends["throughput"].append(len(bucket_reviews))

        return trends

    def _group_by_time_buckets(
        self,
        reviews: List[ReviewMetrics],
        time_range: TimeRange
    ) -> List[List[ReviewMetrics]]:
        """Group reviews into time buckets"""
        if not reviews:
            return []

        # Determine bucket size
        bucket_days = {
            TimeRange.WEEK: 1,
            TimeRange.MONTH: 7,
            TimeRange.QUARTER: 30,
            TimeRange.YEAR: 30,
            TimeRange.ALL_TIME: 30
        }.get(time_range, 7)

        # Sort reviews by date
        sorted_reviews = sorted(reviews, key=lambda r: r.created_at)

        # Create buckets
        buckets = []
        current_bucket = []
        current_date = datetime.fromisoformat(sorted_reviews[0].created_at)

        for review in sorted_reviews:
            review_date = datetime.fromisoformat(review.created_at)

            if (review_date - current_date).days >= bucket_days:
                buckets.append(current_bucket)
                current_bucket = [review]
                current_date = review_date
            else:
                current_bucket.append(review)

        if current_bucket:
            buckets.append(current_bucket)

        return buckets

    def _get_time_range_dates(self, time_range: TimeRange) -> Tuple[str, str]:
        """Get start and end dates for time range"""
        now = datetime.now(timezone.utc)

        if time_range == TimeRange.DAY:
            start = now - timedelta(days=1)
        elif time_range == TimeRange.WEEK:
            start = now - timedelta(weeks=1)
        elif time_range == TimeRange.MONTH:
            start = now - timedelta(days=30)
        elif time_range == TimeRange.QUARTER:
            start = now - timedelta(days=90)
        elif time_range == TimeRange.YEAR:
            start = now - timedelta(days=365)
        else:  # ALL_TIME
            start = datetime.min.replace(tzinfo=timezone.utc)

        return start.isoformat(), now.isoformat()

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

    def _calculate_change(self, old_value: float, new_value: float) -> float:
        """Calculate percentage change"""
        if old_value == 0:
            return 0
        return ((new_value - old_value) / old_value) * 100

    def _empty_summary(self, time_range: TimeRange) -> MetricsSummary:
        """Create empty metrics summary"""
        start_date, end_date = self._get_time_range_dates(time_range)

        return MetricsSummary(
            time_range=time_range.value,
            start_date=start_date,
            end_date=end_date,
            efficiency=EfficiencyMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
            quality=QualityMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0),
            team=TeamMetrics(0, 0, 0, {}, 0, 0, 0, 0, 0),
            process=ProcessMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0),
            trends={}
        )

    def _save_metrics(self):
        """Save metrics to storage"""
        metrics_file = self.storage_path / "reviews.json"

        data = {
            review_id: {
                "review_id": m.review_id,
                "pr_id": m.pr_id,
                "repository": m.repository,
                "author": m.author,
                "reviewers": m.reviewers,
                "created_at": m.created_at,
                "first_response_time_minutes": m.first_response_time_minutes,
                "total_review_time_minutes": m.total_review_time_minutes,
                "time_to_merge_minutes": m.time_to_merge_minutes,
                "lines_added": m.lines_added,
                "lines_deleted": m.lines_deleted,
                "files_changed": m.files_changed,
                "comments_count": m.comments_count,
                "issues_found": m.issues_found,
                "suggestions_made": m.suggestions_made,
                "iterations": m.iterations,
                "approved": m.approved,
                "merged": m.merged,
                "rejected": m.rejected,
                "metadata": m.metadata
            }
            for review_id, m in self.reviews.items()
        }

        with open(metrics_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_metrics(self):
        """Load metrics from storage"""
        metrics_file = self.storage_path / "reviews.json"
        if not metrics_file.exists():
            return

        with open(metrics_file, 'r') as f:
            data = json.load(f)

        for review_id, m_data in data.items():
            self.reviews[review_id] = ReviewMetrics(
                review_id=m_data["review_id"],
                pr_id=m_data["pr_id"],
                repository=m_data["repository"],
                author=m_data["author"],
                reviewers=m_data["reviewers"],
                created_at=m_data["created_at"],
                first_response_time_minutes=m_data.get("first_response_time_minutes"),
                total_review_time_minutes=m_data.get("total_review_time_minutes"),
                time_to_merge_minutes=m_data.get("time_to_merge_minutes"),
                lines_added=m_data.get("lines_added", 0),
                lines_deleted=m_data.get("lines_deleted", 0),
                files_changed=m_data.get("files_changed", 0),
                comments_count=m_data.get("comments_count", 0),
                issues_found=m_data.get("issues_found", 0),
                suggestions_made=m_data.get("suggestions_made", 0),
                iterations=m_data.get("iterations", 1),
                approved=m_data.get("approved", False),
                merged=m_data.get("merged", False),
                rejected=m_data.get("rejected", False),
                metadata=m_data.get("metadata", {})
            )


# Global instance
_metrics_collector = None


def get_metrics_collector(storage_path: Optional[str] = None) -> MetricsCollector:
    """Get global metrics collector instance"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector(storage_path)
    return _metrics_collector
