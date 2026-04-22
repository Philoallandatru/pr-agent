# Dashboard System

The Dashboard System provides comprehensive analytics and visualization for code review activities.

## Features

- **Custom Dashboards**: Create personalized dashboards with configurable widgets
- **Real-time Analytics**: Track review metrics, quality trends, and team efficiency
- **Multiple Widget Types**: Support for various visualization types
- **Time Range Filtering**: Analyze data across different time periods
- **Data Export**: Export dashboard data in JSON or CSV format
- **Auto-refresh**: Automatic data updates at configurable intervals

## Core Components

### Dashboard

A dashboard is a collection of widgets that display various metrics and analytics.

```python
from pr_agent.dashboard import DashboardSystem, TimeRange

system = DashboardSystem()

# Create a dashboard
dashboard = system.create_dashboard(
    dashboard_id="team-overview",
    name="Team Overview",
    description="Main team metrics dashboard",
    time_range=TimeRange.WEEK,
    auto_refresh=True,
    refresh_interval_seconds=300
)
```

### Widgets

Widgets are individual visualization components that display specific metrics.

**Available Widget Types:**
- `REVIEW_STATS`: Review statistics (total, completed, pending)
- `QUALITY_METRICS`: Code quality metrics (issues, complexity, coverage)
- `REVIEWER_WORKLOAD`: Reviewer workload distribution
- `TIME_TRENDS`: Time-based trend charts
- `ISSUE_DISTRIBUTION`: Issue severity distribution
- `TEAM_EFFICIENCY`: Team efficiency metrics
- `RECENT_REVIEWS`: Recent review activity
- `TOP_REVIEWERS`: Top reviewers by activity

```python
# Add a widget
widget = system.add_widget(
    dashboard_id="team-overview",
    widget_id="review-stats",
    widget_type="REVIEW_STATS",
    title="Review Statistics",
    position=(0, 0),  # Grid position (x, y)
    size=(4, 2),      # Grid size (width, height)
    config={
        "show_trends": True,
        "compare_previous": True
    }
)
```

## Analytics

### Review Statistics

Get comprehensive review statistics for a time period:

```python
from pr_agent.dashboard import TimeRange

# Get weekly stats
stats = system.get_review_stats(time_range=TimeRange.WEEK)

print(f"Total reviews: {stats.total_reviews}")
print(f"Completed: {stats.completed_reviews}")
print(f"Average time: {stats.avg_review_time_hours}h")
print(f"Issues found: {stats.total_issues}")
```

**Custom date range:**

```python
stats = system.get_review_stats(
    start_date="2024-01-01",
    end_date="2024-01-31"
)
```

### Reviewer Workload

Track reviewer workload and capacity:

```python
# Get workload for specific reviewer
workload = system.get_reviewer_workload(
    reviewer_id="alice",
    time_range=TimeRange.WEEK
)

print(f"Active reviews: {workload.active_reviews}")
print(f"Completed: {workload.completed_reviews}")
print(f"Avg time: {workload.avg_review_time_hours}h")

# Get all reviewers' workload
all_workload = system.get_reviewer_workload(time_range=TimeRange.WEEK)
for w in all_workload:
    print(f"{w.reviewer_id}: {w.active_reviews} active")
```

### Time Trends

Analyze trends over time:

```python
# Get review count trends
trends = system.get_time_trends(
    metric="reviews",
    time_range=TimeRange.MONTH
)

for trend in trends:
    print(f"{trend.timestamp}: {trend.value}")

# Available metrics:
# - "reviews": Review count
# - "issues": Issue count
# - "review_time": Average review time
# - "quality_score": Quality score
```

### Quality Metrics

Track code quality metrics:

```python
metrics = system.get_quality_metrics(time_range=TimeRange.WEEK)

print(f"Avg complexity: {metrics.avg_complexity}")
print(f"Avg coverage: {metrics.avg_coverage}%")
print(f"Critical issues: {metrics.critical_issues}")
print(f"Quality score: {metrics.quality_score}")
```

### Team Efficiency

Measure team efficiency:

```python
efficiency = system.get_team_efficiency(time_range=TimeRange.WEEK)

print(f"Avg review time: {efficiency.avg_review_time_hours}h")
print(f"Throughput: {efficiency.throughput_per_day} reviews/day")
print(f"First response: {efficiency.avg_first_response_hours}h")
print(f"Efficiency score: {efficiency.efficiency_score}")
```

## Recording Review Data

Record review data for analytics:

```python
system.record_review({
    "review_id": "rev-123",
    "repository": "myorg/myrepo",
    "pr_number": 456,
    "reviewer_id": "alice",
    "status": "completed",
    "review_time_hours": 2.5,
    "issues_found": 3,
    "complexity_score": 15,
    "coverage_percent": 85.5,
    "quality_score": 8.5,
    "timestamp": "2024-01-15T10:30:00Z"
})
```

## Data Export

Export dashboard data for external analysis:

```python
# Export as JSON
data = system.export_data(
    format="json",
    time_range=TimeRange.MONTH
)

# Export as CSV
csv_data = system.export_data(
    format="csv",
    time_range=TimeRange.MONTH
)
```

## REST API

### Create Dashboard

```http
POST /api/dashboards
Content-Type: application/json

{
  "dashboard_id": "team-overview",
  "name": "Team Overview",
  "description": "Main team metrics",
  "time_range": "week",
  "auto_refresh": true,
  "refresh_interval_seconds": 300
}
```

