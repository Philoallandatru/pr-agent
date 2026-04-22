# Code Review Notification System

## Overview

The notification system provides multi-channel notifications for code review events with user preferences, quiet hours, and custom handlers.

## Features

- **Multi-Channel Support**: EMAIL, SLACK, DINGTALK, WECOM, WEBHOOK
- **Event-Based**: Trigger notifications on specific review events
- **User Preferences**: Per-user notification settings
- **Quiet Hours**: Respect user's do-not-disturb periods (supports overnight ranges)
- **Template System**: Jinja2-based notification templates
- **Custom Handlers**: Register custom notification channels
- **Priority Levels**: LOW, NORMAL, HIGH, URGENT
- **Retry Mechanism**: Automatic retry on failure
- **Notification History**: Track all sent notifications

## Architecture

```
NotificationSystem
├── Templates (Jinja2)
├── Preferences (per user)
├── Channels (EMAIL, SLACK, etc.)
├── Custom Handlers
└── History
```

## Data Models

### NotificationTemplate

```python
@dataclass
class NotificationTemplate:
    template_id: str
    event: NotificationEvent
    channel: NotificationChannel
    subject_template: str
    body_template: str
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### NotificationPreference

```python
@dataclass
class NotificationPreference:
    user_id: str
    email: Optional[str] = None
    slack_id: Optional[str] = None
    dingtalk_id: Optional[str] = None
    wecom_id: Optional[str] = None
    enabled_channels: List[NotificationChannel] = field(default_factory=list)
    enabled_events: List[NotificationEvent] = field(default_factory=list)
    quiet_hours_start: Optional[int] = None  # 0-23
    quiet_hours_end: Optional[int] = None    # 0-23
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### Notification

```python
@dataclass
class Notification:
    notification_id: str
    event: NotificationEvent
    channel: NotificationChannel
    recipient: str
    subject: str
    body: str
    priority: NotificationPriority
    status: NotificationStatus
    created_at: datetime
    sent_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

## Notification Events

```python
class NotificationEvent(Enum):
    PR_CREATED = "pr_created"
    PR_UPDATED = "pr_updated"
    PR_MERGED = "pr_merged"
    PR_CLOSED = "pr_closed"
    REVIEW_REQUESTED = "review_requested"
    REVIEW_SUBMITTED = "review_submitted"
    REVIEW_APPROVED = "review_approved"
    REVIEW_REJECTED = "review_rejected"
    COMMENT_ADDED = "comment_added"
    MENTION = "mention"
```

## Notification Channels

```python
class NotificationChannel(Enum):
    EMAIL = "email"
    SLACK = "slack"
    DINGTALK = "dingtalk"
    WECOM = "wecom"
    WEBHOOK = "webhook"
```

## Usage

### Initialize System

```python
from pr_agent.notifications import NotificationSystem

system = NotificationSystem()
```

### Register Templates

```python
from pr_agent.notifications import NotificationTemplate, NotificationEvent, NotificationChannel

template = NotificationTemplate(
    template_id="pr_created_email",
    event=NotificationEvent.PR_CREATED,
    channel=NotificationChannel.EMAIL,
    subject_template="New PR: {{ pr_title }}",
    body_template="""
    A new pull request has been created:
    
    Title: {{ pr_title }}
    Author: {{ author }}
    Repository: {{ repository }}
    URL: {{ pr_url }}
    
    Description:
    {{ description }}
    """
)

system.register_template(template)
```

### Set User Preferences

```python
from pr_agent.notifications import NotificationPreference

preference = NotificationPreference(
    user_id="user123",
    email="user@example.com",
    slack_id="U12345678",
    enabled_channels=[
        NotificationChannel.EMAIL,
        NotificationChannel.SLACK
    ],
    enabled_events=[
        NotificationEvent.REVIEW_REQUESTED,
        NotificationEvent.COMMENT_ADDED
    ],
    quiet_hours_start=22,  # 10 PM
    quiet_hours_end=8      # 8 AM
)

system.set_preference(preference)
```

### Send Notifications

```python
from pr_agent.notifications import NotificationEvent, NotificationPriority

