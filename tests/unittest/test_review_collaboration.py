"""
Tests for Code Review Collaboration System
"""

import pytest
from datetime import datetime, timezone
from pr_agent.review_collaboration import (
    CollaborationSystem,
    ParticipantRole,
    CommentType,
    CommentStatus,
    TaskStatus,
    DecisionStatus,
)


@pytest.fixture
def collab_system(tmp_path):
    """Create collaboration system with temp storage"""
    return CollaborationSystem(storage_path=str(tmp_path))


class TestReviewSession:
    """Test review session management"""

    def test_create_session(self, collab_system):
        """Test creating a review session"""
        session = collab_system.create_session(
            session_id="session-1",
            pr_id="PR-123",
            repository="test/repo",
            title="Review PR-123",
            description="Test review session",
            creator_id="user1",
            creator_name="Alice"
        )

        assert session.session_id == "session-1"
        assert session.pr_id == "PR-123"
        assert session.repository == "test/repo"
        assert session.title == "Review PR-123"
        assert session.is_active is True
        assert "user1" in session.participants
        assert session.participants["user1"].role == ParticipantRole.MODERATOR

    def test_add_participant(self, collab_system):
        """Test adding participants"""
        session = collab_system.create_session(
            session_id="session-1",
            pr_id="PR-123",
            repository="test/repo",
            title="Test"
        )

        participant = collab_system.add_participant(
            session_id="session-1",
            user_id="user2",
            username="Bob",
            role=ParticipantRole.REVIEWER
        )

        assert participant.user_id == "user2"
        assert participant.username == "Bob"
        assert participant.role == ParticipantRole.REVIEWER
        assert "user2" in session.participants


class TestComments:
    """Test comment management"""

    def test_add_comment(self, collab_system):
        """Test adding a comment"""
        session = collab_system.create_session(
            session_id="session-1",
            pr_id="PR-123",
            repository="test/repo",
            title="Test"
        )

        comment = collab_system.add_comment(
            session_id="session-1",
            comment_id="c1",
            author_id="user1",
            content="This needs improvement",
            comment_type=CommentType.SUGGESTION,
            file_path="app.py",
            line_number=42
        )

        assert comment.comment_id == "c1"
        assert comment.author_id == "user1"
        assert comment.content == "This needs improvement"
        assert comment.comment_type == CommentType.SUGGESTION
        assert comment.status == CommentStatus.OPEN
        assert comment.file_path == "app.py"
        assert comment.line_number == 42

    def test_resolve_comment(self, collab_system):
        """Test resolving a comment"""
        session = collab_system.create_session(
            session_id="session-1",
            pr_id="PR-123",
            repository="test/repo",
            title="Test"
        )

        collab_system.add_comment(
            session_id="session-1",
            comment_id="c1",
            author_id="user1",
            content="Test",
            comment_type=CommentType.ISSUE
        )

        comment = collab_system.resolve_comment(
            session_id="session-1",
            comment_id="c1",
            resolved_by="user2"
        )

        assert comment.status == CommentStatus.RESOLVED
        assert comment.resolved_by == "user2"
        assert comment.resolved_at is not None

    def test_threaded_comments(self, collab_system):
        """Test threaded comment discussions"""
        session = collab_system.create_session(
            session_id="session-1",
            pr_id="PR-123",
            repository="test/repo",
            title="Test"
        )

        # Add parent comment
        collab_system.add_comment(
            session_id="session-1",
            comment_id="c1",
            author_id="user1",
            content="Parent comment",
            comment_type=CommentType.QUESTION
        )

        # Add reply
        collab_system.add_comment(
            session_id="session-1",
            comment_id="c2",
            author_id="user2",
            content="Reply to parent",
            comment_type=CommentType.DISCUSSION,
            parent_id="c1"
        )

        # Add nested reply
        collab_system.add_comment(
            session_id="session-1",
            comment_id="c3",
            author_id="user1",
            content="Nested reply",
            comment_type=CommentType.DISCUSSION,
            parent_id="c2"
        )

        thread = collab_system.get_comment_thread("session-1", "c2")
        assert len(thread) == 3
        assert thread[0].comment_id == "c1"
        assert thread[1].comment_id == "c2"
        assert thread[2].comment_id == "c3"

    def test_add_reaction(self, collab_system):
        """Test adding reactions to comments"""
        session = collab_system.create_session(
            session_id="session-1",
            pr_id="PR-123",
            repository="test/repo",
            title="Test"
        )

        collab_system.add_comment(
            session_id="session-1",
            comment_id="c1",
            author_id="user1",
            content="Great work!",
            comment_type=CommentType.PRAISE
        )

        collab_system.add_reaction("session-1", "c1", "user2", "👍")
        collab_system.add_reaction("session-1", "c1", "user3", "👍")
        collab_system.add_reaction("session-1", "c1", "user4", "❤️")

        comment = session.comments["c1"]
        assert "👍" in comment.reactions
        assert len(comment.reactions["👍"]) == 2
        assert "user2" in comment.reactions["👍"]
        assert "user3" in comment.reactions["👍"]
        assert "❤️" in comment.reactions
        assert len(comment.reactions["❤️"]) == 1


