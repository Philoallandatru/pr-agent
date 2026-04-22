# Kubernetes Deployment Guide

This guide provides comprehensive instructions for deploying PR Agent Auto-Review on Kubernetes.

## Overview

The Kubernetes deployment includes:
- **Web Application**: FastAPI backend with 3 replicas (auto-scaling)
- **Poller Service**: Bitbucket Server polling service (1 replica)
- **Redis**: Cache backend (StatefulSet)
- **Persistent Storage**: Data, tokenizers, and repository cache
- **Ingress**: NGINX ingress with TLS
- **Monitoring**: Prometheus metrics endpoints
- **Auto-scaling**: HPA based on CPU/memory

## Prerequisites

- Kubernetes cluster (v1.24+)
- kubectl configured
- kustomize (v4.0+)
- NGINX Ingress Controller
- cert-manager (for TLS certificates)
- Persistent volume provisioner

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Ingress (NGINX)                      │
│              pr-agent.example.com (TLS)                 │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
    ┌────▼─────┐          ┌─────▼────┐
    │ Service  │          │ Service  │
    │ (Web)    │          │ (Redis)  │
    └────┬─────┘          └─────┬────┘
         │                      │
    ┌────▼─────────────┐   ┌────▼──────┐
    │  Deployment      │   │StatefulSet│
    │  (Web x3)        │   │(Redis x1) │
    │  + HPA           │   └───────────┘
    └──────────────────┘
         │
    ┌────▼─────────────┐
    │  Deployment      │
    │  (Poller x1)     │
    └──────────────────┘
         │
    ┌────▼─────────────┐
    │  PVC (3 volumes) │
    │  - data (10Gi)   │
    │  - tokenizers(5) │
    │  - repos (50Gi)  │
    └──────────────────┘
```

## Directory Structure

```
k8s/
├── base/                      # Base Kubernetes manifests
│   ├── namespace.yaml         # Namespace definition
│   ├── configmap.yaml         # Application configuration
│   ├── secret.yaml            # Secrets (credentials)
│   ├── rbac.yaml              # Service account and RBAC
│   ├── pvc.yaml               # Persistent volume claims
│   ├── deployment.yaml        # Web and poller deployments
│   ├── service.yaml           # Services
│   ├── ingress.yaml           # Ingress configuration
│   ├── hpa.yaml               # Horizontal Pod Autoscaler
│   ├── redis.yaml             # Redis StatefulSet
│   └── kustomization.yaml     # Kustomize base
└── overlays/                  # Environment-specific overlays
    ├── dev/                   # Development environment
    │   └── kustomization.yaml
    ├── staging/               # Staging environment
    │   └── kustomization.yaml
    └── production/            # Production environment
        └── kustomization.yaml
```

## Quick Start

### 1. Configure Secrets

Edit `k8s/base/secret.yaml` and update the following values:

```yaml
stringData:
  BITBUCKET_TOKEN: "your-bitbucket-token"
  PR_AGENT_SECRET_KEY: "your-jwt-secret-key-min-32-chars"
  PR_AGENT_ADMIN_PASSWORD: "your-secure-admin-password"
  REDIS_PASSWORD: "your-redis-password"
  DB_ENCRYPTION_KEY: "your-encryption-key-32-chars"
```

**Security Note**: In production, use Kubernetes secrets management tools like:
- Sealed Secrets
- External Secrets Operator
- HashiCorp Vault
- AWS Secrets Manager / Azure Key Vault / GCP Secret Manager

### 2. Update Configuration

Edit `k8s/base/configmap.yaml` to customize application settings:

```toml
[bitbucket_server]
url = "https://bitbucket.your-company.com"
polling_repositories = ["PROJECT/repo1", "PROJECT/repo2"]

[webhook]
slack_url = "https://hooks.slack.com/services/..."
```

### 3. Update Ingress Host

Edit `k8s/base/ingress.yaml` and replace `pr-agent.example.com` with your domain:

```yaml
spec:
  tls:
  - hosts:
    - pr-agent.your-company.com
    secretName: pr-agent-tls
  rules:
  - host: pr-agent.your-company.com
```

### 4. Deploy to Development

```bash
# Apply development configuration
kubectl apply -k k8s/overlays/dev

# Verify deployment
kubectl get pods -n pr-agent-dev
kubectl get svc -n pr-agent-dev
kubectl get ingress -n pr-agent-dev

# Check logs
kubectl logs -n pr-agent-dev -l app=pr-agent,component=web -f
```

### 5. Deploy to Staging

```bash
# Apply staging configuration
kubectl apply -k k8s/overlays/staging

