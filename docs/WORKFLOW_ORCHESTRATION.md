# Workflow Orchestration System

A flexible workflow engine for orchestrating complex code review processes with conditional logic, parallel execution, and dependency management.

## Features

- **Custom Workflows**: Define multi-step review workflows
- **Step Dependencies**: Control execution order with dependencies
- **Conditional Execution**: Execute steps based on runtime conditions
- **Parallel Execution**: Run independent steps in parallel
- **Step Handlers**: Pluggable handlers for different step types
- **Context Propagation**: Share data between workflow steps
- **Execution Tracking**: Monitor workflow progress and status
- **Persistence**: Workflows saved to disk and loaded on startup
- **Retry Logic**: Configure retry behavior for failed steps
- **Cancellation**: Cancel running workflows

## Workflow Components

### Step Types

- **REVIEW**: Code review step
- **APPROVAL**: Approval gate
- **QUALITY_CHECK**: Quality analysis
- **SECURITY_SCAN**: Security scanning
- **TEST**: Test execution
- **NOTIFICATION**: Send notifications
- **CUSTOM**: Custom step type

### Step Status

- **PENDING**: Not yet started
- **IN_PROGRESS**: Currently executing
- **COMPLETED**: Successfully completed
- **FAILED**: Execution failed
- **SKIPPED**: Skipped due to conditions

### Workflow Status

- **PENDING**: Not yet started
- **RUNNING**: Currently executing
- **COMPLETED**: All steps completed
- **FAILED**: One or more steps failed
- **CANCELLED**: Manually cancelled

## Usage

### Creating a Workflow

```python
from pr_agent.workflow_engine import WorkflowEngine, StepType

engine = WorkflowEngine()

# Define workflow steps
steps = [
    {
        "step_id": "review",
        "name": "Code Review",
        "type": "review",
        "config": {
            "reviewers": ["alice", "bob"],
            "min_approvals": 2
        }
    },
    {
        "step_id": "tests",
        "name": "Run Tests",
        "type": "test",
        "depends_on": ["review"],
        "config": {
            "test_suite": "full"
        }
    },
    {
        "step_id": "security",
        "name": "Security Scan",
        "type": "security_scan",
        "depends_on": ["review"],
        "parallel": True  # Can run in parallel with tests
    },
    {
        "step_id": "approve",
        "name": "Final Approval",
        "type": "approval",
        "depends_on": ["tests", "security"],
        "conditions": [
            {
                "field": "test_pass_rate",
                "operator": "greater_than",
                "value": 95
            }
        ]
    }
]

# Create workflow
workflow = engine.create_workflow(
    name="Standard Review Process",
    description="Standard code review workflow with tests and security",
    steps=steps,
    metadata={
        "team": "backend",
        "priority": "high"
    }
)
```

### Registering Step Handlers

```python
from pr_agent.workflow_engine import StepType

def review_handler(step, context):
    """Handle code review step."""
    reviewers = step.config.get("reviewers", [])
    pr_id = context.get("pr_id")
    
    # Perform review logic
    # ...
    
    return {
        "review_completed": True,
        "approvals": 2,
        "comments": 5
    }

def test_handler(step, context):
    """Handle test execution step."""
    test_suite = step.config.get("test_suite", "default")
    
    # Run tests
    # ...
    
    return {
        "tests_run": 150,
        "tests_passed": 148,
        "test_pass_rate": 98.7
    }

# Register handlers
engine.register_step_handler(StepType.REVIEW, review_handler)
engine.register_step_handler(StepType.TEST, test_handler)
```

### Executing a Workflow

```python
# Execute workflow with context
execution = engine.run_workflow(
    workflow_id=workflow.workflow_id,
    context={
        "pr_id": "123",
        "author": "alice",
        "branch": "feature/new-api"
    }
)

# Check execution status
print(f"Status: {execution.status}")
print(f"Completed steps: {execution.completed_steps}")
print(f"Failed steps: {execution.failed_steps}")
```

### Monitoring Execution

```python
# Get execution details
execution = engine.get_execution(execution_id)

print(f"Current step: {execution.current_step}")
print(f"Progress: {len(execution.completed_steps)}/{len(execution.workflow.steps)}")

# Get detailed status
status = engine.get_execution_status(execution_id)

for step_status in status["steps"]:
    print(f"{step_status['name']}: {step_status['status']}")
```

### Conditional Execution

```python
steps = [
    {
        "step_id": "quality_check",
        "name": "Quality Check",
        "type": "quality_check"
    },
    {
        "step_id": "auto_approve",
        "name": "Auto Approve",
        "type": "approval",
        "depends_on": ["quality_check"],
        "conditions": [
            {
                "field": "quality_score",
                "operator": "greater_than",
                "value": 90
            },
            {
                "field": "author",
                "operator": "not_equals",
                "value": "junior_dev"
            }
        ]
    },
    {
        "step_id": "manual_review",
        "name": "Manual Review",
        "type": "review",
        "depends_on": ["quality_check"],
        "conditions": [
            {
                "field": "quality_score",
                "operator": "less_than",
                "value": 90
            }
        ]
    }
]
```

