# Code Quality Gate System

The Quality Gate system provides automated code quality checks to ensure code meets defined standards before merging.

## Features

- **Complexity Analysis**: Detect overly complex code
- **Security Scanning**: Find secrets, vulnerabilities, and dangerous patterns
- **Style Checking**: Enforce code style guidelines
- **Documentation Checking**: Ensure proper documentation
- **Configurable Rules**: Customize thresholds and blocking behavior
- **Multiple Severity Levels**: Critical, High, Medium, Low, Info
- **Detailed Reports**: Get actionable feedback on issues

## Configuration

Configure quality gate in `configuration.toml`:

```toml
[quality_gate]
# Complexity thresholds
max_cyclomatic_complexity = 10
max_cognitive_complexity = 15
max_function_length = 50
max_file_length = 500

# Coverage requirements
min_line_coverage = 80.0
min_branch_coverage = 75.0

# Security checks
check_secrets = true
check_vulnerabilities = true

# Style enforcement
enforce_style = true
max_line_length = 120
max_duplication_percentage = 5.0

# Documentation requirements
require_docstrings = true
min_comment_ratio = 0.1

# Blocking behavior
block_on_critical = true
block_on_high = true
block_on_medium = false
```

## Check Types

### 1. Complexity Analysis

Detects overly complex code that is hard to maintain:

- **Cyclomatic Complexity**: Number of independent paths through code
- **Cognitive Complexity**: How difficult code is to understand
- **Function Length**: Number of lines in a function
- **File Length**: Number of lines in a file

**Example Issues**:
```python
# High cyclomatic complexity (too many branches)
def complex_function(x):
    if x > 0:
        if x > 10:
            if x > 20:
                if x > 30:
                    return "high"
    return "low"

# Long function (too many lines)
def long_function():
    # ... 100+ lines of code ...
    pass
```

### 2. Security Scanning

Finds security vulnerabilities and sensitive data:

- **Secrets Detection**: API keys, passwords, tokens
- **Dangerous Functions**: `eval()`, `exec()`, `pickle.loads()`
- **SQL Injection**: Unsafe SQL query construction
- **Path Traversal**: Unsafe file path handling
- **Command Injection**: Unsafe shell command execution

**Example Issues**:
```python
# Secret in code (CRITICAL)
API_KEY = "sk-1234567890abcdef"

# Dangerous function (HIGH)
result = eval(user_input)

# SQL injection risk (HIGH)
query = f"SELECT * FROM users WHERE id = {user_id}"

# Command injection risk (HIGH)
os.system(f"ls {user_input}")
```

### 3. Style Checking

Enforces code style guidelines:

- **Line Length**: Maximum characters per line
- **Trailing Whitespace**: Spaces at end of lines
- **Indentation**: Consistent indentation
- **Naming Conventions**: PEP 8 naming rules

**Example Issues**:
```python
# Line too long (MEDIUM)
very_long_variable_name = some_function_with_many_parameters(param1, param2, param3, param4, param5, param6, param7)

# Trailing whitespace (LOW)
x = 1   

# Bad naming (MEDIUM)
def MyFunction():  # Should be my_function
    pass
```

### 4. Documentation Checking

Ensures proper documentation:

- **Missing Docstrings**: Public functions/classes without docstrings
- **Comment Ratio**: Percentage of lines that are comments
- **TODO Comments**: Unresolved TODO items

**Example Issues**:
```python
# Missing docstring (MEDIUM)
def public_function(x, y):
    return x + y

# Should have docstring:
def public_function(x, y):
    """Add two numbers."""
    return x + y
```

## Severity Levels

Issues are classified by severity:

- **CRITICAL**: Security vulnerabilities, secrets in code
- **HIGH**: Dangerous patterns, major security risks
- **MEDIUM**: Style violations, missing documentation
- **LOW**: Minor style issues, suggestions
- **INFO**: Informational messages

## Blocking Behavior

Configure which severity levels block merges:

```python
from pr_agent.quality import QualityGateConfig

config = QualityGateConfig(
    block_on_critical=True,   # Always block on critical issues
    block_on_high=True,       # Block on high severity issues
    block_on_medium=False,    # Don't block on medium issues
)
```

## Usage

### Python API

```python
from pr_agent.quality import QualityGate, QualityGateConfig

# Create quality gate with default config
gate = QualityGate()

# Or with custom config
config = QualityGateConfig(
    max_cyclomatic_complexity=15,
    min_line_coverage=90.0,
    block_on_medium=True
)
gate = QualityGate(config)

# Check files
report = gate.check_files([
    "src/module1.py",
    "src/module2.py"
])

# Check results
if report.passed:
    print("✓ All checks passed!")
else:
    print(f"✗ Found {report.metrics['total_issues']} issues")
    
    # Get blocking issues
    blocking = report.get_blocking_issues(config)
    for issue in blocking:
        print(f"{issue.severity.value}: {issue.message}")
        print(f"  File: {issue.file_path}:{issue.line_number}")
```

### REST API

#### Run Quality Check

```bash
POST /api/quality/check
Content-Type: application/json
Authorization: Bearer <token>

{
  "file_paths": [
    "src/module1.py",
    "src/module2.py"
  ],
  "config": {
    "max_cyclomatic_complexity": 15,
    "block_on_medium": true
  }
}
```

