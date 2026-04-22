# API Documentation

Complete API reference for PR-Agent Auto-Review platform.

## Base URL

```
http://localhost:8000
```

## Authentication

All API endpoints require authentication using one of the following methods:

### JWT Token (Web UI)

1. Login to get a token:
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

2. Use token in subsequent requests:
```bash
curl http://localhost:8000/api/repositories \
  -H "Authorization: Bearer <token>"
```

### API Key (Programmatic Access)

1. Create an API key (admin only):
```bash
curl -X POST http://localhost:8000/api/auth/api-keys \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ci-pipeline",
    "permissions": ["read", "write"],
    "expires_days": 365
  }'
```

Response:
```json
{
  "key": "pak_1234567890abcdef",
  "name": "ci-pipeline",
  "permissions": ["read", "write"],
  "expires_at": "2027-04-22T10:00:00"
}
```

2. Use API key in requests:
```bash
curl http://localhost:8000/api/repositories \
  -H "X-API-Key: pak_1234567890abcdef"
```

## Endpoints

### Authentication

#### POST /api/auth/login
Login with username and password.

**Request:**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

#### GET /api/auth/me
Get current user information.

**Response:**
```json
{
  "username": "admin",
  "role": "admin",
  "permissions": ["read", "write", "delete"]
}
```

#### POST /api/auth/api-keys
Create a new API key (admin only).

**Request:**
```json
{
  "name": "ci-pipeline",
  "permissions": ["read", "write"],
  "expires_days": 365
}
```

**Response:**
```json
{
  "key": "pak_1234567890abcdef",
  "name": "ci-pipeline",
  "permissions": ["read", "write"],
  "expires_at": "2027-04-22T10:00:00"
}
```

#### GET /api/auth/api-keys
List all API keys (admin only).

**Response:**
```json
{
  "api_keys": [
    {
      "prefix": "pak_123",
      "name": "ci-pipeline",
      "permissions": ["read", "write"],
      "created_at": "2026-04-22T10:00:00"
    }
  ]
}
```

#### DELETE /api/auth/api-keys/{key_prefix}
Revoke an API key (admin only).

**Response:**
```json
{
  "message": "API key revoked successfully"
}
```

### Repositories

#### GET /api/repositories
List all repositories.

**Response:**
```json
{
  "repositories": [
    {
      "id": 1,
      "project_key": "PROJ",
      "repo_slug": "backend-api",
      "name": "Backend API",
      "url": "https://bitbucket.example.com/projects/PROJ/repos/backend-api",
      "enabled": true,
      "created_at": "2026-04-22T10:00:00",
      "updated_at": "2026-04-22T10:00:00"
    }
  ]
}
```

#### GET /api/repositories/{id}
Get a specific repository.

**Response:**
```json
{
  "id": 1,
  "project_key": "PROJ",
  "repo_slug": "backend-api",
  "name": "Backend API",
  "url": "https://bitbucket.example.com/projects/PROJ/repos/backend-api",
  "enabled": true,
  "created_at": "2026-04-22T10:00:00",
  "updated_at": "2026-04-22T10:00:00"
}
```

#### POST /api/repositories
Create a new repository.

**Request:**
```json
{
  "project_key": "PROJ",
  "repo_slug": "backend-api",
  "name": "Backend API",
  "url": "https://bitbucket.example.com/projects/PROJ/repos/backend-api",
  "enabled": true
}
```

**Response:**
```json
{
  "id": 1,
  "project_key": "PROJ",
  "repo_slug": "backend-api",
  "name": "Backend API",
  "url": "https://bitbucket.example.com/projects/PROJ/repos/backend-api",
  "enabled": true,
  "created_at": "2026-04-22T10:00:00",
  "updated_at": "2026-04-22T10:00:00"
}
```

#### PUT /api/repositories/{id}
Update a repository.

**Request:**
```json
{
  "enabled": false
}
```

**Response:**
```json
{
  "id": 1,
  "enabled": false,
  "updated_at": "2026-04-22T11:00:00"
}
```

#### DELETE /api/repositories/{id}
Delete a repository.

**Response:**
```json
{
  "message": "Repository deleted successfully"
}
```

### Reviews

#### GET /api/reviews
List PR reviews with optional filters.

**Query Parameters:**
- `repository_id` (optional): Filter by repository
- `status` (optional): Filter by status (pending, completed, failed)
- `limit` (optional): Maximum number of results (default: 50)
- `offset` (optional): Pagination offset (default: 0)

**Example:**
```bash
curl "http://localhost:8000/api/reviews?repository_id=1&status=completed&limit=10"
```

**Response:**
```json
{
  "reviews": [
    {
      "id": 1,
      "repository_id": 1,
      "pr_number": 123,
      "pr_title": "Add new feature",
      "pr_author": "john.doe",
      "pr_url": "https://bitbucket.example.com/pr/123",
      "review_status": "completed",
      "review_result": "approved",
      "commands": ["/describe", "/review"],
      "duration": 45.5,
      "created_at": "2026-04-22T10:00:00"
    }
  ],
  "total": 1
}
```

#### GET /api/reviews/{id}
Get a specific review.

