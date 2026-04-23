"""
End-to-End Workflow Tests

Test complete code review workflows from PR creation to completion.
"""

import pytest
import time
from fastapi.testclient import TestClient
from typing import Dict, Any


class TestCompleteReviewWorkflow:
    """Test complete review workflow from start to finish."""

    def test_full_review_lifecycle(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        sample_repository: Dict[str, Any],
        sample_pr_data: Dict[str, Any]
    ):
        """Test complete review lifecycle: create PR -> assign -> review -> complete."""

        # Step 1: Register repository
        response = client.post(
            "/api/repositories",
            json=sample_repository,
            headers=auth_headers
        )
        assert response.status_code in [200, 201]
        repo_id = response.json().get("id") or response.json().get("repository_id")

        # Step 2: Create pull request
        pr_data = {**sample_pr_data, "repository": sample_repository["name"]}
        response = client.post(
            "/api/reviews/create",
            json=pr_data,
            headers=auth_headers
        )
        assert response.status_code in [200, 201]
        review_id = response.json().get("review_id")
        assert review_id is not None

        # Step 3: Get review status
        response = client.get(
            f"/api/reviews/{review_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        review = response.json()
        assert review["status"] in ["pending", "in_progress"]

        # Step 4: Assign reviewers
        response = client.post(
            f"/api/reviews/{review_id}/assign",
            json={"reviewers": ["alice", "bob"]},
            headers=auth_headers
        )
        assert response.status_code == 200

        # Step 5: Add review comments
        response = client.post(
            f"/api/reviews/{review_id}/comments",
            json={
                "file": "src/main.py",
                "line": 10,
                "message": "Consider adding error handling",
                "severity": "medium"
            },
            headers=auth_headers
        )
        assert response.status_code in [200, 201]

        # Step 6: Complete review
        response = client.post(
            f"/api/reviews/{review_id}/complete",
            json={"decision": "approved", "summary": "LGTM"},
            headers=auth_headers
        )
        assert response.status_code == 200

        # Step 7: Verify final status
        response = client.get(
            f"/api/reviews/{review_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        final_review = response.json()
        assert final_review["status"] == "completed"

    def test_automated_review_trigger(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        sample_repository: Dict[str, Any],
        sample_pr_data: Dict[str, Any]
    ):
        """Test automated review triggering on PR creation."""

        # Register repository with auto_review enabled
        repo_data = {**sample_repository, "auto_review": True}
        response = client.post(
            "/api/repositories",
            json=repo_data,
            headers=auth_headers
        )
        assert response.status_code in [200, 201]

        # Create PR (should auto-trigger review)
        pr_data = {**sample_pr_data, "repository": repo_data["name"]}
        response = client.post(
            "/api/reviews/create",
            json=pr_data,
            headers=auth_headers
        )
        assert response.status_code in [200, 201]
        review_id = response.json().get("review_id")

        # Verify review was created
        response = client.get(
            f"/api/reviews/{review_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        review = response.json()
        assert review["status"] in ["pending", "in_progress"]

    def test_review_with_ai_assistant(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        sample_code: str
    ):
        """Test review workflow with AI assistant integration."""

        # Step 1: Get AI code explanation
        response = client.post(
            "/api/ai-assistant/explain-code",
            json={
                "code": sample_code,
                "language": "python",
                "context": "Review context"
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        explanation = response.json()
        assert "explanation" in explanation

        # Step 2: Get AI review suggestions
        response = client.post(
            "/api/ai-assistant/suggest-review",
            json={
                "code": sample_code,
                "file_path": "src/main.py",
                "context": {}
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        suggestions = response.json()
        assert "suggestions" in suggestions

        # Step 3: Optimize review comment
        response = client.post(
            "/api/ai-assistant/optimize-comment",
            json={
                "comment": "This code is bad",
                "context": {}
            },
            headers=auth_headers
        )
        assert response.status_code == 200
        optimized = response.json()
        assert "optimized_comment" in optimized


class TestScheduledReviewWorkflow:
    """Test scheduled review workflows."""

    def test_schedule_periodic_review(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        sample_repository: Dict[str, Any]
    ):
        """Test scheduling periodic reviews."""

        # Add schedule
        response = client.post(
            "/api/scheduler/schedules",
            json={
                "name": "daily-review",
                "repository": sample_repository["name"],
                "cron_expression": "0 9 * * *",  # Daily at 9 AM
                "branches": ["main"],
                "enabled": True
            },
            headers=auth_headers
        )
        assert response.status_code in [200, 201]
        schedule_id = response.json().get("schedule_id")

        # List schedules
        response = client.get(
            "/api/scheduler/schedules",
            headers=auth_headers
        )
        assert response.status_code == 200
        schedules = response.json()
        assert len(schedules) > 0

    def test_trigger_based_review(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        sample_repository: Dict[str, Any]
    ):
        """Test trigger-based review execution."""

        # Add trigger
        response = client.post(
            "/api/scheduler/triggers",
            json={
                "name": "pr-opened-trigger",
                "repository": sample_repository["name"],
                "trigger_type": "PR_OPENED",
                "branch_filter": "feature/*",
                "priority": "HIGH",
                "enabled": True
            },
            headers=auth_headers
        )
        assert response.status_code in [200, 201]
        trigger_id = response.json().get("trigger_id")

        # List triggers
        response = client.get(
            "/api/scheduler/triggers",
            headers=auth_headers
        )
        assert response.status_code == 200
        triggers = response.json()
        assert len(triggers) > 0


class TestReportGenerationWorkflow:
    """Test report generation workflows."""

    def test_generate_and_export_report(
        self,
        client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test report generation and export."""

        # Generate report
        response = client.post(
            "/api/reports/generate",
            json={
                "report_type": "SUMMARY",
                "time_range": "7d",
                "repositories": ["test-repo"],
                "format": "JSON"
            },
            headers=auth_headers
        )
        assert response.status_code in [200, 201]
        report_id = response.json().get("report_id")

        # Get report
        response = client.get(
            f"/api/reports/{report_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        report = response.json()
        assert "data" in report

        # Export report in different formats
        for format_type in ["JSON", "MARKDOWN", "HTML"]:
            response = client.get(
                f"/api/reports/{report_id}/export",
                params={"format": format_type},
                headers=auth_headers
            )
            assert response.status_code == 200


class TestCollaborationWorkflow:
    """Test collaboration workflows."""

    def test_multi_reviewer_collaboration(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        sample_pr_data: Dict[str, Any]
    ):
        """Test multiple reviewers collaborating on a review."""

        # Create review
        response = client.post(
            "/api/reviews/create",
            json=sample_pr_data,
            headers=auth_headers
        )
        assert response.status_code in [200, 201]
        review_id = response.json().get("review_id")

        # Create collaboration session
        response = client.post(
            "/api/collaboration/sessions",
            json={
                "review_id": review_id,
                "participants": ["alice", "bob", "charlie"]
            },
            headers=auth_headers
        )
        assert response.status_code in [200, 201]
        session_id = response.json().get("session_id")

        # Add threaded comments
        response = client.post(
            f"/api/collaboration/sessions/{session_id}/comments",
            json={
                "file": "src/main.py",
                "line": 10,
                "comment": "Should we refactor this?",
                "type": "QUESTION"
            },
            headers=auth_headers
        )
        assert response.status_code in [200, 201]
        comment_id = response.json().get("comment_id")

        # Reply to comment
        response = client.post(
            f"/api/collaboration/comments/{comment_id}/replies",
            json={
                "comment": "Yes, let's extract it to a helper function",
                "author": "bob"
            },
            headers=auth_headers
        )
        assert response.status_code in [200, 201]

    def test_decision_voting(
        self,
        client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test decision voting in collaboration."""

        # Create decision
        response = client.post(
            "/api/collaboration/decisions",
            json={
                "session_id": "session-001",
                "title": "Should we merge this PR?",
                "options": ["Approve", "Request Changes", "Reject"],
                "voters": ["alice", "bob", "charlie"]
            },
            headers=auth_headers
        )
        assert response.status_code in [200, 201]
        decision_id = response.json().get("decision_id")

        # Cast votes
        for voter, choice in [("alice", "Approve"), ("bob", "Approve")]:
            response = client.post(
                f"/api/collaboration/decisions/{decision_id}/vote",
                json={"voter": voter, "choice": choice},
                headers=auth_headers
            )
            assert response.status_code == 200

        # Get results
        response = client.get(
            f"/api/collaboration/decisions/{decision_id}/results",
            headers=auth_headers
        )
        assert response.status_code == 200
        results = response.json()
        assert "votes" in results


class TestKnowledgeBaseWorkflow:
    """Test knowledge base integration workflows."""

    def test_search_and_apply_knowledge(
        self,
        client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test searching and applying knowledge base entries."""

        # Add knowledge entry
        response = client.post(
            "/api/knowledge/entries",
            json={
                "title": "Python Best Practices",
                "content": "Always use type hints...",
                "category": "BEST_PRACTICE",
                "tags": ["python", "typing"],
                "language": "python"
            },
            headers=auth_headers
        )
        assert response.status_code in [200, 201]
        entry_id = response.json().get("entry_id")

        # Search knowledge base
        response = client.get(
            "/api/knowledge/search",
            params={"query": "python type hints", "category": "BEST_PRACTICE"},
            headers=auth_headers
        )
        assert response.status_code == 200
        results = response.json()
        assert len(results) > 0

        # Get related entries
        response = client.get(
            f"/api/knowledge/entries/{entry_id}/related",
            params={"limit": 5},
            headers=auth_headers
        )
        assert response.status_code == 200
        related = response.json()
        assert isinstance(related, list)
