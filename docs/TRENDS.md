# Code Quality Trends Analysis

Track and analyze code quality metrics over time to identify trends, detect degradations, and predict future quality issues.

## Features

- **Metric Tracking**: Record multiple quality metrics over time
- **Trend Analysis**: Analyze trends with statistical methods
- **Degradation Detection**: Automatically detect quality degradations
- **Prediction**: Predict future metric values with confidence scores
- **Comprehensive Reports**: Generate detailed quality reports
- **Visualization**: Text-based visualizations of trends

## Supported Metrics

| Metric | Description | Lower is Better |
|--------|-------------|-----------------|
| `complexity` | Code complexity (cyclomatic complexity) | ✓ |
| `maintainability` | Maintainability index (0-100) | ✗ |
| `coverage` | Test coverage percentage | ✗ |
| `duplication` | Code duplication percentage | ✓ |
| `issues` | Number of code issues | ✓ |
| `loc` | Lines of code | ✓ |
| `technical_debt` | Technical debt in hours | ✓ |

## Usage

### Python API

```python
from pr_agent.trends import TrendsAnalyzer, MetricType
from pathlib import Path

# Create analyzer
analyzer = TrendsAnalyzer(storage_path=Path("./trends"))

# Record metrics
analyzer.record_metrics({
    MetricType.COMPLEXITY: 10.5,
    MetricType.COVERAGE: 85.0,
    MetricType.MAINTAINABILITY: 75.0
})

# Analyze trend for a specific metric
trend = analyzer.analyze_trend(MetricType.COMPLEXITY, days=30)
print(f"Direction: {trend.direction}")
print(f"Change: {trend.change_percentage:.1f}%")
print(f"Prediction: {trend.prediction}")

# Detect degradations
degradations = analyzer.detect_degradations(
    threshold_percentage=10.0,
    days=7
)
for deg in degradations:
    print(f"{deg.metric_type}: {deg.severity} - {deg.description}")

# Generate comprehensive report
report = analyzer.generate_report(days=30, repository="my-repo")
print(f"Overall Health: {report.summary['overall_health']}/100")
```

### REST API

#### Record Metrics

```bash
curl -X POST http://localhost:8000/api/trends/record \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "metrics": {
      "complexity": 10.5,
      "coverage": 85.0,
      "maintainability": 75.0
    },
    "commit_hash": "abc123"
  }'
```

#### Analyze Trend

```bash
curl -X POST http://localhost:8000/api/trends/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "metric_type": "complexity",
    "days": 30
  }'
```

Response:
```json
{
  "metric_type": "complexity",
  "direction": "improving",
  "change_percentage": -15.5,
  "current_value": 8.5,
  "previous_value": 10.0,
  "average_value": 9.2,
  "min_value": 8.0,
  "max_value": 11.0,
  "data_points": 25,
  "prediction": 7.8,
  "confidence": 0.85
}
```

#### Detect Degradations

```bash
curl -X POST "http://localhost:8000/api/trends/degradations?days=7&threshold=10.0" \
  -H "Authorization: Bearer $TOKEN"
```

Response:
```json
{
  "count": 2,
  "degradations": [
    {
      "metric_type": "complexity",
      "file_path": "src/main.py",
      "severity": "high",
      "change_percentage": 25.0,
      "old_value": 10.0,
      "new_value": 12.5,
      "timestamp": "2024-01-15T10:30:00Z",
      "description": "Complexity increased by 25.0%"
    }
  ]
}
```

#### Generate Report

```bash
curl -X POST http://localhost:8000/api/trends/report \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "days": 30,
    "repository": "my-repo"
  }'
```

Text format:
```bash
curl -X POST "http://localhost:8000/api/trends/report?format=text" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "days": 30,
    "repository": "my-repo"
  }'
```

## Trend Analysis

### Trend Directions

- **IMPROVING**: Metric is moving in a positive direction
  - For "lower is better" metrics: decreasing
  - For "higher is better" metrics: increasing
- **STABLE**: Metric shows minimal change (< 5%)
- **DEGRADING**: Metric is moving in a negative direction
  - For "lower is better" metrics: increasing
  - For "higher is better" metrics: decreasing

### Statistical Methods

The analyzer uses linear regression to:
- Calculate trend direction and slope
- Compute change percentage
- Generate predictions with confidence scores
- Identify significant deviations

### Degradation Detection

Degradations are detected when:
1. Metric changes by more than threshold percentage
2. Change is in the negative direction
3. Change persists over multiple data points

Severity levels:
- **Low**: 10-25% change
- **Medium**: 25-50% change
- **High**: 50-100% change
- **Critical**: >100% change

## Report Generation

Comprehensive reports include:

1. **Summary Statistics**
   - Overall health score (0-100)
   - Number of improving/stable/degrading metrics
   - Total degradations by severity

2. **Trend Analysis**
   - Individual trends for each metric
   - Direction and change percentage
   - Predictions with confidence

3. **Degradation Details**
   - All detected degradations
   - Severity and impact
   - Affected files

