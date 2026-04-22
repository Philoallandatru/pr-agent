"""
Code review assignment system.

Automatically assigns reviewers to pull requests based on:
- Reviewer expertise and skills
- Current workload
- File types and patterns
- Historical performance
- Availability
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path, PurePath
from typing import Dict, List, Optional, Set, Any
import json
import random
import fnmatch
import re


import re


def _glob_to_regex(pattern: str) -> re.Pattern:
    """Convert glob pattern to regex, supporting ** for recursive matching."""
    # Escape special regex characters except * and ?
    pattern = pattern.replace('\\', '/')
    pattern = re.escape(pattern)

    # Replace escaped glob patterns with regex equivalents
    pattern = pattern.replace(r'\*\*/', '(?:.+/)?')  # **/ matches any depth
    pattern = pattern.replace(r'/\*\*', '(?:/.+)?')  # /** matches any depth
    pattern = pattern.replace(r'\*\*', '.*')         # ** alone matches anything
    pattern = pattern.replace(r'\*', '[^/]*')        # * matches within a path segment
    pattern = pattern.replace(r'\?', '.')            # ? matches single character

    return re.compile(f'^{pattern}$')


class AssignmentStrategy(Enum):
    """Assignment strategy types."""
    ROUND_ROBIN = "round_robin"
    LOAD_BALANCED = "load_balanced"
    EXPERTISE_BASED = "expertise_based"
    RANDOM = "random"


class ReviewerStatus(Enum):
    """Reviewer availability status."""
    AVAILABLE = "available"
    BUSY = "busy"
    UNAVAILABLE = "unavailable"
    ON_LEAVE = "on_leave"


@dataclass
class Reviewer:
    """Represents a code reviewer."""
    reviewer_id: str
    name: str
    email: str
    skills: List[str] = field(default_factory=list)
    file_patterns: List[str] = field(default_factory=list)
    max_reviews: int = 5
    current_reviews: int = 0
    status: ReviewerStatus = ReviewerStatus.AVAILABLE
    priority: int = 1  # Higher priority = more likely to be assigned
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_available(self) -> bool:
        """Check if reviewer is available for new assignments."""
        return (
            self.status == ReviewerStatus.AVAILABLE and
            self.current_reviews < self.max_reviews
        )

    def can_review_file(self, file_path: str) -> bool:
        """Check if reviewer can review a specific file."""
        if not self.file_patterns:
            return True  # No restrictions

        # Normalize path separators for cross-platform compatibility
        normalized_path = file_path.replace('\\', '/')

        for pattern in self.file_patterns:
            # Convert glob pattern to regex and match
            regex = _glob_to_regex(pattern)
            if regex.match(normalized_path):
                return True
        return False

    def has_skill(self, skill: str) -> bool:
        """Check if reviewer has a specific skill."""
        return skill.lower() in [s.lower() for s in self.skills]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Reviewer":
        """Create from dictionary."""
        data = data.copy()
        data["status"] = ReviewerStatus(data["status"])
        return cls(**data)


@dataclass
class Assignment:
    """Represents a review assignment."""
    assignment_id: str
    pull_request_id: str
    repository: str
    reviewer_id: str
    assigned_at: datetime
    files: List[str] = field(default_factory=list)
    strategy: AssignmentStrategy = AssignmentStrategy.LOAD_BALANCED
    completed: bool = False
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["assigned_at"] = self.assigned_at.isoformat()
        data["completed_at"] = self.completed_at.isoformat() if self.completed_at else None
        data["strategy"] = self.strategy.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Assignment":
        """Create from dictionary."""
        data = data.copy()
        data["assigned_at"] = datetime.fromisoformat(data["assigned_at"])
        if data.get("completed_at"):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        data["strategy"] = AssignmentStrategy(data["strategy"])
        return cls(**data)


class AssignmentEngine:
    """Engine for assigning reviewers to pull requests."""

    def __init__(self, storage_path: Optional[str] = None):
        """Initialize assignment engine."""
        self.storage_path = Path(storage_path) if storage_path else Path.home() / ".pr-agent" / "assignments"
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.reviewers: Dict[str, Reviewer] = {}
        self.assignments: Dict[str, Assignment] = {}
        self.assignment_history: List[Assignment] = []
        self.round_robin_index: Dict[str, int] = {}  # Per repository

        self._load_state()

    def register_reviewer(self, reviewer: Reviewer) -> None:
        """Register a new reviewer."""
        self.reviewers[reviewer.reviewer_id] = reviewer
        self._save_state()

    def unregister_reviewer(self, reviewer_id: str) -> bool:
        """Unregister a reviewer."""
        if reviewer_id in self.reviewers:
            del self.reviewers[reviewer_id]
            self._save_state()
            return True
        return False

    def get_reviewer(self, reviewer_id: str) -> Optional[Reviewer]:
        """Get a reviewer by ID."""
        return self.reviewers.get(reviewer_id)

    def list_reviewers(
        self,
        status: Optional[ReviewerStatus] = None,
        available_only: bool = False
    ) -> List[Reviewer]:
        """List all reviewers."""
        reviewers = list(self.reviewers.values())

        if status:
            reviewers = [r for r in reviewers if r.status == status]

        if available_only:
            reviewers = [r for r in reviewers if r.is_available()]

        return reviewers

    def update_reviewer_status(
        self,
        reviewer_id: str,
        status: ReviewerStatus
    ) -> bool:
        """Update reviewer status."""
        reviewer = self.reviewers.get(reviewer_id)
        if reviewer:
            reviewer.status = status
            self._save_state()
            return True
        return False

    def assign_reviewers(
        self,
        pull_request_id: str,
        repository: str,
        files: List[str],
        num_reviewers: int = 2,
        strategy: AssignmentStrategy = AssignmentStrategy.LOAD_BALANCED,
        required_skills: Optional[List[str]] = None
    ) -> List[Assignment]:
        """Assign reviewers to a pull request."""
        # Get available reviewers
        available = self.list_reviewers(available_only=True)

        if not available:
            raise ValueError("No available reviewers")

        # Filter by required skills
        if required_skills:
            available = [
                r for r in available
                if any(r.has_skill(skill) for skill in required_skills)
            ]

        # Filter by file patterns
        available = [
            r for r in available
            if any(r.can_review_file(f) for f in files)
        ]

        if not available:
            raise ValueError("No reviewers match the requirements")

        # Select reviewers based on strategy
        if strategy == AssignmentStrategy.ROUND_ROBIN:
            selected = self._round_robin_selection(repository, available, num_reviewers)
        elif strategy == AssignmentStrategy.LOAD_BALANCED:
            selected = self._load_balanced_selection(available, num_reviewers)
        elif strategy == AssignmentStrategy.EXPERTISE_BASED:
            selected = self._expertise_based_selection(available, files, num_reviewers)
        elif strategy == AssignmentStrategy.RANDOM:
            selected = self._random_selection(available, num_reviewers)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

        # Create assignments
        assignments = []
        for reviewer in selected:
            assignment_id = f"{pull_request_id}_{reviewer.reviewer_id}"
            assignment = Assignment(
                assignment_id=assignment_id,
                pull_request_id=pull_request_id,
                repository=repository,
                reviewer_id=reviewer.reviewer_id,
                assigned_at=datetime.now(timezone.utc),
                files=files,
                strategy=strategy
            )

            self.assignments[assignment_id] = assignment
            assignments.append(assignment)

            # Update reviewer workload
            reviewer.current_reviews += 1

        self._save_state()
        return assignments

    def _round_robin_selection(
        self,
        repository: str,
        reviewers: List[Reviewer],
        count: int
    ) -> List[Reviewer]:
        """Select reviewers using round-robin strategy."""
        if repository not in self.round_robin_index:
            self.round_robin_index[repository] = 0

        selected = []
        index = self.round_robin_index[repository]

        for _ in range(min(count, len(reviewers))):
            selected.append(reviewers[index % len(reviewers)])
            index += 1

        self.round_robin_index[repository] = index
        return selected

    def _load_balanced_selection(
        self,
        reviewers: List[Reviewer],
        count: int
    ) -> List[Reviewer]:
        """Select reviewers with lowest current workload."""
        # Sort by current reviews (ascending) and priority (descending)
        sorted_reviewers = sorted(
            reviewers,
            key=lambda r: (r.current_reviews, -r.priority)
        )
        return sorted_reviewers[:count]

    def _expertise_based_selection(
        self,
        reviewers: List[Reviewer],
        files: List[str],
        count: int
    ) -> List[Reviewer]:
        """Select reviewers based on file expertise."""
        # Score reviewers based on file pattern matches
        scores = {}
        for reviewer in reviewers:
            score = 0
            for file_path in files:
                if reviewer.can_review_file(file_path):
                    score += 1
            scores[reviewer.reviewer_id] = score

        # Sort by score (descending) and workload (ascending)
        sorted_reviewers = sorted(
            reviewers,
            key=lambda r: (-scores[r.reviewer_id], r.current_reviews)
        )
        return sorted_reviewers[:count]

    def _random_selection(
        self,
        reviewers: List[Reviewer],
        count: int
    ) -> List[Reviewer]:
        """Select reviewers randomly."""
        return random.sample(reviewers, min(count, len(reviewers)))

    def complete_assignment(self, assignment_id: str) -> bool:
        """Mark an assignment as completed."""
        assignment = self.assignments.get(assignment_id)
        if not assignment:
            return False

        assignment.completed = True
        assignment.completed_at = datetime.now(timezone.utc)

        # Update reviewer workload
        reviewer = self.reviewers.get(assignment.reviewer_id)
        if reviewer and reviewer.current_reviews > 0:
            reviewer.current_reviews -= 1

        # Move to history
        self.assignment_history.append(assignment)
        del self.assignments[assignment_id]

        self._save_state()
        return True

    def get_assignment(self, assignment_id: str) -> Optional[Assignment]:
        """Get an assignment by ID."""
        # Check active assignments
        if assignment_id in self.assignments:
            return self.assignments[assignment_id]

        # Check history
        for assignment in self.assignment_history:
            if assignment.assignment_id == assignment_id:
                return assignment

        return None

    def list_assignments(
        self,
        reviewer_id: Optional[str] = None,
        repository: Optional[str] = None,
        completed: Optional[bool] = None
    ) -> List[Assignment]:
        """List assignments."""
        assignments = list(self.assignments.values())

        if completed is False:
            # Only active assignments
            pass
        elif completed is True:
            # Only completed assignments
            assignments = self.assignment_history.copy()
        else:
            # All assignments
            assignments.extend(self.assignment_history)

        if reviewer_id:
            assignments = [a for a in assignments if a.reviewer_id == reviewer_id]

        if repository:
            assignments = [a for a in assignments if a.repository == repository]

        return assignments

    def get_reviewer_stats(self, reviewer_id: str) -> Dict[str, Any]:
        """Get statistics for a reviewer."""
        reviewer = self.reviewers.get(reviewer_id)
        if not reviewer:
            return {}

        all_assignments = [
            a for a in self.assignment_history
            if a.reviewer_id == reviewer_id
        ]

        return {
            "reviewer_id": reviewer_id,
            "name": reviewer.name,
            "status": reviewer.status.value,
            "current_reviews": reviewer.current_reviews,
            "max_reviews": reviewer.max_reviews,
            "total_completed": len(all_assignments),
            "skills": reviewer.skills,
            "file_patterns": reviewer.file_patterns
        }

    def _save_state(self) -> None:
        """Save state to disk."""
        state = {
            "reviewers": {k: v.to_dict() for k, v in self.reviewers.items()},
            "assignments": {k: v.to_dict() for k, v in self.assignments.items()},
            "assignment_history": [a.to_dict() for a in self.assignment_history],
            "round_robin_index": self.round_robin_index
        }

        state_file = self.storage_path / "state.json"
        with open(state_file, "w") as f:
            json.dump(state, f, indent=2)

    def _load_state(self) -> None:
        """Load state from disk."""
        state_file = self.storage_path / "state.json"
        if not state_file.exists():
            return

        try:
            with open(state_file) as f:
                state = json.load(f)

            self.reviewers = {
                k: Reviewer.from_dict(v)
                for k, v in state.get("reviewers", {}).items()
            }

            self.assignments = {
                k: Assignment.from_dict(v)
                for k, v in state.get("assignments", {}).items()
            }

            self.assignment_history = [
                Assignment.from_dict(a)
                for a in state.get("assignment_history", [])
            ]

            self.round_robin_index = state.get("round_robin_index", {})

        except Exception as e:
            print(f"Failed to load state: {e}")


# Global instance
_engine: Optional[AssignmentEngine] = None


def get_assignment_engine() -> AssignmentEngine:
    """Get the global assignment engine instance."""
    global _engine
    if _engine is None:
        _engine = AssignmentEngine()
    return _engine
