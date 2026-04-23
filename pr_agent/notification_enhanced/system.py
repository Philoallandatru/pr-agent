"""
Enhanced Notification System

Provides comprehensive notification functionality with multiple channels,
intelligent routing, templates, and delivery tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import json
import re
from collections import defaultdict


class NotificationChannel(str, Enum):
    """Notification delivery channels"""
    EMAIL = "email"
    SLACK = "slack"
    DINGTALK = "dingtalk"
    WECHAT_WORK = "wechat_work"
    WEBHOOK = "webhook"
    IN_APP = "in_app"
    SMS = "sms"


class NotificationPriority(str, Enum):
    """Notification priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class NotificationStatus(str, Enum):
    """Notification delivery status"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NotificationEvent(str, Enum):
    """Events that trigger notifications"""
    REVIEW_REQUESTED = "review_requested"
    REVIEW_COMPLETED = "review_completed"
    REVIEW_APPROVED = "review_approved"
    REVIEW_REJECTED = "review_rejected"
    COMMENT_ADDED = "comment_added"
    MENTION = "mention"
    ISSUE_FOUND = "issue_found"
    PR_MERGED = "pr_merged"
    PR_CLOSED = "pr_closed"
    DEADLINE_APPROACHING = "deadline_approaching"
    SLA_VIOLATION = "sla_violation"
    QUALITY_GATE_FAILED = "quality_gate_failed"


@dataclass
class NotificationTemplate:
    """Notification message template"""
    template_id: str
    name: str
    event: NotificationEvent
    subject_template: str
    body_template: str
    channel: NotificationChannel
    priority: NotificationPriority = NotificationPriority.MEDIUM
    variables: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def render(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Render template with context variables"""
        subject = self.subject_template
        body = self.body_template

        # Replace variables
        for key, value in context.items():
            placeholder = f"{{{key}}}"
            subject = subject.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))

        return {
            "subject": subject,
            "body": body
        }


@dataclass
class NotificationRule:
    """Rule for intelligent notification routing"""
    rule_id: str
    name: str
    event: NotificationEvent
    conditions: Dict[str, Any]
    channels: List[NotificationChannel]
    priority: NotificationPriority
    enabled: bool = True
    rate_limit: Optional[int] = None  # Max notifications per hour
    quiet_hours: Optional[Dict[str, int]] = None  # {"start": 22, "end": 8}
    metadata: Dict[str, Any] = field(default_factory=dict)

    def matches(self, event: NotificationEvent, context: Dict[str, Any]) -> bool:
        """Check if rule matches event and context"""
        if not self.enabled:
            return False

        if event != self.event:
            return False

        # Check conditions
        for key, expected_value in self.conditions.items():
            actual_value = context.get(key)

            if isinstance(expected_value, dict):
                # Complex condition (e.g., {"operator": ">=", "value": 5})
                operator = expected_value.get("operator", "==")
                value = expected_value.get("value")

                if operator == "==" and actual_value != value:
                    return False
                elif operator == "!=" and actual_value == value:
                    return False
                elif operator == ">" and not (actual_value > value):
                    return False
                elif operator == ">=" and not (actual_value >= value):
                    return False
                elif operator == "<" and not (actual_value < value):
                    return False
                elif operator == "<=" and not (actual_value <= value):
                    return False
                elif operator == "in" and actual_value not in value:
                    return False
                elif operator == "contains" and value not in str(actual_value):
                    return False
            else:
                # Simple equality check
                if actual_value != expected_value:
                    return False

        return True

    def is_in_quiet_hours(self) -> bool:
        """Check if current time is in quiet hours"""
        if not self.quiet_hours:
            return False

        now = datetime.now(timezone.utc)
        current_hour = now.hour

        start = self.quiet_hours.get("start", 0)
        end = self.quiet_hours.get("end", 0)

        if start < end:
            return start <= current_hour < end
        else:
            # Crosses midnight
            return current_hour >= start or current_hour < end


@dataclass
class Notification:
    """Individual notification"""
    notification_id: str
    recipient: str
    channel: NotificationChannel
    event: NotificationEvent
    priority: NotificationPriority
    subject: str
    body: str
    status: NotificationStatus = NotificationStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "notification_id": self.notification_id,
            "recipient": self.recipient,
            "channel": self.channel.value,
            "event": self.event.value,
            "priority": self.priority.value,
            "subject": self.subject,
            "body": self.body,
            "status": self.status.value,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "error": self.error,
            "retry_count": self.retry_count
        }


