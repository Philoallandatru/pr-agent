# Analytics and Reporting Guide

Comprehensive analytics and reporting system for PR-Agent.

## Overview

The analytics module provides:

- **Code Quality Trends**: Track quality metrics over time
- **Team Efficiency**: Analyze team productivity and patterns
- **Review Quality Scoring**: Automated quality assessment
- **Repository Comparison**: Compare metrics across repositories
- **Custom Reports**: Generate reports in multiple formats

## Features

### 1. Code Quality Trends

Track code review quality metrics over time:

```python
from pr_agent.analytics.engine import AnalyticsEngine
from pr_agent.storage.database import Database

db = Database()
engine = AnalyticsEngine(db)

# Get trends for last 30 days
trends = engine.get_code_quality_trends(days=30)

print(f"Total Reviews: {trends['summary']['total_reviews']}")
print(f"Success Rate: {trends['summary']['success_rate']:.2f}%")
print(f"Avg Duration: {trends['summary']['avg_duration_minutes']:.2f} min")

# Daily breakdown
for day in trends['daily_data']:
    print(f"{day['date']}: {day['total_reviews']} reviews, {day['success_rate']:.1f}% success")
```

**Metrics Tracked**:
- Total reviews per day
- Completed vs failed reviews
- Success rate percentage
- Average review duration

### 2. Team Efficiency Metrics

Analyze team productivity and patterns:

```python
# Get efficiency metrics
metrics = engine.get_team_efficiency_metrics(days=30)

print(f"Total Reviews: {metrics['summary']['total_reviews']}")
print(f"Unique Authors: {metrics['summary']['unique_authors']}")
print(f"Reviews per Day: {metrics['summary']['reviews_per_day']:.2f}")
print(f"Avg Review Time: {metrics['summary']['avg_review_time_hours']:.2f} hours")

# Top contributors
for author in metrics['top_authors']:
    print(f"{author['author']}: {author['total_reviews']} reviews, {author['success_rate']:.1f}% success")

# Peak hours
for hour in metrics['hourly_distribution']:
    print(f"{hour['hour']:02d}:00 - {hour['count']} reviews")
```

**Metrics Tracked**:
- Total reviews and unique authors
- Reviews per day/author
- Average review time
- Top contributors
- Hourly distribution

### 3. Review Quality Score

Automated quality assessment with weighted scoring:

```python
# Get quality score
score = engine.get_review_quality_score(days=30)

print(f"Overall Score: {score['overall_score']:.2f}/100")
print(f"Grade: {score['grade']}")

# Component breakdown
for name, component in score['components'].items():
    print(f"{name.title()}: {component['score']:.2f} (weight: {component['weight']}%)")
```

**Scoring Components**:

1. **Success Rate (40%)**
   - Percentage of completed reviews
   - Target: 100%

2. **Review Speed (30%)**
   - Average time to complete review
   - Target: < 2 hours
   - Scoring:
     - ≤ 1 hour: 100 points
     - ≤ 2 hours: 80 points
     - ≤ 4 hours: 60 points
     - ≤ 8 hours: 40 points
     - > 8 hours: 20 points

3. **Coverage (30%)**
   - Review frequency vs target
   - Target: 5 reviews/day (configurable)

**Grading Scale**:
- A: 90-100
- B: 80-89
- C: 70-79
- D: 60-69
- F: < 60

### 4. Repository Comparison

Compare metrics across repositories:

```python
# Compare all repositories
comparison = engine.get_repository_comparison(days=30)

for repo in comparison:
    print(f"{repo['repository']}:")
    print(f"  Reviews: {repo['total_reviews']}")
    print(f"  Success Rate: {repo['success_rate']:.2f}%")
    print(f"  Avg Time: {repo['avg_review_time_hours']:.2f} hours")
```

### 5. Custom Reports

Generate comprehensive reports in multiple formats:

```python
# Generate JSON report
report = engine.generate_custom_report("detailed", {"days": 30})

# Generate for specific repository
report = engine.generate_custom_report("summary", {
    "days": 30,
    "repository_id": 1
})
```

**Report Types**:

- **summary**: Quality trends, efficiency, and score
- **detailed**: All metrics plus repository comparison
- **comparison**: Repository comparison only

## API Endpoints

### Get Analytics Overview

```bash
GET /api/analytics/overview?days=30
```

Returns high-level analytics overview.

**Response**:
```json
{
  "generated_at": "2026-04-22T10:00:00",
  "period_days": 30,
  "quality_score": {
    "overall_score": 85.5,
    "grade": "B"
  },
  "efficiency": {
    "summary": {
      "total_reviews": 150,
      "unique_authors": 12,
      "reviews_per_day": 5.0
    }
  }
}
```

### Get Trend Data

```bash
GET /api/analytics/trends?metric=review_count&days=30
```

**Supported Metrics**:
- `review_count`: Number of reviews
- `success_rate`: Success percentage
- `duration`: Average review time

**Response**:
```json
{
  "metric": "review_count",
  "period_days": 30,
  "data": [
    {"date": "2026-04-01", "value": 5},
    {"date": "2026-04-02", "value": 7}
  ]
}
```

### Get Repository Analytics

