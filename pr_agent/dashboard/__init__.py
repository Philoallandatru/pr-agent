"""Dashboard system for code review analytics."""

from pr_agent.dashboard.dashboard import (
    DashboardSystem,
    Dashboard,
    DashboardWidget,
    WidgetType,
    TimeRange,
    ReviewStats,
    ReviewerWorkload,
    TimeTrend,
    QualityMetrics,
    TeamEfficiency,
    get_dashboard_system,
    configure_dashboard_system
)

__all__ = [
    "DashboardSystem",
    "Dashboard",
    "DashboardWidget",
    "WidgetType",
    "TimeRange",
    "ReviewStats",
    "ReviewerWorkload",
    "TimeTrend",
    "QualityMetrics",
    "TeamEfficiency",
    "get_dashboard_system",
    "configure_dashboard_system"
]
