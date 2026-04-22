"""Unit tests for assignment system."""

import pytest
from datetime import datetime, timezone
from pr_agent.assignment import (
    AssignmentEngine,
    Reviewer,
    Assignment,
    AssignmentStrategy,
    ReviewerStatus,
    get_assignment_engine
)


class TestReviewer:
    """Test Reviewer class."""

    def test_create_reviewer(self):
        """Test creating a reviewer."""
        reviewer = Reviewer(
            reviewer_id="user1",
            name="John Doe",
            email="john@example.com",
            skills=["python", "javascript"],
            file_patterns=["**/*.py", "**/*.js"]
        )

        assert reviewer.reviewer_id == "user1"
        assert reviewer.name == "John Doe"
        assert len(reviewer.skills) == 2
        assert reviewer.status == ReviewerStatus.AVAILABLE

    def test_is_available(self):
        """Test availability check."""
        reviewer = Reviewer(
            reviewer_id="user1",
            name="John Doe",
            email="john@example.com",
            max_reviews=3,
            current_reviews=2
        )

        assert reviewer.is_available() is True

        reviewer.current_reviews = 3
        assert reviewer.is_available() is False

        reviewer.status = ReviewerStatus.BUSY
        assert reviewer.is_available() is False

    def test_can_review_file(self):
        """Test file pattern matching."""
        reviewer = Reviewer(
            reviewer_id="user1",
            name="John Doe",
            email="john@example.com",
            file_patterns=["**/*.py", "src/**/*.js"]
        )

        assert reviewer.can_review_file("app.py") is True
        assert reviewer.can_review_file("src/main.js") is True
        assert reviewer.can_review_file("test.go") is False

    def test_can_review_file_no_restrictions(self):
        """Test file review with no pattern restrictions."""
        reviewer = Reviewer(
            reviewer_id="user1",
            name="John Doe",
            email="john@example.com",
            file_patterns=[]
        )

        assert reviewer.can_review_file("any_file.txt") is True

    def test_has_skill(self):
        """Test skill checking."""
        reviewer = Reviewer(
            reviewer_id="user1",
            name="John Doe",
            email="john@example.com",
            skills=["Python", "JavaScript", "Go"]
        )

        assert reviewer.has_skill("python") is True
        assert reviewer.has_skill("JAVASCRIPT") is True
        assert reviewer.has_skill("rust") is False

    def test_to_dict(self):
        """Test converting reviewer to dictionary."""
        reviewer = Reviewer(
            reviewer_id="user1",
            name="John Doe",
            email="john@example.com",
            skills=["python"]
        )

        data = reviewer.to_dict()
        assert data["reviewer_id"] == "user1"
        assert data["status"] == "available"

    def test_from_dict(self):
        """Test creating reviewer from dictionary."""
        data = {
            "reviewer_id": "user1",
            "name": "John Doe",
            "email": "john@example.com",
            "skills": ["python"],
            "file_patterns": ["**/*.py"],
            "max_reviews": 5,
            "current_reviews": 0,
            "status": "available",
            "priority": 1,
            "metadata": {}
        }

        reviewer = Reviewer.from_dict(data)
        assert reviewer.reviewer_id == "user1"
        assert reviewer.status == ReviewerStatus.AVAILABLE


class TestAssignment:
    """Test Assignment class."""

    def test_create_assignment(self):
        """Test creating an assignment."""
        assignment = Assignment(
            assignment_id="pr123_user1",
            pull_request_id="pr123",
            repository="org/repo",
            reviewer_id="user1",
            assigned_at=datetime.now(timezone.utc),
            files=["app.py", "test.py"]
        )

        assert assignment.assignment_id == "pr123_user1"
        assert assignment.pull_request_id == "pr123"
        assert assignment.completed is False

    def test_to_dict(self):
        """Test converting assignment to dictionary."""
        assignment = Assignment(
            assignment_id="pr123_user1",
            pull_request_id="pr123",
            repository="org/repo",
            reviewer_id="user1",
            assigned_at=datetime.now(timezone.utc)
        )

        data = assignment.to_dict()
        assert data["assignment_id"] == "pr123_user1"
        assert data["strategy"] == "load_balanced"

    def test_from_dict(self):
        """Test creating assignment from dictionary."""
        data = {
            "assignment_id": "pr123_user1",
            "pull_request_id": "pr123",
            "repository": "org/repo",
            "reviewer_id": "user1",
            "assigned_at": datetime.now(timezone.utc).isoformat(),
            "files": ["app.py"],
            "strategy": "load_balanced",
            "completed": False,
            "completed_at": None,
            "metadata": {}
        }

        assignment = Assignment.from_dict(data)
        assert assignment.assignment_id == "pr123_user1"
        assert assignment.strategy == AssignmentStrategy.LOAD_BALANCED


