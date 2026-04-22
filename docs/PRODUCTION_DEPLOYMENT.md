# Production Deployment Guide

This guide provides comprehensive instructions for deploying the PR Agent Auto-Review system to production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Deployment Options](#deployment-options)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Systemd Deployment](#systemd-deployment)
- [Configuration](#configuration)
- [Database Setup](#database-setup)
- [Security Hardening](#security-hardening)
- [Monitoring and Logging](#monitoring-and-logging)
- [Backup and Recovery](#backup-and-recovery)
- [Performance Tuning](#performance-tuning)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)

## Prerequisites

### System Requirements

**Minimum Requirements:**
- CPU: 2 cores
- RAM: 4 GB
- Disk: 20 GB
- OS: Linux (Ubuntu 20.04+, CentOS 8+, Debian 11+)

**Recommended for Production:**
- CPU: 4+ cores
- RAM: 8+ GB
- Disk: 50+ GB SSD
- OS: Ubuntu 22.04 LTS or RHEL 9

### Software Dependencies

- Python 3.9 or higher
- Git 2.30+
- Redis 6.0+ (for caching)
- PostgreSQL 13+ or SQLite 3.35+ (database)
- Node.js 18+ and npm 9+ (for frontend)
- Docker 24+ and Docker Compose 2.20+ (for containerized deployment)
- Kubernetes 1.25+ (for K8s deployment)

### Network Requirements

- Outbound HTTPS (443) access to:
  - GitHub/Bitbucket API endpoints
  - LLM provider APIs (OpenAI, Anthropic, etc.)
  - Hugging Face (for tokenizer downloads)
- Inbound access on configured ports (default: 8000 for API, 3000 for frontend)
- Internal network access between services (API, Redis, database)

## Deployment Options

### 1. Docker Compose (Recommended for Small-Medium Deployments)

**Pros:**
- Easy setup and management
- Isolated environment
- Built-in service orchestration
- Suitable for single-server deployments

**Cons:**
- Limited scalability
- No automatic failover
- Single point of failure

### 2. Kubernetes (Recommended for Large-Scale Deployments)

**Pros:**
- High availability
- Auto-scaling
- Self-healing
- Multi-node support
- Rolling updates

**Cons:**
- Complex setup
- Requires K8s expertise
- Higher resource overhead

### 3. Systemd (Traditional Deployment)

**Pros:**
- Native OS integration
- Low overhead
- Direct control

**Cons:**
- Manual dependency management
- No built-in orchestration
- Requires more manual configuration

## Docker Deployment

### Quick Start

1. **Clone the repository:**

```bash
git clone https://github.com/Philoallandatru/pr-agent.git
cd pr-agent
git checkout auto-review
```

2. **Create environment file:**

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Database
DATABASE_URL=sqlite:///./data/pr_agent.db

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=your_secure_password

# Authentication
JWT_SECRET_KEY=your_jwt_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Bitbucket Server
BITBUCKET_SERVER_URL=https://bitbucket.example.com
BITBUCKET_SERVER_TOKEN=your_bitbucket_token

# LLM Provider
OPENAI_API_KEY=your_openai_key
# or
ANTHROPIC_API_KEY=your_anthropic_key

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ADMIN_PASSWORD=your_grafana_password
```

3. **Start services:**

```bash
docker-compose up -d
```

4. **Verify deployment:**

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f

# Test API
curl http://localhost:8000/health

# Access frontend
open http://localhost:3000
```

### Production Docker Compose Configuration

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  api:
    image: pr-agent-api:latest
    restart: always
    environment:
      - ENVIRONMENT=production
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --requirepass ${REDIS_PASSWORD} --maxmemory 2gb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 2G

  frontend:
    image: pr-agent-frontend:latest
    restart: always
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G

volumes:
  redis_data:
  db_data:
```

Start with production configuration:

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (1.25+)
- kubectl configured
- Helm 3+ (optional but recommended)

### Deploy with Kustomize

1. **Review and customize configurations:**

```bash
# Development
cat k8s/overlays/dev/kustomization.yaml

# Staging
cat k8s/overlays/staging/kustomization.yaml

# Production
cat k8s/overlays/production/kustomization.yaml
```

2. **Create namespace:**

```bash
kubectl create namespace pr-agent-prod
```

3. **Create secrets:**

```bash
# Create secret for sensitive data
kubectl create secret generic pr-agent-secrets \
  --from-literal=jwt-secret-key='your_jwt_secret' \
  --from-literal=bitbucket-token='your_bitbucket_token' \
  --from-literal=openai-api-key='your_openai_key' \
  --from-literal=redis-password='your_redis_password' \
  -n pr-agent-prod
```

4. **Deploy to production:**

```bash
kubectl apply -k k8s/overlays/production
```

5. **Verify deployment:**

```bash
# Check pods
kubectl get pods -n pr-agent-prod

# Check services
kubectl get svc -n pr-agent-prod

# Check ingress
kubectl get ingress -n pr-agent-prod

# View logs
kubectl logs -f deployment/pr-agent-api -n pr-agent-prod
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment pr-agent-api --replicas=5 -n pr-agent-prod

# Enable HPA (Horizontal Pod Autoscaler)
kubectl apply -f k8s/base/hpa.yaml -n pr-agent-prod

# Check HPA status
kubectl get hpa -n pr-agent-prod
```

### Rolling Updates

```bash
# Update image
kubectl set image deployment/pr-agent-api \
  pr-agent-api=pr-agent-api:v2.0.0 \
  -n pr-agent-prod

# Check rollout status
kubectl rollout status deployment/pr-agent-api -n pr-agent-prod

# Rollback if needed
kubectl rollout undo deployment/pr-agent-api -n pr-agent-prod
```

## Systemd Deployment

### Installation

1. **Install system dependencies:**

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3.9 python3.9-venv python3-pip git redis-server nginx

# RHEL/CentOS
sudo dnf install -y python39 python39-pip git redis nginx
```

2. **Create application user:**

```bash
sudo useradd -r -s /bin/bash -d /opt/pr-agent pr-agent
```

3. **Install application:**

```bash
sudo -u pr-agent bash
cd /opt/pr-agent
git clone https://github.com/Philoallandatru/pr-agent.git .
git checkout auto-review

python3.9 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

4. **Configure application:**

```bash
cp pr_agent/settings/configuration.toml.example pr_agent/settings/configuration.toml
# Edit configuration.toml with your settings
```

5. **Install systemd services:**

```bash
sudo cp deployment/systemd/pr-agent-api.service /etc/systemd/system/
sudo cp deployment/systemd/pr-agent-polling.service /etc/systemd/system/
sudo systemctl daemon-reload
```

6. **Start services:**

```bash
sudo systemctl enable pr-agent-api pr-agent-polling
sudo systemctl start pr-agent-api pr-agent-polling
```

7. **Check status:**

```bash
sudo systemctl status pr-agent-api
sudo systemctl status pr-agent-polling
```

### Nginx Configuration

Create `/etc/nginx/sites-available/pr-agent`:

```nginx
upstream pr_agent_api {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name pr-agent.example.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name pr-agent.example.com;

    ssl_certificate /etc/ssl/certs/pr-agent.crt;
    ssl_certificate_key /etc/ssl/private/pr-agent.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Frontend
    location / {
        root /opt/pr-agent/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # API
    location /api {
        proxy_pass http://pr_agent_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /ws {
        proxy_pass http://pr_agent_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # Health check
    location /health {
        proxy_pass http://pr_agent_api;
        access_log off;
    }
}
```

Enable and restart Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/pr-agent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Configuration

### Environment Variables

Key environment variables for production:

```bash
# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Security
JWT_SECRET_KEY=<strong-random-key>
API_KEY_SALT=<random-salt>
ALLOWED_HOSTS=pr-agent.example.com

# Database
DATABASE_URL=postgresql://user:pass@localhost/pr_agent
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://:password@localhost:6379/0
REDIS_MAX_CONNECTIONS=50

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60

# Monitoring
PROMETHEUS_ENABLED=true
SENTRY_DSN=<your-sentry-dsn>
```

### Configuration File

Edit `pr_agent/settings/configuration.toml`:

```toml
[server]
host = "0.0.0.0"
port = 8000
workers = 4
log_level = "info"

[database]
url = "postgresql://user:pass@localhost/pr_agent"
pool_size = 20
max_overflow = 10

[redis]
host = "localhost"
port = 6379
password = "your_password"
db = 0

[bitbucket_server_polling]
enabled = true
interval_seconds = 300
max_concurrent_reviews = 5

[repo_context]
enabled = true
cache_dir = "/var/cache/pr-agent/repos"
max_cache_size_gb = 10

[backup]
enabled = true
backup_dir = "/var/backups/pr-agent"
retention_days = 30
auto_backup_enabled = true
auto_backup_schedule = "0 2 * * *"

[monitoring]
prometheus_enabled = true
metrics_port = 9090
```

## Database Setup

### SQLite (Development/Small Deployments)

```bash
# Database is created automatically
# Location: ./data/pr_agent.db
```

### PostgreSQL (Production)

1. **Install PostgreSQL:**

```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib

# RHEL/CentOS
sudo dnf install postgresql-server postgresql-contrib
sudo postgresql-setup --initdb
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

2. **Create database and user:**

```bash
sudo -u postgres psql

CREATE DATABASE pr_agent;
CREATE USER pr_agent WITH ENCRYPTED PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE pr_agent TO pr_agent;
\q
```

3. **Run migrations:**

```bash
cd /opt/pr-agent
source venv/bin/activate
python -m pr_agent.storage.migration upgrade
```

4. **Verify:**

```bash
python -m pr_agent.storage.migration status
```

## Security Hardening

### 1. Authentication

- Use strong JWT secret keys (minimum 32 characters)
- Enable API key authentication for service-to-service communication
- Implement role-based access control (RBAC)
- Rotate credentials regularly

### 2. Network Security

```bash
# Firewall rules (UFW example)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Restrict Redis access
sudo ufw allow from 10.0.0.0/8 to any port 6379
```

### 3. SSL/TLS

Use Let's Encrypt for free SSL certificates:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d pr-agent.example.com
```

### 4. Application Security

- Enable rate limiting
- Configure CORS properly
- Use security headers
- Sanitize user inputs
- Keep dependencies updated

### 5. Secrets Management

Use environment variables or secret management tools:

```bash
# Kubernetes secrets
kubectl create secret generic pr-agent-secrets \
  --from-file=config.toml=./config.toml

# HashiCorp Vault
vault kv put secret/pr-agent \
  jwt_secret="..." \
  bitbucket_token="..."
```

## Monitoring and Logging

### Prometheus + Grafana

1. **Deploy monitoring stack:**

```bash
cd monitoring
docker-compose up -d
```

2. **Access Grafana:**

```
URL: http://localhost:3001
Username: admin
Password: (from .env)
```

3. **Import dashboards:**

- Navigate to Dashboards → Import
- Upload `monitoring/grafana/dashboards/overview.json`

### Application Logs

**Docker:**
```bash
docker-compose logs -f api
```

**Systemd:**
```bash
sudo journalctl -u pr-agent-api -f
```

**Kubernetes:**
```bash
kubectl logs -f deployment/pr-agent-api -n pr-agent-prod
```

### Log Aggregation

Configure centralized logging with ELK stack or similar:

```yaml
# docker-compose.yml
  filebeat:
    image: docker.elastic.co/beats/filebeat:8.11.0
    volumes:
      - ./filebeat.yml:/usr/share/filebeat/filebeat.yml
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
```

## Backup and Recovery

### Automated Backups

1. **Configure backup settings:**

```toml
[backup]
enabled = true
backup_dir = "/var/backups/pr-agent"
retention_days = 30
auto_backup_enabled = true
auto_backup_schedule = "0 2 * * *"  # Daily at 2 AM
```

2. **Manual backup:**

```bash
# Via API
curl -X POST http://localhost:8000/api/backups \
  -H "Authorization: Bearer $TOKEN"

# Via CLI
python -m pr_agent.cli.auto_review backup create
```

3. **Restore from backup:**

```bash
# List backups
python -m pr_agent.cli.auto_review backup list

# Restore
python -m pr_agent.cli.auto_review backup restore <backup_id>
```

### Disaster Recovery

1. **Backup critical data:**
   - Database
   - Configuration files
   - Repository cache
   - Logs (optional)

2. **Store backups off-site:**

```bash
# Sync to S3
aws s3 sync /var/backups/pr-agent s3://my-bucket/pr-agent-backups/

# Or use rsync
rsync -avz /var/backups/pr-agent/ backup-server:/backups/pr-agent/
```

3. **Test recovery procedures regularly**

## Performance Tuning

### Application Tuning

1. **Worker processes:**

```bash
# Gunicorn workers = (2 x CPU cores) + 1
API_WORKERS=9  # For 4-core system
```

2. **Database connection pool:**

```toml
[database]
pool_size = 20
max_overflow = 10
pool_timeout = 30
```

3. **Redis configuration:**

```bash
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
tcp-backlog 511
```

### Caching Strategy

```toml
[cache]
enabled = true
default_ttl = 3600
max_size_mb = 1024

[cache.strategies]
repository_metadata = 7200
pr_analysis = 3600
user_sessions = 1800
```

### Resource Limits

**Docker:**
```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 4G
    reservations:
      cpus: '1'
      memory: 2G
```

**Kubernetes:**
```yaml
resources:
  requests:
    memory: "2Gi"
    cpu: "1000m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

## Troubleshooting

### Common Issues

#### 1. API Not Responding

```bash
# Check service status
systemctl status pr-agent-api

# Check logs
journalctl -u pr-agent-api -n 100

# Check port binding
netstat -tlnp | grep 8000

# Test connectivity
curl http://localhost:8000/health
```

#### 2. Database Connection Errors

```bash
# Test database connection
psql -h localhost -U pr_agent -d pr_agent

# Check connection pool
# Look for "too many connections" errors in logs

# Increase pool size in configuration
```

#### 3. Redis Connection Issues

```bash
# Test Redis
redis-cli -h localhost -p 6379 -a your_password ping

# Check Redis memory
redis-cli info memory

# Clear cache if needed
redis-cli FLUSHDB
```

#### 4. High Memory Usage

```bash
# Check memory usage
docker stats
# or
top -o %MEM

# Reduce cache size
# Decrease worker count
# Enable memory limits
```

#### 5. Slow Performance

```bash
# Check database queries
# Enable query logging in PostgreSQL

# Check Redis hit rate
redis-cli info stats | grep hit_rate

# Profile application
python -m cProfile -o profile.stats app.py
```

### Debug Mode

Enable debug mode temporarily:

```bash
# Set environment variable
export DEBUG=true
export LOG_LEVEL=DEBUG

# Restart service
systemctl restart pr-agent-api
```

### Health Checks

```bash
# Basic health
curl http://localhost:8000/health

# Detailed health
curl http://localhost:8000/health/ready

# Component health
curl http://localhost:8000/health/live
```

## Maintenance

### Regular Tasks

**Daily:**
- Monitor logs for errors
- Check disk space
- Review metrics dashboards

**Weekly:**
- Review backup status
- Check for security updates
- Analyze performance metrics

**Monthly:**
- Update dependencies
- Review and rotate logs
- Test disaster recovery
- Security audit

### Updates

1. **Backup before updating:**

```bash
python -m pr_agent.cli.auto_review backup create
```

2. **Pull latest code:**

```bash
git fetch origin
git checkout auto-review
git pull origin auto-review
```

3. **Update dependencies:**

```bash
pip install -r requirements.txt --upgrade
```

4. **Run migrations:**

```bash
python -m pr_agent.storage.migration upgrade
```

5. **Restart services:**

```bash
systemctl restart pr-agent-api pr-agent-polling
```

### Log Rotation

Configure logrotate:

```bash
# /etc/logrotate.d/pr-agent
/var/log/pr-agent/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 pr-agent pr-agent
    sharedscripts
    postrotate
        systemctl reload pr-agent-api
    endscript
}
```

### Monitoring Checklist

- [ ] API response times < 200ms (p95)
- [ ] Error rate < 1%
- [ ] CPU usage < 70%
- [ ] Memory usage < 80%
- [ ] Disk usage < 80%
- [ ] Database connections < 80% of pool
- [ ] Redis memory < 90% of maxmemory
- [ ] Backup success rate = 100%
- [ ] SSL certificate valid > 30 days

## Support and Resources

- **Documentation:** https://github.com/Philoallandatru/pr-agent/tree/auto-review/docs
- **Issues:** https://github.com/Philoallandatru/pr-agent/issues
- **Monitoring Guide:** [MONITORING_SETUP.md](./MONITORING_SETUP.md)
- **Security Guide:** [SECURITY.md](./SECURITY.md)
- **API Reference:** [API_REFERENCE.md](./API_REFERENCE.md)

## Appendix

### A. Environment Variables Reference

See [.env.example](./.env.example) for complete list.

### B. Port Reference

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| API | 8000 | HTTP | REST API |
| Frontend | 3000 | HTTP | Web UI |
| Redis | 6379 | TCP | Cache |
| PostgreSQL | 5432 | TCP | Database |
| Prometheus | 9090 | HTTP | Metrics |
| Grafana | 3001 | HTTP | Dashboards |

### C. File Locations

| Component | Path |
|-----------|------|
| Application | /opt/pr-agent |
| Configuration | /opt/pr-agent/pr_agent/settings/configuration.toml |
| Logs | /var/log/pr-agent |
| Database | /var/lib/pr-agent/pr_agent.db |
| Backups | /var/backups/pr-agent |
| Cache | /var/cache/pr-agent |

### D. Useful Commands

```bash
# Check all services
systemctl status pr-agent-*

# View all logs
journalctl -u pr-agent-* -f

# Restart all services
systemctl restart pr-agent-*

# Check disk usage
du -sh /opt/pr-agent/*
df -h

# Check network connections
netstat -tlnp | grep python

# Monitor resources
htop
```
