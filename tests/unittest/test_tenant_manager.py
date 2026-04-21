"""
Unit tests for TenantManager
"""

import unittest
import tempfile
import os
from datetime import datetime, timedelta
from pr_agent.tenants.manager import TenantManager


class TestTenantManager(unittest.TestCase):
    """Test cases for TenantManager"""

    def setUp(self):
        """Set up test database"""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.manager = TenantManager(self.db_path)

    def tearDown(self):
        """Clean up test database"""
        self.manager.conn.close()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    # Organization Tests

    def test_create_organization(self):
        """Test creating an organization"""
        org_id = self.manager.create_organization(
            name="Test Org",
            slug="test-org",
            plan="pro"
        )

        self.assertIsNotNone(org_id)
        self.assertIsInstance(org_id, int)

        # Verify organization was created
        org = self.manager.get_organization(org_id)
        self.assertEqual(org['name'], "Test Org")
        self.assertEqual(org['slug'], "test-org")
        self.assertEqual(org['plan'], "pro")

    def test_get_organization(self):
        """Test getting an organization"""
        org_id = self.manager.create_organization("Test Org", "test-org")
        org = self.manager.get_organization(org_id)

        self.assertIsNotNone(org)
        self.assertEqual(org['name'], "Test Org")
        self.assertEqual(org['slug'], "test-org")

    def test_get_nonexistent_organization(self):
        """Test getting a non-existent organization"""
        org = self.manager.get_organization(99999)
        self.assertIsNone(org)

    def test_get_organization_by_slug(self):
        """Test getting organization by slug"""
        self.manager.create_organization("Test Org", "test-org")
        org = self.manager.get_organization_by_slug("test-org")

        self.assertIsNotNone(org)
        self.assertEqual(org['name'], "Test Org")

    def test_update_organization(self):
        """Test updating an organization"""
        org_id = self.manager.create_organization("Test Org", "test-org")

        success = self.manager.update_organization(
            org_id,
            name="Updated Org",
            plan="enterprise"
        )

        self.assertTrue(success)

        org = self.manager.get_organization(org_id)
        self.assertEqual(org['name'], "Updated Org")
        self.assertEqual(org['plan'], "enterprise")

    def test_delete_organization(self):
        """Test deleting an organization"""
        org_id = self.manager.create_organization("Test Org", "test-org")

        success = self.manager.delete_organization(org_id)
        self.assertTrue(success)

        org = self.manager.get_organization(org_id)
        self.assertIsNone(org)

    def test_list_organizations(self):
        """Test listing organizations"""
        self.manager.create_organization("Org 1", "org-1")
        self.manager.create_organization("Org 2", "org-2")
        self.manager.create_organization("Org 3", "org-3")

        orgs = self.manager.list_organizations()
        self.assertEqual(len(orgs), 3)
        # Organizations are ordered by created_at DESC, so most recent is first
        # But since they're created in quick succession, order might vary
        org_names = {org['name'] for org in orgs}
        self.assertEqual(org_names, {"Org 1", "Org 2", "Org 3"})

    # User Tests

    def test_create_user(self):
        """Test creating a user"""
        user_id = self.manager.create_user(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            full_name="Test User"
        )

        self.assertIsNotNone(user_id)
        self.assertIsInstance(user_id, int)

        user = self.manager.get_user(user_id)
        self.assertEqual(user['username'], "testuser")
        self.assertEqual(user['email'], "test@example.com")
        self.assertEqual(user['full_name'], "Test User")

    def test_get_user_by_username(self):
        """Test getting user by username"""
        self.manager.create_user("testuser", "test@example.com", "hash")
        user = self.manager.get_user_by_username("testuser")

        self.assertIsNotNone(user)
        self.assertEqual(user['username'], "testuser")

    def test_get_user_by_email(self):
        """Test getting user by email"""
        self.manager.create_user("testuser", "test@example.com", "hash")
        user = self.manager.get_user_by_email("test@example.com")

        self.assertIsNotNone(user)
        self.assertEqual(user['email'], "test@example.com")

    def test_update_user(self):
        """Test updating a user"""
        user_id = self.manager.create_user("testuser", "test@example.com", "hash")

        success = self.manager.update_user(
            user_id,
            email="newemail@example.com",
            full_name="Updated Name"
        )

        self.assertTrue(success)

        user = self.manager.get_user(user_id)
        self.assertEqual(user['email'], "newemail@example.com")
        self.assertEqual(user['full_name'], "Updated Name")

    def test_delete_user(self):
        """Test deleting a user"""
        user_id = self.manager.create_user("testuser", "test@example.com", "hash")

        success = self.manager.delete_user(user_id)
        self.assertTrue(success)

        user = self.manager.get_user(user_id)
        self.assertIsNone(user)

    # Membership Tests

    def test_add_member(self):
        """Test adding a member to an organization"""
        org_id = self.manager.create_organization("Test Org", "test-org")
        user_id = self.manager.create_user("testuser", "test@example.com", "hash")

        success = self.manager.add_member(org_id, user_id, "member")
        self.assertTrue(success)

        self.assertTrue(self.manager.is_member(org_id, user_id))

    def test_add_duplicate_member(self):
        """Test adding duplicate member fails"""
        org_id = self.manager.create_organization("Test Org", "test-org")
        user_id = self.manager.create_user("testuser", "test@example.com", "hash")

        self.manager.add_member(org_id, user_id, "member")
        success = self.manager.add_member(org_id, user_id, "member")

        self.assertFalse(success)

    def test_remove_member(self):
        """Test removing a member from organization"""
        org_id = self.manager.create_organization("Test Org", "test-org")
        user_id = self.manager.create_user("testuser", "test@example.com", "hash")

        self.manager.add_member(org_id, user_id, "member")
        success = self.manager.remove_member(org_id, user_id)

        self.assertTrue(success)
        self.assertFalse(self.manager.is_member(org_id, user_id))

    def test_update_member_role(self):
        """Test updating member role"""
        org_id = self.manager.create_organization("Test Org", "test-org")
        user_id = self.manager.create_user("testuser", "test@example.com", "hash")

        self.manager.add_member(org_id, user_id, "member")
        success = self.manager.update_member_role(org_id, user_id, "admin")

        self.assertTrue(success)
        role = self.manager.get_member_role(org_id, user_id)
        self.assertEqual(role, "admin")

    def test_get_organization_members(self):
        """Test getting organization members"""
        org_id = self.manager.create_organization("Test Org", "test-org")
        user1_id = self.manager.create_user("user1", "user1@example.com", "hash")
        user2_id = self.manager.create_user("user2", "user2@example.com", "hash")

        self.manager.add_member(org_id, user1_id, "admin")
        self.manager.add_member(org_id, user2_id, "member")

        members = self.manager.get_organization_members(org_id)
        self.assertEqual(len(members), 2)

    def test_get_user_organizations(self):
        """Test getting user's organizations"""
        org1_id = self.manager.create_organization("Org 1", "org-1")
        org2_id = self.manager.create_organization("Org 2", "org-2")
        user_id = self.manager.create_user("testuser", "test@example.com", "hash")

        self.manager.add_member(org1_id, user_id, "admin")
        self.manager.add_member(org2_id, user_id, "member")

        orgs = self.manager.get_user_organizations(user_id)
        self.assertEqual(len(orgs), 2)

    def test_get_member_role(self):
        """Test getting member role"""
        org_id = self.manager.create_organization("Test Org", "test-org")
        user_id = self.manager.create_user("testuser", "test@example.com", "hash")

        self.manager.add_member(org_id, user_id, "admin")
        role = self.manager.get_member_role(org_id, user_id)

        self.assertEqual(role, "admin")

    # Invitation Tests

    def test_create_invitation(self):
        """Test creating an invitation"""
        org_id = self.manager.create_organization("Test Org", "test-org")
        admin_id = self.manager.create_user("admin", "admin@example.com", "hash")

        token = self.manager.create_invitation(
            org_id,
            email="newuser@example.com",
            role="member",
            invited_by=admin_id
        )

        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)
        self.assertEqual(len(token), 32)

    def test_get_invitation(self):
        """Test getting an invitation"""
        org_id = self.manager.create_organization("Test Org", "test-org")
        admin_id = self.manager.create_user("admin", "admin@example.com", "hash")

        token = self.manager.create_invitation(
            org_id,
            email="newuser@example.com",
            role="member",
            invited_by=admin_id
        )

        invitation = self.manager.get_invitation(token)
        self.assertIsNotNone(invitation)
        self.assertEqual(invitation['email'], "newuser@example.com")
        self.assertEqual(invitation['role'], "member")

    def test_accept_invitation(self):
        """Test accepting an invitation"""
        org_id = self.manager.create_organization("Test Org", "test-org")
        admin_id = self.manager.create_user("admin", "admin@example.com", "hash")
        user_id = self.manager.create_user("newuser", "newuser@example.com", "hash")

        token = self.manager.create_invitation(
            org_id,
            email="newuser@example.com",
            role="member",
            invited_by=admin_id
        )

        success = self.manager.accept_invitation(token, user_id)
        self.assertTrue(success)

        # Verify user is now a member
        self.assertTrue(self.manager.is_member(org_id, user_id))

    # Usage Tracking Tests

    def test_track_usage(self):
        """Test tracking usage"""
        org_id = self.manager.create_organization("Test Org", "test-org")

        # track_usage doesn't return a value, just call it
        self.manager.track_usage(org_id, "api_calls", 10)

    def test_get_usage(self):
        """Test getting usage statistics"""
        org_id = self.manager.create_organization("Test Org", "test-org")

        self.manager.track_usage(org_id, "api_calls", 10)
        self.manager.track_usage(org_id, "storage", 1024)

        usage = self.manager.get_usage(org_id)
        self.assertIsNotNone(usage)
        self.assertEqual(usage.get("api_calls"), 10)
        self.assertEqual(usage.get("storage"), 1024)

    def test_check_quota(self):
        """Test checking quota limits"""
        org_id = self.manager.create_organization("Test Org", "test-org")

        # Default quota should allow operations
        within_quota = self.manager.check_quota(org_id, "users")
        self.assertTrue(within_quota)


if __name__ == '__main__':
    unittest.main()
