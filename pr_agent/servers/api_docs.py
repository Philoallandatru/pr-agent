"""
API Documentation Configuration

Enhanced OpenAPI/Swagger documentation for PR-Agent API.
"""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def custom_openapi(app: FastAPI):
    """Generate custom OpenAPI schema with enhanced documentation."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="PR-Agent API",
        version="1.0.0",
        description="""
# PR-Agent Auto-Review API

Enterprise-grade code review automation platform with AI-powered analysis.

## Features

- 🤖 **Automated PR Reviews**: AI-powered code analysis and suggestions
- 📊 **Repository Management**: Configure and monitor repositories
- 📝 **Review History**: Track all PR reviews and their results
- 🎯 **Custom Prompts**: Customize review behavior with templates
- 🔐 **Authentication**: JWT tokens and API keys
- 📈 **Monitoring**: Prometheus metrics and structured logging
- 🔔 **Notifications**: Multi-platform webhook notifications

## Authentication

All API endpoints require authentication using either:

1. **JWT Token** (for web UI):
   - Login at `/api/auth/login` to get a token
   - Include in `Authorization: Bearer <token>` header

2. **API Key** (for programmatic access):
   - Create at `/api/auth/api-keys` (admin only)
   - Include in `X-API-Key` header

## Rate Limiting

- Default: 100 requests per minute per user
- Burst: 200 requests per minute
- Contact admin for higher limits

## Support

- Documentation: https://github.com/Philoallandatru/pr-agent
- Issues: https://github.com/Philoallandatru/pr-agent/issues
        """,
        routes=app.routes,
        tags=[
            {
                "name": "Authentication",
                "description": "User authentication and API key management"
            },
            {
                "name": "Repositories",
                "description": "Repository configuration and management"
            },
            {
                "name": "Reviews",
                "description": "PR review history and results"
            },
            {
                "name": "Prompts",
                "description": "Custom prompt template management"
            },
            {
                "name": "Monitoring",
                "description": "System health and metrics"
            }
        ]
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token obtained from /api/auth/login"
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for programmatic access"
        }
    }

    # Add servers
    openapi_schema["servers"] = [
        {
            "url": "http://localhost:8000",
            "description": "Local development server"
        },
        {
            "url": "https://staging.pr-agent.example.com",
            "description": "Staging environment"
        },
        {
            "url": "https://pr-agent.example.com",
            "description": "Production environment"
        }
    ]

    # Add contact info
    openapi_schema["info"]["contact"] = {
        "name": "PR-Agent Support",
        "url": "https://github.com/Philoallandatru/pr-agent",
        "email": "support@example.com"
    }

    # Add license
    openapi_schema["info"]["license"] = {
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html"
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


# Example responses for documentation
EXAMPLE_RESPONSES = {
    "repository": {
        "id": 1,
        "project_key": "PROJ",
        "repo_slug": "backend-api",
        "name": "Backend API",
        "url": "https://bitbucket.example.com/projects/PROJ/repos/backend-api",
        "enabled": True,
        "created_at": "2026-04-22T10:00:00",
        "updated_at": "2026-04-22T10:00:00"
    },
    "review": {
        "id": 1,
        "repository_id": 1,
        "pr_number": 123,
        "pr_title": "Add new feature",
        "pr_author": "john.doe",
        "pr_url": "https://bitbucket.example.com/projects/PROJ/repos/backend-api/pull-requests/123",
        "review_status": "completed",
        "review_result": "approved",
        "commands": ["/describe", "/review"],
        "duration": 45.5,
        "created_at": "2026-04-22T10:00:00"
    },
    "prompt": {
        "id": 1,
        "name": "security-review",
        "command": "/review",
        "content": "Focus on security vulnerabilities...",
        "is_active": True,
        "created_at": "2026-04-22T10:00:00",
        "updated_at": "2026-04-22T10:00:00"
    },
    "user": {
        "username": "admin",
        "role": "admin",
        "permissions": ["read", "write", "delete"]
    },
    "token": {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer",
        "expires_in": 86400
    },
    "api_key": {
        "key": "pak_1234567890abcdef",
        "name": "ci-pipeline",
        "permissions": ["read", "write"],
        "expires_at": "2027-04-22T10:00:00"
    },
    "statistics": {
        "total_repositories": 10,
        "total_reviews": 150,
        "reviews_today": 5,
        "reviews_this_week": 25,
        "reviews_this_month": 100,
        "average_duration": 42.3,
        "success_rate": 0.95
    }
}
