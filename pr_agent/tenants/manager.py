"""
Multi-tenant User Management System

Provides user management, organization/tenant isolation, and role-based access control.
"""

import sqlite3
from typing import Dict, List, Optional, Any
from datetime import datetime
import secrets
import string


class TenantManager:
    """
    Manages multi-tenant organizations and user assignments.

    Features:
    - Organization/tenant creation and management
    - User-tenant associations
    - Tenant-level resource isolation
    - Subscription/plan management
    """

    def __init__(self, db_path: str):
        """Initialize tenant manager with database."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        """Create tenant-related tables."""
        cursor = self.conn.cursor()

        # Organizations/Tenants table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS organizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                plan TEXT DEFAULT 'free',
                max_users INTEGER DEFAULT 5,
                max_repositories INTEGER DEFAULT 10,
                max_reviews_per_month INTEGER DEFAULT 100,
                settings TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Users table (enhanced)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                is_active BOOLEAN DEFAULT 1,
                is_superadmin BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # User-Organization membership
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS organization_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(organization_id, user_id)
            )
        """)

        # Tenant-scoped repositories
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tenant_repositories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                repository_id INTEGER NOT NULL,
                FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
                FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE,
                UNIQUE(organization_id, repository_id)
            )
        """)

        # Usage tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                resource_type TEXT NOT NULL,
                count INTEGER DEFAULT 0,
                period TEXT NOT NULL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
                UNIQUE(organization_id, resource_type, period)
            )
        """)

        # Invitations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invitations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                token TEXT UNIQUE NOT NULL,
                invited_by INTEGER NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                accepted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
                FOREIGN KEY (invited_by) REFERENCES users(id)
            )
        """)

        self.conn.commit()

    # Organization Management

    def create_organization(
        self,
        name: str,
        slug: str,
        plan: str = "free",
        settings: Optional[Dict[str, Any]] = None
    ) -> int:
        """Create a new organization/tenant."""
        import json

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO organizations (name, slug, plan, settings)
            VALUES (?, ?, ?, ?)
        """, (name, slug, plan, json.dumps(settings or {})))
        self.conn.commit()
        return cursor.lastrowid

    def get_organization(self, org_id: int) -> Optional[Dict[str, Any]]:
        """Get organization by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM organizations WHERE id = ?", (org_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_organization_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get organization by slug."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM organizations WHERE slug = ?", (slug,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_organization(
        self,
        org_id: int,
        name: Optional[str] = None,
        plan: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update organization details."""
        import json

        updates = []
        params = []

        if name:
            updates.append("name = ?")
            params.append(name)
        if plan:
            updates.append("plan = ?")
            params.append(plan)
        if settings is not None:
            updates.append("settings = ?")
            params.append(json.dumps(settings))

        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(org_id)

        cursor = self.conn.cursor()
        cursor.execute(f"""
            UPDATE organizations
            SET {', '.join(updates)}
            WHERE id = ?
        """, params)
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_organization(self, org_id: int) -> bool:
        """Delete organization and all associated data."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM organizations WHERE id = ?", (org_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def list_organizations(self) -> List[Dict[str, Any]]:
        """List all organizations."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM organizations ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    # User Management

    def create_user(
        self,
        username: str,
        email: str,
        password_hash: str,
        full_name: Optional[str] = None,
        is_superadmin: bool = False
    ) -> int:
        """Create a new user."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, full_name, is_superadmin)
            VALUES (?, ?, ?, ?, ?)
        """, (username, email, password_hash, full_name, is_superadmin))
        self.conn.commit()
        return cursor.lastrowid

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_user(
        self,
        user_id: int,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> bool:
        """Update user details."""
        updates = []
        params = []

        if email:
            updates.append("email = ?")
            params.append(email)
        if full_name is not None:
            updates.append("full_name = ?")
            params.append(full_name)
        if is_active is not None:
            updates.append("is_active = ?")
            params.append(is_active)

        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(user_id)

        cursor = self.conn.cursor()
        cursor.execute(f"""
            UPDATE users
            SET {', '.join(updates)}
            WHERE id = ?
        """, params)
        self.conn.commit()
        return cursor.rowcount > 0

    def delete_user(self, user_id: int) -> bool:
        """Delete user."""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # Organization Membership

    def add_member(
        self,
        org_id: int,
        user_id: int,
        role: str = "member"
    ) -> bool:
        """Add user to organization."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO organization_members (organization_id, user_id, role)
                VALUES (?, ?, ?)
            """, (org_id, user_id, role))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def remove_member(self, org_id: int, user_id: int) -> bool:
        """Remove user from organization."""
        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM organization_members
            WHERE organization_id = ? AND user_id = ?
        """, (org_id, user_id))
        self.conn.commit()
        return cursor.rowcount > 0

    def update_member_role(self, org_id: int, user_id: int, role: str) -> bool:
        """Update member's role in organization."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE organization_members
            SET role = ?
            WHERE organization_id = ? AND user_id = ?
        """, (role, org_id, user_id))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_organization_members(self, org_id: int) -> List[Dict[str, Any]]:
        """Get all members of an organization."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT u.*, om.role, om.joined_at
            FROM users u
            JOIN organization_members om ON u.id = om.user_id
            WHERE om.organization_id = ?
            ORDER BY om.joined_at
        """, (org_id,))
        return [dict(row) for row in cursor.fetchall()]

    def get_user_organizations(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all organizations a user belongs to."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT o.*, om.role
            FROM organizations o
            JOIN organization_members om ON o.id = om.organization_id
            WHERE om.user_id = ?
            ORDER BY om.joined_at DESC
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]

    def is_member(self, org_id: int, user_id: int) -> bool:
        """Check if user is member of organization."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 1 FROM organization_members
            WHERE organization_id = ? AND user_id = ?
        """, (org_id, user_id))
        return cursor.fetchone() is not None

    def get_member_role(self, org_id: int, user_id: int) -> Optional[str]:
        """Get user's role in organization."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT role FROM organization_members
            WHERE organization_id = ? AND user_id = ?
        """, (org_id, user_id))
        row = cursor.fetchone()
        return row[0] if row else None

    # Invitations

    def create_invitation(
        self,
        org_id: int,
        email: str,
        role: str,
        invited_by: int,
        expires_in_days: int = 7
    ) -> str:
        """Create invitation for user to join organization."""
        from datetime import timedelta

        token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
        expires_at = datetime.now() + timedelta(days=expires_in_days)

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO invitations (organization_id, email, role, token, invited_by, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (org_id, email, role, token, invited_by, expires_at))
        self.conn.commit()
        return token

    def get_invitation(self, token: str) -> Optional[Dict[str, Any]]:
        """Get invitation by token."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM invitations WHERE token = ?", (token,))
        row = cursor.fetchone()
        return dict(row) if row else None

    def accept_invitation(self, token: str, user_id: int) -> bool:
        """Accept invitation and add user to organization."""
        invitation = self.get_invitation(token)
        if not invitation:
            return False

        # Check if expired
        expires_at = datetime.fromisoformat(invitation['expires_at'])
        if datetime.now() > expires_at:
            return False

        # Check if already accepted
        if invitation['accepted_at']:
            return False

        # Add user to organization
        success = self.add_member(
            invitation['organization_id'],
            user_id,
            invitation['role']
        )

        if success:
            # Mark invitation as accepted
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE invitations
                SET accepted_at = CURRENT_TIMESTAMP
                WHERE token = ?
            """, (token,))
            self.conn.commit()

        return success

    # Resource Management

    def assign_repository(self, org_id: int, repo_id: int) -> bool:
        """Assign repository to organization."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO tenant_repositories (organization_id, repository_id)
                VALUES (?, ?)
            """, (org_id, repo_id))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def unassign_repository(self, org_id: int, repo_id: int) -> bool:
        """Remove repository from organization."""
        cursor = self.conn.cursor()
        cursor.execute("""
            DELETE FROM tenant_repositories
            WHERE organization_id = ? AND repository_id = ?
        """, (org_id, repo_id))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_organization_repositories(self, org_id: int) -> List[int]:
        """Get all repository IDs for an organization."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT repository_id FROM tenant_repositories
            WHERE organization_id = ?
        """, (org_id,))
        return [row[0] for row in cursor.fetchall()]

    # Usage Tracking

    def track_usage(self, org_id: int, resource_type: str, count: int = 1):
        """Track resource usage for organization."""
        period = datetime.now().strftime("%Y-%m")

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO usage_tracking (organization_id, resource_type, count, period)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(organization_id, resource_type, period) DO UPDATE SET
                count = count + excluded.count,
                recorded_at = CURRENT_TIMESTAMP
        """, (org_id, resource_type, count, period))
        self.conn.commit()

    def get_usage(self, org_id: int, period: Optional[str] = None) -> Dict[str, int]:
        """Get usage statistics for organization."""
        if not period:
            period = datetime.now().strftime("%Y-%m")

        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT resource_type, count
            FROM usage_tracking
            WHERE organization_id = ? AND period = ?
        """, (org_id, period))

        return {row[0]: row[1] for row in cursor.fetchall()}

    def check_quota(self, org_id: int, resource_type: str) -> bool:
        """Check if organization has quota available for resource."""
        org = self.get_organization(org_id)
        if not org:
            return False

        usage = self.get_usage(org_id)
        current = usage.get(resource_type, 0)

        # Check against plan limits
        if resource_type == "reviews":
            return current < org['max_reviews_per_month']
        elif resource_type == "repositories":
            repo_count = len(self.get_organization_repositories(org_id))
            return repo_count < org['max_repositories']
        elif resource_type == "users":
            member_count = len(self.get_organization_members(org_id))
            return member_count < org['max_users']

        return True

    def close(self):
        """Close database connection."""
        self.conn.close()
