# Systemd deployment

This service runs only the Bitbucket Server polling reviewer.

## Install

```bash
sudo useradd -r -s /usr/sbin/nologin pr-agent || true
sudo mkdir -p /opt/pr-agent /etc/pr-agent /var/lib/pr-agent /var/log/pr-agent
sudo chown -R pr-agent:pr-agent /opt/pr-agent /var/lib/pr-agent /var/log/pr-agent

sudo cp -r . /opt/pr-agent
cd /opt/pr-agent
sudo -u pr-agent python3.12 -m venv .venv
sudo -u pr-agent .venv/bin/pip install -r requirements.txt
sudo -u pr-agent .venv/bin/pip install -e .

sudo cp .pr_agent.toml /etc/pr-agent/.pr_agent.toml
sudo cp .env.example /etc/pr-agent/polling.env
sudo editor /etc/pr-agent/.pr_agent.toml
sudo editor /etc/pr-agent/polling.env

sudo cp deployment/systemd/pr-agent-polling.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now pr-agent-polling
```

## Operate

```bash
sudo systemctl status pr-agent-polling
sudo journalctl -u pr-agent-polling -f
sudo systemctl restart pr-agent-polling
```
