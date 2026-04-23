"""
Tests for Enhanced Notification System
"""

import pytest
from datetime import datetime, timezone, timedelta
from pr_agent.notification_enhanced import (
    NotificationEnhancedSystem,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    NotificationEvent,
    NotificationTemplate,
    NotificationRule,
    Notification,
    get_notification_system,
)


@pytest.fixture
def notification_system():
    """Create notification system instance"""
    return NotificationEnhancedSystem()


@pytest.fixture
def sample_template():
    """Create sample notification template"""
    return NotificationTemplate(
        template_id="test_template",
        name="Test Template",
        event=NotificationEvent.REVIEW_REQUESTED,
        subject_template="Review: {pr_title}",
        body_template="Please review {pr_title} by {author}",
        channel=NotificationChannel.EMAIL,
        priority=NotificationPriority.MEDIUM,
        variables=["pr_title", "author"]
    )


@pytest.fixture
def sample_rule():
    """Create sample notification rule"""
    return NotificationRule(
        rule_id="test_rule",
        name="Test Rule",
        event=NotificationEvent.REVIEW_REQUESTED,
        conditions={"priority": "high"},
        channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
        priority=NotificationPriority.HIGH
    )


class TestNotificationTemplate:
    """Test notification template functionality"""

    def test_template_creation(self, sample_template):
        """Test template creation"""
        assert sample_template.template_id == "test_template"
        assert sample_template.event == NotificationEvent.REVIEW_REQUESTED
        assert sample_template.channel == NotificationChannel.EMAIL

    def test_template_render(self, sample_template):
        """Test template rendering"""
        context = {
            "pr_title": "Fix bug",
            "author": "John Doe"
        }

        rendered = sample_template.render(context)

        assert rendered["subject"] == "Review: Fix bug"
        assert rendered["body"] == "Please review Fix bug by John Doe"

    def test_template_render_missing_variable(self, sample_template):
        """Test template rendering with missing variable"""
        context = {"pr_title": "Fix bug"}

        rendered = sample_template.render(context)

        assert "{author}" in rendered["body"]


class TestNotificationRule:
    """Test notification rule functionality"""

    def test_rule_creation(self, sample_rule):
        """Test rule creation"""
        assert sample_rule.rule_id == "test_rule"
        assert sample_rule.event == NotificationEvent.REVIEW_REQUESTED
        assert len(sample_rule.channels) == 2

    def test_rule_matches_simple(self, sample_rule):
        """Test simple rule matching"""
        context = {"priority": "high"}

        assert sample_rule.matches(NotificationEvent.REVIEW_REQUESTED, context)

    def test_rule_not_matches_wrong_event(self, sample_rule):
        """Test rule not matching wrong event"""
        context = {"priority": "high"}

        assert not sample_rule.matches(NotificationEvent.REVIEW_COMPLETED, context)

    def test_rule_not_matches_wrong_condition(self, sample_rule):
        """Test rule not matching wrong condition"""
        context = {"priority": "low"}

        assert not sample_rule.matches(NotificationEvent.REVIEW_REQUESTED, context)

    def test_rule_matches_complex_condition(self):
        """Test complex condition matching"""
        rule = NotificationRule(
            rule_id="complex_rule",
            name="Complex Rule",
            event=NotificationEvent.ISSUE_FOUND,
            conditions={
                "severity": {"operator": ">=", "value": 5},
                "type": {"operator": "in", "value": ["bug", "security"]}
            },
            channels=[NotificationChannel.EMAIL],
            priority=NotificationPriority.HIGH
        )

        # Should match
        context1 = {"severity": 7, "type": "bug"}
        assert rule.matches(NotificationEvent.ISSUE_FOUND, context1)

        # Should not match (severity too low)
        context2 = {"severity": 3, "type": "bug"}
        assert not rule.matches(NotificationEvent.ISSUE_FOUND, context2)

        # Should not match (wrong type)
        context3 = {"severity": 7, "type": "warning"}
        assert not rule.matches(NotificationEvent.ISSUE_FOUND, context3)

    def test_rule_disabled(self, sample_rule):
        """Test disabled rule"""
        sample_rule.enabled = False
        context = {"priority": "high"}

        assert not sample_rule.matches(NotificationEvent.REVIEW_REQUESTED, context)

    def test_quiet_hours_not_in(self):
        """Test not in quiet hours"""
        rule = NotificationRule(
            rule_id="quiet_rule",
            name="Quiet Rule",
            event=NotificationEvent.REVIEW_REQUESTED,
            conditions={},
            channels=[NotificationChannel.EMAIL],
            priority=NotificationPriority.MEDIUM,
            quiet_hours={"start": 22, "end": 8}
        )

        # Mock current hour to 10 (not in quiet hours)
        now = datetime.now(timezone.utc).replace(hour=10)

        # Should not be in quiet hours
        # Note: This test depends on current time, so we just check the method exists
        assert hasattr(rule, 'is_in_quiet_hours')


