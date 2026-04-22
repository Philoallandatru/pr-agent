"""
Tests for code quality trends analysis system.
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from pr_agent.trends import (
    TrendsAnalyzer,
    MetricSnapshot,
    MetricType,
    TrendDirection,
    visualize_trend,
    visualize_report,
)


@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary storage for trends."""
    return tmp_path / "trends"


@pytest.fixture
def analyzer(temp_storage):
    """Create a trends analyzer."""
    return TrendsAnalyzer(temp_storage)


class TestMetricSnapshot:
    """Test MetricSnapshot."""

    def test_snapshot_creation(self):
        """Test creating a metric snapshot."""
        snapshot = MetricSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            metric_type=MetricType.COMPLEXITY,
            value=10.5
        )
        assert snapshot.metric_type == MetricType.COMPLEXITY
        assert snapshot.value == 10.5

    def test_snapshot_with_metadata(self):
        """Test snapshot with metadata."""
        snapshot = MetricSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            metric_type=MetricType.COVERAGE,
            value=85.0,
            file_path="test.py",
            commit_hash="abc123",
            metadata={"branch": "main"}
        )
        assert snapshot.file_path == "test.py"
        assert snapshot.commit_hash == "abc123"
        assert snapshot.metadata["branch"] == "main"


class TestTrendsAnalyzer:
    """Test TrendsAnalyzer."""

    def test_analyzer_creation(self, analyzer, temp_storage):
        """Test analyzer creation."""
        assert analyzer.storage_path == temp_storage
        assert temp_storage.exists()

    def test_record_snapshot(self, analyzer):
        """Test recording a snapshot."""
        snapshot = MetricSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            metric_type=MetricType.COMPLEXITY,
            value=10.0
        )
        analyzer.record_snapshot(snapshot)

        # Verify file was created
        assert analyzer.snapshots_file.exists()

    def test_record_multiple_snapshots(self, analyzer):
        """Test recording multiple snapshots."""
        for i in range(5):
            snapshot = MetricSnapshot(
                timestamp=datetime.now(timezone.utc).isoformat(),
                metric_type=MetricType.COMPLEXITY,
                value=10.0 + i
            )
            analyzer.record_snapshot(snapshot)

        snapshots = analyzer.get_snapshots()
        assert len(snapshots) == 5

    def test_record_metrics(self, analyzer):
        """Test recording multiple metrics at once."""
        metrics = {
            MetricType.COMPLEXITY: 10.0,
            MetricType.COVERAGE: 85.0,
            MetricType.MAINTAINABILITY: 75.0
        }
        analyzer.record_metrics(metrics)

        snapshots = analyzer.get_snapshots()
        assert len(snapshots) == 3

    def test_get_snapshots_by_type(self, analyzer):
        """Test filtering snapshots by type."""
        analyzer.record_metrics({
            MetricType.COMPLEXITY: 10.0,
            MetricType.COVERAGE: 85.0
        })

        complexity_snapshots = analyzer.get_snapshots(metric_type=MetricType.COMPLEXITY)
        assert len(complexity_snapshots) == 1
        assert complexity_snapshots[0].metric_type == MetricType.COMPLEXITY

    def test_get_snapshots_by_date(self, analyzer):
        """Test filtering snapshots by date."""
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)

        # Record old snapshot
        old_snapshot = MetricSnapshot(
            timestamp=yesterday.isoformat(),
            metric_type=MetricType.COMPLEXITY,
            value=10.0
        )
        analyzer.record_snapshot(old_snapshot)

        # Record new snapshot
        new_snapshot = MetricSnapshot(
            timestamp=now.isoformat(),
            metric_type=MetricType.COMPLEXITY,
            value=12.0
        )
        analyzer.record_snapshot(new_snapshot)

        # Filter by date
        recent = analyzer.get_snapshots(start_date=now - timedelta(hours=1))
        assert len(recent) == 1
        assert recent[0].value == 12.0


