# Code Review Bot System

An intelligent automated code review system with learning capabilities, multi-capability support, and customizable rules.

## Features

- **Multi-Capability Review**: Syntax, style, security, performance, best practices, documentation
- **Intelligent Comments**: Confidence-scored suggestions with explanations
- **Learning System**: Improves accuracy based on feedback
- **Custom Checkers**: Add domain-specific review rules
- **Configurable Thresholds**: Control comment confidence and quantity
- **Review Modes**: Full, quick, focused, and learning modes
- **Persistent Learning**: Learning data saved and loaded across sessions

## Bot Capabilities

### Syntax Check
- Trailing whitespace detection
- Mixed indentation detection
- Basic syntax validation

### Style Check
- Line length enforcement
- Code formatting consistency
- Naming convention checks

### Security Scan
- Hardcoded secrets detection (passwords, API keys)
- SQL injection patterns
- XSS vulnerabilities
- Insecure function usage

### Performance Analysis
- Inefficient loop patterns
- String concatenation in loops
- N+1 query detection
- Resource leak detection

### Best Practices
- Bare except clause detection
- Magic number usage
- Code duplication
- SOLID principle violations

### Documentation Check
- Missing docstrings
- Incomplete documentation
- Outdated comments

## Usage

### Creating a Bot

```python
from pr_agent.bot import ReviewerBot, BotConfig, BotCapability

config = BotConfig(
    bot_id="my-bot",
    name="My Review Bot",
    capabilities=[
        BotCapability.SYNTAX_CHECK,
        BotCapability.STYLE_CHECK,
        BotCapability.SECURITY_SCAN,
        BotCapability.BEST_PRACTICES
    ],
    confidence_threshold=0.7,
    max_comments_per_file=10,
    learning_enabled=True
)

bot = ReviewerBot(config)
```

### Reviewing Code

```python
from pr_agent.bot import ReviewMode

# Review a pull request
files = {
    "app.py": """
def process_user(user_id):
    password = "hardcoded123"  # Security issue
    user = get_user(user_id)
    return user
""",
    "utils.py": """
def calculate():  # Missing docstring
    x = 1  
    return x
"""
}

result = bot.review_pr(
    pr_id="PR-123",
    files=files,
    mode=ReviewMode.FULL
)

print(f"Review ID: {result.review_id}")
print(f"Issues found: {result.issues_found}")
print(f"Suggestions: {result.suggestions_made}")
print(f"Summary: {result.summary}")

for comment in result.comments:
    print(f"\n{comment.file_path}:{comment.line_number}")
    print(f"  [{comment.comment_type.value}] {comment.message}")
    if comment.suggestion:
        print(f"  Suggestion: {comment.suggestion}")
    print(f"  Confidence: {comment.confidence:.2f}")
```

### Review Modes

```python
# Full comprehensive review
result = bot.review_pr(pr_id, files, ReviewMode.FULL)

# Quick scan for critical issues only
result = bot.review_pr(pr_id, files, ReviewMode.QUICK)

# Focused review on specific areas
result = bot.review_pr(pr_id, files, ReviewMode.FOCUSED)

# Learning mode with detailed explanations
result = bot.review_pr(pr_id, files, ReviewMode.LEARNING)
```

### Custom Checkers

```python
from pr_agent.bot import BotComment, CommentType
import uuid

def check_todo_comments(file_path: str, content: str):
    """Custom checker for TODO comments."""
    comments = []
    lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        if 'TODO' in line:
            comments.append(BotComment(
                comment_id=str(uuid.uuid4()),
                file_path=file_path,
                line_number=i,
                comment_type=CommentType.INFO,
                message="TODO comment found - consider creating a ticket",
                confidence=0.9,
                rule_id="custom_todo_check"
            ))
    
    return comments

# Register custom checker
bot.add_custom_checker("todo_checker", check_todo_comments)

# Remove custom checker
bot.remove_custom_checker("todo_checker")
```

