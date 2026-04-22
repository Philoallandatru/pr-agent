# Code Review Rules Engine

The Rules Engine provides a flexible, extensible system for defining and enforcing code review rules.

## Features

- **Built-in Rules**: Pre-configured rules for common issues (SQL injection, hardcoded secrets, code style, complexity)
- **Custom Rules**: Define your own rules with pattern matching and custom checkers
- **Rule Sets**: Group related rules for different contexts (security, style, performance)
- **Severity Levels**: ERROR, WARNING, INFO for prioritizing violations
- **Categories**: SECURITY, STYLE, PERFORMANCE, MAINTAINABILITY, DOCUMENTATION
- **File Patterns**: Control which files each rule applies to
- **Import/Export**: Share rule configurations across teams

## Built-in Rules

### Security Rules

#### SEC001: SQL Injection Risk
Detects potential SQL injection vulnerabilities from string concatenation in queries.

**Patterns detected:**
- `execute("... %s ...")`
- `cursor.execute(f"...")`
- String concatenation with `+` operator

**Example violation:**
```python
query = "SELECT * FROM users WHERE id = " + user_id
cursor.execute(query)
```

**Fix:**
```python
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
```

#### SEC002: Hardcoded Secrets
Detects hardcoded passwords, API keys, and secrets in code.

**Patterns detected:**
- `password = "..."`
- `api_key = "..."`
- `secret = "..."`
- `token = "..."`

**Example violation:**
```python
API_KEY = "sk-1234567890abcdef"
```

**Fix:**
```python
API_KEY = os.environ.get("API_KEY")
```

### Style Rules

#### STYLE001: Line Too Long
Enforces maximum line length (default: 120 characters).

**Configuration:**
```python
rule.metadata = {"max_length": 100}  # Custom limit
```

#### STYLE002: Trailing Whitespace
Detects lines with trailing whitespace.

**Example violation:**
```python
def foo():  
    pass  
```

### Complexity Rules

#### COMPLEX001: High Function Complexity
Detects functions with high cyclomatic complexity (default threshold: 10).

**Configuration:**
```python
rule.metadata = {"max_complexity": 15}  # Custom threshold
```

## Usage

### Python API

```python
from pr_agent.rules import RulesEngine, Rule, RuleSeverity, RuleCategory

# Create engine (loads built-in rules)
engine = RulesEngine()

# Check a file
violations = engine.check_file(
    file_path="app.py",
    content=open("app.py").read()
)

# Print violations
for v in violations:
    print(f"{v.severity.value}: {v.message} at line {v.line_number}")
```

### Check Multiple Files

```python
files = {
    "app.py": open("app.py").read(),
    "models.py": open("models.py").read()
}

results = engine.check_files(files)

for file_path, violations in results.items():
    print(f"\n{file_path}: {len(violations)} violations")
    for v in violations:
        print(f"  Line {v.line_number}: {v.message}")
```

### Custom Rules

```python
# Define a custom rule
custom_rule = Rule(
    rule_id="CUSTOM001",
    name="No Print Statements",
    description="Detect print() calls in production code",
    severity=RuleSeverity.WARNING,
    category=RuleCategory.STYLE,
    file_patterns=["**/*.py"],
    exclude_patterns=["**/test_*.py", "**/tests/**"],
    enabled=True
)

# Add a checker function
def check_print_statements(file_path, content, context, rule):
    violations = []
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        if 'print(' in line:
            violations.append(RuleViolation(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                severity=rule.severity,
                category=rule.category,
                message="Avoid print() in production code",
                file_path=file_path,
                line_number=i,
                code_snippet=line.strip(),
                suggestion="Use logging instead"
            ))
    return violations

custom_rule.checker = check_print_statements

# Register the rule
engine.register_rule(custom_rule)
```

### Rule Sets

```python
from pr_agent.rules import RuleSet

# Create a rule set for security checks
security_set = RuleSet(
    name="security",
    description="Security-focused rules",
    rules=[
        engine.get_rule("SEC001"),
        engine.get_rule("SEC002")
    ],
    enabled=True
)

engine.register_rule_set(security_set)

# Use the rule set
rule_set = engine.get_rule_set("security")
violations = []
for rule in rule_set.get_enabled_rules():
    violations.extend(rule.check(file_path, content, {}))
```

### Import/Export Rules

```python
# Export rules to JSON
rules_data = engine.export_rules()
with open("rules.json", "w") as f:
    json.dump(rules_data, f, indent=2)

# Import rules from JSON
with open("rules.json") as f:
    rules_data = json.load(f)
engine.import_rules(rules_data)
```

## REST API

### Check File

```bash
POST /api/rules/check
Content-Type: application/json

{
  "file_path": "app.py",
  "content": "def query_user(id):\n    query = \"SELECT * FROM users WHERE id = \" + id\n    return execute(query)",
  "rule_ids": ["SEC001", "SEC002"]  # Optional: specific rules
}
```

