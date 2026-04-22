# Code Review Automation Scheduler

The scheduler system provides automated code review job management with support for cron-based scheduling, event-driven triggers, and priority-based execution.

## Features

- **Priority-based job queue**: CRITICAL > HIGH > NORMAL > LOW
- **Cron scheduling**: Schedule reviews at specific times
- **Event triggers**: Automatically trigger reviews on PR/commit events
- **Concurrent execution**: Configurable worker pool
- **State persistence**: Jobs, schedules, and triggers survive restarts
- **Branch filtering**: Target specific branches
- **Job management**: Submit, cancel, list, and query jobs

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     ReviewScheduler                          │
├─────────────────────────────────────────────────────────────┤
│  Priority Queue          Worker Pool         State Storage  │
│  ┌──────────┐          ┌──────────┐         ┌──────────┐   │
│  │ CRITICAL │          │ Worker 1 │         │ JSON     │   │
│  │ HIGH     │  ──────> │ Worker 2 │  ────>  │ State    │   │
│  │ NORMAL   │          │ Worker 3 │         │ File     │   │
│  │ LOW      │          └──────────┘         └──────────┘   │
│  └──────────┘                                               │
│                                                              │
│  Schedules (Cron)        Triggers (Events)                  │
│  ┌──────────────┐       ┌──────────────┐                   │
│  │ Daily 9am    │       │ PR Created   │                   │
│  │ Weekly Mon   │       │ Commit Push  │                   │
│  └──────────────┘       └──────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### ReviewJob

Represents a single code review job.

```python
@dataclass
class ReviewJob:
    job_id: str
    repository: str
    pr_number: Optional[int]
    branch: Optional[str]
    commit_hash: Optional[str]
    trigger_type: TriggerType
    priority: ReviewPriority
    status: ReviewStatus
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    metadata: Optional[Dict[str, Any]]
```

**Job Statuses:**
- `PENDING`: Job created but not queued
- `QUEUED`: In priority queue waiting for worker
- `RUNNING`: Being executed by worker
- `COMPLETED`: Successfully finished
- `FAILED`: Execution failed
- `CANCELLED`: Manually cancelled

### ReviewScheduler

Main scheduler class managing jobs, schedules, and triggers.

```python
scheduler = ReviewScheduler(
    storage_path=Path("/path/to/storage"),
    max_concurrent=3,
    job_timeout=3600
)

# Set review executor
scheduler.set_review_executor(my_review_function)

# Start workers
scheduler.start()
```

## Usage

### 1. Manual Job Submission

```python
from pr_agent.scheduler import ReviewScheduler, ReviewPriority, TriggerType

scheduler = ReviewScheduler()
scheduler.set_review_executor(lambda job: {"status": "success"})
scheduler.start()

# Submit a job
job = scheduler.submit_job(
    repository="owner/repo",
    pr_number=123,
    priority=ReviewPriority.HIGH,
    trigger_type=TriggerType.MANUAL
)

print(f"Job {job.job_id} submitted with priority {job.priority.name}")
```

### 2. Cron Scheduling

Schedule reviews to run at specific times using cron expressions.

```python
# Daily at 9am
scheduler.add_schedule(
    schedule_id="daily-review",
    repository="owner/repo",
    cron_expression="0 9 * * *",
    priority=ReviewPriority.NORMAL,
    branches=["main", "develop"]
)

# Every Monday at 10am
scheduler.add_schedule(
    schedule_id="weekly-review",
    repository="owner/repo",
    cron_expression="0 10 * * 1",
    priority=ReviewPriority.LOW
)

# Every 6 hours
scheduler.add_schedule(
    schedule_id="frequent-review",
    repository="owner/repo",
    cron_expression="0 */6 * * *",
    priority=ReviewPriority.NORMAL
)
```

**Cron Expression Format:**
```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6) (Sunday to Saturday)
│ │ │ │ │
* * * * *
```

### 3. Event Triggers

Automatically trigger reviews on repository events.

