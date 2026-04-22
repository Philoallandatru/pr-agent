# Code Review Assignment System

Automatically assigns reviewers to pull requests based on expertise, workload, and availability.

## Features

- **Reviewer Management**: Register reviewers with skills, file patterns, and availability
- **Multiple Assignment Strategies**:
  - Load Balanced: Assigns to reviewers with lowest workload
  - Round Robin: Rotates through available reviewers
  - Expertise Based: Matches reviewers to file types
  - Random: Random selection
- **Workload Tracking**: Monitors current review load per reviewer
- **Skill Matching**: Assigns based on required skills
- **File Pattern Matching**: Supports glob patterns (e.g., `**/*.py`, `src/**/*.js`)
- **Status Management**: Track reviewer availability (available, busy, unavailable, on leave)
- **Assignment History**: Complete audit trail of all assignments
- **Statistics**: Per-reviewer performance metrics

## Usage

### Python API

```python
from pr_agent.assignment import (
    AssignmentEngine,
    Reviewer,
    AssignmentStrategy,
    ReviewerStatus
)

# Initialize engine
engine = AssignmentEngine()

# Register reviewers
alice = Reviewer(
    reviewer_id="alice",
    name="Alice Smith",
    email="alice@example.com",
    skills=["python", "backend"],
    file_patterns=["**/*.py", "backend/**/*"],
    max_reviews=5,
    priority=2
)
engine.register_reviewer(alice)

bob = Reviewer(
    reviewer_id="bob",
    name="Bob Jones",
    email="bob@example.com",
    skills=["javascript", "frontend"],
    file_patterns=["**/*.js", "**/*.jsx", "frontend/**/*"],
    max_reviews=3
)
engine.register_reviewer(bob)

# Assign reviewers to a PR
assignments = engine.assign_reviewers(
    pull_request_id="pr-123",
    repository="org/repo",
    files=["backend/api.py", "backend/models.py"],
    num_reviewers=2,
    strategy=AssignmentStrategy.EXPERTISE_BASED,
    required_skills=["python"]
)

for assignment in assignments:
    print(f"Assigned {assignment.reviewer_id} to PR {assignment.pull_request_id}")

# Complete an assignment
engine.complete_assignment(assignments[0].assignment_id)

# Get reviewer stats
stats = engine.get_reviewer_stats("alice")
print(f"Alice has {stats['current_reviews']} active reviews")
print(f"Total completed: {stats['total_completed']}")
```

### REST API

#### Register Reviewer

```bash
POST /api/reviewers
Content-Type: application/json

{
  "reviewer_id": "alice",
  "name": "Alice Smith",
  "email": "alice@example.com",
  "skills": ["python", "backend"],
  "file_patterns": ["**/*.py", "backend/**/*"],
  "max_reviews": 5,
  "priority": 2
}
```

#### List Reviewers

```bash
GET /api/reviewers?available_only=true
```

#### Get Reviewer

```bash
GET /api/reviewers/alice
```

#### Update Reviewer Status

```bash
PUT /api/reviewers/alice/status?status=busy
```

#### Assign Reviewers

```bash
POST /api/assignments
Content-Type: application/json

{
  "pull_request_id": "pr-123",
  "repository": "org/repo",
  "files": ["backend/api.py", "backend/models.py"],
  "num_reviewers": 2,
  "strategy": "expertise_based",
  "required_skills": ["python"]
}
```

Response:
```json
{
  "message": "Reviewers assigned successfully",
  "assignments": [
    {
      "assignment_id": "pr-123_alice",
      "pull_request_id": "pr-123",
      "repository": "org/repo",
      "reviewer_id": "alice",
      "assigned_at": "2024-01-15T10:30:00Z",
      "files": ["backend/api.py", "backend/models.py"],
      "strategy": "expertise_based",
      "completed": false
    }
  ],
  "count": 1
}
```

#### List Assignments

```bash
# All active assignments
GET /api/assignments

# Assignments for a specific reviewer
GET /api/assignments?reviewer_id=alice

# Completed assignments
GET /api/assignments?completed=true

# Assignments for a repository
GET /api/assignments?repository=org/repo
```

#### Get Assignment

```bash
GET /api/assignments/pr-123_alice
```

#### Complete Assignment

```bash
POST /api/assignments/pr-123_alice/complete
```

#### Get Reviewer Statistics

```bash
GET /api/reviewers/alice/stats
```

Response:
```json
{
  "reviewer_id": "alice",
  "name": "Alice Smith",
  "status": "available",
  "current_reviews": 2,
  "max_reviews": 5,
  "total_completed": 47,
  "skills": ["python", "backend"],
  "file_patterns": ["**/*.py", "backend/**/*"]
}
```

## Assignment Strategies

### Load Balanced (Default)

Assigns to reviewers with the lowest current workload. Considers:
- Current number of active reviews
- Reviewer priority (higher priority = more likely to be assigned)

Best for: Distributing work evenly across the team

### Round Robin

Rotates through available reviewers in order. Maintains separate rotation per repository.

Best for: Fair distribution when all reviewers have equal expertise

### Expertise Based

