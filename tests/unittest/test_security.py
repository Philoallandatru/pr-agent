"""
Unit tests for security and authentication module.
"""

import pytest
from datetime import datetime, timedelta

try:
    from pr_agent.security import (
        AuthManager,
        User,
        APIKey,
        auth_manager,
        hash_api_key_for_storage,
        generate_secure_token,
    )
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False


@pytest.mark.skipif(not SECURITY_AVAILABLE, reason="Security module not available")
class TestAuthManager:
    """Test AuthManager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.auth = AuthManager()

    def test_create_user(self):
        """Test user creation."""
        user = self.auth.create_user("testuser", "test@example.com", "password123", "viewer")

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == "viewer"
        assert user.hashed_password != "password123"  # Should be hashed

    def test_create_duplicate_user(self):
        """Test creating duplicate user raises error."""
        self.auth.create_user("testuser", "test@example.com", "password123")

        with pytest.raises(ValueError, match="already exists"):
            self.auth.create_user("testuser", "other@example.com", "password456")

    def test_authenticate_user_success(self):
        """Test successful user authentication."""
        self.auth.create_user("testuser", "test@example.com", "password123")

        user = self.auth.authenticate_user("testuser", "password123")
        assert user is not None
        assert user.username == "testuser"

    def test_authenticate_user_wrong_password(self):
        """Test authentication with wrong password."""
        self.auth.create_user("testuser", "test@example.com", "password123")

        user = self.auth.authenticate_user("testuser", "wrongpassword")
        assert user is None

    def test_authenticate_user_not_found(self):
        """Test authentication with non-existent user."""
        user = self.auth.authenticate_user("nonexistent", "password123")
        assert user is None

    def test_create_access_token(self):
        """Test JWT token creation."""
        token = self.auth.create_access_token(
            data={"sub": "testuser", "role": "admin"},
            expires_delta=timedelta(hours=1)
        )

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_token_success(self):
        """Test successful token verification."""
        token = self.auth.create_access_token(
            data={"sub": "testuser", "role": "admin"}
        )

        payload = self.auth.verify_token(token)
        assert payload is not None
        assert payload["sub"] == "testuser"
        assert payload["role"] == "admin"

    def test_verify_token_invalid(self):
        """Test verification of invalid token."""
        payload = self.auth.verify_token("invalid.token.here")
        assert payload is None

    def test_create_api_key(self):
        """Test API key creation."""
        key = self.auth.create_api_key("test-key", ["read", "write"])

        assert key is not None
        assert isinstance(key, str)
        assert len(key) > 0

    def test_verify_api_key_success(self):
        """Test successful API key verification."""
        key = self.auth.create_api_key("test-key", ["read", "write"])

        api_key = self.auth.verify_api_key(key)
        assert api_key is not None
        assert api_key.name == "test-key"
        assert api_key.permissions == ["read", "write"]
        assert api_key.last_used is not None

    def test_verify_api_key_invalid(self):
        """Test verification of invalid API key."""
        api_key = self.auth.verify_api_key("invalid-key")
        assert api_key is None

    def test_revoke_api_key(self):
        """Test API key revocation."""
        key = self.auth.create_api_key("test-key", ["read"])

        # Verify key exists
        assert self.auth.verify_api_key(key) is not None

        # Revoke key
        result = self.auth.revoke_api_key(key)
        assert result is True

        # Verify key no longer exists
        assert self.auth.verify_api_key(key) is None

    def test_revoke_nonexistent_api_key(self):
        """Test revoking non-existent API key."""
        result = self.auth.revoke_api_key("nonexistent-key")
        assert result is False

    def test_has_permission_admin(self):
        """Test admin has all permissions."""
        user = User("admin", "admin@example.com", "admin")

        assert self.auth.has_permission(user, "read") is True
        assert self.auth.has_permission(user, "write") is True
        assert self.auth.has_permission(user, "delete") is True

    def test_has_permission_editor(self):
        """Test editor has read and write permissions."""
        user = User("editor", "editor@example.com", "editor")

        assert self.auth.has_permission(user, "read") is True
        assert self.auth.has_permission(user, "write") is True
        assert self.auth.has_permission(user, "delete") is False

    def test_has_permission_viewer(self):
        """Test viewer has only read permission."""
        user = User("viewer", "viewer@example.com", "viewer")

        assert self.auth.has_permission(user, "read") is True
        assert self.auth.has_permission(user, "write") is False
        assert self.auth.has_permission(user, "delete") is False

    def test_has_permission_api_key(self):
        """Test API key permissions."""
        api_key = APIKey("test-key", "test", ["read", "write"], datetime.now())

        assert self.auth.has_permission(api_key, "read") is True
        assert self.auth.has_permission(api_key, "write") is True
        assert self.auth.has_permission(api_key, "delete") is False


@pytest.mark.skipif(not SECURITY_AVAILABLE, reason="Security module not available")
class TestUser:
    """Test User model."""

    def test_user_to_dict(self):
        """Test user serialization."""
        user = User("testuser", "test@example.com", "admin", "hashed_password")

        user_dict = user.to_dict()
        assert user_dict["username"] == "testuser"
        assert user_dict["email"] == "test@example.com"
        assert user_dict["role"] == "admin"
        assert "hashed_password" not in user_dict  # Should not expose password


@pytest.mark.skipif(not SECURITY_AVAILABLE, reason="Security module not available")
class TestAPIKey:
    """Test APIKey model."""

    def test_api_key_to_dict(self):
        """Test API key serialization."""
        created_at = datetime.now()
        api_key = APIKey("very-long-secret-key-12345", "test-key", ["read"], created_at)

        key_dict = api_key.to_dict()
        assert key_dict["key_prefix"] == "very-lon..."  # Only shows prefix
        assert key_dict["name"] == "test-key"
        assert key_dict["permissions"] == ["read"]
        assert key_dict["created_at"] == created_at.isoformat()
        assert key_dict["last_used"] is None

    def test_api_key_last_used(self):
        """Test API key last_used tracking."""
        api_key = APIKey("test-key", "test", ["read"], datetime.now())

        assert api_key.last_used is None

        api_key.last_used = datetime.now()
        assert api_key.last_used is not None


@pytest.mark.skipif(not SECURITY_AVAILABLE, reason="Security module not available")
class TestSecurityUtilities:
    """Test security utility functions."""

    def test_hash_api_key_for_storage(self):
        """Test API key hashing."""
        key = "test-api-key-12345"
        hashed = hash_api_key_for_storage(key)

        assert hashed != key
        assert len(hashed) == 64  # SHA256 produces 64 hex characters

        # Same key should produce same hash
        hashed2 = hash_api_key_for_storage(key)
        assert hashed == hashed2

    def test_generate_secure_token(self):
        """Test secure token generation."""
        token1 = generate_secure_token()
        token2 = generate_secure_token()

        assert token1 != token2  # Should be random
        assert len(token1) > 0
        assert len(token2) > 0

    def test_generate_secure_token_custom_length(self):
        """Test secure token generation with custom length."""
        token = generate_secure_token(length=16)
        assert len(token) > 0
        # URL-safe base64 encoding, so actual length varies


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
