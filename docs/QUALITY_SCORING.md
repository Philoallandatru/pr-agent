# Code Review Quality Scoring System

The Quality Scoring System evaluates and scores code reviews based on multiple quality metrics, providing insights into review effectiveness and reviewer performance.

## Features

- **Multi-Metric Scoring**: Evaluates reviews across 5 key quality dimensions
- **Reviewer Ratings**: Tracks and ranks reviewer performance over time
- **Quality Trends**: Analyzes quality trends and patterns
- **Improvement Suggestions**: Provides personalized feedback for reviewers
- **Automated Scoring**: Calculates scores automatically from review data

## Quality Metrics

The system evaluates reviews based on five key metrics:

### 1. Coverage (25% weight)
Measures how much of the changed code was actually reviewed.

- **100%**: All files reviewed
- **50%**: Half of files reviewed
- **0%**: No files reviewed

### 2. Depth (30% weight)
Evaluates the thoroughness and detail of the review.

- Based on number of comments (0-50 points)
- Based on comment detail/length (0-50 points)
- Good comments are typically 50-200 characters

### 3. Timeliness (15% weight)
Measures how quickly the review was completed.

- **100%**: Within 24 hours
- **80%**: Within 48 hours
- **60%**: Within 72 hours
- **40%**: Within 1 week
- **20%**: Over 1 week

### 4. Effectiveness (20% weight)
Evaluates how useful the review was in improving code quality.

- Based on issues found and resolved
- Higher score for finding actionable issues
- Bonus points for issue resolution rate

### 5. Engagement (10% weight)
Measures the level of interaction and discussion.

- Based on discussion threads
- Based on comment interactions
- Encourages collaborative reviews

## Score Categories

Reviews are categorized based on overall score:

- **Excellent**: 90-100 points
- **Good**: 75-89 points
- **Fair**: 60-74 points
- **Poor**: 0-59 points

## Usage

### Scoring a Review

```python
from pr_agent.quality_scoring import QualityScorer

scorer = QualityScorer()

# Prepare review data
review_data = {
    'files_changed': 10,
    'files_reviewed': 8,
    'comments_count': 15,
    'comment_depth': 120,  # Average chars per comment
    'time_to_review': 20,  # Hours
    'issues_found': 5,
    'issues_resolved': 4,
    'discussion_threads': 3
}

# Score the review
score = scorer.score_review(
    review_id="rev-123",
    reviewer_id="alice",
    review_data=review_data
)

print(f"Overall Score: {score.overall_score}")
print(f"Category: {score.category.value}")
print(f"Feedback: {score.feedback}")
```

### Getting Reviewer Rating

```python
# Get overall rating for a reviewer
rating = scorer.get_reviewer_rating("alice")

print(f"Average Score: {rating.average_score}")
print(f"Total Reviews: {rating.total_reviews}")
print(f"Category: {rating.category.value}")
print(f"Trend: {rating.trend}")

# Metric averages
for metric, avg in rating.metric_averages.items():
    print(f"{metric}: {avg}")
```

### Ranking Reviewers

```python
# Get rankings for all reviewers
rankings = scorer.rank_reviewers()

for rating in rankings:
    print(f"#{rating.rank} {rating.reviewer_id}")
    print(f"  Score: {rating.average_score}")
    print(f"  Percentile: {rating.percentile}%")
    print(f"  Reviews: {rating.total_reviews}")
```

### Analyzing Quality Trends

```python
from pr_agent.quality_scoring import QualityMetric

# Analyze coverage trends
trend = scorer.analyze_quality_trend(
    metric=QualityMetric.COVERAGE,
    period="weekly",
    days=30
)

print(f"Average: {trend.average}")
print(f"Direction: {trend.trend_direction}")
print(f"Change: {trend.change_percentage}%")
```

### Getting Improvement Suggestions

```python
# Get personalized suggestions
suggestions = scorer.get_improvement_suggestions("alice")

for suggestion in suggestions:
    print(f"• {suggestion}")
```

## REST API

### Score a Review

```http
POST /api/quality/score
Content-Type: application/json

{
  "review_id": "rev-123",
  "reviewer_id": "alice",
  "review_data": {
    "files_changed": 10,
    "files_reviewed": 8,
    "comments_count": 15,
    "comment_depth": 120,
    "time_to_review": 20,
    "issues_found": 5,
    "issues_resolved": 4,
    "discussion_threads": 3
  }
}
```

Response:
```json
{
  "review_id": "rev-123",
  "reviewer_id": "alice",
  "overall_score": 82.5,
  "metric_scores": {
    "coverage": 80.0,
    "depth": 85.0,
    "timeliness": 100.0,
    "effectiveness": 88.0,
    "engagement": 70.0
  },
  "category": "good",
  "timestamp": "2024-01-15T10:30:00Z",
  "feedback": [
    "Good review quality with room for improvement.",
    "• Engage more in discussions with the author"
  ]
}
```

### Get Reviewer Rating

```http
GET /api/quality/reviewer/{reviewer_id}
```

Response:
```json
{
  "reviewer_id": "alice",
  "average_score": 85.2,
  "total_reviews": 25,
  "metric_averages": {
    "coverage": 82.0,
    "depth": 88.0,
    "timeliness": 90.0,
    "effectiveness": 85.0,
    "engagement": 75.0
  },
  "category": "good",
  "rank": 3,
  "percentile": 85.0,
  "trend": "improving"
}
```

