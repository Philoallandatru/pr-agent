"""
Code Review Notification System

Sends notifications through multiple channels when review events occur.
"""

import json
import smtplib
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from urllib.parse import urljoin
import requests


class NotificationChannel(Enum):
    """Notification delivery channels."""
    EMAIL = "email"
    SLACK = "slack"
    DINGTALK = "dingtalk"
    WECOM = "wecom"  # WeChat Work (企业微信)
    WEBHOOK = "webhook"


class NotificationEvent(Enum):
    """Types of review events that trigger notifications."""
    PR_CREATED = "pr_created"
    PR_UPDATED = "pr_updated"
    REVIEW_ASSIGNED = "review_assigned"
    REVIEW_COMPLETED = "review_completed"
    REVIEW_APPROVED = "review_approved"
    REVIEW_REJECTED = "review_rejected"
    COMMENT_ADDED = "comment_added"
    ISSUE_FOUND = "issue_found"


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class NotificationTemplate:
    """Template for notification messages."""
    template_id: str
    event: NotificationEvent
    channel: NotificationChannel
    subject_template: str
    body_template: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def render(self, context: Dict[str, Any]) -> tuple[str, str]:
        """Render template with context data."""
        subject = self.subject_template.format(**context)
        body = self.body_template.format(**context)
        return subject, body


@dataclass
class NotificationPreference:
    """User notification preferences."""
    user_id: str
    email: Optional[str] = None
    slack_id: Optional[str] = None
    dingtalk_id: Optional[str] = None
    wecom_id: Optional[str] = None
    enabled_channels: List[NotificationChannel] = field(default_factory=list)
    enabled_events: List[NotificationEvent] = field(default_factory=list)
    quiet_hours_start: Optional[int] = None  # Hour (0-23)
    quiet_hours_end: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def should_notify(self, event: NotificationEvent, channel: NotificationChannel) -> bool:
        """Check if user should receive notification."""
        if channel not in self.enabled_channels:
            return False
        if event not in self.enabled_events:
            return False

        # Check quiet hours
        if self.quiet_hours_start is not None and self.quiet_hours_end is not None:
            current_hour = datetime.now(timezone.utc).hour

            # Handle quiet hours that span midnight (e.g., 22-8)
            if self.quiet_hours_start > self.quiet_hours_end:
                # Quiet hours span midnight
                if current_hour >= self.quiet_hours_start or current_hour < self.quiet_hours_end:
                    return False
            else:
                # Normal quiet hours (e.g., 1-5)
                if self.quiet_hours_start <= current_hour < self.quiet_hours_end:
                    return False

        return True


@dataclass
class Notification:
    """A notification to be sent."""
    notification_id: str
    event: NotificationEvent
    channel: NotificationChannel
    recipient: str
    subject: str
    body: str
    priority: NotificationPriority = NotificationPriority.NORMAL
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: Optional[datetime] = None
    delivered: bool = False
    error: Optional[str] = None
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['event'] = self.event.value
        data['channel'] = self.channel.value
        data['priority'] = self.priority.value
        data['created_at'] = self.created_at.isoformat()
        data['sent_at'] = self.sent_at.isoformat() if self.sent_at else None
        return data


