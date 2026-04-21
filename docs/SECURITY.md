# Security and Authentication

PR-Agent Web Platform includes comprehensive security features to protect your deployment.

## Features

### 1. JWT Token Authentication
- Secure token-based authentication using JSON Web Tokens
- 24-hour token expiration (configurable)
- HS256 algorithm for token signing

### 2. API Key Management
- Create and manage API keys for programmatic access
- Per-key permission control
- Key revocation support
- Last-used tracking

### 3. Role-Based Access Control (RBAC)
Three built-in roles with different permission levels:

- **Admin**: Full access to all operations
- **Editor**: Read and write access (cannot manage users/keys)
- **Viewer**: Read-only access

### 4. Password Security
- Argon2 password hashing (industry standard)
- Bcrypt fallback support
- Secure password storage
- No plaintext passwords

## Configuration

### Environment Variables

```bash
# Secret key for JWT signing (auto-generated if not set)
export PR_AGENT_SECRET_KEY="your-secret-key-here"

# Default admin password (default: "admin")
export PR_AGENT_ADMIN_PASSWORD="your-secure-password"
```

**Important**: Change the default admin password in production!

## API Endpoints

### Authentication

#### Login
```bash
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "your-password"
}

Response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

#### Get Current User
```bash
GET /api/auth/me
Authorization: Bearer <token>

Response:
{
  "username": "admin",
  "email": "admin@example.com",
  "role": "admin"
}
```

#### Create API Key (Admin Only)
```bash
POST /api/auth/api-keys
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "name": "ci-pipeline",
  "permissions": ["read", "write"],
  "expires_days": 90
}

Response:
{
  "key": "very-long-random-key",
  "name": "ci-pipeline",
  "permissions": ["read", "write"],
  "expires_at": "2026-07-15T10:30:00"
}
```

#### List API Keys (Admin Only)
```bash
GET /api/auth/api-keys
Authorization: Bearer <admin-token>

Response:
{
  "api_keys": [
    {
      "key_prefix": "very-lon...",
      "name": "ci-pipeline",
      "permissions": ["read", "write"],
      "created_at": "2026-04-15T10:30:00",
      "last_used": "2026-04-16T14:20:00"
    }
  ]
}
```

#### Revoke API Key (Admin Only)
```bash
DELETE /api/auth/api-keys/{key_prefix}
Authorization: Bearer <admin-token>

Response:
{
  "message": "API key revoked successfully"
}
```

## Using Authentication

### With JWT Token

```bash
# Login to get token
TOKEN=$(curl -X POST http://localhost:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}' \
  | jq -r '.access_token')

# Use token for API requests
curl http://localhost:8080/api/repositories \
  -H "Authorization: Bearer $TOKEN"
```

### With API Key

```bash
# Use API key directly
curl http://localhost:8080/api/repositories \
  -H "Authorization: Bearer your-api-key-here"
```

## Protected Endpoints

All API endpoints require authentication:

### Read Operations (All Roles)
- `GET /api/repositories` - List repositories
- `GET /api/repositories/{id}` - Get repository details
- `GET /api/reviews` - List reviews
- `GET /api/reviews/{id}` - Get review details
- `GET /api/prompts` - List prompt templates
- `GET /api/statistics` - Get statistics

### Write Operations (Editor, Admin)
- `POST /api/repositories` - Create repository
- `PUT /api/repositories/{id}` - Update repository
- `POST /api/reviews` - Create review
- `PUT /api/reviews/{id}` - Update review
- `POST /api/reviews/{id}/retry` - Retry review
- `POST /api/prompts` - Create prompt template
- `PUT /api/prompts/{id}` - Update prompt template

### Delete Operations (Editor, Admin)
- `DELETE /api/repositories/{id}` - Delete repository
- `DELETE /api/prompts/{id}` - Delete prompt template

### Admin Operations (Admin Only)
- `POST /api/auth/api-keys` - Create API key
- `GET /api/auth/api-keys` - List API keys
- `DELETE /api/auth/api-keys/{prefix}` - Revoke API key

## Security Best Practices

### 1. Change Default Credentials
```bash
# Set a strong admin password
export PR_AGENT_ADMIN_PASSWORD="$(openssl rand -base64 32)"
```

### 2. Use Strong Secret Keys
```bash
# Generate a secure secret key
export PR_AGENT_SECRET_KEY="$(openssl rand -base64 64)"
```

### 3. Enable HTTPS
Configure your reverse proxy (nginx/Apache) to use HTTPS:

```nginx
server {
    listen 443 ssl;
    server_name pr-agent.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 4. Rotate API Keys Regularly
```bash
# Revoke old keys
curl -X DELETE http://localhost:8080/api/auth/api-keys/old-key \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# Create new keys
curl -X POST http://localhost:8080/api/auth/api-keys \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"new-key","permissions":["read","write"],"expires_days":90}'
```

### 5. Monitor Access
Check API key usage:
```bash
curl http://localhost:8080/api/auth/api-keys \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  | jq '.api_keys[] | {name, last_used}'
```

### 6. Use Least Privilege
- Create viewer keys for read-only access
- Use editor keys for CI/CD pipelines
- Limit admin access to trusted users only

### 7. Network Security
- Run behind a firewall
- Use VPN for remote access
- Implement rate limiting at reverse proxy level

## Troubleshooting

### Invalid Token Error
```
{"detail": "Invalid authentication credentials"}
```
- Token may have expired (24h lifetime)
- Token may be malformed
- Secret key may have changed
- Solution: Login again to get a new token

### Permission Denied
```
{"detail": "Write permission required"}
```
- Your role doesn't have sufficient permissions
- Solution: Contact admin to upgrade your role or use an API key with appropriate permissions

### API Key Not Working
```
{"detail": "Invalid authentication credentials"}
```
- Key may have been revoked
- Key may be incorrect
- Solution: Create a new API key

## Dependencies

Required Python packages:
- `python-jose[cryptography]` - JWT token handling
- `passlib[argon2]` - Password hashing
- `argon2-cffi` - Argon2 password hashing
- `bcrypt` - Bcrypt password hashing (fallback)

Install with:
```bash
pip install python-jose[cryptography] passlib[argon2] argon2-cffi bcrypt
```

## Testing

Run security tests:
```bash
pytest tests/unittest/test_security.py -v
```

All 23 security tests should pass.
