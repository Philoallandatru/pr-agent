# API Reference

Complete API reference for PR Agent Auto-Review system.

## Table of Contents

- [Authentication](#authentication)
- [Repositories](#repositories)
- [Reviews](#reviews)
- [Prompts](#prompts)
- [Organizations](#organizations)
- [Users](#users)
- [Health & Monitoring](#health--monitoring)
- [Configuration](#configuration)
- [Webhooks](#webhooks)
- [Rate Limiting](#rate-limiting)

## Authentication

### Login

```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin"
  }
}
```

### API Key Authentication

Include API key in header:
```http
X-API-Key: your-api-key-here
```

Or use Bearer token:
```http
Authorization: Bearer your-jwt-token
```

## Repositories

### List Repositories

```http
GET /api/repositories?page=1&per_page=20&search=myrepo
Authorization: Bearer {token}
```

**Query Parameters:**
- `page` (integer, optional): Page number (default: 1)
- `per_page` (integer, optional): Items per page (default: 20, max: 100)
- `search` (string, optional): Search by name or URL
- `status` (string, optional): Filter by status (active, paused, error)

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "name": "my-repo",
      "url": "https://bitbucket.example.com/projects/PROJ/repos/my-repo",
      "status": "active",
      "last_review_at": "2026-04-22T10:30:00Z",
      "total_reviews": 42,
      "created_at": "2026-01-15T08:00:00Z",
      "config": {
        "auto_review": true,
        "review_on_update": true,
        "min_approval_count": 2
      }
    }
  ],
  "total": 100,
  "page": 1,
  "per_page": 20,
  "pages": 5
}
```

### Get Repository

```http
GET /api/repositories/{id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": 1,
  "name": "my-repo",
  "url": "https://bitbucket.example.com/projects/PROJ/repos/my-repo",
  "status": "active",
  "last_review_at": "2026-04-22T10:30:00Z",
  "total_reviews": 42,
  "created_at": "2026-01-15T08:00:00Z",
  "updated_at": "2026-04-22T10:30:00Z",
  "config": {
    "auto_review": true,
    "review_on_update": true,
    "min_approval_count": 2,
    "excluded_branches": ["develop", "staging"],
    "custom_prompts": {
      "review": "custom-review-prompt-id"
    }
  },
  "statistics": {
    "total_prs": 150,
    "reviewed_prs": 142,
    "avg_review_time": 45.2,
    "issues_found": 328
  }
}
```

### Create Repository

```http
POST /api/repositories
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "my-repo",
  "url": "https://bitbucket.example.com/projects/PROJ/repos/my-repo",
  "config": {
    "auto_review": true,
    "review_on_update": true,
    "min_approval_count": 2
  }
}
```

**Response:** 201 Created
```json
{
  "id": 1,
  "name": "my-repo",
  "url": "https://bitbucket.example.com/projects/PROJ/repos/my-repo",
  "status": "active",
  "created_at": "2026-04-22T10:30:00Z"
}
```

### Update Repository

```http
PUT /api/repositories/{id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "config": {
    "auto_review": false,
    "min_approval_count": 3
  }
}
```

**Response:** 200 OK

### Delete Repository

```http
DELETE /api/repositories/{id}
Authorization: Bearer {token}
```

**Response:** 204 No Content

## Reviews

### List Reviews

```http
GET /api/reviews?repository_id=1&status=completed&page=1&per_page=20
Authorization: Bearer {token}
```

**Query Parameters:**
- `repository_id` (integer, optional): Filter by repository
- `pr_number` (integer, optional): Filter by PR number
- `status` (string, optional): Filter by status (pending, in_progress, completed, failed)
- `from_date` (string, optional): ISO 8601 date
- `to_date` (string, optional): ISO 8601 date
- `page` (integer, optional): Page number
- `per_page` (integer, optional): Items per page

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "repository_id": 1,
      "pr_number": 123,
      "pr_title": "Add new feature",
      "pr_author": "john.doe",
      "status": "completed",
      "started_at": "2026-04-22T10:00:00Z",
      "completed_at": "2026-04-22T10:05:00Z",
      "duration": 300,
      "result": {
        "score": 8.5,
        "issues_found": 3,
        "suggestions": 5,
        "summary": "Overall good code quality with minor improvements needed"
      }
    }
  ],
  "total": 500,
  "page": 1,
  "per_page": 20
}
```

### Get Review

```http
GET /api/reviews/{id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": 1,
  "repository_id": 1,
  "pr_number": 123,
  "pr_title": "Add new feature",
  "pr_author": "john.doe",
  "pr_url": "https://bitbucket.example.com/projects/PROJ/repos/my-repo/pull-requests/123",
  "status": "completed",
  "started_at": "2026-04-22T10:00:00Z",
  "completed_at": "2026-04-22T10:05:00Z",
  "duration": 300,
  "result": {
    "score": 8.5,
    "issues_found": 3,
    "suggestions": 5,
    "summary": "Overall good code quality with minor improvements needed",
    "details": {
      "code_quality": {
        "score": 9.0,
        "issues": [
          {
            "severity": "warning",
            "file": "src/main.py",
            "line": 42,
            "message": "Consider using list comprehension for better readability",
            "suggestion": "result = [x * 2 for x in items]"
          }
        ]
      },
      "security": {
        "score": 8.0,
        "issues": [
          {
            "severity": "high",
            "file": "src/auth.py",
            "line": 15,
            "message": "Potential SQL injection vulnerability",
            "suggestion": "Use parameterized queries"
          }
        ]
      },
      "performance": {
        "score": 8.5,
        "issues": []
      }
    }
  },
  "metadata": {
    "model": "gpt-4",
    "prompt_version": "v2.1",
    "tokens_used": 1500,
    "cost": 0.045
  }
}
```

### Trigger Manual Review

```http
POST /api/reviews
Authorization: Bearer {token}
Content-Type: application/json

{
  "repository_id": 1,
  "pr_number": 123,
  "force": false
}
```

**Response:** 202 Accepted
```json
{
  "id": 1,
  "status": "pending",
  "message": "Review queued successfully"
}
```

## Prompts

### List Prompts

```http
GET /api/prompts?type=review&page=1&per_page=20
Authorization: Bearer {token}
```

**Query Parameters:**
- `type` (string, optional): Filter by type (review, describe, improve, etc.)
- `active` (boolean, optional): Filter by active status
- `search` (string, optional): Search by name or description

**Response:**
```json
{
  "items": [
    {
      "id": "custom-review-v1",
      "name": "Custom Review Prompt",
      "type": "review",
      "description": "Custom prompt for code review with security focus",
      "active": true,
      "version": "1.0",
      "created_at": "2026-04-01T00:00:00Z",
      "updated_at": "2026-04-15T10:00:00Z",
      "usage_count": 150
    }
  ],
  "total": 10,
  "page": 1,
  "per_page": 20
}
```

### Get Prompt

```http
GET /api/prompts/{id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": "custom-review-v1",
  "name": "Custom Review Prompt",
  "type": "review",
  "description": "Custom prompt for code review with security focus",
  "active": true,
  "version": "1.0",
  "content": "You are a code reviewer focusing on security...",
  "variables": ["language", "context", "diff"],
  "created_at": "2026-04-01T00:00:00Z",
  "updated_at": "2026-04-15T10:00:00Z",
  "created_by": "admin",
  "usage_count": 150
}
```

### Create Prompt

```http
POST /api/prompts
Authorization: Bearer {token}
Content-Type: application/json

{
  "id": "custom-review-v2",
  "name": "Custom Review Prompt v2",
  "type": "review",
  "description": "Enhanced security-focused review",
  "content": "You are a code reviewer...",
  "active": true
}
```

**Response:** 201 Created

### Update Prompt

```http
PUT /api/prompts/{id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "content": "Updated prompt content...",
  "active": true
}
```

**Response:** 200 OK

### Delete Prompt

```http
DELETE /api/prompts/{id}
Authorization: Bearer {token}
```

**Response:** 204 No Content

## Organizations

### List Organizations

```http
GET /api/organizations?page=1&per_page=20
Authorization: Bearer {token}
```

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "name": "Acme Corp",
      "slug": "acme-corp",
      "plan": "enterprise",
      "member_count": 25,
      "repository_count": 50,
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "total": 5,
  "page": 1,
  "per_page": 20
}
```

### Get Organization

```http
GET /api/organizations/{id}
Authorization: Bearer {token}
```

**Response:**
```json
{
  "id": 1,
  "name": "Acme Corp",
  "slug": "acme-corp",
  "plan": "enterprise",
  "settings": {
    "auto_review_enabled": true,
    "require_approval": true,
    "max_repositories": 100
  },
  "quotas": {
    "api_calls": {
      "used": 15000,
      "limit": 100000,
      "reset_at": "2026-05-01T00:00:00Z"
    },
    "reviews": {
      "used": 500,
      "limit": 10000,
      "reset_at": "2026-05-01T00:00:00Z"
    }
  },
  "statistics": {
    "total_reviews": 5000,
    "total_prs": 5500,
    "avg_review_time": 42.5
  }
}
```

### Create Organization

```http
POST /api/organizations
Authorization: Bearer {token}
Content-Type: application/json

{
  "name": "New Corp",
  "slug": "new-corp",
  "plan": "professional"
}
```

**Response:** 201 Created

## Users

### List Users

```http
GET /api/users?organization_id=1&role=member&page=1&per_page=20
Authorization: Bearer {token}
```

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "username": "john.doe",
      "email": "john@example.com",
      "role": "admin",
      "active": true,
      "last_login": "2026-04-22T09:00:00Z",
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "total": 25,
  "page": 1,
  "per_page": 20
}
```

### Create User

```http
POST /api/users
Authorization: Bearer {token}
Content-Type: application/json

{
  "username": "jane.doe",
  "email": "jane@example.com",
  "password": "secure-password",
  "role": "member",
  "organization_id": 1
}
```

**Response:** 201 Created

### Update User

```http
PUT /api/users/{id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "role": "admin",
  "active": true
}
```

**Response:** 200 OK

## Health & Monitoring

### Health Check

```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-04-22T10:30:00Z",
  "version": "1.0.0",
  "components": {
    "database": {
      "status": "healthy",
      "response_time": 5
    },
    "cache": {
      "status": "healthy",
      "hit_rate": 0.95
    },
    "bitbucket": {
      "status": "healthy",
      "response_time": 150
    }
  }
}
```

### Metrics

```http
GET /api/metrics
Authorization: Bearer {token}
```

**Response:** Prometheus format
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/reviews",status="200"} 1500

# HELP review_duration_seconds Review processing duration
# TYPE review_duration_seconds histogram
review_duration_seconds_bucket{le="10"} 100
review_duration_seconds_bucket{le="30"} 450
review_duration_seconds_bucket{le="60"} 480
```

### Logs

```http
GET /api/logs?level=error&from=2026-04-22T00:00:00Z&limit=100
Authorization: Bearer {token}
```

**Response:**
```json
{
  "logs": [
    {
      "timestamp": "2026-04-22T10:15:30Z",
      "level": "error",
      "message": "Failed to fetch PR details",
      "context": {
        "repository_id": 1,
        "pr_number": 123,
        "error": "Connection timeout"
      }
    }
  ],
  "total": 50,
  "has_more": false
}
```

## Configuration

### Get Configuration

```http
GET /api/config
Authorization: Bearer {token}
```

**Response:**
```json
{
  "polling": {
    "enabled": true,
    "interval": 300,
    "batch_size": 10
  },
  "review": {
    "auto_review": true,
    "review_on_update": true,
    "timeout": 600
  },
  "notifications": {
    "slack_enabled": true,
    "email_enabled": false
  }
}
```

### Update Configuration

```http
PUT /api/config
Authorization: Bearer {token}
Content-Type: application/json

{
  "polling": {
    "interval": 600
  }
}
```

**Response:** 200 OK

## Webhooks

### List Webhooks

```http
GET /api/webhooks?page=1&per_page=20
Authorization: Bearer {token}
```

**Response:**
```json
{
  "items": [
    {
      "id": 1,
      "url": "https://hooks.slack.com/services/...",
      "events": ["review.completed", "review.failed"],
      "active": true,
      "created_at": "2026-04-01T00:00:00Z"
    }
  ],
  "total": 3,
  "page": 1,
  "per_page": 20
}
```

### Create Webhook

```http
POST /api/webhooks
Authorization: Bearer {token}
Content-Type: application/json

{
  "url": "https://hooks.slack.com/services/...",
  "events": ["review.completed", "review.failed"],
  "secret": "webhook-secret",
  "active": true
}
```

**Response:** 201 Created

## Rate Limiting

All API endpoints are subject to rate limiting. Rate limit information is included in response headers:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1714651200
```

**Rate Limits by Plan:**
- Free: 100 requests/hour
- Professional: 1,000 requests/hour
- Enterprise: 10,000 requests/hour

When rate limit is exceeded:
```json
{
  "error": "rate_limit_exceeded",
  "message": "API rate limit exceeded",
  "retry_after": 3600
}
```

## Error Responses

All errors follow this format:

```json
{
  "error": "error_code",
  "message": "Human-readable error message",
  "details": {
    "field": "Additional context"
  },
  "request_id": "req_abc123"
}
```

**Common Error Codes:**
- `400` - Bad Request: Invalid input
- `401` - Unauthorized: Missing or invalid authentication
- `403` - Forbidden: Insufficient permissions
- `404` - Not Found: Resource not found
- `409` - Conflict: Resource already exists
- `422` - Unprocessable Entity: Validation error
- `429` - Too Many Requests: Rate limit exceeded
- `500` - Internal Server Error: Server error
- `503` - Service Unavailable: Service temporarily unavailable

## Pagination

List endpoints support pagination with these parameters:
- `page`: Page number (default: 1)
- `per_page`: Items per page (default: 20, max: 100)

Response includes pagination metadata:
```json
{
  "items": [...],
  "total": 500,
  "page": 1,
  "per_page": 20,
  "pages": 25
}
```

## Filtering & Sorting

Many list endpoints support filtering and sorting:

```http
GET /api/reviews?status=completed&sort=-created_at&from_date=2026-04-01
```

**Sort Format:**
- Ascending: `sort=field_name`
- Descending: `sort=-field_name`

## Webhooks Events

Available webhook events:
- `review.started` - Review process started
- `review.completed` - Review completed successfully
- `review.failed` - Review failed
- `repository.added` - Repository added
- `repository.removed` - Repository removed
- `pr.opened` - New PR detected
- `pr.updated` - PR updated

**Webhook Payload Example:**
```json
{
  "event": "review.completed",
  "timestamp": "2026-04-22T10:30:00Z",
  "data": {
    "review_id": 1,
    "repository_id": 1,
    "pr_number": 123,
    "status": "completed",
    "result": {
      "score": 8.5,
      "issues_found": 3
    }
  }
}
```
