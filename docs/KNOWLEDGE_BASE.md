# Code Review Knowledge Base System

A comprehensive knowledge management system for code review best practices, patterns, anti-patterns, and case studies.

## Features

- **Knowledge Entry Management**: Create, read, update, and delete knowledge entries
- **Multi-Type Support**: Best practices, anti-patterns, code patterns, case studies, guidelines, FAQs
- **Advanced Search**: Full-text search with relevance scoring
- **Tag System**: Organize and filter entries by tags
- **Language Support**: Filter entries by programming language
- **Related Entries**: Automatic discovery of related knowledge
- **Popularity Tracking**: Track views and helpful votes
- **Import/Export**: Bulk import and export of knowledge entries
- **Persistence**: Automatic saving to disk

## Knowledge Types

### Best Practice
Recommended approaches and techniques for code review.

### Anti-Pattern
Common mistakes and practices to avoid.

### Code Pattern
Reusable code patterns and idioms.

### Case Study
Real-world examples and lessons learned.

### Guideline
General guidelines and principles.

### FAQ
Frequently asked questions and answers.

## Usage

### Creating Knowledge Entries

```python
from pr_agent.knowledge import KnowledgeBase, KnowledgeType, Severity

kb = KnowledgeBase()

# Add a best practice
entry = kb.add_entry(
    entry_id="bp-naming-001",
    title="Use Meaningful Variable Names",
    type=KnowledgeType.BEST_PRACTICE,
    content="""
    Always use descriptive variable names that clearly convey their purpose.
    Avoid single-letter names except for loop counters.
    """,
    tags=["naming", "readability", "python"],
    language="python",
    examples=[
        {
            "bad": "x = get_data()",
            "good": "user_profile = get_user_profile()"
        }
    ],
    references=[
        "https://pep8.org/#naming-conventions"
    ]
)
```

### Searching Knowledge

```python
# Simple search
results = kb.search("variable names")

for result in results:
    print(f"Score: {result.relevance_score}")
    print(f"Title: {result.entry.title}")
    print(f"Matched: {result.matched_fields}")

# Search with filters
results = kb.search(
    query="naming",
    type=KnowledgeType.BEST_PRACTICE,
    tags=["python"],
    language="python",
    limit=10
)
```

### Filtering Entries

```python
# Get by type
best_practices = kb.get_by_type(KnowledgeType.BEST_PRACTICE)

# Get by tags
python_entries = kb.get_by_tags(["python", "naming"])

# Get by language
python_entries = kb.get_by_language("python")
```

### Finding Related Entries

```python
# Get related entries
related = kb.get_related("bp-naming-001", limit=5)

for entry in related:
    print(f"- {entry.title}")
```

### Tracking Popularity

```python
# Mark entry as helpful
kb.mark_helpful("bp-naming-001")

# Get popular entries
popular = kb.get_popular(limit=10)

# Get recent entries
recent = kb.get_recent(limit=10)
```

### Statistics

```python
stats = kb.get_statistics()

print(f"Total entries: {stats['total_entries']}")
print(f"By type: {stats['by_type']}")
print(f"By language: {stats['by_language']}")
print(f"Total views: {stats['total_views']}")
```

### Import/Export

```python
# Export all data
data = kb.export_data()

# Import data
kb.import_data(data)
```

## REST API

### Create Entry

```http
POST /api/knowledge/entries
Content-Type: application/json

{
  "entry_id": "bp-001",
  "title": "Use Meaningful Variable Names",
  "type": "best_practice",
  "content": "Always use descriptive names...",
  "tags": ["naming", "python"],
  "language": "python",
  "examples": [
    {
      "bad": "x = 10",
      "good": "max_retries = 10"
    }
  ]
}
```

### Get Entry

```http
GET /api/knowledge/entries/{entry_id}
```

Response:
```json
{
  "id": "bp-001",
  "title": "Use Meaningful Variable Names",
  "type": "best_practice",
  "content": "Always use descriptive names...",
  "tags": ["naming", "python"],
  "language": "python",
  "view_count": 42,
  "helpful_count": 15,
  "created_at": "2024-01-15T10:00:00Z"
}
```

