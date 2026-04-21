# Monitoring and Observability

This document describes the monitoring and observability features of PR-Agent auto-review system.

## Overview

The monitoring system provides:
- **Prometheus metrics** for time-series monitoring
- **Structured logging** with context
- **Performance tracking** for operations
- **Health checks** for system status
- **System metrics** (CPU, memory, disk)

## Features

### 1. Prometheus Metrics

Export metrics in Prometheus format for monitoring and alerting.

**Available Metrics:**

```
# HTTP Requests
pr_agent_http_requests_total{method, endpoint, status}
pr_agent_http_request_duration_seconds{method, endpoint}

# PR Reviews
pr_agent_reviews_total{repository, status}
pr_agent_review_duration_seconds{repository}

# Polling
pr_agent_polling_cycles_total{repository}
pr_agent_polling_errors_total{repository, error_type}

# System
pr_agent_active_reviews
pr_agent_cache_size_bytes{cache_type}
pr_agent_app_info
```

**Metrics Endpoint:**

```bash
curl http://localhost:8000/metrics
```

### 2. Structured Logging

All logs include contextual information for better debugging.

**Example Log Entry:**

```json
{
  "timestamp": "2024-04-21T10:30:45Z",
  "level": "INFO",
  "message": "PR processed successfully",
  "pr_url": "https://bitbucket.example.com/projects/PROJ/repos/api/pull-requests/123",
  "repository": "PROJ/api",
  "duration": "45.23s"
}
```

**Usage in Code:**

```python
from pr_agent.monitoring.metrics import StructuredLogger

logger = StructuredLogger(__name__)

# Set context for all logs
logger.set_context(repository="PROJ/api", pr_id=123)

# Log with additional fields
logger.info("Processing PR", author="john.doe", files_changed=15)

# Clear context
logger.clear_context()
```

### 3. Performance Tracking

Track operation performance with automatic timing.

**Using Decorator:**

```python
from pr_agent.monitoring.metrics import track_performance

@track_performance("clone_repository", labels={"repo": "PROJ/api"})
def clone_repo(url):
    # Your code here
    pass
```

**Using Context Manager:**

```python
from pr_agent.monitoring.metrics import PerformanceTracker

with PerformanceTracker("analyze_dependencies") as tracker:
    tracker.add_metadata(language="python", files=25)
    # Your code here
    pass

print(f"Duration: {tracker.duration}s")
```

### 4. Health Checks

Comprehensive health check endpoint for monitoring system status.

**Endpoint:**

```bash
curl http://localhost:8000/api/health
```

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2024-04-21T10:30:45Z",
  "checks": {
    "database": "ok",
    "bitbucket_connection": "ok",
    "tokenizer_cache": "ok",
    "disk_space": "ok"
  },
  "details": {
    "database_size_mb": 125.5,
    "cache_size_mb": 450.2,
    "disk_free_gb": 50.3
  }
}
```

### 5. System Metrics

Get current system resource usage.

**Endpoint:**

```bash
curl http://localhost:8000/api/metrics
```

**Response:**

```json
{
  "repositories": 5,
  "total_reviews": 1234,
  "reviews_today": 45,
  "system": {
    "cpu_percent": 25.5,
    "memory_percent": 45.2,
    "memory_available_mb": 8192,
    "disk_percent": 60.5,
    "disk_free_gb": 50.3,
    "timestamp": "2024-04-21T10:30:45Z"
  }
}
```

## Integration

### Prometheus Integration

**1. Install Prometheus Client:**

```bash
pip install prometheus-client
```

**2. Configure Prometheus:**

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'pr-agent'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

**3. Start Prometheus:**

```bash
prometheus --config.file=prometheus.yml
```

**4. Access Metrics:**

- Prometheus UI: http://localhost:9090
- Query metrics: `pr_agent_reviews_total`

### Grafana Dashboards

**Example Queries:**

```promql
# Request rate
rate(pr_agent_http_requests_total[5m])