class TestTrendAnalysis:
    """Test trend analysis."""

    def test_analyze_trend_insufficient_data(self, analyzer):
        """Test trend analysis with insufficient data."""
        trend = analyzer.analyze_trend(MetricType.COMPLEXITY, days=30)
        assert trend.direction == TrendDirection.STABLE
        assert trend.data_points == 0

    def test_analyze_trend_improving(self, analyzer):
        """Test detecting improving trend."""
        # Record decreasing complexity (improvement)
        base_time = datetime.now(timezone.utc)
        for i in range(5):
            snapshot = MetricSnapshot(
                timestamp=(base_time - timedelta(days=4-i)).isoformat(),
                metric_type=MetricType.COMPLEXITY,
                value=20.0 - i * 2  # Decreasing
            )
            analyzer.record_snapshot(snapshot)

        trend = analyzer.analyze_trend(MetricType.COMPLEXITY, days=30)
        assert trend.direction == TrendDirection.IMPROVING
        assert trend.change_percentage < 0

    def test_analyze_trend_degrading(self, analyzer):
        """Test detecting degrading trend."""
        # Record increasing complexity (degradation)
        base_time = datetime.now(timezone.utc)
        for i in range(5):
            snapshot = MetricSnapshot(
                timestamp=(base_time - timedelta(days=4-i)).isoformat(),
                metric_type=MetricType.COMPLEXITY,
                value=10.0 + i * 2  # Increasing
            )
            analyzer.record_snapshot(snapshot)

        trend = analyzer.analyze_trend(MetricType.COMPLEXITY, days=30)
        assert trend.direction == TrendDirection.DEGRADING
        assert trend.change_percentage > 0

    def test_analyze_trend_stable(self, analyzer):
        """Test detecting stable trend."""
        # Record stable values
        base_time = datetime.now(timezone.utc)
        for i in range(5):
            snapshot = MetricSnapshot(
                timestamp=(base_time - timedelta(days=4-i)).isoformat(),
                metric_type=MetricType.COMPLEXITY,
                value=10.0  # Constant
            )
            analyzer.record_snapshot(snapshot)

        trend = analyzer.analyze_trend(MetricType.COMPLEXITY, days=30)
        assert trend.direction == TrendDirection.STABLE
        assert abs(trend.change_percentage) < 5

    def test_trend_statistics(self, analyzer):
        """Test trend statistics calculation."""
        values = [10.0, 12.0, 11.0, 13.0, 14.0]
        base_time = datetime.now(timezone.utc)

        for i, value in enumerate(values):
            snapshot = MetricSnapshot(
                timestamp=(base_time - timedelta(days=len(values)-1-i)).isoformat(),
                metric_type=MetricType.COMPLEXITY,
                value=value
            )
            analyzer.record_snapshot(snapshot)

        trend = analyzer.analyze_trend(MetricType.COMPLEXITY, days=30)
        assert trend.min_value == 10.0
        assert trend.max_value == 14.0
        assert trend.average_value == 12.0
        assert trend.data_points == 5

    def test_trend_prediction(self, analyzer):
        """Test trend prediction."""
        # Record linear increasing trend
        base_time = datetime.now(timezone.utc)
        for i in range(10):
            snapshot = MetricSnapshot(
                timestamp=(base_time - timedelta(days=9-i)).isoformat(),
                metric_type=MetricType.COMPLEXITY,
                value=10.0 + i * 1.0
            )
            analyzer.record_snapshot(snapshot)

        trend = analyzer.analyze_trend(MetricType.COMPLEXITY, days=30)
        assert trend.prediction is not None
        assert trend.confidence > 0.8  # Should have high confidence for linear trend


class TestDegradationDetection:
    """Test quality degradation detection."""

    def test_detect_no_degradations(self, analyzer):
        """Test when no degradations exist."""
        # Record stable metrics
        base_time = datetime.now(timezone.utc)
        for i in range(5):
            analyzer.record_metrics({
                MetricType.COMPLEXITY: 10.0,
                MetricType.COVERAGE: 85.0
            })

        degradations = analyzer.detect_degradations(days=7)
        assert len(degradations) == 0

    def test_detect_degradation(self, analyzer):
        """Test detecting quality degradation."""
        base_time = datetime.now(timezone.utc)

        # Record initial good values
        for i in range(3):
            snapshot = MetricSnapshot(
                timestamp=(base_time - timedelta(days=6-i)).isoformat(),
                metric_type=MetricType.COMPLEXITY,
                value=10.0
            )
            analyzer.record_snapshot(snapshot)

        # Record degraded values
        for i in range(3):
            snapshot = MetricSnapshot(
                timestamp=(base_time - timedelta(days=2-i)).isoformat(),
                metric_type=MetricType.COMPLEXITY,
                value=15.0  # 50% increase
            )
            analyzer.record_snapshot(snapshot)

        degradations = analyzer.detect_degradations(threshold_percentage=10.0, days=7)
        assert len(degradations) > 0
        assert any(d.metric_type == MetricType.COMPLEXITY for d in degradations)

    def test_degradation_severity(self, analyzer):
        """Test degradation severity classification."""
        base_time = datetime.now(timezone.utc)

        # Record critical degradation (>50% change)
        snapshot1 = MetricSnapshot(
            timestamp=(base_time - timedelta(days=6)).isoformat(),
            metric_type=MetricType.COMPLEXITY,
            value=10.0
        )
        analyzer.record_snapshot(snapshot1)

        snapshot2 = MetricSnapshot(
            timestamp=base_time.isoformat(),
            metric_type=MetricType.COMPLEXITY,
            value=20.0  # 100% increase
        )
        analyzer.record_snapshot(snapshot2)

        degradations = analyzer.detect_degradations(days=7)
        complexity_deg = [d for d in degradations if d.metric_type == MetricType.COMPLEXITY]
        if complexity_deg:
            assert complexity_deg[0].severity == "critical"


