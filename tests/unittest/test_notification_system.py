"""Tests for notification system."""

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from pr_agent.notifications import (
    NotificationSystem,
    NotificationChannel,
    NotificationEvent,
    NotificationPriority,
    NotificationTemplate,
    NotificationPreference,
    Notification
)


@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary storage directory."""
    return tmp_path / "notifications"


@pytest.fixture
def notification_system(temp_storage):
    """Create a notification system instance."""
    return NotificationSystem(
        storage_path=temp_storage,
        smtp_host="smtp.example.com",
        smtp_user="test@example.com",
        smtp_password="password",
        slack_webhook="https://hooks.slack.com/test",
        dingtalk_webhook="https://oapi.dingtalk.com/test",
        wecom_webhook="https://qyapi.weixin.qq.com/test"
    )


class TestNotificationTemplate:
    """Test notification templates."""

    def test_template_creation(self):
        """Test creating a template."""
        template = NotificationTemplate(
            template_id="test_template",
            event=NotificationEvent.PR_CREATED,
            channel=NotificationChannel.EMAIL,
            subject_template="PR Created: {title}",
            body_template="A new PR was created: {title}"
        )

        assert template.template_id == "test_template"
        assert template.event == NotificationEvent.PR_CREATED
        assert template.channel == NotificationChannel.EMAIL

    def test_template_rendering(self):
        """Test rendering a template."""
        template = NotificationTemplate(
            template_id="test_template",
            event=NotificationEvent.PR_CREATED,
            channel=NotificationChannel.EMAIL,
            subject_template="PR Created: {title}",
            body_template="A new PR was created: {title} by {author}"
        )

        context = {"title": "Fix bug", "author": "Alice"}
        subject, body = template.render(context)

        assert subject == "PR Created: Fix bug"
        assert body == "A new PR was created: Fix bug by Alice"


class TestNotificationPreference:
    """Test notification preferences."""

    def test_preference_creation(self):
        """Test creating preferences."""
        pref = NotificationPreference(
            user_id="alice",
            email="alice@example.com",
            enabled_channels=[NotificationChannel.EMAIL],
            enabled_events=[NotificationEvent.REVIEW_ASSIGNED]
        )

        assert pref.user_id == "alice"
        assert pref.email == "alice@example.com"
        assert NotificationChannel.EMAIL in pref.enabled_channels

    def test_should_notify(self):
        """Test notification filtering."""
        pref = NotificationPreference(
            user_id="alice",
            email="alice@example.com",
            enabled_channels=[NotificationChannel.EMAIL],
            enabled_events=[NotificationEvent.REVIEW_ASSIGNED]
        )

        # Should notify
        assert pref.should_notify(
            NotificationEvent.REVIEW_ASSIGNED,
            NotificationChannel.EMAIL
        )

        # Wrong channel
        assert not pref.should_notify(
            NotificationEvent.REVIEW_ASSIGNED,
            NotificationChannel.SLACK
        )

        # Wrong event
        assert not pref.should_notify(
            NotificationEvent.PR_CREATED,
            NotificationChannel.EMAIL
        )

    def test_quiet_hours(self):
        """Test quiet hours filtering."""
        pref = NotificationPreference(
            user_id="alice",
            email="alice@example.com",
            enabled_channels=[NotificationChannel.EMAIL],
            enabled_events=[NotificationEvent.REVIEW_ASSIGNED],
            quiet_hours_start=22,
            quiet_hours_end=8
        )

        # Mock current hour
        with patch('pr_agent.notifications.notification_system.datetime') as mock_dt:
            # During quiet hours
            mock_dt.now.return_value = datetime(2024, 1, 1, 23, 0, tzinfo=timezone.utc)
            assert not pref.should_notify(
                NotificationEvent.REVIEW_ASSIGNED,
                NotificationChannel.EMAIL
            )

            # Outside quiet hours
            mock_dt.now.return_value = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
            assert pref.should_notify(
                NotificationEvent.REVIEW_ASSIGNED,
                NotificationChannel.EMAIL
            )


class TestNotification:
    """Test notification objects."""

    def test_notification_creation(self):
        """Test creating a notification."""
        notification = Notification(
            notification_id="test_123",
            event=NotificationEvent.REVIEW_ASSIGNED,
            channel=NotificationChannel.EMAIL,
            recipient="alice@example.com",
            subject="Review Assigned",
            body="You have been assigned a review"
        )

        assert notification.notification_id == "test_123"
        assert notification.event == NotificationEvent.REVIEW_ASSIGNED
        assert not notification.delivered
        assert notification.retry_count == 0

    def test_notification_to_dict(self):
        """Test converting notification to dict."""
        notification = Notification(
            notification_id="test_123",
            event=NotificationEvent.REVIEW_ASSIGNED,
            channel=NotificationChannel.EMAIL,
            recipient="alice@example.com",
            subject="Review Assigned",
            body="You have been assigned a review"
        )

        data = notification.to_dict()

        assert data['notification_id'] == "test_123"
        assert data['event'] == "review_assigned"
        assert data['channel'] == "email"
        assert data['recipient'] == "alice@example.com"


class TestNotificationSystem:
    """Test notification system."""

    def test_system_initialization(self, notification_system):
        """Test system initialization."""
        assert notification_system.storage_path.exists()
        assert len(notification_system.templates) > 0  # Default templates

    def test_register_template(self, notification_system):
        """Test registering a template."""
        template = NotificationTemplate(
            template_id="custom_template",
            event=NotificationEvent.PR_CREATED,
            channel=NotificationChannel.EMAIL,
            subject_template="Custom: {title}",
            body_template="Custom body: {title}"
        )

        notification_system.register_template(template)

        assert "custom_template" in notification_system.templates
        assert notification_system.templates["custom_template"] == template

    def test_set_preference(self, notification_system):
        """Test setting user preferences."""
        pref = NotificationPreference(
            user_id="alice",
            email="alice@example.com",
            enabled_channels=[NotificationChannel.EMAIL],
            enabled_events=[NotificationEvent.REVIEW_ASSIGNED]
        )

        notification_system.set_preference(pref)

        assert "alice" in notification_system.preferences
        assert notification_system.get_preference("alice") == pref

    def test_get_recipient_address(self, notification_system):
        """Test getting recipient address for channel."""
        pref = NotificationPreference(
            user_id="alice",
            email="alice@example.com",
            slack_id="U123456"
        )

        assert notification_system._get_recipient_address(
            pref, NotificationChannel.EMAIL
        ) == "alice@example.com"

        assert notification_system._get_recipient_address(
            pref, NotificationChannel.SLACK
        ) == "U123456"

    @patch('pr_agent.notifications.notification_system.smtplib.SMTP')
    def test_send_email(self, mock_smtp, notification_system):
        """Test sending email notification."""
        notification = Notification(
            notification_id="test_123",
            event=NotificationEvent.REVIEW_ASSIGNED,
            channel=NotificationChannel.EMAIL,
            recipient="alice@example.com",
            subject="Review Assigned",
            body="You have been assigned a review"
        )

        # Mock SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        notification_system._send_email(notification)

        # Verify SMTP calls
        mock_smtp.assert_called_once_with("smtp.example.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@example.com", "password")
        mock_server.send_message.assert_called_once()

    @patch('pr_agent.notifications.notification_system.requests.post')
    def test_send_slack(self, mock_post, notification_system):
        """Test sending Slack notification."""
        notification = Notification(
            notification_id="test_123",
            event=NotificationEvent.REVIEW_ASSIGNED,
            channel=NotificationChannel.SLACK,
            recipient="U123456",
            subject="Review Assigned",
            body="You have been assigned a review"
        )

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        notification_system._send_slack(notification)

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://hooks.slack.com/test"

    @patch('pr_agent.notifications.notification_system.requests.post')
    def test_send_dingtalk(self, mock_post, notification_system):
        """Test sending DingTalk notification."""
        notification = Notification(
            notification_id="test_123",
            event=NotificationEvent.REVIEW_ASSIGNED,
            channel=NotificationChannel.DINGTALK,
            recipient="13800138000",
            subject="Review Assigned",
            body="You have been assigned a review"
        )

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        notification_system._send_dingtalk(notification)

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://oapi.dingtalk.com/test"

    @patch('pr_agent.notifications.notification_system.requests.post')
    def test_send_wecom(self, mock_post, notification_system):
        """Test sending WeChat Work notification."""
        notification = Notification(
            notification_id="test_123",
            event=NotificationEvent.REVIEW_ASSIGNED,
            channel=NotificationChannel.WECOM,
            recipient="alice",
            subject="Review Assigned",
            body="You have been assigned a review"
        )

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        notification_system._send_wecom(notification)

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://qyapi.weixin.qq.com/test"

    def test_custom_handler(self, notification_system):
        """Test custom notification handler."""
        handler_called = []

        def custom_handler(notification):
            handler_called.append(notification)

        notification_system.register_handler(NotificationChannel.WEBHOOK, custom_handler)

        notification = Notification(
            notification_id="test_123",
            event=NotificationEvent.REVIEW_ASSIGNED,
            channel=NotificationChannel.WEBHOOK,
            recipient="https://example.com/webhook",
            subject="Review Assigned",
            body="You have been assigned a review"
        )

        notification_system._send_notification(notification)

        assert len(handler_called) == 1
        assert handler_called[0] == notification

    @patch('pr_agent.notifications.notification_system.smtplib.SMTP')
    def test_notify(self, mock_smtp, notification_system):
        """Test sending notifications to multiple recipients."""
        # Setup preferences
        pref1 = NotificationPreference(
            user_id="alice",
            email="alice@example.com",
            enabled_channels=[NotificationChannel.EMAIL],
            enabled_events=[NotificationEvent.REVIEW_ASSIGNED]
        )
        pref2 = NotificationPreference(
            user_id="bob",
            email="bob@example.com",
            enabled_channels=[NotificationChannel.EMAIL],
            enabled_events=[NotificationEvent.REVIEW_ASSIGNED]
        )

        notification_system.set_preference(pref1)
        notification_system.set_preference(pref2)

        # Mock SMTP
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        # Send notifications
        context = {
            "reviewer_name": "Alice",
            "pr_number": "123",
            "repository": "org/repo",
            "pr_title": "Fix bug",
            "pr_author": "Charlie",
            "file_count": 5,
            "pr_url": "https://example.com/pr/123"
        }

        notifications = notification_system.notify(
            event=NotificationEvent.REVIEW_ASSIGNED,
            recipients=["alice", "bob"],
            context=context
        )

        assert len(notifications) == 2
        assert all(n.delivered for n in notifications)

    def test_notification_history(self, notification_system):
        """Test notification history."""
        notification = Notification(
            notification_id="test_123",
            event=NotificationEvent.REVIEW_ASSIGNED,
            channel=NotificationChannel.EMAIL,
            recipient="alice@example.com",
            subject="Review Assigned",
            body="You have been assigned a review",
            metadata={"user_id": "alice"}
        )
        notification.delivered = True

        notification_system.notification_history.append(notification)

        history = notification_system.get_notification_history(user_id="alice")
        assert len(history) == 1
        assert history[0].notification_id == "test_123"

    def test_state_persistence(self, temp_storage):
        """Test saving and loading state."""
        # Create system and add data
        system1 = NotificationSystem(storage_path=temp_storage)

        template = NotificationTemplate(
            template_id="custom_template",
            event=NotificationEvent.PR_CREATED,
            channel=NotificationChannel.EMAIL,
            subject_template="Custom: {title}",
            body_template="Custom body"
        )
        system1.register_template(template)

        pref = NotificationPreference(
            user_id="alice",
            email="alice@example.com",
            enabled_channels=[NotificationChannel.EMAIL],
            enabled_events=[NotificationEvent.REVIEW_ASSIGNED]
        )
        system1.set_preference(pref)

        # Create new system and verify data loaded
        system2 = NotificationSystem(storage_path=temp_storage)

        assert "custom_template" in system2.templates
        assert "alice" in system2.preferences
        assert system2.preferences["alice"].email == "alice@example.com"

    def test_retry_failed_notifications(self, notification_system):
        """Test retrying failed notifications."""
        notification = Notification(
            notification_id="test_123",
            event=NotificationEvent.REVIEW_ASSIGNED,
            channel=NotificationChannel.EMAIL,
            recipient="alice@example.com",
            subject="Review Assigned",
            body="You have been assigned a review"
        )
        notification.error = "Connection failed"
        notification.retry_count = 1

        notification_system.notifications.append(notification)

        with patch.object(notification_system, '_send_notification') as mock_send:
            notification_system.retry_failed()

            mock_send.assert_called_once_with(notification)