class TestTasks:
    """Test task management"""

    def test_create_task(self, collab_system):
        """Test creating a task"""
        session = collab_system.create_session(
            session_id="session-1",
            pr_id="PR-123",
            repository="test/repo",
            title="Test"
        )

        task = collab_system.create_task(
            session_id="session-1",
            task_id="t1",
            title="Fix bug",
            description="Fix the memory leak",
            created_by="user1",
            assignee_id="user2",
            priority="high"
        )

        assert task.task_id == "t1"
        assert task.title == "Fix bug"
        assert task.status == TaskStatus.TODO
        assert task.assignee_id == "user2"
        assert task.priority == "high"

    def test_update_task_status(self, collab_system):
        """Test updating task status"""
        session = collab_system.create_session(
            session_id="session-1",
            pr_id="PR-123",
            repository="test/repo",
            title="Test"
        )

        collab_system.create_task(
            session_id="session-1",
            task_id="t1",
            title="Test task",
            description="Test",
            created_by="user1"
        )

        task = collab_system.update_task_status(
            session_id="session-1",
            task_id="t1",
            status=TaskStatus.IN_PROGRESS
        )
        assert task.status == TaskStatus.IN_PROGRESS

        task = collab_system.update_task_status(
            session_id="session-1",
            task_id="t1",
            status=TaskStatus.COMPLETED
        )
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None


class TestDecisions:
    """Test decision management"""

    def test_propose_decision(self, collab_system):
        """Test proposing a decision"""
        session = collab_system.create_session(
            session_id="session-1",
            pr_id="PR-123",
            repository="test/repo",
            title="Test"
        )

        decision = collab_system.propose_decision(
            session_id="session-1",
            decision_id="d1",
            title="Merge PR",
            description="Should we merge this PR?",
            proposed_by="user1",
            required_approvals=2
        )

        assert decision.decision_id == "d1"
        assert decision.title == "Merge PR"
        assert decision.status == DecisionStatus.PROPOSED
        assert decision.required_approvals == 2

    def test_vote_decision(self, collab_system):
        """Test voting on decisions"""
        session = collab_system.create_session(
            session_id="session-1",
            pr_id="PR-123",
            repository="test/repo",
            title="Test"
        )

        collab_system.propose_decision(
            session_id="session-1",
            decision_id="d1",
            title="Merge PR",
            description="Test",
            proposed_by="user1",
            required_approvals=2
        )

        # First vote
        decision = collab_system.vote_decision(
            session_id="session-1",
            decision_id="d1",
            user_id="user2",
            approve=True
        )
        assert decision.status == DecisionStatus.PROPOSED
        assert decision.votes["user2"] is True

        # Second vote - should finalize
        decision = collab_system.vote_decision(
            session_id="session-1",
            decision_id="d1",
            user_id="user3",
            approve=True
        )
        assert decision.status == DecisionStatus.APPROVED
        assert decision.finalized_at is not None

    def test_reject_decision(self, collab_system):
        """Test rejecting a decision"""
        session = collab_system.create_session(
            session_id="session-1",
            pr_id="PR-123",
            repository="test/repo",
            title="Test"
        )

        collab_system.propose_decision(
            session_id="session-1",
            decision_id="d1",
            title="Test",
            description="Test",
            proposed_by="user1",
            required_approvals=1
        )

        decision = collab_system.vote_decision(
            session_id="session-1",
            decision_id="d1",
            user_id="user2",
            approve=False
        )
        assert decision.votes["user2"] is False
        assert decision.status == DecisionStatus.PROPOSED  # Not finalized