notifications = system.notify(
    event=NotificationEvent.REVIEW_REQUESTED,
    recipients=["user123", "user456"],
    context={
        "pr_title": "Fix authentication bug",
        "author": "john_doe",
        "repository": "myapp",
        "pr_url": "https://github.com/org/myapp/pull/123"
    },
    priority=NotificationPriority.HIGH
)
```

### Register Custom Handler

```python
def custom_webhook_handler(notification):
    """Custom webhook implementation."""
    import requests
    
    payload = {
        "event": notification.event.value,
        "subject": notification.subject,
        "body": notification.body,
        "priority": notification.priority.value
    }
    
    response = requests.post(
        "https://my-webhook.example.com/notify",
        json=payload
    )
    
    if response.status_code != 200:
        raise Exception(f"Webhook failed: {response.text}")

system.register_custom_handler(
    NotificationChannel.WEBHOOK,
    custom_webhook_handler
)
```

### Get Notification History

```python
# Get all notifications for a user
history = system.get_notification_history(user_id="user123", limit=50)

# Get notifications for a specific event
history = system.get_notification_history(
    event=NotificationEvent.REVIEW_REQUESTED,
    limit=100
)
```

## Quiet Hours

Quiet hours prevent notifications during specified time ranges. The system supports overnight ranges (e.g., 22:00-08:00).

### Same-Day Range

```python
preference = NotificationPreference(
    user_id="user123",
    quiet_hours_start=12,  # Noon
    quiet_hours_end=13     # 1 PM
)
# Blocks notifications from 12:00 to 13:00
```

### Overnight Range

```python
preference = NotificationPreference(
    user_id="user123",
    quiet_hours_start=22,  # 10 PM
    quiet_hours_end=8      # 8 AM
)
# Blocks notifications from 22:00 to 08:00 (next day)
```

## Template Variables

Templates use Jinja2 syntax and have access to context variables:

### Common Variables

- `pr_title`: Pull request title
- `pr_url`: Pull request URL
- `author`: PR author username
- `repository`: Repository name
- `description`: PR description

### Event-Specific Variables

**REVIEW_REQUESTED**:
- `reviewer`: Reviewer username
- `deadline`: Review deadline

**REVIEW_SUBMITTED**:
- `reviewer`: Reviewer username
- `status`: Review status (approved/rejected)
- `comments`: Review comments

**COMMENT_ADDED**:
- `commenter`: Comment author
- `comment`: Comment text
- `file`: File path (if applicable)

## REST API

### Register Template

```http
POST /api/notifications/templates
Content-Type: application/json

{
  "template_id": "pr_created_email",
  "event": "pr_created",
  "channel": "email",
  "subject_template": "New PR: {{ pr_title }}",
  "body_template": "A new PR has been created...",
  "metadata": {}
}
```

### Set Preferences

```http
POST /api/notifications/preferences
Content-Type: application/json

{
  "user_id": "user123",
  "email": "user@example.com",
  "slack_id": "U12345678",
  "enabled_channels": ["email", "slack"],
  "enabled_events": ["review_requested", "comment_added"],
  "quiet_hours_start": 22,
  "quiet_hours_end": 8
}
```

### Get Preferences

```http
GET /api/notifications/preferences/user123
```

Response:
```json
{
  "user_id": "user123",
  "email": "user@example.com",
  "slack_id": "U12345678",
  "dingtalk_id": null,
  "wecom_id": null,
  "enabled_channels": ["email", "slack"],
  "enabled_events": ["review_requested", "comment_added"],
  "quiet_hours_start": 22,
  "quiet_hours_end": 8,
  "metadata": {}
}
```

### Send Notification

```http
POST /api/notifications/send
Content-Type: application/json

{
  "event": "review_requested",
  "recipients": ["user123", "user456"],
  "context": {
    "pr_title": "Fix authentication bug",
    "author": "john_doe",
    "repository": "myapp",
    "pr_url": "https://github.com/org/myapp/pull/123",
    "reviewer": "user123"
  },
  "priority": "high",
  "channels": ["email", "slack"]
}
```

Response:
```json
{
  "message": "Notifications sent",
  "count": 2,
  "notifications": [
    {
      "notification_id": "notif_abc123",
      "event": "review_requested",
      "channel": "email",
      "recipient": "user123",
      "subject": "Review Requested: Fix authentication bug",
      "body": "...",
      "priority": "high",
      "status": "sent",
      "created_at": "2024-01-15T10:30:00Z",
      "sent_at": "2024-01-15T10:30:01Z"
    }
  ]
}
```

### Get History

```http
GET /api/notifications/history?user_id=user123&limit=50
```

Response:
```json
{
  "notifications": [...],
  "count": 50
}
```

## Configuration

Add to `configuration.toml`:

```toml
[notifications]
enabled = true
retry_attempts = 3
retry_delay = 60  # seconds

