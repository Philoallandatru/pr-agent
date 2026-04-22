# AI-Driven Code Review System

The AI-driven code review system provides automated code analysis using both static analysis and optional AI-powered insights.

## Features

- **Static Analysis**: Built-in checks for common issues
- **AI-Powered Analysis**: Optional deep analysis using AI models
- **Multiple Categories**: Security, bugs, performance, maintainability, style
- **Severity Levels**: Critical, high, medium, low, info
- **Detailed Reports**: Comprehensive findings with suggestions

## Review Categories

### Security
- Dangerous function usage (eval, exec, pickle)
- Hardcoded credentials
- SQL injection risks
- Command injection vulnerabilities

### Bugs
- Syntax errors
- Type errors
- Logic errors
- Exception handling issues

### Performance
- String concatenation in loops
- Inefficient algorithms
- Unnecessary computations
- Resource leaks

### Maintainability
- Too many function arguments
- Long functions
- Deep nesting
- Code duplication

### Style
- Naming conventions
- Code formatting
- Documentation quality

## Usage

### Basic Usage

```python
from pr_agent.ai_review import AICodeReviewer

# Create reviewer
reviewer = AICodeReviewer()

# Review a single file
findings = reviewer.review_file("path/to/file.py")

# Review a pull request
pr_files = [
    {'path': 'file1.py', 'diff': '...'},
    {'path': 'file2.py', 'diff': '...'}
]
report = reviewer.review_pr(pr_files)

print(f"Found {report.total_findings} issues")
print(f"Critical: {report.critical_count}")
print(f"High: {report.high_count}")
```

### With AI Handler

```python
from pr_agent.ai_review import AICodeReviewer, configure_ai_reviewer
from pr_agent.algo.ai_handlers import AiHandler

# Configure AI handler
ai_handler = AiHandler()
configure_ai_reviewer(ai_handler)

# Use global reviewer
from pr_agent.ai_review import get_ai_reviewer
reviewer = get_ai_reviewer()

# Review with AI insights
findings = reviewer.review_file("complex_code.py")
```

## Review Findings

Each finding includes:

```python
@dataclass
class ReviewFinding:
    category: ReviewCategory          # Issue category
    severity: ReviewSeverity          # Severity level
    title: str                        # Short title
    description: str                  # Detailed description
    file_path: str                    # File path
    line_start: int                   # Start line
    line_end: Optional[int]           # End line
    code_snippet: str                 # Code snippet
    suggestion: Optional[str]         # Fix suggestion
    confidence: Optional[float]       # Confidence (0-1)
```

## Review Report

```python
@dataclass
class AIReviewReport:
    timestamp: float                  # Report timestamp
    files_reviewed: int               # Number of files
    total_findings: int               # Total findings
    findings: List[ReviewFinding]     # All findings
    summary: Optional[str]            # Summary text
    
    # Computed properties
    critical_count: int               # Critical issues
    high_count: int                   # High severity
    medium_count: int                 # Medium severity
    low_count: int                    # Low severity
    by_category: Dict[str, int]       # Group by category
```

## API Endpoints

### Review File

```bash
POST /api/ai-review/file
Content-Type: application/json

{
  "file_path": "path/to/file.py",
  "use_ai": true
}
```

Response:
```json
{
  "findings": [
    {
      "category": "security",
      "severity": "critical",
      "title": "Dangerous eval() usage",
      "description": "Using eval() with user input is dangerous",
      "file_path": "file.py",
      "line_start": 10,
      "code_snippet": "result = eval(user_input)",
      "suggestion": "Use ast.literal_eval() or json.loads()"
    }
  ]
}
```

### Review Pull Request

```bash
POST /api/ai-review/pr
Content-Type: application/json

{
  "files": [
    {
      "path": "file1.py",
      "diff": "..."
    }
  ],
  "use_ai": true
}
```

Response:
```json
{
  "timestamp": 1234567890.0,
  "files_reviewed": 2,
  "total_findings": 5,
  "critical_count": 1,
  "high_count": 2,
  "medium_count": 2,
  "findings": [...],
  "summary": "Found 5 issues: 1 critical, 2 high, 2 medium"
}
```

## Static Analysis Checks

### Security Checks

1. **eval() usage**: Detects dangerous eval() calls
2. **exec() usage**: Detects exec() calls
3. **pickle usage**: Detects unsafe pickle operations
4. **subprocess shell=True**: Detects shell injection risks

### Performance Checks

1. **String concatenation in loops**: Detects inefficient string building
2. **Repeated computations**: Identifies redundant calculations

