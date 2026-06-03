# Bitbucket Server Webhook 快速启动

本文档提供最简单的方式启动 Bitbucket Server webhook 服务。

---

## 方法 1：使用启动脚本（推荐）

### Linux/macOS

```bash
# 1. 设置环境变量
export BITBUCKET_URL="https://bitbucket.example.com"
export BITBUCKET_TOKEN="your_personal_access_token"
export OPENAI_API_KEY="sk-your-openai-key"

# 2. 运行启动脚本
./start_webhook.sh

# 3. 选择启动模式
#    1 - 开发模式（推荐用于测试）
#    2 - 生产模式（多进程）
#    3 - 后台运行
```

### Windows

```cmd
# 1. 设置环境变量
set BITBUCKET_URL=https://bitbucket.example.com
set BITBUCKET_TOKEN=your_personal_access_token
set OPENAI_API_KEY=sk-your-openai-key

# 2. 运行启动脚本
start_webhook.bat

# 3. 选择启动模式
#    1 - 开发模式（推荐）
#    3 - 后台运行
```

---

## 方法 2：直接运行 Python 命令

### 最简单的方式（开发模式）

```bash
# 设置环境变量
export BITBUCKET_URL="https://bitbucket.example.com"
export BITBUCKET_TOKEN="your_token"
export OPENAI_API_KEY="sk-your-key"

# 启动服务
python -m pr_agent.servers.bitbucket_server_webhook
```

服务将在 `http://0.0.0.0:3000` 启动。

### 使用 uvicorn（支持热重载）

```bash
uvicorn pr_agent.servers.bitbucket_server_webhook:app \
  --host 0.0.0.0 \
  --port 3000 \
  --reload
```

### 生产环境（使用 Gunicorn）

```bash
gunicorn pr_agent.servers.bitbucket_server_webhook:app \
  --bind 0.0.0.0:3000 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --timeout 240 \
  --access-logfile - \
  --error-logfile -
```

---

## 方法 3：使用 .env 文件（推荐）

### 1. 创建 .env 文件

```bash
cat > .env << 'EOF'
# Bitbucket Server 配置
BITBUCKET_URL=https://bitbucket.example.com
BITBUCKET_TOKEN=MTIzNDU2Nzg5...

# AI 模型配置（选择一个）
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# AZURE_OPENAI_API_KEY=...

# 可选配置
PORT=3000
HOST=0.0.0.0
LOG_LEVEL=INFO
DATABASE_PATH=./pr_agent.db
EOF
```

### 2. 加载环境变量并启动

**Linux/macOS:**
```bash
# 加载 .env
export $(cat .env | grep -v '^#' | xargs)

# 启动服务
./start_webhook.sh
```

**Windows (PowerShell):**
```powershell
# 加载 .env
Get-Content .env | ForEach-Object {
    if ($_ -match '^([^=]+)=(.*)$') {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2])
    }
}

# 启动服务
.\start_webhook.bat
```

---

## 方法 4：Docker 部署

### 1. 创建 docker-compose.yml

```yaml
version: '3.8'

services:
  pr-agent-webhook:
    image: python:3.11-slim
    working_dir: /app
    ports:
      - "3000:3000"
    environment:
      - BITBUCKET_URL=${BITBUCKET_URL}
      - BITBUCKET_TOKEN=${BITBUCKET_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - .:/app
      - ./pr_agent.db:/app/pr_agent.db
    command: >
      bash -c "
        pip install -e . &&
        python -m pr_agent.servers.bitbucket_server_webhook
      "
    restart: unless-stopped
```

### 2. 启动容器

```bash
# 使用 .env 文件
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

---

## 配置 Bitbucket Server Webhook

服务启动后，在 Bitbucket Server 中配置 webhook：

### 1. 进入仓库或项目设置

- **仓库级别**: Repository → Settings → Webhooks
- **项目级别**: Project → Settings → Webhooks（推荐）

### 2. 创建 Webhook

| 配置项 | 值 |
|--------|-----|
| **Name** | PR Agent |
| **URL** | `http://your-server-ip:3000/webhook` |
| **Status** | Active ✅ |

### 3. 选择触发事件

勾选以下事件：
- ✅ **Pull Request → Opened**
- ✅ **Pull Request → Source branch updated**
- ✅ **Pull Request → Comment added**

### 4. 保存并测试

点击 **Create**，然后：
- 点击 **Test connection** 验证连接
- 或创建一个测试 PR 查看效果

---

## 验证服务是否运行

```bash
# 检查服务健康状态
curl http://localhost:3000/

# 预期输出
{"status":"ok"}
```

---

## 查看日志

### 直接运行模式
日志会直接输出到终端

### 后台运行模式

**Linux/macOS:**
```bash
tail -f webhook_server.log
```

**Windows:**
```cmd
type webhook_server.log
```

### Docker 模式
```bash
docker-compose logs -f pr-agent-webhook
```

---

## 停止服务

### 直接运行模式
按 `Ctrl+C`

### 后台运行模式

**Linux/macOS:**
```bash
# 如果使用 start_webhook.sh 后台模式
kill $(cat webhook_server.pid)
```

**Windows:**
在任务管理器中结束 `python.exe` 进程

### Docker 模式
```bash
docker-compose down
```

---

## 常见问题

### Q: 服务启动失败，提示环境变量未设置

**A:** 确保已设置以下环境变量：
```bash
echo $BITBUCKET_URL
echo $BITBUCKET_TOKEN
echo $OPENAI_API_KEY
```

如果为空，请重新设置。

### Q: Webhook 连接测试失败

**A:** 检查：
1. 服务是否正在运行：`curl http://localhost:3000/`
2. 防火墙是否允许端口 3000
3. Bitbucket Server 能否访问 webhook 服务器的 IP

### Q: PR 创建后没有自动审查

**A:** 检查：
1. Webhook 是否触发成功（查看 Bitbucket webhook 历史）
2. 查看服务器日志是否有错误
3. 确认 Bitbucket Token 有 PR 读写权限

### Q: 如何更改端口？

**A:** 设置 `PORT` 环境变量：
```bash
export PORT=8080
./start_webhook.sh
```

---

## 下一步

- ✅ 配置自动审查规则：编辑 `.pr_agent.toml`
- ✅ 启用效率监控：参考 [MONITORING_QUICKSTART.md](../MONITORING_QUICKSTART.md)
- ✅ 查看完整文档：[BITBUCKET_SERVER_WEBHOOK.md](./BITBUCKET_SERVER_WEBHOOK.md)

---

## 获取帮助

完整文档：[docs/BITBUCKET_SERVER_WEBHOOK.md](./BITBUCKET_SERVER_WEBHOOK.md)

如有问题：
1. 检查服务器日志
2. 查看 [故障排查](./BITBUCKET_SERVER_WEBHOOK.md#故障排查)
3. 提交 GitHub Issue
