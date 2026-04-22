"""
FastAPI middleware for rate limiting and quota management.
"""

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable, Optional
import time

from pr_agent.ratelimit import RateLimiter, RateLimitExceeded, QuotaManager, QuotaExceeded


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce rate limits on API endpoints.

    Adds rate limit headers to responses:
    - X-RateLimit-Limit: Maximum requests allowed
    - X-RateLimit-Remaining: Remaining requests in window
    - X-RateLimit-Reset: Unix timestamp when limit resets
    - Retry-After: Seconds to wait before retrying (on 429)
    """

    def __init__(
        self,
        app,
        rate_limiter: RateLimiter,
        key_func: Optional[Callable] = None,
        exempt_paths: Optional[list] = None
    ):
        """
        Initialize rate limit middleware.

        Args:
            app: FastAPI application
            rate_limiter: RateLimiter instance
            key_func: Function to extract rate limit key from request
            exempt_paths: List of paths to exempt from rate limiting
        """
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.key_func = key_func or self._default_key_func
        self.exempt_paths = exempt_paths or ["/health", "/metrics", "/docs", "/openapi.json"]

    def _default_key_func(self, request: Request) -> str:
        """Default key function uses client IP."""
        # Try to get real IP from headers (for proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to direct client
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Check if path is exempt
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)

        # Get rate limit key
        key = self.key_func(request)

        # Check rate limit
        try:
            allowed, info = self.rate_limiter.check_rate_limit(key)

            if not allowed:
                # Rate limit exceeded
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": f"Rate limit exceeded. Try again in {info['retry_after']} seconds.",
                        "limit": info["limit"],
                        "retry_after": info["retry_after"]
                    },
                    headers={
                        "X-RateLimit-Limit": str(info["limit"]),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(info["reset"]),
                        "Retry-After": str(info["retry_after"])
                    }
                )

            # Process request
            response = await call_next(request)

            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(info["reset"])

            return response

        except Exception as e:
            # On error, allow request but log
            print(f"Rate limit error: {e}")
            return await call_next(request)


class QuotaMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce organization quotas.

    Checks quotas before processing requests that consume resources.
    """

    def __init__(
        self,
        app,
        quota_manager: QuotaManager,
        org_id_func: Optional[Callable] = None,
        quota_paths: Optional[dict] = None
    ):
        """
        Initialize quota middleware.

        Args:
            app: FastAPI application
            quota_manager: QuotaManager instance
            org_id_func: Function to extract org_id from request
            quota_paths: Dict mapping path patterns to quota types
        """
        super().__init__(app)
        self.quota_manager = quota_manager
        self.org_id_func = org_id_func or self._default_org_id_func
        self.quota_paths = quota_paths or {
            "/api/reviews": "reviews",
            "/api/repositories": "repositories"
        }

    def _default_org_id_func(self, request: Request) -> Optional[int]:
        """Default function to extract org_id from request."""
        # Try to get from user state (set by auth middleware)
        if hasattr(request.state, "user"):
            return request.state.user.get("org_id")
        return None

    async def dispatch(self, request: Request, call_next):
        """Process request with quota checking."""
        # Only check POST/PUT/DELETE (resource-consuming operations)
        if request.method not in ["POST", "PUT", "DELETE"]:
            return await call_next(request)

        # Check if path requires quota check
        quota_type = None
        for path_pattern, qtype in self.quota_paths.items():
            if request.url.path.startswith(path_pattern):
                quota_type = qtype
                break

        if not quota_type:
            return await call_next(request)

        # Get organization ID
        org_id = self.org_id_func(request)
        if not org_id:
            # No org_id = skip quota check
            return await call_next(request)

        # Check quota
        try:
            if not self.quota_manager.check_quota(org_id, quota_type):
                quota = self.quota_manager.get_quota(org_id, quota_type)
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "quota_exceeded",
                        "message": f"Quota exceeded for {quota_type}",
                        "quota_type": quota_type,
                        "limit": quota.limit,
                        "used": quota.used,
                        "reset_date": quota.reset_date
                    },
                    headers={
                        "X-Quota-Limit": str(quota.limit),
                        "X-Quota-Remaining": "0",
                        "X-Quota-Reset": quota.reset_date or ""
                    }
                )

            # Process request
            response = await call_next(request)

            # Increment quota on success (2xx status)
            if 200 <= response.status_code < 300:
                try:
                    self.quota_manager.increment_quota(
                        org_id,
                        quota_type,
                        check_limit=False  # Already checked
                    )
                except Exception as e:
                    print(f"Failed to increment quota: {e}")

            # Add quota headers
            quota = self.quota_manager.get_quota(org_id, quota_type)
            if quota:
                response.headers["X-Quota-Limit"] = str(quota.limit)
                response.headers["X-Quota-Remaining"] = str(quota.remaining)
                if quota.reset_date:
                    response.headers["X-Quota-Reset"] = quota.reset_date

            return response

        except Exception as e:
            print(f"Quota check error: {e}")
            return await call_next(request)


def rate_limit_dependency(
    rate_limiter: RateLimiter,
    limit: Optional[int] = None,
    window: Optional[int] = None
):
    """
    Dependency for per-endpoint rate limiting.

    Usage:
        @app.get("/api/endpoint", dependencies=[Depends(rate_limit_dependency(limiter))])
    """
    async def check_rate_limit(request: Request):
        # Get key from request
        key = request.client.host if request.client else "unknown"

        # Check user-specific limit if authenticated
        if hasattr(request.state, "user"):
            user_id = request.state.user.get("id")
            if user_id:
                key = f"user:{user_id}"

        allowed, info = rate_limiter.check_rate_limit(key, limit, window)

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded. Try again in {info['retry_after']} seconds.",
                    "retry_after": info["retry_after"]
                },
                headers={
                    "Retry-After": str(info["retry_after"]),
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(info["reset"])
                }
            )

        # Store info in request state for response headers
        request.state.rate_limit_info = info

    return check_rate_limit


def quota_dependency(
    quota_manager: QuotaManager,
    quota_type: str
):
    """
    Dependency for per-endpoint quota checking.

    Usage:
        @app.post("/api/reviews", dependencies=[Depends(quota_dependency(manager, "reviews"))])
    """
    async def check_quota(request: Request):
        # Get org_id from authenticated user
        if not hasattr(request.state, "user"):
            return  # Skip if not authenticated

        org_id = request.state.user.get("org_id")
        if not org_id:
            return  # Skip if no org

        # Check quota
        if not quota_manager.check_quota(org_id, quota_type):
            quota = quota_manager.get_quota(org_id, quota_type)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "quota_exceeded",
                    "message": f"Quota exceeded for {quota_type}",
                    "quota_type": quota_type,
                    "limit": quota.limit,
                    "used": quota.used,
                    "reset_date": quota.reset_date
                },
                headers={
                    "X-Quota-Limit": str(quota.limit),
                    "X-Quota-Remaining": "0",
                    "X-Quota-Reset": quota.reset_date or ""
                }
            )

        # Store quota info for later increment
        request.state.quota_info = {
            "org_id": org_id,
            "quota_type": quota_type
        }

    return check_quota
