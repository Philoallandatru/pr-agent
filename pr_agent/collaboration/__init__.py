"""
Real-time collaboration system.
"""

from pr_agent.collaboration.room import (
    CollaborationRoom,
    CollaborationManager,
    CollaborationEvent,
    User,
    Comment,
    Annotation,
    EventType,
    UserStatus,
    get_collaboration_manager,
)

__all__ = [
    'CollaborationRoom',
    'CollaborationManager',
    'CollaborationEvent',
    'User',
    'Comment',
    'Annotation',
    'EventType',
    'UserStatus',
    'get_collaboration_manager',
]