### Maintainability Checks

1. **Too many arguments**: Functions with >5 parameters
2. **Long functions**: Functions with >50 lines
3. **Deep nesting**: Nesting depth >4 levels

## AI-Powered Analysis

When an AI handler is configured, the system can:

1. **Understand context**: Analyze code in broader context
2. **Detect subtle issues**: Find complex logic errors
3. **Provide better suggestions**: Context-aware recommendations
4. **Learn patterns**: Improve over time

### AI Analysis Prompt

The system uses a structured prompt:

```
Analyze this code for potential issues:

File: {file_path}
Code:
{code}

Focus on:
- Security vulnerabilities
- Potential bugs
- Performance issues
- Code maintainability
- Best practices

Return findings as JSON array with:
- category: security/bug/performance/maintainability/style
- severity: critical/high/medium/low/info
- title: Short description
- description: Detailed explanation
- line: Line number
- code_snippet: Relevant code
- suggestion: How to fix
- confidence: 0.0-1.0
```

## Configuration

Add to `configuration.toml`:

```toml
[ai_review]
# Enable AI-powered analysis
enable_ai = true

# Minimum confidence threshold (0.0-1.0)
min_confidence = 0.7

# Maximum findings per file
max_findings_per_file = 50

# Categories to check
categories = ["security", "bug", "performance", "maintainability", "style"]

# Severity levels to report
min_severity = "low"

# Static analysis settings
[ai_review.static]
check_security = true
check_performance = true
check_maintainability = true
max_function_args = 5
max_function_lines = 50
max_nesting_depth = 4
```

## Best Practices

1. **Start with static analysis**: Fast and reliable
2. **Use AI for complex code**: Deep analysis when needed
3. **Review findings**: AI suggestions need human review
4. **Set confidence threshold**: Filter low-confidence findings
5. **Integrate with CI/CD**: Automate reviews in pipeline

## Examples

### Example 1: Security Issue

```python
# Bad: Dangerous eval usage
user_input = request.get('code')
result = eval(user_input)  # CRITICAL: eval() with user input
```

Finding:
- Category: Security
- Severity: Critical
- Suggestion: Use `ast.literal_eval()` or `json.loads()`

### Example 2: Performance Issue

```python
# Bad: String concatenation in loop
result = ""
for i in range(10000):
    result += str(i)  # MEDIUM: Inefficient string building
```

Finding:
- Category: Performance
- Severity: Medium
- Suggestion: Use `''.join()` or `io.StringIO()`

### Example 3: Maintainability Issue

```python
# Bad: Too many arguments
def process_data(a, b, c, d, e, f, g):  # MEDIUM: Too many args
    pass
```

Finding:
- Category: Maintainability
- Severity: Medium
- Suggestion: Use a configuration object or dataclass

## Integration

### With PR Review Workflow

```python
from pr_agent.ai_review import get_ai_reviewer
from pr_agent.git_providers import get_git_provider

# Get PR files
git_provider = get_git_provider()
pr_files = git_provider.get_pr_files(pr_number)

# Review with AI
reviewer = get_ai_reviewer()
report = reviewer.review_pr(pr_files)

# Post findings as comments
for finding in report.findings:
    if finding.severity in ['critical', 'high']:
        git_provider.post_comment(
            pr_number,
            finding.file_path,
            finding.line_start,
            f"**{finding.title}**\n\n{finding.description}\n\n{finding.suggestion}"
        )
```

### With Quality Gates

```python
from pr_agent.ai_review import get_ai_reviewer

reviewer = get_ai_reviewer()
report = reviewer.review_pr(pr_files)

# Enforce quality gates
if report.critical_count > 0:
    raise Exception("Critical issues found - blocking merge")

if report.high_count > 5:
    raise Exception("Too many high-severity issues")
```

## Troubleshooting

### No AI Analysis

If AI analysis is not working:

1. Check AI handler is configured
2. Verify API credentials
3. Check network connectivity
4. Review error logs

### Too Many False Positives

If getting too many false positives:

1. Increase confidence threshold
2. Disable specific categories
3. Add ignore patterns
4. Fine-tune AI prompts

### Performance Issues

If reviews are slow:

1. Disable AI for large files
2. Use static analysis only
3. Review only changed files
4. Increase timeout limits

## See Also

- [Quality Gate System](QUALITY_GATE.md)
- [Code Suggestions](CODE_SUGGESTIONS.md)
- [Model Management](MODEL_MANAGEMENT.md)
