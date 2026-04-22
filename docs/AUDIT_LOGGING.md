# Audit Logging System

The audit logging system provides comprehensive tracking of security-relevant events for compliance, security monitoring, and forensic analysis.

## Overview

The audit logger records all significant events in the system, including:
- Authentication attempts (login/logout)
- Authorization decisions (access granted/denied)
- Resource modifications (create/update/delete)
- Configuration changes
- API usage and quota violations
- System events

All audit logs are stored in a SQLite database with efficient indexing for fast queries.

## Features

- **30+ Event Types**: Comprehensive coverage of security-relevant events
- **Severity Levels**: INFO, WARNING, ERROR, CRITICAL
- **Structured Metadata**: JSON-based additional context
- **Advanced Querying**: Filter by event type, user, time range, severity
- **Statistics**: Event counts, top users, trends
- **Automatic Retention**: Configurable cleanup of old logs
- **Real-time Logging**: Events logged to both database and standard logger

## Event Types

### Authentication Events
- `LOGIN_SUCCESS` - Successful user login
- `LOGIN_FAILURE` - Failed login attempt
- `LOGOUT` - User logout
- `TOKEN_CREATED` - API token created
- `TOKEN_REVOKED` - API token revoked
- `PASSWORD_CHANGED` - User password changed

### Authorization Events
- `ACCESS_GRANTED` - Access to resource granted
- `ACCESS_DENIED` - Access to resource denied
- `PERMISSION_CHANGED` - User permissions modified
- `ROLE_CHANGED` - User role changed

### Resource Events
- `RESOURCE_CREATED` - New resource created
- `RESOURCE_UPDATED` - Resource modified
- `RESOURCE_DELETED` - Resource deleted
- `RESOURCE_ACCESSED` - Resource accessed/viewed

### Configuration Events
- `CONFIG_CHANGED` - Configuration modified
- `CONFIG_RELOADED` - Configuration reloaded

### Organization Events
- `ORG_CREATED` - Organization created
- `ORG_UPDATED` - Organization updated
- `ORG_DELETED` - Organization deleted
- `MEMBER_ADDED` - Member added to organization
- `MEMBER_REMOVED` - Member removed from organization

### API Events
- `API_KEY_CREATED` - API key created
- `API_KEY_REVOKED` - API key revoked
- `RATE_LIMIT_EXCEEDED` - Rate limit exceeded
- `QUOTA_EXCEEDED` - Quota limit exceeded

### System Events
- `SERVICE_STARTED` - Service started
- `SERVICE_STOPPED` - Service stopped
- `BACKUP_CREATED` - Backup created
- `MIGRATION_EXECUTED` - Database migration executed

## Configuration

Add to `configuration.toml`:

```toml
[audit]
# Path to audit log database
db_path = "audit.db"

# Retention period in days (default: 90)
retention_days = 90

# Enable audit logging (default: true)
enabled = true
```

## Usage

### Python API

```python
from pr_agent.audit import get_audit_logger, AuditEventType, AuditSeverity

# Get audit logger instance
audit_logger = get_audit_logger()

# Log a simple event
audit_logger.log(
    event_type=AuditEventType.LOGIN_SUCCESS,
    severity=AuditSeverity.INFO,
    username="alice",
    ip_address="192.168.1.100",
    message="User logged in successfully"
)

# Log with metadata
audit_logger.log(
    event_type=AuditEventType.RESOURCE_CREATED,
    severity=AuditSeverity.INFO,
    user_id="user123",
    username="alice",
    resource_type="repository",
    resource_id="repo456",
    action="create",
    result="success",
    message="Repository created",
    metadata={
        "repo_name": "my-project",
        "visibility": "private",
        "size_mb": 15.2
    }
)

# Query logs
from datetime import datetime, timedelta

logs = audit_logger.query(
    event_types=[AuditEventType.LOGIN_SUCCESS, AuditEventType.LOGIN_FAILURE],
    username="alice",
    start_time=datetime.now() - timedelta(days=7),
    limit=50
)

for log in logs:
    print(f"{log['timestamp']} - {log['event_type']} - {log['message']}")

# Get statistics
stats = audit_logger.get_statistics(
    start_time=datetime.now() - timedelta(days=30)
)

print(f"Total events: {stats['total_events']}")
print(f"Events by type: {stats['by_event_type']}")
print(f"Events by severity: {stats['by_severity']}")
print(f"Top users: {stats['top_users']}")

# Cleanup old logs
deleted = audit_logger.cleanup_old_logs(days=90)
print(f"Deleted {deleted} old audit logs")
```

