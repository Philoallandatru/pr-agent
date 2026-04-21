# PR Agent Docker Deployment

Complete Docker setup for PR Agent auto-review system.

## Quick Start

1. **Configure PR Agent**:
```bash
cp pr_agent/settings/configuration.toml pr_agent.toml
# Edit pr_agent.toml with your settings
```

2. **Build and start all services**:
```bash
docker-compose up -d
```

3. **Access the application**:
- Frontend: http://localhost
- API: http://localhost:8000/api
- API Docs: http://localhost:8000/docs

## Services

### Backend (Port 8000)
- FastAPI web server
- REST API endpoints
- SQLite database
- Health checks

### Polling Service
- Bitbucket PR monitoring
- Automatic review triggering
- State persistence

### Frontend (Port 80)
- React web interface
- Nginx reverse proxy
- Static asset serving

## Configuration

### Environment Variables

Create a `.env` file:
```env
BITBUCKET_BEARER_TOKEN=your_token_here
OPENAI_API_KEY=your_key_here
```

### Configuration File

Edit `pr_agent.toml`:
```toml
[config]
model = "gpt-4o"
git_provider = "bitbucket_server"

[bitbucket_server]
url = "https://bitbucket.company.com"
bearer_token = "${BITBUCKET_BEARER_TOKEN}"
enable_polling = true
polling_interval_seconds = 300
polling_repositories = ["PROJ/repo1", "PROJ/repo2"]

[tokenizer]
enable_local_cache = true
local_cache_dir = "/data/tokenizers"

[repo_context]
enable_full_context = true
clone_cache_dir = "/data/repos"

[web_platform]
enable = true
host = "0.0.0.0"
port = 8000
database_path = "/data/db/pr_agent.db"
```

## Management

### Start services
```bash
docker-compose up -d
```

### Stop services
```bash
docker-compose down
```

### View logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f polling
docker-compose logs -f frontend
```

### Restart services
```bash
docker-compose restart
```

### Rebuild after code changes
```bash
docker-compose up -d --build
```

## Data Persistence

Data is stored in Docker volumes:
- `tokenizer-cache`: Cached tokenizer models
- `repo-cache`: Cloned repositories
- `db-data`: SQLite database
- `polling-state`: Polling service state

### Backup data
```bash
docker run --rm -v pr-agent_db-data:/data -v $(pwd):/backup alpine tar czf /backup/db-backup.tar.gz /data
```

### Restore data
```bash
docker run --rm -v pr-agent_db-data:/data -v $(pwd):/backup alpine tar xzf /backup/db-backup.tar.gz -C /
```

## Health Checks

### Check service health
```bash
curl http://localhost:8000/api/health
```

### Check container status
```bash
docker-compose ps
```

## Troubleshooting

### View container logs
```bash
docker-compose logs backend
docker-compose logs polling
```

### Access container shell
```bash
docker-compose exec backend bash
docker-compose exec polling bash
```

### Check resource usage
```bash
docker stats
```

### Reset everything
```bash
docker-compose down -v
docker-compose up -d --build
```

## Production Deployment

### Use production compose file
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Enable HTTPS
Add SSL certificates and update nginx configuration:
```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    # ... rest of config
}
```

### Resource limits
Add to docker-compose.yml:
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
```

## Monitoring

### Prometheus metrics
Add to docker-compose.yml:
```yaml
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
```

### Grafana dashboards
```yaml
services:
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    depends_on:
      - prometheus
```

## Security

### Network isolation
Services communicate via internal network only. Only frontend and backend ports are exposed.

### Read-only filesystem
Add to service definitions:
```yaml
read_only: true
tmpfs:
  - /tmp
```

### Non-root user
Containers run as non-root users by default.

## Scaling

### Scale polling workers
```bash
docker-compose up -d --scale polling=3
```

### Load balancing
Use nginx or traefik for load balancing multiple backend instances.
