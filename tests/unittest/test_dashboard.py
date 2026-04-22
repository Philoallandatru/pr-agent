"""Tests for dashboard system."""

import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import shutil

from pr_agent.dashboard import (
    DashboardSystem,
    Dashboard,
    DashboardWidget,
    WidgetType,
    TimeRange,
    ReviewStats,
    ReviewerWorkload,
    TimeTrend,
    QualityMetrics,
    TeamEfficiency
)


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def dashboard_system(temp_storage):
    """Create dashboard system instance."""
    return DashboardSystem(storage_path=temp_storage)


@pytest.fixture
def sample_review_data():
    """Create sample review data."""
    now = datetime.now(timezone.utc)
    return [
        {
            'review_id': 'rev1',
            'pr_id': 'pr1',
            'reviewer_id': 'reviewer1',
            'reviewer_name': 'Alice',
            'status': 'completed',
            'result': 'approved',
            'review_time_hours': 2.5,
            'comment_count': 5,
            'timestamp': (now - timedelta(days=1)).isoformat(),
            'complexity': 15,
            'maintainability': 75,
            'test_coverage': 85,
            'time_to_first_review_hours': 1.0,
            'time_to_merge_hours': 4.0,
            'issues': [
                {'severity': 'high'},
                {'severity': 'medium'}
            ]
        },
        {
            'review_id': 'rev2',
            'pr_id': 'pr2',
            'reviewer_id': 'reviewer2',
            'reviewer_name': 'Bob',
            'status': 'pending',
            'review_time_hours': 0,
            'comment_count': 0,
            'timestamp': now.isoformat(),
            'complexity': 20,
            'maintainability': 60,
            'test_coverage': 70,
            'issues': []
        },
        {
            'review_id': 'rev3',
            'pr_id': 'pr1',
            'reviewer_id': 'reviewer1',
            'reviewer_name': 'Alice',
            'status': 'completed',
            'result': 'rejected',
            'review_time_hours': 3.0,
            'comment_count': 10,
            'timestamp': (now - timedelta(days=2)).isoformat(),
            'complexity': 25,
            'maintainability': 50,
            'test_coverage': 60,
            'time_to_first_review_hours': 2.0,
            'time_to_merge_hours': 0,
            'issues': [
                {'severity': 'critical'},
                {'severity': 'high'},
                {'severity': 'low'}
            ]
        }
    ]


class TestDashboard:
    """Test Dashboard class."""

    def test_dashboard_creation(self):
        """Test creating a dashboard."""
        dashboard = Dashboard(
            dashboard_id="dash1",
            name="Main Dashboard",
            description="Primary review dashboard",
            time_range=TimeRange.WEEK
        )

        assert dashboard.dashboard_id == "dash1"
        assert dashboard.name == "Main Dashboard"
        assert dashboard.time_range == TimeRange.WEEK
        assert dashboard.auto_refresh is True
        assert len(dashboard.widgets) == 0

    def test_dashboard_to_dict(self):
        """Test dashboard serialization."""
        dashboard = Dashboard(
            dashboard_id="dash1",
            name="Test",
            description="Test dashboard"
        )

        data = dashboard.to_dict()
        assert data['dashboard_id'] == "dash1"
        assert data['name'] == "Test"
        assert data['time_range'] == "week"


class TestDashboardWidget:
    """Test DashboardWidget class."""

    def test_widget_creation(self):
        """Test creating a widget."""
        widget = DashboardWidget(
            widget_id="widget1",
            widget_type=WidgetType.REVIEW_STATS,
            title="Review Statistics",
            position=(0, 0),
            size=(2, 1)
        )

        assert widget.widget_id == "widget1"
        assert widget.widget_type == WidgetType.REVIEW_STATS
        assert widget.position == (0, 0)
        assert widget.size == (2, 1)
        assert widget.enabled is True

    def test_widget_to_dict(self):
        """Test widget serialization."""
        widget = DashboardWidget(
            widget_id="widget1",
            widget_type=WidgetType.REVIEW_STATS,
            title="Stats",
            position=(0, 0),
            size=(1, 1)
        )

        data = widget.to_dict()
        assert data['widget_id'] == "widget1"
        assert data['widget_type'] == "review_stats"


