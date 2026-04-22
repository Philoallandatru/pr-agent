"""
Code Review Bot System

Provides intelligent automated code review capabilities with learning and improvement.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import json
import re
from pathlib import Path


class BotCapability(Enum):
    """Bot capability types."""
    SYNTAX_CHECK = "syntax_check"
    STYLE_CHECK = "style_check"
    SECURITY_SCAN = "security_scan"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    BEST_PRACTICES = "best_practices"
    DOCUMENTATION_CHECK = "documentation_check"
    TEST_COVERAGE = "test_coverage"
    DEPENDENCY_ANALYSIS = "dependency_analysis"


class CommentType(Enum):
    """Comment types."""
    SUGGESTION = "suggestion"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"
    QUESTION = "question"


class ReviewMode(Enum):
    """Review modes."""
    FULL = "full"  # Full comprehensive review
    QUICK = "quick"  # Quick scan for critical issues
    FOCUSED = "focused"  # Focus on specific areas
    LEARNING = "learning"  # Learning mode with explanations


@dataclass
class BotComment:
    """Bot-generated comment."""
    comment_id: str
    file_path: str
    line_number: int
    comment_type: CommentType
    message: str
    suggestion: Optional[str] = None
    confidence: float = 1.0
    rule_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "comment_id": self.comment_id,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "comment_type": self.comment_type.value,
            "message": self.message,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
            "rule_id": self.rule_id,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ReviewResult:
    """Bot review result."""
    review_id: str
    pr_id: str
    bot_id: str
    mode: ReviewMode
    comments: List[BotComment] = field(default_factory=list)
    summary: str = ""
    issues_found: int = 0
    suggestions_made: int = 0
    execution_time: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "review_id": self.review_id,
            "pr_id": self.pr_id,
            "bot_id": self.bot_id,
            "mode": self.mode.value,
            "comments": [c.to_dict() for c in self.comments],
            "summary": self.summary,
            "issues_found": self.issues_found,
            "suggestions_made": self.suggestions_made,
            "execution_time": self.execution_time,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class BotConfig:
    """Bot configuration."""
    bot_id: str
    name: str
    capabilities: List[BotCapability]
    enabled: bool = True
    auto_comment: bool = True
    confidence_threshold: float = 0.7
    max_comments_per_file: int = 10
    learning_enabled: bool = True
    custom_rules: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LearningData:
    """Bot learning data."""
    rule_id: str
    feedback_count: int = 0
    positive_feedback: int = 0
    negative_feedback: int = 0
    accuracy: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def update_accuracy(self):
        """Update accuracy based on feedback."""
        if self.feedback_count > 0:
            self.accuracy = self.positive_feedback / self.feedback_count
        else:
            self.accuracy = 0.0


class ReviewerBot:
    """Intelligent code review bot."""

    def __init__(self, config: BotConfig, storage_path: Optional[Path] = None):
        """Initialize bot."""
        self.config = config
        self.storage_path = storage_path or Path(".pr_agent/bot_data")
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.reviews: Dict[str, ReviewResult] = {}
        self.learning_data: Dict[str, LearningData] = {}
        self.custom_checkers: Dict[str, Callable] = {}

        self._load_learning_data()

    def review_pr(self, pr_id: str, files: Dict[str, str],
                  mode: ReviewMode = ReviewMode.FULL) -> ReviewResult:
        """Review a pull request."""
        import time
        import uuid

        start_time = time.time()
        review_id = str(uuid.uuid4())

        result = ReviewResult(
            review_id=review_id,
            pr_id=pr_id,
            bot_id=self.config.bot_id,
            mode=mode
        )

        # Run checks based on capabilities
        for file_path, content in files.items():
            file_comments = self._review_file(file_path, content, mode)

            # Filter by confidence threshold
            file_comments = [
                c for c in file_comments
                if c.confidence >= self.config.confidence_threshold
            ]

            # Limit comments per file
            if len(file_comments) > self.config.max_comments_per_file:
                file_comments = sorted(
                    file_comments,
                    key=lambda c: c.confidence,
                    reverse=True
                )[:self.config.max_comments_per_file]

            result.comments.extend(file_comments)

        # Generate summary
        result.issues_found = sum(
            1 for c in result.comments
            if c.comment_type in [CommentType.ERROR, CommentType.WARNING]
        )
        result.suggestions_made = sum(
            1 for c in result.comments
            if c.comment_type == CommentType.SUGGESTION
        )
        result.summary = self._generate_summary(result)
        result.execution_time = time.time() - start_time

        self.reviews[review_id] = result
        return result

    def _review_file(self, file_path: str, content: str,
                     mode: ReviewMode) -> List[BotComment]:
        """Review a single file."""
        comments = []

        # Run capability-specific checks
        if BotCapability.SYNTAX_CHECK in self.config.capabilities:
            comments.extend(self._check_syntax(file_path, content))

        if BotCapability.STYLE_CHECK in self.config.capabilities:
            comments.extend(self._check_style(file_path, content))

        if BotCapability.SECURITY_SCAN in self.config.capabilities:
            comments.extend(self._check_security(file_path, content))

        if BotCapability.PERFORMANCE_ANALYSIS in self.config.capabilities:
            comments.extend(self._check_performance(file_path, content))

        if BotCapability.BEST_PRACTICES in self.config.capabilities:
            comments.extend(self._check_best_practices(file_path, content))

        if BotCapability.DOCUMENTATION_CHECK in self.config.capabilities:
            comments.extend(self._check_documentation(file_path, content))

        # Run custom checkers
        for checker_name, checker_func in self.custom_checkers.items():
            try:
                custom_comments = checker_func(file_path, content)
                if custom_comments:
                    comments.extend(custom_comments)
            except Exception:
                pass  # Ignore custom checker errors

        return comments

    def _check_syntax(self, file_path: str, content: str) -> List[BotComment]:
        """Check syntax issues."""
        import uuid
        comments = []

        # Check for common syntax issues
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Check for trailing whitespace
            if line.endswith(' ') or line.endswith('\t'):
                comments.append(BotComment(
                    comment_id=str(uuid.uuid4()),
                    file_path=file_path,
                    line_number=i,
                    comment_type=CommentType.SUGGESTION,
                    message="Trailing whitespace detected",
                    suggestion=line.rstrip(),
                    confidence=0.9,
                    rule_id="syntax_trailing_whitespace"
                ))

            # Check for mixed tabs and spaces
            if '\t' in line and '    ' in line:
                comments.append(BotComment(
                    comment_id=str(uuid.uuid4()),
                    file_path=file_path,
                    line_number=i,
                    comment_type=CommentType.WARNING,
                    message="Mixed tabs and spaces detected",
                    confidence=0.95,
                    rule_id="syntax_mixed_indentation"
                ))

        return comments

    def _check_style(self, file_path: str, content: str) -> List[BotComment]:
        """Check style issues."""
        import uuid
        comments = []

        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Check line length
            if len(line) > 120:
                comments.append(BotComment(
                    comment_id=str(uuid.uuid4()),
                    file_path=file_path,
                    line_number=i,
                    comment_type=CommentType.SUGGESTION,
                    message=f"Line too long ({len(line)} > 120 characters)",
                    confidence=0.8,
                    rule_id="style_line_length"
                ))

        return comments

    def _check_security(self, file_path: str, content: str) -> List[BotComment]:
        """Check security issues."""
        import uuid
        comments = []

        # Check for hardcoded secrets
        secret_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "Possible hardcoded password"),
            (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', "Possible hardcoded API key"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Possible hardcoded secret"),
        ]

        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, message in secret_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    comments.append(BotComment(
                        comment_id=str(uuid.uuid4()),
                        file_path=file_path,
                        line_number=i,
                        comment_type=CommentType.ERROR,
                        message=message,
                        confidence=0.85,
                        rule_id="security_hardcoded_secret"
                    ))

        return comments

    def _check_performance(self, file_path: str, content: str) -> List[BotComment]:
        """Check performance issues."""
        import uuid
        comments = []

        # Check for inefficient patterns
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Check for string concatenation in loops
            if 'for ' in line and '+=' in line and ('"' in line or "'" in line):
                comments.append(BotComment(
                    comment_id=str(uuid.uuid4()),
                    file_path=file_path,
                    line_number=i,
                    comment_type=CommentType.SUGGESTION,
                    message="Consider using list append and join instead of string concatenation in loop",
                    confidence=0.75,
                    rule_id="performance_string_concat"
                ))

        return comments

    def _check_best_practices(self, file_path: str, content: str) -> List[BotComment]:
        """Check best practices."""
        import uuid
        comments = []

        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # Check for bare except
            if re.search(r'except\s*:', line):
                comments.append(BotComment(
                    comment_id=str(uuid.uuid4()),
                    file_path=file_path,
                    line_number=i,
                    comment_type=CommentType.WARNING,
                    message="Avoid bare except clauses, specify exception types",
                    confidence=0.9,
                    rule_id="best_practice_bare_except"
                ))

        return comments

    def _check_documentation(self, file_path: str, content: str) -> List[BotComment]:
        """Check documentation issues."""
        import uuid
        comments = []

        # Check for functions without docstrings
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if re.match(r'\s*def\s+\w+\s*\(', line):
                # Check if next non-empty line is a docstring
                has_docstring = False
                for j in range(i, min(i + 3, len(lines))):
                    next_line = lines[j].strip()
                    if next_line.startswith('"""') or next_line.startswith("'''"):
                        has_docstring = True
                        break

                if not has_docstring:
                    comments.append(BotComment(
                        comment_id=str(uuid.uuid4()),
                        file_path=file_path,
                        line_number=i,
                        comment_type=CommentType.SUGGESTION,
                        message="Consider adding a docstring to document this function",
                        confidence=0.7,
                        rule_id="doc_missing_docstring"
                    ))

        return comments

    def _generate_summary(self, result: ReviewResult) -> str:
        """Generate review summary."""
        if not result.comments:
            return "No issues found. Code looks good! ✓"

        summary_parts = []
        summary_parts.append(f"Found {result.issues_found} issues and {result.suggestions_made} suggestions.")

        # Group by type
        by_type = {}
        for comment in result.comments:
            by_type.setdefault(comment.comment_type, []).append(comment)

        if CommentType.ERROR in by_type:
            summary_parts.append(f"- {len(by_type[CommentType.ERROR])} errors")
        if CommentType.WARNING in by_type:
            summary_parts.append(f"- {len(by_type[CommentType.WARNING])} warnings")
        if CommentType.SUGGESTION in by_type:
            summary_parts.append(f"- {len(by_type[CommentType.SUGGESTION])} suggestions")

        return "\n".join(summary_parts)

    def add_custom_checker(self, name: str, checker: Callable[[str, str], List[BotComment]]):
        """Add a custom checker function."""
        self.custom_checkers[name] = checker

    def remove_custom_checker(self, name: str):
        """Remove a custom checker."""
        self.custom_checkers.pop(name, None)

    def provide_feedback(self, comment_id: str, positive: bool):
        """Provide feedback on a comment for learning."""
        if not self.config.learning_enabled:
            return

        # Find the comment
        comment = None
        for review in self.reviews.values():
            for c in review.comments:
                if c.comment_id == comment_id:
                    comment = c
                    break
            if comment:
                break

        if not comment or not comment.rule_id:
            return

        # Update learning data
        if comment.rule_id not in self.learning_data:
            self.learning_data[comment.rule_id] = LearningData(rule_id=comment.rule_id)

        data = self.learning_data[comment.rule_id]
        data.feedback_count += 1
        if positive:
            data.positive_feedback += 1
        else:
            data.negative_feedback += 1
        data.update_accuracy()
        data.last_updated = datetime.now(timezone.utc)

        self._save_learning_data()

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get learning statistics."""
        if not self.learning_data:
            return {
                "total_rules": 0,
                "total_feedback": 0,
                "average_accuracy": 0.0,
                "rules": []
            }

        total_feedback = sum(d.feedback_count for d in self.learning_data.values())
        avg_accuracy = sum(d.accuracy for d in self.learning_data.values()) / len(self.learning_data)

        return {
            "total_rules": len(self.learning_data),
            "total_feedback": total_feedback,
            "average_accuracy": avg_accuracy,
            "rules": [
                {
                    "rule_id": data.rule_id,
                    "feedback_count": data.feedback_count,
                    "accuracy": data.accuracy,
                    "last_updated": data.last_updated.isoformat()
                }
                for data in sorted(
                    self.learning_data.values(),
                    key=lambda d: d.feedback_count,
                    reverse=True
                )
            ]
        }

    def _load_learning_data(self):
        """Load learning data from storage."""
        data_file = self.storage_path / f"{self.config.bot_id}_learning.json"
        if data_file.exists():
            try:
                with open(data_file, 'r') as f:
                    data = json.load(f)
                    for rule_id, rule_data in data.items():
                        self.learning_data[rule_id] = LearningData(
                            rule_id=rule_id,
                            feedback_count=rule_data['feedback_count'],
                            positive_feedback=rule_data['positive_feedback'],
                            negative_feedback=rule_data['negative_feedback'],
                            accuracy=rule_data['accuracy'],
                            last_updated=datetime.fromisoformat(rule_data['last_updated'])
                        )
            except Exception:
                pass  # Ignore load errors

    def _save_learning_data(self):
        """Save learning data to storage."""
        data_file = self.storage_path / f"{self.config.bot_id}_learning.json"
        try:
            data = {
                rule_id: {
                    "feedback_count": ld.feedback_count,
                    "positive_feedback": ld.positive_feedback,
                    "negative_feedback": ld.negative_feedback,
                    "accuracy": ld.accuracy,
                    "last_updated": ld.last_updated.isoformat()
                }
                for rule_id, ld in self.learning_data.items()
            }
            with open(data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass  # Ignore save errors

    def export_config(self) -> Dict[str, Any]:
        """Export bot configuration."""
        return {
            "bot_id": self.config.bot_id,
            "name": self.config.name,
            "capabilities": [c.value for c in self.config.capabilities],
            "enabled": self.config.enabled,
            "auto_comment": self.config.auto_comment,
            "confidence_threshold": self.config.confidence_threshold,
            "max_comments_per_file": self.config.max_comments_per_file,
            "learning_enabled": self.config.learning_enabled,
            "custom_rules": self.config.custom_rules
        }

    def get_review(self, review_id: str) -> Optional[ReviewResult]:
        """Get a review by ID."""
        return self.reviews.get(review_id)

    def list_reviews(self, pr_id: Optional[str] = None) -> List[ReviewResult]:
        """List reviews, optionally filtered by PR."""
        reviews = list(self.reviews.values())
        if pr_id:
            reviews = [r for r in reviews if r.pr_id == pr_id]
        return sorted(reviews, key=lambda r: r.created_at, reverse=True)