### Rank Reviewers

```http
GET /api/quality/rankings
```

Response:
```json
{
  "rankings": [
    {
      "reviewer_id": "bob",
      "average_score": 92.5,
      "rank": 1,
      "percentile": 100.0,
      "total_reviews": 30
    },
    {
      "reviewer_id": "charlie",
      "average_score": 88.0,
      "rank": 2,
      "percentile": 90.0,
      "total_reviews": 20
    }
  ]
}
```

### Get Quality Trends

```http
GET /api/quality/trends?metric=coverage&days=30
```

Response:
```json
{
  "metric": "coverage",
  "period": "weekly",
  "data_points": [
    {
      "timestamp": "2024-01-01T00:00:00Z",
      "score": 75.0,
      "review_id": "rev-1"
    },
    {
      "timestamp": "2024-01-08T00:00:00Z",
      "score": 80.0,
      "review_id": "rev-2"
    }
  ],
  "average": 77.5,
  "trend_direction": "up",
  "change_percentage": 6.7
}
```

### Get Improvement Suggestions

```http
GET /api/quality/suggestions/{reviewer_id}
```

Response:
```json
{
  "suggestions": [
    "Your average score is 72.5. Focus on the specific areas below to improve.",
    "Coverage: Review all changed files, not just the main ones.",
    "Engagement: Participate more in discussions."
  ]
}
```

## Integration Examples

### With Dashboard System

```python
from pr_agent.quality_scoring import QualityScorer
from pr_agent.dashboard import get_dashboard_system

scorer = QualityScorer()
dashboard = get_dashboard_system()

# Score review
score = scorer.score_review("rev-123", "alice", review_data)

# Record in dashboard
dashboard.record_review({
    "review_id": "rev-123",
    "reviewer_id": "alice",
    "quality_score": score.overall_score,
    "quality_category": score.category.value
})
```

### With Notification System

```python
from pr_agent.quality_scoring import QualityScorer, ScoreCategory
from pr_agent.notifications import get_notification_system

scorer = QualityScorer()
notifications = get_notification_system()

# Score review
score = scorer.score_review("rev-123", "alice", review_data)

# Notify if score is poor
if score.category == ScoreCategory.POOR:
    notifications.send_notification(
        user_id="alice",
        event="LOW_QUALITY_REVIEW",
        title="Review Quality Alert",
        message=f"Your recent review scored {score.overall_score}. "
                f"Please review the feedback: {score.feedback[0]}"
    )
```

### With SLA System

```python
from pr_agent.quality_scoring import QualityScorer
from pr_agent.sla import get_sla_manager

scorer = QualityScorer()
sla_manager = get_sla_manager()

# Score review
score = scorer.score_review("rev-123", "alice", review_data)

# Check if quality meets SLA
if score.overall_score < 60:
    # Trigger escalation
    sla_manager.record_event("rev-123", "quality_violation")
```

## Customizing Metric Weights

```python
scorer = QualityScorer()

# Adjust weights (must sum to 1.0)
scorer.metric_weights = {
    'coverage': 0.30,  # Increase coverage importance
    'depth': 0.25,
    'timeliness': 0.15,
    'effectiveness': 0.20,
    'engagement': 0.10
}
```

## Best Practices

1. **Consistent Data Collection**: Ensure review data is collected consistently
2. **Regular Scoring**: Score reviews promptly after completion
3. **Act on Feedback**: Use suggestions to improve review quality
4. **Monitor Trends**: Track quality trends over time
5. **Set Standards**: Define minimum acceptable scores for your team
6. **Recognize Excellence**: Acknowledge high-performing reviewers
7. **Provide Training**: Use low scores to identify training needs

## Interpreting Scores

### Excellent (90-100)
- Comprehensive coverage of all changes
- Detailed, thoughtful comments
- Quick turnaround time
- Identifies meaningful issues
- Active engagement with author

### Good (75-89)
- Most files reviewed
- Adequate comment detail
- Reasonable response time
- Some useful feedback
- Moderate engagement

### Fair (60-74)
- Partial coverage
- Basic comments
- Slower response
- Limited effectiveness
- Minimal engagement

### Poor (0-59)
- Incomplete coverage
- Superficial comments
- Very slow response
- Little value added
- No engagement

## Troubleshooting

**Scores seem too low:**
- Check if metric weights align with your team's priorities
- Verify review data is being collected correctly
- Consider if targets are realistic for your team

**Scores don't reflect quality:**
- Review the metric calculations
- Adjust weights to match your quality criteria
- Collect more detailed review data

**Trends not showing:**
- Ensure sufficient review history (at least 10 reviews)
- Check date ranges
- Verify reviews are being scored consistently

## Configuration

Quality scoring settings in `configuration.toml`:

```toml
[quality_scoring]
# Metric weights (must sum to 1.0)
coverage_weight = 0.25
depth_weight = 0.30
timeliness_weight = 0.15
effectiveness_weight = 0.20
engagement_weight = 0.10

# Score thresholds
excellent_threshold = 90
good_threshold = 75
fair_threshold = 60

# Timeliness targets (hours)
ideal_review_time = 24
acceptable_review_time = 48

# Comment depth targets (characters)
min_comment_length = 50
ideal_comment_length = 200
```