class NotificationSystem:
    """Manages notification delivery across multiple channels."""

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        slack_webhook: Optional[str] = None,
        dingtalk_webhook: Optional[str] = None,
        wecom_webhook: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: int = 60
    ):
        self.storage_path = storage_path or Path.home() / ".pr-agent" / "notifications"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # SMTP configuration
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password

        # Webhook URLs
        self.slack_webhook = slack_webhook
        self.dingtalk_webhook = dingtalk_webhook
        self.wecom_webhook = wecom_webhook

        # Retry configuration
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Storage
        self.templates: Dict[str, NotificationTemplate] = {}
        self.preferences: Dict[str, NotificationPreference] = {}
        self.notifications: List[Notification] = []
        self.notification_history: List[Notification] = []

        # Custom handlers
        self.custom_handlers: Dict[NotificationChannel, Callable] = {}

        self._load_state()
        self._register_default_templates()

    def _load_state(self):
        """Load state from disk."""
        state_file = self.storage_path / "state.json"
        if not state_file.exists():
            return

        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Load templates
            for template_data in data.get('templates', []):
                template = NotificationTemplate(
                    template_id=template_data['template_id'],
                    event=NotificationEvent(template_data['event']),
                    channel=NotificationChannel(template_data['channel']),
                    subject_template=template_data['subject_template'],
                    body_template=template_data['body_template'],
                    metadata=template_data.get('metadata', {})
                )
                self.templates[template.template_id] = template

            # Load preferences
            for pref_data in data.get('preferences', []):
                pref = NotificationPreference(
                    user_id=pref_data['user_id'],
                    email=pref_data.get('email'),
                    slack_id=pref_data.get('slack_id'),
                    dingtalk_id=pref_data.get('dingtalk_id'),
                    wecom_id=pref_data.get('wecom_id'),
                    enabled_channels=[NotificationChannel(c) for c in pref_data.get('enabled_channels', [])],
                    enabled_events=[NotificationEvent(e) for e in pref_data.get('enabled_events', [])],
                    quiet_hours_start=pref_data.get('quiet_hours_start'),
                    quiet_hours_end=pref_data.get('quiet_hours_end'),
                    metadata=pref_data.get('metadata', {})
                )
                self.preferences[pref.user_id] = pref

        except Exception as e:
            print(f"Failed to load notification state: {e}")

    def _save_state(self):
        """Save state to disk."""
        state_file = self.storage_path / "state.json"

        data = {
            'templates': [
                {
                    'template_id': t.template_id,
                    'event': t.event.value,
                    'channel': t.channel.value,
                    'subject_template': t.subject_template,
                    'body_template': t.body_template,
                    'metadata': t.metadata
                }
                for t in self.templates.values()
            ],
            'preferences': [
                {
                    'user_id': p.user_id,
                    'email': p.email,
                    'slack_id': p.slack_id,
                    'dingtalk_id': p.dingtalk_id,
                    'wecom_id': p.wecom_id,
                    'enabled_channels': [c.value for c in p.enabled_channels],
                    'enabled_events': [e.value for e in p.enabled_events],
                    'quiet_hours_start': p.quiet_hours_start,
                    'quiet_hours_end': p.quiet_hours_end,
                    'metadata': p.metadata
                }
                for p in self.preferences.values()
            ]
        }

        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def _register_default_templates(self):
        """Register default notification templates."""
        # Email templates
        self.register_template(NotificationTemplate(
            template_id="email_review_assigned",
            event=NotificationEvent.REVIEW_ASSIGNED,
            channel=NotificationChannel.EMAIL,
            subject_template="Code Review Assigned: {pr_title}",
            body_template="""Hi {reviewer_name},

You have been assigned to review pull request #{pr_number} in {repository}.

Title: {pr_title}
Author: {pr_author}
Files: {file_count} files changed

View PR: {pr_url}

Best regards,
PR Agent
"""
        ))

        # Slack templates
        self.register_template(NotificationTemplate(
            template_id="slack_review_assigned",
            event=NotificationEvent.REVIEW_ASSIGNED,
            channel=NotificationChannel.SLACK,
            subject_template="",
            body_template="""{{
    "text": "Code Review Assigned",
    "blocks": [
        {{
            "type": "section",
            "text": {{
                "type": "mrkdwn",
                "text": "*Code Review Assigned*\\n<@{slack_id}> You have been assigned to review PR #{pr_number}"
            }}
        }},
        {{
            "type": "section",
            "fields": [
                {{"type": "mrkdwn", "text": "*Repository:*\\n{repository}"}},
                {{"type": "mrkdwn", "text": "*Author:*\\n{pr_author}"}},
                {{"type": "mrkdwn", "text": "*Title:*\\n{pr_title}"}},
                {{"type": "mrkdwn", "text": "*Files:*\\n{file_count} changed"}}
            ]
        }},
        {{
            "type": "actions",
            "elements": [
                {{
                    "type": "button",
                    "text": {{"type": "plain_text", "text": "View PR"}},
                    "url": "{pr_url}"
                }}
            ]
        }}
    ]
}}"""
        ))

    def register_template(self, template: NotificationTemplate):
        """Register a notification template."""
        self.templates[template.template_id] = template
        self._save_state()

    def set_preference(self, preference: NotificationPreference):
        """Set user notification preferences."""
        self.preferences[preference.user_id] = preference
        self._save_state()

    def get_preference(self, user_id: str) -> Optional[NotificationPreference]:
        """Get user notification preferences."""
        return self.preferences.get(user_id)

    def register_handler(self, channel: NotificationChannel, handler: Callable):
        """Register a custom notification handler."""
        self.custom_handlers[channel] = handler

    def notify(
        self,
        event: NotificationEvent,
        recipients: List[str],
        context: Dict[str, Any],
        priority: NotificationPriority = NotificationPriority.NORMAL,
        channels: Optional[List[NotificationChannel]] = None
    ) -> List[Notification]:
        """Send notifications to recipients."""
        notifications = []

        for recipient in recipients:
            pref = self.get_preference(recipient)
            if not pref:
                continue

            # Determine channels to use
            target_channels = channels or pref.enabled_channels

            for channel in target_channels:
                # Check if user wants this notification
                if not pref.should_notify(event, channel):
                    continue

                # Find template
                template_id = f"{channel.value}_{event.value}"
                template = self.templates.get(template_id)
                if not template:
                    continue

                # Get recipient address for channel
                recipient_address = self._get_recipient_address(pref, channel)
                if not recipient_address:
                    continue

                # Render template
                try:
                    subject, body = template.render(context)
                except Exception as e:
                    print(f"Failed to render template {template_id}: {e}")
                    continue

                # Create notification
                notification = Notification(
                    notification_id=f"{event.value}_{recipient}_{channel.value}_{int(time.time())}",
                    event=event,
                    channel=channel,
                    recipient=recipient_address,
                    subject=subject,
                    body=body,
                    priority=priority,
                    metadata=context
                )

                # Send notification
                self._send_notification(notification)
                notifications.append(notification)

        return notifications

    def _get_recipient_address(self, pref: NotificationPreference, channel: NotificationChannel) -> Optional[str]:
        """Get recipient address for a channel."""
        if channel == NotificationChannel.EMAIL:
            return pref.email
        elif channel == NotificationChannel.SLACK:
            return pref.slack_id
        elif channel == NotificationChannel.DINGTALK:
            return pref.dingtalk_id
        elif channel == NotificationChannel.WECOM:
            return pref.wecom_id
        return None

    def _send_notification(self, notification: Notification):
        """Send a notification through its channel."""
        try:
            # Check custom handlers first
            if notification.channel in self.custom_handlers:
                self.custom_handlers[notification.channel](notification)
            elif notification.channel == NotificationChannel.EMAIL:
                self._send_email(notification)
            elif notification.channel == NotificationChannel.SLACK:
                self._send_slack(notification)
            elif notification.channel == NotificationChannel.DINGTALK:
                self._send_dingtalk(notification)
            elif notification.channel == NotificationChannel.WECOM:
                self._send_wecom(notification)
            elif notification.channel == NotificationChannel.WEBHOOK:
                self._send_webhook(notification)
            else:
                raise ValueError(f"Unsupported channel: {notification.channel}")

            notification.delivered = True
            notification.sent_at = datetime.now(timezone.utc)

        except Exception as e:
            notification.error = str(e)
            notification.retry_count += 1

            # Retry if not exceeded max retries
            if notification.retry_count < self.max_retries:
                self.notifications.append(notification)
            else:
                self.notification_history.append(notification)

    def _send_email(self, notification: Notification):
        """Send email notification."""
        if not all([self.smtp_host, self.smtp_user, self.smtp_password]):
            raise ValueError("SMTP not configured")

        msg = MIMEMultipart()
        msg['From'] = self.smtp_user
        msg['To'] = notification.recipient
        msg['Subject'] = notification.subject

        msg.attach(MIMEText(notification.body, 'plain'))

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)

    def _send_slack(self, notification: Notification):
        """Send Slack notification."""
        if not self.slack_webhook:
            raise ValueError("Slack webhook not configured")

        # Parse body as JSON if it looks like JSON
        if notification.body.strip().startswith('{'):
            payload = json.loads(notification.body)
        else:
            payload = {
                "text": notification.subject,
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": notification.body
                        }
                    }
                ]
            }

        response = requests.post(self.slack_webhook, json=payload, timeout=10)
        response.raise_for_status()

    def _send_dingtalk(self, notification: Notification):
        """Send DingTalk notification."""
        if not self.dingtalk_webhook:
            raise ValueError("DingTalk webhook not configured")

        payload = {
            "msgtype": "text",
            "text": {
                "content": f"{notification.subject}\n\n{notification.body}"
            },
            "at": {
                "atMobiles": [notification.recipient],
                "isAtAll": False
            }
        }

        response = requests.post(self.dingtalk_webhook, json=payload, timeout=10)
        response.raise_for_status()

    def _send_wecom(self, notification: Notification):
        """Send WeChat Work notification."""
        if not self.wecom_webhook:
            raise ValueError("WeChat Work webhook not configured")

        payload = {
            "msgtype": "text",
            "text": {
                "content": f"{notification.subject}\n\n{notification.body}",
                "mentioned_list": [notification.recipient]
            }
        }

        response = requests.post(self.wecom_webhook, json=payload, timeout=10)
        response.raise_for_status()

    def _send_webhook(self, notification: Notification):
        """Send generic webhook notification."""
        webhook_url = notification.metadata.get('webhook_url')
        if not webhook_url:
            raise ValueError("Webhook URL not provided")

        payload = notification.to_dict()
        response = requests.post(webhook_url, json=payload, timeout=10)
        response.raise_for_status()

    def retry_failed(self):
        """Retry failed notifications."""
        to_retry = self.notifications[:]
        self.notifications.clear()

        for notification in to_retry:
            time.sleep(self.retry_delay)
            self._send_notification(notification)

    def get_notification_history(
        self,
        user_id: Optional[str] = None,
        event: Optional[NotificationEvent] = None,
        limit: int = 100
    ) -> List[Notification]:
        """Get notification history."""
        history = self.notification_history

        if user_id:
            history = [n for n in history if n.metadata.get('user_id') == user_id]

        if event:
            history = [n for n in history if n.event == event]

        return history[-limit:]


# Singleton instance
_notification_system = None


def get_notification_system() -> NotificationSystem:
    """Get the global notification system instance."""
    global _notification_system
    if _notification_system is None:
        _notification_system = NotificationSystem()
    return _notification_system
