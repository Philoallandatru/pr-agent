"""
Unit tests for real-time collaboration system.
"""

import asyncio
import pytest
from pr_agent.collaboration import (
    CollaborationRoom,
    CollaborationManager,
    User,
    UserStatus,
    EventType,
    get_collaboration_manager,
)


@pytest.fixture
def collaboration_room():
    """Create a collaboration room for testing."""
    return CollaborationRoom("test-room", 123, "test/repo")


@pytest.fixture
def collaboration_manager():
    """Create a collaboration manager for testing."""
    return CollaborationManager()


@pytest.fixture
def test_user():
    """Create a test user."""
    return User(
        id="user1",
        name="Test User",
        email="test@example.com",
        status=UserStatus.ACTIVE,
    )


class TestCollaborationRoom:
    """Test collaboration room functionality."""

    @pytest.mark.asyncio
    async def test_add_user(self, collaboration_room, test_user):
        """Test adding a user to the room."""
        queue = asyncio.Queue()
        await collaboration_room.add_user(test_user, queue)

        assert test_user.id in collaboration_room.users
        assert test_user.id in collaboration_room.connections
        assert len(collaboration_room.event_history) > 0

    @pytest.mark.asyncio
    async def test_remove_user(self, collaboration_room, test_user):
        """Test removing a user from the room."""
        queue = asyncio.Queue()
        await collaboration_room.add_user(test_user, queue)
        await collaboration_room.remove_user(test_user.id)

        assert test_user.id not in collaboration_room.users
        assert test_user.id not in collaboration_room.connections

    @pytest.mark.asyncio
    async def test_update_cursor(self, collaboration_room, test_user):
        """Test updating user cursor position."""
        queue = asyncio.Queue()
        await collaboration_room.add_user(test_user, queue)

        await collaboration_room.update_cursor(
            test_user.id, "test.py", 10, 5
        )

        user = collaboration_room.users[test_user.id]
        assert user.current_file == "test.py"
        assert user.cursor_position == {"line": 10, "column": 5}

    @pytest.mark.asyncio
    async def test_add_comment(self, collaboration_room, test_user):
        """Test adding a comment."""
        queue = asyncio.Queue()
        await collaboration_room.add_user(test_user, queue)

        comment = await collaboration_room.add_comment(
            test_user.id, "test.py", 10, "Test comment"
        )

        assert comment.id in collaboration_room.comments
        assert comment.content == "Test comment"
        assert comment.line_number == 10

    @pytest.mark.asyncio
    async def test_add_comment_reply(self, collaboration_room, test_user):
        """Test adding a reply to a comment."""
        queue = asyncio.Queue()
        await collaboration_room.add_user(test_user, queue)

        # Add parent comment
        parent = await collaboration_room.add_comment(
            test_user.id, "test.py", 10, "Parent comment"
        )

        # Add reply
        reply = await collaboration_room.add_comment(
            test_user.id, "test.py", 10, "Reply comment", parent_id=parent.id
        )

        assert len(collaboration_room.comments[parent.id].replies) == 1
        assert collaboration_room.comments[parent.id].replies[0].content == "Reply comment"

    @pytest.mark.asyncio
    async def test_update_comment(self, collaboration_room, test_user):
        """Test updating a comment."""
        queue = asyncio.Queue()
        await collaboration_room.add_user(test_user, queue)

        comment = await collaboration_room.add_comment(
            test_user.id, "test.py", 10, "Original"
        )

        updated = await collaboration_room.update_comment(
            comment.id, test_user.id, "Updated"
        )

        assert updated.content == "Updated"
        assert updated.updated_at is not None

    @pytest.mark.asyncio
    async def test_delete_comment(self, collaboration_room, test_user):
        """Test deleting a comment."""
        queue = asyncio.Queue()
        await collaboration_room.add_user(test_user, queue)

        comment = await collaboration_room.add_comment(
            test_user.id, "test.py", 10, "Test"
        )

        result = await collaboration_room.delete_comment(comment.id, test_user.id)

        assert result is True
        assert comment.id not in collaboration_room.comments

    @pytest.mark.asyncio
    async def test_add_annotation(self, collaboration_room, test_user):
        """Test adding an annotation."""
        queue = asyncio.Queue()
        await collaboration_room.add_user(test_user, queue)

        annotation = await collaboration_room.add_annotation(
            test_user.id, "test.py", 10, 15, 0, 10, "#ff0000", "Important"
        )

        assert annotation.id in collaboration_room.annotations
        assert annotation.color == "#ff0000"
        assert annotation.label == "Important"

    @pytest.mark.asyncio
    async def test_remove_annotation(self, collaboration_room, test_user):
        """Test removing an annotation."""
        queue = asyncio.Queue()
        await collaboration_room.add_user(test_user, queue)

        annotation = await collaboration_room.add_annotation(
            test_user.id, "test.py", 10, 15, 0, 10, "#ff0000"
        )

        result = await collaboration_room.remove_annotation(annotation.id, test_user.id)

        assert result is True
        assert annotation.id not in collaboration_room.annotations

    @pytest.mark.asyncio
    async def test_update_presence(self, collaboration_room, test_user):
        """Test updating user presence."""
        queue = asyncio.Queue()
        await collaboration_room.add_user(test_user, queue)

        await collaboration_room.update_presence(test_user.id, UserStatus.AWAY)

        user = collaboration_room.users[test_user.id]
        assert user.status == UserStatus.AWAY

    def test_get_active_users(self, collaboration_room):
        """Test getting active users."""
        users = collaboration_room.get_active_users()
        assert isinstance(users, list)

    @pytest.mark.asyncio
    async def test_get_comments_for_file(self, collaboration_room, test_user):
        """Test getting comments for a specific file."""
        queue = asyncio.Queue()
        await collaboration_room.add_user(test_user, queue)

        await collaboration_room.add_comment(test_user.id, "file1.py", 10, "Comment 1")
        await collaboration_room.add_comment(test_user.id, "file2.py", 20, "Comment 2")

        comments = collaboration_room.get_comments_for_file("file1.py")

        assert len(comments) == 1
        assert comments[0].file_path == "file1.py"

    @pytest.mark.asyncio
    async def test_get_annotations_for_file(self, collaboration_room, test_user):
        """Test getting annotations for a specific file."""
        queue = asyncio.Queue()
        await collaboration_room.add_user(test_user, queue)

        await collaboration_room.add_annotation(
            test_user.id, "file1.py", 10, 15, 0, 10, "#ff0000"
        )
        await collaboration_room.add_annotation(
            test_user.id, "file2.py", 20, 25, 0, 10, "#00ff00"
        )

        annotations = collaboration_room.get_annotations_for_file("file1.py")

        assert len(annotations) == 1
        assert annotations[0].file_path == "file1.py"


