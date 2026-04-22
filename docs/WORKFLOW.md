# Code Review Workflow System

Automated multi-stage code review pipeline for comprehensive code quality analysis.

## Overview

The workflow system orchestrates multiple review stages in a configurable pipeline, providing comprehensive code analysis including syntax checking, style validation, security scanning, and complexity analysis.

## Features

- **Multi-Stage Pipeline**: Configurable review stages executed in sequence
- **Parallel Execution**: Optional parallel processing of independent stages
- **Issue Tracking**: Comprehensive issue detection with severity levels
- **Multiple Report Formats**: Text, Markdown, and JSON output formats
- **Flexible Configuration**: Customizable thresholds and enabled stages
- **Error Handling**: Graceful failure handling with detailed error reporting

## Review Stages

### Available Stages

1. **INITIALIZATION**: File validation and preparation
2. **SYNTAX**: Syntax checking and parsing validation
3. **STYLE**: Code style and formatting checks
4. **SECURITY**: Security vulnerability scanning
5. **COMPLEXITY**: Code complexity analysis
6. **DOCUMENTATION**: Documentation coverage checks
7. **DEPENDENCIES**: Dependency analysis and validation
8. **QUALITY_GATE**: Overall quality gate checks
9. **FINALIZATION**: Result aggregation and reporting

## Usage

### Basic Usage

```python
from pr_agent.workflow import ReviewPipeline, ReviewConfig, ReviewStage

# Create configuration
config = ReviewConfig(
    enabled_stages={
        ReviewStage.INITIALIZATION,
        ReviewStage.SYNTAX,
        ReviewStage.STYLE,
        ReviewStage.SECURITY,
        ReviewStage.FINALIZATION
    },
    max_complexity=10,
    fail_on_critical=True
)

# Create pipeline
pipeline = ReviewPipeline(config)

# Run review
result = await pipeline.review_files(['path/to/file.py'])

# Check results
if result.success:
    print(f"Review passed! {len(result.issues)} issues found")
else:
    print(f"Review failed: {result.summary}")
```

### Configuration Options

```python
config = ReviewConfig(
    # Enabled stages
    enabled_stages={ReviewStage.SYNTAX, ReviewStage.STYLE},
    
    # Complexity thresholds
    max_complexity=10,
    min_maintainability=65.0,
    max_file_lines=1000,
    
    # Formatting
    auto_format=False,
    format_languages=['python', 'javascript', 'typescript'],
    
    # AI-powered analysis
    enable_ai=False,
    ai_model='gpt-4',
    
    # Additional checks
    check_dependencies=True,
    check_secrets=True,
    require_docstrings=True,
    min_doc_coverage=80.0,
    
    # Failure conditions
    fail_on_critical=True,
    fail_on_high=False,
    
    # Execution
    parallel_execution=True
)
```

### Review Results

```python
result = await pipeline.review_files(files)

# Access results
print(f"Success: {result.success}")
print(f"Duration: {result.total_duration_seconds}s")
print(f"Issues: {len(result.issues)}")

# Summary statistics
summary = result.summary
print(f"Total issues: {summary['total_issues']}")
print(f"Critical: {summary['severity_counts']['critical']}")
print(f"High: {summary['severity_counts']['high']}")
print(f"Stages completed: {summary['stages_completed']}")
print(f"Stages failed: {summary['stages_failed']}")

# Individual issues
for issue in result.issues:
    print(f"{issue.severity.value}: {issue.message}")
    print(f"  File: {issue.file_path}:{issue.line_number}")
    print(f"  Category: {issue.category}")
    if issue.auto_fixable:
        print(f"  Fix: {issue.suggested_fix}")
```

### Report Formatting

```python
# Text report
text_report = result.format_report('text')
print(text_report)

# Markdown report
markdown_report = result.format_report('markdown')
with open('review_report.md', 'w') as f:
    f.write(markdown_report)

# JSON report
json_report = result.format_report('json')
import json
with open('review_report.json', 'w') as f:
    f.write(json_report)
```

## REST API

### Run Review Workflow

```bash
POST /api/workflow/review
Content-Type: application/json

{
  "files": ["src/main.py", "src/utils.py"],
  "config": {
    "enabled_stages": ["initialization", "syntax", "style", "finalization"],
    "max_complexity": 10,
    "fail_on_critical": true
  }
}
```