### REST API

#### Query Audit Logs

```bash
GET /api/audit/logs

Query Parameters:
- event_type: Filter by event type (e.g., "login_success")
- severity: Filter by severity (info, warning, error, critical)
- user_id: Filter by user ID
- username: Filter by username
- resource_type: Filter by resource type
- start_time: Start of time range (ISO 8601)
- end_time: End of time range (ISO 8601)
- limit: Maximum results (default: 100, max: 1000)
- offset: Pagination offset (default: 0)

Example:
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/audit/logs?event_type=login_success&limit=10"

Response:
{
  "logs": [
    {
      "id": 123,
      "timestamp": "2024-01-15T10:30:00Z",
      "event_type": "login_success",
      "severity": "info",
      "user_id": "user123",
      "username": "alice",
      "ip_address": "192.168.1.100",
      "message": "User logged in successfully",
      "metadata": {"browser": "Chrome"}
    }
  ],
  "count": 1,
  "limit": 10,
  "offset": 0
}
```

#### Get Audit Statistics

```bash
GET /api/audit/statistics

Query Parameters:
- start_time: Start of time range (ISO 8601)
- end_time: End of time range (ISO 8601)

Example:
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/audit/statistics?start_time=2024-01-01T00:00:00Z"

Response:
{
  "total_events": 1523,
  "by_event_type": {
    "login_success": 450,
    "login_failure": 23,
    "resource_created": 120,
    "config_changed": 15
  },
  "by_severity": {
    "info": 1400,
    "warning": 100,
    "error": 20,
    "critical": 3
  },
  "top_users": [
    {"username": "alice", "count": 234},
    {"username": "bob", "count": 189}
  ]
}
```

#### Cleanup Old Logs (Admin Only)

```bash
POST /api/audit/cleanup?days=90

Example:
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/audit/cleanup?days=90"

Response:
{
  "status": "success",
  "deleted_count": 523,
  "retention_days": 90
}
```

## Database Schema

```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    user_id TEXT,
    username TEXT,
    ip_address TEXT,
    resource_type TEXT,
    resource_id TEXT,
    action TEXT,
    result TEXT,
    message TEXT,
    metadata TEXT,  -- JSON
    created_at TEXT NOT NULL
);

-- Indexes for efficient queries
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_event_type ON audit_logs(event_type);
CREATE INDEX idx_audit_user ON audit_logs(user_id, username);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
```

## Best Practices

### What to Log

**DO log:**
- Authentication events (login, logout, token creation)
- Authorization decisions (access granted/denied)
- Resource modifications (create, update, delete)
- Configuration changes
- Security-relevant errors
- Administrative actions
- API key usage

**DON'T log:**
- Passwords or sensitive credentials
- Personal data (unless required for compliance)
- High-frequency read operations (unless suspicious)
- Debug information (use standard logging instead)

### Severity Guidelines

- **INFO**: Normal operations (successful login, resource created)
- **WARNING**: Suspicious activity (failed login, access denied, rate limit exceeded)
- **ERROR**: Operation failures (config reload failed, resource creation failed)
- **CRITICAL**: Security incidents (multiple failed logins, unauthorized access attempts)

### Metadata Best Practices

Include relevant context in metadata:

```python
# Good: Structured, searchable metadata
metadata={
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "resource_name": "my-repo",
    "action_details": {"visibility": "private"}
}

# Bad: Unstructured text
metadata={
    "details": "User alice from 192.168.1.100 created repo my-repo"
}
```

### Query Performance

- Use indexed fields for filtering (timestamp, event_type, user_id, username)
- Limit time ranges for large datasets
- Use pagination for large result sets
- Consider archiving old logs to separate storage

### Retention Policy

- **Compliance**: Check regulatory requirements (GDPR, HIPAA, etc.)
- **Storage**: Balance retention period with storage costs
- **Recommended**: 90 days for general logs, 1+ year for security events
- **Automation**: Schedule regular cleanup jobs

