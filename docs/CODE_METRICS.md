# Code Metrics and Statistics

Comprehensive code metrics analysis system for measuring code quality, complexity, maintainability, and technical debt.

## Features

- **Lines of Code (LOC)**: Total, source, comment, and blank lines
- **Cyclomatic Complexity**: Measure code complexity
- **Maintainability Index**: 0-100 score for code maintainability
- **Code Duplication**: Detect duplicate code blocks
- **Technical Debt**: Estimate hours needed to fix issues
- **Language Support**: Python, JavaScript, TypeScript, Java, Go, and more
- **Project-Wide Analysis**: Aggregate metrics across entire codebase
- **Trend Analysis**: Track metrics over time
- **Quality Reports**: Generate detailed reports in text or JSON

## Quick Start

### Python API

```python
from pr_agent.metrics import get_metrics_analyzer

analyzer = get_metrics_analyzer()

# Analyze single file
metrics = analyzer.analyze_file("path/to/file.py")
print(f"Complexity: {metrics.complexity}")
print(f"Maintainability: {metrics.maintainability}")

# Analyze entire project
project_metrics = analyzer.analyze_project("./src")
print(f"Total Files: {project_metrics.total_files}")
print(f"Total LOC: {project_metrics.total_loc}")
print(f"Technical Debt: {project_metrics.technical_debt_hours} hours")

# Generate report
report = analyzer.generate_report(project_metrics, format="text")
print(report)
```

## REST API

### Analyze File Metrics

```bash
POST /api/metrics/file
Content-Type: application/json
Authorization: Bearer <token>

{
  "file_path": "./src/main.py"
}
```

Response:
```json
{
  "path": "./src/main.py",
  "language": "python",
  "loc": 250,
  "sloc": 180,
  "comments": 40,
  "blank": 30,
  "complexity": 15,
  "maintainability": 72.5,
  "functions": 12,
  "classes": 3,
  "issues": []
}
```

### Analyze Project Metrics

```bash
POST /api/metrics/project
Content-Type: application/json
Authorization: Bearer <token>

{
  "project_dir": "./src",
  "patterns": ["*.py", "*.js"]
}
```

Response:
```json
{
  "summary": {
    "total_files": 42,
    "total_loc": 12500,
    "total_sloc": 9800,
    "total_comments": 1500,
    "total_blank": 1200,
    "total_functions": 320,
    "total_classes": 85,
    "avg_complexity": 12.3,
    "avg_maintainability": 68.5,
    "duplication_percentage": 3.2,
    "technical_debt_hours": 24.5
  },
  "language_breakdown": {
    "python": 35,
    "javascript": 7
  },
  "complexity_distribution": {
    "low": 28,
    "medium": 10,
    "high": 3,
    "critical": 1
  },
  "files": [...]
}
```

### Generate Metrics Report

```bash
POST /api/metrics/report
Content-Type: application/json
Authorization: Bearer <token>

{
  "project_dir": "./src",
  "format": "text",
  "patterns": ["*.py"]
}
```

Response:
```json
{
  "format": "text",
  "report": "============================================================\nCODE METRICS REPORT\n...",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Get Metric Types

```bash
GET /api/metrics/types
Authorization: Bearer <token>
```

Response:
```json
{
  "types": ["loc", "sloc", "comments", "complexity", "maintainability", "duplication", "debt"],
  "severities": ["low", "medium", "high", "critical"]
}
```

## Metrics Explained

### Lines of Code (LOC)

- **Total Lines (LOC)**: All lines including blank and comments
- **Source Lines (SLOC)**: Non-blank, non-comment lines
- **Comment Lines**: Lines containing comments
- **Blank Lines**: Empty lines

```python
metrics = analyzer.analyze_file("file.py")
print(f"Total: {metrics.loc}")
print(f"Source: {metrics.sloc}")
print(f"Comments: {metrics.comments}")
print(f"Blank: {metrics.blank}")
```

### Cyclomatic Complexity

Measures the number of linearly independent paths through code. Higher complexity indicates more difficult to test and maintain code.

**Thresholds:**
- **1-10**: Low complexity (good)
- **11-20**: Medium complexity (acceptable)
- **21-30**: High complexity (refactor recommended)
- **31+**: Critical complexity (refactor required)

```python
if metrics.complexity > 20:
    print("High complexity detected!")
