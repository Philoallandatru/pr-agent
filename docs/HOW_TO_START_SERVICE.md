# 如何启动PR事件监听服务

本文档说明如何启动不同的PR事件监听服务。

---

## 概述

PR-Agent支持多种部署模式来监听PR事件：

1. **Webhook服务器** - 被动接收Git平台的webhook推送
2. **轮询模式** - 主动定期查询PR状态
3. **GitHub Action** - 在GitHub Actions中触发
4. **CLI模式** - 手动命令行触发

---

## 方法1: Webhook服务器（推荐）

### Bitbucket Server Webhook

最简单的方式是使用我们提供的启动脚本：

```bash
# Linux/macOS
./start_webhook.sh

# Windows
start_webhook.bat
```

脚本会自动：
- ✅ 检查环境变量
- ✅ 检查依赖
- ✅ 提供交互式模式选择

**手动启动：**

```bash
# 1. 设置环境变量
export BITBUCKET_URL="https://bitbucket.example.com"
export BITBUCKET_TOKEN="your_personal_access_token"
export OPENAI_API_KEY="sk-your-openai-key"

# 2a. 开发模式（单进程，热重载）
python -m pr_agent.servers.bitbucket_server_webhook

# 2b. 生产模式（多进程）
gunicorn pr_agent.servers.bitbucket_server_webhook:app \
  --config pr_agent/servers/gunicorn_config.py

# 2c. 使用uvicorn（推荐开发）
uvicorn pr_agent.servers.bitbucket_server_webhook:app \
  --host 0.0.0.0 \
  --port 3000 \
  --reload
```

**Docker方式：**

```bash
docker-compose up -d
```

### GitHub Webhook

```bash
# 设置环境变量
export GITHUB_TOKEN="ghp_your_token"
export OPENAI_API_KEY="sk-your-key"

# 启动GitHub App服务器
python -m pr_agent.servers.github_app

# 或使用gunicorn
gunicorn pr_agent.servers.github_app:app \
  --bind 0.0.0.0:3000 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker
```

### GitLab Webhook

```bash
# 设置环境变量
export GITLAB_PERSONAL_ACCESS_TOKEN="your_token"
export GITLAB_URL="https://gitlab.com"
export OPENAI_API_KEY="sk-your-key"

# 启动GitLab webhook服务器
python -m pr_agent.servers.gitlab_webhook
```

---

## 方法2: 轮询模式

轮询模式会定期检查PR状态，无需配置webhook。

### Bitbucket Server 轮询

```bash
# 设置环境变量
export BITBUCKET_URL="https://bitbucket.example.com"
export BITBUCKET_TOKEN="your_token"
export OPENAI_API_KEY="sk-your-key"

# 启动轮询服务
python pr_agent/servers/bitbucket_server_polling.py
```

**配置轮询参数：**

在 `.pr_agent.toml` 中：

```toml
[bitbucket_server]
# 轮询间隔（秒）
polling_interval_seconds = 60

# 审查模式
# "once" - 每个PR只审查一次
# "on_update" - PR更新时重新审查
polling_review_mode = "once"

# 状态文件路径（绝对路径）
polling_state_file = "C:/path/to/polling_state.json"
```

### GitHub 轮询

```bash
export GITHUB_TOKEN="ghp_your_token"
export OPENAI_API_KEY="sk-your-key"

python pr_agent/servers/github_polling.py
```

---

## 方法3: GitHub Actions

在仓库中创建 `.github/workflows/pr-agent.yml`：

```yaml
name: PR Agent

on:
  pull_request:
    types: [opened, reopened, ready_for_review, synchronize]
  issue_comment:

jobs:
  pr_agent_job:
    runs-on: ubuntu-latest
    name: Run PR Agent
    steps:
      - name: PR Agent action
        uses: Codium-ai/pr-agent@main
        env:
          OPENAI_KEY: ${{ secrets.OPENAI_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## 方法4: CLI手动模式

```bash
# 审查PR
python -m pr_agent.cli \
  --pr_url https://github.com/owner/repo/pull/123 \
  review

# 生成PR描述
python -m pr_agent.cli \
  --pr_url https://github.com/owner/repo/pull/123 \
  describe

# 提供代码改进建议
python -m pr_agent.cli \
  --pr_url https://github.com/owner/repo/pull/123 \
  improve
```

---

## 环境变量配置

### 必需变量

**Bitbucket Server:**
```bash
export BITBUCKET_URL="https://bitbucket.example.com"
export BITBUCKET_TOKEN="your_personal_access_token"
```

**GitHub:**
```bash
export GITHUB_TOKEN="ghp_your_token"
# 或使用 GitHub App
export GITHUB_APP_ID="123456"
export GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----..."
```

**GitLab:**
```bash
export GITLAB_PERSONAL_ACCESS_TOKEN="your_token"
export GITLAB_URL="https://gitlab.com"
```

**AI模型（至少一个）:**
```bash
export OPENAI_API_KEY="sk-your-key"
# 或
export ANTHROPIC_API_KEY="sk-ant-your-key"
# 或
export AZURE_OPENAI_API_KEY="your-azure-key"
```

### 可选变量

```bash
# 服务器配置
export PORT=3000
export HOST=0.0.0.0

# 数据库路径
export DATABASE_PATH="./pr_agent.db"

# 日志级别
export LOG_LEVEL=INFO

# Webhook密钥（可选，用于验证webhook来源）
export WEBHOOK_SECRET="your_secret"
```

---

## 配置Git平台Webhook

### Bitbucket Server

1. 进入项目或仓库设置 → **Webhooks**
2. 点击 **Create webhook**
3. 配置：
   - **Name**: PR Agent
   - **URL**: `http://your-server:3000/webhook`
   - **Status**: Active ✅