### Learning from Feedback

```python
# Review code
result = bot.review_pr("PR-123", files)

# User provides feedback on comments
for comment in result.comments:
    # Positive feedback (comment was helpful)
    bot.provide_feedback(comment.comment_id, positive=True)
    
    # Negative feedback (comment was not helpful)
    bot.provide_feedback(comment.comment_id, positive=False)

# Check learning statistics
stats = bot.get_learning_stats()
print(f"Total rules: {stats['total_rules']}")
print(f"Total feedback: {stats['total_feedback']}")
print(f"Average accuracy: {stats['average_accuracy']:.2%}")

for rule in stats['rules']:
    print(f"\n{rule['rule_id']}")
    print(f"  Feedback: {rule['feedback_count']}")
    print(f"  Accuracy: {rule['accuracy']:.2%}")
```

### Configuration

```python
# Adjust confidence threshold
bot.config.confidence_threshold = 0.8  # Only show high-confidence comments

# Limit comments per file
bot.config.max_comments_per_file = 5

# Enable/disable learning
bot.config.learning_enabled = True

# Export configuration
config_dict = bot.export_config()
```

## REST API

### Review PR

```http
POST /api/bot/review
Content-Type: application/json

{
  "bot_id": "default",
  "pr_id": "PR-123",
  "files": {
    "app.py": "def foo():\n    pass\n"
  },
  "mode": "full"
}
```

Response:
```json
{
  "review_id": "rev-456",
  "pr_id": "PR-123",
  "bot_id": "default",
  "mode": "full",
  "comments": [
    {
      "comment_id": "c1",
      "file_path": "app.py",
      "line_number": 1,
      "comment_type": "suggestion",
      "message": "Consider adding a docstring",
      "suggestion": null,
      "confidence": 0.7,
      "rule_id": "doc_missing_docstring"
    }
  ],
  "summary": "Found 0 issues and 1 suggestions.\n- 1 suggestions",
  "issues_found": 0,
  "suggestions_made": 1,
  "execution_time": 0.05
}
```

### Get Review

```http
GET /api/bot/reviews/{review_id}
```

### List Reviews

```http
GET /api/bot/reviews?bot_id=default&pr_id=PR-123
```

### Submit Feedback

```http
POST /api/bot/feedback
Content-Type: application/json

{
  "bot_id": "default",
  "comment_id": "c1",
  "positive": true
}
```

### Get Learning Stats

```http
GET /api/bot/learning-stats?bot_id=default
```

Response:
```json
{
  "total_rules": 10,
  "total_feedback": 150,
  "average_accuracy": 0.85,
  "rules": [
    {
      "rule_id": "security_hardcoded_secret",
      "feedback_count": 25,
      "accuracy": 0.92,
      "last_updated": "2024-01-15T10:00:00Z"
    }
  ]
}
```

### Get Bot Config

```http
GET /api/bot/config?bot_id=default
```

Response:
```json
{
  "bot_id": "default",
  "name": "PR Agent Bot default",
  "capabilities": [
    "syntax_check",
    "style_check",
    "security_scan",
    "performance_analysis",
    "best_practices",
    "documentation_check"
  ],
  "enabled": true,
  "auto_comment": true,
  "confidence_threshold": 0.7,
  "max_comments_per_file": 10,
  "learning_enabled": true
}
```

### Update Bot Config

```http
PUT /api/bot/config
Content-Type: application/json

{
  "bot_id": "default",
  "confidence_threshold": 0.8,
  "max_comments_per_file": 5,
  "learning_enabled": true
}
```

## Comment Types

- **SUGGESTION**: Improvement suggestions
- **WARNING**: Potential issues that should be addressed
- **ERROR**: Critical issues that must be fixed
- **INFO**: Informational comments
- **QUESTION**: Questions for clarification

## Built-in Rules

### Syntax Rules
- `syntax_trailing_whitespace`: Detects trailing whitespace
- `syntax_mixed_indentation`: Detects mixed tabs and spaces

