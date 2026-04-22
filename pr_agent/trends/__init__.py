"""
Code quality trends analysis module.

Provides tools for tracking and analyzing code quality metrics over time.
"""

from pr_agent.trends.analyzer import (
    TrendsAnalyzer,
    MetricSnapshot,
    TrendAnalysis,
    QualityDegradation,
    TrendReport,
    MetricType,
    TrendDirection,
    visualize_trend,
    visualize_report,
)

__all__ = [
    "TrendsAnalyzer",
    "MetricSnapshot",
    "TrendAnalysis",
    "QualityDegradation",
    "TrendReport",
    "MetricType",
    "TrendDirection",
    "visualize_trend",
    "visualize_report",
]