# Verify deployment
kubectl get pods -n pr-agent-staging
```

### 6. Deploy to Production

```bash
# Apply production configuration
kubectl apply -k k8s/overlays/production

# Verify deployment
kubectl get pods -n pr-agent
kubectl get hpa -n pr-agent
```

## Configuration Details

### Resource Requests and Limits

**Web Application (per pod)**:
- Requests: 500m CPU, 1Gi memory
- Limits: 2000m CPU, 4Gi memory

**Poller Service**:
- Requests: 200m CPU, 512Mi memory
- Limits: 1000m CPU, 2Gi memory

**Redis**:
- Requests: 100m CPU, 256Mi memory
- Limits: 500m CPU, 1Gi memory

### Auto-scaling Configuration

The HPA scales based on:
- CPU utilization: 70% threshold
- Memory utilization: 80% threshold

**Scaling behavior**:
- Min replicas: 3 (production), 2 (staging), 1 (dev)
- Max replicas: 10 (production), 5 (staging), 3 (dev)
- Scale up: Fast (100% or 2 pods per 30s)
- Scale down: Gradual (50% or 1 pod per 60s, 5min stabilization)

### Persistent Storage

Three PVCs are created:
1. **pr-agent-data** (10Gi): Database and application data
2. **pr-agent-tokenizers** (5Gi): Cached tokenizer models
3. **pr-agent-repos** (50Gi): Cloned repository cache

**Storage Class**: `standard` (change to your preferred storage class)

**Access Mode**: `ReadWriteMany` (required for multi-pod access)

### Health Checks

**Liveness Probe**:
- Endpoint: `/api/health/liveness`
- Initial delay: 30s
- Period: 10s
- Timeout: 5s
- Failure threshold: 3

**Readiness Probe**:
- Endpoint: `/api/health/readiness`
- Initial delay: 10s
- Period: 5s
- Timeout: 3s
- Failure threshold: 3

**Startup Probe**:
- Endpoint: `/api/health/liveness`
- Initial delay: 0s
- Period: 5s
- Timeout: 3s
- Failure threshold: 30 (max 150s startup time)

## Advanced Configuration

### Using External Redis

To use an external Redis instance instead of the StatefulSet:

1. Remove Redis from deployment:
```bash
# Edit k8s/base/kustomization.yaml
# Remove: - redis.yaml
```

2. Update ConfigMap:
```yaml
[cache]
redis_host = "redis.external.com"
redis_port = 6379
```

3. Update Secret with Redis password

### Using External Database

To use PostgreSQL instead of SQLite:

1. Update ConfigMap:
```yaml
[database]
type = "postgresql"
host = "postgres.external.com"
port = 5432
database = "pr_agent"
```

2. Add database credentials to Secret:
```yaml
DB_USER: "pr_agent"
DB_PASSWORD: "secure-password"
```

### TLS Certificate Management

**Using cert-manager** (recommended):

The Ingress is already configured with cert-manager annotation:
```yaml
annotations:
  cert-manager.io/cluster-issuer: "letsencrypt-prod"
```

Ensure you have a ClusterIssuer configured:
```bash
kubectl get clusterissuer letsencrypt-prod
```

**Using manual certificates**:

1. Create TLS secret:
```bash
kubectl create secret tls pr-agent-tls \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key \
  -n pr-agent
```

2. Remove cert-manager annotation from Ingress

### Custom Storage Class

To use a different storage class:

1. Edit `k8s/base/pvc.yaml`:
```yaml
spec:
  storageClassName: fast-ssd  # Your storage class
```

2. For Redis StatefulSet, edit `k8s/base/redis.yaml`:
```yaml
volumeClaimTemplates:
- spec:
    storageClassName: fast-ssd
```

## Monitoring

### Prometheus Integration

The deployment exposes Prometheus metrics on port 9090:

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "9090"
  prometheus.io/path: "/metrics"
```

**ServiceMonitor** (if using Prometheus Operator):

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: pr-agent
  namespace: pr-agent
spec:
  selector:
    matchLabels:
      app: pr-agent
  endpoints:
  - port: metrics
    interval: 30s
```

### Grafana Dashboards

Import the pre-configured dashboard from `monitoring/grafana/dashboard.json`.

Key metrics:
- HTTP request rate and latency
- PR review statistics
- Cache hit rate
- System resources (CPU, memory, disk)
- Error rates

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl get pods -n pr-agent

# Describe pod for events
kubectl describe pod <pod-name> -n pr-agent

# Check logs
kubectl logs <pod-name> -n pr-agent

# Check init container logs
kubectl logs <pod-name> -n pr-agent -c init-db
```

### Database Migration Issues

