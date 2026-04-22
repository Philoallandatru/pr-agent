"""
GraphQL API for PR Agent.

Provides a flexible GraphQL interface for querying repositories, reviews, and analytics.
"""

import strawberry
from typing import List, Optional
from datetime import datetime

from pr_agent.storage.database import Database


@strawberry.type
class Repository:
    """Repository type."""

    id: int
    url: str
    name: str
    enabled: bool
    last_review: Optional[datetime]
    total_reviews: int


@strawberry.type
class Review:
    """Review type."""

    id: int
    repository_id: int
    pr_number: int
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    result: Optional[str]


@strawberry.type
class Prompt:
    """Prompt type."""

    id: int
    name: str
    content: str
    created_at: datetime
    updated_at: Optional[datetime]


@strawberry.type
class User:
    """User type."""

    id: int
    username: str
    email: Optional[str]
    role: str
    created_at: datetime


@strawberry.type
class Organization:
    """Organization type."""

    id: int
    name: str
    created_at: datetime
    member_count: int


@strawberry.type
class AuditLog:
    """Audit log entry type."""

    id: int
    event_type: str
    user_id: str
    severity: str
    timestamp: datetime
    details: Optional[str]


@strawberry.type
class Plugin:
    """Plugin type."""

    name: str
    version: str
    description: str
    author: str
    enabled: bool


@strawberry.type
class AnalyticsMetrics:
    """Analytics metrics type."""

    total_reviews: int
    avg_review_time: float
    reviews_by_status: str  # JSON string
    top_repositories: str  # JSON string


@strawberry.input
class RepositoryInput:
    """Input for creating/updating repository."""

    url: str
    name: str
    enabled: bool = True


@strawberry.input
class PromptInput:
    """Input for creating/updating prompt."""

    name: str
    content: str


@strawberry.input
class ReviewFilter:
    """Filter for querying reviews."""

    repository_id: Optional[int] = None
    status: Optional[str] = None
    pr_number: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


