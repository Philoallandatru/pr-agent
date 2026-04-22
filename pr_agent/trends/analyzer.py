"""
Code quality trends analysis system.

This module provides functionality to track and analyze code quality metrics over time,
detect quality degradation, and generate trend reports.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of quality metrics."""
    COMPLEXITY = "complexity"
    MAINTAINABILITY = "maintainability"
    COVERAGE = "coverage"
    DUPLICATION = "duplication"
    ISSUES = "issues"
    LOC = "loc"
    TECHNICAL_DEBT = "technical_debt"


class TrendDirection(str, Enum):
    """Trend direction."""
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"


@dataclass
class MetricSnapshot:
    """A snapshot of a quality metric at a point in time."""
    timestamp: str
    metric_type: MetricType
    value: float
    file_path: Optional[str] = None
    commit_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrendAnalysis:
    """Analysis of a metric trend."""
    metric_type: MetricType
    direction: TrendDirection
    change_percentage: float
    current_value: float
    previous_value: float
    average_value: float
    min_value: float
    max_value: float
    data_points: int
    prediction: Optional[float] = None
    confidence: float = 0.0


@dataclass
class QualityDegradation:
    """Detected quality degradation."""
    metric_type: MetricType
    file_path: Optional[str]
    severity: str  # "low", "medium", "high", "critical"
    change_percentage: float
    old_value: float
    new_value: float
    timestamp: str
    description: str


