# Code Review Templates

The Review Templates system provides customizable checklists for different types of code reviews. Templates help ensure consistent and thorough reviews across your team.

## Features

- **Built-in Templates**: Pre-configured templates for common review scenarios
- **Custom Templates**: Create your own templates with custom check items
- **Template Categories**: Security, Performance, Architecture, Style, General
- **Severity Levels**: Critical, High, Medium, Low, Info
- **Import/Export**: Share templates across teams
- **REST API**: Full API for template management

## Built-in Templates

### Security Review (`builtin_security`)
Comprehensive security review checklist covering:
- Authentication & Authorization
- Input Validation
- Cryptography
- Security Logging

### Performance Review (`builtin_performance`)
Performance optimization checklist:
- Database Query Optimization
- Caching Strategy
- Asynchronous Processing

### Architecture Review (`builtin_architecture`)
Software architecture and design review:
- SOLID Principles
- Coupling & Cohesion
- Design Patterns

### Style Review (`builtin_style`)
Code style and readability checklist:
- Naming Conventions
- Comments & Documentation
- Code Formatting

### General Review (`builtin_general`)
General purpose code review:
- Correctness
- Test Coverage
- Error Handling
- Documentation

## Quick Start

### Python API

```python
from pr_agent.review_templates import get_template_manager

# Get the template manager
manager = get_template_manager()

# List all templates
templates = manager.list_templates()

# Get a specific template
template = manager.get_template("builtin_security")

# Apply a template to a file
result = manager.apply_template(
    template_id="builtin_security",
    file_path="app.py",
    content=open("app.py").read()
)

# Check results
print(f"Passed: {result.checks_passed}")
print(f"Failed: {result.checks_failed}")
for finding in result.findings:
    print(f"{finding['check_id']}: {finding['message']}")
```

### REST API

#### List Templates

```bash
GET /api/review-templates
GET /api/review-templates?category=security
GET /api/review-templates?enabled_only=true
```

Response:
```json
{
  "templates": [
    {
      "template_id": "builtin_security",
      "name": "Security Review",
      "description": "Comprehensive security review checklist",
      "category": "security",
      "check_items": [...],
      "enabled": true
    }
  ],
  "count": 1
}
```

#### Get Template

```bash
GET /api/review-templates/{template_id}
```

#### Create Template

```bash
POST /api/review-templates
Content-Type: application/json

{
  "template_id": "custom-security",
  "name": "Custom Security Review",
  "description": "Custom security checklist",
  "category": "security",
  "check_items": [
    {
      "check_id": "SEC-001",
      "title": "Authentication Check",
      "description": "Verify authentication is required",
      "severity": "critical",
      "required": true,
      "guidance": "All endpoints should require authentication",
      "examples": ["Check for @require_auth decorator"]
    }
  ],
  "enabled": true
}
```

#### Delete Template

```bash
DELETE /api/review-templates/{template_id}
```

#### Apply Template

```bash
POST /api/review-templates/{template_id}/apply
Content-Type: application/json

{
  "file_path": "app.py",
  "content": "def login(username, password):\n    ...",
  "context": {
    "repository": "myorg/myrepo",
    "pull_request": "#123"
  }
}
```

Response:
```json
{
  "template_id": "builtin_security",
  "template_name": "Security Review",
  "file_path": "app.py",
  "summary": {
    "template_id": "builtin_security",
    "template_name": "Security Review",
    "file_path": "app.py",
    "total_checks": 5,
    "passed": 3,
    "failed": 2,
    "skipped": 0,
    "pass_rate": 0.6,
    "critical_findings": 1
  },
  "findings": [
    {
      "check_id": "SEC_AUTH",
      "status": "failed",
      "message": "Missing authentication check",
      "severity": "critical",
      "line_number": 10,
      "suggestion": "Add @require_auth decorator"
    }
  ]
}
```

#### Export Templates

```bash
GET /api/review-templates/export
GET /api/review-templates/export?template_ids=builtin_security,builtin_performance
```

Response:
```json
{
  "version": "1.0",
  "templates": [...]
}
```

#### Import Templates

```bash
POST /api/review-templates/import?overwrite=false
Content-Type: application/json

{
  "version": "1.0",
  "templates": [...]
}
```

## Creating Custom Templates

### Template Structure

```python
from pr_agent.review_templates import (
    ReviewTemplate,
    CheckItem,
    TemplateCategory,
    CheckSeverity
)

# Create check items
check1 = CheckItem(
    check_id="CUSTOM-001",
    title="Custom Check",
    description="Description of what to check",
    severity=CheckSeverity.HIGH,
    required=True,
    guidance="How to perform this check",
    examples=["Example 1", "Example 2"]
)

# Create template
template = ReviewTemplate(
    template_id="my-custom-template",
    name="My Custom Template",
    description="Custom review template",
    category=TemplateCategory.SECURITY,
    check_items=[check1]
)

# Register template
manager = get_template_manager()
manager.register_template(template)
```

### Check Item Fields

- **check_id**: Unique identifier (e.g., "SEC-001")
- **title**: Short descriptive title
- **description**: Detailed description of the check
- **severity**: CRITICAL, HIGH, MEDIUM, LOW, INFO
- **required**: Whether this check is mandatory
- **guidance**: Instructions for performing the check
- **examples**: Code examples (good and bad)
- **metadata**: Additional custom data