4. 选择触发事件：
   - ✅ Pull Request → Opened
   - ✅ Pull Request → Source branch updated
   - ✅ Pull Request → Comment added
5. 保存

### GitHub

1. 进入仓库设置 → **Webhooks**
2. 点击 **Add webhook**
3. 配置：
   - **Payload URL**: `http://your-server:3000/webhook`
   - **Content type**: application/json
   - **Secret**: (可选) 设置webhook密钥
4. 选择事件：
   - ✅ Pull requests
   - ✅ Issue comments
5. 保存

### GitLab

1. 进入项目设置 → **Webhooks**
2. 配置：
   - **URL**: `http://your-server:3000/webhook`
   - **Secret Token**: (可选)
3. 选择触发器：
   - ✅ Merge request events
   - ✅ Comments
4. 添加webhook

---

## 验证服务是否运行

```bash
# 健康检查
curl http://localhost:3000/

# 预期输出
{"status":"ok"}

# 查看日志（如果使用systemd）
sudo journalctl -u pr-agent-webhook -f

# 查看日志（Docker）
docker-compose logs -f
```

---

## 使用systemd管理服务（Linux推荐）

### 创建服务文件

`/etc/systemd/system/pr-agent-webhook.service`：

```ini
[Unit]
Description=PR Agent Webhook Service
After=network.target

[Service]
Type=notify
User=pr-agent
Group=pr-agent
WorkingDirectory=/opt/pr-agent
Environment="PATH=/opt/pr-agent/.venv/bin"
EnvironmentFile=/opt/pr-agent/.env
ExecStart=/opt/pr-agent/.venv/bin/gunicorn pr_agent.servers.bitbucket_server_webhook:app --config pr_agent/servers/gunicorn_config.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 管理服务

```bash
# 启用服务
sudo systemctl enable pr-agent-webhook

# 启动服务
sudo systemctl start pr-agent-webhook

# 查看状态
sudo systemctl status pr-agent-webhook

# 查看日志
sudo journalctl -u pr-agent-webhook -f

# 重启服务
sudo systemctl restart pr-agent-webhook

# 停止服务
sudo systemctl stop pr-agent-webhook
```

---

## 使用Windows服务（Windows推荐）

### 使用NSSM

1. 下载NSSM: https://nssm.cc/download
2. 安装服务：

```cmd
nssm install PRAgent "C:\path\to\python.exe" "C:\path\to\pr-agent\pr_agent\servers\bitbucket_server_webhook.py"
nssm set PRAgent AppDirectory "C:\path\to\pr-agent"
nssm set PRAgent AppEnvironmentExtra BITBUCKET_URL=https://bitbucket.example.com BITBUCKET_TOKEN=your_token OPENAI_API_KEY=sk-your-key
nssm start PRAgent
```

3. 管理服务：
```cmd
nssm start PRAgent
nssm stop PRAgent
nssm restart PRAgent
nssm status PRAgent
```

---

## 测试服务

运行测试脚本验证服务是否正常：

```bash
# 测试webhook服务器
python test_webhook.py --url http://localhost:3000

# 测试监控功能
python test_monitoring.py
```

---

## 故障排查

### 服务无法启动

```bash
# 检查环境变量
echo $BITBUCKET_URL
echo $BITBUCKET_TOKEN
echo $OPENAI_API_KEY

# 检查端口占用
netstat -tlnp | grep 3000  # Linux
netstat -ano | findstr :3000  # Windows

# 检查日志
tail -f webhook_server.log
```

### Webhook未触发

1. 检查webhook配置是否正确
2. 检查防火墙是否允许入站连接
3. 检查服务器日志是否收到请求
4. 在Git平台查看webhook发送历史

### PR未被审查

1. 检查配置文件中是否启用了自动审查
2. 检查PR是否被过滤规则忽略
3. 查看数据库确认是否已审查过
4. 检查服务器日志获取详细错误

---

## 性能调优

### 增加并发处理能力

```bash
# 使用更多worker
gunicorn pr_agent.servers.bitbucket_server_webhook:app \
  --workers 8 \
  --worker-class uvicorn.workers.UvicornWorker \
  --timeout 300
```

### 使用反向代理（Nginx）

```nginx
upstream pr_agent_backend {
    server 127.0.0.1:3000;
    server 127.0.0.1:3001;
    server 127.0.0.1:3002;
}

server {
    listen 80;
    server_name webhook.example.com;

    location / {
        proxy_pass http://pr_agent_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
    }
}
```

---

## 监控和日志

### 启用效率监控

```toml
[efficiency_metrics]
enabled = true
database_path = "pr_agent.db"
prometheus_enabled = true
```

### 查看监控数据

```bash
# SQLite仪表板
python monitor_efficiency.py

# Web界面
python web_monitor.py
```

### 日志轮转

```bash
# /etc/logrotate.d/pr-agent-webhook
/var/log/pr-agent/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 pr-agent pr-agent
    postrotate
        systemctl reload pr-agent-webhook
    endscript
}
```

---

## 相关文档

- [Bitbucket Server Webhook完整指南](docs/BITBUCKET_SERVER_WEBHOOK.md)
- [Bitbucket Server快速入门](docs/BITBUCKET_SERVER_QUICKSTART.md)
- [监控指南](docs/MONITORING_GUIDE.md)
- [配置说明](pr_agent/settings/configuration.toml)

---

## 快速启动命令总结

```bash
# Bitbucket Server Webhook（推荐）
./start_webhook.sh

# Bitbucket Server Polling
python pr_agent/servers/bitbucket_server_polling.py

# GitHub Webhook
python -m pr_agent.servers.github_app

# GitLab Webhook
python -m pr_agent.servers.gitlab_webhook

# CLI手动触发
python -m pr_agent.cli --pr_url <url> review
```