```bash
# Run migration manually
kubectl exec -it <pod-name> -n pr-agent -- \
  python -m pr_agent.storage.migration migrate

# Check migration status
kubectl exec -it <pod-name> -n pr-agent -- \
  python -m pr_agent.storage.migration status
```

### PVC Not Binding

```bash
# Check PVC status
kubectl get pvc -n pr-agent

# Describe PVC for events
kubectl describe pvc pr-agent-data -n pr-agent

# Check available PVs
kubectl get pv

# Check storage class
kubectl get storageclass
```

### Ingress Not Working

```bash
# Check ingress status
kubectl get ingress -n pr-agent

# Describe ingress
kubectl describe ingress pr-agent -n pr-agent

# Check ingress controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller

# Test service directly
kubectl port-forward -n pr-agent svc/pr-agent 8000:8000
# Access http://localhost:8000
```

### Redis Connection Issues

```bash
# Check Redis pod
kubectl get pods -n pr-agent -l app=redis

# Test Redis connection
kubectl exec -it redis-0 -n pr-agent -- redis-cli ping

# Check Redis logs
kubectl logs redis-0 -n pr-agent
```

### High Memory Usage

```bash
# Check resource usage
kubectl top pods -n pr-agent

# Increase memory limits
# Edit deployment and update resources.limits.memory

# Check for memory leaks
kubectl exec -it <pod-name> -n pr-agent -- \
  python -c "import psutil; print(psutil.virtual_memory())"
```

## Maintenance

### Updating the Application

```bash
# Update image tag in kustomization
# Edit k8s/overlays/production/kustomization.yaml
images:
- name: pr-agent
  newTag: v1.1.0

# Apply update (rolling update)
kubectl apply -k k8s/overlays/production

# Monitor rollout
kubectl rollout status deployment/pr-agent -n pr-agent

# Rollback if needed
kubectl rollout undo deployment/pr-agent -n pr-agent
```

### Backup and Restore

**Backup**:
```bash
# Backup database
kubectl exec -it <pod-name> -n pr-agent -- \
  sqlite3 /app/data/pr_agent.db ".backup /app/data/backup.db"

# Copy backup locally
kubectl cp pr-agent/<pod-name>:/app/data/backup.db ./backup.db

# Backup PVC (using velero)
velero backup create pr-agent-backup \
  --include-namespaces pr-agent \
  --include-resources pvc,pv
```

**Restore**:
```bash
# Copy backup to pod
kubectl cp ./backup.db pr-agent/<pod-name>:/app/data/restore.db

# Restore database
kubectl exec -it <pod-name> -n pr-agent -- \
  cp /app/data/restore.db /app/data/pr_agent.db

# Restart pods
kubectl rollout restart deployment/pr-agent -n pr-agent
```

### Scaling

**Manual scaling**:
```bash
# Scale web deployment
kubectl scale deployment pr-agent -n pr-agent --replicas=5

# Disable HPA temporarily
kubectl delete hpa pr-agent -n pr-agent
```

**Update HPA**:
```bash
# Edit HPA
kubectl edit hpa pr-agent -n pr-agent

# Or update in manifest and reapply
kubectl apply -k k8s/overlays/production
```

## Security Best Practices

1. **Use Secrets Management**: Don't commit secrets to Git
2. **Enable RBAC**: Limit service account permissions
3. **Network Policies**: Restrict pod-to-pod communication
4. **Pod Security Standards**: Enforce security contexts
5. **Image Scanning**: Scan images for vulnerabilities
6. **TLS Everywhere**: Use TLS for all external communication
7. **Regular Updates**: Keep Kubernetes and images updated
8. **Audit Logging**: Enable Kubernetes audit logs
9. **Resource Limits**: Always set resource limits
10. **Least Privilege**: Run containers as non-root

## Performance Tuning

### Database Optimization

```yaml
# Use faster storage class
storageClassName: fast-ssd

# Increase IOPS
# Configure storage class with high IOPS
```

### Redis Optimization

```yaml
# Increase Redis memory
resources:
  limits:
    memory: 2Gi

# Enable persistence
command:
- redis-server
- --appendonly yes
- --save 900 1
- --save 300 10
```

### Application Tuning

```yaml
# Increase worker processes
env:
- name: WORKERS
  value: "4"

# Tune connection pool
- name: DB_POOL_SIZE
  value: "20"
```

## See Also

- [Deployment Guide](../docs/DEPLOYMENT.md)
- [Monitoring Guide](../docs/MONITORING.md)
- [Security Guide](../docs/SECURITY.md)
- [Performance Guide](../docs/PERFORMANCE.md)