### Update Entry

```http
PUT /api/knowledge/entries/{entry_id}
Content-Type: application/json

{
  "title": "Updated Title",
  "tags": ["new-tag"]
}
```

### Delete Entry

```http
DELETE /api/knowledge/entries/{entry_id}
```

### Search

```http
GET /api/knowledge/search?query=naming&tags=python&language=python
```

Response:
```json
{
  "results": [
    {
      "entry": {
        "id": "bp-001",
        "title": "Use Meaningful Variable Names",
        "type": "best_practice"
      },
      "relevance_score": 15.5,
      "matched_fields": ["title", "tags"]
    }
  ]
}
```

### Get by Type

```http
GET /api/knowledge/type/{type}
```

### Get by Tags

```http
GET /api/knowledge/tags?tags=python,naming
```

### Get by Language

```http
GET /api/knowledge/language/{language}
```

### Get Related

```http
GET /api/knowledge/entries/{entry_id}/related?limit=5
```

### Mark Helpful

```http
POST /api/knowledge/entries/{entry_id}/helpful
```

### Get Popular

```http
GET /api/knowledge/popular?limit=10
```

### Get Recent

```http
GET /api/knowledge/recent?limit=10
```

### Get Statistics

```http
GET /api/knowledge/stats
```

Response:
```json
{
  "total_entries": 150,
  "by_type": {
    "best_practice": 50,
    "anti_pattern": 30,
    "code_pattern": 40,
    "case_study": 20,
    "guideline": 5,
    "faq": 5
  },
  "by_language": {
    "python": 60,
    "javascript": 40,
    "java": 30,
    "go": 20
  },
  "total_tags": 45,
  "total_views": 5000,
  "total_helpful": 800
}
```

### Import

```http
POST /api/knowledge/import
Content-Type: application/json

{
  "entries": [...]
}
```

### Export

```http
GET /api/knowledge/export
```

## Example Knowledge Entries

### Best Practice: Code Review Checklist

```python
kb.add_entry(
    entry_id="bp-checklist-001",
    title="Comprehensive Code Review Checklist",
    type=KnowledgeType.BEST_PRACTICE,
    content="""
    Use this checklist for thorough code reviews:
    
    1. Functionality
       - Does the code do what it's supposed to?
       - Are edge cases handled?
    
    2. Code Quality
       - Is the code readable?
       - Are names meaningful?
       - Is it properly structured?
    
    3. Testing
       - Are there adequate tests?
       - Do tests cover edge cases?
    
    4. Security
       - Are inputs validated?
       - Are there SQL injection risks?
       - Is sensitive data protected?
    
    5. Performance
       - Are there obvious performance issues?
       - Is caching used appropriately?
    """,
    tags=["checklist", "process", "general"],
    severity=Severity.INFO
)
```

### Anti-Pattern: God Object

```python
kb.add_entry(
    entry_id="ap-god-object-001",
    title="God Object Anti-Pattern",
    type=KnowledgeType.ANTI_PATTERN,
    content="""
    A God Object is a class that knows too much or does too much.
    It violates the Single Responsibility Principle.
    """,
    tags=["design", "architecture", "oop"],
    severity=Severity.HIGH,
    examples=[
        {
            "bad": """
class UserManager:
    def create_user(self): pass
    def send_email(self): pass
    def process_payment(self): pass
    def generate_report(self): pass
    def log_activity(self): pass
            """,
            "good": """
class UserService:
    def create_user(self): pass

class EmailService:
    def send_email(self): pass

class PaymentService:
    def process_payment(self): pass
            """
        }
    ],
    related_entries=["bp-srp-001", "bp-solid-001"]
)
```

### Code Pattern: Repository Pattern

