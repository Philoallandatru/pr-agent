# Bitbucket Server Webhook 配置和启动指南

本指南介绍如何为 Bitbucket Server 配置 webhook 并启动 PR Agent 服务器。

## 目录

- [前置要求](#前置要求)
- [环境变量配置](#环境变量配置)
- [启动服务器](#启动服务器)
  - [开发环境](#开发环境)
  - [生产环境](#生产环境)
- [配置 Bitbucket Server Webhook](#配置-bitbucket-server-webhook)
- [验证和测试](#验证和测试)
- [故障排查](#故障排查)
- [Docker 部署](#docker-部署可选)

---

## 前置要求

1. **Python 3.8+** 已安装
2. **PR Agent** 已安装：`pip install -e .`
3. **Bitbucket Server** 管理员权限（用于配置 webhook）
4. **网络访问**：Bitbucket Server 能够访问 webhook 服务器的 URL

---

## 环境变量配置

在启动服务器之前，需要配置以下环境变量。推荐使用 `.env` 文件：

### 创建 `.env` 文件

在项目根目录创建 `.env` 文件：

```bash
# Bitbucket Server 配置
BITBUCKET_URL=https://bitbucket.example.com
BITBUCKET_TOKEN=your_personal_access_token_here

# OpenAI API 配置（如果使用 OpenAI 模型）
OPENAI_API_KEY=sk-your-openai-api-key

# 或者使用其他 AI 提供商
# ANTHROPIC_API_KEY=your_anthropic_key
# AZURE_OPENAI_API_KEY=your_azure_key

# 服务器配置（可选）
WEBHOOK_PORT=3000
WEBHOOK_HOST=0.0.0.0

# 数据库路径（可选，默认为 pr_agent.db）
DATABASE_PATH=./pr_agent.db

# 日志级别（可选）
LOG_LEVEL=INFO
```

### 环境变量说明

| 变量名 | 必需 | 说明 | 示例 |
|--------|------|------|------|
| `BITBUCKET_URL` | ✅ | Bitbucket Server 的基础 URL | `https://bitbucket.example.com` |
| `BITBUCKET_TOKEN` | ✅ | Bitbucket 个人访问令牌（需要 PR 读写权限） | `MTIzNDU2Nzg5...` |
| `OPENAI_API_KEY` | ✅* | OpenAI API 密钥 | `sk-...` |
| `WEBHOOK_PORT` | ❌ | Webhook 服务器端口（默认 3000） | `3000` |
| `WEBHOOK_HOST` | ❌ | 监听地址（默认 0.0.0.0） | `0.0.0.0` |
| `DATABASE_PATH` | ❌ | SQLite 数据库路径 | `./pr_agent.db` |

*至少需要配置一个 AI 提供商的 API 密钥

### 获取 Bitbucket 个人访问令牌

1. 登录 Bitbucket Server
2. 点击右上角头像 → **Manage account**
3. 左侧菜单选择 **Personal access tokens**
4. 点击 **Create a token**
5. 设置权限：
   - **Project permissions**: Read
   - **Repository permissions**: Read, Write
   - **Pull request permissions**: Read, Write
6. 复制生成的令牌（只显示一次）

---

## 启动服务器

### 开发环境

适用于本地测试和开发：

```bash
# 方法 1：直接运行 Python 模块
python -m pr_agent.servers.bitbucket_server_webhook

# 方法 2：使用 uvicorn（推荐，支持热重载）
uvicorn pr_agent.servers.bitbucket_server_webhook:app --host 0.0.0.0 --port 3000 --reload
```

**输出示例：**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:3000 (Press CTRL+C to quit)
```

### 生产环境

使用 Gunicorn 实现多进程部署，提高并发处理能力：

```bash
# 使用项目提供的 gunicorn 配置
gunicorn pr_agent.servers.bitbucket_server_webhook:app \
  --config pr_agent/servers/gunicorn_config.py

# 或者自定义配置
gunicorn pr_agent.servers.bitbucket_server_webhook:app \
  --bind 0.0.0.0:3000 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
```

**参数说明：**
- `--workers 4`：4 个工作进程（推荐设置为 CPU 核心数 × 2）
- `--worker-class uvicorn.workers.UvicornWorker`：使用 ASGI worker
- `--timeout 120`：请求超时时间（秒）
- `--access-logfile -`：访问日志输出到 stdout
- `--error-logfile -`：错误日志输出到 stderr

### 使用 systemd 管理服务（Linux）

创建 systemd 服务文件 `/etc/systemd/system/pr-agent-webhook.service`：

```ini
[Unit]
Description=PR Agent Bitbucket Server Webhook
After=network.target

[Service]
Type=notify
User=pr-agent
Group=pr-agent
WorkingDirectory=/opt/pr-agent
Environment="PATH=/opt/pr-agent/venv/bin"
EnvironmentFile=/opt/pr-agent/.env
ExecStart=/opt/pr-agent/venv/bin/gunicorn pr_agent.servers.bitbucket_server_webhook:app \
  --config pr_agent/servers/gunicorn_config.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable pr-agent-webhook
sudo systemctl start pr-agent-webhook
sudo systemctl status pr-agent-webhook
```

---

## 配置 Bitbucket Server Webhook

### 1. 访问 Webhook 设置

有两种配置级别：

#### 选项 A：仓库级别 Webhook

1. 进入目标仓库
2. 点击左侧 **Repository settings**
3. 选择 **Webhooks**
4. 点击 **Create webhook**

#### 选项 B：项目级别 Webhook（推荐）

1. 进入目标项目
2. 点击左侧 **Project settings**
3. 选择 **Webhooks**
4. 点击 **Create webhook**

### 2. 配置 Webhook

填写以下信息：

| 字段 | 值 | 说明 |
|------|-----|------|
| **Name** | `PR Agent Webhook` | 自定义名称 |
| **URL** | `http://your-server:3000/webhook` | Webhook 服务器地址 |
| **Status** | ✅ Active | 启用 webhook |
| **SSL/TLS** | 根据实际情况 | 如果使用 HTTPS，勾选验证证书 |

### 3. 选择触发事件

勾选以下事件：

- ✅ **Pull Request**
  - ✅ Opened
  - ✅ Modified
  - ✅ Source branch updated
  - ✅ Commented
  - ❌ Merged（可选）
  - ❌ Declined（可选）

### 4. 配置认证（可选）

如果需要验证 webhook 请求来源：

1. 在 **Secret** 字段输入一个随机字符串
2. 在服务器的 `.env` 文件中添加：
   ```bash
   WEBHOOK_SECRET=your_secret_here
   ```

### 5. 保存配置

点击 **Create** 保存 webhook 配置。

---

## 验证和测试

### 1. 检查服务器健康状态

```bash
# 健康检查端点
curl http://localhost:3000/ready

# 预期输出
{"status":"ready"}
```

### 2. 查看服务器日志

```bash
# 如果使用 systemd
sudo journalctl -u pr-agent-webhook -f

# 如果直接运行
# 日志会输出到终端
```

### 3. 测试 Webhook

在 Bitbucket Server 中：

1. 进入 webhook 配置页面
2. 找到刚创建的 webhook
3. 点击 **Test connection** 或 **View details**
4. 查看最近的请求历史

或者创建一个测试 PR：

1. 在配置了 webhook 的仓库中创建新 PR
2. 观察服务器日志，应该看到类似输出：
   ```
   INFO: Received webhook event: pr:opened
   INFO: Processing PR #123 in project/repo
   INFO: Starting PR review...
   ```

### 4. 验证 PR 评论

检查 PR 页面是否出现 AI 生成的评论。

---

## 故障排查

### 问题 1：Webhook 请求失败

**症状：** Bitbucket 显示 webhook 请求失败（红色 ❌）

**排查步骤：**

1. **检查网络连接**
   ```bash
   # 从 Bitbucket Server 主机测试连接
   curl http://your-webhook-server:3000/ready
   ```

2. **检查防火墙规则**
   ```bash
   # 确保端口 3000 已开放
   sudo firewall-cmd --list-ports
   sudo ufw status
   ```

3. **检查服务器日志**
   ```bash
   # 查看是否收到请求
   sudo journalctl -u pr-agent-webhook -n 50
   ```

### 问题 2：服务器启动失败

**症状：** 服务器无法启动或立即退出

**排查步骤：**

1. **检查环境变量**
   ```bash
   # 验证必需的环境变量
   echo $BITBUCKET_URL
   echo $BITBUCKET_TOKEN
   echo $OPENAI_API_KEY
   ```

2. **检查端口占用**
   ```bash
   # Linux
   sudo netstat -tlnp | grep 3000
   
   # Windows
   netstat -ano | findstr :3000
   ```

3. **检查依赖安装**
   ```bash
   pip list | grep -E "fastapi|uvicorn|gunicorn"
   ```

### 问题 3：PR 没有被审查

**症状：** Webhook 触发成功，但 PR 没有评论

**排查步骤：**

1. **检查数据库记录**
   ```bash
   sqlite3 pr_agent.db "SELECT * FROM pr_reviews ORDER BY created_at DESC LIMIT 5;"
   ```

2. **检查配置文件**
   ```bash
   # 确认 skip_reviewed_prs 设置
   grep "skip_reviewed_prs" pr_agent/settings/configuration.toml
   ```

3. **检查 Bitbucket 权限**
   - 确认 token 有 PR 写入权限
   - 确认 token 未过期

4. **查看详细日志**
   ```bash
   # 设置 DEBUG 日志级别
   export LOG_LEVEL=DEBUG
   # 重启服务器
   ```

### 问题 4：性能问题

**症状：** Webhook 响应慢或超时

**解决方案：**

1. **增加 worker 数量**
   ```bash
   gunicorn ... --workers 8
   ```

2. **增加超时时间**
   ```bash
   gunicorn ... --timeout 300
   ```

3. **使用异步处理**
   - Webhook 已经使用异步处理，确保不要阻塞主线程

4. **监控资源使用**
   ```bash
   # CPU 和内存使用
   top -p $(pgrep -f gunicorn)
   ```

---

## Docker 部署（可选）

### 创建 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 安装 PR Agent
RUN pip install -e .

# 暴露端口
EXPOSE 3000

# 启动命令
CMD ["gunicorn", "pr_agent.servers.bitbucket_server_webhook:app", \
     "--bind", "0.0.0.0:3000", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--timeout", "120"]
```

### 创建 docker-compose.yml

```yaml
version: '3.8'

services:
  pr-agent-webhook:
    build: .
    ports:
      - "3000:3000"
    environment:
      - BITBUCKET_URL=${BITBUCKET_URL}
      - BITBUCKET_TOKEN=${BITBUCKET_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - LOG_LEVEL=INFO
    volumes:
      - ./pr_agent.db:/app/pr_agent.db
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/ready"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 启动 Docker 容器

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

---

## 高级配置

### 反向代理（Nginx）

如果需要通过 HTTPS 暴露 webhook：

```nginx
server {
    listen 443 ssl http2;
    server_name webhook.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 增加超时时间（PR 审查可能需要较长时间）
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}
```

### 负载均衡

如果需要高可用部署，可以运行多个实例并使用负载均衡器：

```nginx
upstream pr_agent_backend {
    server 10.0.1.10:3000;
    server 10.0.1.11:3000;
    server 10.0.1.12:3000;
}

server {
    listen 80;
    server_name webhook.example.com;

    location / {
        proxy_pass http://pr_agent_backend;
        # ... 其他配置
    }
}
```

---

## 监控和维护

### 日志轮转

创建 `/etc/logrotate.d/pr-agent-webhook`：

```
/var/log/pr-agent/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 pr-agent pr-agent
    sharedscripts
    postrotate
        systemctl reload pr-agent-webhook
    endscript
}
```

### 监控指标

如果启用了 Prometheus 监控，可以访问：

```bash
curl http://localhost:3000/metrics
```

参考 [MONITORING_GUIDE.md](./MONITORING_GUIDE.md) 了解详细的监控配置。

---

## 相关文档

- [监控指南](./MONITORING_GUIDE.md) - AI 效率指标监控
- [快速入门](../MONITORING_QUICKSTART.md) - 5 分钟快速配置
- [配置文件说明](../pr_agent/settings/configuration.toml) - 完整配置选项

---

## 支持

如有问题，请：

1. 查看 [故障排查](#故障排查) 部分
2. 检查服务器日志
3. 提交 GitHub Issue 并附上日志信息
