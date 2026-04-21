# Bitbucket Server Polling Service

Automatically monitors Bitbucket Server repositories for new and updated pull requests, triggering review commands without requiring webhook configuration.

## Overview

The polling service is ideal for internal network deployments where:
- Webhook configuration is not possible or restricted
- You want centralized PR monitoring across multiple repositories
- Network policies prevent Bitbucket from calling external services

## Configuration

Add the following to your `.pr_agent.toml`:

```toml
[bitbucket_server]
url = "https://bitbucket.internal.company.com"
bearer_token = "${BITBUCKET_TOKEN}"  # or use username/password

# Enable polling
enable_polling = true
polling_interval_seconds = 300  # Check every 5 minutes

# Repositories to monitor (PROJECT/repo-slug format)
polling_repositories = [
    "PROJ/backend-api",
    "PROJ/frontend-app",
    "DATA/analytics-pipeline"
]

# Commands to run on new/updated PRs
polling_commands = [
    "/describe --pr_description.final_update_message=false",
    "/review --pr_reviewer.require_security_review=true",
    "/improve --pr_code_suggestions.commitable_code_suggestions=true"
]

# State file for tracking processed PRs
polling_state_file = ".pr_agent_polling_state.json"

# Maximum parallel PR processing
max_parallel_tasks = 10
```

## Configuration Options

### Required Settings

- **`url`**: Bitbucket Server instance URL
- **`bearer_token`** or **`username`/`password`**: Authentication credentials
- **`enable_polling`**: Set to `true` to enable polling (default: `false`)
- **`polling_repositories`**: List of repositories to monitor in `PROJECT/repo-slug` format

### Optional Settings

- **`polling_interval_seconds`**: Seconds between polls (default: `300` = 5 minutes)
- **`polling_commands`**: Commands to run on PRs (default: describe, review, improve)
- **`polling_state_file`**: Path to state file (default: `.pr_agent_polling_state.json`)
- **`max_parallel_tasks`**: Max concurrent PR processing (default: `10`)

## Running the Polling Service

### Standalone Service

Run as a standalone background service:

```bash
python -m pr_agent.servers.bitbucket_server_polling
```

### As a Systemd Service (Linux)

Create `/etc/systemd/system/pr-agent-polling.service`:

```ini
[Unit]
Description=PR-Agent Bitbucket Server Polling Service
After=network.target

[Service]
Type=simple
User=pr-agent
WorkingDirectory=/opt/pr-agent
Environment="PYTHONPATH=/opt/pr-agent"
ExecStart=/usr/bin/python3 -m pr_agent.servers.bitbucket_server_polling
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable pr-agent-polling
sudo systemctl start pr-agent-polling
sudo systemctl status pr-agent-polling
```

### As a Docker Container

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . /app

RUN pip install -r requirements.txt

CMD ["python", "-m", "pr_agent.servers.bitbucket_server_polling"]
```

Build and run:

```bash
docker build -t pr-agent-polling .
docker run -d \
  --name pr-agent-polling \
  -v /path/to/.pr_agent.toml:/app/.pr_agent.toml \
  -v /path/to/state:/app/state \
  pr-agent-polling
```

## How It Works

### Polling Cycle

1. **Poll Repositories**: Every N seconds, query Bitbucket API for open PRs
2. **Check State**: Compare PR versions against local state file
3. **Detect Changes**:
   - **New PR**: Not in state file
   - **Updated PR**: Version number increased
4. **Apply Filters**: Use same filtering logic as webhooks (ignore patterns, etc.)
5. **Execute Commands**: Run configured commands on new/updated PRs
6. **Update State**: Record PR version and processing timestamp
7. **Wait**: Sleep until next polling interval

### State Management

The polling service maintains a JSON state file tracking processed PRs:

```json
{
  "PROJ/backend-api": {
    "123": {
      "version": 5,
      "last_processed": "2026-04-21T10:30:00",
      "commands_run": ["/describe", "/review", "/improve"],
      "status": "completed"
    }
  }
}
```

**State file benefits**:
- Prevents duplicate processing
- Survives service restarts
- Detects PR updates via version changes
- Automatic cleanup of old entries (30 days)

### Filtering

The polling service respects all webhook filtering settings:

- `CONFIG.IGNORE_REPOSITORIES` - Skip specific repos
- `CONFIG.IGNORE_PR_AUTHORS` - Skip PRs from specific users
- `CONFIG.IGNORE_PR_TITLE` - Skip PRs with matching titles
- `CONFIG.IGNORE_PR_SOURCE_BRANCHES` - Skip PRs from specific branches
- `CONFIG.IGNORE_PR_TARGET_BRANCHES` - Skip PRs to specific branches
- `allow_only_specific_folders` - Only process PRs touching specific folders

## Monitoring

### Logs

The service logs all activity in JSON format:

```json
{
  "level": "INFO",
  "message": "Found new PR: PROJ/backend-api#123 (v5) - Add authentication",
  "server_type": "bitbucket_server_polling",
  "repo": "PROJ/backend-api",
  "pr_id": 123,
  "pr_version": 5,
  "status": "new"
}
```

### Statistics

Every 10 polling iterations, the service logs statistics:

```json
{
  "total_repositories": 3,
  "total_prs_tracked": 45,
  "prs_processed_last_24h": 12,
  "state_file": ".pr_agent_polling_state.json",
  "state_file_exists": true
}
```

### Health Checks

Check if the service is running:

```bash
# Systemd
systemctl status pr-agent-polling

