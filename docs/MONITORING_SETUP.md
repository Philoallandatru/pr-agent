# Monitoring Setup Guide

This guide explains how to set up comprehensive monitoring for PR Agent using Prometheus and Grafana.

## Overview

The monitoring stack includes:
- **Prometheus**: Metrics collection and storage
- **Grafana**: Visualization and dashboards
- **Alertmanager**: Alert routing and notifications
- **Node Exporter**: System-level metrics

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Grafana (Port 3000)                  │
│              Dashboards & Visualization                 │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    ┌────▼─────┐          ┌─────▼────────┐
    │Prometheus│          │ Alertmanager │
    │(Port 9090│          │  (Port 9093) │
    └────┬─────┘          └──────────────┘
         │
    ┌────▼──────────────────────────────┐
    │         Scrape Targets            │
    ├───────────────────────────────────┤
    │ - PR Agent Web (metrics endpoint) │
    │ - PR Agent Poller                 │
    │ - Redis Exporter                  │
    │ - Node Exporter                   │
    │ - Kubernetes API                  │
    └───────────────────────────────────┘
```

## Quick Start

### 1. Deploy Monitoring Stack on Kubernetes

```bash
# Create monitoring namespace
kubectl create namespace monitoring

# Deploy Prometheus
kubectl apply -f monitoring/k8s/prometheus/

# Deploy Grafana
kubectl apply -f monitoring/k8s/grafana/

# Deploy Alertmanager (optional)
kubectl apply -f monitoring/k8s/alertmanager/
```

### 2. Access Grafana

```bash
# Port forward to access Grafana
kubectl port-forward -n monitoring svc/grafana 3000:3000

# Open browser to http://localhost:3000
# Default credentials: admin / admin (change on first login)
```

### 3. Import Dashboards

Dashboards are automatically provisioned from `monitoring/grafana/dashboards/`:
- **PR Agent Overview**: Main dashboard with key metrics
- **Performance**: Detailed performance metrics
- **Resources**: CPU, memory, disk usage
- **Alerts**: Active alerts and alert history

## Prometheus Configuration

### Scrape Configuration

Prometheus is configured to scrape metrics from:

**PR Agent Web Application**:
- Endpoint: `/metrics`
- Port: 9090
- Interval: 15s

**PR Agent Poller**:
- Endpoint: `/metrics`
- Port: 9090
- Interval: 15s

**Redis**:
- Exporter: redis_exporter
- Port: 9121
- Interval: 15s

**Kubernetes**:
- API Server, Nodes, Pods
- Service discovery enabled

### Retention

Default retention: 15 days

To change retention:
```yaml
# Edit prometheus deployment
args:
- '--storage.tsdb.retention.time=30d'
- '--storage.tsdb.retention.size=50GB'
```

## Available Metrics

### HTTP Metrics

```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Response time (P95)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Request by endpoint
sum by (endpoint) (rate(http_requests_total[5m]))
```

### PR Review Metrics

```promql
# Total reviews
sum(pr_reviews_total)

# Review rate
rate(pr_reviews_total[5m])

# Success rate
rate(pr_reviews_total{status="success"}[5m]) / rate(pr_reviews_total[5m])

# Average review duration
rate(pr_review_duration_seconds_sum[5m]) / rate(pr_review_duration_seconds_count[5m])
```

### Cache Metrics

```promql
# Cache hit rate
rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m]))

# Cache operations
rate(cache_operations_total[5m])

# Cache size
cache_size_bytes
```

### Database Metrics

```promql
# Query duration (P95)
histogram_quantile(0.95, rate(db_query_duration_seconds_bucket[5m]))

# Query rate
rate(db_queries_total[5m])

# Error rate
rate(db_errors_total[5m])

# Connection pool usage
db_connections_active / db_connections_max
```

### System Metrics

```promql
# CPU usage
rate(container_cpu_usage_seconds_total{pod=~"pr-agent.*"}[5m]) * 100

# Memory usage
container_memory_usage_bytes{pod=~"pr-agent.*"}

# Disk usage
(node_filesystem_size_bytes - node_filesystem_avail_bytes) / node_filesystem_size_bytes
```

## Alerts

### Critical Alerts

**Service Down**:
```yaml
alert: PRAgentDown
expr: up{job="pr-agent-web"} == 0
for: 2m
```

**High Error Rate**:
```yaml
alert: CriticalErrorRate
expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
for: 2m
```

**Very High Response Time**:
```yaml
alert: VeryHighResponseTime
expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 5
for: 2m
```

### Warning Alerts

**High Memory Usage**:
```yaml
alert: HighMemoryUsage
expr: container_memory_usage_bytes / container_spec_memory_limit_bytes > 0.9
for: 5m
```

**Low Cache Hit Rate**:
```yaml
alert: LowCacheHitRate
expr: rate(cache_hits_total[10m]) / (rate(cache_hits_total[10m]) + rate(cache_misses_total[10m])) < 0.7
for: 10m
```

**Slow Database Queries**:
```yaml
alert: SlowDatabaseQueries
expr: histogram_quantile(0.95, rate(db_query_duration_seconds_bucket[5m])) > 1
for: 5m
```

## Alertmanager Configuration

### Slack Integration

```yaml
receivers:
- name: 'slack'
  slack_configs:
  - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
    channel: '#pr-agent-alerts'
    title: '{{ .GroupLabels.alertname }}'
    text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

