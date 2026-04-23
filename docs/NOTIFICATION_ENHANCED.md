# Enhanced Notification System

The Enhanced Notification System provides intelligent, multi-channel notification delivery with advanced features like templates, rules, rate limiting, and quiet hours.

## Features

### Core Capabilities

1. **Multi-Channel Support**
   - Email notifications
   - Slack integration
   - Microsoft Teams integration
   - Custom webhook endpoints

2. **Template System**
   - Jinja2-based templates
   - Variable substitution
   - Channel-specific formatting
   - Reusable templates

3. **Rule Engine**
   - Conditional notification routing
   - Event-based triggers
   - Priority management
   - Dynamic channel selection

4. **Rate Limiting**
   - Per-recipient rate limits
   - Configurable time windows
   - Automatic throttling

5. **Quiet Hours**
   - Time-based notification suppression
   - Timezone-aware scheduling
   - Per-rule configuration

6. **Retry Mechanism**
   - Automatic retry on failure
   - Exponential backoff
   - Maximum retry limits

## Usage

### Basic Notification

```python
from pr_agent.notification_enhanced import (
    get_notification_system,
    NotificationEvent,
    NotificationChannel,
    NotificationPriority
)

# Get system instance
notification_system = get_notification_system()

# Send notification
notifications = notification_system.send_notification(
    notification_id="notif_001",
    recipient="user@example.com",
    event=NotificationEvent.REVIEW_REQUESTED,
    context={
        "pr_title": "Fix critical bug",
        "author": "John Doe",
        "repository": "my-repo"
    },
    channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
    priority=NotificationPriority.HIGH
)
```

### Creating Templates

```python
from pr_agent.notification_enhanced import NotificationTemplate

template = NotificationTemplate(
    template_id="review_request",
    name="Review Request Template",
    event=NotificationEvent.REVIEW_REQUESTED,
    subject_template="Code Review: {{ pr_title }}",
    body_template="""
    Hello,
    
    {{ author }} has requested your review for PR: {{ pr_title }}
    
    Repository: {{ repository }}
    
    Please review at your earliest convenience.
    """,
    channel=NotificationChannel.EMAIL,
    priority=NotificationPriority.MEDIUM,
    variables=["pr_title", "author", "repository"]
)

notification_system.add_template(template)
```

### Creating Rules

```python
from pr_agent.notification_enhanced import NotificationRule

rule = NotificationRule(
    rule_id="urgent_reviews",
    name="Urgent Review Notifications",
    event=NotificationEvent.REVIEW_REQUESTED,
    conditions={
        "priority": "high",
        "repository": "critical-service"
    },
    channels=[
        NotificationChannel.EMAIL,
        NotificationChannel.SLACK,
        NotificationChannel.TEAMS
    ],
    priority=NotificationPriority.HIGH,
    enabled=True,
    rate_limit={"max_per_hour": 10},
    quiet_hours={"start": 22, "end": 8}  # 10 PM to 8 AM
)

notification_system.add_rule(rule)
```

### Custom Channel Handlers

```python
def custom_sms_handler(notification):
    """Send SMS notification"""
    # Your SMS sending logic here
    print(f"Sending SMS to {notification.recipient}: {notification.subject}")

notification_system.register_channel_handler(
    NotificationChannel.WEBHOOK,
    custom_sms_handler
)
```

## API Reference

### NotificationEnhancedSystem

Main system class for managing notifications.

#### Methods

- `send_notification(notification_id, recipient, event, context, channels=None, priority=None)` - Send notification
- `get_notification(notification_id)` - Get notification by ID
- `list_notifications(recipient=None, status=None, event=None, limit=100)` - List notifications
- `retry_notification(notification_id)` - Retry failed notification
- `cancel_notification(notification_id)` - Cancel pending notification
- `get_statistics(start_date=None, end_date=None)` - Get statistics
- `add_template(template)` - Add notification template
- `list_templates(event=None, channel=None)` - List templates
- `add_rule(rule)` - Add notification rule
- `list_rules(enabled_only=False)` - List rules
- `register_channel_handler(channel, handler)` - Register custom handler

### NotificationEvent

Supported notification events:

- `REVIEW_REQUESTED` - Review requested
- `REVIEW_COMPLETED` - Review completed
- `REVIEW_APPROVED` - Review approved
- `REVIEW_REJECTED` - Review rejected
- `COMMENT_ADDED` - Comment added
- `ISSUE_FOUND` - Issue found
- `ISSUE_RESOLVED` - Issue resolved
- `PR_MERGED` - PR merged
- `PR_CLOSED` - PR closed
- `SYSTEM_ALERT` - System alert

### NotificationChannel

Supported notification channels:

- `EMAIL` - Email notifications
- `SLACK` - Slack messages
- `TEAMS` - Microsoft Teams messages
- `WEBHOOK` - Custom webhook

### NotificationPriority

Priority levels:

- `LOW` - Low priority
- `MEDIUM` - Medium priority
- `HIGH` - High priority
- `URGENT` - Urgent priority

### NotificationStatus

Notification statuses:

- `PENDING` - Waiting to be sent
- `SENT` - Successfully sent
- `FAILED` - Failed to send
- `CANCELLED` - Cancelled by user