# Docker
docker ps | grep pr-agent-polling

# Process
ps aux | grep bitbucket_server_polling
```

Check state file:

```bash
cat .pr_agent_polling_state.json | jq .
```

## Performance Considerations

### Polling Interval

- **Short interval (1-2 min)**: Near real-time, higher API load
- **Medium interval (5 min)**: Balanced, recommended for most cases
- **Long interval (15+ min)**: Lower load, delayed reviews

### API Rate Limits

Bitbucket Server typically allows:
- ~1000 requests/hour per user
- Each poll = 1 request per repository

**Example**: 10 repos × 12 polls/hour = 120 requests/hour (well within limits)

### Parallel Processing

- `max_parallel_tasks` controls concurrent PR processing
- Each PR spawns a separate process
- Adjust based on server resources

## Troubleshooting

### Service won't start

**Error**: "Bitbucket Server polling is not enabled"

**Solution**: Set `bitbucket_server.enable_polling=true` in configuration

---

**Error**: "No repositories configured for polling"

**Solution**: Add repositories to `bitbucket_server.polling_repositories`

---

**Error**: "BITBUCKET_SERVER.URL not configured"

**Solution**: Set `bitbucket_server.url` in configuration

### PRs not being detected

**Check 1**: Verify repository format is correct (`PROJECT/repo-slug`)

```bash
# Correct
polling_repositories = ["PROJ/backend-api"]

# Incorrect
polling_repositories = ["backend-api"]  # Missing project key
```

**Check 2**: Check if PRs are filtered out

Review logs for "filtered out by config" messages. Adjust filter settings if needed.

**Check 3**: Verify authentication

Test Bitbucket API access:

```bash
curl -H "Authorization: Bearer $BITBUCKET_TOKEN" \
  https://bitbucket.internal/rest/api/1.0/projects/PROJ/repos/backend-api/pull-requests
```

### State file issues

**Corrupted state file**:

```bash
# Backup and reset
mv .pr_agent_polling_state.json .pr_agent_polling_state.json.bak
# Service will create new state file
```

**State file growing too large**:

The service automatically cleans up entries older than 30 days. If needed, manually clear:

```bash
echo "{}" > .pr_agent_polling_state.json
```

## Comparison: Polling vs Webhooks

| Feature | Polling | Webhooks |
|---------|---------|----------|
| Setup complexity | Low (just config) | Medium (server + firewall) |
| Real-time response | Delayed (polling interval) | Immediate |
| Network requirements | Outbound only | Inbound + outbound |
| Firewall friendly | Yes | Requires open port |
| API load | Constant (polling) | Event-driven (lower) |
| Missed events | No (state tracking) | Possible (if server down) |
| Multiple repos | Easy (list in config) | Requires webhook per repo |

**Recommendation**: Use polling for internal networks, webhooks for public/cloud deployments.

## Integration with Webhooks

You can run both polling and webhooks simultaneously:

```toml
[bitbucket_server]
# Webhook for some repos
pr_commands = ["/describe", "/review"]

# Polling for others
enable_polling = true
polling_repositories = ["INTERNAL/private-repo"]
polling_commands = ["/describe", "/review", "/improve"]
```

The polling service uses the same filtering and command execution logic as webhooks, ensuring consistent behavior.

## Example Deployment

### Production Setup

```toml
[config]
model = "gpt-4o"
git_provider = "bitbucket_server"
log_level = "INFO"

[bitbucket_server]
url = "https://bitbucket.internal.company.com"
bearer_token = "${BITBUCKET_TOKEN}"

enable_polling = true
polling_interval_seconds = 300
polling_repositories = [
    "BACKEND/user-service",
    "BACKEND/payment-service",
    "FRONTEND/web-app",
    "FRONTEND/mobile-app"
]
polling_commands = [
    "/describe",
    "/review --pr_reviewer.require_security_review=true",
    "/improve --pr_code_suggestions.commitable_code_suggestions=true"
]
polling_state_file = "/var/lib/pr-agent/polling_state.json"
max_parallel_tasks = 5

[pr_reviewer]
require_security_review = true
require_tests_review = true
extra_instructions = "Focus on security vulnerabilities and code quality."
```

### Start Service

```bash
# Create state directory
mkdir -p /var/lib/pr-agent

# Start service
python -m pr_agent.servers.bitbucket_server_polling
```

## Testing

Run unit tests:

```bash
PYTHONPATH=. pytest tests/unittest/test_polling_state.py -v
```

Test polling manually:

```bash
# Set short interval for testing
export BITBUCKET_SERVER__POLLING_INTERVAL_SECONDS=30

# Run service
python -m pr_agent.servers.bitbucket_server_polling
```

Create a test PR and verify it's detected within the polling interval.