class NotificationEnhancedSystem:
    """Enhanced notification system with intelligent routing"""

    def __init__(self):
        self.templates: Dict[str, NotificationTemplate] = {}
        self.rules: Dict[str, NotificationRule] = {}
        self.notifications: Dict[str, Notification] = {}
        self.channel_handlers: Dict[NotificationChannel, Callable] = {}
        self.rate_limits: Dict[str, List[datetime]] = defaultdict(list)

        # Initialize default templates
        self._initialize_default_templates()

    def _initialize_default_templates(self):
        """Initialize default notification templates"""
        # Review requested template
        self.add_template(NotificationTemplate(
            template_id="review_requested_email",
            name="Review Requested - Email",
            event=NotificationEvent.REVIEW_REQUESTED,
            subject_template="Code Review Request: {pr_title}",
            body_template="""
Hello {reviewer_name},

You have been requested to review a pull request:

PR: {pr_title}
Repository: {repository}
Author: {author}
URL: {pr_url}

Please review at your earliest convenience.

Best regards,
PR-Agent
            """.strip(),
            channel=NotificationChannel.EMAIL,
            priority=NotificationPriority.MEDIUM,
            variables=["reviewer_name", "pr_title", "repository", "author", "pr_url"]
        ))

        # Review completed template
        self.add_template(NotificationTemplate(
            template_id="review_completed_email",
            name="Review Completed - Email",
            event=NotificationEvent.REVIEW_COMPLETED,
            subject_template="Review Completed: {pr_title}",
            body_template="""
Hello {author_name},

Your pull request has been reviewed:

PR: {pr_title}
Reviewer: {reviewer}
Status: {status}
Comments: {comment_count}

View details: {pr_url}

Best regards,
PR-Agent
            """.strip(),
            channel=NotificationChannel.EMAIL,
            priority=NotificationPriority.MEDIUM,
            variables=["author_name", "pr_title", "reviewer", "status", "comment_count", "pr_url"]
        ))

        # SLA violation template
        self.add_template(NotificationTemplate(
            template_id="sla_violation_slack",
            name="SLA Violation - Slack",
            event=NotificationEvent.SLA_VIOLATION,
            subject_template="⚠️ SLA Violation Alert",
            body_template="""
*SLA Violation Detected*

PR: {pr_title}
Repository: {repository}
Metric: {metric}
Target: {target}
Actual: {actual}
Overdue: {overdue}

Action required: {pr_url}
            """.strip(),
            channel=NotificationChannel.SLACK,
            priority=NotificationPriority.URGENT,
            variables=["pr_title", "repository", "metric", "target", "actual", "overdue", "pr_url"]
        ))

    def add_template(self, template: NotificationTemplate):
        """Add notification template"""
        self.templates[template.template_id] = template

    def get_template(self, template_id: str) -> Optional[NotificationTemplate]:
        """Get notification template"""
        return self.templates.get(template_id)

    def list_templates(
        self,
        event: Optional[NotificationEvent] = None,
        channel: Optional[NotificationChannel] = None
    ) -> List[NotificationTemplate]:
        """List notification templates"""
        templates = list(self.templates.values())

        if event:
            templates = [t for t in templates if t.event == event]

        if channel:
            templates = [t for t in templates if t.channel == channel]

        return templates

    def add_rule(self, rule: NotificationRule):
        """Add notification rule"""
        self.rules[rule.rule_id] = rule

    def get_rule(self, rule_id: str) -> Optional[NotificationRule]:
        """Get notification rule"""
        return self.rules.get(rule_id)

    def list_rules(self, enabled_only: bool = False) -> List[NotificationRule]:
        """List notification rules"""
        rules = list(self.rules.values())

        if enabled_only:
            rules = [r for r in rules if r.enabled]

        return rules

    def register_channel_handler(
        self,
        channel: NotificationChannel,
        handler: Callable[[Notification], None]
    ):
        """Register handler for notification channel"""
        self.channel_handlers[channel] = handler

    def send_notification(
        self,
        notification_id: str,
        recipient: str,
        event: NotificationEvent,
        context: Dict[str, Any],
        channels: Optional[List[NotificationChannel]] = None,
        priority: Optional[NotificationPriority] = None
    ) -> List[Notification]:
        """Send notification with intelligent routing"""
        notifications = []

        # Find matching rules
        matching_rules = [
            rule for rule in self.rules.values()
            if rule.matches(event, context)
        ]

        # Determine channels and priority
        if not channels:
            if matching_rules:
                # Use channels from first matching rule
                channels = matching_rules[0].channels
                priority = priority or matching_rules[0].priority
            else:
                # Default to email
                channels = [NotificationChannel.EMAIL]
                priority = priority or NotificationPriority.MEDIUM

        # Check rate limits
        for rule in matching_rules:
            if rule.rate_limit and not self._check_rate_limit(rule.rule_id, rule.rate_limit):
                continue

            # Check quiet hours
            if rule.is_in_quiet_hours():
                continue

        # Send to each channel
        for channel in channels:
            # Find template for this channel and event
            template = self._find_template(event, channel)

            if template:
                # Render template
                rendered = template.render(context)
                subject = rendered["subject"]
                body = rendered["body"]
            else:
                # Use default message
                subject = f"{event.value}: {context.get('title', 'Notification')}"
                body = json.dumps(context, indent=2)

            # Create notification
            notification = Notification(
                notification_id=f"{notification_id}_{channel.value}",
                recipient=recipient,
                channel=channel,
                event=event,
                priority=priority,
                subject=subject,
                body=body,
                metadata=context
            )

            # Send notification
            self._send_notification(notification)
            notifications.append(notification)

        return notifications

    def _find_template(
        self,
        event: NotificationEvent,
        channel: NotificationChannel
    ) -> Optional[NotificationTemplate]:
        """Find template for event and channel"""
        for template in self.templates.values():
            if template.event == event and template.channel == channel:
                return template
        return None

    def _check_rate_limit(self, rule_id: str, limit: int) -> bool:
        """Check if rate limit is exceeded"""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=1)

        # Clean old entries
        self.rate_limits[rule_id] = [
            ts for ts in self.rate_limits[rule_id]
            if ts > cutoff
        ]

        # Check limit
        if len(self.rate_limits[rule_id]) >= limit:
            return False

        # Record this notification
        self.rate_limits[rule_id].append(now)
        return True

    def _send_notification(self, notification: Notification):
        """Send notification through channel"""
        self.notifications[notification.notification_id] = notification

        try:
            # Get channel handler
            handler = self.channel_handlers.get(notification.channel)

            if handler:
                # Call handler
                handler(notification)
                notification.status = NotificationStatus.SENT
                notification.sent_at = datetime.now(timezone.utc)
            else:
                # No handler registered
                notification.status = NotificationStatus.FAILED
                notification.error = f"No handler registered for channel: {notification.channel.value}"

        except Exception as e:
            notification.status = NotificationStatus.FAILED
            notification.error = str(e)

    def get_notification(self, notification_id: str) -> Optional[Notification]:
        """Get notification by ID"""
        return self.notifications.get(notification_id)

    def list_notifications(
        self,
        recipient: Optional[str] = None,
        status: Optional[NotificationStatus] = None,
        event: Optional[NotificationEvent] = None,
        limit: int = 100
    ) -> List[Notification]:
        """List notifications with filters"""
        notifications = list(self.notifications.values())

        if recipient:
            notifications = [n for n in notifications if n.recipient == recipient]

        if status:
            notifications = [n for n in notifications if n.status == status]

        if event:
            notifications = [n for n in notifications if n.event == event]

        # Sort by created_at descending
        notifications.sort(key=lambda n: n.created_at, reverse=True)

        return notifications[:limit]

    def retry_notification(self, notification_id: str) -> bool:
        """Retry failed notification"""
        notification = self.notifications.get(notification_id)

        if not notification:
            return False

        if notification.status != NotificationStatus.FAILED:
            return False

        if notification.retry_count >= notification.max_retries:
            return False

        # Increment retry count
        notification.retry_count += 1
        notification.status = NotificationStatus.PENDING
        notification.error = None

        # Retry sending
        self._send_notification(notification)

        return notification.status == NotificationStatus.SENT

    def cancel_notification(self, notification_id: str) -> bool:
        """Cancel pending notification"""
        notification = self.notifications.get(notification_id)

        if not notification:
            return False

        if notification.status != NotificationStatus.PENDING:
            return False

        notification.status = NotificationStatus.CANCELLED
        return True

    def get_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get notification statistics"""
        notifications = list(self.notifications.values())

        if start_date:
            notifications = [n for n in notifications if n.created_at >= start_date]

        if end_date:
            notifications = [n for n in notifications if n.created_at <= end_date]

        # Calculate statistics
        total = len(notifications)
        by_status = defaultdict(int)
        by_channel = defaultdict(int)
        by_event = defaultdict(int)
        by_priority = defaultdict(int)

        for notification in notifications:
            by_status[notification.status.value] += 1
            by_channel[notification.channel.value] += 1
            by_event[notification.event.value] += 1
            if notification.priority:
                by_priority[notification.priority.value] += 1

        return {
            "total": total,
            "by_status": dict(by_status),
            "by_channel": dict(by_channel),
            "by_event": dict(by_event),
            "by_priority": dict(by_priority),
            "success_rate": by_status[NotificationStatus.SENT.value] / total if total > 0 else 0,
            "failure_rate": by_status[NotificationStatus.FAILED.value] / total if total > 0 else 0
        }


# Singleton instance
_notification_system: Optional[NotificationEnhancedSystem] = None


def get_notification_system() -> NotificationEnhancedSystem:
    """Get singleton notification system instance"""
    global _notification_system
    if _notification_system is None:
        _notification_system = NotificationEnhancedSystem()
    return _notification_system