## REST API Endpoints

### Send Notification

```http
POST /api/notifications/send
Content-Type: application/json

{
  "notification_id": "notif_001",
  "recipient": "user@example.com",
  "event": "review_requested",
  "context": {
    "pr_title": "Fix bug",
    "author": "John Doe"
  },
  "channels": ["email", "slack"],
  "priority": "high"
}
```

### Get Notification

```http
GET /api/notifications/{notification_id}
```

### List Notifications

```http
GET /api/notifications?recipient=user@example.com&status=sent&limit=50
```

### Retry Notification

```http
POST /api/notifications/{notification_id}/retry
```

### Cancel Notification

```http
DELETE /api/notifications/{notification_id}
```

### Get Statistics

```http
GET /api/notifications/statistics?start_date=2024-01-01&end_date=2024-12-31
```

### Create Template

```http
POST /api/notifications/templates
Content-Type: application/json

{
  "template_id": "review_request",
  "name": "Review Request",
  "event": "review_requested",
  "subject_template": "Review: {{ pr_title }}",
  "body_template": "Please review {{ pr_title }}",
  "channel": "email",
  "priority": "medium",
  "variables": ["pr_title"]
}
```

### List Templates

```http
GET /api/notifications/templates?event=review_requested&channel=email
```

### Create Rule

```http
POST /api/notifications/rules
Content-Type: application/json

{
  "rule_id": "urgent_reviews",
  "name": "Urgent Reviews",
  "event": "review_requested",
  "conditions": {"priority": "high"},
  "channels": ["email", "slack"],
  "priority": "high",
  "enabled": true,
  "rate_limit": {"max_per_hour": 10},
  "quiet_hours": {"start": 22, "end": 8}
}
```

### List Rules

```http
GET /api/notifications/rules?enabled_only=true
```

## Configuration

Add to `configuration.toml`:

```toml
[notification_enhanced]
# Default channels
default_channels = ["email"]

# Rate limiting
rate_limit_enabled = true
rate_limit_window_seconds = 3600
rate_limit_max_per_window = 100

# Retry settings
max_retries = 3
retry_delay_seconds = 60

# Email settings
email_from = "noreply@example.com"
email_smtp_host = "smtp.example.com"
email_smtp_port = 587

# Slack settings
slack_webhook_url = "https://hooks.slack.com/services/..."
slack_bot_token = "xoxb-..."

# Teams settings
teams_webhook_url = "https://outlook.office.com/webhook/..."
```

## Best Practices

1. **Use Templates** - Create reusable templates for common notification types
2. **Set Priorities** - Use appropriate priority levels to avoid notification fatigue
3. **Configure Quiet Hours** - Respect user time zones and working hours
4. **Rate Limiting** - Prevent notification spam with rate limits
5. **Monitor Statistics** - Track notification delivery and failure rates
6. **Custom Handlers** - Implement custom handlers for specialized channels
7. **Test Thoroughly** - Test notification delivery before production deployment

## Examples

### High-Priority Alert

```python
# Send urgent security alert
notification_system.send_notification(
    notification_id=f"security_alert_{timestamp}",
    recipient="security-team@example.com",
    event=NotificationEvent.SYSTEM_ALERT,
    context={
        "alert_type": "Security Vulnerability",
        "severity": "Critical",
        "description": "SQL injection detected"
    },
    channels=[
        NotificationChannel.EMAIL,
        NotificationChannel.SLACK,
        NotificationChannel.TEAMS
    ],
    priority=NotificationPriority.URGENT
)
```

### Batch Notifications

```python
# Send notifications to multiple recipients
recipients = ["user1@example.com", "user2@example.com", "user3@example.com"]

for recipient in recipients:
    notification_system.send_notification(
        notification_id=f"batch_{recipient}_{timestamp}",
        recipient=recipient,
        event=NotificationEvent.REVIEW_REQUESTED,
        context={"pr_title": "Update documentation"},
        channels=[NotificationChannel.EMAIL]
    )
```

### Conditional Routing

```python
# Create rule for critical repositories
critical_repo_rule = NotificationRule(
    rule_id="critical_repos",
    name="Critical Repository Notifications",
    event=NotificationEvent.REVIEW_REQUESTED,
    conditions={
        "repository": ["auth-service", "payment-service", "user-service"]
    },
    channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
    priority=NotificationPriority.HIGH,
    enabled=True
)

notification_system.add_rule(critical_repo_rule)
```

## Troubleshooting

### Notifications Not Sending

1. Check channel handler registration
2. Verify recipient format
3. Check rate limiting status
4. Review quiet hours configuration
5. Check notification status in database

### Template Rendering Errors

1. Verify all required variables are provided
2. Check template syntax
3. Test template with sample data
4. Review error logs

### Rate Limit Issues

1. Check rate limit configuration
2. Review notification frequency
3. Adjust rate limits if needed
4. Monitor statistics

## See Also

- [Notification System](NOTIFICATIONS.md) - Basic notification system
- [Webhook Integration](WEBHOOK_NOTIFICATIONS.md) - Webhook setup
- [API Documentation](API.md) - Complete API reference
