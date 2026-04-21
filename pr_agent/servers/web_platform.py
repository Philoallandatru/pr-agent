"""
Web Platform API Server

FastAPI backend for PR-Agent web management platform.
Provides REST API for repository management, review history, and prompt customization.
"""

import os
import time
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, Request, Depends
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
async def login(request: LoginRequest):
    """Authenticate user and return JWT token"""
    try:
        user = auth_manager.authenticate_user(request.username, request.password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid username or password")

        from datetime import timedelta
        access_token = auth_manager.create_access_token(
            data={"sub": user.username, "role": user.role},
            expires_delta=timedelta(hours=24)
        )

        structured_logger.info("User logged in", username=user.username)

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
async def health_check():
    """Comprehensive health check endpoint"""
    try:
        from pr_agent.config.validation import HealthChecker
        checker = HealthChecker()
        health_report = checker.check_all()
        return health_report
    except Exception as e:
        get_logger().error(f"Health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


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


def start():
    """Start the web platform server"""
    host = get_settings().get("web_platform.host", "0.0.0.0")
    port = get_settings().get("web_platform.port", 8080)

    get_logger().info(f"Starting PR-Agent Web Platform on {host}:{port}")

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start()
