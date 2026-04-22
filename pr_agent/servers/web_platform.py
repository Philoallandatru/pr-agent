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


if __name__ == "__main__":
    start()
