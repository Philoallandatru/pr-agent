"""
Quota management for organizations and users.

Tracks usage against configured limits:
- API calls per month
- Reviews per month
- Repositories per organization
- Users per organization
- Storage usage
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from dataclasses import dataclass
import sqlite3


class QuotaExceeded(Exception):
    """Raised when quota is exceeded."""

    def __init__(self, quota_type: str, limit: int, current: int):
        self.quota_type = quota_type
        self.limit = limit
        self.current = current
        super().__init__(
            f"Quota exceeded for {quota_type}: {current}/{limit}"
        )


@dataclass
class QuotaInfo:
    """Quota information."""
    quota_type: str
    limit: int
    used: int
    remaining: int
    reset_date: Optional[str] = None

    @property
    def percentage_used(self) -> float:
        """Calculate percentage of quota used."""
        if self.limit == 0:
            return 0.0
        return (self.used / self.limit) * 100

    @property
    def is_exceeded(self) -> bool:
        """Check if quota is exceeded."""
        return self.used >= self.limit


class QuotaManager:
    """
    Manage quotas for organizations and users.

    Supports:
    - Monthly API call limits
    - Monthly review limits
    - Repository count limits
    - User count limits
    - Storage limits
    - Custom quota types
    """

    def __init__(self, db_path: str):
        """
        Initialize quota manager.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Quota definitions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quota_definitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL,
                quota_type TEXT NOT NULL,
                limit_value INTEGER NOT NULL,
                reset_period TEXT DEFAULT 'monthly',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(org_id, quota_type)
            )
        """)

        # Quota usage table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quota_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL,
                quota_type TEXT NOT NULL,
                period TEXT NOT NULL,
                used_value INTEGER DEFAULT 0,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(org_id, quota_type, period)
            )
        """)

        # Quota alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quota_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL,
                quota_type TEXT NOT NULL,
                threshold INTEGER NOT NULL,
                notified_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def set_quota(
        self,
        org_id: int,
        quota_type: str,
        limit: int,
        reset_period: str = "monthly"
    ):
        """
        Set quota limit for an organization.

        Args:
            org_id: Organization ID
            quota_type: Type of quota (api_calls, reviews, repositories, users, storage)
            limit: Maximum allowed value
            reset_period: Reset period (monthly, daily, yearly, never)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO quota_definitions (org_id, quota_type, limit_value, reset_period)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(org_id, quota_type) DO UPDATE SET
                limit_value = excluded.limit_value,
                reset_period = excluded.reset_period
        """, (org_id, quota_type, limit, reset_period))

        conn.commit()
        conn.close()

    def get_quota(self, org_id: int, quota_type: str) -> Optional[QuotaInfo]:
        """
        Get quota information.

        Args:
            org_id: Organization ID
            quota_type: Type of quota

        Returns:
            QuotaInfo object or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get quota definition
        cursor.execute("""
            SELECT limit_value, reset_period
            FROM quota_definitions
            WHERE org_id = ? AND quota_type = ?
        """, (org_id, quota_type))

        result = cursor.fetchone()
        if not result:
            conn.close()
            return None

        limit, reset_period = result

        # Get current usage
        period = self._get_current_period(reset_period)
        cursor.execute("""
            SELECT used_value
            FROM quota_usage
            WHERE org_id = ? AND quota_type = ? AND period = ?
        """, (org_id, quota_type, period))

        usage_result = cursor.fetchone()
        used = usage_result[0] if usage_result else 0

        conn.close()

        reset_date = self._get_reset_date(reset_period) if reset_period != "never" else None

        return QuotaInfo(
            quota_type=quota_type,
            limit=limit,
            used=used,
            remaining=max(0, limit - used),
            reset_date=reset_date
        )

    def check_quota(self, org_id: int, quota_type: str, amount: int = 1) -> bool:
        """
        Check if quota allows the requested amount.

        Args:
            org_id: Organization ID
            quota_type: Type of quota
            amount: Amount to check (default: 1)

        Returns:
            True if quota allows, False otherwise
        """
        quota = self.get_quota(org_id, quota_type)
        if not quota:
            # No quota defined = unlimited
            return True

        return quota.used + amount <= quota.limit

    def increment_quota(
        self,
        org_id: int,
        quota_type: str,
        amount: int = 1,
        check_limit: bool = True
    ) -> QuotaInfo:
        """
        Increment quota usage.

        Args:
            org_id: Organization ID
            quota_type: Type of quota
            amount: Amount to increment
            check_limit: Raise exception if limit exceeded

        Returns:
            Updated QuotaInfo

        Raises:
            QuotaExceeded: If check_limit=True and quota exceeded
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get quota definition
        cursor.execute("""
            SELECT limit_value, reset_period
            FROM quota_definitions
            WHERE org_id = ? AND quota_type = ?
        """, (org_id, quota_type))

        result = cursor.fetchone()
        if not result:
            conn.close()
            # No quota defined = unlimited
            return QuotaInfo(
                quota_type=quota_type,
                limit=0,
                used=amount,
                remaining=0
            )

        limit, reset_period = result
        period = self._get_current_period(reset_period)

        # Get or create usage record
        cursor.execute("""
            INSERT INTO quota_usage (org_id, quota_type, period, used_value)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(org_id, quota_type, period) DO UPDATE SET
                used_value = used_value + excluded.used_value,
                last_updated = CURRENT_TIMESTAMP
            RETURNING used_value
        """, (org_id, quota_type, period, amount))

        new_used = cursor.fetchone()[0]

        conn.commit()
        conn.close()

        # Check if exceeded
        if check_limit and new_used > limit:
            raise QuotaExceeded(quota_type, limit, new_used)

        reset_date = self._get_reset_date(reset_period) if reset_period != "never" else None

        return QuotaInfo(
            quota_type=quota_type,
            limit=limit,
            used=new_used,
            remaining=max(0, limit - new_used),
            reset_date=reset_date
        )

    def decrement_quota(
        self,
        org_id: int,
        quota_type: str,
        amount: int = 1
    ) -> QuotaInfo:
        """
        Decrement quota usage (e.g., when deleting resources).

        Args:
            org_id: Organization ID
            quota_type: Type of quota
            amount: Amount to decrement

        Returns:
            Updated QuotaInfo
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get quota definition
        cursor.execute("""
            SELECT limit_value, reset_period
            FROM quota_definitions
            WHERE org_id = ? AND quota_type = ?
        """, (org_id, quota_type))

        result = cursor.fetchone()
        if not result:
            conn.close()
            return QuotaInfo(
                quota_type=quota_type,
                limit=0,
                used=0,
                remaining=0
            )

        limit, reset_period = result
        period = self._get_current_period(reset_period)

        # Update usage (don't go below 0)
        cursor.execute("""
            UPDATE quota_usage
            SET used_value = MAX(0, used_value - ?),
                last_updated = CURRENT_TIMESTAMP
            WHERE org_id = ? AND quota_type = ? AND period = ?
            RETURNING used_value
        """, (amount, org_id, quota_type, period))

        result = cursor.fetchone()
        new_used = result[0] if result else 0

        conn.commit()
        conn.close()

        reset_date = self._get_reset_date(reset_period) if reset_period != "never" else None

        return QuotaInfo(
            quota_type=quota_type,
            limit=limit,
            used=new_used,
            remaining=max(0, limit - new_used),
            reset_date=reset_date
        )

    def get_all_quotas(self, org_id: int) -> List[QuotaInfo]:
        """
        Get all quotas for an organization.

        Args:
            org_id: Organization ID

        Returns:
            List of QuotaInfo objects
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT quota_type, limit_value, reset_period
            FROM quota_definitions
            WHERE org_id = ?
        """, (org_id,))

        quotas = []
        for quota_type, limit, reset_period in cursor.fetchall():
            period = self._get_current_period(reset_period)

            cursor.execute("""
                SELECT used_value
                FROM quota_usage
                WHERE org_id = ? AND quota_type = ? AND period = ?
            """, (org_id, quota_type, period))

            usage_result = cursor.fetchone()
            used = usage_result[0] if usage_result else 0

            reset_date = self._get_reset_date(reset_period) if reset_period != "never" else None

            quotas.append(QuotaInfo(
                quota_type=quota_type,
                limit=limit,
                used=used,
                remaining=max(0, limit - used),
                reset_date=reset_date
            ))

        conn.close()
        return quotas

    def reset_quota(self, org_id: int, quota_type: str):
        """
        Manually reset quota usage to zero.

        Args:
            org_id: Organization ID
            quota_type: Type of quota
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM quota_usage
            WHERE org_id = ? AND quota_type = ?
        """, (org_id, quota_type))

        conn.commit()
        conn.close()

    def set_alert_threshold(
        self,
        org_id: int,
        quota_type: str,
        threshold: int
    ):
        """
        Set alert threshold (percentage) for quota.

        Args:
            org_id: Organization ID
            quota_type: Type of quota
            threshold: Percentage threshold (0-100)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO quota_alerts (org_id, quota_type, threshold)
            VALUES (?, ?, ?)
        """, (org_id, quota_type, threshold))

        conn.commit()
        conn.close()

    def check_alerts(self, org_id: int) -> List[Dict[str, Any]]:
        """
        Check if any quotas have exceeded alert thresholds.

        Args:
            org_id: Organization ID

        Returns:
            List of alerts with quota info
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT qa.quota_type, qa.threshold, qa.notified_at
            FROM quota_alerts qa
            WHERE qa.org_id = ?
        """, (org_id,))

        alerts = []
        for quota_type, threshold, notified_at in cursor.fetchall():
            quota = self.get_quota(org_id, quota_type)
            if quota and quota.percentage_used >= threshold:
                if not notified_at:
                    # Mark as notified
                    cursor.execute("""
                        UPDATE quota_alerts
                        SET notified_at = CURRENT_TIMESTAMP
                        WHERE org_id = ? AND quota_type = ?
                    """, (org_id, quota_type))

                alerts.append({
                    "quota_type": quota_type,
                    "threshold": threshold,
                    "current_percentage": quota.percentage_used,
                    "quota_info": quota
                })

        conn.commit()
        conn.close()
        return alerts

    def _get_current_period(self, reset_period: str) -> str:
        """Get current period identifier."""
        now = datetime.now(timezone.utc)

        if reset_period == "daily":
            return now.strftime("%Y-%m-%d")
        elif reset_period == "monthly":
            return now.strftime("%Y-%m")
        elif reset_period == "yearly":
            return now.strftime("%Y")
        else:  # never
            return "permanent"

    def _get_reset_date(self, reset_period: str) -> str:
        """Get next reset date."""
        now = datetime.now(timezone.utc)

        if reset_period == "daily":
            next_reset = now.replace(hour=0, minute=0, second=0, microsecond=0)
            next_reset = next_reset.replace(day=next_reset.day + 1)
        elif reset_period == "monthly":
            if now.month == 12:
                next_reset = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                next_reset = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        elif reset_period == "yearly":
            next_reset = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            return "never"

        return next_reset.isoformat()
