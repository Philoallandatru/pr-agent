# Health Monitoring System

The health monitoring system provides comprehensive health checks for all system components, enabling proactive monitoring and quick issue detection.

## Overview

The health checker monitors:
- **Database**: Connection status and response time
- **Cache**: Redis availability and performance
- **External Services**: API endpoint availability
- **System Resources**: CPU, memory, and disk usage

All health checks are exposed via REST API endpoints compatible with Kubernetes probes.

## Features

- **Component-Level Checks**: Individual health status for each component
- **Response Time Tracking**: Measure performance of each component
- **Kubernetes Integration**: Ready/live probes for orchestration
- **Async Execution**: Non-blocking health checks
- **Configurable Thresholds**: Customize warning/error levels
- **Detailed Status**: Rich diagnostic information

## Health Status Levels

- `healthy`: Component is functioning normally
- `degraded`: Component is working but with issues (e.g., high latency)
- `unhealthy`: Component is not functioning

## Configuration

Add to `configuration.toml`:

```toml
[health]
# Enable health checks (default: true)
enabled = true

# Database health check timeout (seconds)
db_timeout = 5.0

# Cache health check timeout (seconds)
cache_timeout = 3.0

# External service timeout (seconds)
external_timeout = 10.0

# System resource thresholds
cpu_warning_threshold = 80.0      # CPU usage % warning
cpu_critical_threshold = 95.0     # CPU usage % critical
memory_warning_threshold = 85.0   # Memory usage % warning
memory_critical_threshold = 95.0  # Memory usage % critical
disk_warning_threshold = 85.0     # Disk usage % warning
disk_critical_threshold = 95.0    # Disk usage % critical

# External services to monitor
[[health.external_services]]
name = "github_api"
url = "https://api.github.com"
method = "GET"
timeout = 5.0

[[health.external_services]]
name = "bitbucket_server"
url = "https://bitbucket.example.com/rest/api/1.0/application-properties"
method = "GET"
timeout = 5.0
```

## API Endpoints

### Full Health Check

```bash
GET /api/health

Returns comprehensive health status of all components.

Example:
curl http://localhost:8000/api/health

Response:
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "components": {
    "database": {
      "status": "healthy",
      "response_time_ms": 5.2,
      "message": "Database connection successful",
      "details": {
        "tables": 15,
        "size_mb": 234.5
      }
    },
    "cache": {
      "status": "healthy",
      "response_time_ms": 1.8,
      "message": "Cache operational",
      "details": {
        "keys": 1523,
        "memory_mb": 45.2
      }
    },
    "external_services": {
      "status": "healthy",
      "message": "All external services reachable",
      "details": {
        "github_api": {
          "status": "healthy",
          "response_time_ms": 123.4
        },
        "bitbucket_server": {
          "status": "healthy",
          "response_time_ms": 89.2
        }
      }
    },
    "system": {
      "status": "healthy",
      "message": "System resources within normal range",
      "details": {
        "cpu_percent": 45.2,
        "memory_percent": 62.1,
        "disk_percent": 38.5
      }
    }
  }
}
```

### Readiness Probe

```bash
GET /api/health/ready

Kubernetes readiness probe - checks if service is ready to accept traffic.

Returns 200 if ready, 503 if not ready.

Example:
curl http://localhost:8000/api/health/ready

Response (ready):
{
  "status": "ready",
  "timestamp": "2024-01-15T10:30:00Z"
}

Response (not ready):
{
  "status": "not_ready",
  "timestamp": "2024-01-15T10:30:00Z",
  "reason": "Database connection failed"
}
```

### Liveness Probe

```bash
GET /api/health/live

Kubernetes liveness probe - checks if service is alive.

Returns 200 if alive, 503 if dead.

Example:
curl http://localhost:8000/api/health/live

Response:
{
  "status": "alive",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Python API

```python
from pr_agent.health import HealthChecker
from pr_agent.storage.database import DatabaseManager
from pr_agent.settings.configuration import get_settings

# Initialize health checker
settings = get_settings()
db = DatabaseManager(settings.config.get("database", {}).get("path", "pr_agent.db"))

