# SLA Management System

The SLA (Service Level Agreement) Management System monitors code review performance against defined time targets and handles escalations when SLAs are violated.

## Features

- **SLA Policy Definition**: Define time targets for different review metrics
- **Multi-Priority Support**: Different SLAs for different priority levels
- **Real-time Compliance Monitoring**: Track reviews against SLA targets
- **Violation Detection**: Automatic detection of SLA violations
- **Escalation Management**: Automatic escalation when SLAs are violated
- **Statistics and Reporting**: Comprehensive SLA compliance statistics
- **Flexible Targeting**: Apply SLAs by repository, team, or priority

## Core Concepts

### SLA Metrics

The system tracks four key metrics:

- **First Response Time**: Time from PR creation to first review comment
- **Review Completion Time**: Time from PR creation to review completion
- **Approval Time**: Time from PR creation to approval
- **Merge Time**: Time from PR creation to merge

### SLA Status

Reviews can have the following SLA status:

- **Compliant**: All metrics within target
- **At Risk**: Approaching target (>80% by default)
- **Violated**: Exceeded target time
- **Escalated**: Violation escalated to senior reviewers

### Priority Levels

- **Low**: Non-urgent changes
- **Normal**: Standard priority
- **High**: Important changes
- **Critical**: Urgent fixes requiring immediate attention

## Usage

### Creating SLA Policies

```python
from pr_agent.sla import SLAManager, SLATarget, SLAPriority, SLAMetric

manager = SLAManager()

# Define targets
targets = [
    SLATarget(
        metric=SLAMetric.FIRST_RESPONSE_TIME,
        target_hours=2.0,
        warning_threshold_percent=80.0
    ),
    SLATarget(
        metric=SLAMetric.REVIEW_COMPLETION_TIME,
        target_hours=24.0
    )
]

# Create policy
policy = manager.create_policy(
    policy_id="standard-sla",
    name="Standard Review SLA",
    description="Standard SLA for normal priority reviews",
    priority=SLAPriority.NORMAL,
    targets=targets,
    applies_to={
        "repositories": ["myorg/myrepo", "myorg/another-repo"]
    },
    escalation_enabled=True,
    escalation_targets=["senior-reviewer-1", "senior-reviewer-2"]
)
```

### Tracking Reviews

```python
# Start tracking a review
manager.start_tracking(
    review_id="rev-123",
    repository="myorg/myrepo",
    priority=SLAPriority.NORMAL,
    metadata={"pr_number": 456}
)

# Record events as they happen
manager.record_event("rev-123", "first_response")
manager.record_event("rev-123", "completed")
manager.record_event("rev-123", "approved")
manager.record_event("rev-123", "merged")
```

### Checking Compliance

```python
# Check compliance at any time
compliance = manager.check_compliance("rev-123")

print(f"Status: {compliance.status}")
print(f"Violations: {len(compliance.violations)}")

for metric, data in compliance.metrics.items():
    print(f"{metric}: {data['actual_hours']}h / {data['target_hours']}h")
    if data['violated']:
        print(f"  VIOLATED by {data['violation_percent']}%")
    elif data['at_risk']:
        print(f"  AT RISK")
```

### Handling Violations

```python
# Register violation callback
def on_violation(violation):
    print(f"SLA violated for {violation.review_id}")
    print(f"Metric: {violation.metric}")
    print(f"Target: {violation.target_hours}h")
    print(f"Actual: {violation.actual_hours}h")

manager.register_violation_callback(on_violation)

# Register escalation callback
def on_escalation(violation, policy):
    print(f"Escalating {violation.review_id} to {violation.escalated_to}")
    # Send notification, reassign review, etc.

manager.register_escalation_callback(on_escalation)
```

### Getting Violations

```python
# Get all unresolved violations
violations = manager.get_violations(resolved=False)

# Get violations for specific review
review_violations = manager.get_violations(review_id="rev-123")

# Get violations for specific policy
policy_violations = manager.get_violations(policy_id="standard-sla")

# Resolve a violation
manager.resolve_violation(violation.violation_id)
```

