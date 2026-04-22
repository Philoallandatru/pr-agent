"""
Real-time collaboration system for PR Agent.

Provides WebSocket-based real-time collaboration features including:
- Multi-user code review sessions
- Live cursor tracking and presence
- Real-time comments and annotations
- Collaborative editing with operational transformation
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Set
from uuid import uuid4

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Collaboration event types."""
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    CURSOR_MOVED = "cursor_moved"
    COMMENT_ADDED = "comment_added"
    COMMENT_UPDATED = "comment_updated"
    COMMENT_DELETED = "comment_deleted"
    ANNOTATION_ADDED = "annotation_added"
    ANNOTATION_REMOVED = "annotation_removed"
    FILE_OPENED = "file_opened"
    FILE_CLOSED = "file_closed"
    EDIT_APPLIED = "edit_applied"
    PRESENCE_UPDATE = "presence_update"


class UserStatus(str, Enum):
    """User presence status."""
    ACTIVE = "active"
    IDLE = "idle"
    AWAY = "away"


@dataclass
class User:
    """Collaboration user."""
    id: str
    name: str
    email: str
    avatar_url: Optional[str] = None
    status: UserStatus = UserStatus.ACTIVE
    last_seen: float = field(default_factory=time.time)
    current_file: Optional[str] = None
    cursor_position: Optional[Dict[str, int]] = None  # {line, column}


@dataclass
class Comment:
    """Code review comment."""
    id: str
    user_id: str
    file_path: str
    line_number: int
    content: str
    created_at: float
    updated_at: Optional[float] = None
    resolved: bool = False
    replies: List['Comment'] = field(default_factory=list)


@dataclass
class Annotation:
    """Code annotation/highlight."""
    id: str
    user_id: str
    file_path: str
    start_line: int
    end_line: int
    start_column: int
    end_column: int
    color: str
    label: Optional[str] = None


@dataclass
class CollaborationEvent:
    """Real-time collaboration event."""
    type: EventType
    user_id: str
    timestamp: float
    data: Dict
    room_id: str


