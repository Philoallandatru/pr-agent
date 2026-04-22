# Code Quality Report Generation

Comprehensive quality report generation system supporting multiple output formats (JSON, Markdown, HTML, PDF) with customizable sections and rich visualizations.

## Features

- **Multiple Output Formats**: JSON, Markdown, HTML, PDF
- **Customizable Sections**: Choose which sections to include
- **Rich Visualizations**: Charts, tables, and formatted output
- **Quality Metrics**: LOC, coverage, complexity, maintainability
- **Trend Analysis**: Historical metric trends
- **Issue Tracking**: Severity-based issue grouping
- **Recommendations**: Actionable improvement suggestions
- **Metadata Support**: Custom metadata in reports

## Report Sections

### Available Sections

1. **Summary**: Executive summary with key metrics
2. **Metrics**: Detailed quality metrics table
3. **Trends**: Historical trend analysis
4. **Issues**: Issues grouped by severity
5. **Recommendations**: Improvement recommendations
6. **Details**: Additional details (future use)

## Usage

### Python API

```python
from pathlib import Path
from pr_agent.reports import (
    ReportGenerator,
    ReportFormat,
    ReportSection,
    QualityMetrics,
    TrendData,
    Issue,
    Recommendation,
)

# Initialize generator
generator = ReportGenerator(output_dir=Path("./reports"))

# Create quality metrics
metrics = QualityMetrics(
    lines_of_code=10000,
    test_coverage=85.5,
    complexity_score=12.3,
    maintainability_index=78.5,
    code_smells=15,
    bugs=3,
    vulnerabilities=1,
    technical_debt_hours=24.5,
    duplication_percentage=5.2
)

# Create trend data
trends = [
    TrendData(
        timestamp="2024-01-01T00:00:00Z",
        metric_name="test_coverage",
        value=80.0
    ),
    TrendData(
        timestamp="2024-01-02T00:00:00Z",
        metric_name="test_coverage",
        value=82.5
    ),
]

# Create issues
issues = [
    Issue(
        severity="HIGH",
        category="Security",
        file_path="src/auth.py",
        line_number=42,
        message="Potential SQL injection vulnerability",
        rule_id="SEC001"
    ),
]

# Create recommendations
recommendations = [
    Recommendation(
        priority="HIGH",
        category="Testing",
        title="Increase test coverage",
        description="Add unit tests for critical authentication modules",
        estimated_effort="2-3 days",
        impact="High"
    ),
]

# Generate HTML report
output_path = generator.generate_report(
    repository="myorg/myrepo",
    metrics=metrics,
    trends=trends,
    issues=issues,
    recommendations=recommendations,
    format=ReportFormat.HTML
)

print(f"Report generated: {output_path}")
```

### Generate Report with Selected Sections

```python
# Only include summary and metrics
output_path = generator.generate_report(
    repository="myorg/myrepo",
    metrics=metrics,
    trends=trends,
    issues=issues,
    recommendations=recommendations,
    format=ReportFormat.MARKDOWN,
    sections=[ReportSection.SUMMARY, ReportSection.METRICS]
)
```

### Add Custom Metadata

```python
output_path = generator.generate_report(
    repository="myorg/myrepo",
    metrics=metrics,
    trends=trends,
    issues=issues,
    recommendations=recommendations,
    format=ReportFormat.JSON,
    metadata={
        "branch": "main",
        "commit": "abc123",
        "author": "john.doe",
        "ci_build": "12345"
    }
)
```

## REST API

### Generate Report

**POST** `/api/reports/generate`

Generate a quality report.

**Request Body:**
```json
{
  "repository": "myorg/myrepo",
  "metrics": {
    "lines_of_code": 10000,
    "test_coverage": 85.5,
    "complexity_score": 12.3,
    "maintainability_index": 78.5,
    "code_smells": 15,
    "bugs": 3,
    "vulnerabilities": 1,
    "technical_debt_hours": 24.5,
    "duplication_percentage": 5.2
  },
  "trends": [
    {
      "timestamp": "2024-01-01T00:00:00Z",
      "metric_name": "test_coverage",
      "value": 80.0
    }
  ],
  "issues": [
    {
      "severity": "HIGH",
      "category": "Security",
      "file_path": "src/auth.py",
      "line_number": 42,
      "message": "Potential SQL injection vulnerability",
      "rule_id": "SEC001"
    }
  ],
  "recommendations": [
    {
      "priority": "HIGH",
      "category": "Testing",
      "title": "Increase test coverage",
      "description": "Add unit tests for critical modules",
      "estimated_effort": "2-3 days",
      "impact": "High"
    }
  ],
  "format": "html",
  "sections": ["summary", "metrics", "issues"],
  "metadata": {
    "branch": "main",
    "commit": "abc123"
  }
}
```

**Response:**
```json
{
  "file_path": "/home/user/.pr_agent/reports/report_20240101_120000.html",
  "filename": "report_20240101_120000.html",
  "format": "html",
  "download_url": "/api/reports/download/report_20240101_120000.html"
}
```

### Download Report

**GET** `/api/reports/download/{filename}`

Download a generated report.

**Response:** File download

### List Reports

