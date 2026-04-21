"""
Notification system for PR-Agent.

Supports multiple notification channels for PR review events.
"""

from pr_agent.notifications.webhook import (
    webhook_notifier,
    notify_review_started,
    notify_review_completed,
    notify_review_failed,
    NotificationEvent,
    NotificationChannel,
)

__all__ = [
    "webhook_notifier",
    "notify_review_started",
    "notify_review_completed",
    "notify_review_failed",
    "NotificationEvent",
    "NotificationChannel",
]