### Template Categories

- **SECURITY**: Security-related checks
- **PERFORMANCE**: Performance optimization checks
- **ARCHITECTURE**: Architecture and design checks
- **STYLE**: Code style and formatting checks
- **GENERAL**: General purpose checks

## Best Practices

### Template Design

1. **Keep it Focused**: Each template should have a clear purpose
2. **Use Severity Appropriately**: Reserve CRITICAL for security/data loss issues
3. **Provide Guidance**: Include clear instructions for each check
4. **Add Examples**: Show both good and bad code examples
5. **Make it Actionable**: Checks should have clear pass/fail criteria

### Check Item Guidelines

```python
# Good check item
CheckItem(
    check_id="SEC-001",
    title="SQL Injection Prevention",
    description="Verify all SQL queries use parameterized statements",
    severity=CheckSeverity.CRITICAL,
    required=True,
    guidance="Use parameterized queries or ORM methods. Never concatenate user input into SQL strings.",
    examples=[
        "❌ cursor.execute(f'SELECT * FROM users WHERE id = {user_id}')",
        "✅ cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))"
    ]
)

# Bad check item (too vague)
CheckItem(
    check_id="GEN-001",
    title="Code Quality",
    description="Check code quality",
    severity=CheckSeverity.MEDIUM
)
```

### Review Workflow

1. **Select Template**: Choose appropriate template for the review type
2. **Apply Template**: Run the template against the code
3. **Review Findings**: Examine failed checks and findings
4. **Provide Feedback**: Add comments and suggestions
5. **Track Progress**: Monitor pass rates over time

## Integration Examples

### CI/CD Integration

```python
# In your CI pipeline
from pr_agent.review_templates import get_template_manager

def review_pull_request(pr_files):
    manager = get_template_manager()
    results = []
    
    for file_path in pr_files:
        with open(file_path) as f:
            content = f.read()
        
        # Apply security template
        result = manager.apply_template(
            template_id="builtin_security",
            file_path=file_path,
            content=content
        )
        
        results.append(result)
    
    # Fail if critical issues found
    critical_count = sum(
        r.get_summary()["critical_findings"]
        for r in results
    )
    
    if critical_count > 0:
        print(f"❌ Found {critical_count} critical security issues")
        exit(1)
    
    print("✅ Security review passed")
```

### Pre-commit Hook

```python
#!/usr/bin/env python3
# .git/hooks/pre-commit

import sys
from pr_agent.review_templates import get_template_manager

def main():
    manager = get_template_manager()
    
    # Get staged files
    staged_files = get_staged_python_files()
    
    for file_path in staged_files:
        with open(file_path) as f:
            content = f.read()
        
        result = manager.apply_template(
            template_id="builtin_style",
            file_path=file_path,
            content=content
        )
        
        if result.checks_failed > 0:
            print(f"❌ Style issues in {file_path}")
            for finding in result.findings:
                if finding["status"] == "failed":
                    print(f"  {finding['check_id']}: {finding['message']}")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## Storage

Templates are stored in `~/.pr-agent/review_templates/` by default. Each template is saved as a JSON file.

To use a custom storage location:

```python
from pathlib import Path
from pr_agent.review_templates import TemplateManager

manager = TemplateManager(storage_path=Path("/custom/path"))
```

## API Reference

### TemplateManager

- `get_template(template_id: str) -> Optional[ReviewTemplate]`
- `list_templates(category: Optional[TemplateCategory] = None, enabled_only: bool = False) -> List[ReviewTemplate]`
- `register_template(template: ReviewTemplate)`
- `unregister_template(template_id: str) -> bool`
- `apply_template(template_id: str, file_path: str, content: str, context: Optional[Dict] = None) -> ReviewResult`
- `export_templates(template_ids: Optional[List[str]] = None) -> Dict[str, Any]`
- `import_templates(data: Dict[str, Any], overwrite: bool = False)`

### ReviewTemplate

- `add_check(check: CheckItem)`
- `get_required_checks() -> List[CheckItem]`
- `get_checks_by_severity(severity: CheckSeverity) -> List[CheckItem]`
- `to_dict() -> Dict[str, Any]`
- `from_dict(data: Dict[str, Any]) -> ReviewTemplate`

### ReviewResult

- `add_finding(check_id: str, status: str, message: str, severity: CheckSeverity, line_number: Optional[int] = None, suggestion: Optional[str] = None)`
- `get_summary() -> Dict[str, Any]`

## Troubleshooting

### Template Not Found

```python
template = manager.get_template("my-template")
if not template:
    print("Template not found. Available templates:")
    for t in manager.list_templates():
        print(f"  - {t.template_id}: {t.name}")
```

### Import Conflicts

When importing templates, use `overwrite=True` to replace existing templates:

```python
manager.import_templates(data, overwrite=True)
```

### Custom Storage Path

If templates aren't persisting, check the storage path:

```python
manager = get_template_manager()
print(f"Storage path: {manager.storage_path}")
```

## See Also

- [Rules Engine](RULES_ENGINE.md) - Automated code analysis rules
- [Code Review Workflow](WORKFLOW.md) - Complete review pipeline
- [API Documentation](API.md) - Full API reference