class TestCollaborationManager:
    """Test collaboration manager functionality."""

    def test_create_room(self, collaboration_manager):
        """Test creating a collaboration room."""
        room = collaboration_manager.create_room(123, "test/repo")

        assert room.pr_number == 123
        assert room.repository == "test/repo"
        assert room.room_id in collaboration_manager.rooms

    def test_get_room(self, collaboration_manager):
        """Test getting a room by ID."""
        room = collaboration_manager.create_room(123, "test/repo")
        retrieved = collaboration_manager.get_room(room.room_id)

        assert retrieved is room

    def test_get_nonexistent_room(self, collaboration_manager):
        """Test getting a nonexistent room."""
        room = collaboration_manager.get_room("nonexistent")
        assert room is None

    def test_get_or_create_room_existing(self, collaboration_manager):
        """Test getting existing room."""
        room1 = collaboration_manager.create_room(123, "test/repo")
        room2 = collaboration_manager.get_or_create_room(123, "test/repo")

        assert room1 is room2

    def test_get_or_create_room_new(self, collaboration_manager):
        """Test creating new room when none exists."""
        room = collaboration_manager.get_or_create_room(123, "test/repo")

        assert room.pr_number == 123
        assert room.repository == "test/repo"

    @pytest.mark.asyncio
    async def test_join_room(self, collaboration_manager, test_user):
        """Test joining a room."""
        room = collaboration_manager.create_room(123, "test/repo")
        queue = asyncio.Queue()

        result = await collaboration_manager.join_room(room.room_id, test_user, queue)

        assert result is True
        assert test_user.id in room.users
        assert test_user.id in collaboration_manager.user_rooms

    @pytest.mark.asyncio
    async def test_join_nonexistent_room(self, collaboration_manager, test_user):
        """Test joining a nonexistent room."""
        queue = asyncio.Queue()
        result = await collaboration_manager.join_room("nonexistent", test_user, queue)

        assert result is False

    @pytest.mark.asyncio
    async def test_leave_room(self, collaboration_manager, test_user):
        """Test leaving a room."""
        room = collaboration_manager.create_room(123, "test/repo")
        queue = asyncio.Queue()

        await collaboration_manager.join_room(room.room_id, test_user, queue)
        await collaboration_manager.leave_room(room.room_id, test_user.id)

        assert test_user.id not in room.users

    @pytest.mark.asyncio
    async def test_leave_room_cleanup_empty(self, collaboration_manager, test_user):
        """Test that empty rooms are cleaned up."""
        room = collaboration_manager.create_room(123, "test/repo")
        queue = asyncio.Queue()

        await collaboration_manager.join_room(room.room_id, test_user, queue)
        await collaboration_manager.leave_room(room.room_id, test_user.id)

        # Room should be removed when empty
        assert room.room_id not in collaboration_manager.rooms

    @pytest.mark.asyncio
    async def test_get_user_rooms(self, collaboration_manager, test_user):
        """Test getting all rooms a user is in."""
        room1 = collaboration_manager.create_room(123, "test/repo1")
        room2 = collaboration_manager.create_room(456, "test/repo2")
        queue = asyncio.Queue()

        await collaboration_manager.join_room(room1.room_id, test_user, queue)
        await collaboration_manager.join_room(room2.room_id, test_user, queue)

        user_rooms = collaboration_manager.get_user_rooms(test_user.id)

        assert len(user_rooms) == 2
        assert room1 in user_rooms
        assert room2 in user_rooms


class TestGlobalCollaborationManager:
    """Test global collaboration manager singleton."""

    def test_get_collaboration_manager(self):
        """Test getting global collaboration manager."""
        manager1 = get_collaboration_manager()
        manager2 = get_collaboration_manager()

        assert manager1 is manager2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
