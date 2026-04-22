"""
Code Review Dashboard System

Provides comprehensive analytics and visualization for code review activities.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import json
from collections import defaultdict


class WidgetType(Enum):
    """Dashboard widget types."""
    REVIEW_STATS = "review_stats"
    REVIEWER_WORKLOAD = "reviewer_workload"
    TIME_TRENDS = "time_trends"
    QUALITY_METRICS = "quality_metrics"
    TEAM_EFFICIENCY = "team_efficiency"
    TOP_REVIEWERS = "top_reviewers"
    BOTTLENECKS = "bottlenecks"
    CUSTOM = "custom"


class TimeRange(Enum):
    """Time range for analytics."""
    TODAY = "today"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"
    CUSTOM = "custom"


@dataclass
class ReviewStats:
    """Review statistics."""
    total_reviews: int = 0
    pending_reviews: int = 0
    in_progress_reviews: int = 0
    completed_reviews: int = 0
    approved_reviews: int = 0
    rejected_reviews: int = 0
    avg_review_time_hours: float = 0.0
    avg_comments_per_review: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReviewerWorkload:
    """Reviewer workload statistics."""
    reviewer_id: str
    reviewer_name: str
    pending_count: int = 0
    in_progress_count: int = 0
    completed_count: int = 0
    avg_review_time_hours: float = 0.0
    total_comments: int = 0
    approval_rate: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TimeTrend:
    """Time-based trend data."""
    timestamp: datetime
    pending_count: int = 0
    completed_count: int = 0
    avg_review_time_hours: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class QualityMetrics:
    """Code quality metrics."""
    avg_complexity: float = 0.0
    avg_maintainability: float = 0.0
    avg_test_coverage: float = 0.0
    total_issues: int = 0
    critical_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TeamEfficiency:
    """Team efficiency metrics."""
    total_prs: int = 0
    avg_time_to_first_review_hours: float = 0.0
    avg_time_to_merge_hours: float = 0.0
    review_throughput: float = 0.0  # reviews per day
    active_reviewers: int = 0
    collaboration_score: float = 0.0  # 0-100
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DashboardWidget:
    """Dashboard widget configuration."""
    widget_id: str
    widget_type: WidgetType
    title: str
    position: Tuple[int, int]  # (row, col)
    size: Tuple[int, int]  # (width, height)
    config: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['widget_type'] = self.widget_type.value
        return data


@dataclass
class Dashboard:
    """Dashboard configuration."""
    dashboard_id: str
    name: str
    description: str
    widgets: List[DashboardWidget] = field(default_factory=list)
    time_range: TimeRange = TimeRange.WEEK
    auto_refresh: bool = True
    refresh_interval_seconds: int = 300
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['widgets'] = [w.to_dict() for w in self.widgets]
        data['time_range'] = self.time_range.value
        return data


class DashboardSystem:
    """Dashboard system for code review analytics."""

    def __init__(self, storage_path: Optional[Path] = None):
        """Initialize dashboard system."""
        self.storage_path = storage_path or Path.home() / ".pr_agent" / "dashboards"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.dashboards: Dict[str, Dashboard] = {}
        self.review_data: List[Dict[str, Any]] = []
        self.reviewer_data: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        self._load_dashboards()

    def _load_dashboards(self):
        """Load dashboards from storage."""
        config_file = self.storage_path / "dashboards.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    for dash_data in data.get('dashboards', []):
                        dashboard = self._deserialize_dashboard(dash_data)
                        self.dashboards[dashboard.dashboard_id] = dashboard
            except Exception:
                pass

    def _save_dashboards(self):
        """Save dashboards to storage."""
        config_file = self.storage_path / "dashboards.json"
        data = {
            'dashboards': [d.to_dict() for d in self.dashboards.values()]
        }
        with open(config_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _deserialize_dashboard(self, data: Dict[str, Any]) -> Dashboard:
        """Deserialize dashboard from dict."""
        widgets = []
        for w_data in data.get('widgets', []):
            widget = DashboardWidget(
                widget_id=w_data['widget_id'],
                widget_type=WidgetType(w_data['widget_type']),
                title=w_data['title'],
                position=tuple(w_data['position']),
                size=tuple(w_data['size']),
                config=w_data.get('config', {}),
                enabled=w_data.get('enabled', True),
                metadata=w_data.get('metadata', {})
            )
            widgets.append(widget)

        return Dashboard(
            dashboard_id=data['dashboard_id'],
            name=data['name'],
            description=data['description'],
            widgets=widgets,
            time_range=TimeRange(data.get('time_range', 'week')),
            auto_refresh=data.get('auto_refresh', True),
            refresh_interval_seconds=data.get('refresh_interval_seconds', 300),
            metadata=data.get('metadata', {})
        )

    def create_dashboard(
        self,
        dashboard_id: str,
        name: str,
        description: str,
        time_range: TimeRange = TimeRange.WEEK,
        auto_refresh: bool = True,
        refresh_interval_seconds: int = 300,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dashboard:
        """Create a new dashboard."""
        dashboard = Dashboard(
            dashboard_id=dashboard_id,
            name=name,
            description=description,
            time_range=time_range,
            auto_refresh=auto_refresh,
            refresh_interval_seconds=refresh_interval_seconds,
            metadata=metadata or {}
        )

        self.dashboards[dashboard_id] = dashboard
        self._save_dashboards()

        return dashboard

    def add_widget(
        self,
        dashboard_id: str,
        widget_id: str,
        widget_type: WidgetType,
        title: str,
        position: Tuple[int, int],
        size: Tuple[int, int],
        config: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DashboardWidget:
        """Add widget to dashboard."""
        if dashboard_id not in self.dashboards:
            raise ValueError(f"Dashboard {dashboard_id} not found")

        widget = DashboardWidget(
            widget_id=widget_id,
            widget_type=widget_type,
            title=title,
            position=position,
            size=size,
            config=config or {},
            metadata=metadata or {}
        )

        self.dashboards[dashboard_id].widgets.append(widget)
        self._save_dashboards()

        return widget

    def remove_widget(self, dashboard_id: str, widget_id: str):
        """Remove widget from dashboard."""
        if dashboard_id not in self.dashboards:
            raise ValueError(f"Dashboard {dashboard_id} not found")

        dashboard = self.dashboards[dashboard_id]
        dashboard.widgets = [w for w in dashboard.widgets if w.widget_id != widget_id]
        self._save_dashboards()

    def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        """Get dashboard by ID."""
        return self.dashboards.get(dashboard_id)

    def list_dashboards(self) -> List[Dashboard]:
        """List all dashboards."""
        return list(self.dashboards.values())

    def delete_dashboard(self, dashboard_id: str):
        """Delete a dashboard."""
        if dashboard_id in self.dashboards:
            del self.dashboards[dashboard_id]
            self._save_dashboards()

    def record_review(self, review_data: Dict[str, Any]):
        """Record review data for analytics."""
        # Only set timestamp if not already present
        if 'timestamp' not in review_data:
            review_data['timestamp'] = datetime.now(timezone.utc).isoformat()
        self.review_data.append(review_data)

        # Track by reviewer
        if 'reviewer_id' in review_data:
            self.reviewer_data[review_data['reviewer_id']].append(review_data)

    def get_review_stats(
        self,
        time_range: TimeRange = TimeRange.WEEK,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> ReviewStats:
        """Get review statistics."""
        filtered_reviews = self._filter_by_time_range(
            self.review_data, time_range, start_date, end_date
        )

        if not filtered_reviews:
            return ReviewStats()

        total = len(filtered_reviews)
        pending = sum(1 for r in filtered_reviews if r.get('status') == 'pending')
        in_progress = sum(1 for r in filtered_reviews if r.get('status') == 'in_progress')
        completed = sum(1 for r in filtered_reviews if r.get('status') == 'completed')
        approved = sum(1 for r in filtered_reviews if r.get('result') == 'approved')
        rejected = sum(1 for r in filtered_reviews if r.get('result') == 'rejected')

        # Calculate average review time
        review_times = [r.get('review_time_hours', 0) for r in filtered_reviews if r.get('review_time_hours')]
        avg_review_time = sum(review_times) / len(review_times) if review_times else 0.0

        # Calculate average comments
        comment_counts = [r.get('comment_count', 0) for r in filtered_reviews]
        avg_comments = sum(comment_counts) / len(comment_counts) if comment_counts else 0.0

        return ReviewStats(
            total_reviews=total,
            pending_reviews=pending,
            in_progress_reviews=in_progress,
            completed_reviews=completed,
            approved_reviews=approved,
            rejected_reviews=rejected,
            avg_review_time_hours=round(avg_review_time, 2),
            avg_comments_per_review=round(avg_comments, 2)
        )

    def get_reviewer_workload(
        self,
        reviewer_id: Optional[str] = None,
        time_range: TimeRange = TimeRange.WEEK,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[ReviewerWorkload]:
        """Get reviewer workload statistics."""
        workloads = []

        reviewer_ids = [reviewer_id] if reviewer_id else list(self.reviewer_data.keys())

        for rid in reviewer_ids:
            reviews = self.reviewer_data.get(rid, [])
            filtered_reviews = self._filter_by_time_range(
                reviews, time_range, start_date, end_date
            )

            if not filtered_reviews:
                continue

            pending = sum(1 for r in filtered_reviews if r.get('status') == 'pending')
            in_progress = sum(1 for r in filtered_reviews if r.get('status') == 'in_progress')
            completed = sum(1 for r in filtered_reviews if r.get('status') == 'completed')

            review_times = [r.get('review_time_hours', 0) for r in filtered_reviews if r.get('review_time_hours')]
            avg_time = sum(review_times) / len(review_times) if review_times else 0.0

            total_comments = sum(r.get('comment_count', 0) for r in filtered_reviews)

            approved = sum(1 for r in filtered_reviews if r.get('result') == 'approved')
            approval_rate = (approved / completed * 100) if completed > 0 else 0.0

            workload = ReviewerWorkload(
                reviewer_id=rid,
                reviewer_name=filtered_reviews[0].get('reviewer_name', rid),
                pending_count=pending,
                in_progress_count=in_progress,
                completed_count=completed,
                avg_review_time_hours=round(avg_time, 2),
                total_comments=total_comments,
                approval_rate=round(approval_rate, 2)
            )
            workloads.append(workload)

        return workloads

    def get_time_trends(
        self,
        time_range: TimeRange = TimeRange.WEEK,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        granularity: str = "day"
    ) -> List[TimeTrend]:
        """Get time-based trends."""
        filtered_reviews = self._filter_by_time_range(
            self.review_data, time_range, start_date, end_date
        )

        if not filtered_reviews:
            return []

        # Group by time period
        trends_by_period: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for review in filtered_reviews:
            timestamp = datetime.fromisoformat(review['timestamp'])
            if granularity == "day":
                period_key = timestamp.strftime("%Y-%m-%d")
            elif granularity == "week":
                period_key = timestamp.strftime("%Y-W%W")
            elif granularity == "month":
                period_key = timestamp.strftime("%Y-%m")
            else:
                period_key = timestamp.strftime("%Y-%m-%d")

            trends_by_period[period_key].append(review)

        # Calculate trends for each period
        trends = []
        for period_key, period_reviews in sorted(trends_by_period.items()):
            pending = sum(1 for r in period_reviews if r.get('status') == 'pending')
            completed = sum(1 for r in period_reviews if r.get('status') == 'completed')

            review_times = [r.get('review_time_hours', 0) for r in period_reviews if r.get('review_time_hours')]
            avg_time = sum(review_times) / len(review_times) if review_times else 0.0

            # Parse period key back to datetime
            if granularity == "day":
                timestamp = datetime.strptime(period_key, "%Y-%m-%d")
            elif granularity == "month":
                timestamp = datetime.strptime(period_key, "%Y-%m")
            else:
                timestamp = datetime.strptime(period_key.split('-')[0], "%Y")

            trend = TimeTrend(
                timestamp=timestamp.replace(tzinfo=timezone.utc),
                pending_count=pending,
                completed_count=completed,
                avg_review_time_hours=round(avg_time, 2)
            )
            trends.append(trend)

        return trends

    def get_quality_metrics(
        self,
        time_range: TimeRange = TimeRange.WEEK,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> QualityMetrics:
        """Get code quality metrics."""
        filtered_reviews = self._filter_by_time_range(
            self.review_data, time_range, start_date, end_date
        )

        if not filtered_reviews:
            return QualityMetrics()

        # Aggregate quality metrics
        complexities = [r.get('complexity', 0) for r in filtered_reviews if r.get('complexity')]
        avg_complexity = sum(complexities) / len(complexities) if complexities else 0.0

        maintainabilities = [r.get('maintainability', 0) for r in filtered_reviews if r.get('maintainability')]
        avg_maintainability = sum(maintainabilities) / len(maintainabilities) if maintainabilities else 0.0

        coverages = [r.get('test_coverage', 0) for r in filtered_reviews if r.get('test_coverage')]
        avg_coverage = sum(coverages) / len(coverages) if coverages else 0.0

        # Count issues by severity
        total_issues = 0
        critical = 0
        high = 0
        medium = 0
        low = 0

        for review in filtered_reviews:
            issues = review.get('issues', [])
            total_issues += len(issues)
            for issue in issues:
                severity = issue.get('severity', 'low')
                if severity == 'critical':
                    critical += 1
                elif severity == 'high':
                    high += 1
                elif severity == 'medium':
                    medium += 1
                else:
                    low += 1

        return QualityMetrics(
            avg_complexity=round(avg_complexity, 2),
            avg_maintainability=round(avg_maintainability, 2),
            avg_test_coverage=round(avg_coverage, 2),
            total_issues=total_issues,
            critical_issues=critical,
            high_issues=high,
            medium_issues=medium,
            low_issues=low
        )

    def get_team_efficiency(
        self,
        time_range: TimeRange = TimeRange.WEEK,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> TeamEfficiency:
        """Get team efficiency metrics."""
        filtered_reviews = self._filter_by_time_range(
            self.review_data, time_range, start_date, end_date
        )

        if not filtered_reviews:
            return TeamEfficiency()

        total_prs = len(set(r.get('pr_id') for r in filtered_reviews if r.get('pr_id')))

        # Time to first review
        first_review_times = [r.get('time_to_first_review_hours', 0) for r in filtered_reviews if r.get('time_to_first_review_hours')]
        avg_first_review = sum(first_review_times) / len(first_review_times) if first_review_times else 0.0

        # Time to merge
        merge_times = [r.get('time_to_merge_hours', 0) for r in filtered_reviews if r.get('time_to_merge_hours')]
        avg_merge = sum(merge_times) / len(merge_times) if merge_times else 0.0

        # Review throughput (reviews per day)
        days = self._get_days_in_range(time_range, start_date, end_date)
        throughput = len(filtered_reviews) / days if days > 0 else 0.0

        # Active reviewers
        active_reviewers = len(set(r.get('reviewer_id') for r in filtered_reviews if r.get('reviewer_id')))

        # Collaboration score (based on multiple reviewers per PR)
        pr_reviewer_counts = defaultdict(set)
        for review in filtered_reviews:
            pr_id = review.get('pr_id')
            reviewer_id = review.get('reviewer_id')
            if pr_id and reviewer_id:
                pr_reviewer_counts[pr_id].add(reviewer_id)

        multi_reviewer_prs = sum(1 for reviewers in pr_reviewer_counts.values() if len(reviewers) > 1)
        collaboration_score = (multi_reviewer_prs / total_prs * 100) if total_prs > 0 else 0.0

        return TeamEfficiency(
            total_prs=total_prs,
            avg_time_to_first_review_hours=round(avg_first_review, 2),
            avg_time_to_merge_hours=round(avg_merge, 2),
            review_throughput=round(throughput, 2),
            active_reviewers=active_reviewers,
            collaboration_score=round(collaboration_score, 2)
        )

    def export_data(
        self,
        dashboard_id: str,
        format: str = "json",
        time_range: TimeRange = TimeRange.WEEK,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Export dashboard data."""
        dashboard = self.get_dashboard(dashboard_id)
        if not dashboard:
            raise ValueError(f"Dashboard {dashboard_id} not found")

        data = {
            'dashboard': dashboard.to_dict(),
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'time_range': time_range.value,
            'data': {}
        }

        # Collect data for each widget
        for widget in dashboard.widgets:
            if widget.widget_type == WidgetType.REVIEW_STATS:
                data['data'][widget.widget_id] = self.get_review_stats(
                    time_range, start_date, end_date
                ).to_dict()
            elif widget.widget_type == WidgetType.REVIEWER_WORKLOAD:
                data['data'][widget.widget_id] = [
                    w.to_dict() for w in self.get_reviewer_workload(
                        time_range=time_range, start_date=start_date, end_date=end_date
                    )
                ]
            elif widget.widget_type == WidgetType.TIME_TRENDS:
                data['data'][widget.widget_id] = [
                    t.to_dict() for t in self.get_time_trends(
                        time_range, start_date, end_date
                    )
                ]
            elif widget.widget_type == WidgetType.QUALITY_METRICS:
                data['data'][widget.widget_id] = self.get_quality_metrics(
                    time_range, start_date, end_date
                ).to_dict()
            elif widget.widget_type == WidgetType.TEAM_EFFICIENCY:
                data['data'][widget.widget_id] = self.get_team_efficiency(
                    time_range, start_date, end_date
                ).to_dict()

        return data

    def _filter_by_time_range(
        self,
        data: List[Dict[str, Any]],
        time_range: TimeRange,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> List[Dict[str, Any]]:
        """Filter data by time range."""
        now = datetime.now(timezone.utc)

        if time_range == TimeRange.CUSTOM:
            if not start_date or not end_date:
                return data
            start = start_date
            end = end_date
        elif time_range == TimeRange.TODAY:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif time_range == TimeRange.WEEK:
            start = now - timedelta(days=7)
            end = now
        elif time_range == TimeRange.MONTH:
            start = now - timedelta(days=30)
            end = now
        elif time_range == TimeRange.QUARTER:
            start = now - timedelta(days=90)
            end = now
        elif time_range == TimeRange.YEAR:
            start = now - timedelta(days=365)
            end = now
        else:
            return data

        filtered = []
        for item in data:
            timestamp = datetime.fromisoformat(item['timestamp'])
            if start <= timestamp <= end:
                filtered.append(item)

        return filtered

    def _get_days_in_range(
        self,
        time_range: TimeRange,
        start_date: Optional[datetime],
        end_date: Optional[datetime]
    ) -> int:
        """Get number of days in time range."""
        if time_range == TimeRange.CUSTOM and start_date and end_date:
            return (end_date - start_date).days
        elif time_range == TimeRange.TODAY:
            return 1
        elif time_range == TimeRange.WEEK:
            return 7
        elif time_range == TimeRange.MONTH:
            return 30
        elif time_range == TimeRange.QUARTER:
            return 90
        elif time_range == TimeRange.YEAR:
            return 365
        return 1


# Global instance
_dashboard_system: Optional[DashboardSystem] = None


def get_dashboard_system() -> DashboardSystem:
    """Get global dashboard system instance."""
    global _dashboard_system
    if _dashboard_system is None:
        _dashboard_system = DashboardSystem()
    return _dashboard_system


def configure_dashboard_system(storage_path: Path):
    """Configure global dashboard system."""
    global _dashboard_system
    _dashboard_system = DashboardSystem(storage_path=storage_path)
