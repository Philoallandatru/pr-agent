"""
Code Review Collaboration System

Provides team collaboration features for code reviews including:
- Review session management
- Comment threads and discussions
- Task assignment and tracking
- Real-time collaboration
- Decision making and consensus
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import json
from pathlib import Path


class ParticipantRole(Enum):
    """Participant role in review session"""
    AUTHOR = "author"
    REVIEWER = "reviewer"
    OBSERVER = "observer"
    MODERATOR = "moderator"


class CommentType(Enum):
    """Type of comment"""
    QUESTION = "question"
    SUGGESTION = "suggestion"
    ISSUE = "issue"
    PRAISE = "praise"
    DISCUSSION = "discussion"


class CommentStatus(Enum):
    """Status of comment"""
    OPEN = "open"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"
    DEFERRED = "deferred"


class TaskStatus(Enum):
    """Status of collaboration task"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DecisionStatus(Enum):
    """Status of decision"""
    PROPOSED = "proposed"
    DISCUSSING = "discussing"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


@dataclass
class Participant:
    """Review session participant"""
    user_id: str
    username: str
    role: ParticipantRole
    joined_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_active: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_online: bool = True


@dataclass
class Comment:
    """Review comment with threading support"""
    comment_id: str
    author_id: str
    content: str
    comment_type: CommentType
    status: CommentStatus = CommentStatus.OPEN
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    parent_id: Optional[str] = None  # For threaded discussions
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved_by: Optional[str] = None
    resolved_at: Optional[str] = None
    reactions: Dict[str, List[str]] = field(default_factory=dict)  # emoji -> [user_ids]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """Collaboration task"""
    task_id: str
    title: str
    description: str
    assignee_id: Optional[str] = None
    status: TaskStatus = TaskStatus.TODO
    priority: str = "normal"  # low, normal, high, critical
    created_by: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    due_date: Optional[str] = None
    completed_at: Optional[str] = None
    related_comments: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Decision:
    """Team decision record"""
    decision_id: str
    title: str
    description: str
    proposed_by: str
    status: DecisionStatus = DecisionStatus.PROPOSED
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    votes: Dict[str, bool] = field(default_factory=dict)  # user_id -> approve/reject
    required_approvals: int = 1
    comments: List[str] = field(default_factory=list)
    finalized_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReviewSession:
    """Collaborative review session"""
    session_id: str
    pr_id: str
    repository: str
    title: str
    description: str = ""
    participants: Dict[str, Participant] = field(default_factory=dict)
    comments: Dict[str, Comment] = field(default_factory=dict)
    tasks: Dict[str, Task] = field(default_factory=dict)
    decisions: Dict[str, Decision] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class CollaborationSystem:
    """Manages collaborative code review sessions"""

    def __init__(self, storage_path: Optional[str] = None):
        self.sessions: Dict[str, ReviewSession] = {}
        self.storage_path = Path(storage_path) if storage_path else Path.home() / ".pr_agent" / "collaboration"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Event callbacks
        self.event_handlers: Dict[str, List[Callable]] = {
            "session_created": [],
            "participant_joined": [],
            "comment_added": [],
            "comment_resolved": [],
            "task_created": [],
            "task_completed": [],
            "decision_proposed": [],
            "decision_finalized": [],
        }

    def create_session(
        self,
        session_id: str,
        pr_id: str,
        repository: str,
        title: str,
        description: str = "",
        creator_id: str = "",
        creator_name: str = ""
    ) -> ReviewSession:
        """Create a new review session"""
        session = ReviewSession(
            session_id=session_id,
            pr_id=pr_id,
            repository=repository,
            title=title,
            description=description
        )

        # Add creator as moderator
        if creator_id:
            session.participants[creator_id] = Participant(
                user_id=creator_id,
                username=creator_name,
                role=ParticipantRole.MODERATOR
            )

        self.sessions[session_id] = session
        self._trigger_event("session_created", session)
        self._save_session(session)
        return session

    def add_participant(
        self,
        session_id: str,
        user_id: str,
        username: str,
        role: ParticipantRole = ParticipantRole.REVIEWER
    ) -> Participant:
        """Add participant to session"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        participant = Participant(
            user_id=user_id,
            username=username,
            role=role
        )
        session.participants[user_id] = participant
        self._trigger_event("participant_joined", session, participant)
        self._save_session(session)
        return participant

    def add_comment(
        self,
        session_id: str,
        comment_id: str,
        author_id: str,
        content: str,
        comment_type: CommentType,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
        parent_id: Optional[str] = None
    ) -> Comment:
        """Add comment to session"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        comment = Comment(
            comment_id=comment_id,
            author_id=author_id,
            content=content,
            comment_type=comment_type,
            file_path=file_path,
            line_number=line_number,
            parent_id=parent_id
        )
        session.comments[comment_id] = comment

        # Update participant activity
        if author_id in session.participants:
            session.participants[author_id].last_active = datetime.now(timezone.utc).isoformat()

        self._trigger_event("comment_added", session, comment)
        self._save_session(session)
        return comment

    def resolve_comment(
        self,
        session_id: str,
        comment_id: str,
        resolved_by: str
    ) -> Comment:
        """Resolve a comment"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        comment = session.comments.get(comment_id)
        if not comment:
            raise ValueError(f"Comment {comment_id} not found")

        comment.status = CommentStatus.RESOLVED
        comment.resolved_by = resolved_by
        comment.resolved_at = datetime.now(timezone.utc).isoformat()

        self._trigger_event("comment_resolved", session, comment)
        self._save_session(session)
        return comment

    def add_reaction(
        self,
        session_id: str,
        comment_id: str,
        user_id: str,
        emoji: str
    ):
        """Add reaction to comment"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        comment = session.comments.get(comment_id)
        if not comment:
            raise ValueError(f"Comment {comment_id} not found")

        if emoji not in comment.reactions:
            comment.reactions[emoji] = []

        if user_id not in comment.reactions[emoji]:
            comment.reactions[emoji].append(user_id)

        self._save_session(session)

    def create_task(
        self,
        session_id: str,
        task_id: str,
        title: str,
        description: str,
        created_by: str,
        assignee_id: Optional[str] = None,
        priority: str = "normal",
        due_date: Optional[str] = None
    ) -> Task:
        """Create a task"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        task = Task(
            task_id=task_id,
            title=title,
            description=description,
            created_by=created_by,
            assignee_id=assignee_id,
            priority=priority,
            due_date=due_date
        )
        session.tasks[task_id] = task
        self._trigger_event("task_created", session, task)
        self._save_session(session)
        return task

    def update_task_status(
        self,
        session_id: str,
        task_id: str,
        status: TaskStatus
    ) -> Task:
        """Update task status"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        task = session.tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task.status = status
        if status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now(timezone.utc).isoformat()
            self._trigger_event("task_completed", session, task)

        self._save_session(session)
        return task

    def propose_decision(
        self,
        session_id: str,
        decision_id: str,
        title: str,
        description: str,
        proposed_by: str,
        required_approvals: int = 1
    ) -> Decision:
        """Propose a decision"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        decision = Decision(
            decision_id=decision_id,
            title=title,
            description=description,
            proposed_by=proposed_by,
            required_approvals=required_approvals
        )
        session.decisions[decision_id] = decision
        self._trigger_event("decision_proposed", session, decision)
        self._save_session(session)
        return decision

    def vote_decision(
        self,
        session_id: str,
        decision_id: str,
        user_id: str,
        approve: bool
    ) -> Decision:
        """Vote on a decision"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        decision = session.decisions.get(decision_id)
        if not decision:
            raise ValueError(f"Decision {decision_id} not found")

        decision.votes[user_id] = approve

        # Check if decision can be finalized
        approvals = sum(1 for v in decision.votes.values() if v)
        if approvals >= decision.required_approvals:
            decision.status = DecisionStatus.APPROVED
            decision.finalized_at = datetime.now(timezone.utc).isoformat()
            self._trigger_event("decision_finalized", session, decision)

        self._save_session(session)
        return decision

    def get_comment_thread(
        self,
        session_id: str,
        comment_id: str
    ) -> List[Comment]:
        """Get comment thread (parent and all replies)"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        thread = []
        comment = session.comments.get(comment_id)
        if not comment:
            return thread

        # Find root comment
        root = comment
        while root.parent_id:
            root = session.comments.get(root.parent_id)
            if not root:
                break

        if root:
            thread.append(root)
            # Find all replies
            self._collect_replies(session, root.comment_id, thread)

        return thread

    def _collect_replies(
        self,
        session: ReviewSession,
        parent_id: str,
        thread: List[Comment]
    ):
        """Recursively collect comment replies"""
        for comment in session.comments.values():
            if comment.parent_id == parent_id:
                thread.append(comment)
                self._collect_replies(session, comment.comment_id, thread)

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get session statistics"""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        open_comments = sum(1 for c in session.comments.values() if c.status == CommentStatus.OPEN)
        resolved_comments = sum(1 for c in session.comments.values() if c.status == CommentStatus.RESOLVED)

        pending_tasks = sum(1 for t in session.tasks.values() if t.status in [TaskStatus.TODO, TaskStatus.IN_PROGRESS])
        completed_tasks = sum(1 for t in session.tasks.values() if t.status == TaskStatus.COMPLETED)

        pending_decisions = sum(1 for d in session.decisions.values() if d.status in [DecisionStatus.PROPOSED, DecisionStatus.DISCUSSING])

        return {
            "session_id": session_id,
            "participants": len(session.participants),
            "online_participants": sum(1 for p in session.participants.values() if p.is_online),
            "total_comments": len(session.comments),
            "open_comments": open_comments,
            "resolved_comments": resolved_comments,
            "total_tasks": len(session.tasks),
            "pending_tasks": pending_tasks,
            "completed_tasks": completed_tasks,
            "total_decisions": len(session.decisions),
            "pending_decisions": pending_decisions,
            "is_active": session.is_active
        }

    def on_event(self, event_type: str, handler: Callable):
        """Register event handler"""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].append(handler)

    def _trigger_event(self, event_type: str, *args):
        """Trigger event handlers"""
        for handler in self.event_handlers.get(event_type, []):
            try:
                handler(*args)
            except Exception:
                pass  # Don't let handler errors break the system

    def _save_session(self, session: ReviewSession):
        """Save session to storage"""
        session_file = self.storage_path / f"{session.session_id}.json"

        # Convert to dict for JSON serialization
        data = {
            "session_id": session.session_id,
            "pr_id": session.pr_id,
            "repository": session.repository,
            "title": session.title,
            "description": session.description,
            "participants": {
                uid: {
                    "user_id": p.user_id,
                    "username": p.username,
                    "role": p.role.value,
                    "joined_at": p.joined_at,
                    "last_active": p.last_active,
                    "is_online": p.is_online
                }
                for uid, p in session.participants.items()
            },
            "comments": {
                cid: {
                    "comment_id": c.comment_id,
                    "author_id": c.author_id,
                    "content": c.content,
                    "comment_type": c.comment_type.value,
                    "status": c.status.value,
                    "file_path": c.file_path,
                    "line_number": c.line_number,
                    "parent_id": c.parent_id,
                    "created_at": c.created_at,
                    "updated_at": c.updated_at,
                    "resolved_by": c.resolved_by,
                    "resolved_at": c.resolved_at,
                    "reactions": c.reactions,
                    "metadata": c.metadata
                }
                for cid, c in session.comments.items()
            },
            "tasks": {
                tid: {
                    "task_id": t.task_id,
                    "title": t.title,
                    "description": t.description,
                    "assignee_id": t.assignee_id,
                    "status": t.status.value,
                    "priority": t.priority,
                    "created_by": t.created_by,
                    "created_at": t.created_at,
                    "due_date": t.due_date,
                    "completed_at": t.completed_at,
                    "related_comments": t.related_comments,
                    "metadata": t.metadata
                }
                for tid, t in session.tasks.items()
            },
            "decisions": {
                did: {
                    "decision_id": d.decision_id,
                    "title": d.title,
                    "description": d.description,
                    "proposed_by": d.proposed_by,
                    "status": d.status.value,
                    "created_at": d.created_at,
                    "votes": d.votes,
                    "required_approvals": d.required_approvals,
                    "comments": d.comments,
                    "finalized_at": d.finalized_at,
                    "metadata": d.metadata
                }
                for did, d in session.decisions.items()
            },
            "created_at": session.created_at,
            "started_at": session.started_at,
            "completed_at": session.completed_at,
            "is_active": session.is_active,
            "metadata": session.metadata
        }

        with open(session_file, 'w') as f:
            json.dump(data, f, indent=2)

    def load_session(self, session_id: str) -> Optional[ReviewSession]:
        """Load session from storage"""
        session_file = self.storage_path / f"{session_id}.json"
        if not session_file.exists():
            return None

        with open(session_file, 'r') as f:
            data = json.load(f)

        # Reconstruct session
        session = ReviewSession(
            session_id=data["session_id"],
            pr_id=data["pr_id"],
            repository=data["repository"],
            title=data["title"],
            description=data["description"],
            created_at=data["created_at"],
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            is_active=data["is_active"],
            metadata=data.get("metadata", {})
        )

        # Reconstruct participants
        for uid, p_data in data.get("participants", {}).items():
            session.participants[uid] = Participant(
                user_id=p_data["user_id"],
                username=p_data["username"],
                role=ParticipantRole(p_data["role"]),
                joined_at=p_data["joined_at"],
                last_active=p_data["last_active"],
                is_online=p_data["is_online"]
            )

        # Reconstruct comments
        for cid, c_data in data.get("comments", {}).items():
            session.comments[cid] = Comment(
                comment_id=c_data["comment_id"],
                author_id=c_data["author_id"],
                content=c_data["content"],
                comment_type=CommentType(c_data["comment_type"]),
                status=CommentStatus(c_data["status"]),
                file_path=c_data.get("file_path"),
                line_number=c_data.get("line_number"),
                parent_id=c_data.get("parent_id"),
                created_at=c_data["created_at"],
                updated_at=c_data["updated_at"],
                resolved_by=c_data.get("resolved_by"),
                resolved_at=c_data.get("resolved_at"),
                reactions=c_data.get("reactions", {}),
                metadata=c_data.get("metadata", {})
            )

        # Reconstruct tasks
        for tid, t_data in data.get("tasks", {}).items():
            session.tasks[tid] = Task(
                task_id=t_data["task_id"],
                title=t_data["title"],
                description=t_data["description"],
                assignee_id=t_data.get("assignee_id"),
                status=TaskStatus(t_data["status"]),
                priority=t_data["priority"],
                created_by=t_data["created_by"],
                created_at=t_data["created_at"],
                due_date=t_data.get("due_date"),
                completed_at=t_data.get("completed_at"),
                related_comments=t_data.get("related_comments", []),
                metadata=t_data.get("metadata", {})
            )

        # Reconstruct decisions
        for did, d_data in data.get("decisions", {}).items():
            session.decisions[did] = Decision(
                decision_id=d_data["decision_id"],
                title=d_data["title"],
                description=d_data["description"],
                proposed_by=d_data["proposed_by"],
                status=DecisionStatus(d_data["status"]),
                created_at=d_data["created_at"],
                votes=d_data.get("votes", {}),
                required_approvals=d_data["required_approvals"],
                comments=d_data.get("comments", []),
                finalized_at=d_data.get("finalized_at"),
                metadata=d_data.get("metadata", {})
            )

        self.sessions[session_id] = session
        return session


# Global instance
_collaboration_system = None


def get_collaboration_system(storage_path: Optional[str] = None) -> CollaborationSystem:
    """Get global collaboration system instance"""
    global _collaboration_system
    if _collaboration_system is None:
        _collaboration_system = CollaborationSystem(storage_path)
    return _collaboration_system