class TestDashboardSystem:
    """Test DashboardSystem class."""

    def test_system_initialization(self, dashboard_system):
        """Test system initialization."""
        assert dashboard_system is not None
        assert len(dashboard_system.dashboards) == 0
        assert len(dashboard_system.review_data) == 0

    def test_create_dashboard(self, dashboard_system):
        """Test creating a dashboard."""
        dashboard = dashboard_system.create_dashboard(
            dashboard_id="dash1",
            name="Test Dashboard",
            description="Test",
            time_range=TimeRange.MONTH
        )

        assert dashboard.dashboard_id == "dash1"
        assert dashboard.name == "Test Dashboard"
        assert dashboard.time_range == TimeRange.MONTH

        # Verify it's stored
        assert "dash1" in dashboard_system.dashboards

    def test_add_widget(self, dashboard_system):
        """Test adding widget to dashboard."""
        dashboard_system.create_dashboard(
            dashboard_id="dash1",
            name="Test",
            description="Test"
        )

        widget = dashboard_system.add_widget(
            dashboard_id="dash1",
            widget_id="widget1",
            widget_type=WidgetType.REVIEW_STATS,
            title="Stats",
            position=(0, 0),
            size=(2, 1)
        )

        assert widget.widget_id == "widget1"
        dashboard = dashboard_system.get_dashboard("dash1")
        assert len(dashboard.widgets) == 1

    def test_remove_widget(self, dashboard_system):
        """Test removing widget from dashboard."""
        dashboard_system.create_dashboard(
            dashboard_id="dash1",
            name="Test",
            description="Test"
        )

        dashboard_system.add_widget(
            dashboard_id="dash1",
            widget_id="widget1",
            widget_type=WidgetType.REVIEW_STATS,
            title="Stats",
            position=(0, 0),
            size=(1, 1)
        )

        dashboard_system.remove_widget("dash1", "widget1")

        dashboard = dashboard_system.get_dashboard("dash1")
        assert len(dashboard.widgets) == 0

    def test_list_dashboards(self, dashboard_system):
        """Test listing dashboards."""
        dashboard_system.create_dashboard("dash1", "Dashboard 1", "Test 1")
        dashboard_system.create_dashboard("dash2", "Dashboard 2", "Test 2")

        dashboards = dashboard_system.list_dashboards()
        assert len(dashboards) == 2

    def test_delete_dashboard(self, dashboard_system):
        """Test deleting a dashboard."""
        dashboard_system.create_dashboard("dash1", "Test", "Test")
        dashboard_system.delete_dashboard("dash1")

        assert "dash1" not in dashboard_system.dashboards

    def test_record_review(self, dashboard_system):
        """Test recording review data."""
        review_data = {
            'review_id': 'rev1',
            'reviewer_id': 'reviewer1',
            'status': 'completed'
        }

        dashboard_system.record_review(review_data)

        assert len(dashboard_system.review_data) == 1
        assert 'timestamp' in dashboard_system.review_data[0]
        assert 'reviewer1' in dashboard_system.reviewer_data

    def test_get_review_stats(self, dashboard_system, sample_review_data):
        """Test getting review statistics."""
        for review in sample_review_data:
            dashboard_system.record_review(review)

        stats = dashboard_system.get_review_stats(TimeRange.WEEK)

        assert stats.total_reviews == 3
        assert stats.pending_reviews == 1
        assert stats.completed_reviews == 2
        assert stats.approved_reviews == 1
        assert stats.rejected_reviews == 1
        assert stats.avg_review_time_hours > 0
        assert stats.avg_comments_per_review > 0

    def test_get_review_stats_empty(self, dashboard_system):
        """Test getting stats with no data."""
        stats = dashboard_system.get_review_stats(TimeRange.WEEK)

        assert stats.total_reviews == 0
        assert stats.pending_reviews == 0
        assert stats.avg_review_time_hours == 0.0

    def test_get_reviewer_workload(self, dashboard_system, sample_review_data):
        """Test getting reviewer workload."""
        for review in sample_review_data:
            dashboard_system.record_review(review)

        workloads = dashboard_system.get_reviewer_workload(time_range=TimeRange.WEEK)

        assert len(workloads) == 2
        alice_workload = next(w for w in workloads if w.reviewer_id == 'reviewer1')
        assert alice_workload.completed_count == 2
        assert alice_workload.total_comments == 15

    def test_get_reviewer_workload_specific(self, dashboard_system, sample_review_data):
        """Test getting workload for specific reviewer."""
        for review in sample_review_data:
            dashboard_system.record_review(review)

        workloads = dashboard_system.get_reviewer_workload(
            reviewer_id='reviewer1',
            time_range=TimeRange.WEEK
        )

        assert len(workloads) == 1
        assert workloads[0].reviewer_id == 'reviewer1'

    def test_get_time_trends(self, dashboard_system, sample_review_data):
        """Test getting time trends."""
        for review in sample_review_data:
            dashboard_system.record_review(review)

        trends = dashboard_system.get_time_trends(
            time_range=TimeRange.WEEK,
            granularity="day"
        )

        assert len(trends) > 0
        assert all(isinstance(t, TimeTrend) for t in trends)
        assert all(hasattr(t, 'timestamp') for t in trends)

    def test_get_quality_metrics(self, dashboard_system, sample_review_data):
        """Test getting quality metrics."""
        for review in sample_review_data:
            dashboard_system.record_review(review)

        metrics = dashboard_system.get_quality_metrics(TimeRange.WEEK)

        assert metrics.avg_complexity > 0
        assert metrics.avg_maintainability > 0
        assert metrics.avg_test_coverage > 0
        assert metrics.total_issues == 5
        assert metrics.critical_issues == 1
        assert metrics.high_issues == 2
        assert metrics.medium_issues == 1
        assert metrics.low_issues == 1

    def test_get_team_efficiency(self, dashboard_system, sample_review_data):
        """Test getting team efficiency metrics."""
        for review in sample_review_data:
            dashboard_system.record_review(review)

        efficiency = dashboard_system.get_team_efficiency(TimeRange.WEEK)

        assert efficiency.total_prs == 2
        assert efficiency.active_reviewers == 2
        assert efficiency.avg_time_to_first_review_hours > 0
        assert efficiency.review_throughput > 0
        assert 0 <= efficiency.collaboration_score <= 100

    def test_export_data(self, dashboard_system, sample_review_data):
        """Test exporting dashboard data."""
        # Create dashboard with widgets
        dashboard_system.create_dashboard("dash1", "Test", "Test")
        dashboard_system.add_widget(
            "dash1", "widget1", WidgetType.REVIEW_STATS,
            "Stats", (0, 0), (1, 1)
        )
        dashboard_system.add_widget(
            "dash1", "widget2", WidgetType.QUALITY_METRICS,
            "Quality", (0, 1), (1, 1)
        )

        # Add review data
        for review in sample_review_data:
            dashboard_system.record_review(review)

        # Export
        data = dashboard_system.export_data("dash1", time_range=TimeRange.WEEK)

        assert 'dashboard' in data
        assert 'generated_at' in data
        assert 'data' in data
        assert 'widget1' in data['data']
        assert 'widget2' in data['data']

    def test_time_range_filtering(self, dashboard_system):
        """Test time range filtering."""
        now = datetime.now(timezone.utc)

        # Add reviews at different times
        dashboard_system.record_review({
            'review_id': 'rev1',
            'status': 'completed',
            'timestamp': (now - timedelta(days=1)).isoformat()
        })
        dashboard_system.record_review({
            'review_id': 'rev2',
            'status': 'completed',
            'timestamp': (now - timedelta(days=10)).isoformat()
        })
        dashboard_system.record_review({
            'review_id': 'rev3',
            'status': 'completed',
            'timestamp': (now - timedelta(days=40)).isoformat()
        })

        # Test different time ranges
        stats_week = dashboard_system.get_review_stats(TimeRange.WEEK)
        assert stats_week.total_reviews == 1

        stats_month = dashboard_system.get_review_stats(TimeRange.MONTH)
        assert stats_month.total_reviews == 2

        stats_quarter = dashboard_system.get_review_stats(TimeRange.QUARTER)
        assert stats_quarter.total_reviews == 3

    def test_custom_time_range(self, dashboard_system):
        """Test custom time range."""
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=5)
        end = now

        dashboard_system.record_review({
            'review_id': 'rev1',
            'status': 'completed',
            'timestamp': (now - timedelta(days=3)).isoformat()
        })

        stats = dashboard_system.get_review_stats(
            TimeRange.CUSTOM,
            start_date=start,
            end_date=end
        )

        assert stats.total_reviews == 1

    def test_persistence(self, temp_storage):
        """Test dashboard persistence."""
        # Create system and dashboard
        system1 = DashboardSystem(storage_path=temp_storage)
        system1.create_dashboard("dash1", "Test", "Test")
        system1.add_widget(
            "dash1", "widget1", WidgetType.REVIEW_STATS,
            "Stats", (0, 0), (1, 1)
        )

        # Create new system instance (should load from storage)
        system2 = DashboardSystem(storage_path=temp_storage)
        dashboard = system2.get_dashboard("dash1")

        assert dashboard is not None
        assert dashboard.dashboard_id == "dash1"
        assert len(dashboard.widgets) == 1