### List Dashboards

```http
GET /api/dashboards
```

### Get Dashboard

```http
GET /api/dashboards/{dashboard_id}
```

### Delete Dashboard

```http
DELETE /api/dashboards/{dashboard_id}
```

### Add Widget

```http
POST /api/dashboards/{dashboard_id}/widgets
Content-Type: application/json

{
  "widget_id": "review-stats",
  "widget_type": "REVIEW_STATS",
  "title": "Review Statistics",
  "position": {"x": 0, "y": 0},
  "size": {"w": 4, "h": 2},
  "config": {
    "show_trends": true
  }
}
```

### Remove Widget

```http
DELETE /api/dashboards/{dashboard_id}/widgets/{widget_id}
```

### Record Review

```http
POST /api/dashboards/reviews
Content-Type: application/json

{
  "review_id": "rev-123",
  "repository": "myorg/myrepo",
  "reviewer_id": "alice",
  "status": "completed",
  "review_time_hours": 2.5,
  "issues_found": 3
}
```

### Get Review Statistics

```http
GET /api/dashboards/stats/reviews?time_range=week
GET /api/dashboards/stats/reviews?start_date=2024-01-01&end_date=2024-01-31
```

### Get Reviewer Workload

```http
GET /api/dashboards/stats/workload?time_range=week
GET /api/dashboards/stats/workload?reviewer_id=alice&time_range=week
```

### Get Time Trends

```http
GET /api/dashboards/stats/trends?metric=reviews&time_range=month
```

### Get Quality Metrics

```http
GET /api/dashboards/stats/quality?time_range=week
```

### Get Team Efficiency

```http
GET /api/dashboards/stats/efficiency?time_range=week
```

### Export Data

```http
GET /api/dashboards/export?format=json&time_range=month
GET /api/dashboards/export?format=csv&time_range=month
```

## Time Ranges

Available time range options:
- `day`: Last 24 hours
- `week`: Last 7 days
- `month`: Last 30 days
- `year`: Last 365 days

Or use custom date ranges with `start_date` and `end_date`.

## Configuration

Dashboard settings in `configuration.toml`:

```toml
[dashboard]
# Storage path for dashboard data
storage_path = "~/.pr-agent/dashboards"

# Default time range
default_time_range = "week"

# Auto-refresh settings
auto_refresh_enabled = true
default_refresh_interval_seconds = 300

# Data retention
data_retention_days = 90

# Export settings
export_formats = ["json", "csv"]
```

## Best Practices

1. **Regular Data Recording**: Record review data consistently for accurate analytics
2. **Appropriate Time Ranges**: Use appropriate time ranges for different metrics
3. **Widget Organization**: Organize widgets logically on dashboards
4. **Auto-refresh**: Enable auto-refresh for real-time monitoring
5. **Data Export**: Regularly export data for backup and external analysis
6. **Custom Dashboards**: Create role-specific dashboards (team lead, developer, manager)

## Example: Complete Dashboard Setup

```python
from pr_agent.dashboard import DashboardSystem, TimeRange

system = DashboardSystem()

# Create dashboard
dashboard = system.create_dashboard(
    dashboard_id="team-dashboard",
    name="Team Dashboard",
    description="Comprehensive team metrics",
    time_range=TimeRange.WEEK
)

# Add widgets
system.add_widget(
    dashboard_id="team-dashboard",
    widget_id="review-stats",
    widget_type="REVIEW_STATS",
    title="Review Statistics",
    position=(0, 0),
    size=(4, 2)
)

system.add_widget(
    dashboard_id="team-dashboard",
    widget_id="quality-metrics",
    widget_type="QUALITY_METRICS",
    title="Code Quality",
    position=(4, 0),
    size=(4, 2)
)

system.add_widget(
    dashboard_id="team-dashboard",
    widget_id="workload",
    widget_type="REVIEWER_WORKLOAD",
    title="Reviewer Workload",
    position=(0, 2),
    size=(4, 3)
)

system.add_widget(
    dashboard_id="team-dashboard",
    widget_id="trends",
    widget_type="TIME_TRENDS",
    title="Review Trends",
    position=(4, 2),
    size=(4, 3)
)

# Record some reviews
system.record_review({
    "review_id": "rev-1",
    "repository": "myorg/myrepo",
    "reviewer_id": "alice",
    "status": "completed",
    "review_time_hours": 2.0,
    "issues_found": 2,
    "quality_score": 8.5
})

# Get analytics
stats = system.get_review_stats(time_range=TimeRange.WEEK)
print(f"Total reviews: {stats.total_reviews}")

workload = system.get_reviewer_workload(time_range=TimeRange.WEEK)
for w in workload:
    print(f"{w.reviewer_id}: {w.completed_reviews} completed")
```

## Troubleshooting

**Dashboard not updating:**
- Check auto-refresh settings
- Verify data is being recorded
- Check time range filters

**Missing data:**
- Ensure review data is being recorded with `record_review()`
- Check data retention settings
- Verify time range includes the data period

**Widget not displaying:**
- Verify widget type is valid
- Check widget configuration
- Ensure dashboard exists

**Export fails:**
- Check export format is supported
- Verify sufficient data exists
- Check file permissions for export path
