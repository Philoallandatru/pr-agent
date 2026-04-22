# PR Agent Systemd Services

## Installation

1. **Create user and directories**:
```bash
sudo useradd -r -s /bin/false pr-agent
sudo mkdir -p /opt/pr-agent /var/lib/pr-agent /var/log/pr-agent
sudo chown -R pr-agent:pr-agent /opt/pr-agent /var/lib/pr-agent /var/log/pr-agent
```

2. **Install PR Agent**:
```bash
cd /opt/pr-agent
sudo -u pr-agent python3 -m venv venv
sudo -u pr-agent venv/bin/pip install -e /path/to/pr-agent
```

3. **Configure**:
```bash
sudo -u pr-agent cp /path/to/.pr_agent.toml /opt/pr-agent/
```

4. **Install service files**:
```bash
sudo cp deployment/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
```

5. **Enable and start services**:
```bash
# Start polling service
sudo systemctl enable pr-agent-polling
sudo systemctl start pr-agent-polling

# Start web platform
sudo systemctl enable pr-agent-web
sudo systemctl start pr-agent-web
```

## Management

### Check status
```bash
sudo systemctl status pr-agent-polling
sudo systemctl status pr-agent-web
```

### View logs
```bash
sudo journalctl -u pr-agent-polling -f
sudo journalctl -u pr-agent-web -f
```

### Restart services
```bash
sudo systemctl restart pr-agent-polling
sudo systemctl restart pr-agent-web
```

### Stop services
```bash
sudo systemctl stop pr-agent-polling
sudo systemctl stop pr-agent-web
```

## Configuration

Edit `/opt/pr-agent/.pr_agent.toml` and restart services:

```bash
sudo systemctl restart pr-agent-polling pr-agent-web
```

## Troubleshooting

### Check service status
```bash
systemctl status pr-agent-polling
systemctl status pr-agent-web
```

### View recent logs
```bash
journalctl -u pr-agent-polling -n 100
journalctl -u pr-agent-web -n 100
```

### Check permissions
```bash
ls -la /opt/pr-agent
ls -la /var/lib/pr-agent
ls -la /var/log/pr-agent
```

### Test manually
```bash
sudo -u pr-agent /opt/pr-agent/venv/bin/python -m pr_agent.servers.bitbucket_server_polling
sudo -u pr-agent /opt/pr-agent/venv/bin/python -m pr_agent.servers.web_platform
```