4. **Recommendations**
   - Suggested actions based on trends
   - Priority areas for improvement

## Storage

Metrics are stored in JSON format:

```
trends/
├── snapshots.json      # All metric snapshots
└── metadata.json       # Analysis metadata
```

Each snapshot includes:
- Timestamp
- Metric type and value
- Optional file path
- Optional commit hash
- Optional metadata

## Integration

### CI/CD Integration

```yaml
# .github/workflows/quality-trends.yml
name: Quality Trends

on:
  push:
    branches: [main]

jobs:
  track-quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Run quality analysis
        run: |
          # Calculate metrics
          COMPLEXITY=$(radon cc -a src/)
          COVERAGE=$(pytest --cov=src --cov-report=json | jq '.totals.percent_covered')
          
      - name: Record metrics
        run: |
          curl -X POST $API_URL/api/trends/record \
            -H "Authorization: Bearer $TOKEN" \
            -d "{
              \"metrics\": {
                \"complexity\": $COMPLEXITY,
                \"coverage\": $COVERAGE
              },
              \"commit_hash\": \"$GITHUB_SHA\"
            }"
```

### Pre-commit Hook

```python
# .git/hooks/pre-commit
from pr_agent.trends import TrendsAnalyzer, MetricType
from radon.complexity import cc_visit
import coverage

# Calculate metrics
with open('src/main.py') as f:
    complexity = sum(c.complexity for c in cc_visit(f.read()))

cov = coverage.Coverage()
cov.start()
# Run tests...
cov.stop()
coverage_pct = cov.report()

# Record metrics
analyzer = TrendsAnalyzer()
analyzer.record_metrics({
    MetricType.COMPLEXITY: complexity,
    MetricType.COVERAGE: coverage_pct
})

# Check for degradations
degradations = analyzer.detect_degradations(threshold_percentage=10.0, days=1)
if degradations:
    print("⚠️  Quality degradations detected:")
    for deg in degradations:
        print(f"  - {deg.metric_type}: {deg.description}")
    exit(1)
```

## Best Practices

1. **Regular Recording**: Record metrics on every commit or daily
2. **Consistent Metrics**: Use the same calculation method over time
3. **Set Thresholds**: Define acceptable degradation thresholds
4. **Monitor Trends**: Review trends weekly or monthly
5. **Act on Degradations**: Address degradations promptly
6. **Track Context**: Include commit hashes and file paths
7. **Generate Reports**: Create regular quality reports

## Configuration

```toml
[trends]
# Storage path for trends data
storage_path = "./trends"

# Default analysis period in days
default_days = 30

# Degradation detection threshold (percentage)
degradation_threshold = 10.0

# Minimum data points for trend analysis
min_data_points = 3

# Prediction confidence threshold
prediction_confidence = 0.7
```

## Troubleshooting

### Insufficient Data

**Problem**: "Insufficient data for trend analysis"

**Solution**: Record more metrics over time. Minimum 3 data points required.

### Unstable Predictions

**Problem**: Low confidence scores in predictions

**Solution**: 
- Increase data points
- Ensure consistent metric calculation
- Check for outliers in data

### Missing Trends

**Problem**: Some metrics don't show trends

**Solution**:
- Verify metrics are being recorded
- Check storage path permissions
- Ensure metric types are correct

## Examples

### Track Complexity Over Sprint

```python
from pr_agent.trends import TrendsAnalyzer, MetricType
from datetime import datetime, timedelta

analyzer = TrendsAnalyzer()

# Record daily complexity
for day in range(14):
    date = datetime.now() - timedelta(days=13-day)
    complexity = calculate_complexity()  # Your calculation
    
    analyzer.record_metrics(
        {MetricType.COMPLEXITY: complexity},
        commit_hash=get_commit_hash(date)
    )

# Analyze sprint trend
trend = analyzer.analyze_trend(MetricType.COMPLEXITY, days=14)
print(f"Sprint complexity trend: {trend.direction}")
print(f"Change: {trend.change_percentage:.1f}%")
```

### Quality Gate Based on Trends

```python
def quality_gate_check():
    analyzer = TrendsAnalyzer()
    
    # Check recent degradations
    degradations = analyzer.detect_degradations(days=7, threshold_percentage=5.0)
    
    # Fail if critical degradations
    critical = [d for d in degradations if d.severity == "critical"]
    if critical:
        print("❌ Critical quality degradations detected!")
        for deg in critical:
            print(f"  {deg.metric_type}: {deg.description}")
        return False
    
    # Check overall health
    report = analyzer.generate_report(days=30)
    if report.summary["overall_health"] < 70:
        print("❌ Overall quality health below threshold!")
        return False
    
    print("✅ Quality gate passed")
    return True
```

## See Also

- [Code Metrics](CODE_METRICS.md) - Metric calculation
- [Quality Gate](QUALITY_GATE.md) - Quality enforcement
- [Monitoring](MONITORING.md) - System monitoring
