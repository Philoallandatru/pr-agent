# Bitbucket Server polling on Linux

This guide runs PR-Agent as a polling service for Bitbucket Server / Data Center.
Use this mode when Bitbucket webhooks are unavailable, blocked by network rules, or operationally hard to manage.

The polling service periodically scans configured repositories for open pull requests. For each PR it stores the last
seen `fromRef.latestCommit` in SQLite. When the PR is new or the source head commit changes, it runs the configured
PR-Agent commands, such as `/describe`, `/review`, and `/improve`.

## When to use this mode

Use polling when:

- Bitbucket Server cannot call back to a PR-Agent webhook endpoint.
- You want a private outbound-only service that talks to Bitbucket and the model provider.
- You can tolerate review latency equal to the polling interval, for example 1 to 5 minutes.

Prefer webhooks when you need near-real-time execution or when the PR volume is high.

## Behavior

- Trigger key: `fromRef.latestCommit`
- State store: SQLite
- Default commands: `BITBUCKET_SERVER.PR_COMMANDS`, or `/review` if no command list is configured
- Default interval: 300 seconds
- Default first-run behavior: process existing open PRs

To avoid reviewing every existing open PR on first deployment, set:

```bash
BITBUCKET_SERVER_POLLING__PROCESS_UNKNOWN_PRS=false
```

With this setting, the first cycle only records the current head commit for existing open PRs. Later source-branch
updates will trigger the commands normally.

## Required Bitbucket permissions

Create a Bitbucket Server HTTP access token for a service account. The token needs enough permission to:

- read the configured repositories
- read open pull requests and diffs
- write PR comments

In Bitbucket Server, create it from:

```text
Manage account -> HTTP access tokens -> Create token
```

## Configuration

The polling service reads the same PR-Agent settings system as the rest of the project. On Linux, environment variables
are usually the simplest option:

```bash
export CONFIG__GIT_PROVIDER="bitbucket_server"
export BITBUCKET_SERVER__URL="https://bitbucket.example.com"
export BITBUCKET_SERVER__BEARER_TOKEN="YOUR_BITBUCKET_SERVER_TOKEN"
export OPENAI__KEY="YOUR_OPENAI_KEY"

export BITBUCKET_SERVER_POLLING__REPOSITORIES='["PROJ/repo-a","PROJ/repo-b"]'
export BITBUCKET_SERVER_POLLING__INTERVAL_SECONDS="300"
export BITBUCKET_SERVER_POLLING__STATE_PATH="/var/lib/pr-agent/bitbucket-polling.sqlite3"
export BITBUCKET_SERVER_POLLING__PROCESS_UNKNOWN_PRS="false"
export BITBUCKET_SERVER_POLLING__COMMANDS='["/describe --pr_description.final_update_message=false","/review","/improve --pr_code_suggestions.commitable_code_suggestions=true"]'
```

Repository entries must use:

```text
PROJECT_KEY/repo-slug
```

## Option A: Run with Docker

Build the image:

```bash
cd /opt/pr-agent
docker build . \
  -t pr-agent:bitbucket-server-polling \
  --target bitbucket_server_polling \
  -f docker/Dockerfile
```

Create a persistent state directory:

```bash
sudo mkdir -p /var/lib/pr-agent
sudo chown "$USER":"$USER" /var/lib/pr-agent
```

Run the service:

```bash
docker run -d \
  --name pr-agent-bitbucket-polling \
  --restart unless-stopped \
  -e CONFIG__GIT_PROVIDER="bitbucket_server" \
  -e BITBUCKET_SERVER__URL="https://bitbucket.example.com" \
  -e BITBUCKET_SERVER__BEARER_TOKEN="YOUR_BITBUCKET_SERVER_TOKEN" \
  -e OPENAI__KEY="YOUR_OPENAI_KEY" \
  -e BITBUCKET_SERVER_POLLING__REPOSITORIES='["PROJ/repo-a","PROJ/repo-b"]' \
  -e BITBUCKET_SERVER_POLLING__INTERVAL_SECONDS="300" \
  -e BITBUCKET_SERVER_POLLING__STATE_PATH="/data/bitbucket-polling.sqlite3" \
  -e BITBUCKET_SERVER_POLLING__PROCESS_UNKNOWN_PRS="false" \
  -e BITBUCKET_SERVER_POLLING__COMMANDS='["/describe --pr_description.final_update_message=false","/review","/improve --pr_code_suggestions.commitable_code_suggestions=true"]' \
  -v /var/lib/pr-agent:/data \
  pr-agent:bitbucket-server-polling
```

Check logs:

```bash
docker logs -f pr-agent-bitbucket-polling
```

Stop it:

```bash
docker stop pr-agent-bitbucket-polling
docker rm pr-agent-bitbucket-polling
```

## Option B: Run with systemd and a Python virtual environment

Create a Linux user and install PR-Agent:

```bash
sudo useradd --system --create-home --home-dir /opt/pr-agent --shell /usr/sbin/nologin pr-agent
sudo mkdir -p /opt/pr-agent /var/lib/pr-agent
sudo chown -R pr-agent:pr-agent /opt/pr-agent /var/lib/pr-agent
```

Install dependencies from the repository checkout:

```bash
cd /opt/pr-agent
sudo -u pr-agent python3.12 -m venv .venv
sudo -u pr-agent .venv/bin/python -m pip install --upgrade pip setuptools wheel
sudo -u pr-agent .venv/bin/python -m pip install -r requirements.txt
```

Create an environment file:

```bash
sudo tee /etc/pr-agent-bitbucket-polling.env >/dev/null <<'EOF'
CONFIG__GIT_PROVIDER=bitbucket_server
BITBUCKET_SERVER__URL=https://bitbucket.example.com
BITBUCKET_SERVER__BEARER_TOKEN=YOUR_BITBUCKET_SERVER_TOKEN
OPENAI__KEY=YOUR_OPENAI_KEY
BITBUCKET_SERVER_POLLING__REPOSITORIES='["PROJ/repo-a","PROJ/repo-b"]'
BITBUCKET_SERVER_POLLING__INTERVAL_SECONDS=300
BITBUCKET_SERVER_POLLING__STATE_PATH=/var/lib/pr-agent/bitbucket-polling.sqlite3
BITBUCKET_SERVER_POLLING__PROCESS_UNKNOWN_PRS=false
BITBUCKET_SERVER_POLLING__COMMANDS='["/describe --pr_description.final_update_message=false","/review","/improve --pr_code_suggestions.commitable_code_suggestions=true"]'
EOF

sudo chmod 600 /etc/pr-agent-bitbucket-polling.env
sudo chown root:root /etc/pr-agent-bitbucket-polling.env
```

Create the systemd unit:

```bash
sudo tee /etc/systemd/system/pr-agent-bitbucket-polling.service >/dev/null <<'EOF'
[Unit]
Description=PR-Agent Bitbucket Server polling service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pr-agent
Group=pr-agent
WorkingDirectory=/opt/pr-agent
EnvironmentFile=/etc/pr-agent-bitbucket-polling.env
ExecStart=/opt/pr-agent/.venv/bin/python -m pr_agent.servers.bitbucket_server_polling
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF
```

Start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now pr-agent-bitbucket-polling
sudo systemctl status pr-agent-bitbucket-polling
```

View logs:

```bash
journalctl -u pr-agent-bitbucket-polling -f
```

Restart after changing configuration:

```bash
sudo systemctl restart pr-agent-bitbucket-polling
```

## Option C: Run from cron

Cron is less flexible than the long-running polling service, but it works for very small installations.

Create a wrapper script:

```bash
sudo tee /opt/pr-agent/run-bitbucket-polling-once.sh >/dev/null <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