### Statistics

```python
# Get statistics for all policies
stats = manager.get_statistics()

for stat in stats:
    print(f"Policy: {stat.policy_id}")
    print(f"Total reviews: {stat.total_reviews}")
    print(f"Compliant: {stat.compliant_reviews}")
    print(f"Violated: {stat.violated_reviews}")
    print(f"Compliance rate: {stat.compliance_rate}%")

# Get statistics for specific time period
from datetime import datetime, timedelta

end_date = datetime.now()
start_date = end_date - timedelta(days=30)

stats = manager.get_statistics(
    start_date=start_date,
    end_date=end_date
)
```

## REST API

### Create SLA Policy

```http
POST /api/sla/policies
Content-Type: application/json

{
  "policy_id": "standard-sla",
  "name": "Standard Review SLA",
  "description": "Standard SLA for normal priority reviews",
  "priority": "normal",
  "targets": [
    {
      "metric": "first_response_time",
      "target_hours": 2.0,
      "warning_threshold_percent": 80.0
    },
    {
      "metric": "review_completion_time",
      "target_hours": 24.0
    }
  ],
  "applies_to": {
    "repositories": ["myorg/myrepo"]
  },
  "escalation_enabled": true,
  "escalation_targets": ["senior-reviewer"]
}
```

### List SLA Policies

```http
GET /api/sla/policies
GET /api/sla/policies?enabled_only=true
```

### Get SLA Policy

```http
GET /api/sla/policies/{policy_id}
```

### Update SLA Policy

```http
PUT /api/sla/policies/{policy_id}
Content-Type: application/json

{
  "enabled": false,
  "escalation_targets": ["new-reviewer"]
}
```

### Delete SLA Policy

```http
DELETE /api/sla/policies/{policy_id}
```

### Start Tracking

```http
POST /api/sla/tracking/start
Content-Type: application/json

{
  "review_id": "rev-123",
  "repository": "myorg/myrepo",
  "priority": "normal",
  "metadata": {
    "pr_number": 456
  }
}
```

### Record Event

```http
POST /api/sla/tracking/event
Content-Type: application/json

{
  "review_id": "rev-123",
  "event_type": "first_response",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Event types:**
- `first_response`: First review comment
- `completed`: Review completed
- `approved`: PR approved
- `merged`: PR merged

### Check Compliance

```http
GET /api/sla/compliance/{review_id}
```

### Get Violations

```http
GET /api/sla/violations
GET /api/sla/violations?review_id=rev-123
GET /api/sla/violations?policy_id=standard-sla
GET /api/sla/violations?resolved=false
```

### Resolve Violation

```http
POST /api/sla/violations/{violation_id}/resolve
```

### Get Statistics

```http
GET /api/sla/statistics
GET /api/sla/statistics?policy_id=standard-sla
GET /api/sla/statistics?start_date=2024-01-01&end_date=2024-01-31
```

## Configuration

SLA settings in `configuration.toml`:

```toml
[sla]
# Storage path for SLA data
storage_path = "~/.pr-agent/sla"

# Default warning threshold (percentage of target)
default_warning_threshold = 80.0

# Enable automatic escalation
auto_escalation_enabled = true

# Escalation delay (minutes after violation)
escalation_delay_minutes = 30

# Enable notifications
notifications_enabled = true
```

## Example Policies

### Critical Priority SLA

```python
# Very tight SLA for critical issues
targets = [
    SLATarget(
        metric=SLAMetric.FIRST_RESPONSE_TIME,
        target_hours=0.5  # 30 minutes
    ),
    SLATarget(
        metric=SLAMetric.REVIEW_COMPLETION_TIME,
        target_hours=2.0
    )
]

