"""
Unit tests for audit logging system.
"""

import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from pr_agent.audit.logger import (
    AuditLogger,
    AuditEventType,
    AuditSeverity,
    get_audit_logger
)


class TestAuditLogger(unittest.TestCase):
    """Test cases for AuditLogger."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.logger = AuditLogger(self.db_path)

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_initialization(self):
        """Test audit logger initialization."""
        self.assertTrue(os.path.exists(self.db_path))

        # Verify table exists
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_logs'"
        )
        self.assertIsNotNone(cursor.fetchone())
        conn.close()

    def test_log_basic_event(self):
        """Test logging a basic audit event."""
        log_id = self.logger.log(
            event_type=AuditEventType.LOGIN_SUCCESS,
            severity=AuditSeverity.INFO,
            username="testuser",
            ip_address="192.168.1.1",
            message="User logged in successfully"
        )

        self.assertIsInstance(log_id, int)
        self.assertGreater(log_id, 0)

    def test_log_with_metadata(self):
        """Test logging event with metadata."""
        metadata = {
            "browser": "Chrome",
            "os": "Windows",
            "version": "1.0.0"
        }

        log_id = self.logger.log(
            event_type=AuditEventType.CONFIG_CHANGED,
            severity=AuditSeverity.WARNING,
            user_id="user123",
            username="admin",
            action="update",
            result="success",
            metadata=metadata
        )

        # Query and verify metadata
        logs = self.logger.query(limit=1)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["metadata"], metadata)

    def test_log_resource_event(self):
        """Test logging resource-related event."""
        log_id = self.logger.log(
            event_type=AuditEventType.RESOURCE_DELETED,
            severity=AuditSeverity.WARNING,
            user_id="user456",
            username="admin",
            resource_type="repository",
            resource_id="repo123",
            action="delete",
            result="success",
            message="Repository deleted"
        )

        logs = self.logger.query(resource_type="repository")
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["resource_id"], "repo123")

    def test_query_by_event_type(self):
        """Test querying logs by event type."""
        # Log multiple events
        self.logger.log(AuditEventType.LOGIN_SUCCESS, username="user1")
        self.logger.log(AuditEventType.LOGIN_FAILURE, username="user2")
        self.logger.log(AuditEventType.LOGIN_SUCCESS, username="user3")
        self.logger.log(AuditEventType.LOGOUT, username="user1")

        # Query login success events
        logs = self.logger.query(
            event_types=[AuditEventType.LOGIN_SUCCESS]
        )
        self.assertEqual(len(logs), 2)
        self.assertTrue(all(log["event_type"] == "login_success" for log in logs))

    def test_query_by_severity(self):
        """Test querying logs by severity."""
        self.logger.log(AuditEventType.LOGIN_SUCCESS, severity=AuditSeverity.INFO)
        self.logger.log(AuditEventType.ACCESS_DENIED, severity=AuditSeverity.WARNING)
        self.logger.log(AuditEventType.LOGIN_FAILURE, severity=AuditSeverity.ERROR)

        # Query warnings
        logs = self.logger.query(severity=AuditSeverity.WARNING)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["severity"], "warning")

    def test_query_by_user(self):
        """Test querying logs by user."""
        self.logger.log(AuditEventType.LOGIN_SUCCESS, user_id="user1", username="alice")
        self.logger.log(AuditEventType.LOGIN_SUCCESS, user_id="user2", username="bob")
        self.logger.log(AuditEventType.LOGOUT, user_id="user1", username="alice")

        # Query by user_id
        logs = self.logger.query(user_id="user1")
        self.assertEqual(len(logs), 2)

        # Query by username
        logs = self.logger.query(username="bob")
        self.assertEqual(len(logs), 1)

    def test_query_by_time_range(self):
        """Test querying logs by time range."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=2)
        future = now + timedelta(hours=2)

        # Log events
        self.logger.log(AuditEventType.LOGIN_SUCCESS, username="user1")

        # Query with time range
        logs = self.logger.query(start_time=past, end_time=future)
        self.assertEqual(len(logs), 1)

        # Query outside time range
        logs = self.logger.query(
            start_time=now + timedelta(days=1),
            end_time=now + timedelta(days=2)
        )
        self.assertEqual(len(logs), 0)

    def test_query_pagination(self):
        """Test query pagination."""
        # Log 10 events
        for i in range(10):
            self.logger.log(
                AuditEventType.LOGIN_SUCCESS,
                username=f"user{i}"
            )

        # Query first page
        logs_page1 = self.logger.query(limit=5, offset=0)
        self.assertEqual(len(logs_page1), 5)

        # Query second page
        logs_page2 = self.logger.query(limit=5, offset=5)
        self.assertEqual(len(logs_page2), 5)

        # Verify no overlap
        ids_page1 = {log["id"] for log in logs_page1}
        ids_page2 = {log["id"] for log in logs_page2}
        self.assertEqual(len(ids_page1 & ids_page2), 0)

    def test_get_statistics(self):
        """Test getting audit log statistics."""
        # Log various events
        self.logger.log(AuditEventType.LOGIN_SUCCESS, username="alice")
        self.logger.log(AuditEventType.LOGIN_SUCCESS, username="alice")
        self.logger.log(AuditEventType.LOGIN_FAILURE, username="bob")
        self.logger.log(AuditEventType.ACCESS_DENIED, severity=AuditSeverity.WARNING)

        stats = self.logger.get_statistics()

        self.assertEqual(stats["total_events"], 4)
        self.assertIn("login_success", stats["by_event_type"])
        self.assertEqual(stats["by_event_type"]["login_success"], 2)
        self.assertIn("info", stats["by_severity"])
        self.assertGreater(len(stats["top_users"]), 0)

    def test_get_statistics_with_time_range(self):
        """Test statistics with time range filter."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=1)

        # Log events
        self.logger.log(AuditEventType.LOGIN_SUCCESS)
        self.logger.log(AuditEventType.LOGOUT)

        stats = self.logger.get_statistics(start_time=past)
        self.assertEqual(stats["total_events"], 2)

    def test_cleanup_old_logs(self):
        """Test cleaning up old audit logs."""
        # Log some events
        for i in range(5):
            self.logger.log(
                AuditEventType.LOGIN_SUCCESS,
                username=f"user{i}"
            )

        # Manually set old timestamps
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        old_time = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
        cursor.execute(
            "UPDATE audit_logs SET timestamp = ? WHERE id <= 3",
            (old_time,)
        )
        conn.commit()
        conn.close()

        # Cleanup logs older than 90 days
        deleted = self.logger.cleanup_old_logs(days=90)
        self.assertEqual(deleted, 3)

        # Verify remaining logs
        logs = self.logger.query(limit=100)
        self.assertEqual(len(logs), 2)

    def test_multiple_event_types_query(self):
        """Test querying multiple event types."""
        self.logger.log(AuditEventType.LOGIN_SUCCESS)
        self.logger.log(AuditEventType.LOGIN_FAILURE)
        self.logger.log(AuditEventType.LOGOUT)
        self.logger.log(AuditEventType.ACCESS_DENIED)

        logs = self.logger.query(
            event_types=[
                AuditEventType.LOGIN_SUCCESS,
                AuditEventType.LOGIN_FAILURE
            ]
        )
        self.assertEqual(len(logs), 2)

    def test_complex_query(self):
        """Test complex query with multiple filters."""
        # Log various events
        self.logger.log(
            AuditEventType.RESOURCE_CREATED,
            severity=AuditSeverity.INFO,
            user_id="user1",
            username="alice",
            resource_type="repository",
            resource_id="repo1"
        )
        self.logger.log(
            AuditEventType.RESOURCE_UPDATED,
            severity=AuditSeverity.INFO,
            user_id="user1",
            username="alice",
            resource_type="repository",
            resource_id="repo1"
        )
        self.logger.log(
            AuditEventType.RESOURCE_DELETED,
            severity=AuditSeverity.WARNING,
            user_id="user2",
            username="bob",
            resource_type="repository",
            resource_id="repo2"
        )

        # Complex query
        logs = self.logger.query(
            event_types=[
                AuditEventType.RESOURCE_CREATED,
                AuditEventType.RESOURCE_UPDATED
            ],
            user_id="user1",
            resource_type="repository"
        )
        self.assertEqual(len(logs), 2)
        self.assertTrue(all(log["user_id"] == "user1" for log in logs))

    def test_get_audit_logger_singleton(self):
        """Test global audit logger singleton."""
        logger1 = get_audit_logger(self.db_path)
        logger2 = get_audit_logger(self.db_path)

        self.assertIs(logger1, logger2)

    def test_event_ordering(self):
        """Test that events are returned in reverse chronological order."""
        # Log events with slight delay
        for i in range(3):
            self.logger.log(
                AuditEventType.LOGIN_SUCCESS,
                username=f"user{i}"
            )

        logs = self.logger.query(limit=3)
        self.assertEqual(len(logs), 3)

        # Verify descending order
        timestamps = [log["timestamp"] for log in logs]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))


if __name__ == "__main__":
    unittest.main()