class TestReviewStats:
    """Test ReviewStats class."""

    def test_stats_creation(self):
        """Test creating review stats."""
        stats = ReviewStats(
            total_reviews=10,
            pending_reviews=2,
            completed_reviews=8,
            avg_review_time_hours=2.5
        )

        assert stats.total_reviews == 10
        assert stats.pending_reviews == 2
        assert stats.avg_review_time_hours == 2.5

    def test_stats_to_dict(self):
        """Test stats serialization."""
        stats = ReviewStats(total_reviews=5)
        data = stats.to_dict()

        assert data['total_reviews'] == 5
        assert 'avg_review_time_hours' in data


class TestReviewerWorkload:
    """Test ReviewerWorkload class."""

    def test_workload_creation(self):
        """Test creating reviewer workload."""
        workload = ReviewerWorkload(
            reviewer_id="rev1",
            reviewer_name="Alice",
            completed_count=10,
            approval_rate=85.5
        )

        assert workload.reviewer_id == "rev1"
        assert workload.reviewer_name == "Alice"
        assert workload.approval_rate == 85.5


class TestTimeTrend:
    """Test TimeTrend class."""

    def test_trend_creation(self):
        """Test creating time trend."""
        now = datetime.now(timezone.utc)
        trend = TimeTrend(
            timestamp=now,
            completed_count=5,
            avg_review_time_hours=2.0
        )

        assert trend.timestamp == now
        assert trend.completed_count == 5

    def test_trend_to_dict(self):
        """Test trend serialization."""
        now = datetime.now(timezone.utc)
        trend = TimeTrend(timestamp=now, completed_count=5)
        data = trend.to_dict()

        assert 'timestamp' in data
        assert isinstance(data['timestamp'], str)


class TestQualityMetrics:
    """Test QualityMetrics class."""

    def test_metrics_creation(self):
        """Test creating quality metrics."""
        metrics = QualityMetrics(
            avg_complexity=15.5,
            total_issues=10,
            critical_issues=2
        )

        assert metrics.avg_complexity == 15.5
        assert metrics.total_issues == 10
        assert metrics.critical_issues == 2


class TestTeamEfficiency:
    """Test TeamEfficiency class."""

    def test_efficiency_creation(self):
        """Test creating team efficiency."""
        efficiency = TeamEfficiency(
            total_prs=50,
            active_reviewers=5,
            collaboration_score=75.0
        )

        assert efficiency.total_prs == 50
        assert efficiency.active_reviewers == 5
        assert efficiency.collaboration_score == 75.0