Response:
```json
{
  "passed": false,
  "issues": [
    {
      "check_type": "security",
      "severity": "critical",
      "message": "Potential secret detected: API key",
      "file_path": "src/module1.py",
      "line_number": 10,
      "column": 12,
      "code": "API_KEY = 'sk-123'",
      "suggestion": "Move secrets to environment variables"
    }
  ],
  "metrics": {
    "files_checked": 2,
    "total_issues": 5,
    "by_severity": {
      "critical": 1,
      "high": 2,
      "medium": 2
    },
    "by_type": {
      "security": 3,
      "complexity": 1,
      "style": 1
    }
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "duration_seconds": 2.5
}
```

#### Get Quality Configuration

```bash
GET /api/quality/config
Authorization: Bearer <token>
```

Response:
```json
{
  "max_cyclomatic_complexity": 10,
  "max_cognitive_complexity": 15,
  "max_function_length": 50,
  "max_file_length": 500,
  "min_line_coverage": 80.0,
  "min_branch_coverage": 75.0,
  "check_secrets": true,
  "check_vulnerabilities": true,
  "enforce_style": true,
  "max_line_length": 120,
  "max_duplication_percentage": 5.0,
  "require_docstrings": true,
  "min_comment_ratio": 0.1,
  "block_on_critical": true,
  "block_on_high": true,
  "block_on_medium": false
}
```

#### Update Quality Configuration

```bash
PUT /api/quality/config
Content-Type: application/json
Authorization: Bearer <token>

{
  "max_cyclomatic_complexity": 15,
  "min_line_coverage": 90.0,
  "block_on_medium": true
}
```

## Integration with PR Review

Quality gate automatically runs on pull requests:

```python
from pr_agent.quality import QualityGate
from pr_agent.git_providers import get_git_provider

# Get PR files
git_provider = get_git_provider()
pr_files = git_provider.get_pr_files(pr_number)

# Run quality checks
gate = QualityGate()
report = gate.check_files(pr_files)

# Post results as PR comment
if not report.passed:
    comment = format_quality_report(report)
    git_provider.post_comment(pr_number, comment)
```

## Quality Report Format

The quality report includes:

```python
class QualityReport:
    passed: bool                    # Overall pass/fail
    issues: List[QualityIssue]     # All detected issues
    metrics: Dict                   # Summary metrics
    timestamp: datetime             # When check ran
    duration_seconds: float         # How long it took
    
    # Helper methods
    def get_blocking_issues(config) -> List[QualityIssue]
    def get_issues_by_severity(severity) -> List[QualityIssue]
    def get_issues_by_type(check_type) -> List[QualityIssue]
```

## Best Practices

### 1. Start with Lenient Rules

Begin with relaxed thresholds and gradually tighten:

```toml
# Initial configuration
max_cyclomatic_complexity = 20  # Start high
block_on_medium = false         # Don't block on medium issues
```

### 2. Focus on Critical Issues First

Always block on critical security issues:

```toml
block_on_critical = true
check_secrets = true
check_vulnerabilities = true
```

### 3. Customize for Your Team

Adjust rules based on your team's standards:

```toml
# For strict teams
max_cyclomatic_complexity = 5
require_docstrings = true
min_line_coverage = 95.0

# For pragmatic teams
max_cyclomatic_complexity = 15
require_docstrings = false
min_line_coverage = 70.0
```

### 4. Use in CI/CD Pipeline

Integrate quality gate in your CI pipeline:

```yaml
# .github/workflows/quality.yml
name: Quality Gate
on: [pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Quality Gate
        run: |
          python -m pr_agent.quality check \
            --files $(git diff --name-only origin/main)
```

### 5. Provide Clear Feedback

When quality checks fail, provide actionable suggestions:

```python
issue = QualityIssue(
    check_type=CheckType.COMPLEXITY,
    severity=Severity.HIGH,
    message="Function has cyclomatic complexity of 15 (max: 10)",
    suggestion="Consider breaking this function into smaller functions"
)
```

## Troubleshooting

### False Positives

If you get false positives, you can:

1. **Adjust thresholds**: Increase limits in configuration
2. **Disable specific checks**: Set `check_secrets = false`
3. **Add exceptions**: Use inline comments to suppress warnings

```python
# quality: disable=complexity
def complex_but_necessary_function():
    # ... complex logic ...
    pass
```

### Performance Issues

For large codebases:

1. **Check only changed files**: Don't check entire codebase
2. **Use caching**: Cache analysis results
3. **Run in parallel**: Process files concurrently

```python
# Only check changed files
changed_files = git_provider.get_changed_files()
report = gate.check_files(changed_files)
```

## Metrics and Monitoring

Quality gate exports Prometheus metrics:

- `quality_checks_total`: Total number of checks run
- `quality_issues_total`: Total issues found by severity/type
- `quality_check_duration_seconds`: Check duration
- `quality_gate_passed`: Whether gate passed (1) or failed (0)

View metrics at `/metrics` endpoint.

## See Also

- [Security Documentation](SECURITY.md)
- [Monitoring Setup](MONITORING_SETUP.md)
- [API Reference](API_REFERENCE.md)