manager.create_policy(
    policy_id="critical-sla",
    name="Critical Issue SLA",
    description="SLA for critical production issues",
    priority=SLAPriority.CRITICAL,
    targets=targets,
    escalation_enabled=True,
    escalation_targets=["oncall-lead", "engineering-manager"]
)
```

### High Priority SLA

```python
# Faster SLA for high priority work
targets = [
    SLATarget(
        metric=SLAMetric.FIRST_RESPONSE_TIME,
        target_hours=1.0
    ),
    SLATarget(
        metric=SLAMetric.REVIEW_COMPLETION_TIME,
        target_hours=8.0
    )
]

manager.create_policy(
    policy_id="high-priority-sla",
    name="High Priority SLA",
    description="SLA for high priority features",
    priority=SLAPriority.HIGH,
    targets=targets
)
```

### Low Priority SLA

```python
# Relaxed SLA for low priority work
targets = [
    SLATarget(
        metric=SLAMetric.FIRST_RESPONSE_TIME,
        target_hours=8.0
    ),
    SLATarget(
        metric=SLAMetric.REVIEW_COMPLETION_TIME,
        target_hours=72.0  # 3 days
    )
]

manager.create_policy(
    policy_id="low-priority-sla",
    name="Low Priority SLA",
    description="SLA for low priority changes",
    priority=SLAPriority.LOW,
    targets=targets,
    escalation_enabled=False  # No escalation for low priority
)
```

## Integration Examples

### With Notification System

```python
from pr_agent.sla import get_sla_manager
from pr_agent.notifications import get_notification_system

sla_manager = get_sla_manager()
notification_system = get_notification_system()

def notify_violation(violation):
    """Send notification when SLA is violated."""
    notification_system.send_notification(
        user_id=violation.escalated_to,
        event="SLA_VIOLATED",
        title=f"SLA Violation: {violation.review_id}",
        message=f"Review {violation.review_id} violated {violation.metric.value} SLA",
        priority="high"
    )

sla_manager.register_violation_callback(notify_violation)
```

### With Assignment System

```python
from pr_agent.sla import get_sla_manager
from pr_agent.assignment import get_assignment_engine

sla_manager = get_sla_manager()
assignment_engine = get_assignment_engine()

def escalate_review(violation, policy):
    """Reassign review when escalated."""
    if policy.escalation_targets:
        assignment_engine.assign_review(
            review_id=violation.review_id,
            reviewer_id=policy.escalation_targets[0],
            reason="SLA escalation"
        )

sla_manager.register_escalation_callback(escalate_review)
```

### With Dashboard System

```python
from pr_agent.sla import get_sla_manager
from pr_agent.dashboard import get_dashboard_system

sla_manager = get_sla_manager()
dashboard = get_dashboard_system()

# Record SLA compliance in dashboard
compliance = sla_manager.check_compliance("rev-123")

dashboard.record_review({
    "review_id": "rev-123",
    "sla_status": compliance.status.value,
    "sla_violations": len(compliance.violations),
    "sla_compliant": compliance.status == SLAStatus.COMPLIANT
})
```

## Best Practices

1. **Set Realistic Targets**: Base SLA targets on historical data and team capacity
2. **Use Priority Levels**: Different priorities should have different SLAs
3. **Monitor Compliance**: Regularly review SLA statistics to identify trends
4. **Adjust as Needed**: Update SLA targets based on team performance and business needs
5. **Escalate Appropriately**: Only escalate when necessary to avoid alert fatigue
6. **Track All Metrics**: Monitor multiple metrics for comprehensive coverage
7. **Communicate SLAs**: Ensure team understands SLA expectations
8. **Review Violations**: Analyze violations to identify process improvements

## Troubleshooting

**SLA not being checked:**
- Verify tracking was started with `start_tracking()`
- Check that a policy exists for the review's priority and repository
- Ensure policy is enabled

**Escalation not working:**
- Verify `escalation_enabled` is `True` in policy
- Check that `escalation_targets` are configured
- Ensure escalation callback is registered

**Incorrect compliance status:**
- Verify events are being recorded correctly
- Check that timestamps are accurate
- Review target hours in policy

**Statistics not accurate:**
- Ensure `check_compliance()` is being called regularly
- Verify date range filters
- Check that compliance history is being saved