```

### Maintainability Index

A 0-100 score indicating how maintainable the code is. Higher is better.

**Scale:**
- **85-100**: Highly maintainable
- **65-84**: Moderately maintainable
- **20-64**: Low maintainability
- **0-19**: Very low maintainability

```python
if metrics.maintainability < 65:
    print("Low maintainability!")
```

### Code Duplication

Percentage of code that is duplicated across files. Lower is better.

**Thresholds:**
- **0-5%**: Excellent
- **5-10%**: Good
- **10-20%**: Acceptable
- **20%+**: High duplication (refactor recommended)

```python
if project_metrics.duplication_percentage > 10:
    print("High code duplication detected!")
```

### Technical Debt

Estimated hours needed to address code quality issues.

**Calculated from:**
- Complexity over threshold (5 min per point)
- Low maintainability (1 hour per 10 points below 65)
- Large files (2 hours per 1000 lines over 500)
- Code duplication (1 hour per 1% duplication)

```python
print(f"Technical debt: {project_metrics.technical_debt_hours} hours")
print(f"Estimated cost: ${project_metrics.technical_debt_hours * 100}")
```

## Advanced Usage

### Custom File Patterns

```python
# Analyze only specific files
metrics = analyzer.analyze_project(
    "./src",
    patterns=["*.py", "!*_test.py", "!*/migrations/*"]
)
```

### Complexity Thresholds

```python
analyzer = MetricsAnalyzer()
analyzer.complexity_thresholds = {
    Severity.LOW: 5,
    Severity.MEDIUM: 10,
    Severity.HIGH: 15,
    Severity.CRITICAL: 20
}
```

### Duplication Detection

```python
# Adjust minimum lines for duplication
analyzer.duplicate_threshold = 10  # Default is 6

metrics = analyzer.analyze_project("./src")
print(f"Duplication: {metrics.duplication_percentage}%")
```

### Issue Detection

```python
metrics = analyzer.analyze_file("file.py")

for issue in metrics.issues:
    print(f"Issue: {issue}")

# Common issues:
# - "Critical complexity: 52"
# - "High complexity: 25"
# - "Low maintainability: 18.5"
# - "Large file: 1200 SLOC"
```

## Report Formats

### Text Report

```python
report = analyzer.generate_report(metrics, format="text")
print(report)
```

Output:
```
============================================================
CODE METRICS REPORT
============================================================

Generated: 2024-01-15T10:30:00Z

SUMMARY
------------------------------------------------------------
Total Files:              42
Total Lines:              12,500
Source Lines:             9,800
Comment Lines:            1,500
Blank Lines:              1,200
Functions:                320
Classes:                  85

Average Complexity:       12.30
Average Maintainability:  68.50
Code Duplication:         3.20%
Technical Debt:           24.50 hours

LANGUAGE BREAKDOWN
------------------------------------------------------------
python               35 files
javascript            7 files

COMPLEXITY DISTRIBUTION
------------------------------------------------------------
Low                  28 files
Medium               10 files
High                  3 files
Critical              1 files

TOP ISSUES
------------------------------------------------------------

./src/complex_module.py
  - Critical complexity: 52
  - Low maintainability: 18.5

./src/large_file.py
  - Large file: 1200 SLOC
```

### JSON Report

```python
report = analyzer.generate_report(metrics, format="json")
data = json.loads(report)

print(f"Total files: {data['summary']['total_files']}")
print(f"Technical debt: {data['summary']['technical_debt_hours']} hours")
```

## Best Practices

### 1. Set Quality Goals

```python
# Define acceptable thresholds
MAX_COMPLEXITY = 15
MIN_MAINTAINABILITY = 65
MAX_DUPLICATION = 5.0

metrics = analyzer.analyze_project("./src")

if metrics.avg_complexity > MAX_COMPLEXITY:
    print("❌ Complexity too high")
    
if metrics.avg_maintainability < MIN_MAINTAINABILITY:
    print("❌ Maintainability too low")
    
if metrics.duplication_percentage > MAX_DUPLICATION:
    print("❌ Too much duplication")
```

### 2. Track Trends

```python
import json
from datetime import datetime

# Save metrics
metrics = analyzer.analyze_project("./src")
timestamp = datetime.now().isoformat()

with open(f"metrics_{timestamp}.json", "w") as f:
    report = analyzer.generate_report(metrics, format="json")
    f.write(report)

# Compare over time
# Load previous metrics and compare
```

### 3. Integrate with CI/CD

```bash
#!/bin/bash
# ci-metrics.sh