class TestSessionStats:
    """Test session statistics"""

    def test_get_session_stats(self, collab_system):
        """Test getting session statistics"""
        session = collab_system.create_session(
            session_id="session-1",
            pr_id="PR-123",
            repository="test/repo",
            title="Test",
            creator_id="user1",
            creator_name="Alice"
        )

        collab_system.add_participant("session-1", "user2", "Bob", ParticipantRole.REVIEWER)
        collab_system.add_participant("session-1", "user3", "Charlie", ParticipantRole.OBSERVER)

        collab_system.add_comment("session-1", "c1", "user1", "Comment 1", CommentType.ISSUE)
        collab_system.add_comment("session-1", "c2", "user2", "Comment 2", CommentType.SUGGESTION)
        collab_system.resolve_comment("session-1", "c1", "user2")

        collab_system.create_task("session-1", "t1", "Task 1", "Test", "user1")
        collab_system.create_task("session-1", "t2", "Task 2", "Test", "user1")
        collab_system.update_task_status("session-1", "t1", TaskStatus.COMPLETED)

        collab_system.propose_decision("session-1", "d1", "Decision 1", "Test", "user1")

        stats = collab_system.get_session_stats("session-1")

        assert stats["participants"] == 3
        assert stats["total_comments"] == 2
        assert stats["open_comments"] == 1
        assert stats["resolved_comments"] == 1
        assert stats["total_tasks"] == 2
        assert stats["pending_tasks"] == 1
        assert stats["completed_tasks"] == 1
        assert stats["total_decisions"] == 1
        assert stats["pending_decisions"] == 1


class TestPersistence:
    """Test session persistence"""

    def test_save_and_load_session(self, collab_system):
        """Test saving and loading sessions"""
        # Create session with data
        session = collab_system.create_session(
            session_id="session-1",
            pr_id="PR-123",
            repository="test/repo",
            title="Test Session",
            creator_id="user1",
            creator_name="Alice"
        )

        collab_system.add_participant("session-1", "user2", "Bob", ParticipantRole.REVIEWER)
        collab_system.add_comment("session-1", "c1", "user1", "Test comment", CommentType.ISSUE)
        collab_system.create_task("session-1", "t1", "Test task", "Description", "user1")
        collab_system.propose_decision("session-1", "d1", "Test decision", "Description", "user1")

        # Create new system and load session
        new_system = CollaborationSystem(storage_path=str(collab_system.storage_path))
        loaded_session = new_system.load_session("session-1")

        assert loaded_session is not None
        assert loaded_session.session_id == "session-1"
        assert loaded_session.pr_id == "PR-123"
        assert len(loaded_session.participants) == 2
        assert len(loaded_session.comments) == 1
        assert len(loaded_session.tasks) == 1
        assert len(loaded_session.decisions) == 1


class TestEventHandlers:
    """Test event handling"""

    def test_event_handlers(self, collab_system):
        """Test registering and triggering event handlers"""
        events_received = []

        def on_session_created(session):
            events_received.append(("session_created", session.session_id))

        def on_comment_added(session, comment):
            events_received.append(("comment_added", comment.comment_id))

        def on_task_created(session, task):
            events_received.append(("task_created", task.task_id))

        def on_task_completed(session, task):
            events_received.append(("task_completed", task.task_id))

        collab_system.on_event("session_created", on_session_created)
        collab_system.on_event("comment_added", on_comment_added)
        collab_system.on_event("task_created", on_task_created)
        collab_system.on_event("task_completed", on_task_completed)

        # Trigger events
        collab_system.create_session("session-1", "PR-123", "test/repo", "Test")
        collab_system.add_comment("session-1", "c1", "user1", "Test", CommentType.ISSUE)
        collab_system.create_task("session-1", "t1", "Task", "Test", "user1")
        collab_system.update_task_status("session-1", "t1", TaskStatus.COMPLETED)

        assert len(events_received) == 4
        assert events_received[0] == ("session_created", "session-1")
        assert events_received[1] == ("comment_added", "c1")
        assert events_received[2] == ("task_created", "t1")
        assert events_received[3] == ("task_completed", "t1")


class TestErrorHandling:
    """Test error handling"""

    def test_invalid_session(self, collab_system):
        """Test operations on non-existent session"""
        with pytest.raises(ValueError, match="Session .* not found"):
            collab_system.add_participant("invalid", "user1", "Test", ParticipantRole.REVIEWER)

        with pytest.raises(ValueError, match="Session .* not found"):
            collab_system.add_comment("invalid", "c1", "user1", "Test", CommentType.ISSUE)

    def test_invalid_comment(self, collab_system):
        """Test operations on non-existent comment"""
        collab_system.create_session("session-1", "PR-123", "test/repo", "Test")

        with pytest.raises(ValueError, match="Comment .* not found"):
            collab_system.resolve_comment("session-1", "invalid", "user1")

        with pytest.raises(ValueError, match="Comment .* not found"):
            collab_system.add_reaction("session-1", "invalid", "user1", "👍")

    def test_invalid_task(self, collab_system):
        """Test operations on non-existent task"""
        collab_system.create_session("session-1", "PR-123", "test/repo", "Test")

        with pytest.raises(ValueError, match="Task .* not found"):
            collab_system.update_task_status("session-1", "invalid", TaskStatus.COMPLETED)