## Integration Examples

### Middleware Integration

```python
from fastapi import Request
from pr_agent.audit import get_audit_logger, AuditEventType, AuditSeverity

audit_logger = get_audit_logger()

@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    # Log API access
    if request.url.path.startswith("/api/"):
        user = get_current_user(request)  # Your auth logic
        
        audit_logger.log(
            event_type=AuditEventType.RESOURCE_ACCESSED,
            severity=AuditSeverity.INFO,
            user_id=user.id if user else None,
            username=user.username if user else None,
            ip_address=request.client.host,
            resource_type="api_endpoint",
            resource_id=request.url.path,
            action=request.method,
            metadata={
                "query_params": dict(request.query_params),
                "user_agent": request.headers.get("user-agent")
            }
        )
    
    response = await call_next(request)
    return response
```

### Error Handler Integration

```python
@app.exception_handler(Exception)
async def audit_exception_handler(request: Request, exc: Exception):
    audit_logger.log(
        event_type=AuditEventType.RESOURCE_ACCESSED,
        severity=AuditSeverity.ERROR,
        ip_address=request.client.host,
        resource_type="api_endpoint",
        resource_id=request.url.path,
        action=request.method,
        result="error",
        message=str(exc),
        metadata={
            "exception_type": type(exc).__name__,
            "traceback": traceback.format_exc()
        }
    )
    raise exc
```

## Monitoring and Alerting

### Key Metrics to Monitor

1. **Failed Login Attempts**: Alert on multiple failures from same IP
2. **Access Denied Events**: Monitor for unauthorized access attempts
3. **Critical Events**: Immediate alerts for critical severity
4. **Unusual Activity**: Spike in events from single user/IP
5. **Quota Violations**: Track API abuse patterns

### Example Alert Rules

```python
# Alert on 5+ failed logins in 5 minutes
failed_logins = audit_logger.query(
    event_types=[AuditEventType.LOGIN_FAILURE],
    start_time=datetime.now() - timedelta(minutes=5)
)

if len(failed_logins) >= 5:
    send_alert("Multiple failed login attempts detected")

# Alert on critical events
critical_events = audit_logger.query(
    severity=AuditSeverity.CRITICAL,
    start_time=datetime.now() - timedelta(hours=1)
)

if critical_events:
    send_alert(f"Critical security event: {critical_events[0]['message']}")
```

## Compliance

### GDPR Considerations

- **Right to Access**: Provide users access to their audit logs
- **Right to Erasure**: Implement user data deletion (anonymize logs)
- **Data Minimization**: Only log necessary information
- **Retention Limits**: Define and enforce retention periods

### SOC 2 / ISO 27001

- **Access Logging**: Log all access to sensitive resources
- **Change Tracking**: Audit all configuration and permission changes
- **Incident Response**: Use audit logs for security investigations
- **Regular Reviews**: Periodic audit log analysis

## Troubleshooting

### High Database Size

```bash
# Check database size
ls -lh audit.db

# Cleanup old logs
curl -X POST -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/audit/cleanup?days=30"

# Vacuum database to reclaim space
sqlite3 audit.db "VACUUM;"
```

### Slow Queries

```python
# Use indexed fields
logs = audit_logger.query(
    event_types=[AuditEventType.LOGIN_SUCCESS],  # Indexed
    username="alice",  # Indexed
    start_time=recent_time  # Indexed
)

# Avoid full table scans
# Bad: No filters
logs = audit_logger.query(limit=10000)

# Good: Filtered query
logs = audit_logger.query(
    start_time=datetime.now() - timedelta(days=1),
    limit=100
)
```

### Missing Events

Check that audit logging is enabled:

```python
from pr_agent.audit import get_audit_logger

audit_logger = get_audit_logger()

# Verify logging works
log_id = audit_logger.log(
    event_type=AuditEventType.LOGIN_SUCCESS,
    username="test"
)

print(f"Log ID: {log_id}")  # Should print a number

# Query to verify
logs = audit_logger.query(limit=1)
print(logs)  # Should show the test log
```

## See Also

- [Security Documentation](SECURITY.md)
- [Monitoring Guide](MONITORING.md)
- [API Documentation](API.md)
- [Deployment Guide](DEPLOYMENT.md)