health_checker = HealthChecker(
    db_manager=db,
    config=settings.config
)

# Run all health checks
health_status = await health_checker.check_all()

print(f"Overall status: {health_status['status']}")
print(f"Database: {health_status['components']['database']['status']}")
print(f"Cache: {health_status['components']['cache']['status']}")

# Check individual components
db_health = await health_checker.check_database()
print(f"Database status: {db_health.status}")
print(f"Response time: {db_health.response_time_ms}ms")

cache_health = await health_checker.check_cache()
print(f"Cache status: {cache_health.status}")

system_health = health_checker.check_system_resources()
print(f"CPU: {system_health.details['cpu_percent']}%")
print(f"Memory: {system_health.details['memory_percent']}%")
print(f"Disk: {system_health.details['disk_percent']}%")

# Check readiness
is_ready = health_checker.get_readiness()
print(f"Service ready: {is_ready['status'] == 'ready'}")

# Check liveness
is_alive = health_checker.get_liveness()
print(f"Service alive: {is_alive['status'] == 'alive'}")
```

## Kubernetes Integration

### Deployment Configuration

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pr-agent
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: pr-agent
        image: pr-agent:latest
        ports:
        - containerPort: 8000
        
        # Readiness probe - checks if pod is ready to serve traffic
        readinessProbe:
          httpGet:
            path: /api/health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          successThreshold: 1
          failureThreshold: 3
        
        # Liveness probe - checks if pod is alive
        livenessProbe:
          httpGet:
            path: /api/health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          successThreshold: 1
          failureThreshold: 3
        
        # Startup probe - checks if application has started
        startupProbe:
          httpGet:
            path: /api/health/live
            port: 8000
          initialDelaySeconds: 0
          periodSeconds: 5
          timeoutSeconds: 3
          successThreshold: 1
          failureThreshold: 30
```

### Service Configuration

```yaml
apiVersion: v1
kind: Service
metadata:
  name: pr-agent
spec:
  selector:
    app: pr-agent
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

## Monitoring Integration

### Prometheus Metrics

Health check results are automatically exported as Prometheus metrics:

```prometheus
# Health check status (1 = healthy, 0 = unhealthy)
health_check_status{component="database"} 1
health_check_status{component="cache"} 1
health_check_status{component="system"} 1

# Response times (milliseconds)
health_check_response_time_ms{component="database"} 5.2
health_check_response_time_ms{component="cache"} 1.8

# System resources
system_cpu_percent 45.2
system_memory_percent 62.1
system_disk_percent 38.5
```

### Grafana Dashboard

Example Grafana queries:

```promql
# Overall health status
sum(health_check_status)

# Database response time
health_check_response_time_ms{component="database"}

# CPU usage over time
system_cpu_percent

# Memory usage alert
system_memory_percent > 85
```

## Alerting Rules

### Prometheus Alert Rules

```yaml
groups:
- name: health_checks
  interval: 30s
  rules:
  
  # Component unhealthy
  - alert: ComponentUnhealthy
    expr: health_check_status == 0
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "Component {{ $labels.component }} is unhealthy"
      description: "{{ $labels.component }} has been unhealthy for 2 minutes"
  
  # High response time
  - alert: HighResponseTime
    expr: health_check_response_time_ms > 1000
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High response time for {{ $labels.component }}"
      description: "{{ $labels.component }} response time is {{ $value }}ms"
  
  # High CPU usage
  - alert: HighCPUUsage
    expr: system_cpu_percent > 80
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High CPU usage"
      description: "CPU usage is {{ $value }}%"
  
  # High memory usage
  - alert: HighMemoryUsage
    expr: system_memory_percent > 85
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage"
      description: "Memory usage is {{ $value }}%"
  
  # Critical disk usage
  - alert: CriticalDiskUsage
    expr: system_disk_percent > 90
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "Critical disk usage"
      description: "Disk usage is {{ $value }}%"