### Style Rules
- `style_line_length`: Enforces maximum line length (120 chars)

### Security Rules
- `security_hardcoded_secret`: Detects hardcoded passwords, API keys, secrets

### Performance Rules
- `performance_string_concat`: Detects inefficient string concatenation in loops

### Best Practice Rules
- `best_practice_bare_except`: Detects bare except clauses

### Documentation Rules
- `doc_missing_docstring`: Detects functions without docstrings

## Integration Examples

### With Workflow Engine

```python
from pr_agent.workflow_engine import WorkflowEngine, StepType
from pr_agent.bot import ReviewerBot, BotConfig, BotCapability

engine = WorkflowEngine()
bot = ReviewerBot(BotConfig(
    bot_id="workflow-bot",
    name="Workflow Bot",
    capabilities=[BotCapability.SECURITY_SCAN, BotCapability.BEST_PRACTICES]
))

def bot_review_handler(step, context):
    """Bot review step handler."""
    files = context.get("files", {})
    pr_id = context.get("pr_id")
    
    result = bot.review_pr(pr_id, files)
    
    return {
        "bot_review_completed": True,
        "issues_found": result.issues_found,
        "suggestions_made": result.suggestions_made,
        "bot_comments": [c.to_dict() for c in result.comments]
    }

engine.register_step_handler(StepType.REVIEW, bot_review_handler)
```

### With Notification System

```python
from pr_agent.notifications import NotificationSystem

def review_with_notifications(bot, pr_id, files):
    """Review and send notifications."""
    result = bot.review_pr(pr_id, files)
    
    if result.issues_found > 0:
        notifier = NotificationSystem()
        notifier.send(
            message=f"Bot found {result.issues_found} issues in {pr_id}",
            channels=["slack"],
            recipients=["dev-team"]
        )
    
    return result
```

### With Quality Scoring

```python
from pr_agent.quality_scoring import QualityScorer

def review_and_score(bot, pr_id, files):
    """Review and calculate quality score."""
    result = bot.review_pr(pr_id, files)
    
    scorer = QualityScorer()
    score = scorer.calculate_review_score(result.review_id)
    
    return {
        "review": result,
        "quality_score": score
    }
```

## Best Practices

1. **Start Conservative**: Begin with high confidence threshold (0.8+)
2. **Collect Feedback**: Actively collect user feedback to improve accuracy
3. **Custom Rules**: Add domain-specific rules for your codebase
4. **Review Modes**: Use appropriate mode for context (quick for CI, full for PR)
5. **Limit Comments**: Avoid overwhelming developers with too many comments
6. **Monitor Learning**: Track learning stats to ensure improvement
7. **Regular Updates**: Update bot configuration based on team feedback
8. **Combine Capabilities**: Enable multiple capabilities for comprehensive review

## Configuration

Bot settings in `configuration.toml`:

```toml
[reviewer_bot]
# Default bot ID
default_bot_id = "default"

# Storage path for learning data
storage_path = ".pr_agent/bot_data"

# Default confidence threshold
confidence_threshold = 0.7

# Maximum comments per file
max_comments_per_file = 10

# Enable learning by default
learning_enabled = true

# Auto-comment on PRs
auto_comment = true

# Default capabilities
capabilities = [
    "syntax_check",
    "style_check",
    "security_scan",
    "best_practices"
]
```

## Troubleshooting

**Too many comments:**
- Increase `confidence_threshold`
- Reduce `max_comments_per_file`
- Disable less critical capabilities

**Missing issues:**
- Lower `confidence_threshold`
- Enable more capabilities
- Add custom checkers for specific patterns

**Low accuracy:**
- Collect more feedback
- Review learning stats
- Adjust rule confidence based on feedback

**Learning not improving:**
- Ensure `learning_enabled` is true
- Check that feedback is being provided
- Verify learning data is persisting to disk