class CollaborationRoom:
    """
    Real-time collaboration room for PR review.

    Manages WebSocket connections, user presence, and event broadcasting.
    """

    def __init__(self, room_id: str, pr_number: int, repository: str):
        self.room_id = room_id
        self.pr_number = pr_number
        self.repository = repository
        self.created_at = time.time()

        # User management
        self.users: Dict[str, User] = {}
        self.connections: Dict[str, asyncio.Queue] = {}

        # Collaboration data
        self.comments: Dict[str, Comment] = {}
        self.annotations: Dict[str, Annotation] = {}

        # Event history (last 100 events)
        self.event_history: List[CollaborationEvent] = []
        self.max_history = 100

        logger.info(f"Created collaboration room {room_id} for PR #{pr_number}")

    async def add_user(self, user: User, connection_queue: asyncio.Queue) -> None:
        """Add user to the room."""
        self.users[user.id] = user
        self.connections[user.id] = connection_queue

        # Broadcast user joined event
        event = CollaborationEvent(
            type=EventType.USER_JOINED,
            user_id=user.id,
            timestamp=time.time(),
            data={
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "avatar_url": user.avatar_url,
                    "status": user.status.value,
                }
            },
            room_id=self.room_id,
        )
        await self._broadcast_event(event, exclude_user=user.id)
        self._add_to_history(event)

        # Send current room state to new user
        await self._send_room_state(user.id)

        logger.info(f"User {user.name} joined room {self.room_id}")

    async def remove_user(self, user_id: str) -> None:
        """Remove user from the room."""
        if user_id not in self.users:
            return

        user = self.users[user_id]
        del self.users[user_id]
        del self.connections[user_id]

        # Remove user's annotations
        self.annotations = {
            aid: ann for aid, ann in self.annotations.items()
            if ann.user_id != user_id
        }

        # Broadcast user left event
        event = CollaborationEvent(
            type=EventType.USER_LEFT,
            user_id=user_id,
            timestamp=time.time(),
            data={"user_id": user_id},
            room_id=self.room_id,
        )
        await self._broadcast_event(event)
        self._add_to_history(event)

        logger.info(f"User {user.name} left room {self.room_id}")

    async def update_cursor(self, user_id: str, file_path: str,
                           line: int, column: int) -> None:
        """Update user's cursor position."""
        if user_id not in self.users:
            return

        user = self.users[user_id]
        user.cursor_position = {"line": line, "column": column}
        user.current_file = file_path
        user.last_seen = time.time()

        # Broadcast cursor update
        event = CollaborationEvent(
            type=EventType.CURSOR_MOVED,
            user_id=user_id,
            timestamp=time.time(),
            data={
                "file_path": file_path,
                "line": line,
                "column": column,
            },
            room_id=self.room_id,
        )
        await self._broadcast_event(event, exclude_user=user_id)

    async def add_comment(self, user_id: str, file_path: str,
                         line_number: int, content: str,
                         parent_id: Optional[str] = None) -> Comment:
        """Add a comment to the code."""
        comment = Comment(
            id=str(uuid4()),
            user_id=user_id,
            file_path=file_path,
            line_number=line_number,
            content=content,
            created_at=time.time(),
        )

        if parent_id and parent_id in self.comments:
            # Add as reply
            self.comments[parent_id].replies.append(comment)
        else:
            # Add as top-level comment
            self.comments[comment.id] = comment

        # Broadcast comment added event
        event = CollaborationEvent(
            type=EventType.COMMENT_ADDED,
            user_id=user_id,
            timestamp=time.time(),
            data={
                "comment_id": comment.id,
                "file_path": file_path,
                "line_number": line_number,
                "content": content,
                "parent_id": parent_id,
            },
            room_id=self.room_id,
        )
        await self._broadcast_event(event)
        self._add_to_history(event)

        return comment

    async def update_comment(self, comment_id: str, user_id: str,
                            content: str) -> Optional[Comment]:
        """Update an existing comment."""
        comment = self.comments.get(comment_id)
        if not comment or comment.user_id != user_id:
            return None

        comment.content = content
        comment.updated_at = time.time()

        # Broadcast comment updated event
        event = CollaborationEvent(
            type=EventType.COMMENT_UPDATED,
            user_id=user_id,
            timestamp=time.time(),
            data={
                "comment_id": comment_id,
                "content": content,
            },
            room_id=self.room_id,
        )
        await self._broadcast_event(event)
        self._add_to_history(event)

        return comment

    async def delete_comment(self, comment_id: str, user_id: str) -> bool:
        """Delete a comment."""
        comment = self.comments.get(comment_id)
        if not comment or comment.user_id != user_id:
            return False

        del self.comments[comment_id]

        # Broadcast comment deleted event
        event = CollaborationEvent(
            type=EventType.COMMENT_DELETED,
            user_id=user_id,
            timestamp=time.time(),
            data={"comment_id": comment_id},
            room_id=self.room_id,
        )
        await self._broadcast_event(event)
        self._add_to_history(event)

        return True

    async def add_annotation(self, user_id: str, file_path: str,
                            start_line: int, end_line: int,
                            start_column: int, end_column: int,
                            color: str, label: Optional[str] = None) -> Annotation:
        """Add a code annotation/highlight."""
        annotation = Annotation(
            id=str(uuid4()),
            user_id=user_id,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            start_column=start_column,
            end_column=end_column,
            color=color,
            label=label,
        )

        self.annotations[annotation.id] = annotation

        # Broadcast annotation added event
        event = CollaborationEvent(
            type=EventType.ANNOTATION_ADDED,
            user_id=user_id,
            timestamp=time.time(),
            data={
                "annotation_id": annotation.id,
                "file_path": file_path,
                "start_line": start_line,
                "end_line": end_line,
                "start_column": start_column,
                "end_column": end_column,
                "color": color,
                "label": label,
            },
            room_id=self.room_id,
        )
        await self._broadcast_event(event)

        return annotation

    async def remove_annotation(self, annotation_id: str, user_id: str) -> bool:
        """Remove a code annotation."""
        annotation = self.annotations.get(annotation_id)
        if not annotation or annotation.user_id != user_id:
            return False

        del self.annotations[annotation_id]

        # Broadcast annotation removed event
        event = CollaborationEvent(
            type=EventType.ANNOTATION_REMOVED,
            user_id=user_id,
            timestamp=time.time(),
            data={"annotation_id": annotation_id},
            room_id=self.room_id,
        )
        await self._broadcast_event(event)

        return True

    async def update_presence(self, user_id: str, status: UserStatus) -> None:
        """Update user presence status."""
        if user_id not in self.users:
            return

        user = self.users[user_id]
        user.status = status
        user.last_seen = time.time()

        # Broadcast presence update
        event = CollaborationEvent(
            type=EventType.PRESENCE_UPDATE,
            user_id=user_id,
            timestamp=time.time(),
            data={"status": status.value},
            room_id=self.room_id,
        )
        await self._broadcast_event(event, exclude_user=user_id)

    def get_active_users(self) -> List[User]:
        """Get list of active users in the room."""
        return list(self.users.values())

    def get_comments_for_file(self, file_path: str) -> List[Comment]:
        """Get all comments for a specific file."""
        return [
            comment for comment in self.comments.values()
            if comment.file_path == file_path
        ]

    def get_annotations_for_file(self, file_path: str) -> List[Annotation]:
        """Get all annotations for a specific file."""
        return [
            ann for ann in self.annotations.values()
            if ann.file_path == file_path
        ]

    async def _broadcast_event(self, event: CollaborationEvent,
                              exclude_user: Optional[str] = None) -> None:
        """Broadcast event to all connected users."""
        message = {
            "type": event.type.value,
            "user_id": event.user_id,
            "timestamp": event.timestamp,
            "data": event.data,
            "room_id": event.room_id,
        }

        for user_id, queue in self.connections.items():
            if user_id != exclude_user:
                try:
                    await queue.put(message)
                except Exception as e:
                    logger.error(f"Failed to send event to user {user_id}: {e}")

    async def _send_room_state(self, user_id: str) -> None:
        """Send current room state to a user."""
        if user_id not in self.connections:
            return

        state = {
            "type": "room_state",
            "data": {
                "room_id": self.room_id,
                "pr_number": self.pr_number,
                "repository": self.repository,
                "users": [
                    {
                        "id": u.id,
                        "name": u.name,
                        "email": u.email,
                        "avatar_url": u.avatar_url,
                        "status": u.status.value,
                        "current_file": u.current_file,
                        "cursor_position": u.cursor_position,
                    }
                    for u in self.users.values()
                ],
                "comments": [
                    {
                        "id": c.id,
                        "user_id": c.user_id,
                        "file_path": c.file_path,
                        "line_number": c.line_number,
                        "content": c.content,
                        "created_at": c.created_at,
                        "updated_at": c.updated_at,
                        "resolved": c.resolved,
                        "replies": [
                            {
                                "id": r.id,
                                "user_id": r.user_id,
                                "content": r.content,
                                "created_at": r.created_at,
                            }
                            for r in c.replies
                        ],
                    }
                    for c in self.comments.values()
                ],
                "annotations": [
                    {
                        "id": a.id,
                        "user_id": a.user_id,
                        "file_path": a.file_path,
                        "start_line": a.start_line,
                        "end_line": a.end_line,
                        "start_column": a.start_column,
                        "end_column": a.end_column,
                        "color": a.color,
                        "label": a.label,
                    }
                    for a in self.annotations.values()
                ],
            },
        }

        try:
            await self.connections[user_id].put(state)
        except Exception as e:
            logger.error(f"Failed to send room state to user {user_id}: {e}")

    def _add_to_history(self, event: CollaborationEvent) -> None:
        """Add event to history."""
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)