class TestReportGeneration:
    """Test report generation."""

    def test_generate_empty_report(self, analyzer):
        """Test generating report with no data."""
        report = analyzer.generate_report(days=30, repository="test-repo")
        assert report.repository == "test-repo"
        assert len(report.trends) == 0
        assert len(report.degradations) == 0

    def test_generate_report_with_data(self, analyzer):
        """Test generating report with data."""
        # Record some metrics
        base_time = datetime.now(timezone.utc)
        for i in range(5):
            analyzer.record_metrics({
                MetricType.COMPLEXITY: 10.0 + i,
                MetricType.COVERAGE: 85.0 - i
            })

        report = analyzer.generate_report(days=30, repository="test-repo")
        assert len(report.trends) > 0
        assert "overall_health" in report.summary
        assert 0 <= report.summary["overall_health"] <= 100

    def test_report_summary(self, analyzer):
        """Test report summary statistics."""
        # Record mixed trends
        base_time = datetime.now(timezone.utc)
        for i in range(5):
            snapshot1 = MetricSnapshot(
                timestamp=(base_time - timedelta(days=4-i)).isoformat(),
                metric_type=MetricType.COMPLEXITY,
                value=20.0 - i  # Improving
            )
            snapshot2 = MetricSnapshot(
                timestamp=(base_time - timedelta(days=4-i)).isoformat(),
                metric_type=MetricType.COVERAGE,
                value=80.0  # Stable
            )
            analyzer.record_snapshot(snapshot1)
            analyzer.record_snapshot(snapshot2)

        report = analyzer.generate_report(days=30)
        assert report.summary["improving"] >= 0
        assert report.summary["stable"] >= 0
        assert report.summary["degrading"] >= 0


class TestVisualization:
    """Test visualization functions."""

    def test_visualize_trend(self, analyzer):
        """Test trend visualization."""
        # Create trend data
        base_time = datetime.now(timezone.utc)
        for i in range(5):
            snapshot = MetricSnapshot(
                timestamp=(base_time - timedelta(days=4-i)).isoformat(),
                metric_type=MetricType.COMPLEXITY,
                value=10.0 + i
            )
            analyzer.record_snapshot(snapshot)

        trend = analyzer.analyze_trend(MetricType.COMPLEXITY, days=30)
        text = visualize_trend(trend)

        assert "Metric: complexity" in text
        assert "Direction:" in text
        assert "Change:" in text

    def test_visualize_report(self, analyzer):
        """Test report visualization."""
        # Record some data
        analyzer.record_metrics({
            MetricType.COMPLEXITY: 10.0,
            MetricType.COVERAGE: 85.0
        })

        report = analyzer.generate_report(days=30, repository="test-repo")
        text = visualize_report(report)

        assert "Quality Trends Report" in text
        assert "test-repo" in text
        assert "Overall Health" in text


class TestMetricTypes:
    """Test different metric types."""

    def test_all_metric_types(self, analyzer):
        """Test recording all metric types."""
        metrics = {
            MetricType.COMPLEXITY: 10.0,
            MetricType.MAINTAINABILITY: 75.0,
            MetricType.COVERAGE: 85.0,
            MetricType.DUPLICATION: 5.0,
            MetricType.ISSUES: 3.0,
            MetricType.LOC: 1000.0,
            MetricType.TECHNICAL_DEBT: 2.5
        }
        analyzer.record_metrics(metrics)

        snapshots = analyzer.get_snapshots()
        assert len(snapshots) == len(MetricType)

    def test_metric_improvement_direction(self, analyzer):
        """Test that improvement direction is correct for each metric."""
        # For complexity, lower is better
        base_time = datetime.now(timezone.utc)
        for i in range(5):
            snapshot = MetricSnapshot(
                timestamp=(base_time - timedelta(days=4-i)).isoformat(),
                metric_type=MetricType.COMPLEXITY,
                value=20.0 - i * 2  # Decreasing
            )
            analyzer.record_snapshot(snapshot)

        trend = analyzer.analyze_trend(MetricType.COMPLEXITY, days=30)
        assert trend.direction == TrendDirection.IMPROVING

        # For coverage, higher is better
        analyzer2 = TrendsAnalyzer(analyzer.storage_path.parent / "trends2")
        for i in range(5):
            snapshot = MetricSnapshot(
                timestamp=(base_time - timedelta(days=4-i)).isoformat(),
                metric_type=MetricType.COVERAGE,
                value=70.0 + i * 2  # Increasing
            )
            analyzer2.record_snapshot(snapshot)

        trend2 = analyzer2.analyze_trend(MetricType.COVERAGE, days=30)
        assert trend2.direction == TrendDirection.IMPROVING
