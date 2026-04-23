"""
Web Platform API Server

FastAPI backend for PR-Agent web management platform.
Provides REST API for repository management, review history, and prompt customization.
"""

import os
import time
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Request, Depends, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from pydantic import BaseModel
import uvicorn

from pr_agent.config_loader import get_settings
from pr_agent.log import get_logger
from pr_agent.storage.database import Database
from pr_agent.monitoring.metrics import metrics, StructuredLogger
from pr_agent.security import (
    auth_manager,
    get_current_user,
    get_current_user_or_api_key,
    require_permission,
    require_role,
    User,
)
from pr_agent.tenants.manager import TenantManager
from pr_agent.servers import tenant_routes
from pr_agent.ratelimit import RateLimiter, QuotaManager
from pr_agent.ratelimit.middleware import RateLimitMiddleware, QuotaMiddleware
from pr_agent.health import HealthChecker
from pr_agent.config.hot_reload import get_hot_reload_manager
from pr_agent.audit import get_audit_logger, AuditEventType, AuditSeverity
from pr_agent.servers.log_stream import init_log_streaming, handle_log_stream, get_log_stream_manager
from pr_agent.backup import BackupManager
from pr_agent.plugins import PluginManager
from pr_agent.models import get_model_manager, ModelType, ModelStatus
from pr_agent.quality import get_quality_gate, QualityGateConfig, CheckType, Severity
from pr_agent.suggestions import get_suggestion_engine, SuggestionType, SuggestionPriority
from pr_agent.collaboration import get_collaboration_manager, User as CollabUser, UserStatus
from pr_agent.collaboration.websocket import handle_collaboration_websocket
from pr_agent.coverage import get_coverage_tracker, CoverageStatus
from pr_agent.ai_review import get_ai_reviewer, ReviewCategory, ReviewSeverity
from pr_agent.dependency_graph import (
    DependencyGraphAnalyzer,
    get_dependency_visualizer,
    NodeType,
)
from pr_agent.code_search import (
    get_search_engine,
    get_code_navigator,
    SearchType,
    SymbolType,
)
from pr_agent.refactoring import (
    get_refactoring_engine,
    RefactoringType,
    RefactoringSeverity,
)
from pr_agent.templates import (
    get_template_manager,
    TemplateLanguage,
    TemplateCategory,
)
from pr_agent.formatting import (
    get_formatter_manager,
    FormatterLanguage,
    FormatConfig,
)
from pr_agent.documentation import (
    get_doc_generator,
    DocLanguage,
    DocFormat,
)
from pr_agent.metrics import (
    get_metrics_analyzer,
    MetricType,
    Severity as MetricSeverity,
)
from pr_agent.ai_assistant import (
    get_assistant,
    AssistantCapability,
    MessageRole,
    ConfidenceLevel,
)
from pr_agent.export import (
    get_exporter,
    ExportFormat,
    ChartType,
    ChartData,
    ReportSection,
    ExportReport,
)
from pr_agent.notification_enhanced import (
    get_notification_system,
    NotificationEvent,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
)
from pr_agent.orchestration import (
    get_orchestration_engine,
    WorkflowDefinition,
    TaskDefinition,
    TaskType,
    WorkflowStatus,
    TaskStatus,
)
from strawberry.fastapi import GraphQLRouter
from pr_agent.graphql import schema

# Initialize structured logger
structured_logger = StructuredLogger(__name__)


# Pydantic models for request/response
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class APIKeyCreate(BaseModel):
    name: str
    permissions: List[str]
    expires_days: Optional[int] = None


class APIKeyResponse(BaseModel):
    key: str
    name: str
    permissions: List[str]
    expires_at: Optional[str]


class RepositoryCreate(BaseModel):
    project_key: str
    repo_slug: str
    polling_enabled: bool = True
    polling_interval: int = 300
    custom_prompts: Optional[Dict] = None


class RepositoryUpdate(BaseModel):
    polling_enabled: Optional[bool] = None
    polling_interval: Optional[int] = None
    custom_prompts: Optional[Dict] = None


class PRReviewCreate(BaseModel):
    repository_id: int
    pr_id: int
    pr_title: str
    pr_author: str
    pr_url: str
    commands_run: List[str]


class PRReviewUpdate(BaseModel):
    status: Optional[str] = None
    review_result: Optional[Dict] = None
    error_message: Optional[str] = None


class PromptTemplateCreate(BaseModel):
    command: str
    template: str
    repository_id: Optional[int] = None
    is_active: bool = True


class PromptTemplateUpdate(BaseModel):
    template: Optional[str] = None
    is_active: Optional[bool] = None


class LogCreate(BaseModel):
    level: str
    message: str
    details: Optional[Dict] = None


# Tenant management models
class OrganizationCreate(BaseModel):
    name: str
    slug: str
    plan: str = "free"
    settings: Optional[Dict] = None


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    plan: Optional[str] = None
    settings: Optional[Dict] = None


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class MemberAdd(BaseModel):
    user_id: int
    role: str = "member"


class InvitationCreate(BaseModel):
    email: str
    role: str = "member"
    expires_in_days: int = 7


# Initialize FastAPI app
app = FastAPI(
    title="PR-Agent Web Platform",
    description="Management API for PR-Agent auto-review system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database instance
db = Database()

# Tenant manager instance
tenant_manager = TenantManager(db.db_path)

# Initialize audit logger
audit_logger = get_audit_logger(
    db_path=get_settings().get("audit.db_path", "audit.db")
)
structured_logger.info("Audit logging initialized")

# Initialize hot reload manager
hot_reload_manager = None
if get_settings().get("config.hot_reload_enabled", False):
    config_path = os.path.join(os.path.dirname(__file__), "..", "settings", "configuration.toml")
    hot_reload_manager = get_hot_reload_manager(
        config_path=config_path,
        check_interval=get_settings().get("config.hot_reload_interval", 5.0)
    )
    hot_reload_manager.start()
    structured_logger.info("Configuration hot reload enabled")

# Initialize health checker
health_checker = HealthChecker(
    db_manager=db,
    cache_manager=None,  # Will be set after cache initialization
    config=get_settings().config
)

# Initialize rate limiter and quota manager
settings = get_settings()
rate_limit_enabled = settings.get("rate_limit.enabled", True)
quota_enabled = settings.get("quota.enabled", True)

if rate_limit_enabled:
    # Try to connect to Redis, fallback to memory
    redis_client = None
    try:
        import redis
        redis_url = settings.get("rate_limit.redis_url", "redis://localhost:6379/0")
        redis_client = redis.from_url(redis_url, decode_responses=False)
        redis_client.ping()
        structured_logger.info("Connected to Redis for rate limiting")
    except Exception as e:
        structured_logger.warning(f"Redis connection failed, using memory backend: {e}")

    rate_limiter = RateLimiter(
        redis_client=redis_client,
        default_limit=settings.get("rate_limit.default_limit", 1000),
        default_window=settings.get("rate_limit.default_window", 3600),
        strategy=settings.get("rate_limit.strategy", "sliding_window")
    )

    # Add rate limit middleware
    app.add_middleware(
        RateLimitMiddleware,
        rate_limiter=rate_limiter,
        key_func=lambda req: (
            f"user:{req.state.user.get('id')}"
            if hasattr(req.state, "user") and req.state.user
            else req.client.host if req.client else "unknown"
        ),
        exempt_paths=["/health", "/metrics", "/docs", "/openapi.json", "/redoc"]
    )
    structured_logger.info("Rate limiting enabled")

if quota_enabled:
    quota_manager = QuotaManager(db.db_path)

    # Add quota middleware
    app.add_middleware(
        QuotaMiddleware,
        quota_manager=quota_manager,
        org_id_func=lambda req: (
            req.state.user.get("org_id")
            if hasattr(req.state, "user") and req.state.user
            else None
        ),
        quota_paths={
            "/api/reviews": "reviews",
            "/api/repositories": "repositories"
        }
    )
    structured_logger.info("Quota management enabled")

# Register tenant routes
tenant_routes.set_tenant_manager(tenant_manager)
app.include_router(tenant_routes.router)

# Register GraphQL endpoint
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql", tags=["GraphQL"])


# Middleware for request tracking
@app.middleware("http")
async def track_requests(request: Request, call_next):
    """Track HTTP requests with metrics."""
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time
    metrics.track_http_request(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
        duration=duration
    )

    structured_logger.info(
        "HTTP request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration=f"{duration:.3f}s"
    )

    return response


# Health check
@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "status": "ok",
        "service": "PR-Agent Web Platform",
        "version": "1.0.0"
    }


