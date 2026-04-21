"""
Webhook notification system for PR review events.

Supports multiple notification channels:
- Slack
- DingTalk (钉钉)
- WeCom (企业微信)
- Custom webhooks
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import aiohttp
from pr_agent.config_loader import get_settings


class NotificationChannel(str, Enum):
    """Supported notification channels."""
    SLACK = "slack"
    DINGTALK = "dingtalk"
    WECOM = "wecom"
    CUSTOM = "custom"


class NotificationEvent(str, Enum):
    """Notification event types."""
    REVIEW_STARTED = "review_started"
    REVIEW_COMPLETED = "review_completed"
    REVIEW_FAILED = "review_failed"
    PR_APPROVED = "pr_approved"
    PR_REJECTED = "pr_rejected"


class WebhookNotifier:
    """Webhook notification manager."""

    def __init__(self):
        self.settings = get_settings()
        self.enabled = self.settings.get("WEBHOOK.ENABLED", False)
        self.channels = self._load_channels()
        self.timeout = self.settings.get("WEBHOOK.TIMEOUT", 10)
        self.retry_count = self.settings.get("WEBHOOK.RETRY_COUNT", 3)

    def _load_channels(self) -> List[Dict[str, Any]]:
        """Load configured notification channels."""
        channels = []

        # Slack
        slack_url = self.settings.get("WEBHOOK.SLACK_URL")
        if slack_url:
            channels.append({
                "type": NotificationChannel.SLACK,
                "url": slack_url,
                "enabled": self.settings.get("WEBHOOK.SLACK_ENABLED", True)
            })

        # DingTalk
        dingtalk_url = self.settings.get("WEBHOOK.DINGTALK_URL")
        if dingtalk_url:
            channels.append({
                "type": NotificationChannel.DINGTALK,
                "url": dingtalk_url,
                "secret": self.settings.get("WEBHOOK.DINGTALK_SECRET"),
                "enabled": self.settings.get("WEBHOOK.DINGTALK_ENABLED", True)
            })

        # WeCom
        wecom_url = self.settings.get("WEBHOOK.WECOM_URL")
        if wecom_url:
            channels.append({
                "type": NotificationChannel.WECOM,
                "url": wecom_url,
                "enabled": self.settings.get("WEBHOOK.WECOM_ENABLED", True)
            })

        # Custom webhooks
        custom_urls = self.settings.get("WEBHOOK.CUSTOM_URLS", [])
        for url in custom_urls:
            channels.append({
                "type": NotificationChannel.CUSTOM,
                "url": url,
                "enabled": True
            })

        return [ch for ch in channels if ch.get("enabled", True)]

    async def notify(
        self,
        event: NotificationEvent,
        pr_data: Dict[str, Any],
        review_data: Optional[Dict[str, Any]] = None
    ):
        """Send notification to all configured channels."""
        if not self.enabled or not self.channels:
            return

        tasks = []
        for channel in self.channels:
            task = self._send_notification(channel, event, pr_data, review_data)
            tasks.append(task)

        # Send all notifications concurrently
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_notification(
        self,
        channel: Dict[str, Any],
        event: NotificationEvent,
        pr_data: Dict[str, Any],
        review_data: Optional[Dict[str, Any]]
    ):
        """Send notification to a specific channel."""
        channel_type = channel["type"]

        # Build message based on channel type
        if channel_type == NotificationChannel.SLACK:
            payload = self._build_slack_message(event, pr_data, review_data)
        elif channel_type == NotificationChannel.DINGTALK:
            payload = self._build_dingtalk_message(event, pr_data, review_data)
        elif channel_type == NotificationChannel.WECOM:
            payload = self._build_wecom_message(event, pr_data, review_data)
        else:
            payload = self._build_custom_message(event, pr_data, review_data)

        # Send with retry
        for attempt in range(self.retry_count):
            try:
                await self._send_webhook(channel["url"], payload)
                break
            except Exception as e:
                if attempt == self.retry_count - 1:
                    print(f"Failed to send notification to {channel_type}: {e}")
                else:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

    async def _send_webhook(self, url: str, payload: Dict[str, Any]):
        """Send HTTP POST request to webhook URL."""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                response.raise_for_status()

    def _build_slack_message(
        self,
        event: NotificationEvent,
        pr_data: Dict[str, Any],
        review_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build Slack message format."""
        color = self._get_event_color(event)
        title = self._get_event_title(event)

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": title
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Repository:*\n{pr_data.get('repository', 'N/A')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*PR:*\n#{pr_data.get('pr_number', 'N/A')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Author:*\n{pr_data.get('author', 'N/A')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Status:*\n{event.value}"
                    }
                ]
            }
        ]

        if pr_data.get("title"):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Title:*\n{pr_data['title']}"
                }
            })

        if pr_data.get("url"):
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View PR"
                        },
                        "url": pr_data["url"]
                    }
                ]
            })

        return {
            "attachments": [
                {
                    "color": color,
                    "blocks": blocks
                }
            ]
        }

    def _build_dingtalk_message(
        self,
        event: NotificationEvent,
        pr_data: Dict[str, Any],
        review_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build DingTalk message format."""
        title = self._get_event_title(event)

        text = f"### {title}\n\n"
        text += f"**仓库:** {pr_data.get('repository', 'N/A')}\n\n"
        text += f"**PR:** #{pr_data.get('pr_number', 'N/A')}\n\n"
        text += f"**作者:** {pr_data.get('author', 'N/A')}\n\n"
        text += f"**状态:** {event.value}\n\n"

        if pr_data.get("title"):
            text += f"**标题:** {pr_data['title']}\n\n"

        if pr_data.get("url"):
            text += f"[查看 PR]({pr_data['url']})"

        return {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": text
            }
        }

    def _build_wecom_message(
        self,
        event: NotificationEvent,
        pr_data: Dict[str, Any],
        review_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build WeCom (企业微信) message format."""
        title = self._get_event_title(event)

        content = f"{title}\n"
        content += f"仓库: {pr_data.get('repository', 'N/A')}\n"
        content += f"PR: #{pr_data.get('pr_number', 'N/A')}\n"
        content += f"作者: {pr_data.get('author', 'N/A')}\n"
        content += f"状态: {event.value}\n"

        if pr_data.get("title"):
            content += f"标题: {pr_data['title']}\n"

        if pr_data.get("url"):
            content += f"链接: {pr_data['url']}"

        return {
            "msgtype": "text",
            "text": {
                "content": content
            }
        }

    def _build_custom_message(
        self,
        event: NotificationEvent,
        pr_data: Dict[str, Any],
        review_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build generic message format for custom webhooks."""
        return {
            "event": event.value,
            "timestamp": datetime.now().isoformat(),
            "pr": pr_data,
            "review": review_data
        }

    def _get_event_color(self, event: NotificationEvent) -> str:
        """Get color for event type."""
        colors = {
            NotificationEvent.REVIEW_STARTED: "#36a64f",  # Green
            NotificationEvent.REVIEW_COMPLETED: "#2eb886",  # Green
            NotificationEvent.REVIEW_FAILED: "#ff0000",  # Red
            NotificationEvent.PR_APPROVED: "#00ff00",  # Bright green
            NotificationEvent.PR_REJECTED: "#ff6600",  # Orange
        }
        return colors.get(event, "#808080")  # Gray default

    def _get_event_title(self, event: NotificationEvent) -> str:
        """Get human-readable title for event."""
        titles = {
            NotificationEvent.REVIEW_STARTED: "🔄 PR Review Started",
            NotificationEvent.REVIEW_COMPLETED: "✅ PR Review Completed",
            NotificationEvent.REVIEW_FAILED: "❌ PR Review Failed",
            NotificationEvent.PR_APPROVED: "👍 PR Approved",
            NotificationEvent.PR_REJECTED: "👎 PR Rejected",
        }
        return titles.get(event, "PR Event")


# Global notifier instance
webhook_notifier = WebhookNotifier()


async def notify_review_started(pr_data: Dict[str, Any]):
    """Notify that PR review has started."""
    await webhook_notifier.notify(NotificationEvent.REVIEW_STARTED, pr_data)


async def notify_review_completed(pr_data: Dict[str, Any], review_data: Dict[str, Any]):
    """Notify that PR review has completed."""
    await webhook_notifier.notify(NotificationEvent.REVIEW_COMPLETED, pr_data, review_data)


async def notify_review_failed(pr_data: Dict[str, Any], error: str):
    """Notify that PR review has failed."""
    review_data = {"error": error}
    await webhook_notifier.notify(NotificationEvent.REVIEW_FAILED, pr_data, review_data)