```python
# Trigger on PR creation
scheduler.add_trigger(
    trigger_id="pr-created",
    repository="owner/repo",
    trigger_type=TriggerType.PR_CREATED,
    priority=ReviewPriority.HIGH
)

# Trigger on commits to main branch
scheduler.add_trigger(
    trigger_id="main-commits",
    repository="owner/repo",
    trigger_type=TriggerType.COMMIT_PUSHED,
    priority=ReviewPriority.NORMAL,
    filters={"branches": ["main"]}
)

# Trigger on PR updates
scheduler.add_trigger(
    trigger_id="pr-updated",
    repository="owner/repo",
    trigger_type=TriggerType.PR_UPDATED,
    priority=ReviewPriority.NORMAL
)

# Handle an event
jobs = scheduler.handle_event(
    event_type=TriggerType.PR_CREATED,
    repository="owner/repo",
    pr_number=123,
    branch="feature/new-feature"
)
```

**Trigger Types:**
- `MANUAL`: Manually submitted
- `SCHEDULED`: Triggered by cron schedule
- `PR_CREATED`: New pull request
- `PR_UPDATED`: Pull request updated
- `COMMIT_PUSHED`: New commit pushed
- `BRANCH_CREATED`: New branch created

### 4. Job Management

```python
# Get job status
job = scheduler.get_job("job_id")
print(f"Status: {job.status.name}")

# List all jobs
jobs = scheduler.list_jobs()

# List jobs with filters
pending_jobs = scheduler.list_jobs(
    status=ReviewStatus.QUEUED,
    repository="owner/repo"
)

# Cancel a job
if scheduler.cancel_job("job_id"):
    print("Job cancelled")
```

### 5. Schedule Management

```python
# List schedules
schedules = scheduler.list_schedules()

# Remove schedule
scheduler.remove_schedule("schedule_id")
```

### 6. Trigger Management

```python
# List triggers
triggers = scheduler.list_triggers()

# Remove trigger
scheduler.remove_trigger("trigger_id")
```

## REST API

The scheduler is integrated into the web platform with REST endpoints.

### Submit Job

```http
POST /api/scheduler/jobs
Content-Type: application/json

{
  "repository": "owner/repo",
  "pr_number": 123,
  "priority": "HIGH",
  "trigger_type": "MANUAL"
}
```

### Get Job

```http
GET /api/scheduler/jobs/{job_id}
```

### List Jobs

```http
GET /api/scheduler/jobs?status=QUEUED&repository=owner/repo
```

### Cancel Job

```http
DELETE /api/scheduler/jobs/{job_id}
```

### Add Schedule

```http
POST /api/scheduler/schedules
Content-Type: application/json

{
  "schedule_id": "daily-review",
  "repository": "owner/repo",
  "cron_expression": "0 9 * * *",
  "priority": "NORMAL",
  "branches": ["main"]
}
```

### List Schedules

```http
GET /api/scheduler/schedules
```

### Remove Schedule

```http
DELETE /api/scheduler/schedules/{schedule_id}
```

### Add Trigger

```http
POST /api/scheduler/triggers
Content-Type: application/json

{
  "trigger_id": "pr-created",
  "repository": "owner/repo",
  "trigger_type": "PR_CREATED",
  "priority": "HIGH",
  "filters": {"branches": ["main"]}
}
```

### List Triggers

```http
GET /api/scheduler/triggers
```

### Remove Trigger

```http
DELETE /api/scheduler/triggers/{trigger_id}
```

## Configuration

Add to `configuration.toml`:

```toml
[scheduler]
# Storage path for scheduler state
storage_path = "~/.pr_agent/scheduler"

# Maximum concurrent review jobs
max_concurrent = 3

# Job timeout in seconds
job_timeout = 3600

# Enable scheduler on startup
auto_start = true
```

## State Persistence

The scheduler automatically saves state to disk:

```
~/.pr_agent/scheduler/
├── state.json          # Schedules, triggers, job history
└── jobs/
    ├── job_1.json
    ├── job_2.json
    └── ...
```