# Authentication endpoints
@app.post("/api/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest, req: Request):
    """Authenticate user and return JWT token"""
    try:
        user = auth_manager.authenticate_user(request.username, request.password)
        if not user:
            # Log failed login attempt
            audit_logger.log(
                event_type=AuditEventType.LOGIN_FAILURE,
                severity=AuditSeverity.WARNING,
                username=request.username,
                ip_address=req.client.host if req.client else None,
                result="failure",
                message="Invalid credentials"
            )
            raise HTTPException(status_code=401, detail="Invalid username or password")

        from datetime import timedelta
        access_token = auth_manager.create_access_token(
            data={"sub": user.username, "role": user.role},
            expires_delta=timedelta(hours=24)
        )

        structured_logger.info("User logged in", username=user.username)

        # Log successful login
        audit_logger.log(
            event_type=AuditEventType.LOGIN_SUCCESS,
            severity=AuditSeverity.INFO,
            user_id=str(user.id) if hasattr(user, 'id') else None,
            username=user.username,
            ip_address=req.client.host if req.client else None,
            result="success",
            message="User logged in successfully",
            metadata={"role": user.role}
        )

        return TokenResponse(
            access_token=access_token,
            expires_in=24 * 3600
        )
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Login failed: {e}")
        raise HTTPException(status_code=500, detail="Login failed")


@app.get("/api/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information"""
    return current_user.to_dict()


@app.post("/api/auth/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    request: APIKeyCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new API key (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")

    try:
        key = auth_manager.create_api_key(request.name, request.permissions)

        expires_at = None
        if request.expires_days:
            from datetime import timedelta
            expires_at = (datetime.now() + timedelta(days=request.expires_days)).isoformat()

        structured_logger.info(
            "API key created",
            name=request.name,
            created_by=current_user.username
        )

        return APIKeyResponse(
            key=key,
            name=request.name,
            permissions=request.permissions,
            expires_at=expires_at
        )
    except Exception as e:
        get_logger().error(f"Failed to create API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/auth/api-keys")
async def list_api_keys(current_user: User = Depends(get_current_user)):
    """List all API keys (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")

    keys = [key.to_dict() for key in auth_manager.api_keys.values()]
    return {"api_keys": keys}


@app.delete("/api/auth/api-keys/{key_prefix}")
async def revoke_api_key(
    key_prefix: str,
    current_user: User = Depends(get_current_user)
):
    """Revoke an API key (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")

    # Find key by prefix
    key_to_revoke = None
    for key in auth_manager.api_keys.keys():
        if key.startswith(key_prefix):
            key_to_revoke = key
            break

    if not key_to_revoke:
        raise HTTPException(status_code=404, detail="API key not found")

    auth_manager.revoke_api_key(key_to_revoke)
    structured_logger.info("API key revoked", key_prefix=key_prefix, revoked_by=current_user.username)

    return {"message": "API key revoked successfully"}


@app.get("/api/health")
async def health_check(details: bool = Query(True, description="Include detailed information")):
    """
    Comprehensive health check endpoint.

    Checks:
    - Database connectivity and performance
    - Redis cache availability
    - System resources (CPU, memory, disk)
    - External services connectivity

    Args:
        details: Include detailed information in response

    Returns:
        Health status with component details
    """
    try:
        health_report = await health_checker.check_all(include_details=details)

        # Set HTTP status code based on health
        status_code = 200
        if health_report["status"] == "unhealthy":
            status_code = 503
        elif health_report["status"] == "degraded":
            status_code = 200  # Still accepting requests

        return health_report
    except Exception as e:
        structured_logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@app.get("/api/health/ready")
async def readiness_check():
    """
    Readiness check endpoint for Kubernetes/load balancers.

    Returns 200 if service is ready to accept requests.
    """
    readiness = health_checker.get_readiness()
    status_code = 200 if readiness["ready"] else 503
    return readiness


@app.get("/api/health/live")
async def liveness_check():
    """
    Liveness check endpoint for Kubernetes/load balancers.

    Returns 200 if service is alive.
    """
    return health_checker.get_liveness()


# Repository endpoints
@app.get("/api/repositories")
async def list_repositories(current_user=Depends(get_current_user_or_api_key)):
    """List all monitored repositories"""
    try:
        start_time = time.time()
        repos = db.get_all_repositories()
        metrics.track_database_query("get_all_repositories", time.time() - start_time)
        return {"repositories": repos}
    except Exception as e:
        get_logger().error(f"Failed to list repositories: {e}")
        metrics.increment_error("list_repositories_error")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/repositories")
async def create_repository(repo: RepositoryCreate, current_user=Depends(get_current_user_or_api_key)):
    """Add a new repository to monitor"""
    # Check write permission
    if not auth_manager.has_permission(current_user, "write"):
        raise HTTPException(status_code=403, detail="Write permission required")

    try:
        repo_id = db.add_repository(
            project_key=repo.project_key,
            repo_slug=repo.repo_slug,
            polling_enabled=repo.polling_enabled,
            polling_interval=repo.polling_interval,
            custom_prompts=repo.custom_prompts
        )
        return {"id": repo_id, "message": "Repository added successfully"}
    except Exception as e:
        get_logger().error(f"Failed to create repository: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/repositories/{repo_id}")
async def get_repository(repo_id: int, current_user=Depends(get_current_user_or_api_key)):
    """Get repository details"""
    repo = db.get_repository(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@app.put("/api/repositories/{repo_id}")
async def update_repository(repo_id: int, update: RepositoryUpdate, current_user=Depends(get_current_user_or_api_key)):
    """Update repository settings"""
    # Check write permission
    if not auth_manager.has_permission(current_user, "write"):
        raise HTTPException(status_code=403, detail="Write permission required")

    try:
        # Check if repository exists
        repo = db.get_repository(repo_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        db.update_repository(
            repo_id=repo_id,
            polling_enabled=update.polling_enabled,
            polling_interval=update.polling_interval,
            custom_prompts=update.custom_prompts
        )
        return {"message": "Repository updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to update repository: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/repositories/{repo_id}")
async def delete_repository(repo_id: int, current_user=Depends(get_current_user_or_api_key)):
    """Delete repository"""
    # Check write permission
    if not auth_manager.has_permission(current_user, "write"):
        raise HTTPException(status_code=403, detail="Write permission required")

    try:
        repo = db.get_repository(repo_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        db.delete_repository(repo_id)
        return {"message": "Repository deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to delete repository: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# PR Review endpoints
@app.get("/api/reviews")
async def list_reviews(
    repository_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user=Depends(get_current_user_or_api_key)
):
    """List PR reviews with filters"""
    try:
        reviews = db.get_pr_reviews(
            repository_id=repository_id,
            status=status,
            limit=limit,
            offset=offset
        )
        return {"reviews": reviews, "count": len(reviews)}
    except Exception as e:
        get_logger().error(f"Failed to list reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reviews")
async def create_review(review: PRReviewCreate, current_user=Depends(get_current_user_or_api_key)):
    """Create a new PR review record"""
    # Check write permission
    if not auth_manager.has_permission(current_user, "write"):
        raise HTTPException(status_code=403, detail="Write permission required")

    try:
        review_id = db.add_pr_review(
            repository_id=review.repository_id,
            pr_id=review.pr_id,
            pr_title=review.pr_title,
            pr_author=review.pr_author,
            pr_url=review.pr_url,
            commands_run=review.commands_run
        )
        return {"id": review_id, "message": "Review created successfully"}
    except Exception as e:
        get_logger().error(f"Failed to create review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reviews/{review_id}")
async def get_review(review_id: int, current_user=Depends(get_current_user_or_api_key)):
    """Get detailed review results"""
    review = db.get_pr_review(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@app.put("/api/reviews/{review_id}")
async def update_review(review_id: int, update: PRReviewUpdate, current_user=Depends(get_current_user_or_api_key)):
    """Update review status and results"""
    # Check write permission
    if not auth_manager.has_permission(current_user, "write"):
        raise HTTPException(status_code=403, detail="Write permission required")

    try:
        review = db.get_pr_review(review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")

        db.update_pr_review(
            review_id=review_id,
            status=update.status,
            review_result=update.review_result,
            error_message=update.error_message
        )
        return {"message": "Review updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to update review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reviews/{review_id}/retry")
async def retry_review(review_id: int, current_user=Depends(get_current_user_or_api_key)):
    """Retry a failed review"""
    # Check write permission
    if not auth_manager.has_permission(current_user, "write"):
        raise HTTPException(status_code=403, detail="Write permission required")

    try:
        review = db.get_pr_review(review_id)
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")

        # Reset status to pending
        db.update_pr_review(review_id=review_id, status="pending")

        # TODO: Trigger actual review process
        return {"message": "Review retry initiated"}
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to retry review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Prompt template endpoints
@app.get("/api/prompts")
async def list_prompts(
    repository_id: Optional[int] = Query(None),
    command: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user_or_api_key)
):
    """List prompt templates"""
    try:
        prompts = db.get_prompt_templates(
            repository_id=repository_id,
            command=command
        )
        return {"prompts": prompts}
    except Exception as e:
        get_logger().error(f"Failed to list prompts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/prompts")
async def create_prompt(
    prompt: PromptTemplateCreate,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Create a new prompt template"""
    if not auth_manager.has_permission(current_user, "write"):
        raise HTTPException(status_code=403, detail="Write permission required")

    try:
        prompt_id = db.add_prompt_template(
            command=prompt.command,
            template=prompt.template,
            repository_id=prompt.repository_id,
            is_active=prompt.is_active
        )
        return {"id": prompt_id, "message": "Prompt template created successfully"}
    except Exception as e:
        get_logger().error(f"Failed to create prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/prompts/{prompt_id}")
async def update_prompt(
    prompt_id: int,
    update: PromptTemplateUpdate,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Update prompt template"""
    if not auth_manager.has_permission(current_user, "write"):
        raise HTTPException(status_code=403, detail="Write permission required")

    try:
        db.update_prompt_template(
            template_id=prompt_id,
            template=update.template,
            is_active=update.is_active
        )
        return {"message": "Prompt template updated successfully"}
    except Exception as e:
        get_logger().error(f"Failed to update prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/prompts/{prompt_id}")
async def delete_prompt(
    prompt_id: int,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Delete prompt template"""
    if not auth_manager.has_permission(current_user, "delete"):
        raise HTTPException(status_code=403, detail="Delete permission required")

    try:
        db.delete_prompt_template(prompt_id)
        return {"message": "Prompt template deleted successfully"}
    except Exception as e:
        get_logger().error(f"Failed to delete prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# System monitoring endpoints
@app.get("/api/status")
async def get_status(current_user: User = Depends(get_current_user_or_api_key)):
    """Get system status"""
    try:
        # TODO: Check polling service status
        return {
            "polling_active": True,  # Placeholder
            "queue_size": 0,  # Placeholder
            "last_poll": datetime.now().isoformat()
        }
    except Exception as e:
        get_logger().error(f"Failed to get status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/logs")
async def get_logs(
    level: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get system logs"""
    try:
        logs = db.get_logs(level=level, limit=limit, offset=offset)
        return {"logs": logs, "count": len(logs)}
    except Exception as e:
        get_logger().error(f"Failed to get logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/logs")
async def create_log(
    log: LogCreate,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Add system log entry"""
    if not auth_manager.has_permission(current_user, "write"):
        raise HTTPException(status_code=403, detail="Write permission required")

    try:
        db.add_log(
            level=log.level,
            message=log.message,
            details=log.details
        )
        return {"message": "Log entry created"}
    except Exception as e:
        get_logger().error(f"Failed to create log: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics")
async def get_metrics(current_user: User = Depends(get_current_user_or_api_key)):
    """Get platform statistics and metrics"""
    try:
        stats = db.get_statistics()

        # Add system metrics
        from pr_agent.monitoring.metrics import get_system_metrics
        system_metrics = get_system_metrics()
        stats['system'] = system_metrics

        return stats
    except Exception as e:
        get_logger().error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics")
async def prometheus_metrics(current_user: User = Depends(get_current_user_or_api_key)):
    """Prometheus metrics endpoint"""
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        from fastapi.responses import Response

        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )
    except ImportError:
        return {"error": "Prometheus client not installed"}
    except Exception as e:
        get_logger().error(f"Failed to generate metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Analytics endpoints
@app.get("/api/analytics/overview")
async def get_analytics_overview(
    days: int = 30,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get analytics overview for the specified time period"""
    try:
        from pr_agent.analytics.engine import AnalyticsEngine
        engine = AnalyticsEngine(db)

        overview = engine.get_overview(days=days)
        return overview
    except Exception as e:
        get_logger().error(f"Failed to get analytics overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/trends")
async def get_analytics_trends(
    metric: str = "review_count",
    days: int = 30,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get trend analysis for a specific metric"""
    try:
        from pr_agent.analytics.engine import AnalyticsEngine
        engine = AnalyticsEngine(db)

        trends = engine.get_trends(metric=metric, days=days)
        return trends
    except Exception as e:
        get_logger().error(f"Failed to get trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/repository/{repo_id}")
async def get_repository_analytics(
    repo_id: int,
    days: int = 30,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get analytics for a specific repository"""
    try:
        from pr_agent.analytics.engine import AnalyticsEngine
        engine = AnalyticsEngine(db)

        analytics = engine.get_repository_analytics(repo_id=repo_id, days=days)
        return analytics
    except Exception as e:
        get_logger().error(f"Failed to get repository analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/report")
async def generate_analytics_report(
    start_date: str = None,
    end_date: str = None,
    format: str = "json",
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Generate comprehensive analytics report"""
    try:
        from pr_agent.analytics.engine import AnalyticsEngine
        from datetime import datetime

        engine = AnalyticsEngine(db)

        # Parse dates
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None

        report = engine.generate_report(start_date=start, end_date=end, format=format)

        if format == "json":
            return report
        else:
            # Return as downloadable file
            from fastapi.responses import Response
            return Response(
                content=report,
                media_type="text/plain",
                headers={"Content-Disposition": f"attachment; filename=analytics_report.{format}"}
            )
    except Exception as e:
        get_logger().error(f"Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Configuration endpoints
@app.get("/api/config")
async def get_config(current_user: User = Depends(get_current_user_or_api_key)):
    """Get current configuration (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin permission required")

    try:
        config = {
            "bitbucket_server": {
                "url": get_settings().get("bitbucket_server.url", ""),
                "polling_enabled": get_settings().get("bitbucket_server.enable_polling", False),
                "polling_interval": get_settings().get("bitbucket_server.polling_interval_seconds", 300),
            },
            "repo_context": {
                "enabled": get_settings().get("repo_context.enable_full_context", False),
                "max_related_files": get_settings().get("repo_context.max_related_files", 20),
            }
        }
        return config
    except Exception as e:
        get_logger().error(f"Failed to get config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/config")
async def update_config(
    config_update: Dict,
    current_user: User = Depends(require_role("admin")),
    req: Request = None
):
    """Update configuration (admin only)"""
    try:
        # Update configuration file
        import toml
        config_path = os.path.join(os.path.dirname(__file__), "..", "settings", "configuration.toml")

        # Read current config
        with open(config_path, 'r') as f:
            current_config = toml.load(f)

        # Merge updates
        for section, values in config_update.items():
            if section not in current_config:
                current_config[section] = {}
            current_config[section].update(values)

        # Write updated config
        with open(config_path, 'w') as f:
            toml.dump(current_config, f)

        structured_logger.info("Configuration updated", user=current_user.username, sections=list(config_update.keys()))

        # Log audit event
        audit_logger.log(
            event_type=AuditEventType.CONFIG_UPDATED,
            severity=AuditSeverity.INFO,
            user_id=str(current_user.id) if hasattr(current_user, 'id') else None,
            username=current_user.username,
            ip_address=req.client.host if req and req.client else None,
            action="update",
            result="success",
            message=f"Configuration updated: {', '.join(config_update.keys())}"
        )

        # Trigger reload if hot reload is enabled
        if hot_reload_manager:
            hot_reload_manager.watcher._trigger_reload()

        return {"message": "Configuration updated successfully"}
    except Exception as e:
        get_logger().error(f"Failed to update config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/reload")
async def reload_config(current_user: User = Depends(require_role("admin")), req: Request = None):
    """Manually trigger configuration reload (admin only)"""
    if not hot_reload_manager:
        raise HTTPException(status_code=503, detail="Hot reload not enabled")

    try:
        # Trigger manual reload by calling the watcher's reload method
        hot_reload_manager.watcher._trigger_reload()

        structured_logger.info("Manual config reload triggered", user=current_user.username)

        # Log audit event
        audit_logger.log(
            event_type=AuditEventType.CONFIG_RELOADED,
            severity=AuditSeverity.INFO,
            user_id=str(current_user.id) if hasattr(current_user, 'id') else None,
            username=current_user.username,
            ip_address=req.client.host if req and req.client else None,
            action="reload",
            result="success",
            message="Configuration reloaded manually"
        )

        return {
            "status": "success",
            "message": "Configuration reloaded successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        get_logger().error(f"Failed to reload config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/config/reload/status")
async def get_reload_status(current_user: User = Depends(get_current_user_or_api_key)):
    """Get hot reload status and history"""
    if not hot_reload_manager:
        return {
            "enabled": False,
            "message": "Hot reload not enabled"
        }

    try:
        status = hot_reload_manager.get_status()
        history = hot_reload_manager.get_reload_history(limit=10)

        return {
            "enabled": True,
            "status": status,
            "recent_reloads": history
        }
    except Exception as e:
        get_logger().error(f"Failed to get reload status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/reload/enable")
async def enable_hot_reload(current_user: User = Depends(require_role("admin"))):
    """Enable hot reload at runtime (admin only)"""
    global hot_reload_manager

    if hot_reload_manager and hot_reload_manager.watcher.is_running:
        return {
            "status": "already_enabled",
            "message": "Hot reload is already enabled"
        }

    try:
        config_path = os.path.join(os.path.dirname(__file__), "..", "settings", "configuration.toml")

        if not hot_reload_manager:
            hot_reload_manager = get_hot_reload_manager(config_path)

        hot_reload_manager.start()

        structured_logger.info("Hot reload enabled at runtime", user=current_user.username)

        return {
            "status": "success",
            "message": "Hot reload enabled successfully"
        }
    except Exception as e:
        get_logger().error(f"Failed to enable hot reload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/reload/disable")
async def disable_hot_reload(current_user: User = Depends(require_role("admin"))):
    """Disable hot reload at runtime (admin only)"""
    if not hot_reload_manager:
        return {
            "status": "already_disabled",
            "message": "Hot reload is not enabled"
        }

    try:
        hot_reload_manager.stop()

        structured_logger.info("Hot reload disabled at runtime", user=current_user.username)

        return {
            "status": "success",
            "message": "Hot reload disabled successfully"
        }
    except Exception as e:
        get_logger().error(f"Failed to disable hot reload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Audit log endpoints
@app.get("/api/audit/logs")
async def get_audit_logs(
    event_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Query audit logs (admin or viewer with audit permission)"""
    if current_user.role not in ["admin", "viewer"]:
        raise HTTPException(status_code=403, detail="Admin or viewer role required")

    try:
        # Parse filters
        event_types = None
        if event_type:
            try:
                event_types = [AuditEventType(event_type)]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid event type: {event_type}")

        severity_filter = None
        if severity:
            try:
                severity_filter = AuditSeverity(severity)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid severity: {severity}")

        start_dt = None
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_time format")

        end_dt = None
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_time format")

        # Query logs
        logs = audit_logger.query(
            event_types=event_types,
            severity=severity_filter,
            user_id=user_id,
            username=username,
            resource_type=resource_type,
            start_time=start_dt,
            end_time=end_dt,
            limit=limit,
            offset=offset
        )

        return {
            "logs": logs,
            "count": len(logs),
            "limit": limit,
            "offset": offset
        }
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to query audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/audit/statistics")
async def get_audit_statistics(
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    current_user: User = Depends(require_role("admin"))
):
    """Get audit log statistics (admin only)"""
    try:
        start_dt = None
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_time format")

        end_dt = None
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_time format")

        stats = audit_logger.get_statistics(
            start_time=start_dt,
            end_time=end_dt
        )

        return stats
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get audit statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/audit/cleanup")
async def cleanup_audit_logs(
    days: int = Query(90, ge=1, le=365),
    current_user: User = Depends(require_role("admin"))
):
    """Clean up old audit logs (admin only)"""
    try:
        deleted = audit_logger.cleanup_old_logs(days=days)

        audit_logger.log(
            event_type=AuditEventType.RESOURCE_DELETED,
            severity=AuditSeverity.INFO,
            user_id=str(current_user.id) if hasattr(current_user, 'id') else None,
            username=current_user.username,
            resource_type="audit_logs",
            action="cleanup",
            result="success",
            message=f"Cleaned up {deleted} audit logs older than {days} days",
            metadata={"days": days, "deleted_count": deleted}
        )

        return {
            "status": "success",
            "deleted_count": deleted,
            "retention_days": days
        }
    except Exception as e:
        get_logger().error(f"Failed to cleanup audit logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def start():
    """Start the web platform server"""
    host = get_settings().get("web_platform.host", "0.0.0.0")
    port = get_settings().get("web_platform.port", 8080)

    get_logger().info(f"Starting PR-Agent Web Platform on {host}:{port}")

    uvicorn.run(app, host=host, port=port)


# WebSocket endpoint for real-time log streaming
@app.websocket("/ws/logs")
async def websocket_logs(
    websocket: WebSocket,
    level: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for streaming logs in real-time.

    Query parameters:
    - level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - search: Search term to filter logs
    """
    await handle_log_stream(websocket, level=level, search=search)


@app.get("/api/logs/export")
async def export_logs(
    format: str = Query("json", regex="^(json|csv|txt)$"),
    lines: int = Query(1000, ge=1, le=10000),
    current_user: User = Depends(require_role("admin"))
):
    """Export recent logs in specified format (admin only)."""
    try:
        log_manager = get_log_stream_manager()
        logs = log_manager.log_buffer[-lines:]

        if format == "json":
            return {"logs": logs}
        elif format == "csv":
            import csv
            from io import StringIO

            output = StringIO()
            if logs:
                writer = csv.DictWriter(output, fieldnames=logs[0].keys())
                writer.writeheader()
                writer.writerows(logs)

            return {"content": output.getvalue(), "content_type": "text/csv"}
        else:  # txt
            lines_text = [
                f"[{log['timestamp']}] {log['level']} - {log['logger']}: {log['message']}"
                for log in logs
            ]
            return {"content": "\n".join(lines_text), "content_type": "text/plain"}

    except Exception as e:
        get_logger().error(f"Failed to export logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    init_log_streaming()
    structured_logger.info("Web platform started successfully")


# Backup and restore endpoints
backup_manager = BackupManager()


class BackupCreate(BaseModel):
    include_db: bool = True
    include_config: bool = True
    include_cache: bool = False
    include_logs: bool = False
    description: Optional[str] = None


class BackupRestore(BaseModel):
    restore_db: bool = True
    restore_config: bool = True
    restore_cache: bool = False
    restore_logs: bool = False
    create_backup_before_restore: bool = True


@app.post("/api/backups")
async def create_backup(
    backup_request: BackupCreate,
    current_user: User = Depends(require_role("admin"))
):
    """Create a new backup (admin only)."""
    try:
        backup_path = backup_manager.create_backup(
            include_db=backup_request.include_db,
            include_config=backup_request.include_config,
            include_cache=backup_request.include_cache,
            include_logs=backup_request.include_logs,
            description=backup_request.description,
        )

        audit_logger.log(
            event_type=AuditEventType.BACKUP_CREATED,
            user_id=current_user.username,
            severity=AuditSeverity.INFO,
            details={"backup_path": backup_path, "description": backup_request.description},
        )

        return {"message": "Backup created successfully", "backup_path": backup_path}

    except Exception as e:
        get_logger().error(f"Failed to create backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/backups")
async def list_backups(current_user: User = Depends(require_role("admin"))):
    """List all available backups (admin only)."""
    try:
        backups = backup_manager.list_backups()
        return {"backups": backups}
    except Exception as e:
        get_logger().error(f"Failed to list backups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/backups/{backup_id}")
async def get_backup_info(
    backup_id: str,
    current_user: User = Depends(require_role("admin"))
):
    """Get detailed information about a backup (admin only)."""
    try:
        backup_path = backup_manager.backup_dir / f"backup_{backup_id}.tar.{backup_manager.compression}"
        info = backup_manager.get_backup_info(str(backup_path))
        return info
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Backup not found")
    except Exception as e:
        get_logger().error(f"Failed to get backup info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/backups/{backup_id}/restore")
async def restore_backup(
    backup_id: str,
    restore_request: BackupRestore,
    current_user: User = Depends(require_role("admin"))
):
    """Restore from a backup (admin only)."""
    try:
        backup_path = backup_manager.backup_dir / f"backup_{backup_id}.tar.{backup_manager.compression}"

        if not backup_path.exists():
            raise HTTPException(status_code=404, detail="Backup not found")

        backup_manager.restore_backup(
            backup_path=str(backup_path),
            restore_db=restore_request.restore_db,
            restore_config=restore_request.restore_config,
            restore_cache=restore_request.restore_cache,
            restore_logs=restore_request.restore_logs,
            create_backup_before_restore=restore_request.create_backup_before_restore,
        )

        audit_logger.log(
            event_type=AuditEventType.BACKUP_RESTORED,
            user_id=current_user.username,
            severity=AuditSeverity.WARNING,
            details={"backup_id": backup_id, "backup_path": str(backup_path)},
        )

        return {"message": "Backup restored successfully"}

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Backup not found")
    except Exception as e:
        get_logger().error(f"Failed to restore backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/backups/{backup_id}")
async def delete_backup(
    backup_id: str,
    current_user: User = Depends(require_role("admin"))
):
    """Delete a backup (admin only)."""
    try:
        backup_path = backup_manager.backup_dir / f"backup_{backup_id}.tar.{backup_manager.compression}"

        if not backup_path.exists():
            raise HTTPException(status_code=404, detail="Backup not found")

        backup_manager.delete_backup(str(backup_path))

        audit_logger.log(
            event_type=AuditEventType.BACKUP_DELETED,
            user_id=current_user.username,
            severity=AuditSeverity.INFO,
            details={"backup_id": backup_id},
        )

        return {"message": "Backup deleted successfully"}

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Backup not found")
    except Exception as e:
        get_logger().error(f"Failed to delete backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Plugin management endpoints
plugin_manager = PluginManager()


class PluginConfig(BaseModel):
    config: Dict[str, Any]


@app.get("/api/plugins")
async def list_plugins(current_user: User = Depends(get_current_user)):
    """List all available plugins."""
    try:
        return {"plugins": plugin_manager.list_plugins()}
    except Exception as e:
        get_logger().error(f"Failed to list plugins: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/plugins/{plugin_name}/reload")
async def reload_plugin(
    plugin_name: str,
    current_user: User = Depends(require_role("admin"))
):
    """Reload a plugin (admin only)."""
    try:
        if plugin_manager.reload_plugin(plugin_name):
            audit_logger.log(
                event_type=AuditEventType.CONFIG_UPDATED,
                user_id=current_user.username,
                severity=AuditSeverity.INFO,
                details={"action": "reload_plugin", "plugin": plugin_name},
            )
            return {"message": f"Plugin {plugin_name} reloaded successfully"}
        else:
            raise HTTPException(status_code=404, detail="Plugin not found")
    except Exception as e:
        get_logger().error(f"Failed to reload plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/plugins/{plugin_name}/unload")
async def unload_plugin(
    plugin_name: str,
    current_user: User = Depends(require_role("admin"))
):
    """Unload a plugin (admin only)."""
    try:
        if plugin_manager.unload_plugin(plugin_name):
            audit_logger.log(
                event_type=AuditEventType.CONFIG_UPDATED,
                user_id=current_user.username,
                severity=AuditSeverity.INFO,
                details={"action": "unload_plugin", "plugin": plugin_name},
            )
            return {"message": f"Plugin {plugin_name} unloaded successfully"}
        else:
            raise HTTPException(status_code=404, detail="Plugin not found")
    except Exception as e:
        get_logger().error(f"Failed to unload plugin: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/plugins/{plugin_name}")
async def get_plugin_info(
    plugin_name: str,
    current_user: User = Depends(get_current_user)
):
    """Get plugin information."""
    try:
        plugin = plugin_manager.get_plugin(plugin_name)
        if not plugin:
            raise HTTPException(status_code=404, detail="Plugin not found")

        return plugin.get_metadata()
    except Exception as e:
        get_logger().error(f"Failed to get plugin info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# AI Model Management Endpoints
# ============================================================================

@app.get("/api/models")
async def list_models(
    status: Optional[str] = None,
    model_type: Optional[str] = None,
    provider: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """List all AI models with optional filtering."""
    try:
        model_manager = get_model_manager()

        # Parse filters
        status_filter = ModelStatus(status) if status else None
        type_filter = ModelType(model_type) if model_type else None

        models = model_manager.list_models(
            status=status_filter,
            model_type=type_filter,
            provider=provider
        )

        return [model.to_dict() for model in models]
    except Exception as e:
        get_logger().error(f"Failed to list models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/models")
async def register_model(
    model_data: Dict,
    current_user: User = Depends(require_role("admin"))
):
    """Register a new AI model."""
    try:
        model_manager = get_model_manager()

        model = model_manager.register_model(
            model_id=model_data["model_id"],
            name=model_data["name"],
            provider=model_data["provider"],
            model_type=ModelType(model_data["model_type"]),
            version=model_data["version"],
            config=model_data.get("config", {}),
            tags=model_data.get("tags", [])
        )

        get_audit_logger().log(
            event_type=AuditEventType.CONFIG_UPDATED,
            user_id=current_user.username,
            severity=AuditSeverity.INFO,
            details={"action": "register_model", "model_id": model.model_id}
        )

        return model.to_dict()
    except Exception as e:
        get_logger().error(f"Failed to register model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/models/{model_id}")
async def get_model(
    model_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get model by ID."""
    try:
        model_manager = get_model_manager()
        model = model_manager.get_model(model_id)

        if not model:
            raise HTTPException(status_code=404, detail="Model not found")

        return model.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/models/{model_id}")
async def update_model(
    model_id: str,
    updates: Dict,
    current_user: User = Depends(require_role("admin"))
):
    """Update model configuration."""
    try:
        model_manager = get_model_manager()

        # Convert string enums if present
        if "status" in updates:
            updates["status"] = ModelStatus(updates["status"])
        if "model_type" in updates:
            updates["model_type"] = ModelType(updates["model_type"])

        model = model_manager.update_model(model_id, **updates)

        get_audit_logger().log(
            event_type=AuditEventType.CONFIG_UPDATED,
            user_id=current_user.username,
            severity=AuditSeverity.INFO,
            details={"action": "update_model", "model_id": model_id, "updates": list(updates.keys())}
        )

        return model.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        get_logger().error(f"Failed to update model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/models/{model_id}")
async def delete_model(
    model_id: str,
    current_user: User = Depends(require_role("admin"))
):
    """Delete a model."""
    try:
        model_manager = get_model_manager()
        model_manager.delete_model(model_id)

        get_audit_logger().log(
            event_type=AuditEventType.CONFIG_UPDATED,
            user_id=current_user.username,
            severity=AuditSeverity.WARNING,
            details={"action": "delete_model", "model_id": model_id}
        )

        return {"message": f"Model {model_id} deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        get_logger().error(f"Failed to delete model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/models/{model_id}/activate")
async def activate_model(
    model_id: str,
    current_user: User = Depends(require_role("admin"))
):
    """Set model as active."""
    try:
        model_manager = get_model_manager()
        model_manager.set_active_model(model_id)

        get_audit_logger().log(
            event_type=AuditEventType.CONFIG_UPDATED,
            user_id=current_user.username,
            severity=AuditSeverity.INFO,
            details={"action": "activate_model", "model_id": model_id}
        )

        return {"message": f"Model {model_id} activated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        get_logger().error(f"Failed to activate model: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/models/{model_id}/metrics")
async def get_model_metrics(
    model_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get model performance metrics."""
    try:
        model_manager = get_model_manager()
        metrics = model_manager.get_metrics(model_id)

        if not metrics:
            raise HTTPException(status_code=404, detail="Model not found")

        from dataclasses import asdict
        return asdict(metrics)
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get model metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/models/{model_id}/health")
async def check_model_health(
    model_id: str,
    current_user: User = Depends(get_current_user)
):
    """Check model health status."""
    try:
        model_manager = get_model_manager()
        health = await model_manager.check_health(model_id)
        return health
    except Exception as e:
        get_logger().error(f"Failed to check model health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ab-tests")
async def create_ab_test(
    test_data: Dict,
    current_user: User = Depends(require_role("admin"))
):
    """Create an A/B test."""
    try:
        model_manager = get_model_manager()

        test = model_manager.create_ab_test(
            test_id=test_data["test_id"],
            models=test_data["models"],
            traffic_split=test_data["traffic_split"]
        )

        get_audit_logger().log(
            event_type=AuditEventType.CONFIG_UPDATED,
            user_id=current_user.username,
            severity=AuditSeverity.INFO,
            details={"action": "create_ab_test", "test_id": test.test_id}
        )

        return test.get_results()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        get_logger().error(f"Failed to create A/B test: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ab-tests/{test_id}")
async def get_ab_test(
    test_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get A/B test results."""
    try:
        model_manager = get_model_manager()
        test = model_manager.get_ab_test(test_id)

        if not test:
            raise HTTPException(status_code=404, detail="A/B test not found")

        return test.get_results()
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get A/B test: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ab-tests/{test_id}/end")
async def end_ab_test(
    test_id: str,
    winner_data: Optional[Dict] = None,
    current_user: User = Depends(require_role("admin"))
):
    """End an A/B test."""
    try:
        model_manager = get_model_manager()
        winner_model_id = winner_data.get("winner_model_id") if winner_data else None

        model_manager.end_ab_test(test_id, winner_model_id)

        get_audit_logger().log(
            event_type=AuditEventType.CONFIG_UPDATED,
            user_id=current_user.username,
            severity=AuditSeverity.INFO,
            details={"action": "end_ab_test", "test_id": test_id, "winner": winner_model_id}
        )

        return {"message": f"A/B test {test_id} ended successfully", "winner": winner_model_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        get_logger().error(f"Failed to end A/B test: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Quality Gate endpoints
class QualityCheckRequest(BaseModel):
    file_paths: List[str]
    config: Optional[Dict] = None


class QualityIssueResponse(BaseModel):
    check_type: str
    severity: str
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column: Optional[int] = None
    code: Optional[str] = None
    suggestion: Optional[str] = None
    metadata: Dict = {}


class QualityReportResponse(BaseModel):
    passed: bool
    issues: List[QualityIssueResponse]
    metrics: Dict
    timestamp: str
    duration_seconds: float


@app.post("/api/quality/check", response_model=QualityReportResponse)
async def check_quality(
    request: QualityCheckRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Run quality checks on files."""
    try:
        # Configure quality gate if custom config provided
        quality_gate = get_quality_gate()
        if request.config:
            from pr_agent.quality import configure_quality_gate
            config = QualityGateConfig(**request.config)
            configure_quality_gate(config)
            quality_gate = get_quality_gate()

        # Run checks
        report = quality_gate.check_files(request.file_paths)

        # Convert to response format
        issues = [
            QualityIssueResponse(
                check_type=issue.check_type.value,
                severity=issue.severity.value,
                message=issue.message,
                file_path=issue.file_path,
                line_number=issue.line_number,
                column=issue.column,
                code=issue.code,
                suggestion=issue.suggestion,
                metadata=issue.metadata
            )
            for issue in report.issues
        ]

        get_audit_logger().log(
            event_type=AuditEventType.SYSTEM_EVENT,
            user_id=current_user.username,
            severity=AuditSeverity.INFO,
            details={
                "action": "quality_check",
                "files_checked": len(request.file_paths),
                "issues_found": len(report.issues),
                "passed": report.passed
            }
        )

        return QualityReportResponse(
            passed=report.passed,
            issues=issues,
            metrics=report.metrics,
            timestamp=report.timestamp.isoformat(),
            duration_seconds=report.duration_seconds
        )
    except Exception as e:
        get_logger().error(f"Failed to run quality check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/quality/config")
async def get_quality_config(
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get current quality gate configuration."""
    try:
        quality_gate = get_quality_gate()
        config = quality_gate.config

        return {
            "max_cyclomatic_complexity": config.max_cyclomatic_complexity,
            "max_cognitive_complexity": config.max_cognitive_complexity,
            "max_function_length": config.max_function_length,
            "max_file_length": config.max_file_length,
            "min_line_coverage": config.min_line_coverage,
            "min_branch_coverage": config.min_branch_coverage,
            "check_secrets": config.check_secrets,
            "check_vulnerabilities": config.check_vulnerabilities,
            "enforce_style": config.enforce_style,
            "max_line_length": config.max_line_length,
            "max_duplication_percentage": config.max_duplication_percentage,
            "require_docstrings": config.require_docstrings,
            "min_comment_ratio": config.min_comment_ratio,
            "block_on_critical": config.block_on_critical,
            "block_on_high": config.block_on_high,
            "block_on_medium": config.block_on_medium
        }
    except Exception as e:
        get_logger().error(f"Failed to get quality config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/quality/config")
async def update_quality_config(
    config_data: Dict,
    current_user: User = Depends(require_role("admin"))
):
    """Update quality gate configuration."""
    try:
        from pr_agent.quality import configure_quality_gate

        config = QualityGateConfig(**config_data)
        configure_quality_gate(config)

        get_audit_logger().log(
            event_type=AuditEventType.CONFIG_UPDATED,
            user_id=current_user.username,
            severity=AuditSeverity.MEDIUM,
            details={"action": "update_quality_config", "config": config_data}
        )

        return {"message": "Quality gate configuration updated successfully"}
    except Exception as e:
        get_logger().error(f"Failed to update quality config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Code Suggestion endpoints
class SuggestionRequest(BaseModel):
    file_paths: List[str]
    suggestion_types: Optional[List[str]] = None


class SuggestionResponse(BaseModel):
    type: str
    priority: str
    title: str
    description: str
    file_path: str
    line_number: int
    original_code: str
    suggested_code: str
    reasoning: str
    tags: List[str]


@app.post("/api/suggestions/analyze")
async def analyze_code_suggestions(
    request: SuggestionRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Analyze code and generate improvement suggestions."""
    try:
        engine = get_suggestion_engine()

        # Parse suggestion types
        types = None
        if request.suggestion_types:
            types = [SuggestionType(t) for t in request.suggestion_types]

        # Analyze files
        all_suggestions = []
        for file_path in request.file_paths:
            suggestions = engine.analyze_file(file_path, types)
            all_suggestions.extend(suggestions)

        # Convert to response format
        response_suggestions = [
            SuggestionResponse(
                type=s.type.value,
                priority=s.priority.value,
                title=s.title,
                description=s.description,
                file_path=s.file_path,
                line_number=s.line_number,
                original_code=s.original_code,
                suggested_code=s.suggested_code,
                reasoning=s.reasoning,
                tags=s.tags
            )
            for s in all_suggestions
        ]

        get_audit_logger().log(
            event_type=AuditEventType.SYSTEM_EVENT,
            user_id=current_user.username,
            severity=AuditSeverity.INFO,
            details={
                "action": "code_suggestions",
                "files_analyzed": len(request.file_paths),
                "suggestions_generated": len(all_suggestions)
            }
        )

        return {
            "total_suggestions": len(all_suggestions),
            "files_analyzed": len(request.file_paths),
            "suggestions": response_suggestions
        }
    except Exception as e:
        get_logger().error(f"Failed to analyze code suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/suggestions/types")
async def get_suggestion_types(
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get available suggestion types."""
    return {
        "types": [
            {
                "value": t.value,
                "name": t.name,
                "description": {
                    "refactoring": "Code refactoring suggestions",
                    "performance": "Performance optimization suggestions",
                    "readability": "Code readability improvements",
                    "best_practice": "Best practice recommendations",
                    "security": "Security improvement suggestions"
                }.get(t.value, "")
            }
            for t in SuggestionType
        ]
    }


# Real-time Collaboration endpoints
class RoomCreateRequest(BaseModel):
    pr_number: int
    repository: str


@app.post("/api/collaboration/rooms")
async def create_collaboration_room(
    request: RoomCreateRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Create a new collaboration room for a PR."""
    try:
        manager = get_collaboration_manager()
        room = manager.create_room(request.pr_number, request.repository)

        get_audit_logger().log(
            event_type=AuditEventType.SYSTEM_EVENT,
            user_id=current_user.username,
            severity=AuditSeverity.INFO,
            details={
                "action": "create_collaboration_room",
                "room_id": room.room_id,
                "pr_number": request.pr_number,
                "repository": request.repository
            }
        )

        return {
            "room_id": room.room_id,
            "pr_number": room.pr_number,
            "repository": room.repository,
            "created_at": room.created_at
        }
    except Exception as e:
        get_logger().error(f"Failed to create collaboration room: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/collaboration/rooms/{room_id}")
async def get_collaboration_room(
    room_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get collaboration room details."""
    try:
        manager = get_collaboration_manager()
        room = manager.get_room(room_id)

        if not room:
            raise HTTPException(status_code=404, detail="Room not found")

        return {
            "room_id": room.room_id,
            "pr_number": room.pr_number,
            "repository": room.repository,
            "created_at": room.created_at,
            "active_users": [
                {
                    "id": u.id,
                    "name": u.name,
                    "email": u.email,
                    "status": u.status.value,
                    "current_file": u.current_file,
                    "cursor_position": u.cursor_position
                }
                for u in room.get_active_users()
            ],
            "comment_count": len(room.comments),
            "annotation_count": len(room.annotations)
        }
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get collaboration room: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/collaboration/rooms/{room_id}/comments")
async def get_room_comments(
    room_id: str,
    file_path: Optional[str] = None,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get comments in a collaboration room."""
    try:
        manager = get_collaboration_manager()
        room = manager.get_room(room_id)

        if not room:
            raise HTTPException(status_code=404, detail="Room not found")

        if file_path:
            comments = room.get_comments_for_file(file_path)
        else:
            comments = list(room.comments.values())

        return {
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
                            "created_at": r.created_at
                        }
                        for r in c.replies
                    ]
                }
                for c in comments
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get room comments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/collaboration/{room_id}")
async def collaboration_websocket(
    websocket: WebSocket,
    room_id: str,
    user_id: str = Query(...),
    user_name: str = Query(...),
    user_email: str = Query(...)
):
    """WebSocket endpoint for real-time collaboration."""
    await handle_collaboration_websocket(
        websocket,
        room_id,
        user_id,
        user_name,
        user_email
    )


# Code Coverage endpoints
class CoverageRunRequest(BaseModel):
    test_command: Optional[str] = None
    source_dirs: Optional[List[str]] = None


@app.post("/api/coverage/run")
async def run_coverage(
    request: CoverageRunRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Run tests with coverage and generate report."""
    try:
        tracker = get_coverage_tracker()
        report = tracker.run_coverage(
            test_command=request.test_command,
            source_dirs=request.source_dirs
        )

        get_audit_logger().log(
            event_type=AuditEventType.SYSTEM_EVENT,
            user_id=current_user.username,
            severity=AuditSeverity.INFO,
            details={
                "action": "run_coverage",
                "line_coverage": report.line_coverage_percent,
                "branch_coverage": report.branch_coverage_percent,
            }
        )

        return {
            "timestamp": report.timestamp,
            "line_coverage": {
                "percent": report.line_coverage_percent,
                "covered": report.lines_covered,
                "total": report.lines_valid,
            },
            "branch_coverage": {
                "percent": report.branch_coverage_percent,
                "covered": report.branches_covered,
                "total": report.branches_valid,
            },
            "status": report.status.value,
            "files_count": len(report.files),
        }
    except Exception as e:
        get_logger().error(f"Failed to run coverage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/coverage/summary")
async def get_coverage_summary(
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get coverage summary with trends."""
    try:
        tracker = get_coverage_tracker()
        summary = tracker.generate_summary()
        return summary
    except Exception as e:
        get_logger().error(f"Failed to get coverage summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/coverage/trend")
async def get_coverage_trend(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get coverage trend over time."""
    try:
        tracker = get_coverage_tracker()
        trend = tracker.get_trend(days=days)

        return {
            "timestamps": trend.timestamps,
            "line_rates": [r * 100 for r in trend.line_rates],
            "branch_rates": [r * 100 for r in trend.branch_rates],
        }
    except Exception as e:
        get_logger().error(f"Failed to get coverage trend: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/coverage/files")
async def get_coverage_files(
    threshold: float = Query(70.0, ge=0, le=100),
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get files with low coverage."""
    try:
        tracker = get_coverage_tracker()
        low_coverage = tracker.get_low_coverage_files(threshold=threshold)

        return {
            "threshold": threshold,
            "files": [
                {
                    "path": fc.file_path,
                    "line_coverage": fc.line_coverage_percent,
                    "branch_coverage": fc.branch_coverage_percent,
                    "lines_covered": fc.lines_covered,
                    "lines_total": fc.lines_valid,
                    "missing_lines": fc.missing_lines,
                    "status": fc.status.value,
                }
                for fc in sorted(low_coverage, key=lambda x: x.line_coverage_percent)
            ]
        }
    except Exception as e:
        get_logger().error(f"Failed to get coverage files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/coverage/file/{file_path:path}")
async def get_file_coverage(
    file_path: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get coverage for a specific file."""
    try:
        tracker = get_coverage_tracker()
        file_cov = tracker.get_file_coverage(file_path)

        if not file_cov:
            raise HTTPException(status_code=404, detail="File coverage not found")

        return {
            "path": file_cov.file_path,
            "line_coverage": file_cov.line_coverage_percent,
            "branch_coverage": file_cov.branch_coverage_percent,
            "lines_covered": file_cov.lines_covered,
            "lines_total": file_cov.lines_valid,
            "branches_covered": file_cov.branches_covered,
            "branches_total": file_cov.branches_valid,
            "missing_lines": file_cov.missing_lines,
            "status": file_cov.status.value,
        }
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get file coverage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# AI Review endpoints
class AIReviewFileRequest(BaseModel):
    file_path: str
    use_ai: bool = False


class AIReviewPRRequest(BaseModel):
    files: List[Dict[str, str]]  # [{"path": "...", "diff": "..."}]
    use_ai: bool = False


@app.post("/api/ai-review/file")
async def review_file(
    request: AIReviewFileRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Review a single file with AI-driven analysis."""
    try:
        reviewer = get_ai_reviewer()
        findings = reviewer.review_file(request.file_path)

        # Log audit event
        audit_logger = get_audit_logger()
        audit_logger.log_event(
            event_type=AuditEventType.REVIEW_COMPLETED,
            user_id=current_user.username,
            severity=AuditSeverity.INFO,
            details={
                "file_path": request.file_path,
                "findings_count": len(findings),
                "use_ai": request.use_ai
            }
        )

        return {
            "findings": [
                {
                    "category": f.category.value,
                    "severity": f.severity.value,
                    "title": f.title,
                    "description": f.description,
                    "file_path": f.file_path,
                    "line_start": f.line_start,
                    "line_end": f.line_end,
                    "code_snippet": f.code_snippet,
                    "suggestion": f.suggestion,
                    "confidence": f.confidence,
                }
                for f in findings
            ]
        }
    except Exception as e:
        get_logger().error(f"Failed to review file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ai-review/pr")
async def review_pr(
    request: AIReviewPRRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Review a pull request with AI-driven analysis."""
    try:
        reviewer = get_ai_reviewer()
        report = reviewer.review_pr(request.files)

        # Log audit event
        audit_logger = get_audit_logger()
        audit_logger.log_event(
            event_type=AuditEventType.REVIEW_COMPLETED,
            user_id=current_user.username,
            severity=AuditSeverity.INFO,
            details={
                "files_reviewed": report.files_reviewed,
                "total_findings": report.total_findings,
                "critical_count": report.critical_count,
                "high_count": report.high_count,
                "use_ai": request.use_ai
            }
        )

        return {
            "timestamp": report.timestamp,
            "files_reviewed": report.files_reviewed,
            "total_findings": report.total_findings,
            "critical_count": report.critical_count,
            "high_count": report.high_count,
            "medium_count": report.medium_count,
            "low_count": report.low_count,
            "by_category": report.by_category,
            "summary": report.summary,
            "findings": [
                {
                    "category": f.category.value,
                    "severity": f.severity.value,
                    "title": f.title,
                    "description": f.description,
                    "file_path": f.file_path,
                    "line_start": f.line_start,
                    "line_end": f.line_end,
                    "code_snippet": f.code_snippet,
                    "suggestion": f.suggestion,
                    "confidence": f.confidence,
                }
                for f in report.findings
            ]
        }
    except Exception as e:
        get_logger().error(f"Failed to review PR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ai-review/categories")
async def get_review_categories(
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get available review categories."""
    return {
        "categories": [
            {"value": cat.value, "name": cat.name}
            for cat in ReviewCategory
        ]
    }


@app.get("/api/ai-review/severities")
async def get_review_severities(
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get available severity levels."""
    return {
        "severities": [
            {"value": sev.value, "name": sev.name}
            for sev in ReviewSeverity
        ]
    }


# Dependency Graph endpoints
class DependencyAnalysisRequest(BaseModel):
    directory: str
    patterns: Optional[List[str]] = None


class DependencyVisualizationRequest(BaseModel):
    directory: str
    output_path: str
    format: str = "svg"
    layout: str = "dot"
    patterns: Optional[List[str]] = None


@app.post("/api/dependency-graph/analyze")
async def analyze_dependencies(
    request: DependencyAnalysisRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Analyze code dependencies in a directory."""
    try:
        analyzer = get_dependency_analyzer()
        graph = analyzer.analyze_directory(request.directory, request.patterns)

        return {
            "nodes": list(graph.nodes),
            "edges": [{"source": s, "target": t} for s, t in graph.edges],
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges)
        }
    except Exception as e:
        get_logger().error(f"Failed to analyze dependencies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dependency-graph/visualize")
async def visualize_dependencies(
    request: DependencyVisualizationRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Generate dependency graph visualization."""
    try:
        analyzer = get_dependency_analyzer()
        visualizer = get_dependency_visualizer()

        # Analyze dependencies
        graph = analyzer.analyze_directory(request.directory, request.patterns)

        # Generate visualization
        visualizer.generate_graph(
            graph,
            request.output_path,
            format=request.format,
            layout=request.layout
        )

        return {
            "message": "Visualization generated successfully",
            "output_path": f"{request.output_path}.{request.format}",
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges)
        }
    except Exception as e:
        get_logger().error(f"Failed to visualize dependencies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dependency-graph/cycles")
async def detect_dependency_cycles(
    request: DependencyAnalysisRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Detect circular dependencies."""
    try:
        analyzer = get_dependency_analyzer()
        graph = analyzer.analyze_directory(request.directory, request.patterns)
        cycles = analyzer.detect_cycles(graph)

        return {
            "cycles": cycles,
            "cycle_count": len(cycles),
            "has_cycles": len(cycles) > 0
        }
    except Exception as e:
        get_logger().error(f"Failed to detect cycles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dependency-graph/impact")
async def analyze_impact(
    directory: str = Body(...),
    module: str = Body(...),
    patterns: Optional[List[str]] = Body(None),
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Analyze impact of changing a module."""
    try:
        analyzer = get_dependency_analyzer()
        graph = analyzer.analyze_directory(directory, patterns)
        impact = analyzer.get_impact_analysis(graph, module)

        return {
            "module": module,
            "direct_dependents": impact["direct_dependents"],
            "all_dependents": impact["all_dependents"],
            "impact_score": impact["impact_score"]
        }
    except Exception as e:
        get_logger().error(f"Failed to analyze impact: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Code Search and Navigation Endpoints

@app.post("/api/code-search/index")
async def index_codebase(
    directory: str = Body(...),
    extensions: Optional[List[str]] = Body(None),
    exclude_patterns: Optional[List[str]] = Body(None),
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Index codebase for searching."""
    try:
        search_engine = get_search_engine(directory)
        search_engine.index_directory(extensions, exclude_patterns)

        # Get statistics
        total_files = len(search_engine.file_cache)
        total_symbols = sum(len(symbols) for symbols in search_engine.symbol_index.values())

        return {
            "status": "indexed",
            "total_files": total_files,
            "total_symbols": total_symbols
        }
    except Exception as e:
        get_logger().error(f"Failed to index codebase: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/code-search/search")
async def search_code(
    query: str = Body(...),
    search_type: str = Body("full_text"),
    case_sensitive: bool = Body(False),
    whole_word: bool = Body(False),
    max_results: int = Body(100),
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Search code."""
    try:
        search_engine = get_search_engine()

        if search_type == "full_text":
            results = search_engine.search_full_text(
                query,
                case_sensitive=case_sensitive,
                whole_word=whole_word,
                max_results=max_results
            )
        elif search_type == "regex":
            results = search_engine.search_regex(
                query,
                case_sensitive=case_sensitive,
                max_results=max_results
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid search type")

        return {
            "query": query,
            "search_type": search_type,
            "result_count": len(results),
            "results": [r.to_dict() for r in results]
        }
    except Exception as e:
        get_logger().error(f"Failed to search code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/code-search/symbols")
async def search_symbols(
    symbol_name: str = Body(...),
    symbol_type: Optional[str] = Body(None),
    fuzzy: bool = Body(False),
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Search for symbols."""
    try:
        search_engine = get_search_engine()

        # Convert symbol type string to enum
        symbol_type_enum = None
        if symbol_type:
            symbol_type_enum = SymbolType[symbol_type.upper()]

        symbols = search_engine.search_symbol(
            symbol_name,
            symbol_type=symbol_type_enum,
            fuzzy=fuzzy
        )

        return {
            "symbol_name": symbol_name,
            "result_count": len(symbols),
            "symbols": [s.to_dict() for s in symbols]
        }
    except Exception as e:
        get_logger().error(f"Failed to search symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/code-search/definition")
async def find_definition(
    symbol_name: str = Body(...),
    file_path: str = Body(...),
    line_number: int = Body(...),
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Find symbol definition."""
    try:
        search_engine = get_search_engine()
        symbol = search_engine.find_definition(symbol_name, file_path, line_number)

        if symbol:
            return {"found": True, "symbol": symbol.to_dict()}
        else:
            return {"found": False, "symbol": None}
    except Exception as e:
        get_logger().error(f"Failed to find definition: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/code-search/references")
async def find_references(
    symbol_name: str = Body(...),
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Find all references to a symbol."""
    try:
        search_engine = get_search_engine()
        references = search_engine.find_references(symbol_name)

        return {
            "symbol_name": symbol_name,
            "reference_count": len(references),
            "references": [r.to_dict() for r in references]
        }
    except Exception as e:
        get_logger().error(f"Failed to find references: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/code-search/outline/{file_path:path}")
async def get_file_outline(
    file_path: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get file outline."""
    try:
        navigator = get_code_navigator()
        outline = navigator.get_file_outline(file_path)

        # Convert symbols to dicts
        result = {}
        for key, symbols in outline.items():
            result[key] = [s.to_dict() for s in symbols]

        return {
            "file_path": file_path,
            "outline": result
        }
    except Exception as e:
        get_logger().error(f"Failed to get file outline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/code-search/workspace-symbols")
async def get_workspace_symbols(
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get all workspace symbols."""
    try:
        navigator = get_code_navigator()
        symbols = navigator.get_workspace_symbols()

        # Convert to dicts
        result = {}
        for key, symbol_list in symbols.items():
            result[key] = [s.to_dict() for s in symbol_list]

        return {
            "symbols": result,
            "total_count": sum(len(v) for v in symbols.values())
        }
    except Exception as e:
        get_logger().error(f"Failed to get workspace symbols: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Code Refactoring Endpoints

@app.post("/api/refactoring/rename")
async def rename_symbol(
    workspace: str = Body(...),
    old_name: str = Body(...),
    new_name: str = Body(...),
    scope: Optional[str] = Body(None),
    apply: bool = Body(False),
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Rename a symbol across the workspace."""
    try:
        engine = get_refactoring_engine()
        result = engine.rename_symbol(workspace, old_name, new_name, scope)

        if apply and result.success:
            applied = engine.apply_refactoring(result)
            if not applied:
                raise HTTPException(status_code=500, detail="Failed to apply refactoring")

        return {
            "success": result.success,
            "refactoring_type": result.refactoring_type.value,
            "affected_files": result.affected_files,
            "edit_count": len(result.edits),
            "warnings": result.warnings,
            "severity": result.severity.value,
            "preview": result.preview,
            "applied": apply and result.success
        }
    except Exception as e:
        get_logger().error(f"Failed to rename symbol: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/refactoring/extract-method")
async def extract_method(
    file_path: str = Body(...),
    start_line: int = Body(...),
    end_line: int = Body(...),
    method_name: str = Body(...),
    apply: bool = Body(False),
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Extract code block into a new method."""
    try:
        engine = get_refactoring_engine()
        result = engine.extract_method(file_path, start_line, end_line, method_name)

        if apply and result.success:
            applied = engine.apply_refactoring(result)
            if not applied:
                raise HTTPException(status_code=500, detail="Failed to apply refactoring")

        return {
            "success": result.success,
            "refactoring_type": result.refactoring_type.value,
            "affected_files": result.affected_files,
            "edit_count": len(result.edits),
            "warnings": result.warnings,
            "severity": result.severity.value,
            "preview": result.preview,
            "applied": apply and result.success
        }
    except Exception as e:
        get_logger().error(f"Failed to extract method: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/refactoring/inline-variable")
async def inline_variable(
    file_path: str = Body(...),
    variable_name: str = Body(...),
    line: int = Body(...),
    apply: bool = Body(False),
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Inline a variable."""
    try:
        engine = get_refactoring_engine()
        result = engine.inline_variable(file_path, variable_name, line)

        if apply and result.success:
            applied = engine.apply_refactoring(result)
            if not applied:
                raise HTTPException(status_code=500, detail="Failed to apply refactoring")

        return {
            "success": result.success,
            "refactoring_type": result.refactoring_type.value,
            "affected_files": result.affected_files,
            "edit_count": len(result.edits),
            "warnings": result.warnings,
            "severity": result.severity.value,
            "preview": result.preview,
            "applied": apply and result.success
        }
    except Exception as e:
        get_logger().error(f"Failed to inline variable: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/refactoring/preview")
async def preview_refactoring(
    refactoring_type: str = Body(...),
    params: Dict = Body(...),
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Preview a refactoring operation without applying it."""
    try:
        engine = get_refactoring_engine()

        if refactoring_type == "rename_symbol":
            result = engine.rename_symbol(
                params.get("workspace"),
                params.get("old_name"),
                params.get("new_name"),
                params.get("scope")
            )
        elif refactoring_type == "extract_method":
            result = engine.extract_method(
                params.get("file_path"),
                params.get("start_line"),
                params.get("end_line"),
                params.get("method_name")
            )
        elif refactoring_type == "inline_variable":
            result = engine.inline_variable(
                params.get("file_path"),
                params.get("variable_name"),
                params.get("line")
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid refactoring type")

        # Return detailed edits for preview
        edits = []
        for edit in result.edits:
            edits.append({
                "file_path": edit.file_path,
                "start_line": edit.start_line,
                "start_col": edit.start_col,
                "end_line": edit.end_line,
                "end_col": edit.end_col,
                "old_text": edit.old_text,
                "new_text": edit.new_text
            })

        return {
            "success": result.success,
            "refactoring_type": result.refactoring_type.value,
            "affected_files": result.affected_files,
            "edits": edits,
            "warnings": result.warnings,
            "severity": result.severity.value,
            "preview": result.preview
        }
    except Exception as e:
        get_logger().error(f"Failed to preview refactoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Code Template Endpoints

@app.get("/api/templates")
async def list_templates(
    language: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user_or_api_key)
):
    """List code templates with optional filters."""
    try:
        manager = get_template_manager()

        lang = TemplateLanguage(language) if language else None
        cat = TemplateCategory(category) if category else None
        tag_list = tags.split(",") if tags else None

        templates = manager.list_templates(language=lang, category=cat, tags=tag_list)

        return {
            "templates": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "language": t.language.value,
                    "category": t.category.value,
                    "tags": t.tags,
                    "author": t.author,
                    "usage_count": t.usage_count,
                    "created_at": t.created_at
                }
                for t in templates
            ],
            "total": len(templates)
        }
    except Exception as e:
        get_logger().error(f"Failed to list templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/templates/{template_id}")
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get a specific template by ID."""
    try:
        manager = get_template_manager()
        template = manager.get_template(template_id)

        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        return {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "language": template.language.value,
            "category": template.category.value,
            "content": template.content,
            "variables": [
                {
                    "name": v.name,
                    "description": v.description,
                    "default": v.default,
                    "required": v.required,
                    "type": v.type,
                    "choices": v.choices
                }
                for v in template.variables
            ],
            "tags": template.tags,
            "author": template.author,
            "usage_count": template.usage_count,
            "created_at": template.created_at,
            "updated_at": template.updated_at
        }
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/templates")
async def create_template(
    template_data: Dict,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Create a new code template."""
    try:
        from pr_agent.templates import CodeTemplate, TemplateVariable

        # Parse variables
        variables = []
        for var_data in template_data.get("variables", []):
            variables.append(TemplateVariable(**var_data))

        # Create template
        template = CodeTemplate(
            id=template_data["id"],
            name=template_data["name"],
            description=template_data["description"],
            language=TemplateLanguage(template_data["language"]),
            category=TemplateCategory(template_data["category"]),
            content=template_data["content"],
            variables=variables,
            tags=template_data.get("tags", []),
            author=current_user.username
        )

        manager = get_template_manager()
        created = manager.create_template(template)

        return {
            "id": created.id,
            "message": "Template created successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        get_logger().error(f"Failed to create template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/templates/{template_id}")
async def update_template(
    template_id: str,
    updates: Dict,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Update an existing template."""
    try:
        manager = get_template_manager()
        updated = manager.update_template(template_id, updates)

        return {
            "id": updated.id,
            "message": "Template updated successfully"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        get_logger().error(f"Failed to update template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/templates/{template_id}")
async def delete_template(
    template_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Delete a template."""
    try:
        manager = get_template_manager()
        success = manager.delete_template(template_id)

        if not success:
            raise HTTPException(status_code=404, detail="Template not found")

        return {"message": "Template deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to delete template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/templates/search")
async def search_templates(
    query: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Search templates by name, description, or tags."""
    try:
        manager = get_template_manager()
        results = manager.search_templates(query)

        return {
            "results": [
                {
                    "id": t.id,
                    "name": t.name,
                    "description": t.description,
                    "language": t.language.value,
                    "category": t.category.value,
                    "tags": t.tags,
                    "usage_count": t.usage_count
                }
                for t in results
            ],
            "total": len(results)
        }
    except Exception as e:
        get_logger().error(f"Failed to search templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/templates/{template_id}/instantiate")
async def instantiate_template(
    template_id: str,
    variables: Dict[str, any],
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Instantiate a template with variables."""
    try:
        manager = get_template_manager()
        instance = manager.instantiate_template(template_id, variables)

        return {
            "template_id": instance.template_id,
            "content": instance.content,
            "variables": instance.variables,
            "created_at": instance.created_at
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        get_logger().error(f"Failed to instantiate template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/templates/{template_id}/preview")
async def preview_template(
    template_id: str,
    variables: Dict[str, any],
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Preview template rendering without saving."""
    try:
        manager = get_template_manager()
        content = manager.preview_template(template_id, variables)

        return {
            "template_id": template_id,
            "content": content
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        get_logger().error(f"Failed to preview template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Code Formatting Endpoints

@app.post("/api/format")
async def format_code(
    code: str,
    language: str,
    config: Optional[Dict[str, any]] = None,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Format code for specified language."""
    try:
        # Parse config
        format_config = None
        if config:
            format_config = FormatConfig(**config)

        manager = get_formatter_manager(format_config)
        lang = FormatterLanguage(language)
        result = manager.format(code, lang)

        return {
            "success": result.success,
            "formatted_code": result.formatted_code,
            "changes_made": result.changes_made,
            "error": result.error,
            "formatter": result.formatter
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        get_logger().error(f"Failed to format code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/format/check")
async def check_format(
    code: str,
    language: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Check if code is properly formatted."""
    try:
        manager = get_formatter_manager()
        lang = FormatterLanguage(language)
        is_formatted = manager.check(code, lang)

        return {
            "is_formatted": is_formatted,
            "language": language
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        get_logger().error(f"Failed to check format: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/format/available")
async def get_available_formatters(
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get list of available formatters."""
    try:
        manager = get_formatter_manager()
        available = manager.get_available_formatters()

        return {
            "formatters": {
                lang.value: is_available
                for lang, is_available in available.items()
            }
        }
    except Exception as e:
        get_logger().error(f"Failed to get available formatters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Documentation Generation Endpoints
# ============================================================================

class GenerateDocsRequest(BaseModel):
    """Request to generate documentation."""
    source_dir: str
    output_dir: str
    language: str = "python"
    format: str = "markdown"
    patterns: Optional[List[str]] = None


class GenerateDocsResponse(BaseModel):
    """Response from documentation generation."""
    success: bool
    output_path: Optional[str] = None
    modules_count: int
    errors: List[str]
    warnings: List[str]


@app.post("/api/docs/generate", response_model=GenerateDocsResponse)
async def generate_documentation(
    request: GenerateDocsRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Generate documentation from source code."""
    try:
        generator = get_doc_generator()

        # Convert string to enum
        language = DocLanguage(request.language.lower())
        format = DocFormat(request.format.lower())

        result = generator.generate_docs(
            request.source_dir,
            request.output_dir,
            language=language,
            format=format,
            patterns=request.patterns
        )

        return GenerateDocsResponse(
            success=result.success,
            output_path=result.output_path,
            modules_count=len(result.modules),
            errors=result.errors,
            warnings=result.warnings
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        get_logger().error(f"Failed to generate documentation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ExtractModuleRequest(BaseModel):
    """Request to extract module documentation."""
    code: str
    language: str = "python"


@app.post("/api/docs/extract")
async def extract_module_docs(
    request: ExtractModuleRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Extract documentation from code."""
    import tempfile

    try:
        from pr_agent.documentation.generator import PythonDocExtractor

        language = DocLanguage(request.language.lower())

        if language != DocLanguage.PYTHON:
            raise HTTPException(
                status_code=400,
                detail=f"Extraction only supported for Python, got {language}"
            )

        # Write code to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(request.code)
            temp_path = f.name

        try:
            extractor = PythonDocExtractor()
            module_doc = extractor.extract_module(temp_path)
        finally:
            os.unlink(temp_path)

        return {
            "name": module_doc.name,
            "docstring": module_doc.docstring,
            "classes": [
                {
                    "name": cls.name,
                    "docstring": cls.docstring,
                    "bases": cls.bases,
                    "methods": [
                        {
                            "name": m.name,
                            "docstring": m.docstring,
                            "signature": m.signature,
                            "parameters": m.parameters,
                            "return_type": m.return_type
                        }
                        for m in cls.methods
                    ]
                }
                for cls in module_doc.classes
            ],
            "functions": [
                {
                    "name": f.name,
                    "docstring": f.docstring,
                    "signature": f.signature,
                    "parameters": f.parameters,
                    "return_type": f.return_type
                }
                for f in module_doc.functions
            ]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        get_logger().error(f"Failed to extract documentation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/docs/formats")
async def get_doc_formats(
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get available documentation formats."""
    return {
        "formats": [f.value for f in DocFormat],
        "languages": [l.value for l in DocLanguage]
    }


# ============================================================================
# Code Metrics Endpoints
# ============================================================================

class AnalyzeFileMetricsRequest(BaseModel):
    file_path: str


class AnalyzeProjectMetricsRequest(BaseModel):
    project_dir: str
    patterns: Optional[List[str]] = None


class GenerateMetricsReportRequest(BaseModel):
    project_dir: str
    format: str = "text"
    patterns: Optional[List[str]] = None


@app.post("/api/metrics/file")
async def analyze_file_metrics(
    request: AnalyzeFileMetricsRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Analyze metrics for a single file."""
    try:
        analyzer = get_metrics_analyzer()
        metrics = analyzer.analyze_file(request.file_path)

        return {
            "path": metrics.path,
            "language": metrics.language,
            "loc": metrics.loc,
            "sloc": metrics.sloc,
            "comments": metrics.comments,
            "blank": metrics.blank,
            "complexity": metrics.complexity,
            "maintainability": metrics.maintainability,
            "functions": metrics.functions,
            "classes": metrics.classes,
            "issues": metrics.issues
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        get_logger().error(f"Failed to analyze file metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/metrics/project")
async def analyze_project_metrics(
    request: AnalyzeProjectMetricsRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Analyze metrics for entire project."""
    try:
        analyzer = get_metrics_analyzer()
        metrics = analyzer.analyze_project(
            request.project_dir,
            patterns=request.patterns
        )

        return {
            "summary": {
                "total_files": metrics.total_files,
                "total_loc": metrics.total_loc,
                "total_sloc": metrics.total_sloc,
                "total_comments": metrics.total_comments,
                "total_blank": metrics.total_blank,
                "total_functions": metrics.total_functions,
                "total_classes": metrics.total_classes,
                "avg_complexity": metrics.avg_complexity,
                "avg_maintainability": metrics.avg_maintainability,
                "duplication_percentage": metrics.duplication_percentage,
                "technical_debt_hours": metrics.technical_debt_hours
            },
            "language_breakdown": metrics.language_breakdown,
            "complexity_distribution": metrics.complexity_distribution,
            "timestamp": metrics.timestamp,
            "files": [
                {
                    "path": f.path,
                    "language": f.language,
                    "loc": f.loc,
                    "sloc": f.sloc,
                    "complexity": f.complexity,
                    "maintainability": f.maintainability,
                    "issues": f.issues
                }
                for f in metrics.files[:100]  # Limit to first 100 files
            ]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        get_logger().error(f"Failed to analyze project metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/metrics/report")
async def generate_metrics_report(
    request: GenerateMetricsReportRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Generate metrics report."""
    try:
        analyzer = get_metrics_analyzer()
        metrics = analyzer.analyze_project(
            request.project_dir,
            patterns=request.patterns
        )

        report = analyzer.generate_report(metrics, format=request.format)

        return {
            "format": request.format,
            "report": report,
            "timestamp": metrics.timestamp
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        get_logger().error(f"Failed to generate metrics report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics/types")
async def get_metric_types(
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get available metric types."""
    return {
        "types": [t.value for t in MetricType],
        "severities": [s.value for s in MetricSeverity]
    }


# ============================================================================
# Workflow API
# ============================================================================

from pr_agent.workflow import (
    ReviewPipeline,
    ReviewConfig,
    ReviewStage,
    format_review_report
)


class WorkflowRunRequest(BaseModel):
    """Request to run review workflow."""
    file_paths: Optional[List[str]] = None
    directory: Optional[str] = None
    patterns: Optional[List[str]] = None
    config: Optional[Dict[str, Any]] = None


class WorkflowConfigRequest(BaseModel):
    """Request to configure workflow."""
    enabled_stages: Optional[List[str]] = None
    max_complexity: Optional[int] = None
    min_maintainability: Optional[float] = None
    max_file_lines: Optional[int] = None
    auto_format: Optional[bool] = None
    enable_ai: Optional[bool] = None
    fail_on_critical: Optional[bool] = None
    fail_on_high: Optional[bool] = None


@app.post("/api/workflow/run")
async def run_review_workflow(
    request: WorkflowRunRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """
    Run automated code review workflow.

    Can review specific files or an entire directory.
    """
    try:
        # Build config
        config = ReviewConfig()

        if request.config:
            if "enabled_stages" in request.config:
                config.enabled_stages = {
                    ReviewStage(s) for s in request.config["enabled_stages"]
                }
            if "max_complexity" in request.config:
                config.max_complexity = request.config["max_complexity"]
            if "min_maintainability" in request.config:
                config.min_maintainability = request.config["min_maintainability"]
            if "max_file_lines" in request.config:
                config.max_file_lines = request.config["max_file_lines"]
            if "auto_format" in request.config:
                config.auto_format = request.config["auto_format"]
            if "enable_ai" in request.config:
                config.enable_ai = request.config["enable_ai"]
            if "fail_on_critical" in request.config:
                config.fail_on_critical = request.config["fail_on_critical"]
            if "fail_on_high" in request.config:
                config.fail_on_high = request.config["fail_on_high"]

        # Create pipeline
        pipeline = ReviewPipeline(config)

        # Run review
        if request.file_paths:
            result = await pipeline.review_files(request.file_paths)
        elif request.directory:
            result = await pipeline.review_directory(
                request.directory,
                patterns=request.patterns
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Either file_paths or directory must be provided"
            )

        # Format response
        return {
            "success": result.success,
            "start_time": result.start_time.isoformat(),
            "end_time": result.end_time.isoformat(),
            "duration_seconds": result.total_duration_seconds,
            "summary": result.summary,
            "stages": [
                {
                    "stage": s.stage.value,
                    "success": s.success,
                    "duration_seconds": s.duration_seconds,
                    "issue_count": len(s.issues),
                    "error": s.error
                }
                for s in result.stages
            ],
            "issues": [
                {
                    "severity": i.severity.value,
                    "category": i.category,
                    "message": i.message,
                    "file_path": i.file_path,
                    "line_number": i.line_number,
                    "suggestion": i.suggestion,
                    "auto_fixable": i.auto_fixable
                }
                for i in result.issues
            ]
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        get_logger().error(f"Failed to run workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workflow/report")
async def generate_workflow_report(
    request: WorkflowRunRequest,
    format: str = "markdown",
    current_user: User = Depends(get_current_user_or_api_key)
):
    """
    Run workflow and generate formatted report.

    Supports text, markdown, and json formats.
    """
    try:
        # Build config
        config = ReviewConfig()
        if request.config:
            if "enabled_stages" in request.config:
                config.enabled_stages = {
                    ReviewStage(s) for s in request.config["enabled_stages"]
                }

        # Create pipeline
        pipeline = ReviewPipeline(config)

        # Run review
        if request.file_paths:
            result = await pipeline.review_files(request.file_paths)
        elif request.directory:
            result = await pipeline.review_directory(
                request.directory,
                patterns=request.patterns
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Either file_paths or directory must be provided"
            )

        # Generate report
        report = format_review_report(result, format=format)

        return {
            "format": format,
            "report": report,
            "success": result.success,
            "timestamp": result.end_time.isoformat()
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        get_logger().error(f"Failed to generate workflow report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflow/stages")
async def get_workflow_stages(
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get available workflow stages."""
    return {
        "stages": [s.value for s in ReviewStage],
        "default_stages": [
            ReviewStage.INITIALIZATION.value,
            ReviewStage.QUALITY_GATE.value,
            ReviewStage.FORMATTING.value,
            ReviewStage.METRICS.value,
            ReviewStage.SECURITY.value,
            ReviewStage.DOCUMENTATION.value,
            ReviewStage.FINALIZATION.value
        ]
    }


@app.post("/api/workflow/config")
async def configure_workflow(
    request: WorkflowConfigRequest,
    current_user: User = Depends(require_role("admin"))
):
    """Configure default workflow settings (admin only)."""
    try:
        config = ReviewConfig()

        if request.enabled_stages is not None:
            config.enabled_stages = {ReviewStage(s) for s in request.enabled_stages}
        if request.max_complexity is not None:
            config.max_complexity = request.max_complexity
        if request.min_maintainability is not None:
            config.min_maintainability = request.min_maintainability
        if request.max_file_lines is not None:
            config.max_file_lines = request.max_file_lines
        if request.auto_format is not None:
            config.auto_format = request.auto_format
        if request.enable_ai is not None:
            config.enable_ai = request.enable_ai
        if request.fail_on_critical is not None:
            config.fail_on_critical = request.fail_on_critical
        if request.fail_on_high is not None:
            config.fail_on_high = request.fail_on_high

        # TODO: Persist configuration to database or file

        return {
            "status": "success",
            "message": "Workflow configuration updated",
            "config": {
                "enabled_stages": [s.value for s in config.enabled_stages],
                "max_complexity": config.max_complexity,
                "min_maintainability": config.min_maintainability,
                "max_file_lines": config.max_file_lines,
                "auto_format": config.auto_format,
                "enable_ai": config.enable_ai,
                "fail_on_critical": config.fail_on_critical,
                "fail_on_high": config.fail_on_high
            }
        }

    except Exception as e:
        get_logger().error(f"Failed to configure workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Impact Analysis API
# ============================================================================

from pr_agent.impact import (
    ImpactAnalyzer,
    ChangeType,
    RiskLevel,
)
from pr_agent.trends import (
    TrendsAnalyzer,
    MetricType,
    TrendDirection,
    visualize_report as visualize_trends_report,
)
from pr_agent.scheduler import (
    get_scheduler,
    ReviewJob,
    ReviewStatus,
    ReviewPriority,
    TriggerType,
)
from pr_agent.reports import (
    ReportGenerator,
    ReportFormat,
    ReportSection,
    QualityMetrics,
    TrendData,
    Issue,
    Recommendation,
)


class ImpactAnalysisRequest(BaseModel):
    """Request for impact analysis."""
    changed_files: List[str]
    repo_path: Optional[str] = None
    include_tests: bool = True
    max_depth: int = 3


@app.post("/api/impact/analyze")
async def analyze_impact(
    request: ImpactAnalysisRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """
    Analyze the impact of code changes.

    Returns impact analysis including:
    - Changed files details
    - Impacted files (direct and indirect)
    - Affected tests
    - Risk assessment
    - Dependency graph
    """
    try:
        # Use provided repo path or default to current directory
        repo_path = request.repo_path or os.getcwd()

        # Create analyzer
        analyzer = ImpactAnalyzer(repo_path)

        # Analyze changes
        result = analyzer.analyze_changes(
            changed_files=request.changed_files,
            include_tests=request.include_tests,
            max_depth=request.max_depth
        )

        # Format response
        return {
            "analysis_time": result.analysis_time.isoformat(),
            "changes": [
                {
                    "file_path": c.file_path,
                    "change_type": c.change_type.value,
                    "lines_added": c.lines_added,
                    "lines_deleted": c.lines_deleted,
                    "functions_changed": c.functions_changed,
                    "classes_changed": c.classes_changed
                }
                for c in result.changes
            ],
            "impacted_files": [
                {
                    "file_path": f.file_path,
                    "impact_type": f.impact_type,
                    "distance": f.distance,
                    "reason": f.reason
                }
                for f in result.impacted_files
            ],
            "affected_tests": result.affected_tests,
            "risk_assessment": {
                "level": result.risk_assessment.level.value,
                "score": result.risk_assessment.score,
                "factors": result.risk_assessment.factors,
                "recommendations": result.risk_assessment.recommendations
            },
            "dependency_graph": result.dependency_graph,
            "metadata": result.metadata
        }

    except Exception as e:
        get_logger().error(f"Failed to analyze impact: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/impact/visualize")
async def visualize_impact(
    request: ImpactAnalysisRequest,
    format: str = "text",
    current_user: User = Depends(get_current_user_or_api_key)
):
    """
    Visualize impact analysis results.

    Supported formats:
    - text: Human-readable text report
    - dot: GraphViz DOT format
    """
    try:
        # Use provided repo path or default to current directory
        repo_path = request.repo_path or os.getcwd()

        # Create analyzer
        analyzer = ImpactAnalyzer(repo_path)

        # Analyze changes
        result = analyzer.analyze_changes(
            changed_files=request.changed_files,
            include_tests=request.include_tests,
            max_depth=request.max_depth
        )

        # Generate visualization
        visualization = analyzer.visualize_impact(result, output_format=format)

        return {
            "format": format,
            "content": visualization
        }

    except Exception as e:
        get_logger().error(f"Failed to visualize impact: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Quality Trends API
# ============================================================================


class TrendsRecordRequest(BaseModel):
    """Request to record quality metrics."""
    metrics: Dict[str, float]
    file_path: Optional[str] = None
    commit_hash: Optional[str] = None
    storage_path: Optional[str] = None


class TrendsAnalysisRequest(BaseModel):
    """Request for trends analysis."""
    metric_type: str
    days: int = 30
    file_path: Optional[str] = None
    storage_path: Optional[str] = None


class TrendsReportRequest(BaseModel):
    """Request for trends report."""
    days: int = 30
    repository: str = "unknown"
    storage_path: Optional[str] = None


@app.post("/api/trends/record")
async def record_quality_metrics(
    request: TrendsRecordRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """
    Record quality metrics for trend analysis.

    Metrics can include:
    - complexity: Code complexity score
    - maintainability: Maintainability index
    - coverage: Test coverage percentage
    - duplication: Code duplication percentage
    - issues: Number of issues
    - loc: Lines of code
    - technical_debt: Technical debt hours
    """
    try:
        # Create analyzer
        from pathlib import Path
        storage_path = Path(request.storage_path) if request.storage_path else None
        analyzer = TrendsAnalyzer(storage_path)

        # Convert string keys to MetricType
        metrics = {}
        for key, value in request.metrics.items():
            try:
                metric_type = MetricType(key)
                metrics[metric_type] = value
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid metric type: {key}"
                )

        # Record metrics
        analyzer.record_metrics(
            metrics=metrics,
            file_path=request.file_path,
            commit_hash=request.commit_hash
        )

        return {
            "status": "success",
            "message": f"Recorded {len(metrics)} metrics",
            "metrics": list(request.metrics.keys())
        }

    except Exception as e:
        get_logger().error(f"Failed to record metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/trends/analyze")
async def analyze_quality_trend(
    request: TrendsAnalysisRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """
    Analyze trend for a specific quality metric.

    Returns trend analysis including:
    - Direction (improving/stable/degrading)
    - Change percentage
    - Current and previous values
    - Statistics (min/max/average)
    - Prediction with confidence
    """
    try:
        # Create analyzer
        from pathlib import Path
        storage_path = Path(request.storage_path) if request.storage_path else None
        analyzer = TrendsAnalyzer(storage_path)

        # Convert string to MetricType
        try:
            metric_type = MetricType(request.metric_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid metric type: {request.metric_type}"
            )

        # Analyze trend
        trend = analyzer.analyze_trend(
            metric_type=metric_type,
            days=request.days,
            file_path=request.file_path
        )

        return {
            "metric_type": trend.metric_type.value,
            "direction": trend.direction.value,
            "change_percentage": trend.change_percentage,
            "current_value": trend.current_value,
            "previous_value": trend.previous_value,
            "average_value": trend.average_value,
            "min_value": trend.min_value,
            "max_value": trend.max_value,
            "data_points": trend.data_points,
            "prediction": trend.prediction,
            "confidence": trend.confidence
        }

    except Exception as e:
        get_logger().error(f"Failed to analyze trend: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/trends/degradations")
async def detect_quality_degradations(
    days: int = 7,
    threshold: float = 10.0,
    storage_path: Optional[str] = None,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """
    Detect quality degradations.

    Returns list of detected degradations with:
    - Metric type
    - Severity (low/medium/high/critical)
    - Change percentage
    - Old and new values
    - Description
    """
    try:
        # Create analyzer
        from pathlib import Path
        path = Path(storage_path) if storage_path else None
        analyzer = TrendsAnalyzer(path)

        # Detect degradations
        degradations = analyzer.detect_degradations(
            threshold_percentage=threshold,
            days=days
        )

        return {
            "count": len(degradations),
            "degradations": [
                {
                    "metric_type": d.metric_type.value,
                    "file_path": d.file_path,
                    "severity": d.severity,
                    "change_percentage": d.change_percentage,
                    "old_value": d.old_value,
                    "new_value": d.new_value,
                    "timestamp": d.timestamp,
                    "description": d.description
                }
                for d in degradations
            ]
        }

    except Exception as e:
        get_logger().error(f"Failed to detect degradations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/trends/report")
async def generate_trends_report(
    request: TrendsReportRequest,
    format: str = "json",
    current_user: User = Depends(get_current_user_or_api_key)
):
    """
    Generate comprehensive trends report.

    Supported formats:
    - json: Structured JSON report
    - text: Human-readable text report

    Returns:
    - Trends for all metrics
    - Detected degradations
    - Summary statistics
    - Overall health score
    """
    try:
        # Create analyzer
        from pathlib import Path
        storage_path = Path(request.storage_path) if request.storage_path else None
        analyzer = TrendsAnalyzer(storage_path)

        # Generate report
        report = analyzer.generate_report(
            days=request.days,
            repository=request.repository
        )

        if format == "text":
            # Generate text visualization
            text_report = visualize_trends_report(report)
            return {
                "format": "text",
                "content": text_report
            }
        else:
            # Return JSON
            return {
                "format": "json",
                "repository": report.repository,
                "start_date": report.start_date,
                "end_date": report.end_date,
                "generated_at": report.generated_at,
                "summary": report.summary,
                "trends": [
                    {
                        "metric_type": t.metric_type.value,
                        "direction": t.direction.value,
                        "change_percentage": t.change_percentage,
                        "current_value": t.current_value,
                        "previous_value": t.previous_value,
                        "average_value": t.average_value,
                        "min_value": t.min_value,
                        "max_value": t.max_value,
                        "data_points": t.data_points,
                        "prediction": t.prediction,
                        "confidence": t.confidence
                    }
                    for t in report.trends
                ],
                "degradations": [
                    {
                        "metric_type": d.metric_type.value,
                        "file_path": d.file_path,
                        "severity": d.severity,
                        "change_percentage": d.change_percentage,
                        "old_value": d.old_value,
                        "new_value": d.new_value,
                        "timestamp": d.timestamp,
                        "description": d.description
                    }
                    for d in report.degradations
                ]
            }

    except Exception as e:
        get_logger().error(f"Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Scheduler API
# ============================================================================

class ScheduleJobRequest(BaseModel):
    """Request to schedule a review job."""
    repository: str
    pr_number: Optional[int] = None
    branch: Optional[str] = None
    priority: str = "normal"
    trigger_type: str = "manual"
    config_overrides: Optional[Dict] = None


class ScheduleConfigRequest(BaseModel):
    """Request to add a schedule."""
    name: str
    cron_expression: str
    repository: str
    branches: Optional[List[str]] = None
    enabled: bool = True
    config_overrides: Optional[Dict] = None


class TriggerConfigRequest(BaseModel):
    """Request to add a trigger."""
    name: str
    trigger_type: str
    repository: str
    branch_filter: Optional[str] = None
    priority: str = "normal"
    config_overrides: Optional[Dict] = None


@app.post("/api/scheduler/jobs")
async def schedule_job(
    request: ScheduleJobRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Schedule a new review job."""
    try:
        scheduler = get_scheduler()

        job = scheduler.submit_job(
            repository=request.repository,
            trigger_type=TriggerType[request.trigger_type.upper()],
            priority=ReviewPriority[request.priority.upper()],
            pr_number=request.pr_number,
            branch=request.branch,
            metadata=request.config_overrides or {}
        )

        return {
            "job_id": job.job_id,
            "status": job.status.value,
            "priority": job.priority.value,
            "created_at": job.created_at.isoformat()
        }

    except Exception as e:
        get_logger().error(f"Failed to schedule job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/scheduler/jobs/{job_id}")
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get job details by ID."""
    try:
        scheduler = get_scheduler()
        job = scheduler.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        return {
            "job_id": job.job_id,
            "repository": job.repository,
            "pr_number": job.pr_number,
            "branch": job.branch,
            "status": job.status.value,
            "priority": job.priority.value,
            "trigger_type": job.trigger_type.value,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "error": job.error
        }

    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/scheduler/jobs")
async def list_jobs(
    status: Optional[str] = None,
    repository: Optional[str] = None,
    limit: int = Query(100, le=1000),
    current_user: User = Depends(get_current_user_or_api_key)
):
    """List jobs with optional filtering."""
    try:
        scheduler = get_scheduler()

        status_filter = ReviewStatus[status.upper()] if status else None
        jobs = scheduler.list_jobs(
            status=status_filter,
            repository=repository,
            limit=limit
        )

        return {
            "jobs": [
                {
                    "job_id": job.job_id,
                    "repository": job.repository,
                    "pr_number": job.pr_number,
                    "branch": job.branch,
                    "status": job.status.value,
                    "priority": job.priority.value,
                    "trigger_type": job.trigger_type.value,
                    "created_at": job.created_at.isoformat(),
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None
                }
                for job in jobs
            ],
            "total": len(jobs)
        }

    except Exception as e:
        get_logger().error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/scheduler/jobs/{job_id}")
async def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Cancel a pending or running job."""
    try:
        scheduler = get_scheduler()
        success = scheduler.cancel_job(job_id)

        if not success:
            raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")

        return {"message": "Job cancelled successfully"}

    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to cancel job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scheduler/schedules")
async def add_schedule(
    request: ScheduleConfigRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Add a new schedule."""
    try:
        scheduler = get_scheduler()

        schedule = scheduler.add_schedule(
            schedule_id=request.name,
            repository=request.repository,
            cron_expression=request.cron_expression,
            branches=request.branches,
            enabled=request.enabled,
            metadata=request.config_overrides or {}
        )

        return {
            "schedule_id": schedule.schedule_id,
            "message": "Schedule added successfully"
        }

    except Exception as e:
        get_logger().error(f"Failed to add schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/scheduler/schedules")
async def list_schedules(
    current_user: User = Depends(get_current_user_or_api_key)
):
    """List all schedules."""
    try:
        scheduler = get_scheduler()
        schedules = scheduler.list_schedules()

        return {
            "schedules": [
                {
                    "schedule_id": s.schedule_id,
                    "name": s.name,
                    "cron_expression": s.cron_expression,
                    "repository": s.repository,
                    "branches": s.branches,
                    "enabled": s.enabled,
                    "last_run": s.last_run.isoformat() if s.last_run else None,
                    "next_run": s.next_run.isoformat() if s.next_run else None
                }
                for s in schedules
            ]
        }

    except Exception as e:
        get_logger().error(f"Failed to list schedules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/scheduler/schedules/{schedule_id}")
async def remove_schedule(
    schedule_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Remove a schedule."""
    try:
        scheduler = get_scheduler()
        success = scheduler.remove_schedule(schedule_id)

        if not success:
            raise HTTPException(status_code=404, detail="Schedule not found")

        return {"message": "Schedule removed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to remove schedule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/scheduler/triggers")
async def add_trigger(
    request: TriggerConfigRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Add a new trigger."""
    try:
        scheduler = get_scheduler()

        filters = {}
        if request.branch_filter:
            filters["branches"] = [request.branch_filter]

        trigger = scheduler.add_trigger(
            trigger_id=request.name,
            repository=request.repository,
            trigger_type=TriggerType[request.trigger_type.upper()],
            priority=ReviewPriority[request.priority.upper()],
            filters=filters,
            metadata=request.config_overrides or {}
        )

        return {
            "trigger_id": trigger.trigger_id,
            "message": "Trigger added successfully"
        }

    except Exception as e:
        get_logger().error(f"Failed to add trigger: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/scheduler/triggers")
async def list_triggers(
    current_user: User = Depends(get_current_user_or_api_key)
):
    """List all triggers."""
    try:
        scheduler = get_scheduler()
        triggers = scheduler.list_triggers()

        return {
            "triggers": [
                {
                    "trigger_id": t.trigger_id,
                    "name": t.name,
                    "trigger_type": t.trigger_type.value,
                    "repository": t.repository,
                    "branch_filter": t.branch_filter,
                    "priority": t.priority.value,
                    "enabled": t.enabled
                }
                for t in triggers
            ]
        }

    except Exception as e:
        get_logger().error(f"Failed to list triggers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/scheduler/triggers/{trigger_id}")
async def remove_trigger(
    trigger_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Remove a trigger."""
    try:
        scheduler = get_scheduler()
        success = scheduler.remove_trigger(trigger_id)

        if not success:
            raise HTTPException(status_code=404, detail="Trigger not found")

        return {"message": "Trigger removed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to remove trigger: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Report Generation API
# ============================================================================

# Global report generator instance
_report_generator = None


def get_report_generator() -> ReportGenerator:
    """Get or create report generator instance."""
    global _report_generator
    if _report_generator is None:
        from pathlib import Path
        output_dir = Path.home() / ".pr_agent" / "reports"
        _report_generator = ReportGenerator(output_dir=output_dir)
    return _report_generator


@app.post("/api/reports/generate")
async def generate_report(
    repository: str,
    metrics: Dict[str, Any],
    trends: List[Dict[str, Any]] = [],
    issues: List[Dict[str, Any]] = [],
    recommendations: List[Dict[str, Any]] = [],
    format: str = "html",
    sections: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """
    Generate a quality report.

    Args:
        repository: Repository identifier
        metrics: Quality metrics dictionary
        trends: List of trend data points
        issues: List of issues found
        recommendations: List of recommendations
        format: Output format (json, markdown, html, pdf)
        sections: Sections to include (all if None)
        metadata: Additional metadata

    Returns:
        Report file path and download URL
    """
    try:
        generator = get_report_generator()

        # Convert format string to enum
        try:
            report_format = ReportFormat(format.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format: {format}. Must be one of: json, markdown, html, pdf"
            )

        # Convert sections strings to enums
        report_sections = None
        if sections:
            try:
                report_sections = [ReportSection(s.lower()) for s in sections]
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid section: {e}")

        # Convert dictionaries to dataclasses
        quality_metrics = QualityMetrics(**metrics)
        trend_data = [TrendData(**t) for t in trends]
        issue_list = [Issue(**i) for i in issues]
        recommendation_list = [Recommendation(**r) for r in recommendations]

        # Generate report
        output_path = generator.generate_report(
            repository=repository,
            metrics=quality_metrics,
            trends=trend_data,
            issues=issue_list,
            recommendations=recommendation_list,
            format=report_format,
            sections=report_sections,
            metadata=metadata
        )

        return {
            "file_path": str(output_path),
            "filename": output_path.name,
            "format": format,
            "download_url": f"/api/reports/download/{output_path.name}"
        }

    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports/download/{filename}")
async def download_report(
    filename: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Download a generated report."""
    try:
        generator = get_report_generator()
        file_path = generator.output_dir / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Report not found")

        # Determine media type based on extension
        media_types = {
            ".json": "application/json",
            ".md": "text/markdown",
            ".html": "text/html",
            ".pdf": "application/pdf"
        }
        media_type = media_types.get(file_path.suffix, "application/octet-stream")

        from fastapi.responses import FileResponse
        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            filename=filename
        )

    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to download report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports/list")
async def list_reports(
    current_user: User = Depends(get_current_user_or_api_key)
):
    """List all generated reports."""
    try:
        generator = get_report_generator()

        if not generator.output_dir.exists():
            return {"reports": []}

        reports = []
        for file_path in sorted(generator.output_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if file_path.is_file() and file_path.name.startswith("report_"):
                reports.append({
                    "filename": file_path.name,
                    "format": file_path.suffix[1:],  # Remove leading dot
                    "size": file_path.stat().st_size,
                    "created_at": file_path.stat().st_mtime,
                    "download_url": f"/api/reports/download/{file_path.name}"
                })

        return {"reports": reports}

    except Exception as e:
        get_logger().error(f"Failed to list reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/reports/{filename}")
async def delete_report(
    filename: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Delete a generated report."""
    try:
        generator = get_report_generator()
        file_path = generator.output_dir / filename

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Report not found")

        file_path.unlink()

        return {"message": "Report deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to delete report: {e}")
        raise HTTPException(status_code=500, detail=str(e))
# ============================================================================
# Rules Engine API
# ============================================================================

from pr_agent.rules import (
    RulesEngine,
    Rule,
    RuleSet,
    RuleSeverity,
    RuleCategory,
    get_engine
)

from pr_agent.review_templates import (
    TemplateManager,
    ReviewTemplate,
    TemplateCategory,
    CheckSeverity,
    CheckItem,
    get_template_manager
)


class RuleCheckRequest(BaseModel):
    """Request to check file against rules."""
    file_path: str
    content: str
    rule_ids: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None


class RuleCreateRequest(BaseModel):
    """Request to create a new rule."""
    rule_id: str
    name: str
    description: str
    severity: str
    category: str
    file_patterns: List[str]
    exclude_patterns: Optional[List[str]] = None
    enabled: bool = True
    metadata: Optional[Dict[str, Any]] = None


class RuleSetCreateRequest(BaseModel):
    """Request to create a rule set."""
    name: str
    description: str
    rule_ids: List[str]  # Will be converted to Rule objects
    enabled: bool = True


@app.post("/api/rules/check")
async def check_file_rules(
    request: RuleCheckRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """
    Check a file against rules.

    Returns list of violations found.
    """
    try:
        engine = get_engine()

        violations = engine.check_file(
            file_path=request.file_path,
            content=request.content,
            context=request.context,
            rule_ids=request.rule_ids
        )

        return {
            "file_path": request.file_path,
            "violations": [
                {
                    "rule_id": v.rule_id,
                    "rule_name": v.rule_name,
                    "severity": v.severity.value,
                    "category": v.category.value,
                    "message": v.message,
                    "line_number": v.line_number,
                    "code_snippet": v.code_snippet,
                    "suggestion": v.suggestion
                }
                for v in violations
            ],
            "total_violations": len(violations)
        }

    except Exception as e:
        get_logger().error(f"Failed to check rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rules/check-multiple")
async def check_multiple_files(
    files: Dict[str, str],
    rule_ids: Optional[List[str]] = None,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """
    Check multiple files against rules.

    Args:
        files: Dict mapping file paths to content
        rule_ids: Optional list of specific rules to check
    """
    try:
        engine = get_engine()

        results = engine.check_files(
            files=files,
            rule_ids=rule_ids
        )

        return {
            "results": {
                file_path: [
                    {
                        "rule_id": v.rule_id,
                        "rule_name": v.rule_name,
                        "severity": v.severity.value,
                        "category": v.category.value,
                        "message": v.message,
                        "line_number": v.line_number,
                        "code_snippet": v.code_snippet,
                        "suggestion": v.suggestion
                    }
                    for v in violations
                ]
                for file_path, violations in results.items()
            },
            "total_files": len(results),
            "total_violations": sum(len(v) for v in results.values())
        }

    except Exception as e:
        get_logger().error(f"Failed to check multiple files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rules")
async def list_rules(
    enabled_only: bool = False,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """List all registered rules."""
    try:
        engine = get_engine()
        rules = engine.list_rules(enabled_only=enabled_only)

        # Filter by category if specified
        if category:
            try:
                cat = RuleCategory(category)
                rules = [r for r in rules if r.category == cat]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid category: {category}")

        return {
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "name": r.name,
                    "description": r.description,
                    "severity": r.severity.value,
                    "category": r.category.value,
                    "file_patterns": r.file_patterns,
                    "exclude_patterns": r.exclude_patterns,
                    "enabled": r.enabled,
                    "metadata": r.metadata
                }
                for r in rules
            ],
            "total": len(rules)
        }

    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to list rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rules")
async def create_rule(
    request: RuleCreateRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Create a new custom rule."""
    try:
        engine = get_engine()

        # Parse severity and category
        try:
            severity = RuleSeverity(request.severity)
            category = RuleCategory(request.category)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Create rule
        rule = Rule(
            rule_id=request.rule_id,
            name=request.name,
            description=request.description,
            severity=severity,
            category=category,
            file_patterns=request.file_patterns,
            exclude_patterns=request.exclude_patterns or [],
            enabled=request.enabled,
            metadata=request.metadata
        )

        engine.register_rule(rule)

        return {
            "message": "Rule created successfully",
            "rule_id": rule.rule_id
        }

    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to create rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Delete a rule."""
    try:
        engine = get_engine()
        engine.unregister_rule(rule_id)

        return {"message": "Rule deleted successfully"}

    except Exception as e:
        get_logger().error(f"Failed to delete rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rules/sets")
async def list_rule_sets(
    current_user: User = Depends(get_current_user_or_api_key)
):
    """List all rule sets."""
    try:
        engine = get_engine()

        return {
            "rule_sets": [
                {
                    "name": name,
                    "description": rs.description,
                    "rule_ids": [r.rule_id for r in rs.rules],
                    "enabled": rs.enabled
                }
                for name, rs in engine.rule_sets.items()
            ]
        }

    except Exception as e:
        get_logger().error(f"Failed to list rule sets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rules/sets")
async def create_rule_set(
    request: RuleSetCreateRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Create a new rule set."""
    try:
        engine = get_engine()

        # Convert rule IDs to Rule objects
        rules = []
        for rule_id in request.rule_ids:
            if rule_id not in engine.rules:
                raise HTTPException(
                    status_code=400,
                    detail=f"Rule not found: {rule_id}"
                )
            rules.append(engine.rules[rule_id])

        rule_set = RuleSet(
            name=request.name,
            description=request.description,
            rules=rules,
            enabled=request.enabled
        )

        engine.register_rule_set(rule_set)

        return {
            "message": "Rule set created successfully",
            "name": rule_set.name
        }

    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to create rule set: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rules/export")
async def export_rules(
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Export all rules to JSON."""
    try:
        engine = get_engine()
        rules_data = engine.export_rules()

        return rules_data

    except Exception as e:
        get_logger().error(f"Failed to export rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rules/import")
async def import_rules(
    rules_data: Dict[str, Any],
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Import rules from JSON."""
    try:
        engine = get_engine()
        engine.import_rules(rules_data)

        return {"message": "Rules imported successfully"}

    except Exception as e:
        get_logger().error(f"Failed to import rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Review Templates API
# ============================================================================

@app.get("/api/review-templates")
async def list_review_templates(
    category: Optional[str] = None,
    enabled_only: bool = False,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """List all review templates."""
    try:
        manager = get_template_manager()

        cat = TemplateCategory(category) if category else None
        templates = manager.list_templates(category=cat, enabled_only=enabled_only)

        return {
            "templates": [t.to_dict() for t in templates],
            "count": len(templates)
        }

    except Exception as e:
        get_logger().error(f"Failed to list templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/review-templates/{template_id}")
async def get_review_template(
    template_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get a specific review template."""
    try:
        manager = get_template_manager()
        template = manager.get_template(template_id)

        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        return template.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/review-templates")
async def create_review_template(
    template_data: Dict[str, Any],
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Create a new review template."""
    try:
        manager = get_template_manager()

        # Parse check items
        check_items = []
        for item_data in template_data.get("check_items", []):
            check_items.append(CheckItem(
                check_id=item_data["check_id"],
                title=item_data["title"],
                description=item_data["description"],
                severity=CheckSeverity(item_data["severity"]),
                required=item_data.get("required", True),
                guidance=item_data.get("guidance", ""),
                examples=item_data.get("examples", []),
                metadata=item_data.get("metadata", {})
            ))

        # Create template
        template = ReviewTemplate(
            template_id=template_data["template_id"],
            name=template_data["name"],
            description=template_data["description"],
            category=TemplateCategory(template_data["category"]),
            check_items=check_items,
            enabled=template_data.get("enabled", True),
            metadata=template_data.get("metadata", {})
        )

        manager.register_template(template)

        return {
            "message": "Template created successfully",
            "template_id": template.template_id
        }

    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to create template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/review-templates/{template_id}")
async def delete_review_template(
    template_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Delete a review template."""
    try:
        manager = get_template_manager()

        if not manager.get_template(template_id):
            raise HTTPException(status_code=404, detail="Template not found")

        success = manager.unregister_template(template_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete template")

        return {"message": "Template deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to delete template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/review-templates/{template_id}/apply")
async def apply_review_template(
    template_id: str,
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Apply a review template to a file."""
    try:
        manager = get_template_manager()

        file_path = request.get("file_path")
        content = request.get("content")
        context = request.get("context", {})

        if not file_path or not content:
            raise HTTPException(
                status_code=400,
                detail="file_path and content are required"
            )

        result = manager.apply_template(
            template_id=template_id,
            file_path=file_path,
            content=content,
            context=context
        )

        return {
            "template_id": result.template_id,
            "template_name": result.template_name,
            "file_path": result.file_path,
            "summary": result.get_summary(),
            "findings": result.findings
        }

    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to apply template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/review-templates/export")
async def export_review_templates(
    template_ids: Optional[str] = None,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Export review templates to JSON."""
    try:
        manager = get_template_manager()

        ids = template_ids.split(",") if template_ids else None
        export_data = manager.export_templates(template_ids=ids)

        return export_data

    except Exception as e:
        get_logger().error(f"Failed to export templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/review-templates/import")
async def import_review_templates(
    import_data: Dict[str, Any],
    overwrite: bool = False,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Import review templates from JSON."""
    try:
        manager = get_template_manager()
        manager.import_templates(import_data, overwrite=overwrite)

        return {
            "message": "Templates imported successfully",
            "count": len(import_data.get("templates", []))
        }

    except Exception as e:
        get_logger().error(f"Failed to import templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Assignment System API
# ============================================================================

from pr_agent.assignment import (
    AssignmentEngine,
    Reviewer,
    Assignment,
    AssignmentStrategy,
    ReviewerStatus,
    get_assignment_engine
)


@app.post("/api/reviewers")
async def create_reviewer(
    reviewer: Dict[str, Any],
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Register a new reviewer."""
    try:
        engine = get_assignment_engine()

        reviewer_obj = Reviewer(
            reviewer_id=reviewer["reviewer_id"],
            name=reviewer["name"],
            email=reviewer["email"],
            skills=reviewer.get("skills", []),
            file_patterns=reviewer.get("file_patterns", []),
            max_reviews=reviewer.get("max_reviews", 5),
            priority=reviewer.get("priority", 1),
            metadata=reviewer.get("metadata", {})
        )

        engine.register_reviewer(reviewer_obj)

        return {
            "message": "Reviewer registered successfully",
            "reviewer": reviewer_obj.to_dict()
        }

    except Exception as e:
        get_logger().error(f"Failed to register reviewer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reviewers")
async def list_reviewers(
    status: Optional[str] = None,
    available_only: bool = False,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """List all reviewers."""
    try:
        engine = get_assignment_engine()

        reviewer_status = ReviewerStatus(status) if status else None
        reviewers = engine.list_reviewers(
            status=reviewer_status,
            available_only=available_only
        )

        return {
            "reviewers": [r.to_dict() for r in reviewers],
            "count": len(reviewers)
        }

    except Exception as e:
        get_logger().error(f"Failed to list reviewers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reviewers/{reviewer_id}")
async def get_reviewer(
    reviewer_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get a specific reviewer."""
    try:
        engine = get_assignment_engine()
        reviewer = engine.get_reviewer(reviewer_id)

        if not reviewer:
            raise HTTPException(status_code=404, detail="Reviewer not found")

        return reviewer.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get reviewer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/reviewers/{reviewer_id}")
async def delete_reviewer(
    reviewer_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Unregister a reviewer."""
    try:
        engine = get_assignment_engine()

        if not engine.unregister_reviewer(reviewer_id):
            raise HTTPException(status_code=404, detail="Reviewer not found")

        return {"message": "Reviewer unregistered successfully"}

    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to unregister reviewer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/reviewers/{reviewer_id}/status")
async def update_reviewer_status(
    reviewer_id: str,
    status: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Update reviewer status."""
    try:
        engine = get_assignment_engine()
        reviewer_status = ReviewerStatus(status)

        if not engine.update_reviewer_status(reviewer_id, reviewer_status):
            raise HTTPException(status_code=404, detail="Reviewer not found")

        return {"message": "Reviewer status updated successfully"}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid status: {e}")
    except Exception as e:
        get_logger().error(f"Failed to update reviewer status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/assignments")
async def assign_reviewers(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Assign reviewers to a pull request."""
    try:
        engine = get_assignment_engine()

        strategy = AssignmentStrategy(request.get("strategy", "load_balanced"))

        assignments = engine.assign_reviewers(
            pull_request_id=request["pull_request_id"],
            repository=request["repository"],
            files=request["files"],
            num_reviewers=request.get("num_reviewers", 2),
            strategy=strategy,
            required_skills=request.get("required_skills")
        )

        return {
            "message": "Reviewers assigned successfully",
            "assignments": [a.to_dict() for a in assignments],
            "count": len(assignments)
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        get_logger().error(f"Failed to assign reviewers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/assignments")
async def list_assignments(
    reviewer_id: Optional[str] = None,
    repository: Optional[str] = None,
    completed: Optional[bool] = None,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """List assignments."""
    try:
        engine = get_assignment_engine()

        assignments = engine.list_assignments(
            reviewer_id=reviewer_id,
            repository=repository,
            completed=completed
        )

        return {
            "assignments": [a.to_dict() for a in assignments],
            "count": len(assignments)
        }

    except Exception as e:
        get_logger().error(f"Failed to list assignments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/assignments/{assignment_id}")
async def get_assignment(
    assignment_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get a specific assignment."""
    try:
        engine = get_assignment_engine()
        assignment = engine.get_assignment(assignment_id)

        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        return assignment.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get assignment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/assignments/{assignment_id}/complete")
async def complete_assignment(
    assignment_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Mark an assignment as completed."""
    try:
        engine = get_assignment_engine()

        if not engine.complete_assignment(assignment_id):
            raise HTTPException(status_code=404, detail="Assignment not found")

        return {"message": "Assignment completed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to complete assignment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reviewers/{reviewer_id}/stats")
async def get_reviewer_stats(
    reviewer_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get statistics for a reviewer."""
    try:
        engine = get_assignment_engine()
        stats = engine.get_reviewer_stats(reviewer_id)

        if not stats:
            raise HTTPException(status_code=404, detail="Reviewer not found")

        return stats

    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get reviewer stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Notification System API
# ============================================================================

from pr_agent.notifications import (
    NotificationSystem,
    NotificationChannel,
    NotificationEvent,
    NotificationPriority,
    NotificationTemplate,
    NotificationPreference,
    get_notification_system
)
from pr_agent.dashboard import (
    DashboardSystem,
    Dashboard,
    DashboardWidget,
    TimeRange
)
from pr_agent.sla import (
    SLAManager,
    SLAPolicy,
    SLATarget,
    SLAPriority,
    SLAMetric,
    get_sla_manager
)
from pr_agent.quality_scoring import (
    QualityScorer,
    ReviewScore,
    QualityMetric
)
from pr_agent.knowledge import (
    KnowledgeBase,
    KnowledgeType,
    Severity as KnowledgeSeverity
)
from pr_agent.workflow_engine import (
    WorkflowEngine,
    StepType,
    WorkflowStatus,
    ConditionOperator,
    get_workflow_engine
)
from pr_agent.bot import (
    ReviewerBot,
    BotConfig,
    BotCapability,
    CommentType,
    ReviewMode
)

from pr_agent.review_collaboration import (
    CollaborationSystem,
    ParticipantRole,
    CommentType as CollabCommentType,
    CommentStatus,
    TaskStatus,
    DecisionStatus,
    get_collaboration_system,
)

from pr_agent.metrics import (
    MetricsCollector,
    ReviewMetrics,
    TimeRange,
    get_metrics_collector,
)

from pr_agent.report_generator import (
    ReportGenerator,
    ReportType,
    ReportFormat,
    ReportConfig,
)


@app.post("/api/notifications/templates")
async def create_notification_template(
    template: Dict[str, Any],
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Register a notification template."""
    try:
        system = get_notification_system()

        template_obj = NotificationTemplate(
            template_id=template["template_id"],
            event=NotificationEvent(template["event"]),
            channel=NotificationChannel(template["channel"]),
            subject_template=template["subject_template"],
            body_template=template["body_template"],
            metadata=template.get("metadata", {})
        )

        system.register_template(template_obj)

        return {"message": "Template registered successfully"}

    except Exception as e:
        get_logger().error(f"Failed to register template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notifications/preferences")
async def set_notification_preference(
    preference: Dict[str, Any],
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Set user notification preferences."""
    try:
        system = get_notification_system()

        pref_obj = NotificationPreference(
            user_id=preference["user_id"],
            email=preference.get("email"),
            slack_id=preference.get("slack_id"),
            dingtalk_id=preference.get("dingtalk_id"),
            wecom_id=preference.get("wecom_id"),
            enabled_channels=[NotificationChannel(c) for c in preference.get("enabled_channels", [])],
            enabled_events=[NotificationEvent(e) for e in preference.get("enabled_events", [])],
            quiet_hours_start=preference.get("quiet_hours_start"),
            quiet_hours_end=preference.get("quiet_hours_end"),
            metadata=preference.get("metadata", {})
        )

        system.set_preference(pref_obj)

        return {"message": "Preferences saved successfully"}

    except Exception as e:
        get_logger().error(f"Failed to set preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notifications/preferences/{user_id}")
async def get_notification_preference(
    user_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get user notification preferences."""
    try:
        system = get_notification_system()
        pref = system.get_preference(user_id)

        if not pref:
            raise HTTPException(status_code=404, detail="Preferences not found")

        return {
            "user_id": pref.user_id,
            "email": pref.email,
            "slack_id": pref.slack_id,
            "dingtalk_id": pref.dingtalk_id,
            "wecom_id": pref.wecom_id,
            "enabled_channels": [c.value for c in pref.enabled_channels],
            "enabled_events": [e.value for e in pref.enabled_events],
            "quiet_hours_start": pref.quiet_hours_start,
            "quiet_hours_end": pref.quiet_hours_end,
            "metadata": pref.metadata
        }

    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notifications/send")
async def send_notification(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Send notifications to recipients."""
    try:
        system = get_notification_system()

        event = NotificationEvent(request["event"])
        recipients = request["recipients"]
        context = request["context"]
        priority = NotificationPriority(request.get("priority", "normal"))
        channels = [NotificationChannel(c) for c in request.get("channels", [])] if request.get("channels") else None

        notifications = system.notify(
            event=event,
            recipients=recipients,
            context=context,
            priority=priority,
            channels=channels
        )

        return {
            "message": "Notifications sent",
            "count": len(notifications),
            "notifications": [n.to_dict() for n in notifications]
        }

    except Exception as e:
        get_logger().error(f"Failed to send notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notifications/history")
async def get_notification_history(
    user_id: Optional[str] = None,
    event: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get notification history."""
    try:
        system = get_notification_system()

        event_enum = NotificationEvent(event) if event else None
        history = system.get_notification_history(
            user_id=user_id,
            event=event_enum,
            limit=limit
        )

        return {
            "notifications": [n.to_dict() for n in history],
            "count": len(history)
        }

    except Exception as e:
        get_logger().error(f"Failed to get notification history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Dashboard API
# ============================================================================

# Global dashboard system instance
_dashboard_system = None


def get_dashboard_system() -> DashboardSystem:
    """Get or create dashboard system instance."""
    global _dashboard_system
    if _dashboard_system is None:
        _dashboard_system = DashboardSystem()
    return _dashboard_system


@app.post("/api/dashboards")
async def create_dashboard(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Create a new dashboard."""
    try:
        system = get_dashboard_system()
        dashboard = system.create_dashboard(
            dashboard_id=request["dashboard_id"],
            name=request["name"],
            description=request.get("description", ""),
            time_range=TimeRange(request.get("time_range", "week")),
            auto_refresh=request.get("auto_refresh", True),
            refresh_interval_seconds=request.get("refresh_interval_seconds", 300),
            metadata=request.get("metadata")
        )
        return dashboard.to_dict()
    except Exception as e:
        get_logger().error(f"Failed to create dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboards")
async def list_dashboards(
    current_user: User = Depends(get_current_user_or_api_key)
):
    """List all dashboards."""
    try:
        system = get_dashboard_system()
        dashboards = system.list_dashboards()
        return {
            "dashboards": [d.to_dict() for d in dashboards],
            "count": len(dashboards)
        }
    except Exception as e:
        get_logger().error(f"Failed to list dashboards: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboards/{dashboard_id}")
async def get_dashboard(
    dashboard_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get dashboard by ID."""
    try:
        system = get_dashboard_system()
        dashboard = system.get_dashboard(dashboard_id)
        if not dashboard:
            raise HTTPException(status_code=404, detail="Dashboard not found")
        return dashboard.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/dashboards/{dashboard_id}")
async def delete_dashboard(
    dashboard_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Delete a dashboard."""
    try:
        system = get_dashboard_system()
        system.delete_dashboard(dashboard_id)
        return {"message": "Dashboard deleted successfully"}
    except Exception as e:
        get_logger().error(f"Failed to delete dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dashboards/{dashboard_id}/widgets")
async def add_widget(
    dashboard_id: str,
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Add widget to dashboard."""
    try:
        system = get_dashboard_system()

        # Parse position and size
        position_data = request.get("position", {"x": 0, "y": 0})
        position = (position_data.get("x", 0), position_data.get("y", 0))

        size_data = request.get("size", {"w": 4, "h": 4})
        size = (size_data.get("w", 4), size_data.get("h", 4))

        widget = system.add_widget(
            dashboard_id=dashboard_id,
            widget_id=request["widget_id"],
            widget_type=request["widget_type"],
            title=request["title"],
            position=position,
            size=size,
            config=request.get("config", {}),
            metadata=request.get("metadata")
        )
        return widget.to_dict()
    except Exception as e:
        get_logger().error(f"Failed to add widget: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/dashboards/{dashboard_id}/widgets/{widget_id}")
async def remove_widget(
    dashboard_id: str,
    widget_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Remove widget from dashboard."""
    try:
        system = get_dashboard_system()
        system.remove_widget(dashboard_id, widget_id)
        return {"message": "Widget removed successfully"}
    except Exception as e:
        get_logger().error(f"Failed to remove widget: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/dashboards/reviews")
async def record_review(
    review_data: Dict[str, Any],
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Record review data for analytics."""
    try:
        system = get_dashboard_system()
        system.record_review(review_data)
        return {"message": "Review recorded successfully"}
    except Exception as e:
        get_logger().error(f"Failed to record review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboards/stats/reviews")
async def get_review_stats(
    time_range: str = "week",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get review statistics."""
    try:
        system = get_dashboard_system()

        # Parse time range
        if time_range in ["day", "week", "month", "year"]:
            time_range_enum = TimeRange(time_range)
            stats = system.get_review_stats(time_range=time_range_enum)
        elif start_date and end_date:
            stats = system.get_review_stats(
                start_date=start_date,
                end_date=end_date
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Either time_range or start_date/end_date must be provided"
            )

        return stats.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get review stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboards/stats/workload")
async def get_reviewer_workload(
    reviewer_id: Optional[str] = None,
    time_range: str = "week",
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get reviewer workload statistics."""
    try:
        system = get_dashboard_system()
        time_range_enum = TimeRange(time_range)
        workload = system.get_reviewer_workload(
            reviewer_id=reviewer_id,
            time_range=time_range_enum
        )

        if reviewer_id:
            return workload.to_dict() if workload else {}
        else:
            return {
                "workloads": [w.to_dict() for w in workload],
                "count": len(workload)
            }
    except Exception as e:
        get_logger().error(f"Failed to get reviewer workload: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboards/stats/trends")
async def get_time_trends(
    metric: str = "reviews",
    time_range: str = "week",
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get time-based trends."""
    try:
        system = get_dashboard_system()
        time_range_enum = TimeRange(time_range)
        trends = system.get_time_trends(
            metric=metric,
            time_range=time_range_enum
        )
        return {
            "trends": [t.to_dict() for t in trends],
            "count": len(trends)
        }
    except Exception as e:
        get_logger().error(f"Failed to get time trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboards/stats/quality")
async def get_quality_metrics(
    time_range: str = "week",
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get code quality metrics."""
    try:
        system = get_dashboard_system()
        time_range_enum = TimeRange(time_range)
        metrics = system.get_quality_metrics(time_range=time_range_enum)
        return metrics.to_dict()
    except Exception as e:
        get_logger().error(f"Failed to get quality metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboards/stats/efficiency")
async def get_team_efficiency(
    time_range: str = "week",
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get team efficiency metrics."""
    try:
        system = get_dashboard_system()
        time_range_enum = TimeRange(time_range)
        efficiency = system.get_team_efficiency(time_range=time_range_enum)
        return efficiency.to_dict()
    except Exception as e:
        get_logger().error(f"Failed to get team efficiency: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboards/export")
async def export_dashboard_data(
    format: str = "json",
    time_range: str = "week",
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Export dashboard data."""
    try:
        system = get_dashboard_system()
        time_range_enum = TimeRange(time_range)
        data = system.export_data(
            format=format,
            time_range=time_range_enum
        )

        if format == "json":
            return data
        elif format == "csv":
            return Response(
                content=data,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=dashboard_data.csv"}
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported format")
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to export dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SLA Management API
# ============================================================================

@app.post("/api/sla/policies")
async def create_sla_policy(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Create a new SLA policy."""
    try:
        manager = get_sla_manager()

        # Parse targets
        targets = []
        for t_data in request.get("targets", []):
            target = SLATarget(
                metric=SLAMetric(t_data["metric"]),
                target_hours=t_data["target_hours"],
                warning_threshold_percent=t_data.get("warning_threshold_percent", 80.0),
                metadata=t_data.get("metadata", {})
            )
            targets.append(target)

        policy = manager.create_policy(
            policy_id=request["policy_id"],
            name=request["name"],
            description=request["description"],
            priority=SLAPriority(request["priority"]),
            targets=targets,
            applies_to=request.get("applies_to", {}),
            escalation_enabled=request.get("escalation_enabled", True),
            escalation_targets=request.get("escalation_targets", []),
            notification_enabled=request.get("notification_enabled", True),
            metadata=request.get("metadata", {})
        )

        return policy.to_dict()
    except Exception as e:
        get_logger().error(f"Failed to create SLA policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sla/policies")
async def list_sla_policies(
    enabled_only: bool = False,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """List all SLA policies."""
    try:
        manager = get_sla_manager()
        policies = manager.list_policies(enabled_only=enabled_only)
        return {
            "policies": [p.to_dict() for p in policies],
            "count": len(policies)
        }
    except Exception as e:
        get_logger().error(f"Failed to list SLA policies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sla/policies/{policy_id}")
async def get_sla_policy(
    policy_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get SLA policy by ID."""
    try:
        manager = get_sla_manager()
        policy = manager.get_policy(policy_id)
        if not policy:
            raise HTTPException(status_code=404, detail="Policy not found")
        return policy.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get SLA policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/sla/policies/{policy_id}")
async def update_sla_policy(
    policy_id: str,
    updates: Dict[str, Any],
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Update an SLA policy."""
    try:
        manager = get_sla_manager()
        policy = manager.update_policy(policy_id, **updates)
        return policy.to_dict()
    except Exception as e:
        get_logger().error(f"Failed to update SLA policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/sla/policies/{policy_id}")
async def delete_sla_policy(
    policy_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Delete an SLA policy."""
    try:
        manager = get_sla_manager()
        manager.delete_policy(policy_id)
        return {"message": "Policy deleted successfully"}
    except Exception as e:
        get_logger().error(f"Failed to delete SLA policy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sla/tracking/start")
async def start_sla_tracking(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Start tracking a review for SLA compliance."""
    try:
        manager = get_sla_manager()
        manager.start_tracking(
            review_id=request["review_id"],
            repository=request["repository"],
            priority=SLAPriority(request.get("priority", "normal")),
            metadata=request.get("metadata", {})
        )
        return {"message": "Tracking started successfully"}
    except Exception as e:
        get_logger().error(f"Failed to start SLA tracking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sla/tracking/event")
async def record_sla_event(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Record a review event for SLA tracking."""
    try:
        manager = get_sla_manager()
        timestamp = None
        if "timestamp" in request:
            timestamp = datetime.fromisoformat(request["timestamp"])

        manager.record_event(
            review_id=request["review_id"],
            event_type=request["event_type"],
            timestamp=timestamp
        )
        return {"message": "Event recorded successfully"}
    except Exception as e:
        get_logger().error(f"Failed to record SLA event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sla/compliance/{review_id}")
async def check_sla_compliance(
    review_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Check SLA compliance for a review."""
    try:
        manager = get_sla_manager()
        compliance = manager.check_compliance(review_id)
        if not compliance:
            raise HTTPException(status_code=404, detail="No applicable SLA policy found")
        return compliance.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to check SLA compliance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sla/violations")
async def get_sla_violations(
    review_id: Optional[str] = None,
    policy_id: Optional[str] = None,
    resolved: Optional[bool] = None,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get SLA violations with optional filters."""
    try:
        manager = get_sla_manager()
        violations = manager.get_violations(
            review_id=review_id,
            policy_id=policy_id,
            resolved=resolved
        )
        return {
            "violations": [v.to_dict() for v in violations],
            "count": len(violations)
        }
    except Exception as e:
        get_logger().error(f"Failed to get SLA violations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sla/violations/{violation_id}/resolve")
async def resolve_sla_violation(
    violation_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Mark an SLA violation as resolved."""
    try:
        manager = get_sla_manager()
        manager.resolve_violation(violation_id)
        return {"message": "Violation resolved successfully"}
    except Exception as e:
        get_logger().error(f"Failed to resolve SLA violation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sla/statistics")
async def get_sla_statistics(
    policy_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get SLA statistics."""
    try:
        manager = get_sla_manager()

        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None

        stats = manager.get_statistics(
            policy_id=policy_id,
            start_date=start,
            end_date=end
        )

        return {
            "statistics": [s.to_dict() for s in stats],
            "count": len(stats)
        }
    except Exception as e:
        get_logger().error(f"Failed to get SLA statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Quality Scoring API endpoints
@app.post("/api/quality/score")
async def calculate_quality_score(
    review_id: str,
    pr_id: str,
    reviewer_id: str,
    metrics: Dict[str, Any],
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Calculate quality score for a review."""
    try:
        scorer = QualityScorer()
        score = scorer.calculate_score(
            review_id=review_id,
            pr_id=pr_id,
            reviewer_id=reviewer_id,
            metrics=metrics
        )
        return score.to_dict()
    except Exception as e:
        get_logger().error(f"Failed to calculate quality score: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/quality/reviewer-rating/{reviewer_id}")
async def get_reviewer_rating(
    reviewer_id: str,
    days: int = 30,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get reviewer rating and statistics."""
    try:
        scorer = QualityScorer()
        rating = scorer.get_reviewer_rating(reviewer_id, days=days)
        return rating
    except Exception as e:
        get_logger().error(f"Failed to get reviewer rating: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/quality/trends")
async def get_quality_trends(
    reviewer_id: Optional[str] = None,
    days: int = 90,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get quality trends over time."""
    try:
        scorer = QualityScorer()
        trends = scorer.get_trends(reviewer_id=reviewer_id, days=days)
        return {"trends": trends}
    except Exception as e:
        get_logger().error(f"Failed to get quality trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/quality/suggestions/{reviewer_id}")
async def get_improvement_suggestions(
    reviewer_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get improvement suggestions for a reviewer."""
    try:
        scorer = QualityScorer()
        suggestions = scorer.get_improvement_suggestions(reviewer_id)
        return {"suggestions": suggestions}
    except Exception as e:
        get_logger().error(f"Failed to get improvement suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Knowledge Base API
@app.post("/api/knowledge/entries")
async def create_knowledge_entry(
    entry: dict,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Create a new knowledge entry."""
    try:
        kb = KnowledgeBase()
        entry_id = kb.add_entry(
            title=entry["title"],
            content=entry["content"],
            entry_type=KnowledgeType(entry["type"]),
            category=entry["category"],
            tags=entry.get("tags", []),
            severity=KnowledgeSeverity(entry.get("severity", "info")),
            code_example=entry.get("code_example"),
            references=entry.get("references", [])
        )
        return {"entry_id": entry_id}
    except Exception as e:
        get_logger().error(f"Failed to create knowledge entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/knowledge/entries/{entry_id}")
async def get_knowledge_entry(
    entry_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get a knowledge entry by ID."""
    try:
        kb = KnowledgeBase()
        entry = kb.get_entry(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        return entry.dict()
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get knowledge entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/knowledge/entries/{entry_id}")
async def update_knowledge_entry(
    entry_id: str,
    updates: dict,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Update a knowledge entry."""
    try:
        kb = KnowledgeBase()
        kb.update_entry(entry_id, **updates)
        return {"status": "updated"}
    except Exception as e:
        get_logger().error(f"Failed to update knowledge entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/knowledge/entries/{entry_id}")
async def delete_knowledge_entry(
    entry_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Delete a knowledge entry."""
    try:
        kb = KnowledgeBase()
        kb.delete_entry(entry_id)
        return {"status": "deleted"}
    except Exception as e:
        get_logger().error(f"Failed to delete knowledge entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/knowledge/search")
async def search_knowledge(
    query: str,
    tags: Optional[str] = None,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Search knowledge entries."""
    try:
        kb = KnowledgeBase()
        tag_list = tags.split(",") if tags else []
        entries = kb.search(query, tags=tag_list)
        return {"entries": [e.dict() for e in entries]}
    except Exception as e:
        get_logger().error(f"Failed to search knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/knowledge/categories/{category}")
async def get_knowledge_by_category(
    category: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get knowledge entries by category."""
    try:
        kb = KnowledgeBase()
        entries = kb.get_by_category(category)
        return {"entries": [e.dict() for e in entries]}
    except Exception as e:
        get_logger().error(f"Failed to get knowledge by category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/knowledge/tags/{tag}")
async def get_knowledge_by_tag(
    tag: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get knowledge entries by tag."""
    try:
        kb = KnowledgeBase()
        entries = kb.get_by_tag(tag)
        return {"entries": [e.dict() for e in entries]}
    except Exception as e:
        get_logger().error(f"Failed to get knowledge by tag: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/knowledge/popular")
async def get_popular_knowledge(
    limit: int = 10,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get popular knowledge entries."""
    try:
        kb = KnowledgeBase()
        entries = kb.get_popular(limit=limit)
        return {"entries": [e.dict() for e in entries]}
    except Exception as e:
        get_logger().error(f"Failed to get popular knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/knowledge/stats")
async def get_knowledge_stats(
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get knowledge base statistics."""
    try:
        kb = KnowledgeBase()
        stats = kb.get_stats()
        return stats
    except Exception as e:
        get_logger().error(f"Failed to get knowledge stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/knowledge/import")
async def import_knowledge(
    data: dict,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Import knowledge entries from JSON."""
    try:
        kb = KnowledgeBase()
        count = kb.import_from_json(data)
        return {"imported": count}
    except Exception as e:
        get_logger().error(f"Failed to import knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/knowledge/export")
async def export_knowledge(
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Export all knowledge entries to JSON."""
    try:
        kb = KnowledgeBase()
        data = kb.export_to_json()
        return data
    except Exception as e:
        get_logger().error(f"Failed to export knowledge: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Workflow Engine API
@app.post("/api/workflows")
async def create_workflow(
    workflow: dict,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Create a new workflow."""
    try:
        engine = get_workflow_engine()
        wf = engine.create_workflow(
            name=workflow["name"],
            description=workflow["description"],
            steps=workflow["steps"],
            metadata=workflow.get("metadata")
        )
        return {"workflow_id": wf.workflow_id}
    except Exception as e:
        get_logger().error(f"Failed to create workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflows/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get a workflow by ID."""
    try:
        engine = get_workflow_engine()
        workflow = engine.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="Workflow not found")

        return {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "description": workflow.description,
            "status": workflow.status.value,
            "created_at": workflow.created_at.isoformat(),
            "steps": [
                {
                    "step_id": step.step_id,
                    "name": step.name,
                    "type": step.type.value,
                    "config": step.config,
                    "depends_on": step.depends_on,
                    "parallel": step.parallel
                }
                for step in workflow.steps
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflows")
async def list_workflows(
    current_user: User = Depends(get_current_user_or_api_key)
):
    """List all workflows."""
    try:
        engine = get_workflow_engine()
        workflows = engine.list_workflows()
        return {
            "workflows": [
                {
                    "workflow_id": wf.workflow_id,
                    "name": wf.name,
                    "description": wf.description,
                    "status": wf.status.value,
                    "created_at": wf.created_at.isoformat()
                }
                for wf in workflows
            ]
        }
    except Exception as e:
        get_logger().error(f"Failed to list workflows: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/workflows/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Delete a workflow."""
    try:
        engine = get_workflow_engine()
        result = engine.delete_workflow(workflow_id)
        if not result:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to delete workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workflows/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    context: Optional[dict] = None,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Execute a workflow."""
    try:
        engine = get_workflow_engine()
        execution = engine.run_workflow(workflow_id, context)
        return {
            "execution_id": execution.execution_id,
            "status": execution.status.value
        }
    except Exception as e:
        get_logger().error(f"Failed to execute workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflows/executions/{execution_id}")
async def get_execution(
    execution_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get execution details."""
    try:
        engine = get_workflow_engine()
        execution = engine.get_execution(execution_id)
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")

        return {
            "execution_id": execution.execution_id,
            "workflow_id": execution.workflow_id,
            "status": execution.status.value,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "current_step": execution.current_step,
            "completed_steps": execution.completed_steps,
            "failed_steps": execution.failed_steps
        }
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflows/executions")
async def list_executions(
    workflow_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """List workflow executions."""
    try:
        engine = get_workflow_engine()
        workflow_status = WorkflowStatus(status) if status else None
        executions = engine.list_executions(workflow_id=workflow_id, status=workflow_status)

        return {
            "executions": [
                {
                    "execution_id": ex.execution_id,
                    "workflow_id": ex.workflow_id,
                    "status": ex.status.value,
                    "started_at": ex.started_at.isoformat() if ex.started_at else None,
                    "completed_at": ex.completed_at.isoformat() if ex.completed_at else None
                }
                for ex in executions
            ]
        }
    except Exception as e:
        get_logger().error(f"Failed to list executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/workflows/executions/{execution_id}/cancel")
async def cancel_execution(
    execution_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Cancel a running execution."""
    try:
        engine = get_workflow_engine()
        result = engine.cancel_execution(execution_id)
        if not result:
            raise HTTPException(status_code=400, detail="Cannot cancel execution")
        return {"status": "cancelled"}
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to cancel execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflows/executions/{execution_id}/status")
async def get_execution_status(
    execution_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get detailed execution status."""
    try:
        engine = get_workflow_engine()
        status = engine.get_execution_status(execution_id)
        if not status:
            raise HTTPException(status_code=404, detail="Execution not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get execution status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Reviewer Bot API
# ============================================================================

# Global bot instances
_reviewer_bots: Dict[str, ReviewerBot] = {}


def get_reviewer_bot(bot_id: str = "default") -> ReviewerBot:
    """Get or create reviewer bot instance."""
    if bot_id not in _reviewer_bots:
        config = BotConfig(
            bot_id=bot_id,
            name=f"PR Agent Bot {bot_id}",
            capabilities=[
                BotCapability.SYNTAX_CHECK,
                BotCapability.STYLE_CHECK,
                BotCapability.SECURITY_SCAN,
                BotCapability.PERFORMANCE_ANALYSIS,
                BotCapability.BEST_PRACTICES,
                BotCapability.DOCUMENTATION_CHECK
            ],
            confidence_threshold=0.7,
            learning_enabled=True
        )
        _reviewer_bots[bot_id] = ReviewerBot(config)
    return _reviewer_bots[bot_id]


@app.post("/api/bot/review")
async def bot_review_pr(
    request: dict,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Trigger bot PR review."""
    try:
        bot_id = request.get("bot_id", "default")
        bot = get_reviewer_bot(bot_id)

        result = bot.review_pr(
            pr_id=request["pr_id"],
            files=request["files"],
            mode=ReviewMode(request.get("mode", "full"))
        )

        return result.to_dict()
    except Exception as e:
        get_logger().error(f"Bot review failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/bot/reviews/{review_id}")
async def get_bot_review(
    review_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get a bot review by ID."""
    try:
        # Search all bots for the review
        for bot in _reviewer_bots.values():
            review = bot.get_review(review_id)
            if review:
                return review.to_dict()

        raise HTTPException(status_code=404, detail="Review not found")
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/bot/reviews")
async def list_bot_reviews(
    bot_id: Optional[str] = None,
    pr_id: Optional[str] = None,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """List bot reviews."""
    try:
        reviews = []

        if bot_id:
            bot = get_reviewer_bot(bot_id)
            reviews = bot.list_reviews(pr_id=pr_id)
        else:
            # Get reviews from all bots
            for bot in _reviewer_bots.values():
                reviews.extend(bot.list_reviews(pr_id=pr_id))

        return {
            "reviews": [r.to_dict() for r in reviews]
        }
    except Exception as e:
        get_logger().error(f"Failed to list reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/bot/feedback")
async def submit_bot_feedback(
    request: dict,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Submit feedback for bot learning."""
    try:
        bot_id = request.get("bot_id", "default")
        bot = get_reviewer_bot(bot_id)

        bot.provide_feedback(
            comment_id=request["comment_id"],
            positive=request["positive"]
        )

        return {"status": "success"}
    except Exception as e:
        get_logger().error(f"Failed to submit feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/bot/learning-stats")
async def get_bot_learning_stats(
    bot_id: str = "default",
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get bot learning statistics."""
    try:
        bot = get_reviewer_bot(bot_id)
        stats = bot.get_learning_stats()
        return stats
    except Exception as e:
        get_logger().error(f"Failed to get learning stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/bot/config")
async def get_bot_config(
    bot_id: str = "default",
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get bot configuration."""
    try:
        bot = get_reviewer_bot(bot_id)
        return bot.export_config()
    except Exception as e:
        get_logger().error(f"Failed to get bot config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/bot/config")
async def update_bot_config(
    request: dict,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Update bot configuration."""
    try:
        bot_id = request.get("bot_id", "default")
        bot = get_reviewer_bot(bot_id)

        # Update config fields
        if "confidence_threshold" in request:
            bot.config.confidence_threshold = request["confidence_threshold"]
        if "max_comments_per_file" in request:
            bot.config.max_comments_per_file = request["max_comments_per_file"]
        if "learning_enabled" in request:
            bot.config.learning_enabled = request["learning_enabled"]

        return {"status": "updated"}
    except Exception as e:
        get_logger().error(f"Failed to update bot config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/bot/custom-checker")
async def add_custom_checker(
    request: dict,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Add a custom checker to bot."""
    try:
        bot_id = request.get("bot_id", "default")
        bot = get_reviewer_bot(bot_id)

        # Note: This is a placeholder - actual implementation would need
        # to handle dynamic code loading securely
        return {
            "status": "success",
            "message": "Custom checker registration not yet implemented"
        }
    except Exception as e:
        get_logger().error(f"Failed to add custom checker: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Review Collaboration System APIs
@app.post("/api/review-collaboration/sessions")
async def create_review_session(
    request: dict,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Create a new review collaboration session."""
    try:
        system = get_collaboration_system()
        session = system.create_session(
            session_id=request["session_id"],
            pr_id=request["pr_id"],
            repository=request["repository"],
            title=request.get("title", ""),
            description=request.get("description", "")
        )
        return {
            "session_id": session.session_id,
            "pr_id": session.pr_id,
            "repository": session.repository,
            "status": session.status.value,
            "created_at": session.created_at
        }
    except Exception as e:
        get_logger().error(f"Failed to create review session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/review-collaboration/sessions/{session_id}")
async def get_review_session(
    session_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get review session details."""
    try:
        system = get_collaboration_system()
        session = system.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return {
            "session_id": session.session_id,
            "pr_id": session.pr_id,
            "repository": session.repository,
            "title": session.title,
            "description": session.description,
            "status": session.status.value,
            "participants": [
                {
                    "user_id": p.user_id,
                    "role": p.role.value,
                    "status": p.status.value
                }
                for p in session.participants
            ],
            "comments_count": len(session.comments),
            "tasks_count": len(session.tasks),
            "created_at": session.created_at,
            "ended_at": session.ended_at
        }
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get review session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/review-collaboration/sessions/{session_id}/participants")
async def add_session_participant(
    session_id: str,
    request: dict,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Add a participant to review session."""
    try:
        system = get_collaboration_system()
        from pr_agent.review_collaboration import ParticipantRole

        system.add_participant(
            session_id=session_id,
            user_id=request["user_id"],
            role=ParticipantRole[request.get("role", "REVIEWER").upper()]
        )
        return {"status": "success"}
    except Exception as e:
        get_logger().error(f"Failed to add participant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/review-collaboration/sessions/{session_id}/comments")
async def add_session_comment(
    session_id: str,
    request: dict,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Add a comment to review session."""
    try:
        system = get_collaboration_system()
        from pr_agent.review_collaboration import CommentType

        comment = system.add_comment(
            session_id=session_id,
            comment_id=request["comment_id"],
            author=request["author"],
            content=request["content"],
            comment_type=CommentType[request.get("type", "GENERAL").upper()],
            file_path=request.get("file_path"),
            line_number=request.get("line_number"),
            parent_id=request.get("parent_id")
        )
        return {
            "comment_id": comment.comment_id,
            "author": comment.author,
            "type": comment.comment_type.value,
            "created_at": comment.created_at
        }
    except Exception as e:
        get_logger().error(f"Failed to add comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/review-collaboration/sessions/{session_id}/tasks")
async def create_session_task(
    session_id: str,
    request: dict,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Create a task in review session."""
    try:
        system = get_collaboration_system()
        from pr_agent.review_collaboration import TaskPriority

        task = system.create_task(
            session_id=session_id,
            task_id=request["task_id"],
            title=request["title"],
            description=request.get("description", ""),
            assignee=request.get("assignee"),
            priority=TaskPriority[request.get("priority", "MEDIUM").upper()]
        )
        return {
            "task_id": task.task_id,
            "title": task.title,
            "status": task.status.value,
            "priority": task.priority.value,
            "created_at": task.created_at
        }
    except Exception as e:
        get_logger().error(f"Failed to create task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/review-collaboration/sessions/{session_id}/comments/{comment_id}/vote")
async def vote_on_comment(
    session_id: str,
    comment_id: str,
    request: dict,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Vote on a comment."""
    try:
        system = get_collaboration_system()
        from pr_agent.review_collaboration import VoteType

        system.vote_on_comment(
            session_id=session_id,
            comment_id=comment_id,
            user_id=request["user_id"],
            vote_type=VoteType[request["vote_type"].upper()]
        )
        return {"status": "success"}
    except Exception as e:
        get_logger().error(f"Failed to vote on comment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/review-collaboration/sessions/{session_id}/stats")
async def get_session_stats(
    session_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get session statistics."""
    try:
        system = get_collaboration_system()
        stats = system.get_session_stats(session_id)
        return stats
    except Exception as e:
        get_logger().error(f"Failed to get session stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/review-collaboration/sessions/{session_id}/end")
async def end_review_session(
    session_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """End a review session."""
    try:
        system = get_collaboration_system()
        system.end_session(session_id)
        return {"status": "success"}
    except Exception as e:
        get_logger().error(f"Failed to end session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Metrics Collection API
# ============================================================================

@app.post("/api/metrics/reviews")
async def record_review_metric(
    request: dict,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Record a code review metric."""
    try:
        collector = get_metrics_collector()

        metrics = ReviewMetrics(
            review_id=request["review_id"],
            pr_id=request["pr_id"],
            repository=request["repository"],
            author=request["author"],
            reviewers=request["reviewers"],
            created_at=request.get("created_at", datetime.now(timezone.utc).isoformat()),
            first_response_time_minutes=request.get("first_response_time_minutes"),
            total_review_time_minutes=request.get("total_review_time_minutes"),
            time_to_merge_minutes=request.get("time_to_merge_minutes"),
            lines_added=request.get("lines_added", 0),
            lines_deleted=request.get("lines_deleted", 0),
            files_changed=request.get("files_changed", 0),
            comments_count=request.get("comments_count", 0),
            issues_found=request.get("issues_found", 0),
            suggestions_made=request.get("suggestions_made", 0),
            iterations=request.get("iterations", 1),
            approved=request.get("approved", False),
            merged=request.get("merged", False),
            rejected=request.get("rejected", False),
            metadata=request.get("metadata", {})
        )

        collector.record_review(metrics)
        return {"status": "success", "review_id": request["review_id"]}
    except Exception as e:
        get_logger().error(f"Failed to record review metric: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/metrics/reviews/{review_id}")
async def update_review_metric(
    review_id: str,
    request: dict,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Update a review metric."""
    try:
        collector = get_metrics_collector()
        collector.update_review(review_id, **request)
        return {"status": "success"}
    except Exception as e:
        get_logger().error(f"Failed to update review metric: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics/summary")
async def get_metrics_summary(
    time_range: str = "month",
    repository: Optional[str] = None,
    author: Optional[str] = None,
    reviewer: Optional[str] = None,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get comprehensive metrics summary."""
    try:
        collector = get_metrics_collector()

        # Convert time_range string to TimeRange enum
        time_range_map = {
            "day": TimeRange.DAY,
            "week": TimeRange.WEEK,
            "month": TimeRange.MONTH,
            "quarter": TimeRange.QUARTER,
            "year": TimeRange.YEAR,
            "all": TimeRange.ALL_TIME
        }

        if time_range not in time_range_map:
            raise HTTPException(status_code=400, detail=f"Invalid time_range: {time_range}")

        summary = collector.get_metrics_summary(
            time_range=time_range_map[time_range],
            repository=repository,
            author=author,
            reviewer=reviewer
        )

        return {
            "time_range": summary.time_range,
            "start_date": summary.start_date,
            "end_date": summary.end_date,
            "efficiency": {
                "avg_first_response_time_minutes": summary.efficiency.avg_first_response_time_minutes,
                "avg_total_review_time_minutes": summary.efficiency.avg_total_review_time_minutes,
                "avg_time_to_merge_minutes": summary.efficiency.avg_time_to_merge_minutes,
                "median_first_response_time_minutes": summary.efficiency.median_first_response_time_minutes,
                "reviews_per_day": summary.efficiency.reviews_per_day,
                "throughput": summary.efficiency.throughput,
                "p90_response_time": summary.efficiency.p90_response_time,
                "p95_response_time": summary.efficiency.p95_response_time
            },
            "quality": {
                "avg_comments_per_review": summary.quality.avg_comments_per_review,
                "avg_issues_per_review": summary.quality.avg_issues_per_review,
                "avg_suggestions_per_review": summary.quality.avg_suggestions_per_review,
                "avg_iterations": summary.quality.avg_iterations,
                "approval_rate": summary.quality.approval_rate,
                "rejection_rate": summary.quality.rejection_rate,
                "thoroughness_score": summary.quality.thoroughness_score,
                "issue_detection_rate": summary.quality.issue_detection_rate
            },
            "team": {
                "total_reviewers": summary.team.total_reviewers,
                "active_reviewers": summary.team.active_reviewers,
                "avg_reviews_per_reviewer": summary.team.avg_reviews_per_reviewer,
                "workload_std_dev": summary.team.workload_std_dev,
                "avg_reviewers_per_pr": summary.team.avg_reviewers_per_pr
            },
            "process": {
                "total_reviews": summary.process.total_reviews,
                "completed_reviews": summary.process.completed_reviews,
                "pending_reviews": summary.process.pending_reviews,
                "completion_rate": summary.process.completion_rate,
                "avg_lines_changed": summary.process.avg_lines_changed,
                "avg_files_changed": summary.process.avg_files_changed,
                "merge_rate": summary.process.merge_rate
            },
            "trends": summary.trends
        }
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get metrics summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics/reviewer/{reviewer}")
async def get_reviewer_metrics(
    reviewer: str,
    time_range: str = "month",
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get metrics for a specific reviewer."""
    try:
        collector = get_metrics_collector()

        time_range_map = {
            "day": TimeRange.DAY,
            "week": TimeRange.WEEK,
            "month": TimeRange.MONTH,
            "quarter": TimeRange.QUARTER,
            "year": TimeRange.YEAR
        }

        if time_range not in time_range_map:
            raise HTTPException(status_code=400, detail=f"Invalid time_range: {time_range}")

        metrics = collector.get_reviewer_metrics(reviewer, time_range_map[time_range])
        return metrics
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get reviewer metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics/author/{author}")
async def get_author_metrics(
    author: str,
    time_range: str = "month",
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get metrics for a specific author."""
    try:
        collector = get_metrics_collector()

        time_range_map = {
            "day": TimeRange.DAY,
            "week": TimeRange.WEEK,
            "month": TimeRange.MONTH,
            "quarter": TimeRange.QUARTER,
            "year": TimeRange.YEAR
        }

        if time_range not in time_range_map:
            raise HTTPException(status_code=400, detail=f"Invalid time_range: {time_range}")

        metrics = collector.get_author_metrics(author, time_range_map[time_range])
        return metrics
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get author metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics/repository/{repository:path}")
async def get_repository_metrics(
    repository: str,
    time_range: str = "month",
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get metrics for a specific repository."""
    try:
        collector = get_metrics_collector()

        time_range_map = {
            "day": TimeRange.DAY,
            "week": TimeRange.WEEK,
            "month": TimeRange.MONTH,
            "quarter": TimeRange.QUARTER,
            "year": TimeRange.YEAR
        }

        if time_range not in time_range_map:
            raise HTTPException(status_code=400, detail=f"Invalid time_range: {time_range}")

        metrics = collector.get_repository_metrics(repository, time_range_map[time_range])
        return metrics
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to get repository metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics/compare")
async def compare_periods(
    period1: str = "quarter",
    period2: str = "month",
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Compare metrics between two time periods."""
    try:
        collector = get_metrics_collector()

        time_range_map = {
            "day": TimeRange.DAY,
            "week": TimeRange.WEEK,
            "month": TimeRange.MONTH,
            "quarter": TimeRange.QUARTER,
            "year": TimeRange.YEAR
        }

        if period1 not in time_range_map or period2 not in time_range_map:
            raise HTTPException(status_code=400, detail="Invalid time period")

        comparison = collector.compare_periods(
            time_range_map[period1],
            time_range_map[period2]
        )
        return comparison
    except HTTPException:
        raise
    except Exception as e:
        get_logger().error(f"Failed to compare periods: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Report Generator API
_report_generator = None

def get_report_generator() -> ReportGenerator:
    """Get report generator singleton."""
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator()
    return _report_generator


@app.post("/api/reports/generate")
async def generate_report(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Generate a report."""
    try:
        generator = get_report_generator()

        config = ReportConfig(
            report_id=request["report_id"],
            report_type=ReportType(request["report_type"]),
            title=request["title"],
            description=request.get("description", ""),
            format=ReportFormat(request.get("format", "html")),
            include_charts=request.get("include_charts", True),
            include_raw_data=request.get("include_raw_data", False),
            template_id=request.get("template_id"),
            metadata=request.get("metadata", {})
        )

        data = request["data"]
        start_date = None
        end_date = None

        if "start_date" in request:
            start_date = datetime.fromisoformat(request["start_date"])
        if "end_date" in request:
            end_date = datetime.fromisoformat(request["end_date"])

        report = generator.generate_report(config, data, start_date, end_date)

        return {
            "report_id": report.report_id,
            "report_type": report.report_type.value,
            "format": report.format.value,
            "title": report.title,
            "generated_at": report.generated_at.isoformat(),
            "file_path": report.file_path,
            "content": report.content,
            "metadata": report.metadata
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports/{report_id}")
async def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get a generated report."""
    try:
        generator = get_report_generator()
        report = generator.get_report(report_id)

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        return {
            "report_id": report.report_id,
            "report_type": report.report_type.value,
            "format": report.format.value,
            "title": report.title,
            "generated_at": report.generated_at.isoformat(),
            "file_path": report.file_path,
            "content": report.content,
            "metadata": report.metadata
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports")
async def list_reports(
    report_type: Optional[str] = None,
    format: Optional[str] = None,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """List generated reports."""
    try:
        generator = get_report_generator()

        type_filter = ReportType(report_type) if report_type else None
        format_filter = ReportFormat(format) if format else None

        reports = generator.list_reports(type_filter, format_filter)

        return {
            "reports": [
                {
                    "report_id": r.report_id,
                    "report_type": r.report_type.value,
                    "format": r.format.value,
                    "title": r.title,
                    "generated_at": r.generated_at.isoformat(),
                    "file_path": r.file_path,
                    "metadata": r.metadata
                }
                for r in reports
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reports/templates")
async def register_report_template(
    template: Dict[str, Any],
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Register a report template."""
    try:
        generator = get_report_generator()
        generator.register_template(template["template_id"], template)

        return {"message": "Template registered successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reports/schedule")
async def schedule_report(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Schedule a report for periodic generation."""
    try:
        generator = get_report_generator()

        config = ReportConfig(
            report_id=request["report_id"],
            report_type=ReportType(request["report_type"]),
            title=request["title"],
            description=request.get("description", ""),
            format=ReportFormat(request.get("format", "html")),
            metadata=request.get("metadata", {})
        )

        schedule_id = generator.schedule_report(
            config,
            request["schedule"],
            request["data_source"]
        )

        return {"schedule_id": schedule_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/reports/{report_id}/download")
async def download_report(
    report_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Download a generated report file."""
    try:
        generator = get_report_generator()
        report = generator.get_report(report_id)

        if not report:
            raise HTTPException(status_code=404, detail="Report not found")

        if not report.file_path:
            raise HTTPException(status_code=404, detail="Report file not available")

        from fastapi.responses import FileResponse
        return FileResponse(
            path=report.file_path,
            filename=Path(report.file_path).name,
            media_type="application/octet-stream"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# AI Assistant API
# ============================================================================

class ChatRequest(BaseModel):
    """Chat request."""
    conversation_id: str
    message: str
    context: Optional[Dict] = None


class ChatResponse(BaseModel):
    """Chat response."""
    content: str
    confidence: str
    suggestions: List[str] = []
    code_snippets: List[Dict[str, str]] = []


class CodeExplanationRequest(BaseModel):
    """Code explanation request."""
    code: str
    language: str = "python"
    context: Optional[Dict] = None


class CodeExplanationResponse(BaseModel):
    """Code explanation response."""
    explanation: str
    key_concepts: List[str]
    complexity_analysis: Dict
    potential_issues: List[Dict]
    improvement_suggestions: List[str]


class ReviewOptimizationRequest(BaseModel):
    """Review optimization request."""
    comment: str
    context: Optional[Dict] = None


class ReviewOptimizationResponse(BaseModel):
    """Review optimization response."""
    original_comment: str
    optimized_comment: str
    improvements: List[str]
    tone_score: float
    clarity_score: float


class ReviewSuggestionsRequest(BaseModel):
    """Review suggestions request."""
    code: str
    file_path: str
    context: Optional[Dict] = None


@app.post("/api/assistant/chat", response_model=ChatResponse)
async def assistant_chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Chat with AI assistant."""
    try:
        assistant = get_assistant()
        response = assistant.chat(
            request.conversation_id,
            request.message,
            request.context
        )

        audit_logger.log_event(
            AuditEventType.AI_ASSISTANT_CHAT,
            user_id=current_user.username,
            severity=AuditSeverity.INFO,
            details={
                "conversation_id": request.conversation_id,
                "message_length": len(request.message)
            }
        )

        return ChatResponse(
            content=response.content,
            confidence=response.confidence.value,
            suggestions=response.suggestions,
            code_snippets=response.code_snippets
        )
    except Exception as e:
        structured_logger.error("AI assistant chat failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/assistant/explain", response_model=CodeExplanationResponse)
async def explain_code(
    request: CodeExplanationRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Explain code snippet."""
    try:
        assistant = get_assistant()
        explanation = assistant.explain_code(
            request.code,
            request.language,
            request.context
        )

        audit_logger.log_event(
            AuditEventType.CODE_EXPLANATION,
            user_id=current_user.username,
            severity=AuditSeverity.INFO,
            details={
                "language": request.language,
                "code_length": len(request.code)
            }
        )

        return CodeExplanationResponse(
            explanation=explanation.explanation,
            key_concepts=explanation.key_concepts,
            complexity_analysis=explanation.complexity_analysis,
            potential_issues=explanation.potential_issues,
            improvement_suggestions=explanation.improvement_suggestions
        )
    except Exception as e:
        structured_logger.error("Code explanation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/assistant/optimize", response_model=ReviewOptimizationResponse)
async def optimize_review_comment(
    request: ReviewOptimizationRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Optimize review comment."""
    try:
        assistant = get_assistant()
        optimization = assistant.optimize_review_comment(
            request.comment,
            request.context
        )

        audit_logger.log_event(
            AuditEventType.REVIEW_OPTIMIZATION,
            user_id=current_user.username,
            severity=AuditSeverity.INFO,
            details={
                "original_length": len(request.comment),
                "optimized_length": len(optimization.optimized_comment)
            }
        )

        return ReviewOptimizationResponse(
            original_comment=optimization.original_comment,
            optimized_comment=optimization.optimized_comment,
            improvements=optimization.improvements,
            tone_score=optimization.tone_score,
            clarity_score=optimization.clarity_score
        )
    except Exception as e:
        structured_logger.error("Review optimization failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/assistant/suggest")
async def suggest_review_points(
    request: ReviewSuggestionsRequest,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Suggest review points for code."""
    try:
        assistant = get_assistant()
        suggestions = assistant.suggest_review_points(
            request.code,
            request.file_path,
            request.context
        )

        audit_logger.log_event(
            AuditEventType.REVIEW_SUGGESTIONS,
            user_id=current_user.username,
            severity=AuditSeverity.INFO,
            details={
                "file_path": request.file_path,
                "suggestions_count": len(suggestions)
            }
        )

        return {"suggestions": suggestions}
    except Exception as e:
        structured_logger.error("Review suggestions failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/assistant/conversations/{conversation_id}/history")
async def get_conversation_history(
    conversation_id: str,
    limit: Optional[int] = Query(None, ge=1, le=100),
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get conversation history."""
    try:
        assistant = get_assistant()
        messages = assistant.get_conversation_history(conversation_id, limit)

        return {
            "conversation_id": conversation_id,
            "messages": [
                {
                    "role": msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": msg.metadata
                }
                for msg in messages
            ]
        }
    except Exception as e:
        structured_logger.error("Failed to get conversation history", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/assistant/conversations/{conversation_id}")
async def clear_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Clear conversation history."""
    try:
        assistant = get_assistant()
        assistant.clear_conversation(conversation_id)

        audit_logger.log_event(
            AuditEventType.CONVERSATION_CLEARED,
            user_id=current_user.username,
            severity=AuditSeverity.INFO,
            details={"conversation_id": conversation_id}
        )

        return {"message": "Conversation cleared successfully"}
    except Exception as e:
        structured_logger.error("Failed to clear conversation", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Report Export API
# ============================================================================

@app.post("/api/export/report")
async def export_report(
    request: Dict,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Export a report in specified format."""
    try:
        exporter = get_exporter()

        # Build report from request data
        report = ExportReport(
            title=request.get("title", "Code Review Report"),
            subtitle=request.get("subtitle"),
            author=request.get("author", current_user.username),
            date=datetime.now(),
            summary=request.get("summary", ""),
            sections=[
                ReportSection(
                    title=section.get("title", ""),
                    content=section.get("content", ""),
                    charts=[
                        ChartData(
                            type=ChartType(chart.get("type", "bar")),
                            title=chart.get("title", ""),
                            data=chart.get("data", {}),
                            labels=chart.get("labels"),
                            colors=chart.get("colors")
                        )
                        for chart in section.get("charts", [])
                    ],
                    tables=section.get("tables", []),
                    subsections=[
                        ReportSection(
                            title=sub.get("title", ""),
                            content=sub.get("content", "")
                        )
                        for sub in section.get("subsections", [])
                    ]
                )
                for section in request.get("sections", [])
            ],
            metadata=request.get("metadata", {})
        )

        # Export report
        format_str = request.get("format", "json")
        export_format = ExportFormat(format_str)
        output_path = request.get("output_path")

        data = exporter.export(report, export_format, output_path)

        audit_logger.log_event(
            AuditEventType.REPORT_EXPORTED,
            user_id=current_user.username,
            severity=AuditSeverity.INFO,
            details={
                "format": format_str,
                "title": report.title,
                "sections": len(report.sections)
            }
        )

        # Return base64 encoded data for binary formats
        if export_format in [ExportFormat.PDF, ExportFormat.EXCEL, ExportFormat.WORD]:
            import base64
            return {
                "format": format_str,
                "data": base64.b64encode(data).decode('utf-8'),
                "filename": f"report.{format_str}"
            }
        else:
            # Return text data directly
            return {
                "format": format_str,
                "data": data.decode('utf-8') if isinstance(data, bytes) else data,
                "filename": f"report.{format_str}"
            }
    except Exception as e:
        structured_logger.error("Failed to export report", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/export/formats")
async def get_export_formats(
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get available export formats."""
    try:
        exporter = get_exporter()
        formats = exporter.get_available_formats()

        return {
            "formats": [
                {
                    "value": fmt.value,
                    "label": fmt.value.upper(),
                    "available": exporter.is_format_available(fmt)
                }
                for fmt in ExportFormat
            ]
        }
    except Exception as e:
        structured_logger.error("Failed to get export formats", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/export/chart-types")
async def get_chart_types(
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get available chart types."""
    try:
        return {
            "chart_types": [
                {
                    "value": chart_type.value,
                    "label": chart_type.value.capitalize()
                }
                for chart_type in ChartType
            ]
        }
    except Exception as e:
        structured_logger.error("Failed to get chart types", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Enhanced Notification API
# ============================================================================

@app.post("/api/notifications/send")
async def send_notification(
    request: Dict,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Send notification with intelligent routing."""
    try:
        notification_system = get_notification_system()

        notification_id = request.get("notification_id", f"notif_{int(datetime.now().timestamp())}")
        recipient = request.get("recipient")
        event = NotificationEvent(request.get("event"))
        context = request.get("context", {})
        channels = [NotificationChannel(ch) for ch in request.get("channels", [])] if request.get("channels") else None
        priority = NotificationPriority(request.get("priority")) if request.get("priority") else None

        notifications = notification_system.send_notification(
            notification_id=notification_id,
            recipient=recipient,
            event=event,
            context=context,
            channels=channels,
            priority=priority
        )

        audit_logger.log_event(
            AuditEventType.NOTIFICATION_SENT,
            user_id=current_user.username,
            severity=AuditSeverity.INFO,
            details={
                "recipient": recipient,
                "event": event.value,
                "channels": [ch.value for ch in (channels or [])]
            }
        )

        return {
            "notifications": [n.to_dict() for n in notifications]
        }
    except Exception as e:
        structured_logger.error("Failed to send notification", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notifications/{notification_id}")
async def get_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get notification by ID."""
    try:
        notification_system = get_notification_system()
        notification = notification_system.get_notification(notification_id)

        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")

        return notification.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error("Failed to get notification", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notifications")
async def list_notifications(
    recipient: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    event: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user_or_api_key)
):
    """List notifications with filters."""
    try:
        notification_system = get_notification_system()

        status_enum = NotificationStatus(status) if status else None
        event_enum = NotificationEvent(event) if event else None

        notifications = notification_system.list_notifications(
            recipient=recipient,
            status=status_enum,
            event=event_enum,
            limit=limit
        )

        return {
            "notifications": [n.to_dict() for n in notifications],
            "total": len(notifications)
        }
    except Exception as e:
        structured_logger.error("Failed to list notifications", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notifications/{notification_id}/retry")
async def retry_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Retry failed notification."""
    try:
        notification_system = get_notification_system()
        result = notification_system.retry_notification(notification_id)

        if not result:
            raise HTTPException(status_code=400, detail="Cannot retry notification")

        return {"message": "Notification retried successfully"}
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error("Failed to retry notification", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/notifications/{notification_id}")
async def cancel_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Cancel pending notification."""
    try:
        notification_system = get_notification_system()
        result = notification_system.cancel_notification(notification_id)

        if not result:
            raise HTTPException(status_code=400, detail="Cannot cancel notification")

        return {"message": "Notification cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error("Failed to cancel notification", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notifications/statistics")
async def get_notification_statistics(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get notification statistics."""
    try:
        notification_system = get_notification_system()

        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None

        stats = notification_system.get_statistics(start_date=start, end_date=end)

        return stats
    except Exception as e:
        structured_logger.error("Failed to get notification statistics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notifications/templates")
async def create_notification_template(
    request: Dict,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Create notification template."""
    try:
        notification_system = get_notification_system()

        from pr_agent.notification_enhanced import NotificationTemplate

        template = NotificationTemplate(
            template_id=request.get("template_id"),
            name=request.get("name"),
            event=NotificationEvent(request.get("event")),
            subject_template=request.get("subject_template"),
            body_template=request.get("body_template"),
            channel=NotificationChannel(request.get("channel")),
            priority=NotificationPriority(request.get("priority", "medium")),
            variables=request.get("variables", []),
            metadata=request.get("metadata", {})
        )

        notification_system.add_template(template)

        return {"message": "Template created successfully", "template_id": template.template_id}
    except Exception as e:
        structured_logger.error("Failed to create template", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notifications/templates")
async def list_notification_templates(
    event: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user_or_api_key)
):
    """List notification templates."""
    try:
        notification_system = get_notification_system()

        event_enum = NotificationEvent(event) if event else None
        channel_enum = NotificationChannel(channel) if channel else None

        templates = notification_system.list_templates(event=event_enum, channel=channel_enum)

        return {
            "templates": [
                {
                    "template_id": t.template_id,
                    "name": t.name,
                    "event": t.event.value,
                    "channel": t.channel.value,
                    "priority": t.priority.value,
                    "variables": t.variables
                }
                for t in templates
            ]
        }
    except Exception as e:
        structured_logger.error("Failed to list templates", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notifications/rules")
async def create_notification_rule(
    request: Dict,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Create notification rule."""
    try:
        notification_system = get_notification_system()

        from pr_agent.notification_enhanced import NotificationRule

        rule = NotificationRule(
            rule_id=request.get("rule_id"),
            name=request.get("name"),
            event=NotificationEvent(request.get("event")),
            conditions=request.get("conditions", {}),
            channels=[NotificationChannel(ch) for ch in request.get("channels", [])],
            priority=NotificationPriority(request.get("priority", "medium")),
            enabled=request.get("enabled", True),
            rate_limit=request.get("rate_limit"),
            quiet_hours=request.get("quiet_hours"),
            metadata=request.get("metadata", {})
        )

        notification_system.add_rule(rule)

        return {"message": "Rule created successfully", "rule_id": rule.rule_id}
    except Exception as e:
        structured_logger.error("Failed to create rule", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notifications/rules")
async def list_notification_rules(
    enabled_only: bool = Query(False),
    current_user: User = Depends(get_current_user_or_api_key)
):
    """List notification rules."""
    try:
        notification_system = get_notification_system()

        rules = notification_system.list_rules(enabled_only=enabled_only)

        return {
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "name": r.name,
                    "event": r.event.value,
                    "channels": [ch.value for ch in r.channels],
                    "priority": r.priority.value,
                    "enabled": r.enabled,
                    "rate_limit": r.rate_limit,
                    "quiet_hours": r.quiet_hours
                }
                for r in rules
            ]
        }
    except Exception as e:
        structured_logger.error("Failed to list rules", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Orchestration Engine API
@app.post("/api/orchestration/workflows")
async def create_workflow(
    workflow_data: Dict[str, Any],
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Create a new workflow definition"""
    try:
        engine = get_orchestration_engine()

        # Parse tasks
        tasks = []
        for task_data in workflow_data.get("tasks", []):
            task = TaskDefinition(
                task_id=task_data["task_id"],
                name=task_data["name"],
                task_type=TaskType[task_data["task_type"].upper()],
                action=task_data.get("action"),
                condition=task_data.get("condition"),
                depends_on=task_data.get("depends_on", []),
                retry_count=task_data.get("retry_count", 0),
                timeout=task_data.get("timeout")
            )
            tasks.append(task)

        workflow = WorkflowDefinition(
            workflow_id=workflow_data["workflow_id"],
            name=workflow_data["name"],
            description=workflow_data.get("description", ""),
            tasks=tasks,
            variables=workflow_data.get("variables", {})
        )

        engine.register_workflow(workflow)

        return {
            "workflow_id": workflow.workflow_id,
            "name": workflow.name,
            "description": workflow.description,
            "task_count": len(workflow.tasks)
        }
    except Exception as e:
        structured_logger.error("Failed to create workflow", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/orchestration/workflows")
async def list_workflows(
    current_user: User = Depends(get_current_user_or_api_key)
):
    """List all registered workflows"""
    try:
        engine = get_orchestration_engine()
        workflows = engine.list_workflows()

        return {
            "workflows": [
                {
                    "workflow_id": w.workflow_id,
                    "name": w.name,
                    "description": w.description,
                    "task_count": len(w.tasks),
                    "variables": w.variables
                }
                for w in workflows
            ]
        }
    except Exception as e:
        structured_logger.error("Failed to list workflows", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/orchestration/workflows/{workflow_id}/start")
async def start_workflow(
    workflow_id: str,
    context: Dict[str, Any] = None,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Start a workflow execution"""
    try:
        engine = get_orchestration_engine()
        execution = engine.start_workflow(workflow_id, context or {})

        return {
            "execution_id": execution.execution_id,
            "workflow_id": execution.workflow_id,
            "status": execution.status.value,
            "started_at": execution.started_at.isoformat(),
            "task_count": len(execution.task_executions)
        }
    except Exception as e:
        structured_logger.error("Failed to start workflow", workflow_id=workflow_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/orchestration/executions/{execution_id}")
async def get_execution(
    execution_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Get workflow execution status"""
    try:
        engine = get_orchestration_engine()
        execution = engine.get_execution(execution_id)

        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")

        return {
            "execution_id": execution.execution_id,
            "workflow_id": execution.workflow_id,
            "status": execution.status.value,
            "started_at": execution.started_at.isoformat(),
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "context": execution.context,
            "error": execution.error,
            "tasks": [
                {
                    "task_id": task_id,
                    "status": task_exec.status.value,
                    "started_at": task_exec.started_at.isoformat() if task_exec.started_at else None,
                    "completed_at": task_exec.completed_at.isoformat() if task_exec.completed_at else None,
                    "result": task_exec.result,
                    "error": task_exec.error,
                    "retry_count": task_exec.retry_count
                }
                for task_id, task_exec in execution.task_executions.items()
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error("Failed to get execution", execution_id=execution_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/orchestration/executions/{execution_id}/cancel")
async def cancel_execution(
    execution_id: str,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """Cancel a running workflow execution"""
    try:
        engine = get_orchestration_engine()
        success = engine.cancel_execution(execution_id)

        if not success:
            raise HTTPException(status_code=404, detail="Execution not found or already completed")

        return {"message": "Execution cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        structured_logger.error("Failed to cancel execution", execution_id=execution_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/orchestration/executions")
async def list_executions(
    workflow_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user_or_api_key)
):
    """List workflow executions"""
    try:
        engine = get_orchestration_engine()

        if workflow_id:
            executions = engine.list_executions(workflow_id=workflow_id)
        else:
            executions = engine.list_executions()

        # Filter by status if provided
        if status:
            status_enum = WorkflowStatus[status.upper()]
            executions = [e for e in executions if e.status == status_enum]

        return {
            "executions": [
                {
                    "execution_id": e.execution_id,
                    "workflow_id": e.workflow_id,
                    "status": e.status.value,
                    "started_at": e.started_at.isoformat(),
                    "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                    "error": e.error
                }
                for e in executions
            ]
        }
    except Exception as e:
        structured_logger.error("Failed to list executions", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    start()
