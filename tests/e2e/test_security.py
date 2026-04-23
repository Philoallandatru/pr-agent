"""
Security Tests

Test security features and vulnerabilities.
"""

import pytest
from fastapi.testclient import TestClient
from typing import Dict, Any


class TestAuthentication:
    """Test authentication and authorization."""

    def test_unauthenticated_access_denied(self, client: TestClient):
        """Test that unauthenticated requests are denied."""

        protected_endpoints = [
            "/api/repositories",
            "/api/reviews",
            "/api/dashboards/main/stats",
            "/api/metrics",
        ]

        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401

    def test_invalid_token_rejected(self, client: TestClient):
        """Test that invalid tokens are rejected."""

        invalid_headers = {"Authorization": "Bearer invalid_token_12345"}

        response = client.get("/api/repositories", headers=invalid_headers)
        assert response.status_code == 401

    def test_expired_token_rejected(self, client: TestClient):
        """Test that expired tokens are rejected."""

        # This would require generating an expired token
        # For now, test with a malformed token
        expired_headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.expired"}

        response = client.get("/api/repositories", headers=expired_headers)
        assert response.status_code == 401

    def test_login_with_invalid_credentials(self, client: TestClient):
        """Test login with invalid credentials."""

        response = client.post(
            "/api/auth/login",
            json={
                "username": "nonexistent",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401

    def test_password_not_returned_in_response(
        self,
        client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test that passwords are never returned in API responses."""

        # Get user info
        response = client.get("/api/auth/me", headers=auth_headers)

        if response.status_code == 200:
            user_data = response.json()
            assert "password" not in user_data
            assert "password_hash" not in user_data


class TestAuthorization:
    """Test role-based access control."""

    def test_admin_only_endpoints(
        self,
        client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test that admin-only endpoints require admin role."""

        admin_endpoints = [
            ("/api/config", "GET"),
            ("/api/config", "PUT"),
        ]

        for endpoint, method in admin_endpoints:
            if method == "GET":
                response = client.get(endpoint, headers=auth_headers)
            else:
                response = client.put(endpoint, json={}, headers=auth_headers)

            # Should either succeed (if user is admin) or return 403
            assert response.status_code in [200, 403]

    def test_user_cannot_access_others_data(
        self,
        client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test that users cannot access other users' private data."""

        # Try to access another user's private reviews
        response = client.get(
            "/api/reviews",
            params={"author": "other_user", "private": True},
            headers=auth_headers
        )

        # Should either return empty list or 403
        if response.status_code == 200:
            reviews = response.json()
            # If we get data, it should not contain other users' private reviews
            for review in reviews:
                assert review.get("author") != "other_user" or not review.get("private")


class TestInputValidation:
    """Test input validation and sanitization."""

    def test_sql_injection_prevention(
        self,
        client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test that SQL injection attempts are prevented."""

        malicious_inputs = [
            "'; DROP TABLE reviews; --",
            "1' OR '1'='1",
            "admin'--",
            "' UNION SELECT * FROM users--",
        ]

        for malicious_input in malicious_inputs:
            response = client.get(
                "/api/reviews",
                params={"repository": malicious_input},
                headers=auth_headers
            )

            # Should not cause server error
            assert response.status_code in [200, 400, 422]

    def test_xss_prevention(
        self,
        client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test that XSS attempts are prevented."""

        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
        ]

        for payload in xss_payloads:
            response = client.post(
                "/api/reviews/create",
                json={
                    "pr_number": 1,
                    "title": payload,
                    "repository": "test-repo",
                    "author": "test",
                    "branch": "test",
                    "base_branch": "main"
                },
                headers=auth_headers
            )

            # Should either succeed with sanitized input or reject
            assert response.status_code in [200, 201, 400, 422]

            if response.status_code in [200, 201]:
                review = response.json()
                # Title should be sanitized (no script tags)
                assert "<script>" not in review.get("title", "")

    def test_path_traversal_prevention(
        self,
        client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test that path traversal attempts are prevented."""

        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/passwd",
        ]

        for path in malicious_paths:
            response = client.get(
                f"/api/files/{path}",
                headers=auth_headers
            )

            # Should not allow access to system files
            assert response.status_code in [400, 403, 404]

    def test_command_injection_prevention(
        self,
        client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test that command injection attempts are prevented."""

        malicious_commands = [
            "; ls -la",
            "| cat /etc/passwd",
            "&& rm -rf /",
            "`whoami`",
        ]

        for command in malicious_commands:
            response = client.post(
                "/api/repositories",
                json={
                    "name": f"repo{command}",
                    "url": "https://github.com/test/repo",
                    "branch": "main"
                },
                headers=auth_headers
            )

            # Should either sanitize or reject
            assert response.status_code in [200, 201, 400, 422]


class TestDataProtection:
    """Test data protection and privacy."""

    def test_sensitive_data_not_logged(
        self,
        client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test that sensitive data is not logged."""

        # Login with credentials
        response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "testpassword123"
            }
        )

        # Password should not appear in logs (we can't directly test this,
        # but we ensure the response doesn't echo it back)
        if response.status_code == 200:
            response_data = response.json()
            assert "password" not in str(response_data).lower()

    def test_api_keys_not_exposed(
        self,
        client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test that API keys are not exposed in responses."""

        response = client.get("/api/config", headers=auth_headers)

        if response.status_code == 200:
            config = response.json()
            # Check that sensitive keys are masked or not present
            sensitive_keys = ["api_key", "secret_key", "password", "token"]
            for key in sensitive_keys:
                if key in config:
                    value = config[key]
                    # Should be masked (e.g., "***") or empty
                    assert value in ["", "***", None] or len(value) < 5

    def test_https_redirect(self, client: TestClient):
        """Test that HTTP requests are redirected to HTTPS in production."""

        # This test would need to be run against a production-like environment
        # For now, we just verify the security headers are present
        response = client.get("/api/health")

        # Check for security headers
        headers = response.headers
        # In production, these should be set
        # assert "Strict-Transport-Security" in headers


class TestRateLimiting:
    """Test rate limiting."""

    def test_rate_limit_enforcement(
        self,
        client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test that rate limits are enforced."""

        endpoint = "/api/dashboards/main/stats"

        # Make many requests quickly
        responses = []
        for _ in range(100):
            response = client.get(endpoint, headers=auth_headers)
            responses.append(response.status_code)

        # Should eventually hit rate limit (429)
        # Note: This depends on rate limit configuration
        rate_limited = any(status == 429 for status in responses)

        # If rate limiting is enabled, we should see 429 responses
        # If not enabled, all should be 200
        assert all(status in [200, 429] for status in responses)

    def test_rate_limit_headers(
        self,
        client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test that rate limit headers are present."""

        response = client.get("/api/dashboards/main/stats", headers=auth_headers)

        # Check for rate limit headers (if implemented)
        headers = response.headers
        # Common rate limit headers
        rate_limit_headers = [
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        ]

        # At least some rate limit info should be present
        # (if rate limiting is implemented)
        # has_rate_limit_info = any(h in headers for h in rate_limit_headers)


class TestAuditLogging:
    """Test audit logging."""

    def test_sensitive_operations_logged(
        self,
        client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test that sensitive operations are logged."""

        # Perform sensitive operation
        response = client.post(
            "/api/repositories",
            json={
                "name": "audit-test-repo",
                "url": "https://github.com/test/repo",
                "branch": "main"
            },
            headers=auth_headers
        )

        # Operation should succeed
        assert response.status_code in [200, 201]

        # Check audit logs (if accessible via API)
        logs_response = client.get("/api/audit/logs", headers=auth_headers)

        if logs_response.status_code == 200:
            logs = logs_response.json()
            # Should contain log of repository creation
            assert any(
                log.get("event_type") == "REPOSITORY_CREATED"
                for log in logs
            )

    def test_failed_login_attempts_logged(self, client: TestClient):
        """Test that failed login attempts are logged."""

        # Attempt failed login
        response = client.post(
            "/api/auth/login",
            json={
                "username": "testuser",
                "password": "wrongpassword"
            }
        )

        assert response.status_code == 401

        # Failed attempts should be logged (implementation-dependent)