State is loaded on startup, so schedules and triggers survive restarts.

## Priority System

Jobs are executed in priority order:

1. **CRITICAL**: Urgent issues, security fixes
2. **HIGH**: Important PRs, main branch commits
3. **NORMAL**: Regular PRs and reviews
4. **LOW**: Background tasks, scheduled reviews

Within the same priority, jobs are FIFO (first in, first out).

## Worker Pool

The scheduler uses a configurable worker pool:

```python
scheduler = ReviewScheduler(max_concurrent=5)
```

- Each worker runs in a separate thread
- Workers pull jobs from the priority queue
- Failed jobs are marked as FAILED with error details
- Completed jobs are moved to history

## Review Executor

The review executor is a callback function that performs the actual review:

```python
def my_review_executor(job: ReviewJob) -> Dict[str, Any]:
    """
    Execute a review job.
    
    Args:
        job: The review job to execute
        
    Returns:
        Review result dictionary
    """
    # Perform review
    result = {
        "status": "success",
        "issues_found": 5,
        "suggestions": ["Fix typo", "Add tests"]
    }
    return result

scheduler.set_review_executor(my_review_executor)
```

## Error Handling

- Jobs that fail are marked as `FAILED` with error details
- Failed jobs remain in history for debugging
- Workers continue processing other jobs after failures
- Job timeout prevents hung reviews

## Best Practices

1. **Set appropriate priorities**: Use CRITICAL sparingly, NORMAL for most reviews
2. **Configure worker pool**: Match `max_concurrent` to available resources
3. **Use branch filters**: Target specific branches to reduce noise
4. **Monitor job history**: Check for patterns in failures
5. **Set reasonable timeouts**: Balance thoroughness with responsiveness
6. **Clean up old jobs**: Periodically archive completed jobs

## Examples

### Example 1: PR Review Automation

```python
# Trigger high-priority review on PR creation
scheduler.add_trigger(
    trigger_id="pr-review",
    repository="owner/repo",
    trigger_type=TriggerType.PR_CREATED,
    priority=ReviewPriority.HIGH
)

# When PR is created
jobs = scheduler.handle_event(
    event_type=TriggerType.PR_CREATED,
    repository="owner/repo",
    pr_number=123
)
```

### Example 2: Scheduled Security Scans

```python
# Daily security scan at 2am
scheduler.add_schedule(
    schedule_id="security-scan",
    repository="owner/repo",
    cron_expression="0 2 * * *",
    priority=ReviewPriority.CRITICAL,
    branches=["main", "production"]
)
```

### Example 3: Branch-Specific Reviews

```python
# High priority for main branch
scheduler.add_trigger(
    trigger_id="main-commits",
    repository="owner/repo",
    trigger_type=TriggerType.COMMIT_PUSHED,
    priority=ReviewPriority.HIGH,
    filters={"branches": ["main"]}
)

# Normal priority for feature branches
scheduler.add_trigger(
    trigger_id="feature-commits",
    repository="owner/repo",
    trigger_type=TriggerType.COMMIT_PUSHED,
    priority=ReviewPriority.NORMAL,
    filters={"branches": ["feature/*"]}
)
```

## Troubleshooting

### Jobs stuck in QUEUED

- Check if workers are started: `scheduler.start()`
- Verify review executor is set: `scheduler.set_review_executor(func)`
- Check worker pool size: increase `max_concurrent`

### Jobs timing out

- Increase `job_timeout` parameter
- Optimize review executor performance
- Check for blocking operations in executor

### State not persisting

- Verify `storage_path` is writable
- Check disk space
- Review file permissions

### High memory usage

- Reduce `max_concurrent` workers
- Clean up old job history
- Optimize review executor

## See Also

- [Workflow Documentation](WORKFLOW.md) - Review pipeline stages
- [Impact Analysis](IMPACT_ANALYSIS.md) - Change impact analysis
- [Trends Analysis](TRENDS.md) - Quality trends tracking