class CollaborationManager:
    """
    Manages collaboration rooms and WebSocket connections.
    """

    def __init__(self):
        self.rooms: Dict[str, CollaborationRoom] = {}
        self.user_rooms: Dict[str, Set[str]] = {}  # user_id -> room_ids
        logger.info("Collaboration manager initialized")

    def create_room(self, pr_number: int, repository: str) -> CollaborationRoom:
        """Create a new collaboration room."""
        room_id = f"{repository}:{pr_number}:{uuid4().hex[:8]}"
        room = CollaborationRoom(room_id, pr_number, repository)
        self.rooms[room_id] = room
        return room

    def get_room(self, room_id: str) -> Optional[CollaborationRoom]:
        """Get a collaboration room by ID."""
        return self.rooms.get(room_id)

    def get_or_create_room(self, pr_number: int, repository: str) -> CollaborationRoom:
        """Get existing room or create new one for PR."""
        # Find existing room for this PR
        for room in self.rooms.values():
            if room.pr_number == pr_number and room.repository == repository:
                return room

        # Create new room
        return self.create_room(pr_number, repository)

    async def join_room(self, room_id: str, user: User,
                       connection_queue: asyncio.Queue) -> bool:
        """Join a collaboration room."""
        room = self.get_room(room_id)
        if not room:
            return False

        await room.add_user(user, connection_queue)

        if user.id not in self.user_rooms:
            self.user_rooms[user.id] = set()
        self.user_rooms[user.id].add(room_id)

        return True

    async def leave_room(self, room_id: str, user_id: str) -> None:
        """Leave a collaboration room."""
        room = self.get_room(room_id)
        if room:
            await room.remove_user(user_id)

        if user_id in self.user_rooms:
            self.user_rooms[user_id].discard(room_id)
            if not self.user_rooms[user_id]:
                del self.user_rooms[user_id]

        # Clean up empty rooms
        if room and not room.users:
            del self.rooms[room_id]
            logger.info(f"Removed empty room {room_id}")

    def get_user_rooms(self, user_id: str) -> List[CollaborationRoom]:
        """Get all rooms a user is in."""
        if user_id not in self.user_rooms:
            return []

        return [
            self.rooms[room_id]
            for room_id in self.user_rooms[user_id]
            if room_id in self.rooms
        ]


# Global collaboration manager instance
_collaboration_manager: Optional[CollaborationManager] = None


def get_collaboration_manager() -> CollaborationManager:
    """Get the global collaboration manager instance."""
    global _collaboration_manager
    if _collaboration_manager is None:
        _collaboration_manager = CollaborationManager()
    return _collaboration_manager