[notifications.email]
smtp_host = "smtp.gmail.com"
smtp_port = 587
smtp_user = "notifications@example.com"
smtp_password = "your-password"
from_address = "PR Agent <notifications@example.com>"

[notifications.slack]
bot_token = "xoxb-your-slack-bot-token"
default_channel = "#code-reviews"

[notifications.dingtalk]
webhook_url = "https://oapi.dingtalk.com/robot/send?access_token=..."
secret = "your-secret"

[notifications.wecom]
webhook_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=..."
```

## Best Practices

1. **Template Design**: Keep templates concise and actionable
2. **Quiet Hours**: Respect user preferences to avoid notification fatigue
3. **Priority Levels**: Use HIGH/URGENT sparingly for critical events
4. **Custom Handlers**: Implement retry logic in custom handlers
5. **Testing**: Test templates with various context data
6. **Monitoring**: Track notification delivery rates and failures

## Error Handling

The system includes automatic retry for failed notifications:

```python
# Configure retry behavior
system = NotificationSystem(
    retry_attempts=3,
    retry_delay=60  # seconds
)
```

Failed notifications are logged and can be retrieved from history:

```python
failed = [n for n in system.get_notification_history() 
          if n.status == NotificationStatus.FAILED]
```

## Testing

Run tests:

```bash
pytest tests/unittest/test_notification_system.py -v
```

Test coverage:
- Template registration and rendering
- User preference management
- Quiet hours logic (including overnight ranges)
- Multi-channel delivery
- Custom handler registration
- Retry mechanism
- Notification history

## Examples

### Example 1: PR Review Request

```python
# Register template
template = NotificationTemplate(
    template_id="review_request",
    event=NotificationEvent.REVIEW_REQUESTED,
    channel=NotificationChannel.EMAIL,
    subject_template="Review Requested: {{ pr_title }}",
    body_template="""
    Hi {{ reviewer }},
    
    {{ author }} has requested your review on:
    {{ pr_title }}
    
    Repository: {{ repository }}
    URL: {{ pr_url }}
    
    Please review by {{ deadline }}.
    """
)
system.register_template(template)

# Send notification
system.notify(
    event=NotificationEvent.REVIEW_REQUESTED,
    recipients=["reviewer123"],
    context={
        "pr_title": "Add user authentication",
        "author": "john_doe",
        "repository": "myapp",
        "pr_url": "https://github.com/org/myapp/pull/456",
        "reviewer": "reviewer123",
        "deadline": "2024-01-20"
    }
)
```

### Example 2: Slack Notification

```python
# Set up Slack preference
preference = NotificationPreference(
    user_id="user123",
    slack_id="U12345678",
    enabled_channels=[NotificationChannel.SLACK],
    enabled_events=[NotificationEvent.COMMENT_ADDED]
)
system.set_preference(preference)

# Register Slack template
template = NotificationTemplate(
    template_id="comment_slack",
    event=NotificationEvent.COMMENT_ADDED,
    channel=NotificationChannel.SLACK,
    subject_template="",  # Slack doesn't use subject
    body_template="""
    :speech_balloon: *New Comment* on {{ pr_title }}
    
    *{{ commenter }}* commented:
    > {{ comment }}
    
    <{{ pr_url }}|View PR>
    """
)
system.register_template(template)

# Send notification
system.notify(
    event=NotificationEvent.COMMENT_ADDED,
    recipients=["user123"],
    context={
        "pr_title": "Fix bug in login",
        "commenter": "jane_doe",
        "comment": "This looks good, but please add tests.",
        "pr_url": "https://github.com/org/myapp/pull/789"
    }
)
```

## Troubleshooting

### Notifications Not Sent

1. Check user preferences are set correctly
2. Verify event is enabled for the user
3. Check if current time is within quiet hours
4. Review notification history for error messages

### Template Rendering Errors

1. Verify all required variables are in context
2. Check Jinja2 syntax in templates
3. Test templates with sample data

### Custom Handler Failures

1. Implement proper error handling in handler
2. Add logging to track failures
3. Consider implementing retry logic

## Future Enhancements

- [ ] Notification batching (digest emails)
- [ ] Rate limiting per user
- [ ] Notification scheduling
- [ ] A/B testing for templates
- [ ] Analytics dashboard
- [ ] Mobile push notifications
- [ ] SMS support