```python
kb.add_entry(
    entry_id="cp-repository-001",
    title="Repository Pattern",
    type=KnowledgeType.CODE_PATTERN,
    content="""
    The Repository pattern mediates between the domain and data mapping layers.
    It provides a collection-like interface for accessing domain objects.
    """,
    tags=["pattern", "architecture", "database"],
    language="python",
    examples=[
        {
            "implementation": """
class UserRepository:
    def __init__(self, db):
        self.db = db
    
    def find_by_id(self, user_id):
        return self.db.query(User).filter_by(id=user_id).first()
    
    def find_all(self):
        return self.db.query(User).all()
    
    def save(self, user):
        self.db.add(user)
        self.db.commit()
            """
        }
    ],
    references=[
        "https://martinfowler.com/eaaCatalog/repository.html"
    ]
)
```

### Case Study: Performance Optimization

```python
kb.add_entry(
    entry_id="cs-perf-001",
    title="N+1 Query Problem Resolution",
    type=KnowledgeType.CASE_STUDY,
    content="""
    Problem: API endpoint was taking 5+ seconds to load user profiles.
    
    Investigation:
    - Profiled the code and found N+1 query problem
    - Each user's posts were loaded in separate queries
    
    Solution:
    - Used eager loading to fetch all data in one query
    - Reduced queries from 100+ to 2
    
    Result:
    - Response time reduced from 5s to 200ms
    - 96% improvement
    
    Lesson: Always profile before optimizing. The N+1 problem is common
    with ORMs and can be easily fixed with eager loading.
    """,
    tags=["performance", "database", "optimization"],
    language="python",
    severity=Severity.HIGH,
    examples=[
        {
            "before": """
users = User.query.all()
for user in users:
    posts = Post.query.filter_by(user_id=user.id).all()
            """,
            "after": """
users = User.query.options(joinedload(User.posts)).all()
            """
        }
    ]
)
```

## Integration Examples

### With Quality Scoring

```python
from pr_agent.knowledge import KnowledgeBase
from pr_agent.quality_scoring import QualityScorer

kb = KnowledgeBase()
scorer = QualityScorer()

# Get improvement suggestions
suggestions = scorer.get_improvement_suggestions("reviewer-123")

# Find relevant knowledge entries
for suggestion in suggestions:
    if "coverage" in suggestion.lower():
        entries = kb.search("code coverage", type=KnowledgeType.BEST_PRACTICE)
        # Show relevant knowledge to reviewer
```

### With Review Workflow

```python
from pr_agent.knowledge import KnowledgeBase
from pr_agent.workflow import ReviewPipeline

kb = KnowledgeBase()
pipeline = ReviewPipeline()

# Run review
result = await pipeline.run(files)

# For each issue, suggest relevant knowledge
for issue in result.issues:
    related = kb.search(
        issue.description,
        tags=[issue.category],
        limit=3
    )
    # Attach knowledge references to issue
```

## Best Practices

1. **Consistent Tagging**: Use a standard set of tags across entries
2. **Rich Examples**: Include both good and bad examples
3. **Keep Updated**: Regularly review and update entries
4. **Link Related**: Connect related entries for better discovery
5. **Add References**: Include external references for deeper learning
6. **Track Popularity**: Use view and helpful counts to identify valuable content
7. **Language Specific**: Tag entries with programming languages when applicable

## Configuration

Knowledge base settings in `configuration.toml`:

```toml
[knowledge]
# Storage path
storage_path = ".pr_agent/knowledge"

# Search settings
max_search_results = 50
min_relevance_score = 1.0

# Popularity settings
popular_threshold = 10  # Minimum helpful votes
recent_days = 30  # Days to consider for "recent"
```

## Troubleshooting

**Search returns no results:**
- Check if entries exist with `kb.get_statistics()`
- Verify search query matches entry content
- Try broader search terms

**Related entries not showing:**
- Ensure entries have common tags
- Add explicit related_entries links
- Check if entries exist in the same category

**Import fails:**
- Verify JSON format matches export format
- Check for duplicate entry IDs
- Ensure all required fields are present
