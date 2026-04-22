"""
End-to-end integration tests for PR-Agent auto-review system.

Tests the complete workflow from authentication to PR review.
"""

import pytest
import requests
import time
from typing import Dict, Optional


class TestE2EWorkflow:
    """End-to-end workflow tests."""

    BASE_URL = "http://localhost:8000"

    @pytest.fixture(scope="class")
    def api_client(self):
        """Create API client with authentication."""
        return APIClient(self.BASE_URL)

    def test_01_health_check(self, api_client):
        """Test system health check."""
        response = api_client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_02_login_success(self, api_client):
        """Test successful login."""
        token = api_client.login("admin", "admin123")
        assert token is not None
        assert len(token) > 0

    def test_03_login_failure(self, api_client):
        """Test login with wrong credentials."""
        with pytest.raises(Exception):
            api_client.login("admin", "wrongpassword")

    def test_04_get_current_user(self, api_client):
        """Test getting current user info."""
        api_client.login("admin", "admin123")
        user = api_client.get_current_user()

        assert user["username"] == "admin"
        assert user["role"] == "admin"
        assert "email" in user

    def test_05_create_repository(self, api_client):
        """Test creating a repository."""
        api_client.login("admin", "admin123")

        repo_data = {
            "project_key": "TEST",
            "repo_slug": "test-repo",
            "name": "Test Repository",
            "url": "https://bitbucket.example.com/projects/TEST/repos/test-repo",
            "enabled": True
        }

        repo = api_client.create_repository(repo_data)
        assert repo["id"] is not None
        assert repo["project_key"] == "TEST"
        assert repo["repo_slug"] == "test-repo"

        # Store repo ID for later tests
        api_client.test_repo_id = repo["id"]

    def test_06_list_repositories(self, api_client):
        """Test listing repositories."""
        api_client.login("admin", "admin123")

        repos = api_client.list_repositories()
        assert isinstance(repos, list)
        assert len(repos) > 0

        # Find our test repo
        test_repo = next((r for r in repos if r["repo_slug"] == "test-repo"), None)
        assert test_repo is not None

    def test_07_get_repository(self, api_client):
        """Test getting a specific repository."""
        api_client.login("admin", "admin123")

        repo = api_client.get_repository(api_client.test_repo_id)
        assert repo["id"] == api_client.test_repo_id
        assert repo["repo_slug"] == "test-repo"

    def test_08_update_repository(self, api_client):
        """Test updating a repository."""
        api_client.login("admin", "admin123")

        update_data = {
            "enabled": False,
            "name": "Test Repository (Updated)"
        }

        repo = api_client.update_repository(api_client.test_repo_id, update_data)
        assert repo["enabled"] is False
        assert repo["name"] == "Test Repository (Updated)"

    def test_09_create_prompt_template(self, api_client):
        """Test creating a prompt template."""
        api_client.login("admin", "admin123")

        prompt_data = {
            "name": "test-prompt",
            "command": "review",
            "content": "Please review this PR carefully.",
            "is_active": True
        }

        prompt = api_client.create_prompt_template(prompt_data)
        assert prompt["id"] is not None
        assert prompt["name"] == "test-prompt"

        api_client.test_prompt_id = prompt["id"]

    def test_10_list_prompt_templates(self, api_client):
        """Test listing prompt templates."""
        api_client.login("admin", "admin123")

        prompts = api_client.list_prompt_templates()
        assert isinstance(prompts, list)

        test_prompt = next((p for p in prompts if p["name"] == "test-prompt"), None)
        assert test_prompt is not None

    def test_11_update_prompt_template(self, api_client):
        """Test updating a prompt template."""
        api_client.login("admin", "admin123")

        update_data = {
            "content": "Please review this PR very carefully.",
            "is_active": False
        }

        prompt = api_client.update_prompt_template(api_client.test_prompt_id, update_data)
        assert prompt["is_active"] is False
        assert "very carefully" in prompt["content"]

    def test_12_get_statistics(self, api_client):
        """Test getting system statistics."""
        api_client.login("admin", "admin123")

        stats = api_client.get_statistics()
        assert "repositories" in stats
        assert "reviews" in stats
        assert stats["repositories"]["total"] > 0

    def test_13_get_system_status(self, api_client):
        """Test getting system status."""
        api_client.login("admin", "admin123")

        status = api_client.get_system_status()
        assert "polling_active" in status
        assert "last_poll" in status

    def test_14_get_logs(self, api_client):
        """Test getting system logs."""
        api_client.login("admin", "admin123")

        logs = api_client.get_logs(limit=10)
        assert "logs" in logs
        assert isinstance(logs["logs"], list)

    def test_15_create_api_key(self, api_client):
        """Test creating an API key."""
        api_client.login("admin", "admin123")

        key_data = {
            "name": "test-api-key",
            "permissions": ["read", "write"]
        }

        result = api_client.create_api_key(key_data)
        assert "key" in result
        assert len(result["key"]) > 0

        api_client.test_api_key = result["key"]

    def test_16_use_api_key(self, api_client):
        """Test using API key for authentication."""
        # Use API key instead of JWT
        api_client.token = None
        api_client.api_key = api_client.test_api_key

        repos = api_client.list_repositories()
        assert isinstance(repos, list)

    def test_17_list_api_keys(self, api_client):
        """Test listing API keys."""
        api_client.login("admin", "admin123")

        keys = api_client.list_api_keys()
        assert isinstance(keys, list)

        test_key = next((k for k in keys if k["name"] == "test-api-key"), None)
        assert test_key is not None

    def test_18_revoke_api_key(self, api_client):
        """Test revoking an API key."""
        api_client.login("admin", "admin123")

        # Get key prefix
        keys = api_client.list_api_keys()
        test_key = next((k for k in keys if k["name"] == "test-api-key"), None)
        key_prefix = test_key["key_prefix"]

        result = api_client.revoke_api_key(key_prefix)
        assert result["message"] == "API key revoked"

    def test_19_viewer_permissions(self, api_client):
        """Test viewer role permissions."""
        # Create a viewer user
        api_client.login("admin", "admin123")

        # Try to create repository as viewer (should fail)
        # This would require creating a viewer user first
        # Skipping for now as it requires user management endpoints
        pass

    def test_20_delete_prompt_template(self, api_client):
        """Test deleting a prompt template."""
        api_client.login("admin", "admin123")

        api_client.delete_prompt_template(api_client.test_prompt_id)

        # Verify deletion
        prompts = api_client.list_prompt_templates()
        test_prompt = next((p for p in prompts if p["id"] == api_client.test_prompt_id), None)
        assert test_prompt is None

    def test_21_delete_repository(self, api_client):
        """Test deleting a repository."""
        api_client.login("admin", "admin123")

        api_client.delete_repository(api_client.test_repo_id)

        # Verify deletion
        repos = api_client.list_repositories()
        test_repo = next((r for r in repos if r["id"] == api_client.test_repo_id), None)
        assert test_repo is None