class TestAssignmentEngine:
    """Test AssignmentEngine class."""

    @pytest.fixture
    def temp_storage(self, tmp_path):
        """Create temporary storage directory."""
        return tmp_path / "assignments"

    @pytest.fixture
    def engine(self, temp_storage):
        """Create assignment engine with temporary storage."""
        return AssignmentEngine(storage_path=str(temp_storage))

    @pytest.fixture
    def reviewers(self):
        """Create test reviewers."""
        return [
            Reviewer(
                reviewer_id="user1",
                name="Alice",
                email="alice@example.com",
                skills=["python", "backend"],
                file_patterns=["**/*.py"],
                max_reviews=5,
                priority=2
            ),
            Reviewer(
                reviewer_id="user2",
                name="Bob",
                email="bob@example.com",
                skills=["javascript", "frontend"],
                file_patterns=["**/*.js", "**/*.jsx"],
                max_reviews=3,
                priority=1
            ),
            Reviewer(
                reviewer_id="user3",
                name="Charlie",
                email="charlie@example.com",
                skills=["python", "javascript"],
                file_patterns=["**/*.py", "**/*.js"],
                max_reviews=4,
                priority=1
            )
        ]

    def test_register_reviewer(self, engine):
        """Test registering a reviewer."""
        reviewer = Reviewer(
            reviewer_id="user1",
            name="John Doe",
            email="john@example.com"
        )

        engine.register_reviewer(reviewer)
        assert engine.get_reviewer("user1") is not None

    def test_unregister_reviewer(self, engine):
        """Test unregistering a reviewer."""
        reviewer = Reviewer(
            reviewer_id="user1",
            name="John Doe",
            email="john@example.com"
        )

        engine.register_reviewer(reviewer)
        assert engine.unregister_reviewer("user1") is True
        assert engine.get_reviewer("user1") is None

    def test_unregister_nonexistent_reviewer(self, engine):
        """Test unregistering a non-existent reviewer."""
        assert engine.unregister_reviewer("nonexistent") is False

    def test_list_reviewers(self, engine, reviewers):
        """Test listing reviewers."""
        for reviewer in reviewers:
            engine.register_reviewer(reviewer)

        all_reviewers = engine.list_reviewers()
        assert len(all_reviewers) == 3

    def test_list_available_reviewers(self, engine, reviewers):
        """Test listing only available reviewers."""
        reviewers[0].status = ReviewerStatus.BUSY
        for reviewer in reviewers:
            engine.register_reviewer(reviewer)

        available = engine.list_reviewers(available_only=True)
        assert len(available) == 2

    def test_update_reviewer_status(self, engine):
        """Test updating reviewer status."""
        reviewer = Reviewer(
            reviewer_id="user1",
            name="John Doe",
            email="john@example.com"
        )

        engine.register_reviewer(reviewer)
        engine.update_reviewer_status("user1", ReviewerStatus.BUSY)

        updated = engine.get_reviewer("user1")
        assert updated.status == ReviewerStatus.BUSY

    def test_assign_reviewers_load_balanced(self, engine, reviewers):
        """Test load-balanced assignment."""
        for reviewer in reviewers:
            engine.register_reviewer(reviewer)

        assignments = engine.assign_reviewers(
            pull_request_id="pr123",
            repository="org/repo",
            files=["app.py", "test.py"],
            num_reviewers=2,
            strategy=AssignmentStrategy.LOAD_BALANCED
        )

        assert len(assignments) == 2
        assert all(a.pull_request_id == "pr123" for a in assignments)

        # Check workload updated
        for assignment in assignments:
            reviewer = engine.get_reviewer(assignment.reviewer_id)
            assert reviewer.current_reviews == 1

    def test_assign_reviewers_round_robin(self, engine, reviewers):
        """Test round-robin assignment."""
        for reviewer in reviewers:
            engine.register_reviewer(reviewer)

        # First assignment
        assignments1 = engine.assign_reviewers(
            pull_request_id="pr123",
            repository="org/repo",
            files=["app.py"],
            num_reviewers=1,
            strategy=AssignmentStrategy.ROUND_ROBIN
        )

        # Second assignment
        assignments2 = engine.assign_reviewers(
            pull_request_id="pr124",
            repository="org/repo",
            files=["app.py"],
            num_reviewers=1,
            strategy=AssignmentStrategy.ROUND_ROBIN
        )

        # Should assign different reviewers
        assert assignments1[0].reviewer_id != assignments2[0].reviewer_id

    def test_assign_reviewers_expertise_based(self, engine, reviewers):
        """Test expertise-based assignment."""
        for reviewer in reviewers:
            engine.register_reviewer(reviewer)

        assignments = engine.assign_reviewers(
            pull_request_id="pr123",
            repository="org/repo",
            files=["app.py", "utils.py"],
            num_reviewers=2,
            strategy=AssignmentStrategy.EXPERTISE_BASED
        )

        assert len(assignments) == 2

        # Should prefer reviewers with Python file patterns
        reviewer_ids = [a.reviewer_id for a in assignments]
        assert "user1" in reviewer_ids or "user3" in reviewer_ids

    def test_assign_reviewers_with_required_skills(self, engine, reviewers):
        """Test assignment with required skills."""
        for reviewer in reviewers:
            engine.register_reviewer(reviewer)

        assignments = engine.assign_reviewers(
            pull_request_id="pr123",
            repository="org/repo",
            files=["app.py"],
            num_reviewers=1,
            required_skills=["python"]
        )

        assert len(assignments) == 1

        reviewer = engine.get_reviewer(assignments[0].reviewer_id)
        assert reviewer.has_skill("python")

    def test_assign_reviewers_no_available(self, engine):
        """Test assignment with no available reviewers."""
        reviewer = Reviewer(
            reviewer_id="user1",
            name="John Doe",
            email="john@example.com",
            status=ReviewerStatus.BUSY
        )

        engine.register_reviewer(reviewer)

        with pytest.raises(ValueError, match="No available reviewers"):
            engine.assign_reviewers(
                pull_request_id="pr123",
                repository="org/repo",
                files=["app.py"]
            )

    def test_complete_assignment(self, engine, reviewers):
        """Test completing an assignment."""
        for reviewer in reviewers:
            engine.register_reviewer(reviewer)

        assignments = engine.assign_reviewers(
            pull_request_id="pr123",
            repository="org/repo",
            files=["app.py"],
            num_reviewers=1
        )

        assignment_id = assignments[0].assignment_id
        reviewer_id = assignments[0].reviewer_id

        # Complete the assignment
        assert engine.complete_assignment(assignment_id) is True

        # Check workload decreased
        reviewer = engine.get_reviewer(reviewer_id)
        assert reviewer.current_reviews == 0

        # Check assignment moved to history
        assignment = engine.get_assignment(assignment_id)
        assert assignment.completed is True

    def test_complete_nonexistent_assignment(self, engine):
        """Test completing a non-existent assignment."""
        assert engine.complete_assignment("nonexistent") is False

    def test_list_assignments(self, engine, reviewers):
        """Test listing assignments."""
        for reviewer in reviewers:
            engine.register_reviewer(reviewer)

        engine.assign_reviewers(
            pull_request_id="pr123",
            repository="org/repo",
            files=["app.py"],
            num_reviewers=2
        )

        assignments = engine.list_assignments()
        assert len(assignments) == 2

    def test_list_assignments_by_reviewer(self, engine, reviewers):
        """Test listing assignments for a specific reviewer."""
        for reviewer in reviewers:
            engine.register_reviewer(reviewer)

        assignments = engine.assign_reviewers(
            pull_request_id="pr123",
            repository="org/repo",
            files=["app.py"],
            num_reviewers=2
        )

        reviewer_id = assignments[0].reviewer_id
        reviewer_assignments = engine.list_assignments(reviewer_id=reviewer_id)

        assert len(reviewer_assignments) == 1
        assert reviewer_assignments[0].reviewer_id == reviewer_id

    def test_list_completed_assignments(self, engine, reviewers):
        """Test listing completed assignments."""
        for reviewer in reviewers:
            engine.register_reviewer(reviewer)

        assignments = engine.assign_reviewers(
            pull_request_id="pr123",
            repository="org/repo",
            files=["app.py"],
            num_reviewers=1
        )

        engine.complete_assignment(assignments[0].assignment_id)

        completed = engine.list_assignments(completed=True)
        assert len(completed) == 1
        assert completed[0].completed is True

    def test_get_reviewer_stats(self, engine, reviewers):
        """Test getting reviewer statistics."""
        for reviewer in reviewers:
            engine.register_reviewer(reviewer)

        # Assign and complete some reviews
        assignments = engine.assign_reviewers(
            pull_request_id="pr123",
            repository="org/repo",
            files=["app.py"],
            num_reviewers=1
        )

        reviewer_id = assignments[0].reviewer_id
        engine.complete_assignment(assignments[0].assignment_id)

        stats = engine.get_reviewer_stats(reviewer_id)
        assert stats["reviewer_id"] == reviewer_id
        assert stats["total_completed"] == 1
        assert stats["current_reviews"] == 0

    def test_get_reviewer_stats_nonexistent(self, engine):
        """Test getting stats for non-existent reviewer."""
        stats = engine.get_reviewer_stats("nonexistent")
        assert stats == {}


def test_get_assignment_engine():
    """Test getting the global assignment engine."""
    engine1 = get_assignment_engine()
    engine2 = get_assignment_engine()

    # Should return the same instance
    assert engine1 is engine2