**Response:**
```json
{
  "file_path": "app.py",
  "violations": [
    {
      "rule_id": "SEC001",
      "rule_name": "SQL Injection Risk",
      "severity": "error",
      "category": "security",
      "message": "Potential SQL injection vulnerability detected",
      "line_number": 2,
      "code_snippet": "query = \"SELECT * FROM users WHERE id = \" + id",
      "suggestion": "Use parameterized queries instead of string concatenation"
    }
  ],
  "total_violations": 1
}
```

### Check Multiple Files

```bash
POST /api/rules/check-multiple
Content-Type: application/json

{
  "files": {
    "app.py": "...",
    "models.py": "..."
  },
  "rule_ids": null  # Check all enabled rules
}
```

### List Rules

```bash
GET /api/rules?enabled_only=true&category=security
```

**Response:**
```json
{
  "rules": [
    {
      "rule_id": "SEC001",
      "name": "SQL Injection Risk",
      "description": "Detect potential SQL injection vulnerabilities",
      "severity": "error",
      "category": "security",
      "file_patterns": ["**/*.py", "**/*.js", "**/*.java"],
      "exclude_patterns": ["**/test_*.py"],
      "enabled": true,
      "metadata": {}
    }
  ],
  "total": 1
}
```

### Create Custom Rule

```bash
POST /api/rules
Content-Type: application/json

{
  "rule_id": "CUSTOM001",
  "name": "No Print Statements",
  "description": "Detect print() calls",
  "severity": "warning",
  "category": "style",
  "file_patterns": ["**/*.py"],
  "exclude_patterns": ["**/test_*.py"],
  "enabled": true
}
```

### Delete Rule

```bash
DELETE /api/rules/CUSTOM001
```

### List Rule Sets

```bash
GET /api/rules/sets
```

### Create Rule Set

```bash
POST /api/rules/sets
Content-Type: application/json

{
  "name": "security",
  "description": "Security-focused rules",
  "rule_ids": ["SEC001", "SEC002"],
  "enabled": true
}
```

### Export Rules

```bash
GET /api/rules/export
```

### Import Rules

```bash
POST /api/rules/import
Content-Type: application/json

{
  "rules": [...],
  "rule_sets": [...]
}
```

## Configuration

Rules can be configured via metadata:

```python
# Line length rule
rule = engine.get_rule("STYLE001")
rule.metadata["max_length"] = 100

# Complexity rule
rule = engine.get_rule("COMPLEX001")
rule.metadata["max_complexity"] = 15
```

## File Pattern Matching

Rules use glob patterns to match files:

- `**/*.py` - All Python files recursively
- `*.js` - JavaScript files in current directory
- `src/**/*.java` - Java files under src/
- `!**/test_*.py` - Exclude test files (use exclude_patterns)

## Best Practices

1. **Start with Built-in Rules**: Use the pre-configured rules as a baseline
2. **Customize Gradually**: Adjust severity and thresholds based on your team's needs
3. **Use Rule Sets**: Group rules by context (pre-commit, CI, security audit)
4. **Document Custom Rules**: Add clear descriptions and examples
5. **Test Rules**: Verify custom rules work as expected before deploying
6. **Share Configurations**: Export/import rules to maintain consistency across projects

## Integration

### Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

python -c "
from pr_agent.rules import get_engine
import sys

engine = get_engine()
violations = []

for file in sys.argv[1:]:
    with open(file) as f:
        violations.extend(engine.check_file(file, f.read()))

if violations:
    for v in violations:
        print(f'{v.file_path}:{v.line_number}: {v.severity.value}: {v.message}')
    sys.exit(1)
" $(git diff --cached --name-only --diff-filter=ACM)
```

### CI/CD Pipeline

```yaml
# .github/workflows/code-review.yml
name: Code Review

on: [pull_request]

jobs:
  rules-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Check Rules
        run: |
          python -m pr_agent.cli.rules check \
            --files "**/*.py" \
            --rule-set security \
            --fail-on error
```

## Troubleshooting

### Rule Not Matching Files

Check file patterns:
```python
rule = engine.get_rule("SEC001")
print(rule.matches_file("app.py"))  # Should return True
print(rule.file_patterns)
```

### Custom Checker Not Working

Ensure checker signature is correct:
```python
def my_checker(file_path: str, content: str, context: dict, rule: Rule) -> List[RuleViolation]:
    # Must return list of RuleViolation objects
    return []
```

### Performance Issues

- Limit file patterns to relevant files
- Use exclude_patterns to skip large directories
- Check specific rules instead of all rules
- Cache file content when checking multiple rules

## See Also

- [Workflow System](WORKFLOW.md) - Integrate rules into review pipelines
- [Quality Reports](REPORTS.md) - Generate reports from rule violations
- [Impact Analysis](IMPACT_ANALYSIS.md) - Assess impact of rule violations