python -c "
from pr_agent.metrics import get_metrics_analyzer

analyzer = get_metrics_analyzer()
metrics = analyzer.analyze_project('./src')

# Fail if quality gates not met
if metrics.avg_complexity > 20:
    print('FAIL: Complexity too high')
    exit(1)

if metrics.avg_maintainability < 60:
    print('FAIL: Maintainability too low')
    exit(1)

print('PASS: All quality gates passed')
"
```

### 4. Focus on High-Impact Files

```python
metrics = analyzer.analyze_project("./src")

# Find files with most issues
problem_files = sorted(
    [f for f in metrics.files if f.issues],
    key=lambda f: len(f.issues),
    reverse=True
)

print("Top 10 problem files:")
for file in problem_files[:10]:
    print(f"{file.path}: {len(file.issues)} issues")
```

### 5. Monitor Technical Debt

```python
# Calculate debt per developer
TEAM_SIZE = 5
HOURS_PER_SPRINT = 80

metrics = analyzer.analyze_project("./src")
debt_per_dev = metrics.technical_debt_hours / TEAM_SIZE
sprints_needed = debt_per_dev / HOURS_PER_SPRINT

print(f"Technical debt: {metrics.technical_debt_hours} hours")
print(f"Per developer: {debt_per_dev:.1f} hours")
print(f"Sprints needed: {sprints_needed:.1f}")
```

## Examples

### Complete Quality Check

```python
from pr_agent.metrics import get_metrics_analyzer, Severity

def check_code_quality(project_dir: str) -> bool:
    """Check if code meets quality standards."""
    analyzer = get_metrics_analyzer()
    metrics = analyzer.analyze_project(project_dir)
    
    issues = []
    
    # Check complexity
    if metrics.avg_complexity > 15:
        issues.append(f"High complexity: {metrics.avg_complexity:.1f}")
    
    # Check maintainability
    if metrics.avg_maintainability < 65:
        issues.append(f"Low maintainability: {metrics.avg_maintainability:.1f}")
    
    # Check duplication
    if metrics.duplication_percentage > 5:
        issues.append(f"High duplication: {metrics.duplication_percentage:.1f}%")
    
    # Check technical debt
    if metrics.technical_debt_hours > 40:
        issues.append(f"High technical debt: {metrics.technical_debt_hours:.1f} hours")
    
    if issues:
        print("❌ Quality check failed:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    
    print("✅ Quality check passed")
    return True

# Run check
check_code_quality("./src")
```

### Generate Dashboard Data

```python
def generate_dashboard_data(project_dir: str) -> dict:
    """Generate data for metrics dashboard."""
    analyzer = get_metrics_analyzer()
    metrics = analyzer.analyze_project(project_dir)
    
    return {
        "overview": {
            "files": metrics.total_files,
            "loc": metrics.total_loc,
            "functions": metrics.total_functions,
            "classes": metrics.total_classes
        },
        "quality": {
            "complexity": metrics.avg_complexity,
            "maintainability": metrics.avg_maintainability,
            "duplication": metrics.duplication_percentage,
            "debt_hours": metrics.technical_debt_hours
        },
        "languages": metrics.language_breakdown,
        "distribution": metrics.complexity_distribution,
        "top_issues": [
            {"file": f.path, "issues": f.issues}
            for f in sorted(metrics.files, key=lambda x: len(x.issues), reverse=True)[:10]
        ]
    }

data = generate_dashboard_data("./src")
print(json.dumps(data, indent=2))
```

## Troubleshooting

### High Complexity

**Problem**: Files with complexity > 30

**Solutions**:
- Break down large functions
- Extract helper methods
- Simplify conditional logic
- Use early returns

### Low Maintainability

**Problem**: Maintainability index < 65

**Solutions**:
- Reduce complexity
- Add comments and documentation
- Improve naming
- Refactor large files

### High Duplication

**Problem**: Duplication > 10%

**Solutions**:
- Extract common code to functions
- Create utility modules
- Use inheritance or composition
- Apply DRY principle

## See Also

- [Code Quality Gate](QUALITY_GATE.md) - Automated quality checks
- [Code Documentation](CODE_DOCUMENTATION.md) - Generate docs
- [Code Formatting](CODE_FORMATTING.md) - Format code
- [AI Code Review](AI_REVIEW.md) - AI-powered review
