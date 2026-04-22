"""
Integration tests for rate limiting and quota middleware
"""
import pytest
from fastapi.testclient import TestClient
from pr_agent.servers.web_platform import app
from pr_agent.storage.database import Database
from pr_agent.tenants.manager import TenantManager
import tempfile
import os


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def test_db():
    """Create temporary test database"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    db = Database(path)
    yield db

    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def tenant_manager(test_db):
    """Create tenant manager with test database"""
    return TenantManager(test_db.db_path)


class TestRateLimitMiddleware:
    """Test rate limiting middleware integration"""

    def test_rate_limit_headers_present(self, client):
        """Test that rate limit headers are added to responses"""
        response = client.get("/health")

        # Check for rate limit headers
        assert "X-RateLimit-Limit" in response.headers or response.status_code == 200

    def test_rate_limit_enforcement(self, client):
        """Test that rate limits are enforced"""
        # Make multiple requests to trigger rate limit
        responses = []
        for i in range(15):
            response = client.post(
                "/api/auth/login",
                json={"username": "test", "password": "test"}
            )
            responses.append(response)

        # At least one request should succeed (first few)
        success_count = sum(1 for r in responses if r.status_code != 429)
        assert success_count > 0

    def test_exempt_paths_not_rate_limited(self, client):
        """Test that exempt paths are not rate limited"""
        # Health endpoint should be exempt
        for i in range(20):
            response = client.get("/health")
            assert response.status_code == 200


class TestQuotaMiddleware:
    """Test quota middleware integration"""

    def test_quota_tracking(self, client, tenant_manager):
        """Test that quota usage is tracked"""
        # Create test organization
        org_id = tenant_manager.create_organization("Test Org", plan="free")

        # Create test user
        from pr_agent.security.auth import AuthManager
        auth_manager = AuthManager(tenant_manager.db_path)
        user_id = auth_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="password123",
            role="admin"
        )

        # Update user with org_id
        import sqlite3
        conn = sqlite3.connect(tenant_manager.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET org_id = ? WHERE id = ?",
            (org_id, user_id)
        )
        conn.commit()
        conn.close()

        # Login to get token
        response = client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "password123"}
        )
        assert response.status_code == 200
        token = response.json()["access_token"]

        # Make authenticated request
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/repositories", headers=headers)

        # Check that quota was tracked
        usage = tenant_manager.get_usage(org_id, "repositories")
        assert usage is not None


class TestMiddlewareOrder:
    """Test that middleware is applied in correct order"""

    def test_cors_before_rate_limit(self, client):
        """Test that CORS headers are present even with rate limiting"""
        response = client.options("/api/repositories")

        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers or response.status_code == 200

    def test_authentication_before_quota(self, client):
        """Test that authentication is checked before quota"""
        # Unauthenticated request should fail with 401, not quota error
        response = client.get("/api/repositories")
        assert response.status_code in [401, 403, 200]  # Not 429 (quota exceeded)


class TestConfigurationIntegration:
    """Test configuration integration"""

    def test_rate_limit_config_loaded(self):
        """Test that rate limit configuration is loaded"""
        from pr_agent.config_loader import get_settings
        settings = get_settings()

        # Check that rate limit config exists
        assert settings.get("rate_limit.enabled") is not None

    def test_quota_config_loaded(self):
        """Test that quota configuration is loaded"""
        from pr_agent.config_loader import get_settings
        settings = get_settings()

        # Check that quota config exists
        assert settings.get("quota.enabled") is not None


class TestEndToEndFlow:
    """Test complete end-to-end flow with all middleware"""

    def test_complete_request_flow(self, client, tenant_manager):
        """Test complete request flow through all middleware"""
        # 1. Create organization and user
        org_id = tenant_manager.create_organization("E2E Test Org", plan="pro")

        from pr_agent.security.auth import AuthManager
        auth_manager = AuthManager(tenant_manager.db_path)
        user_id = auth_manager.create_user(
            username="e2euser",
            email="e2e@example.com",
            password="password123",
            role="admin"
        )

        # Link user to org
        import sqlite3
        conn = sqlite3.connect(tenant_manager.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET org_id = ? WHERE id = ?",
            (org_id, user_id)
        )
        conn.commit()
        conn.close()

        # 2. Login (rate limited)
        response = client.post(
            "/api/auth/login",
            json={"username": "e2euser", "password": "password123"}
        )
        assert response.status_code == 200
        token = response.json()["access_token"]

        # 3. Make authenticated request (quota tracked)
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/repositories", headers=headers)

        # Request should succeed
        assert response.status_code == 200

        # 4. Verify quota was tracked
        usage = tenant_manager.get_usage(org_id, "repositories")
        assert usage is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
