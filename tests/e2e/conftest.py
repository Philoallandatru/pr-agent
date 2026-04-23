"""
End-to-End Integration Test Configuration

Provides test fixtures, utilities, and configuration for E2E testing.
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import Generator, Dict, Any
import pytest
from fastapi.testclient import TestClient
from pr_agent.servers.web_platform import app
from pr_agent.storage.database import Database


@pytest.fixture(scope="session")
def test_data_dir() -> Generator[Path, None, None]:
    """Create temporary directory for test data."""
    temp_dir = Path(tempfile.mkdtemp(prefix="pr_agent_e2e_"))
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def test_database(test_data_dir: Path) -> Generator[Database, None, None]:
    """Create test database."""
    db_path = test_data_dir / "test.db"
    db = Database(str(db_path))
    db.initialize()
    yield db
    db.close()


@pytest.fixture(scope="function")
def client(test_database: Database) -> Generator[TestClient, None, None]:
    """Create test client for API testing."""
    # Override database in app
    app.state.database = test_database

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def auth_headers(client: TestClient) -> Dict[str, str]:
    """Get authentication headers for API requests."""
    # Login to get token
    response = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "admin123"
        }
    )

    if response.status_code == 200:
        token = response.json().get("access_token")
        return {"Authorization": f"Bearer {token}"}

    # If login fails, return empty headers (some tests may not need auth)
    return {}


@pytest.fixture(scope="function")
def sample_repository() -> Dict[str, Any]:
    """Sample repository data for testing."""
    return {
        "name": "test-repo",
        "url": "https://github.com/test/repo",
        "branch": "main",
        "enabled": True,
        "auto_review": True
    }


@pytest.fixture(scope="function")
def sample_pr_data() -> Dict[str, Any]:
    """Sample pull request data for testing."""
    return {
        "pr_number": 123,
        "title": "Add new feature",
        "description": "This PR adds a new feature",
        "author": "developer",
        "branch": "feature/new-feature",
        "base_branch": "main",
        "files_changed": [
            "src/main.py",
            "tests/test_main.py"
        ],
        "additions": 50,
        "deletions": 10
    }


@pytest.fixture(scope="function")
def sample_code() -> str:
    """Sample code for testing."""
    return """
def calculate_sum(a: int, b: int) -> int:
    '''Calculate the sum of two numbers.'''
    return a + b

def process_data(data: list) -> dict:
    '''Process a list of data.'''
    result = {}
    for item in data:
        if item > 0:
            result[item] = item * 2
    return result
"""


@pytest.fixture(scope="function")
def sample_review_data() -> Dict[str, Any]:
    """Sample review data for testing."""
    return {
        "review_id": "review-001",
        "pr_id": "123",
        "repository": "test/repo",
        "author": "reviewer",
        "reviewers": ["alice", "bob"],
        "status": "pending",
        "comments": [],
        "quality_score": 0.0
    }


class TestDataGenerator:
    """Generate test data for various scenarios."""

    @staticmethod
    def generate_repositories(count: int = 5) -> list:
        """Generate multiple test repositories."""
        repos = []
        for i in range(count):
            repos.append({
                "name": f"repo-{i}",
                "url": f"https://github.com/test/repo-{i}",
                "branch": "main",
                "enabled": True,
                "auto_review": i % 2 == 0
            })
        return repos

    @staticmethod
    def generate_pull_requests(repo_name: str, count: int = 10) -> list:
        """Generate multiple test pull requests."""
        prs = []
        for i in range(count):
            prs.append({
                "pr_number": i + 1,
                "title": f"PR #{i + 1}: Feature update",
                "description": f"This PR updates feature {i}",
                "author": f"dev-{i % 3}",
                "branch": f"feature/update-{i}",
                "base_branch": "main",
                "repository": repo_name,
                "files_changed": [f"src/file{i}.py"],
                "additions": 20 + i * 5,
                "deletions": 5 + i
            })
        return prs

    @staticmethod
    def generate_reviews(pr_id: str, count: int = 3) -> list:
        """Generate multiple test reviews."""
        reviews = []
        reviewers = ["alice", "bob", "charlie"]
        for i in range(count):
            reviews.append({
                "review_id": f"review-{pr_id}-{i}",
                "pr_id": pr_id,
                "reviewer": reviewers[i % len(reviewers)],
                "status": ["approved", "changes_requested", "commented"][i % 3],
                "comments": [
                    {
                        "line": 10 + i,
                        "message": f"Comment {i}",
                        "severity": "medium"
                    }
                ],
                "quality_score": 70 + i * 5
            })
        return reviews


@pytest.fixture(scope="session")
def test_data_generator() -> TestDataGenerator:
    """Provide test data generator."""
    return TestDataGenerator()


# Environment setup
def pytest_configure(config):
    """Configure pytest environment."""
    # Set test environment variables
    os.environ["TESTING"] = "true"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["LOG_LEVEL"] = "DEBUG"


def pytest_unconfigure(config):
    """Cleanup after tests."""
    # Clean up environment variables
    os.environ.pop("TESTING", None)
    os.environ.pop("DATABASE_URL", None)
    os.environ.pop("LOG_LEVEL", None)