cd /opt/pr-agent
export CONFIG__GIT_PROVIDER="bitbucket_server"
export BITBUCKET_SERVER__URL="https://bitbucket.example.com"
export BITBUCKET_SERVER__BEARER_TOKEN="YOUR_BITBUCKET_SERVER_TOKEN"
export OPENAI__KEY="YOUR_OPENAI_KEY"
export BITBUCKET_SERVER_POLLING__REPOSITORIES='["PROJ/repo-a","PROJ/repo-b"]'
export BITBUCKET_SERVER_POLLING__STATE_PATH="/var/lib/pr-agent/bitbucket-polling.sqlite3"
export BITBUCKET_SERVER_POLLING__PROCESS_UNKNOWN_PRS="false"
export BITBUCKET_SERVER_POLLING__COMMANDS='["/review"]'

timeout 240s /opt/pr-agent/.venv/bin/python - <<'PY'
import asyncio

from pr_agent.servers.bitbucket_server_polling import (
    SQLitePollingState,
    build_bitbucket_client,
    load_config,
    run_polling_cycle,
)

config = load_config()
client = build_bitbucket_client(config)
state = SQLitePollingState(config.state_path)
asyncio.run(run_polling_cycle(client, state, config))
PY
EOF

sudo chmod +x /opt/pr-agent/run-bitbucket-polling-once.sh
```

Add a cron entry:

```bash
*/5 * * * * /opt/pr-agent/run-bitbucket-polling-once.sh >> /var/log/pr-agent-bitbucket-polling.log 2>&1
```

Use cron only if one cycle reliably finishes before the next one starts. For normal use, prefer Docker or systemd.

## Smoke test

Before enabling automatic commands, test one PR manually:

```bash
export CONFIG__GIT_PROVIDER="bitbucket_server"
export BITBUCKET_SERVER__URL="https://bitbucket.example.com"
export BITBUCKET_SERVER__BEARER_TOKEN="YOUR_BITBUCKET_SERVER_TOKEN"
export OPENAI__KEY="YOUR_OPENAI_KEY"

python -m pr_agent.cli \
  --pr_url "https://bitbucket.example.com/projects/PROJ/repos/repo-a/pull-requests/123" \
  review
```

Then run one polling cycle with `PROCESS_UNKNOWN_PRS=false` to populate the SQLite state without reviewing existing PRs:

```bash
export BITBUCKET_SERVER_POLLING__REPOSITORIES='["PROJ/repo-a"]'
export BITBUCKET_SERVER_POLLING__STATE_PATH="/tmp/pr-agent-bitbucket-polling.sqlite3"
export BITBUCKET_SERVER_POLLING__PROCESS_UNKNOWN_PRS="false"

python - <<'PY'
import asyncio

from pr_agent.servers.bitbucket_server_polling import (
    SQLitePollingState,
    build_bitbucket_client,
    load_config,
    run_polling_cycle,
)

config = load_config()
client = build_bitbucket_client(config)
state = SQLitePollingState(config.state_path)
asyncio.run(run_polling_cycle(client, state, config))
PY
```

Push a new commit to the PR source branch and run the polling service again. The configured commands should execute and
publish PR comments.

## Troubleshooting

### The service reviews every open PR after startup

Set:

```bash
BITBUCKET_SERVER_POLLING__PROCESS_UNKNOWN_PRS=false
```

Then delete the SQLite state file only if you intentionally want to rebuild the baseline.

### The service keeps retrying the same PR

This means at least one configured command failed or returned `False`. Check logs:

```bash
docker logs pr-agent-bitbucket-polling
# or
journalctl -u pr-agent-bitbucket-polling -n 200
```

The state advances only after all commands for the PR complete successfully.

### The service never detects a PR update

Check that:

- the PR belongs to one of the configured `PROJECT/repo-slug` entries
- the source branch head commit changed
- the Bitbucket token can read the repository and pull request
- the SQLite state file is writable by the service user

### The service cannot write comments

The Bitbucket service account token likely has read-only permission. Grant it repository write/comment permissions, then
restart the service.