class APIClient:
    """Helper class for API interactions."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.token: Optional[str] = None
        self.api_key: Optional[str] = None
        self.test_repo_id: Optional[int] = None
        self.test_prompt_id: Optional[int] = None
        self.test_api_key: Optional[str] = None

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {"Content-Type": "application/json"}

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        elif self.api_key:
            headers["X-API-Key"] = self.api_key

        return headers

    def get(self, path: str, **kwargs):
        """Make GET request."""
        url = f"{self.base_url}{path}"
        headers = self._get_headers()
        response = requests.get(url, headers=headers, **kwargs)
        response.raise_for_status()
        return response

    def post(self, path: str, data: Dict = None, **kwargs):
        """Make POST request."""
        url = f"{self.base_url}{path}"
        headers = self._get_headers()
        response = requests.post(url, json=data, headers=headers, **kwargs)
        response.raise_for_status()
        return response

    def put(self, path: str, data: Dict = None, **kwargs):
        """Make PUT request."""
        url = f"{self.base_url}{path}"
        headers = self._get_headers()
        response = requests.put(url, json=data, headers=headers, **kwargs)
        response.raise_for_status()
        return response

    def delete(self, path: str, **kwargs):
        """Make DELETE request."""
        url = f"{self.base_url}{path}"
        headers = self._get_headers()
        response = requests.delete(url, headers=headers, **kwargs)
        response.raise_for_status()
        return response

    def login(self, username: str, password: str) -> str:
        """Login and get JWT token."""
        response = self.post("/api/auth/login", {
            "username": username,
            "password": password
        })
        data = response.json()
        self.token = data["access_token"]
        return self.token

    def get_current_user(self) -> Dict:
        """Get current user info."""
        response = self.get("/api/auth/me")
        return response.json()

    def create_repository(self, data: Dict) -> Dict:
        """Create a repository."""
        response = self.post("/api/repositories", data)
        return response.json()

    def list_repositories(self) -> list:
        """List all repositories."""
        response = self.get("/api/repositories")
        data = response.json()
        return data.get("repositories", [])

    def get_repository(self, repo_id: int) -> Dict:
        """Get a specific repository."""
        response = self.get(f"/api/repositories/{repo_id}")
        return response.json()

    def update_repository(self, repo_id: int, data: Dict) -> Dict:
        """Update a repository."""
        response = self.put(f"/api/repositories/{repo_id}", data)
        return response.json()

    def delete_repository(self, repo_id: int):
        """Delete a repository."""
        self.delete(f"/api/repositories/{repo_id}")

    def create_prompt_template(self, data: Dict) -> Dict:
        """Create a prompt template."""
        response = self.post("/api/prompts", data)
        return response.json()

    def list_prompt_templates(self) -> list:
        """List all prompt templates."""
        response = self.get("/api/prompts")
        data = response.json()
        return data.get("prompts", [])

    def update_prompt_template(self, prompt_id: int, data: Dict) -> Dict:
        """Update a prompt template."""
        response = self.put(f"/api/prompts/{prompt_id}", data)
        return response.json()

    def delete_prompt_template(self, prompt_id: int):
        """Delete a prompt template."""
        self.delete(f"/api/prompts/{prompt_id}")

    def get_statistics(self) -> Dict:
        """Get system statistics."""
        response = self.get("/api/metrics")
        return response.json()

    def get_system_status(self) -> Dict:
        """Get system status."""
        response = self.get("/api/status")
        return response.json()

    def get_logs(self, level: str = None, limit: int = 100) -> Dict:
        """Get system logs."""
        params = {"limit": limit}
        if level:
            params["level"] = level
        response = self.get("/api/logs", params=params)
        return response.json()

    def create_api_key(self, data: Dict) -> Dict:
        """Create an API key."""
        response = self.post("/api/auth/api-keys", data)
        return response.json()

    def list_api_keys(self) -> list:
        """List all API keys."""
        response = self.get("/api/auth/api-keys")
        data = response.json()
        return data.get("keys", [])

    def revoke_api_key(self, key_prefix: str) -> Dict:
        """Revoke an API key."""
        response = self.delete(f"/api/auth/api-keys/{key_prefix}")
        return response.json()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
