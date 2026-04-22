"""
Audit logging system for tracking security-relevant events.

This module provides comprehensive audit logging for compliance,
security monitoring, and forensic analysis.
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """Types of auditable events."""

    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_CREATED = "token_created"
    TOKEN_REVOKED = "token_revoked"
    PASSWORD_CHANGED = "password_changed"

    # Authorization events
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PERMISSION_CHANGED = "permission_changed"
    ROLE_CHANGED = "role_changed"

    # Resource events
    RESOURCE_CREATED = "resource_created"
    RESOURCE_UPDATED = "resource_updated"
    RESOURCE_DELETED = "resource_deleted"
    RESOURCE_ACCESSED = "resource_accessed"

    # Configuration events
    CONFIG_CHANGED = "config_changed"
    CONFIG_UPDATED = "config_updated"
    CONFIG_RELOADED = "config_reloaded"

    # Organization events
    ORG_CREATED = "org_created"
    ORG_UPDATED = "org_updated"
    ORG_DELETED = "org_deleted"
    MEMBER_ADDED = "member_added"
    MEMBER_REMOVED = "member_removed"

    # API events
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    QUOTA_EXCEEDED = "quota_exceeded"

    # System events
    SERVICE_STARTED = "service_started"
    SERVICE_STOPPED = "service_stopped"
    BACKUP_CREATED = "backup_created"
    MIGRATION_EXECUTED = "migration_executed"


class AuditSeverity(str, Enum):
    """Severity levels for audit events."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditLogger:
    """
    Audit logger for recording security-relevant events.

    Stores audit logs in SQLite database with support for:
    - Event categorization and severity levels
    - User and IP tracking
    - Structured metadata
    - Efficient querying and filtering
    - Automatic retention management
    """

    def __init__(self, db_path: str = "audit.db"):
        """
        Initialize audit logger.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        """Initialize audit log database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                user_id TEXT,
                username TEXT,
                ip_address TEXT,
                resource_type TEXT,
                resource_id TEXT,
                action TEXT,
                result TEXT,
                message TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL
            )
        """)

        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp
            ON audit_logs(timestamp DESC)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_event_type
            ON audit_logs(event_type)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_user
            ON audit_logs(user_id, username)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_resource
            ON audit_logs(resource_type, resource_id)
        """)

        conn.commit()
        conn.close()

        logger.info(f"Audit log database initialized: {self.db_path}")

    def log(
        self,
        event_type: AuditEventType,
        severity: AuditSeverity = AuditSeverity.INFO,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        result: Optional[str] = None,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Log an audit event.

        Args:
            event_type: Type of event
            severity: Event severity level
            user_id: ID of user performing action
            username: Username of user
            ip_address: IP address of request
            resource_type: Type of resource affected
            resource_id: ID of resource affected
            action: Action performed
            result: Result of action (success/failure)
            message: Human-readable message
            metadata: Additional structured data

        Returns:
            ID of created audit log entry
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        metadata_json = json.dumps(metadata) if metadata else None

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO audit_logs (
                timestamp, event_type, severity, user_id, username,
                ip_address, resource_type, resource_id, action,
                result, message, metadata, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            timestamp, event_type.value, severity.value, user_id, username,
            ip_address, resource_type, resource_id, action,
            result, message, metadata_json, timestamp
        ))

        log_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Also log to standard logger for immediate visibility
        log_msg = f"AUDIT: {event_type.value}"
        if username:
            log_msg += f" by {username}"
        if message:
            log_msg += f" - {message}"

        if severity == AuditSeverity.CRITICAL:
            logger.critical(log_msg)
        elif severity == AuditSeverity.ERROR:
            logger.error(log_msg)
        elif severity == AuditSeverity.WARNING:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

        return log_id

    def query(
        self,
        event_types: Optional[List[AuditEventType]] = None,
        severity: Optional[AuditSeverity] = None,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Query audit logs with filters.

        Args:
            event_types: Filter by event types
            severity: Filter by severity
            user_id: Filter by user ID
            username: Filter by username
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            start_time: Filter by start timestamp
            end_time: Filter by end timestamp
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of audit log entries
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []

        if event_types:
            placeholders = ",".join("?" * len(event_types))
            query += f" AND event_type IN ({placeholders})"
            params.extend([et.value for et in event_types])

        if severity:
            query += " AND severity = ?"
            params.append(severity.value)

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        if username:
            query += " AND username = ?"
            params.append(username)

        if resource_type:
            query += " AND resource_type = ?"
            params.append(resource_type)

        if resource_id:
            query += " AND resource_id = ?"
            params.append(resource_id)

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, params)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            entry = dict(row)
            if entry["metadata"]:
                entry["metadata"] = json.loads(entry["metadata"])
            results.append(entry)

        conn.close()
        return results

    def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get audit log statistics.

        Args:
            start_time: Start of time range
            end_time: End of time range

        Returns:
            Statistics dictionary
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = "SELECT COUNT(*) as total FROM audit_logs WHERE 1=1"
        params = []

        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())

        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())

        cursor.execute(query, params)
        total = cursor.fetchone()[0]

        # Count by event type
        query_by_type = query.replace("COUNT(*) as total", "event_type, COUNT(*) as count")
        query_by_type += " GROUP BY event_type ORDER BY count DESC"
        cursor.execute(query_by_type, params)
        by_event_type = {row[0]: row[1] for row in cursor.fetchall()}

        # Count by severity
        query_by_severity = query.replace("COUNT(*) as total", "severity, COUNT(*) as count")
        query_by_severity += " GROUP BY severity ORDER BY count DESC"
        cursor.execute(query_by_severity, params)
        by_severity = {row[0]: row[1] for row in cursor.fetchall()}

        # Top users
        query_top_users = query.replace("COUNT(*) as total", "username, COUNT(*) as count")
        query_top_users += " AND username IS NOT NULL GROUP BY username ORDER BY count DESC LIMIT 10"
        cursor.execute(query_top_users, params)
        top_users = [{"username": row[0], "count": row[1]} for row in cursor.fetchall()]

        conn.close()

        return {
            "total_events": total,
            "by_event_type": by_event_type,
            "by_severity": by_severity,
            "top_users": top_users
        }

    def cleanup_old_logs(self, days: int = 90) -> int:
        """
        Delete audit logs older than specified days.

        Args:
            days: Number of days to retain

        Returns:
            Number of deleted records
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM audit_logs WHERE timestamp < ?",
            (cutoff_time.isoformat(),)
        )

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        logger.info(f"Cleaned up {deleted} audit logs older than {days} days")
        return deleted


# Global audit logger instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger(db_path: str = "audit.db") -> AuditLogger:
    """
    Get or create global audit logger instance.

    Args:
        db_path: Path to audit database

    Returns:
        AuditLogger instance
    """
    global _audit_logger

    if _audit_logger is None:
        _audit_logger = AuditLogger(db_path)

    return _audit_logger