```bash
GET /api/analytics/repository/{repo_id}?days=30
```

Returns complete analytics for a specific repository.

### Generate Report

```bash
GET /api/analytics/report?start_date=2026-04-01&end_date=2026-04-30&format=json
```

**Formats**:
- `json`: Structured JSON data
- `csv`: CSV format for spreadsheets
- `text`: Human-readable text

**Response** (JSON):
```json
{
  "type": "comprehensive",
  "generated_at": "2026-04-22T10:00:00",
  "period": {
    "start": "2026-04-01T00:00:00",
    "end": "2026-04-30T23:59:59",
    "days": 30
  },
  "quality_trends": {...},
  "efficiency_metrics": {...},
  "quality_score": {...},
  "repository_comparison": [...]
}
```

## Export Reports

### Export to JSON

```python
from pr_agent.analytics.engine import export_report_to_json

report = engine.generate_custom_report("detailed", {"days": 30})
export_report_to_json(report, "analytics_report.json")
```

### Export to CSV

```python
from pr_agent.analytics.engine import export_report_to_csv

report = engine.generate_custom_report("comparison", {"days": 30})
export_report_to_csv(report, "repository_comparison.csv")
```

### Generate Text Report

```python
report = engine.generate_report(format="text")
with open("report.txt", "w") as f:
    f.write(report)
```

## Dashboard Integration

### Frontend Example

```typescript
// Fetch analytics overview
const response = await fetch('/api/analytics/overview?days=30');
const data = await response.json();

// Display quality score
console.log(`Quality Score: ${data.quality_score.overall_score}`);
console.log(`Grade: ${data.quality_score.grade}`);

// Fetch trend data for chart
const trendsResponse = await fetch('/api/analytics/trends?metric=review_count&days=30');
const trends = await trendsResponse.json();

// Use with charting library (e.g., Chart.js)
const chartData = {
  labels: trends.data.map(d => d.date),
  datasets: [{
    label: 'Reviews',
    data: trends.data.map(d => d.value)
  }]
};
```

## Scheduled Reports

### Daily Report Generation

```python
import schedule
import time

def generate_daily_report():
    engine = AnalyticsEngine(Database())
    report = engine.generate_report(format="text")
    
    # Send via email or save to file
    with open(f"daily_report_{datetime.now().date()}.txt", "w") as f:
        f.write(report)

# Schedule daily at 9 AM
schedule.every().day.at("09:00").do(generate_daily_report)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### Weekly Summary

```python
def generate_weekly_summary():
    engine = AnalyticsEngine(Database())
    
    # Last 7 days
    report = engine.generate_custom_report("detailed", {"days": 7})
    
    # Export to multiple formats
    export_report_to_json(report, "weekly_summary.json")
    export_report_to_csv(report, "weekly_summary.csv")

schedule.every().monday.at("09:00").do(generate_weekly_summary)
```

## Best Practices

### 1. Regular Monitoring

Monitor key metrics daily:

```python
def check_quality_metrics():
    engine = AnalyticsEngine(Database())
    score = engine.get_review_quality_score(days=1)
    
    if score['overall_score'] < 70:
        # Alert team
        send_alert(f"Quality score dropped to {score['overall_score']}")
```

### 2. Trend Analysis

Look for patterns over time:

```python
# Compare week-over-week
current_week = engine.get_code_quality_trends(days=7)
previous_week = engine.get_code_quality_trends(days=14)

current_rate = current_week['summary']['success_rate']
# Calculate previous week rate from daily data
```

### 3. Team Performance

Track individual and team metrics:

```python
metrics = engine.get_team_efficiency_metrics(days=30)

# Identify top performers
top_authors = metrics['top_authors'][:3]

# Identify peak hours for scheduling
peak_hours = sorted(
    metrics['hourly_distribution'],
    key=lambda x: x['count'],
    reverse=True
)[:3]
```

### 4. Repository Health

Monitor repository-specific metrics:

```python
repos = db.get_all_repositories()

for repo in repos:
    analytics = engine.get_repository_analytics(repo['id'], days=30)
    score = analytics['quality_score']['overall_score']
    
    if score < 70:
        print(f"Warning: {repo['project_key']}/{repo['repo_slug']} score: {score}")
```

## Troubleshooting

### No Data Available

```python
trends = engine.get_code_quality_trends(days=30)
if trends['summary']['total_reviews'] == 0:
    print("No reviews found in the specified period")
```

### Slow Queries

For large datasets, use shorter time periods:

```python
# Instead of 90 days
trends = engine.get_code_quality_trends(days=30)

# Or use caching
from pr_agent.storage.db_optimizer import CachedDatabase
cached_db = CachedDatabase(db)
engine = AnalyticsEngine(cached_db)
```

### Memory Usage

For large reports, stream to file:

```python
import json

report = engine.generate_custom_report("detailed", {"days": 90})

with open("large_report.json", "w") as f:
    json.dump(report, f, indent=2)
```

## Related Documentation

- [API Documentation](API.md)
- [Performance Guide](PERFORMANCE.md)
- [Monitoring Guide](MONITORING.md)
- [Database Schema](DATABASE_MIGRATIONS.md)