@strawberry.type
class Query:
    """GraphQL queries."""

    @strawberry.field
    def repositories(self, limit: int = 100, offset: int = 0) -> List[Repository]:
        """Get all repositories."""
        db = Database()
        repos = db.get_repositories(limit=limit, offset=offset)
        return [
            Repository(
                id=r["id"],
                url=r["url"],
                name=r["name"],
                enabled=r["enabled"],
                last_review=r.get("last_review"),
                total_reviews=r.get("total_reviews", 0),
            )
            for r in repos
        ]

    @strawberry.field
    def repository(self, id: int) -> Optional[Repository]:
        """Get repository by ID."""
        db = Database()
        repo = db.get_repository(id)
        if not repo:
            return None
        return Repository(
            id=repo["id"],
            url=repo["url"],
            name=repo["name"],
            enabled=repo["enabled"],
            last_review=repo.get("last_review"),
            total_reviews=repo.get("total_reviews", 0),
        )

    @strawberry.field
    def reviews(
        self, filter: Optional[ReviewFilter] = None, limit: int = 100, offset: int = 0
    ) -> List[Review]:
        """Get reviews with optional filtering."""
        db = Database()

        # Build filter dict
        filter_dict = {}
        if filter:
            if filter.repository_id:
                filter_dict["repository_id"] = filter.repository_id
            if filter.status:
                filter_dict["status"] = filter.status
            if filter.pr_number:
                filter_dict["pr_number"] = filter.pr_number

        reviews = db.get_reviews(filter=filter_dict, limit=limit, offset=offset)
        return [
            Review(
                id=r["id"],
                repository_id=r["repository_id"],
                pr_number=r["pr_number"],
                status=r["status"],
                created_at=r["created_at"],
                completed_at=r.get("completed_at"),
                result=r.get("result"),
            )
            for r in reviews
        ]

    @strawberry.field
    def review(self, id: int) -> Optional[Review]:
        """Get review by ID."""
        db = Database()
        review = db.get_review(id)
        if not review:
            return None
        return Review(
            id=review["id"],
            repository_id=review["repository_id"],
            pr_number=review["pr_number"],
            status=review["status"],
            created_at=review["created_at"],
            completed_at=review.get("completed_at"),
            result=review.get("result"),
        )

    @strawberry.field
    def prompts(self, limit: int = 100, offset: int = 0) -> List[Prompt]:
        """Get all prompts."""
        db = Database()
        prompts = db.get_prompts(limit=limit, offset=offset)
        return [
            Prompt(
                id=p["id"],
                name=p["name"],
                content=p["content"],
                created_at=p["created_at"],
                updated_at=p.get("updated_at"),
            )
            for p in prompts
        ]

    @strawberry.field
    def prompt(self, id: int) -> Optional[Prompt]:
        """Get prompt by ID."""
        db = Database()
        prompt = db.get_prompt(id)
        if not prompt:
            return None
        return Prompt(
            id=prompt["id"],
            name=prompt["name"],
            content=prompt["content"],
            created_at=prompt["created_at"],
            updated_at=prompt.get("updated_at"),
        )

    @strawberry.field
    def users(self, limit: int = 100, offset: int = 0) -> List[User]:
        """Get all users."""
        from pr_agent.security import auth_manager

        users = auth_manager.list_users(limit=limit, offset=offset)
        return [
            User(
                id=u["id"],
                username=u["username"],
                email=u.get("email"),
                role=u["role"],
                created_at=u["created_at"],
            )
            for u in users
        ]

    @strawberry.field
    def audit_logs(
        self,
        user_id: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLog]:
        """Get audit logs."""
        from pr_agent.audit import get_audit_logger

        audit_logger = get_audit_logger()
        logs = audit_logger.get_logs(
            user_id=user_id, event_type=event_type, limit=limit, offset=offset
        )
        return [
            AuditLog(
                id=log["id"],
                event_type=log["event_type"],
                user_id=log["user_id"],
                severity=log["severity"],
                timestamp=log["timestamp"],
                details=log.get("details"),
            )
            for log in logs
        ]

    @strawberry.field
    def analytics(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> AnalyticsMetrics:
        """Get analytics metrics."""
        from pr_agent.analytics import get_analytics_engine
        import json

        engine = get_analytics_engine()
        metrics = engine.get_metrics(start_date=start_date, end_date=end_date)

        return AnalyticsMetrics(
            total_reviews=metrics["total_reviews"],
            avg_review_time=metrics["avg_review_time"],
            reviews_by_status=json.dumps(metrics["reviews_by_status"]),
            top_repositories=json.dumps(metrics["top_repositories"]),
        )

    @strawberry.field
    def plugins(self) -> List[Plugin]:
        """Get all plugins."""
        from pr_agent.plugins import get_plugin_manager

        manager = get_plugin_manager()
        plugins = manager.list_plugins()
        return [
            Plugin(
                name=p["name"],
                version=p["version"],
                description=p["description"],
                author=p["author"],
                enabled=p["enabled"],
            )
            for p in plugins
        ]


@strawberry.type
class Mutation:
    """GraphQL mutations."""

    @strawberry.mutation
    def create_repository(self, input: RepositoryInput) -> Repository:
        """Create a new repository."""
        db = Database()
        repo_id = db.add_repository(input.url, input.name, input.enabled)
        repo = db.get_repository(repo_id)
        return Repository(
            id=repo["id"],
            url=repo["url"],
            name=repo["name"],
            enabled=repo["enabled"],
            last_review=None,
            total_reviews=0,
        )

    @strawberry.mutation
    def update_repository(self, id: int, input: RepositoryInput) -> Optional[Repository]:
        """Update a repository."""
        db = Database()
        success = db.update_repository(id, input.url, input.name, input.enabled)
        if not success:
            return None
        repo = db.get_repository(id)
        return Repository(
            id=repo["id"],
            url=repo["url"],
            name=repo["name"],
            enabled=repo["enabled"],
            last_review=repo.get("last_review"),
            total_reviews=repo.get("total_reviews", 0),
        )

    @strawberry.mutation
    def delete_repository(self, id: int) -> bool:
        """Delete a repository."""
        db = Database()
        return db.delete_repository(id)

    @strawberry.mutation
    def create_prompt(self, input: PromptInput) -> Prompt:
        """Create a new prompt."""
        db = Database()
        prompt_id = db.add_prompt(input.name, input.content)
        prompt = db.get_prompt(prompt_id)
        return Prompt(
            id=prompt["id"],
            name=prompt["name"],
            content=prompt["content"],
            created_at=prompt["created_at"],
            updated_at=None,
        )

    @strawberry.mutation
    def update_prompt(self, id: int, input: PromptInput) -> Optional[Prompt]:
        """Update a prompt."""
        db = Database()
        success = db.update_prompt(id, input.name, input.content)
        if not success:
            return None
        prompt = db.get_prompt(id)
        return Prompt(
            id=prompt["id"],
            name=prompt["name"],
            content=prompt["content"],
            created_at=prompt["created_at"],
            updated_at=prompt.get("updated_at"),
        )

    @strawberry.mutation
    def delete_prompt(self, id: int) -> bool:
        """Delete a prompt."""
        db = Database()
        return db.delete_prompt(id)


# Create schema
schema = strawberry.Schema(query=Query, mutation=Mutation)