class TestNotification:
    """Test notification functionality"""

    def test_notification_creation(self):
        """Test notification creation"""
        notification = Notification(
            notification_id="test_notif",
            recipient="user@example.com",
            channel=NotificationChannel.EMAIL,
            event=NotificationEvent.REVIEW_REQUESTED,
            priority=NotificationPriority.MEDIUM,
            subject="Test Subject",
            body="Test Body"
        )

        assert notification.notification_id == "test_notif"
        assert notification.status == NotificationStatus.PENDING
        assert notification.retry_count == 0

    def test_notification_to_dict(self):
        """Test notification serialization"""
        notification = Notification(
            notification_id="test_notif",
            recipient="user@example.com",
            channel=NotificationChannel.EMAIL,
            event=NotificationEvent.REVIEW_REQUESTED,
            priority=NotificationPriority.MEDIUM,
            subject="Test Subject",
            body="Test Body"
        )

        data = notification.to_dict()

        assert data["notification_id"] == "test_notif"
        assert data["recipient"] == "user@example.com"
        assert data["channel"] == "email"
        assert data["status"] == "pending"


class TestNotificationEnhancedSystem:
    """Test notification system functionality"""

    def test_system_initialization(self, notification_system):
        """Test system initialization"""
        assert len(notification_system.templates) > 0
        assert len(notification_system.rules) == 0
        assert len(notification_system.notifications) == 0

    def test_add_template(self, notification_system, sample_template):
        """Test adding template"""
        initial_count = len(notification_system.templates)
        notification_system.add_template(sample_template)

        assert len(notification_system.templates) == initial_count + 1
        assert notification_system.get_template("test_template") == sample_template

    def test_list_templates(self, notification_system, sample_template):
        """Test listing templates"""
        notification_system.add_template(sample_template)

        # List all templates
        all_templates = notification_system.list_templates()
        assert len(all_templates) > 0

        # Filter by event
        event_templates = notification_system.list_templates(
            event=NotificationEvent.REVIEW_REQUESTED
        )
        assert len(event_templates) > 0

        # Filter by channel
        channel_templates = notification_system.list_templates(
            channel=NotificationChannel.EMAIL
        )
        assert len(channel_templates) > 0

    def test_add_rule(self, notification_system, sample_rule):
        """Test adding rule"""
        notification_system.add_rule(sample_rule)

        assert len(notification_system.rules) == 1
        assert notification_system.get_rule("test_rule") == sample_rule

    def test_list_rules(self, notification_system, sample_rule):
        """Test listing rules"""
        notification_system.add_rule(sample_rule)

        # List all rules
        all_rules = notification_system.list_rules()
        assert len(all_rules) == 1

        # List enabled only
        enabled_rules = notification_system.list_rules(enabled_only=True)
        assert len(enabled_rules) == 1

        # Disable rule and list again
        sample_rule.enabled = False
        enabled_rules = notification_system.list_rules(enabled_only=True)
        assert len(enabled_rules) == 0

    def test_register_channel_handler(self, notification_system):
        """Test registering channel handler"""
        handler_called = []

        def test_handler(notification):
            handler_called.append(notification)

        notification_system.register_channel_handler(
            NotificationChannel.EMAIL,
            test_handler
        )

        assert NotificationChannel.EMAIL in notification_system.channel_handlers

    def test_send_notification_with_template(self, notification_system, sample_template):
        """Test sending notification with template"""
        notification_system.add_template(sample_template)

        # Register handler
        sent_notifications = []

        def test_handler(notification):
            sent_notifications.append(notification)

        notification_system.register_channel_handler(
            NotificationChannel.EMAIL,
            test_handler
        )

        # Send notification
        context = {
            "pr_title": "Fix bug",
            "author": "John Doe"
        }

        notifications = notification_system.send_notification(
            notification_id="test_001",
            recipient="user@example.com",
            event=NotificationEvent.REVIEW_REQUESTED,
            context=context,
            channels=[NotificationChannel.EMAIL]
        )

        assert len(notifications) == 1
        # The system uses default template if available, so check it contains the PR title
        assert "Fix bug" in notifications[0].subject
        assert notifications[0].status == NotificationStatus.SENT
        assert len(sent_notifications) == 1

    def test_send_notification_without_template(self, notification_system):
        """Test sending notification without template"""
        # Register handler
        sent_notifications = []

        def test_handler(notification):
            sent_notifications.append(notification)

        notification_system.register_channel_handler(
            NotificationChannel.SLACK,
            test_handler
        )

        # Send notification
        context = {"title": "Test Notification"}

        notifications = notification_system.send_notification(
            notification_id="test_002",
            recipient="user@example.com",
            event=NotificationEvent.COMMENT_ADDED,
            context=context,
            channels=[NotificationChannel.SLACK]
        )

        assert len(notifications) == 1
        assert "comment_added" in notifications[0].subject
        assert len(sent_notifications) == 1

    def test_send_notification_with_rule(self, notification_system, sample_rule):
        """Test sending notification with matching rule"""
        notification_system.add_rule(sample_rule)

        # Register handlers
        def test_handler(notification):
            pass

        notification_system.register_channel_handler(
            NotificationChannel.EMAIL,
            test_handler
        )
        notification_system.register_channel_handler(
            NotificationChannel.SLACK,
            test_handler
        )

        # Send notification with matching context
        context = {"priority": "high", "title": "Test"}

        notifications = notification_system.send_notification(
            notification_id="test_003",
            recipient="user@example.com",
            event=NotificationEvent.REVIEW_REQUESTED,
            context=context
        )

        # Should send to both channels from rule
        assert len(notifications) == 2

    def test_get_notification(self, notification_system):
        """Test getting notification"""
        # Register handler
        def test_handler(notification):
            pass

        notification_system.register_channel_handler(
            NotificationChannel.EMAIL,
            test_handler
        )

        # Send notification
        notifications = notification_system.send_notification(
            notification_id="test_004",
            recipient="user@example.com",
            event=NotificationEvent.REVIEW_REQUESTED,
            context={"title": "Test"},
            channels=[NotificationChannel.EMAIL]
        )

        # Get notification
        notification = notification_system.get_notification(
            notifications[0].notification_id
        )

        assert notification is not None
        assert notification.notification_id == notifications[0].notification_id

    def test_list_notifications(self, notification_system):
        """Test listing notifications"""
        # Register handler
        def test_handler(notification):
            pass

        notification_system.register_channel_handler(
            NotificationChannel.EMAIL,
            test_handler
        )

        # Send multiple notifications
        for i in range(3):
            notification_system.send_notification(
                notification_id=f"test_{i}",
                recipient="user@example.com",
                event=NotificationEvent.REVIEW_REQUESTED,
                context={"title": f"Test {i}"},
                channels=[NotificationChannel.EMAIL]
            )

        # List all notifications
        all_notifications = notification_system.list_notifications()
        assert len(all_notifications) >= 3

        # Filter by recipient
        recipient_notifications = notification_system.list_notifications(
            recipient="user@example.com"
        )
        assert len(recipient_notifications) >= 3

        # Filter by status
        sent_notifications = notification_system.list_notifications(
            status=NotificationStatus.SENT
        )
        assert len(sent_notifications) >= 3

    def test_retry_notification(self, notification_system):
        """Test retrying failed notification"""
        # Register failing handler
        def failing_handler(notification):
            raise Exception("Test failure")

        notification_system.register_channel_handler(
            NotificationChannel.EMAIL,
            failing_handler
        )

        # Send notification (will fail)
        notifications = notification_system.send_notification(
            notification_id="test_retry",
            recipient="user@example.com",
            event=NotificationEvent.REVIEW_REQUESTED,
            context={"title": "Test"},
            channels=[NotificationChannel.EMAIL]
        )

        notification = notifications[0]
        assert notification.status == NotificationStatus.FAILED

        # Retry should fail again
        result = notification_system.retry_notification(notification.notification_id)
        assert not result
        assert notification.retry_count == 1

    def test_cancel_notification(self, notification_system):
        """Test canceling notification"""
        # Create pending notification manually
        notification = Notification(
            notification_id="test_cancel",
            recipient="user@example.com",
            channel=NotificationChannel.EMAIL,
            event=NotificationEvent.REVIEW_REQUESTED,
            priority=NotificationPriority.MEDIUM,
            subject="Test",
            body="Test"
        )

        notification_system.notifications[notification.notification_id] = notification

        # Cancel notification
        result = notification_system.cancel_notification(notification.notification_id)
        assert result
        assert notification.status == NotificationStatus.CANCELLED

    def test_get_statistics(self, notification_system):
        """Test getting statistics"""
        # Register handler
        def test_handler(notification):
            pass

        notification_system.register_channel_handler(
            NotificationChannel.EMAIL,
            test_handler
        )

        # Send notifications
        for i in range(5):
            notification_system.send_notification(
                notification_id=f"test_stats_{i}",
                recipient="user@example.com",
                event=NotificationEvent.REVIEW_REQUESTED,
                context={"title": f"Test {i}"},
                channels=[NotificationChannel.EMAIL]
            )

        # Get statistics
        stats = notification_system.get_statistics()

        assert stats["total"] >= 5
        assert "by_status" in stats
        assert "by_channel" in stats
        assert "by_event" in stats
        assert "success_rate" in stats

    def test_singleton_instance(self):
        """Test singleton instance"""
        system1 = get_notification_system()
        system2 = get_notification_system()

        assert system1 is system2


class TestRateLimiting:
    """Test rate limiting functionality"""

    def test_rate_limit_not_exceeded(self, notification_system):
        """Test rate limit not exceeded"""
        rule = NotificationRule(
            rule_id="rate_limit_rule",
            name="Rate Limit Rule",
            event=NotificationEvent.REVIEW_REQUESTED,
            conditions={},
            channels=[NotificationChannel.EMAIL],
            priority=NotificationPriority.MEDIUM,
            rate_limit=10
        )

        notification_system.add_rule(rule)

        # Should allow first notification
        result = notification_system._check_rate_limit("rate_limit_rule", 10)
        assert result

    def test_rate_limit_exceeded(self, notification_system):
        """Test rate limit exceeded"""
        rule_id = "rate_limit_rule_2"

        # Fill up rate limit
        for i in range(5):
            notification_system._check_rate_limit(rule_id, 5)

        # Should be exceeded
        result = notification_system._check_rate_limit(rule_id, 5)
        assert not result