### Condition Operators

- **EQUALS**: Field equals value
- **NOT_EQUALS**: Field does not equal value
- **GREATER_THAN**: Field is greater than value
- **LESS_THAN**: Field is less than value
- **CONTAINS**: Field contains value (string search)
- **NOT_CONTAINS**: Field does not contain value

### Parallel Execution

```python
steps = [
    {
        "step_id": "lint",
        "name": "Linting",
        "type": "quality_check",
        "parallel": True
    },
    {
        "step_id": "unit_tests",
        "name": "Unit Tests",
        "type": "test",
        "parallel": True
    },
    {
        "step_id": "security_scan",
        "name": "Security Scan",
        "type": "security_scan",
        "parallel": True
    },
    {
        "step_id": "approve",
        "name": "Approve",
        "type": "approval",
        "depends_on": ["lint", "unit_tests", "security_scan"]
    }
]
```

## REST API

### Create Workflow

```http
POST /api/workflows
Content-Type: application/json

{
  "name": "Standard Review",
  "description": "Standard review workflow",
  "steps": [
    {
      "step_id": "review",
      "name": "Code Review",
      "type": "review",
      "config": {"reviewers": ["alice"]}
    }
  ],
  "metadata": {"team": "backend"}
}
```

Response:
```json
{
  "workflow_id": "wf-123"
}
```

### Get Workflow

```http
GET /api/workflows/{workflow_id}
```

Response:
```json
{
  "workflow_id": "wf-123",
  "name": "Standard Review",
  "description": "Standard review workflow",
  "status": "pending",
  "created_at": "2024-01-15T10:00:00Z",
  "steps": [
    {
      "step_id": "review",
      "name": "Code Review",
      "type": "review",
      "config": {"reviewers": ["alice"]},
      "depends_on": [],
      "parallel": false
    }
  ]
}
```

### List Workflows

```http
GET /api/workflows
```

Response:
```json
{
  "workflows": [
    {
      "workflow_id": "wf-123",
      "name": "Standard Review",
      "description": "Standard review workflow",
      "status": "pending",
      "created_at": "2024-01-15T10:00:00Z"
    }
  ]
}
```

### Delete Workflow

```http
DELETE /api/workflows/{workflow_id}
```

### Execute Workflow

```http
POST /api/workflows/{workflow_id}/execute
Content-Type: application/json

{
  "pr_id": "123",
  "author": "alice"
}
```

Response:
```json
{
  "execution_id": "exec-456",
  "status": "running"
}
```

### Get Execution

```http
GET /api/workflows/executions/{execution_id}
```

Response:
```json
{
  "execution_id": "exec-456",
  "workflow_id": "wf-123",
  "status": "running",
  "started_at": "2024-01-15T10:05:00Z",
  "completed_at": null,
  "current_step": "review",
  "completed_steps": [],
  "failed_steps": []
}
```

### List Executions

```http
GET /api/workflows/executions?workflow_id=wf-123&status=completed
```

Response:
```json
{
  "executions": [
    {
      "execution_id": "exec-456",
      "workflow_id": "wf-123",
      "status": "completed",
      "started_at": "2024-01-15T10:05:00Z",
      "completed_at": "2024-01-15T10:15:00Z"
    }
  ]
}
```

### Cancel Execution

```http
POST /api/workflows/executions/{execution_id}/cancel
```

### Get Execution Status

```http
GET /api/workflows/executions/{execution_id}/status
```

Response:
```json
{
  "execution_id": "exec-456",
  "workflow_id": "wf-123",
  "status": "running",
  "started_at": "2024-01-15T10:05:00Z",
  "completed_at": null,
  "current_step": "tests",
  "completed_steps": ["review"],
  "failed_steps": [],
  "steps": [
    {
      "step_id": "review",
      "name": "Code Review",
      "type": "review",
      "status": "completed",
      "started_at": "2024-01-15T10:05:00Z",
      "completed_at": "2024-01-15T10:08:00Z",
      "error": null
    },
    {
      "step_id": "tests",
      "name": "Run Tests",
      "type": "test",
      "status": "in_progress",
      "started_at": "2024-01-15T10:08:00Z",
      "completed_at": null,
      "error": null
    }
  ]
}
```

## Example Workflows

### Simple Linear Workflow

```python
steps = [
    {"step_id": "review", "name": "Review", "type": "review"},
    {"step_id": "test", "name": "Test", "type": "test", "depends_on": ["review"]},
    {"step_id": "approve", "name": "Approve", "type": "approval", "depends_on": ["test"]}
]
```

### Parallel Quality Checks

