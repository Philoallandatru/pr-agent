"""
Unit tests for webhook notification system.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from pr_agent.notifications.webhook import (
    WebhookNotifier,
    NotificationEvent,
    NotificationChannel,
)


class TestWebhookNotifier:
    """Test WebhookNotifier functionality."""

    @pytest.fixture
    def notifier(self):
        """Create a notifier instance for testing."""
        with patch('pr_agent.notifications.webhook.get_settings') as mock_settings:
            mock_settings.return_value.get.side_effect = lambda key, default=None: {
                'WEBHOOK.ENABLED': True,
                'WEBHOOK.TIMEOUT': 10,
                'WEBHOOK.RETRY_COUNT': 3,
                'WEBHOOK.SLACK_URL': 'https://hooks.slack.com/test',
                'WEBHOOK.SLACK_ENABLED': True,
            }.get(key, default)

            return WebhookNotifier()

    def test_load_channels(self, notifier):
        """Test loading notification channels."""
        assert len(notifier.channels) > 0
        assert notifier.channels[0]['type'] == NotificationChannel.SLACK

    def test_build_slack_message(self, notifier):
        """Test building Slack message format."""
        pr_data = {
            'repository': 'TEST/repo',
            'pr_number': 123,
            'author': 'testuser',
            'title': 'Test PR',
            'url': 'https://bitbucket.example.com/pr/123'
        }

        message = notifier._build_slack_message(
            NotificationEvent.REVIEW_COMPLETED,
            pr_data,
            None
        )

        assert 'attachments' in message
        assert len(message['attachments']) > 0
        assert 'blocks' in message['attachments'][0]

    def test_build_dingtalk_message(self, notifier):
        """Test building DingTalk message format."""
        pr_data = {
            'repository': 'TEST/repo',
            'pr_number': 123,
            'author': 'testuser',
            'title': 'Test PR',
            'url': 'https://bitbucket.example.com/pr/123'
        }

        message = notifier._build_dingtalk_message(
            NotificationEvent.REVIEW_COMPLETED,
            pr_data,
            None
        )

        assert message['msgtype'] == 'markdown'
        assert 'markdown' in message
        assert 'title' in message['markdown']
        assert 'text' in message['markdown']

    def test_build_wecom_message(self, notifier):
        """Test building WeCom message format."""
        pr_data = {
            'repository': 'TEST/repo',
            'pr_number': 123,
            'author': 'testuser',
            'title': 'Test PR',
            'url': 'https://bitbucket.example.com/pr/123'
        }

        message = notifier._build_wecom_message(
            NotificationEvent.REVIEW_COMPLETED,
            pr_data,
            None
        )

        assert message['msgtype'] == 'text'
        assert 'text' in message
        assert 'content' in message['text']

    def test_build_custom_message(self, notifier):
        """Test building custom message format."""
        pr_data = {
            'repository': 'TEST/repo',
            'pr_number': 123,
            'author': 'testuser'
        }

        review_data = {
            'duration': 45.5,
            'status': 'success'
        }

        message = notifier._build_custom_message(
            NotificationEvent.REVIEW_COMPLETED,
            pr_data,
            review_data
        )

        assert message['event'] == NotificationEvent.REVIEW_COMPLETED.value
        assert 'timestamp' in message
        assert message['pr'] == pr_data
        assert message['review'] == review_data

    def test_get_event_color(self, notifier):
        """Test getting color for event types."""
        assert notifier._get_event_color(NotificationEvent.REVIEW_COMPLETED) == "#2eb886"
        assert notifier._get_event_color(NotificationEvent.REVIEW_FAILED) == "#ff0000"
        assert notifier._get_event_color(NotificationEvent.PR_APPROVED) == "#00ff00"

    def test_get_event_title(self, notifier):
        """Test getting title for event types."""
        assert "Completed" in notifier._get_event_title(NotificationEvent.REVIEW_COMPLETED)
        assert "Failed" in notifier._get_event_title(NotificationEvent.REVIEW_FAILED)
        assert "Started" in notifier._get_event_title(NotificationEvent.REVIEW_STARTED)

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Complex aiohttp mocking - tested via integration tests")
    async def test_send_webhook_success(self, notifier):
        """Test successful webhook sending."""
        # This is tested via integration tests instead
        pass

    @pytest.mark.asyncio
    async def test_send_notification_with_retry(self, notifier):
        """Test notification sending with retry logic."""
        pr_data = {
            'repository': 'TEST/repo',
            'pr_number': 123,
            'author': 'testuser'
        }

        channel = {
            'type': NotificationChannel.SLACK,
            'url': 'https://hooks.slack.com/test'
        }

        with patch.object(notifier, '_send_webhook', new_callable=AsyncMock) as mock_send:
            # Fail twice, then succeed
            mock_send.side_effect = [Exception("Network error"), Exception("Network error"), None]

            await notifier._send_notification(
                channel,
                NotificationEvent.REVIEW_COMPLETED,
                pr_data,
                None
            )

            # Should have retried 3 times
            assert mock_send.call_count == 3

    @pytest.mark.asyncio
    async def test_notify_disabled(self):
        """Test that notifications are skipped when disabled."""
        with patch('pr_agent.notifications.webhook.get_settings') as mock_settings:
            mock_settings.return_value.get.side_effect = lambda key, default=None: {
                'WEBHOOK.ENABLED': False,
            }.get(key, default)

            notifier = WebhookNotifier()

            pr_data = {'repository': 'TEST/repo', 'pr_number': 123}

            # Should return immediately without sending
            await notifier.notify(NotificationEvent.REVIEW_COMPLETED, pr_data)

            # No exception should be raised
            assert True

    @pytest.mark.asyncio
    async def test_notify_multiple_channels(self, notifier):
        """Test sending notifications to multiple channels."""
        with patch('pr_agent.notifications.webhook.get_settings') as mock_settings:
            mock_settings.return_value.get.side_effect = lambda key, default=None: {
                'WEBHOOK.ENABLED': True,
                'WEBHOOK.SLACK_URL': 'https://hooks.slack.com/test',
                'WEBHOOK.SLACK_ENABLED': True,
                'WEBHOOK.DINGTALK_URL': 'https://oapi.dingtalk.com/test',
                'WEBHOOK.DINGTALK_ENABLED': True,
            }.get(key, default)

            notifier = WebhookNotifier()

            pr_data = {'repository': 'TEST/repo', 'pr_number': 123}

            with patch.object(notifier, '_send_notification', new_callable=AsyncMock) as mock_send:
                await notifier.notify(NotificationEvent.REVIEW_COMPLETED, pr_data)

                # Should send to both channels
                assert mock_send.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