**Response:**
```json
{
  "id": 1,
  "repository_id": 1,
  "pr_number": 123,
  "pr_title": "Add new feature",
  "pr_author": "john.doe",
  "pr_url": "https://bitbucket.example.com/pr/123",
  "review_status": "completed",
  "review_result": "approved",
  "commands": ["/describe", "/review"],
  "duration": 45.5,
  "created_at": "2026-04-22T10:00:00"
}
```

#### POST /api/reviews
Create a new review record.

**Request:**
```json
{
  "repository_id": 1,
  "pr_number": 123,
  "pr_title": "Add new feature",
  "pr_author": "john.doe",
  "pr_url": "https://bitbucket.example.com/pr/123",
  "commands": ["/describe", "/review"]
}
```

**Response:**
```json
{
  "id": 1,
  "repository_id": 1,
  "pr_number": 123,
  "review_status": "pending",
  "created_at": "2026-04-22T10:00:00"
}
```

### Prompts

#### GET /api/prompts
List all prompt templates.

**Response:**
```json
{
  "prompts": [
    {
      "id": 1,
      "name": "security-review",
      "command": "/review",
      "content": "Focus on security vulnerabilities...",
      "is_active": true,
      "created_at": "2026-04-22T10:00:00",
      "updated_at": "2026-04-22T10:00:00"
    }
  ]
}
```

#### POST /api/prompts
Create a new prompt template.

**Request:**
```json
{
  "name": "security-review",
  "command": "/review",
  "content": "Focus on security vulnerabilities and best practices...",
  "is_active": true
}
```

**Response:**
```json
{
  "id": 1,
  "name": "security-review",
  "command": "/review",
  "content": "Focus on security vulnerabilities...",
  "is_active": true,
  "created_at": "2026-04-22T10:00:00"
}
```

#### PUT /api/prompts/{id}
Update a prompt template.

**Request:**
```json
{
  "content": "Updated prompt content...",
  "is_active": true
}
```

**Response:**
```json
{
  "id": 1,
  "content": "Updated prompt content...",
  "updated_at": "2026-04-22T11:00:00"
}
```

#### DELETE /api/prompts/{id}
Delete a prompt template.

**Response:**
```json
{
  "message": "Prompt deleted successfully"
}
```

### Monitoring

#### GET /api/health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-04-22T10:00:00",
  "version": "1.0.0",
  "database": "connected",
  "uptime": 3600
}
```

#### GET /api/statistics
Get system statistics.

**Response:**
```json
{
  "repositories": {
    "total": 10,
    "active": 8
  },
  "reviews": {
    "total": 150,
    "today": 5,
    "this_week": 25,
    "this_month": 100,
    "success_rate": 0.95
  },
  "performance": {
    "average_duration": 42.3,
    "median_duration": 38.5,
    "p95_duration": 65.2
  }
}
```

#### GET /api/metrics
Get metrics in JSON format.

**Response:**
```json
{
  "http_requests_total": 1234,
  "http_request_duration_seconds": 0.123,
  "pr_reviews_total": 150,
  "pr_review_duration_seconds": 42.3,
  "system_cpu_percent": 25.5,
  "system_memory_percent": 45.2
}
```

#### GET /metrics
Get metrics in Prometheus format.

**Response:**
```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/repositories"} 1234

# HELP pr_reviews_total Total PR reviews
# TYPE pr_reviews_total counter
pr_reviews_total{repository="PROJ/backend-api",status="success"} 150
```

## Error Responses

All endpoints return standard error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Insufficient permissions"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Rate Limiting

- Default: 100 requests per minute per user
- Burst: 200 requests per minute
- Headers included in response:
  - `X-RateLimit-Limit`: Maximum requests per minute
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Time when limit resets (Unix timestamp)

## Pagination

List endpoints support pagination:

```bash
curl "http://localhost:8000/api/reviews?limit=50&offset=0"
```

Response includes pagination metadata:
```json
{
  "reviews": [...],
  "total": 150,
  "limit": 50,
  "offset": 0,
  "has_more": true
}
```

## Webhooks

Configure webhooks to receive notifications:

```toml
[webhook]
enabled = true
slack_url = "https://hooks.slack.com/services/..."
dingtalk_url = "https://oapi.dingtalk.com/robot/send?access_token=..."
```

Events:
- `review_started`: PR review has started
- `review_completed`: PR review completed successfully
- `review_failed`: PR review failed

## SDKs and Tools

### Python SDK

```python
from pr_agent_sdk import PRAgentClient

client = PRAgentClient(
    base_url="http://localhost:8000",
    api_key="pak_1234567890abcdef"
)

# List repositories
repos = client.repositories.list()

# Get review history
reviews = client.reviews.list(repository_id=1, status="completed")

# Create prompt
prompt = client.prompts.create(
    name="security-review",
    command="/review",
    content="Focus on security..."
)
```

### CLI Tool

```bash
# Install
pip install pr-agent-cli

# Configure
pr-agent config set api-key pak_1234567890abcdef

# List repositories
pr-agent repos list

# Get review
pr-agent reviews get 123
```

### Postman Collection

Import the Postman collection from `docs/postman_collection.json` for easy API testing.

## Interactive Documentation

Visit the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Support

- GitHub: https://github.com/Philoallandatru/pr-agent
- Issues: https://github.com/Philoallandatru/pr-agent/issues
- Documentation: https://pr-agent.readthedocs.io