```

## Best Practices

### Health Check Design

1. **Fast Checks**: Keep health checks under 5 seconds
2. **Lightweight**: Avoid expensive operations in health checks
3. **Idempotent**: Health checks should not modify state
4. **Informative**: Include diagnostic details in responses
5. **Graceful Degradation**: Return partial health if some components fail

### Probe Configuration

1. **Readiness vs Liveness**:
   - Readiness: Can service handle requests? (database connected, cache available)
   - Liveness: Is service alive? (process running, not deadlocked)

2. **Timing**:
   - `initialDelaySeconds`: Wait for app to start (10-30s)
   - `periodSeconds`: Check frequency (5-10s for readiness, 10-30s for liveness)
   - `timeoutSeconds`: Max check duration (3-5s)
   - `failureThreshold`: Failures before marking unhealthy (3-5)

3. **Startup Probe**:
   - Use for slow-starting applications
   - Prevents premature liveness failures during startup

### Monitoring Strategy

1. **Alert on Trends**: Don't alert on single failures, wait for patterns
2. **Escalation**: Warning → Critical based on duration and severity
3. **Context**: Include component details in alerts
4. **Actionable**: Alerts should suggest remediation steps

## Troubleshooting

### Database Health Check Fails

```bash
# Check database connection
sqlite3 pr_agent.db "SELECT 1;"

# Check database file permissions
ls -la pr_agent.db

# Check database locks
lsof pr_agent.db

# Verify database schema
sqlite3 pr_agent.db ".schema"
```

### Cache Health Check Fails

```bash
# Check Redis connection
redis-cli ping

# Check Redis memory
redis-cli info memory

# Check Redis keys
redis-cli dbsize

# Test cache operations
redis-cli SET test_key test_value
redis-cli GET test_key
```

### High Response Times

```python
# Enable detailed timing
import time

start = time.time()
health = await health_checker.check_database()
duration = (time.time() - start) * 1000
print(f"Database check took {duration}ms")

# Check for slow queries
# Review database query performance
# Consider adding indexes
```

### System Resource Issues

```bash
# Check CPU usage
top -bn1 | grep "Cpu(s)"

# Check memory usage
free -h

# Check disk usage
df -h

# Check process resources
ps aux | grep pr-agent

# Check for memory leaks
# Monitor memory usage over time
watch -n 5 'ps aux | grep pr-agent'
```

## Advanced Usage

### Custom Health Checks

```python
from pr_agent.health import HealthChecker, ComponentHealth, HealthStatus

class CustomHealthChecker(HealthChecker):
    async def check_custom_service(self) -> ComponentHealth:
        """Check custom service health"""
        try:
            # Your custom check logic
            response = await custom_service.ping()
            
            return ComponentHealth(
                name="custom_service",
                status=HealthStatus.HEALTHY,
                message="Custom service operational",
                details={"version": response.version},
                response_time_ms=response.time
            )
        except Exception as e:
            return ComponentHealth(
                name="custom_service",
                status=HealthStatus.UNHEALTHY,
                message=f"Custom service check failed: {str(e)}"
            )
    
    async def check_all(self):
        """Override to include custom checks"""
        result = await super().check_all()
        
        # Add custom check
        custom_health = await self.check_custom_service()
        result["components"]["custom_service"] = custom_health.to_dict()
        
        # Update overall status if custom check fails
        if custom_health.status == HealthStatus.UNHEALTHY:
            result["status"] = "unhealthy"
        
        return result
```

### Health Check Middleware

```python
from fastapi import Request, Response
from pr_agent.health import get_health_checker

@app.middleware("http")
async def health_check_middleware(request: Request, call_next):
    # Skip health checks for health endpoints
    if request.url.path.startswith("/api/health"):
        return await call_next(request)
    
    # Check if service is ready
    health_checker = get_health_checker()
    readiness = health_checker.get_readiness()
    
    if readiness["status"] != "ready":
        return Response(
            content="Service not ready",
            status_code=503,
            headers={"Retry-After": "30"}
        )
    
    return await call_next(request)
```

## See Also

- [Monitoring Guide](MONITORING.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Configuration Hot Reload](HOT_RELOAD.md)
- [Performance Optimization](PERFORMANCE.md)