# Average review duration
rate(pr_agent_review_duration_seconds_sum[5m]) / rate(pr_agent_review_duration_seconds_count[5m])

# Error rate
rate(pr_agent_reviews_total{status="error"}[5m])

# Active reviews
pr_agent_active_reviews
```

**Dashboard Panels:**

1. **Request Rate** - Line chart of HTTP requests/sec
2. **Review Duration** - Histogram of review processing time
3. **Error Rate** - Line chart of errors/sec
4. **Active Reviews** - Gauge of current active reviews
5. **System Resources** - CPU, memory, disk usage

### Alerting

**Example Prometheus Alerts:**

```yaml
groups:
  - name: pr_agent_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(pr_agent_reviews_total{status="error"}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High PR review error rate"
          description: "Error rate is {{ $value }} errors/sec"

      - alert: SlowReviews
        expr: rate(pr_agent_review_duration_seconds_sum[5m]) / rate(pr_agent_review_duration_seconds_count[5m]) > 300
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "PR reviews are slow"
          description: "Average review time is {{ $value }}s"

      - alert: HighMemoryUsage
        expr: pr_agent_system_memory_percent > 90
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value }}%"
```

## Configuration

Add to `configuration.toml`:

```toml
[monitoring]
enable_prometheus = true
enable_structured_logging = true
log_level = "INFO"
metrics_port = 8000

[monitoring.health_checks]
check_interval_seconds = 60
disk_space_threshold_gb = 10
memory_threshold_percent = 90
```

## Best Practices

### 1. Metric Naming

- Use `pr_agent_` prefix for all metrics
- Use snake_case for metric names
- Include units in metric names (e.g., `_seconds`, `_bytes`)

### 2. Label Cardinality

- Keep label cardinality low (< 1000 unique values)
- Avoid high-cardinality labels (e.g., PR IDs, timestamps)
- Use aggregation for high-cardinality data

### 3. Logging

- Use structured logging for all application logs
- Include context (repository, PR ID, user)
- Log at appropriate levels (DEBUG, INFO, WARNING, ERROR)
- Avoid logging sensitive data (tokens, passwords)

### 4. Performance Tracking

- Track critical operations (PR review, repository cloning)
- Set reasonable timeout thresholds
- Monitor p50, p95, p99 latencies

### 5. Alerting

- Alert on symptoms, not causes
- Set appropriate thresholds and durations
- Include actionable information in alerts
- Test alerts regularly

## Troubleshooting

### Metrics Not Appearing

**Check Prometheus client:**

```bash
pip list | grep prometheus
```

**Verify metrics endpoint:**

```bash
curl http://localhost:8000/metrics
```

### High Memory Usage

**Check cache sizes:**

```bash
curl http://localhost:8000/api/metrics | jq '.system'
```

**Clear caches:**

```bash
python -m pr_agent.cli.auto_review config --clear-cache
```

### Slow Reviews

**Check review duration:**

```promql
histogram_quantile(0.95, rate(pr_agent_review_duration_seconds_bucket[5m]))
```

**Optimize:**
- Reduce `max_related_files` in repo context
- Decrease `max_context_tokens`
- Enable caching

## Examples

### Custom Metrics

```python
from pr_agent.monitoring.metrics import metrics

# Track custom operation
start_time = time.time()
# ... your code ...
duration = time.time() - start_time

metrics.track_pr_review(
    repository="PROJ/api",
    status="success",
    duration=duration
)
```

### Custom Health Check

```python
from pr_agent.config.validation import HealthChecker

checker = HealthChecker()

# Add custom check
def check_external_api():
    try:
        response = requests.get("https://api.example.com/health")
        return response.status_code == 200
    except:
        return False

checker.add_check("external_api", check_external_api)

# Run all checks
health_report = checker.check_all()
```

## Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Structured Logging Best Practices](https://www.structlog.org/)