```python
steps = [
    {"step_id": "lint", "name": "Lint", "type": "quality_check", "parallel": True},
    {"step_id": "test", "name": "Test", "type": "test", "parallel": True},
    {"step_id": "security", "name": "Security", "type": "security_scan", "parallel": True},
    {"step_id": "approve", "name": "Approve", "type": "approval", 
     "depends_on": ["lint", "test", "security"]}
]
```

### Conditional Approval

```python
steps = [
    {"step_id": "analyze", "name": "Analyze", "type": "quality_check"},
    {
        "step_id": "auto_approve",
        "name": "Auto Approve",
        "type": "approval",
        "depends_on": ["analyze"],
        "conditions": [
            {"field": "score", "operator": "greater_than", "value": 95},
            {"field": "complexity", "operator": "less_than", "value": 10}
        ]
    },
    {
        "step_id": "manual_review",
        "name": "Manual Review",
        "type": "review",
        "depends_on": ["analyze"],
        "conditions": [
            {"field": "score", "operator": "less_than", "value": 95}
        ]
    }
]
```

### Multi-Stage Review

```python
steps = [
    {"step_id": "junior_review", "name": "Junior Review", "type": "review",
     "config": {"reviewer_level": "junior"}},
    {"step_id": "senior_review", "name": "Senior Review", "type": "review",
     "depends_on": ["junior_review"], "config": {"reviewer_level": "senior"}},
    {"step_id": "tests", "name": "Tests", "type": "test",
     "depends_on": ["junior_review"], "parallel": True},
    {"step_id": "security", "name": "Security", "type": "security_scan",
     "depends_on": ["junior_review"], "parallel": True},
    {"step_id": "final_approve", "name": "Final Approval", "type": "approval",
     "depends_on": ["senior_review", "tests", "security"]}
]
```

## Integration Examples

### With Review Pipeline

```python
from pr_agent.workflow_engine import get_workflow_engine, StepType
from pr_agent.workflow import ReviewPipeline

engine = get_workflow_engine()

def review_step_handler(step, context):
    """Execute review using ReviewPipeline."""
    pipeline = ReviewPipeline()
    result = pipeline.run(context["files"])
    return {
        "issues_found": len(result.issues),
        "quality_score": result.quality_score
    }

engine.register_step_handler(StepType.REVIEW, review_step_handler)
```

### With Notification System

```python
from pr_agent.notifications import NotificationSystem

def notification_handler(step, context):
    """Send notification."""
    notifier = NotificationSystem()
    message = step.config.get("message", "Workflow step completed")
    channels = step.config.get("channels", ["email"])
    
    notifier.send(
        message=message,
        channels=channels,
        recipients=context.get("recipients", [])
    )
    
    return {"notification_sent": True}

engine.register_step_handler(StepType.NOTIFICATION, notification_handler)
```

### With SLA Management

```python
from pr_agent.sla import SLAManager

def approval_handler(step, context):
    """Check SLA compliance before approval."""
    sla_manager = SLAManager()
    review_id = context["review_id"]
    policy_id = step.config.get("sla_policy")
    
    compliance = sla_manager.check_compliance(review_id, policy_id)
    
    if not compliance.is_compliant:
        return {
            "approved": False,
            "reason": "SLA violation",
            "violations": compliance.violations
        }
    
    return {"approved": True}

engine.register_step_handler(StepType.APPROVAL, approval_handler)
```

## Best Practices

1. **Clear Dependencies**: Explicitly define step dependencies
2. **Meaningful Names**: Use descriptive step IDs and names
3. **Idempotent Handlers**: Handlers should be safe to retry
4. **Error Handling**: Handle errors gracefully in handlers
5. **Context Management**: Use context to share data between steps
6. **Parallel When Possible**: Mark independent steps as parallel
7. **Conditional Logic**: Use conditions to create flexible workflows
8. **Monitoring**: Track execution status and handle failures
9. **Testing**: Test workflows with different scenarios
10. **Documentation**: Document workflow purpose and requirements

## Configuration

Workflow engine settings in `configuration.toml`:

```toml
[workflow_engine]
# Storage path for workflows
storage_path = ".pr_agent/workflows"

# Default timeout for steps (seconds)
default_step_timeout = 300

# Maximum parallel steps
max_parallel_steps = 5

# Enable execution history
keep_execution_history = true
history_retention_days = 30
```

## Troubleshooting

**Workflow not executing:**
- Check that all step handlers are registered
- Verify step dependencies are correct
- Ensure conditions evaluate correctly

**Steps executing in wrong order:**
- Review dependency configuration
- Check for circular dependencies
- Verify parallel flag settings

**Execution stuck:**
- Check for missing step handlers
- Review timeout settings
- Look for blocking operations in handlers

**Context not propagating:**
- Ensure handlers return dictionaries
- Check that step results are being captured
- Verify context keys match condition fields