**GET** `/api/reports/list`

List all generated reports.

**Response:**
```json
{
  "reports": [
    {
      "filename": "report_20240101_120000.html",
      "format": "html",
      "size": 45678,
      "created_at": 1704110400.0,
      "download_url": "/api/reports/download/report_20240101_120000.html"
    }
  ]
}
```

### Delete Report

**DELETE** `/api/reports/{filename}`

Delete a generated report.

**Response:**
```json
{
  "message": "Report deleted successfully"
}
```

## Report Formats

### JSON Format

Machine-readable format containing all report data in structured JSON.

**Use Cases:**
- API integration
- Data processing
- Automated analysis

### Markdown Format

Human-readable text format with Markdown formatting.

**Use Cases:**
- Documentation
- GitHub/GitLab integration
- Version control

**Features:**
- Tables for metrics
- Severity-based issue grouping
- Trend indicators (↑↓→)
- Code formatting

### HTML Format

Rich web format with CSS styling and responsive design.

**Use Cases:**
- Web dashboards
- Email reports
- Interactive viewing

**Features:**
- Gradient headers
- Metric cards
- Color-coded severity
- Responsive layout
- Professional styling

### PDF Format

Print-ready format (requires `weasyprint` library).

**Use Cases:**
- Formal reports
- Archival
- Presentations

**Installation:**
```bash
pip install weasyprint
```

## Quality Metrics

### Lines of Code (LOC)
Total number of code lines in the repository.

### Test Coverage
Percentage of code covered by tests (0-100%).

### Complexity Score
Average cyclomatic complexity across all functions.

### Maintainability Index
Code maintainability score (0-100, higher is better).

### Code Smells
Number of code quality issues that don't affect functionality.

### Bugs
Number of confirmed or potential bugs.

### Vulnerabilities
Number of security vulnerabilities.

### Technical Debt
Estimated hours to fix all quality issues.

### Code Duplication
Percentage of duplicated code (0-100%).

## Issue Severity Levels

- **CRITICAL**: Severe issues requiring immediate attention
- **HIGH**: Important issues that should be fixed soon
- **MEDIUM**: Moderate issues to address in normal workflow
- **LOW**: Minor issues or suggestions

## Recommendation Priorities

- **CRITICAL**: Must be addressed immediately
- **HIGH**: Should be addressed in current sprint
- **MEDIUM**: Should be addressed in next sprint
- **LOW**: Nice to have improvements

## Integration Examples

### With Scheduler

```python
from pr_agent.scheduler import get_scheduler
from pr_agent.reports import ReportGenerator, QualityMetrics

# Generate report after review completes
def on_review_complete(job):
    generator = ReportGenerator(output_dir=Path("./reports"))
    
    # Collect metrics from review results
    metrics = QualityMetrics(
        lines_of_code=job.results.get("loc", 0),
        test_coverage=job.results.get("coverage", 0.0),
        # ... other metrics
    )
    
    # Generate report
    generator.generate_report(
        repository=job.repository,
        metrics=metrics,
        trends=[],
        issues=job.results.get("issues", []),
        recommendations=job.results.get("recommendations", []),
        format=ReportFormat.HTML
    )

scheduler = get_scheduler()
scheduler.set_review_executor(on_review_complete)
```

### With CI/CD

```yaml
# .github/workflows/quality-report.yml
name: Quality Report

on:
  push:
    branches: [main]

jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Generate Quality Report
        run: |
          curl -X POST http://pr-agent-server/api/reports/generate \
            -H "Content-Type: application/json" \
            -d @quality-data.json
      
      - name: Upload Report
        uses: actions/upload-artifact@v2
        with:
          name: quality-report
          path: reports/
```

## Best Practices

1. **Regular Generation**: Generate reports on every commit or daily
2. **Trend Tracking**: Include historical data for trend analysis
3. **Actionable Recommendations**: Provide specific, actionable suggestions
4. **Severity Classification**: Properly classify issues by severity
5. **Metadata**: Include build/commit info for traceability
6. **Format Selection**: Choose format based on audience
   - JSON for automation
   - HTML for stakeholders
   - Markdown for developers
   - PDF for formal reports

## Troubleshooting

### PDF Generation Fails

**Problem:** `ImportError: weasyprint is required`

**Solution:**
```bash
pip install weasyprint
```

### Large Reports

**Problem:** Reports are too large or slow to generate

**Solution:**
- Limit issues to top N per severity
- Use selected sections instead of all
- Generate separate reports for different aspects

### Missing Sections

**Problem:** Expected sections not appearing in report

**Solution:**
- Check that data is provided (empty lists won't show)
- Verify section names are correct
- Ensure sections parameter includes desired sections

## Configuration

Reports are stored in `~/.pr_agent/reports/` by default.

To customize:

```python
from pathlib import Path

generator = ReportGenerator(
    output_dir=Path("/custom/path/reports")
)
```

## Performance

- **JSON**: ~10ms for typical report
- **Markdown**: ~20ms for typical report
- **HTML**: ~30ms for typical report
- **PDF**: ~500ms for typical report (requires rendering)

Report generation is fast and suitable for real-time use in most cases.