### Email Integration

```yaml
receivers:
- name: 'email'
  email_configs:
  - to: 'ops-team@example.com'
    from: 'alertmanager@example.com'
    smarthost: 'smtp.example.com:587'
    auth_username: 'alertmanager'
    auth_password: 'password'
```

### PagerDuty Integration

```yaml
receivers:
- name: 'pagerduty'
  pagerduty_configs:
  - service_key: 'YOUR_PAGERDUTY_SERVICE_KEY'
    description: '{{ .GroupLabels.alertname }}'
```

## Grafana Dashboards

### Overview Dashboard

Key panels:
- Service status (up/down)
- HTTP request rate
- P95 response time
- Total PR reviews
- CPU and memory usage
- Error rate
- Cache hit rate
- Database query duration

### Performance Dashboard

Detailed metrics:
- Request latency percentiles (P50, P95, P99)
- Throughput by endpoint
- Error breakdown by status code
- Slow query analysis
- Token usage rate

### Resources Dashboard

System metrics:
- CPU usage per pod
- Memory usage per pod
- Disk I/O
- Network traffic
- Pod restart count

### Alerts Dashboard

Alert management:
- Active alerts
- Alert history
- Alert frequency
- Time to resolution

## Custom Metrics

### Adding Custom Metrics

In your Python code:

```python
from pr_agent.monitoring import MetricsCollector

metrics = MetricsCollector()

# Counter
metrics.increment_counter('custom_events_total', labels={'type': 'example'})

# Gauge
metrics.set_gauge('custom_queue_size', 42)

# Histogram
with metrics.track_performance('custom_operation'):
    # Your code here
    pass
```

### Querying Custom Metrics

```promql
# Counter
rate(custom_events_total[5m])

# Gauge
custom_queue_size

# Histogram
histogram_quantile(0.95, rate(custom_operation_duration_seconds_bucket[5m]))
```

## Troubleshooting

### Prometheus Not Scraping Targets

```bash
# Check Prometheus targets
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# Open http://localhost:9090/targets

# Check service discovery
# Open http://localhost:9090/service-discovery

# Verify metrics endpoint
kubectl exec -it <pr-agent-pod> -n pr-agent -- curl localhost:9090/metrics
```

### Grafana Not Showing Data

```bash
# Check Grafana logs
kubectl logs -n monitoring deployment/grafana

# Test Prometheus datasource
# Grafana UI -> Configuration -> Data Sources -> Prometheus -> Test

# Verify Prometheus is accessible
kubectl exec -it -n monitoring deployment/grafana -- \
  curl http://prometheus:9090/api/v1/query?query=up
```

### High Cardinality Issues

If Prometheus is using too much memory:

```yaml
# Limit label values
metric_relabel_configs:
- source_labels: [__name__]
  regex: 'high_cardinality_metric.*'
  action: drop

# Reduce retention
args:
- '--storage.tsdb.retention.time=7d'
```

### Missing Metrics

```bash
# Check if metrics are being exported
kubectl exec -it <pr-agent-pod> -n pr-agent -- \
  curl localhost:9090/metrics | grep metric_name

# Check Prometheus scrape errors
# Prometheus UI -> Status -> Targets -> Show errors

# Verify service annotations
kubectl get svc pr-agent -n pr-agent -o yaml | grep prometheus
```

## Best Practices

1. **Set Appropriate Retention**: Balance storage costs with data needs
2. **Use Recording Rules**: Pre-compute expensive queries
3. **Label Wisely**: Avoid high cardinality labels
4. **Alert on Symptoms**: Alert on user-facing issues, not causes
5. **Dashboard Organization**: Group related metrics together
6. **Regular Review**: Review and update dashboards and alerts
7. **Document Metrics**: Add descriptions to custom metrics
8. **Test Alerts**: Regularly test alert routing
9. **Monitor the Monitors**: Set up meta-monitoring
10. **Backup Configuration**: Version control Prometheus/Grafana configs

## Recording Rules

Pre-compute expensive queries:

```yaml
groups:
- name: pr_agent_rules
  interval: 30s
  rules:
  - record: job:http_requests:rate5m
    expr: rate(http_requests_total[5m])
  
  - record: job:http_errors:rate5m
    expr: rate(http_requests_total{status=~"5.."}[5m])
  
  - record: job:cache_hit_rate:rate5m
    expr: rate(cache_hits_total[5m]) / (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m]))
```

## Performance Tuning

### Prometheus

```yaml
# Increase memory
resources:
  limits:
    memory: 4Gi

# Tune scrape settings
global:
  scrape_interval: 30s  # Reduce frequency
  scrape_timeout: 10s

# Enable compression
remote_write:
- url: http://remote-storage:9090/api/v1/write
  queue_config:
    capacity: 10000
    max_shards: 50
```

### Grafana

```yaml
# Enable caching
[caching]
enabled = true

# Increase query timeout
[dataproxy]
timeout = 300

# Optimize database
[database]
max_open_conn = 100
max_idle_conn = 50
```

## See Also

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PR Agent Metrics Reference](./METRICS.md)
- [Alert Runbooks](./RUNBOOKS.md)