Response:
```json
{
  "success": true,
  "total_duration_seconds": 2.5,
  "issues": [
    {
      "severity": "medium",
      "category": "style",
      "message": "Line too long (120 > 88 characters)",
      "file_path": "src/main.py",
      "line_number": 42,
      "auto_fixable": true,
      "suggested_fix": "Break line into multiple lines"
    }
  ],
  "summary": {
    "total_issues": 1,
    "severity_counts": {
      "critical": 0,
      "high": 0,
      "medium": 1,
      "low": 0,
      "info": 0
    },
    "stages_completed": 4,
    "stages_failed": 0
  }
}
```

### Get Available Stages

```bash
GET /api/workflow/stages
```

Response:
```json
{
  "stages": [
    "initialization",
    "syntax",
    "style",
    "security",
    "complexity",
    "documentation",
    "dependencies",
    "quality_gate",
    "finalization"
  ]
}
```

### Validate Configuration

```bash
POST /api/workflow/config
Content-Type: application/json

{
  "enabled_stages": ["syntax", "style"],
  "max_complexity": 10
}
```

Response:
```json
{
  "valid": true,
  "config": {
    "enabled_stages": ["syntax", "style"],
    "max_complexity": 10,
    "min_maintainability": 65.0,
    "fail_on_critical": true
  }
}
```

## Issue Severity Levels

- **CRITICAL**: Must be fixed immediately (security vulnerabilities, syntax errors)
- **HIGH**: Should be fixed soon (major bugs, performance issues)
- **MEDIUM**: Should be addressed (code smells, maintainability issues)
- **LOW**: Nice to fix (minor style issues, suggestions)
- **INFO**: Informational only (tips, best practices)

## Issue Categories

- **syntax**: Syntax and parsing errors
- **style**: Code style and formatting issues
- **security**: Security vulnerabilities
- **complexity**: Code complexity issues
- **performance**: Performance problems
- **maintainability**: Maintainability concerns
- **documentation**: Documentation issues
- **dependencies**: Dependency problems
- **best_practices**: Best practice violations

## Integration Examples

### CI/CD Integration

```yaml
# GitHub Actions
- name: Run Code Review
  run: |
    curl -X POST http://localhost:8000/api/workflow/review \
      -H "Content-Type: application/json" \
      -d '{
        "files": ["src/**/*.py"],
        "config": {
          "enabled_stages": ["syntax", "style", "security"],
          "fail_on_critical": true
        }
      }'
```

### Pre-commit Hook

```python
#!/usr/bin/env python3
import asyncio
from pr_agent.workflow import ReviewPipeline, ReviewConfig, ReviewStage

async def main():
    config = ReviewConfig(
        enabled_stages={
            ReviewStage.SYNTAX,
            ReviewStage.STYLE,
            ReviewStage.SECURITY
        },
        fail_on_critical=True
    )
    
    pipeline = ReviewPipeline(config)
    result = await pipeline.review_files(['staged_files.txt'])
    
    if not result.success:
        print("Review failed! Fix issues before committing.")
        for issue in result.issues:
            if issue.severity.value in ['critical', 'high']:
                print(f"{issue.severity.value}: {issue.message}")
        exit(1)

if __name__ == '__main__':
    asyncio.run(main())
```

## Best Practices

1. **Start Simple**: Begin with basic stages (syntax, style) and add more as needed
2. **Set Appropriate Thresholds**: Adjust complexity and maintainability thresholds for your project
3. **Use Parallel Execution**: Enable parallel execution for faster reviews on large codebases
4. **Review Reports**: Regularly review generated reports to identify patterns
5. **Automate**: Integrate into CI/CD pipelines for consistent code quality
6. **Customize**: Tailor enabled stages and configurations to your team's needs

## Troubleshooting

### Pipeline Fails Immediately

- Check that all files exist and are readable
- Verify file paths are correct
- Ensure enabled stages are valid

### No Issues Detected

- Lower thresholds (max_complexity, min_maintainability)
- Enable more stages
- Check that files contain actual code

### Performance Issues

- Enable parallel execution
- Reduce number of enabled stages
- Process files in smaller batches

## See Also

- [Code Quality Gate](QUALITY_GATE.md)
- [Code Metrics](CODE_METRICS.md)
- [Security Scanning](SECURITY.md)
- [AI Review](AI_REVIEW.md)
