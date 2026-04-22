"""
Code Metrics Module

Provides code metrics analysis and reporting.
"""

from pr_agent.metrics.analyzer import (
    MetricsAnalyzer,
    get_metrics_analyzer,
    FileMetrics,
    ProjectMetrics,
    MetricsTrend,
    MetricType,
    Severity,
)

__all__ = [
    "MetricsAnalyzer",
    "get_metrics_analyzer",
    "FileMetrics",
    "ProjectMetrics",
    "MetricsTrend",
    "MetricType",
    "Severity",
]