Scores reviewers based on file pattern matches and assigns to those with highest scores.

Best for: Matching reviewers to their areas of expertise

### Random

Randomly selects from available reviewers.

Best for: Simple random distribution

## File Pattern Matching

Supports glob patterns with `**` for recursive matching:

- `**/*.py` - All Python files at any depth
- `src/**/*.js` - All JavaScript files under src/
- `*.md` - Markdown files in root only
- `tests/**/*` - All files under tests/

## Reviewer Status

- `available` - Ready for new assignments
- `busy` - Temporarily unavailable but can be assigned if needed
- `unavailable` - Should not receive new assignments
- `on_leave` - Out of office, do not assign

## Configuration

The assignment engine stores state in `~/.pr-agent/assignments/state.json` by default.

To use a custom storage location:

```python
engine = AssignmentEngine(storage_path="/path/to/storage")
```

## Integration with Bitbucket Server Polling

The assignment system can be integrated with the Bitbucket Server polling service to automatically assign reviewers when new PRs are created:

```python
from pr_agent.servers.bitbucket_server_polling import BitbucketServerPolling
from pr_agent.assignment import get_assignment_engine

# In your polling callback
def on_pr_created(pr_data):
    engine = get_assignment_engine()
    
    assignments = engine.assign_reviewers(
        pull_request_id=pr_data["id"],
        repository=pr_data["repository"],
        files=pr_data["changed_files"],
        num_reviewers=2,
        strategy=AssignmentStrategy.LOAD_BALANCED
    )
    
    # Notify assigned reviewers
    for assignment in assignments:
        notify_reviewer(assignment)
```

## Best Practices

1. **Set Realistic Max Reviews**: Don't overload reviewers. 3-5 concurrent reviews is typical.

2. **Use Priority Wisely**: Higher priority reviewers will be assigned more often in load-balanced mode.

3. **Keep File Patterns Specific**: More specific patterns lead to better expertise matching.

4. **Update Status Regularly**: Keep reviewer status current to avoid assigning to unavailable people.

5. **Track Completion**: Always mark assignments as completed to keep workload counts accurate.

6. **Monitor Statistics**: Use reviewer stats to identify bottlenecks and balance workload.

7. **Combine Strategies**: Use expertise-based for specialized files, load-balanced for general code.

## Troubleshooting

### No Available Reviewers

If you get "No available reviewers" error:
- Check that reviewers are registered
- Verify reviewer status is `available`
- Ensure reviewers haven't reached `max_reviews`
- Check that file patterns match the files being reviewed

### No Reviewers Match Requirements

If you get "No reviewers match the requirements" error:
- Verify required skills are spelled correctly
- Check that file patterns match the files
- Ensure at least one reviewer has the required skills
- Try removing skill requirements or using broader file patterns

### Assignments Not Completing

If workload counts seem wrong:
- Ensure you're calling `complete_assignment()` when reviews finish
- Check for duplicate assignments
- Verify assignment IDs are correct
- Review the assignment history

## API Reference

### Reviewer Class

```python
@dataclass
class Reviewer:
    reviewer_id: str          # Unique identifier
    name: str                 # Display name
    email: str                # Email address
    skills: List[str]         # List of skills (e.g., ["python", "backend"])
    file_patterns: List[str]  # Glob patterns (e.g., ["**/*.py"])
    max_reviews: int          # Maximum concurrent reviews (default: 5)
    current_reviews: int      # Current active reviews (default: 0)
    status: ReviewerStatus    # Availability status (default: AVAILABLE)
    priority: int             # Assignment priority (default: 1)
    metadata: Dict[str, Any]  # Custom metadata (default: {})
```

### Assignment Class

```python
@dataclass
class Assignment:
    assignment_id: str           # Unique identifier
    pull_request_id: str         # PR identifier
    repository: str              # Repository name
    reviewer_id: str             # Assigned reviewer
    assigned_at: datetime        # Assignment timestamp
    files: List[str]             # Files to review
    strategy: AssignmentStrategy # Strategy used
    completed: bool              # Completion status (default: False)
    completed_at: Optional[datetime]  # Completion timestamp
    metadata: Dict[str, Any]     # Custom metadata (default: {})
```

### AssignmentEngine Methods

- `register_reviewer(reviewer: Reviewer)` - Register a new reviewer
- `unregister_reviewer(reviewer_id: str) -> bool` - Remove a reviewer
- `get_reviewer(reviewer_id: str) -> Optional[Reviewer]` - Get reviewer by ID
- `list_reviewers(status=None, available_only=False) -> List[Reviewer]` - List reviewers
- `update_reviewer_status(reviewer_id: str, status: ReviewerStatus) -> bool` - Update status
- `assign_reviewers(...)` - Assign reviewers to a PR
- `complete_assignment(assignment_id: str) -> bool` - Mark assignment complete
- `get_assignment(assignment_id: str) -> Optional[Assignment]` - Get assignment by ID
- `list_assignments(...)` - List assignments with filters
- `get_reviewer_stats(reviewer_id: str) -> Dict[str, Any]` - Get reviewer statistics