@dataclass
class TrendReport:
    """Comprehensive trend analysis report."""
    repository: str
    start_date: str
    end_date: str
    trends: List[TrendAnalysis]
    degradations: List[QualityDegradation]
    summary: Dict[str, Any]
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TrendsAnalyzer:
    """Analyzes code quality trends over time."""

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize the trends analyzer.

        Args:
            storage_path: Path to store trend data (default: .pr_agent/trends)
        """
        self.storage_path = storage_path or Path.cwd() / ".pr_agent" / "trends"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.snapshots_file = self.storage_path / "snapshots.jsonl"

    def record_snapshot(self, snapshot: MetricSnapshot) -> None:
        """
        Record a quality metric snapshot.

        Args:
            snapshot: The metric snapshot to record
        """
        try:
            with open(self.snapshots_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(snapshot)) + "\n")
            logger.info(f"Recorded snapshot: {snapshot.metric_type} = {snapshot.value}")
        except Exception as e:
            logger.error(f"Failed to record snapshot: {e}")
            raise

    def record_metrics(self, metrics: Dict[MetricType, float],
                      file_path: Optional[str] = None,
                      commit_hash: Optional[str] = None) -> None:
        """
        Record multiple metrics at once.

        Args:
            metrics: Dictionary of metric types to values
            file_path: Optional file path for file-specific metrics
            commit_hash: Optional commit hash
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        for metric_type, value in metrics.items():
            snapshot = MetricSnapshot(
                timestamp=timestamp,
                metric_type=metric_type,
                value=value,
                file_path=file_path,
                commit_hash=commit_hash
            )
            self.record_snapshot(snapshot)

    def get_snapshots(self,
                     metric_type: Optional[MetricType] = None,
                     file_path: Optional[str] = None,
                     start_date: Optional[datetime] = None,
                     end_date: Optional[datetime] = None) -> List[MetricSnapshot]:
        """
        Retrieve metric snapshots with optional filtering.

        Args:
            metric_type: Filter by metric type
            file_path: Filter by file path
            start_date: Filter by start date
            end_date: Filter by end date

        Returns:
            List of matching snapshots
        """
        if not self.snapshots_file.exists():
            return []

        snapshots = []
        try:
            with open(self.snapshots_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    snapshot = MetricSnapshot(**data)

                    # Apply filters
                    if metric_type and snapshot.metric_type != metric_type:
                        continue
                    if file_path and snapshot.file_path != file_path:
                        continue

                    snapshot_time = datetime.fromisoformat(snapshot.timestamp)
                    if start_date and snapshot_time < start_date:
                        continue
                    if end_date and snapshot_time > end_date:
                        continue

                    snapshots.append(snapshot)
        except Exception as e:
            logger.error(f"Failed to read snapshots: {e}")
            raise

        return sorted(snapshots, key=lambda s: s.timestamp)

    def analyze_trend(self, metric_type: MetricType,
                     days: int = 30,
                     file_path: Optional[str] = None) -> TrendAnalysis:
        """
        Analyze trend for a specific metric.

        Args:
            metric_type: The metric to analyze
            days: Number of days to analyze
            file_path: Optional file path filter

        Returns:
            Trend analysis result
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        snapshots = self.get_snapshots(
            metric_type=metric_type,
            file_path=file_path,
            start_date=start_date,
            end_date=end_date
        )

        if len(snapshots) < 2:
            # Not enough data
            current_value = snapshots[0].value if snapshots else 0.0
            return TrendAnalysis(
                metric_type=metric_type,
                direction=TrendDirection.STABLE,
                change_percentage=0.0,
                current_value=current_value,
                previous_value=current_value,
                average_value=current_value,
                min_value=current_value,
                max_value=current_value,
                data_points=len(snapshots)
            )

        values = [s.value for s in snapshots]
        current_value = values[-1]
        previous_value = values[0]

        # Calculate statistics
        average_value = sum(values) / len(values)
        min_value = min(values)
        max_value = max(values)

        # Calculate change percentage
        if previous_value != 0:
            change_percentage = ((current_value - previous_value) / previous_value) * 100
        else:
            change_percentage = 0.0

        # Determine direction
        if abs(change_percentage) < 5:
            direction = TrendDirection.STABLE
        elif self._is_improving(metric_type, change_percentage):
            direction = TrendDirection.IMPROVING
        else:
            direction = TrendDirection.DEGRADING

        # Simple linear prediction
        prediction = None
        confidence = 0.0
        if len(values) >= 3:
            prediction, confidence = self._predict_next_value(values)

        return TrendAnalysis(
            metric_type=metric_type,
            direction=direction,
            change_percentage=change_percentage,
            current_value=current_value,
            previous_value=previous_value,
            average_value=average_value,
            min_value=min_value,
            max_value=max_value,
            data_points=len(snapshots),
            prediction=prediction,
            confidence=confidence
        )

    def _is_improving(self, metric_type: MetricType, change_percentage: float) -> bool:
        """
        Determine if a change is an improvement based on metric type.

        Args:
            metric_type: The metric type
            change_percentage: The percentage change

        Returns:
            True if improving, False otherwise
        """
        # For these metrics, lower is better
        lower_is_better = {
            MetricType.COMPLEXITY,
            MetricType.DUPLICATION,
            MetricType.ISSUES,
            MetricType.TECHNICAL_DEBT
        }

        # For these metrics, higher is better
        higher_is_better = {
            MetricType.MAINTAINABILITY,
            MetricType.COVERAGE
        }

        if metric_type in lower_is_better:
            return change_percentage < 0
        elif metric_type in higher_is_better:
            return change_percentage > 0
        else:
            # For LOC and others, stable is good
            return abs(change_percentage) < 10

    def _predict_next_value(self, values: List[float]) -> Tuple[float, float]:
        """
        Predict the next value using simple linear regression.

        Args:
            values: Historical values

        Returns:
            Tuple of (predicted_value, confidence)
        """
        n = len(values)
        x = list(range(n))

        # Calculate linear regression
        x_mean = sum(x) / n
        y_mean = sum(values) / n

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return values[-1], 0.0

        slope = numerator / denominator
        intercept = y_mean - slope * x_mean

        # Predict next value
        prediction = slope * n + intercept

        # Calculate R-squared for confidence
        y_pred = [slope * x[i] + intercept for i in range(n)]
        ss_res = sum((values[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((values[i] - y_mean) ** 2 for i in range(n))

        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
        confidence = max(0.0, min(1.0, r_squared))

        return prediction, confidence

    def detect_degradations(self,
                          threshold_percentage: float = 10.0,
                          days: int = 7) -> List[QualityDegradation]:
        """
        Detect quality degradations.

        Args:
            threshold_percentage: Minimum percentage change to consider degradation
            days: Number of days to check

        Returns:
            List of detected degradations
        """
        degradations = []

        for metric_type in MetricType:
            trend = self.analyze_trend(metric_type, days=days)

            if trend.direction == TrendDirection.DEGRADING and \
               abs(trend.change_percentage) >= threshold_percentage:

                # Determine severity
                if abs(trend.change_percentage) >= 50:
                    severity = "critical"
                elif abs(trend.change_percentage) >= 30:
                    severity = "high"
                elif abs(trend.change_percentage) >= 20:
                    severity = "medium"
                else:
                    severity = "low"

                degradation = QualityDegradation(
                    metric_type=metric_type,
                    file_path=None,
                    severity=severity,
                    change_percentage=trend.change_percentage,
                    old_value=trend.previous_value,
                    new_value=trend.current_value,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    description=f"{metric_type.value} degraded by {abs(trend.change_percentage):.1f}%"
                )
                degradations.append(degradation)

        return degradations

    def generate_report(self,
                       days: int = 30,
                       repository: str = "unknown") -> TrendReport:
        """
        Generate a comprehensive trend report.

        Args:
            days: Number of days to analyze
            repository: Repository name

        Returns:
            Trend report
        """
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        # Analyze trends for all metrics
        trends = []
        for metric_type in MetricType:
            trend = self.analyze_trend(metric_type, days=days)
            if trend.data_points > 0:
                trends.append(trend)

        # Detect degradations
        degradations = self.detect_degradations(days=days)

        # Generate summary
        improving_count = sum(1 for t in trends if t.direction == TrendDirection.IMPROVING)
        stable_count = sum(1 for t in trends if t.direction == TrendDirection.STABLE)
        degrading_count = sum(1 for t in trends if t.direction == TrendDirection.DEGRADING)

        summary = {
            "total_metrics": len(trends),
            "improving": improving_count,
            "stable": stable_count,
            "degrading": degrading_count,
            "degradations_detected": len(degradations),
            "critical_degradations": sum(1 for d in degradations if d.severity == "critical"),
            "overall_health": self._calculate_health_score(trends)
        }

        return TrendReport(
            repository=repository,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            trends=trends,
            degradations=degradations,
            summary=summary
        )

    def _calculate_health_score(self, trends: List[TrendAnalysis]) -> float:
        """
        Calculate overall health score (0-100).

        Args:
            trends: List of trend analyses

        Returns:
            Health score
        """
        if not trends:
            return 50.0

        score = 0.0
        for trend in trends:
            if trend.direction == TrendDirection.IMPROVING:
                score += 100
            elif trend.direction == TrendDirection.STABLE:
                score += 70
            else:  # DEGRADING
                score += 30

        return score / len(trends)


def visualize_trend(trend: TrendAnalysis) -> str:
    """
    Generate a text visualization of a trend.

    Args:
        trend: The trend to visualize

    Returns:
        Text visualization
    """
    direction_symbol = {
        TrendDirection.IMPROVING: "↑",
        TrendDirection.STABLE: "→",
        TrendDirection.DEGRADING: "↓"
    }

    lines = [
        f"Metric: {trend.metric_type.value}",
        f"Direction: {direction_symbol[trend.direction]} {trend.direction.value}",
        f"Change: {trend.change_percentage:+.1f}%",
        f"Current: {trend.current_value:.2f}",
        f"Previous: {trend.previous_value:.2f}",
        f"Average: {trend.average_value:.2f}",
        f"Range: {trend.min_value:.2f} - {trend.max_value:.2f}",
        f"Data Points: {trend.data_points}"
    ]

    if trend.prediction is not None:
        lines.append(f"Prediction: {trend.prediction:.2f} (confidence: {trend.confidence:.1%})")

    return "\n".join(lines)


def visualize_report(report: TrendReport) -> str:
    """
    Generate a text visualization of a trend report.

    Args:
        report: The report to visualize

    Returns:
        Text visualization
    """
    lines = [
        "=" * 60,
        f"Quality Trends Report: {report.repository}",
        f"Period: {report.start_date[:10]} to {report.end_date[:10]}",
        "=" * 60,
        "",
        "Summary:",
        f"  Overall Health: {report.summary['overall_health']:.1f}/100",
        f"  Improving: {report.summary['improving']}",
        f"  Stable: {report.summary['stable']}",
        f"  Degrading: {report.summary['degrading']}",
        f"  Degradations Detected: {report.summary['degradations_detected']}",
        ""
    ]

    if report.degradations:
        lines.append("⚠️  Quality Degradations:")
        for deg in report.degradations:
            lines.append(f"  [{deg.severity.upper()}] {deg.description}")
        lines.append("")

    lines.append("Trends:")
    for trend in report.trends:
        lines.append("")
        lines.append(visualize_trend(trend))

    lines.append("")
    lines.append("=" * 60)

    return "\n".join(lines)
