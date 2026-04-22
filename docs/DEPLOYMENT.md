# PR-Agent 部署指南

本文档提供 PR-Agent 自动审查系统的完整部署指南。

## 目录

- [系统要求](#系统要求)
- [Docker 部署（推荐）](#docker-部署推荐)
- [手动部署](#手动部署)
- [配置说明](#配置说明)
- [安全配置](#安全配置)
- [监控和维护](#监控和维护)

## 系统要求

### 硬件要求
- CPU: 2核心以上
- 内存: 4GB 以上
- 磁盘: 20GB 以上可用空间

### 软件要求
- Docker 20.10+ 和 Docker Compose 1.29+（Docker 部署）
- Python 3.9+（手动部署）
- Node.js 18+（前端开发）
- Git 2.0+

## Docker 部署（推荐）

### 1. 克隆仓库

```bash
git clone https://github.com/your-org/pr-agent.git
cd pr-agent
git checkout auto-review
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
nano .env
```

**必须修改的配置：**

```bash
# JWT 密钥（生成随机字符串）
JWT_SECRET_KEY=$(openssl rand -hex 32)

# Bitbucket Server 配置
BITBUCKET_SERVER_URL=https://your-bitbucket-server.com
BITBUCKET_BEARER_TOKEN=your-token-here
```

### 3. 配置 PR-Agent

```bash
# 复制配置模板
cp pr_agent.toml.example pr_agent.toml

# 编辑配置文件
nano pr_agent.toml
```

**关键配置项：**

```toml
[config]
model = "gpt-4o"
git_provider = "bitbucket_server"

[bitbucket_server]
url = "https://your-bitbucket-server.com"
bearer_token = "${BITBUCKET_BEARER_TOKEN}"
enable_polling = true
polling_interval_seconds = 300
polling_repositories = [
    "PROJECT/repo-name"
]

[tokenizer]
local_cache_dir = "/data/tokenizers"
enable_local_cache = true
fallback_to_download = false

[repo_context]
enable_full_context = true
clone_cache_dir = "/data/repos"

[web_platform]
host = "0.0.0.0"
port = 8000
```

### 4. 启动服务

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 查看服务状态
docker-compose ps
```

### 5. 访问 Web 界面

打开浏览器访问：`http://localhost`

**默认登录凭据：**
- 用户名: `admin`
- 密码: `admin123`

**⚠️ 首次登录后请立即修改密码！**

### 6. 预下载 Tokenizer（离线部署）

如果在内网环境部署，需要先在有网络的机器上下载 tokenizer：

```bash
# 在有网络的机器上
docker-compose run --rm backend python -m pr_agent.algo.tokenizer_manager download --models gpt-4o

# 打包 tokenizer 缓存
docker run --rm -v pr-agent_tokenizer-cache:/data alpine tar czf - /data/tokenizers > tokenizers.tar.gz

# 在内网机器上恢复
docker volume create pr-agent_tokenizer-cache
docker run --rm -v pr-agent_tokenizer-cache:/data -i alpine tar xzf - < tokenizers.tar.gz
```

## 手动部署

### 1. 安装后端依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
export JWT_SECRET_KEY="your-secret-key"
export BITBUCKET_SERVER_URL="https://your-bitbucket.com"
export BITBUCKET_BEARER_TOKEN="your-token"
```

### 3. 启动后端服务

```bash
# 启动 Web 平台
python -m pr_agent.servers.web_platform &

# 启动轮询服务
python -m pr_agent.servers.bitbucket_server_polling &
```

### 4. 构建前端

```bash
cd frontend
npm install
npm run build

# 使用 nginx 或其他 web 服务器托管 dist/ 目录
```

### 5. 配置 Nginx（可选）

```nginx
server {
    listen 80;
    server_name pr-agent.example.com;

    # 前端静态文件
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 代理
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Prometheus metrics
    location /metrics {
        proxy_pass http://localhost:8000;
    }
}
```

## 配置说明

### 认证配置

系统使用 JWT 进行认证。配置项：

```bash
JWT_SECRET_KEY=your-secret-key  # 必须修改
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 24小时
```

### 默认用户

系统会自动创建默认管理员用户：
- 用户名: `admin`
- 密码: `admin123`

**生产环境部署前必须修改默认密码！**

### 角色权限

系统支持三种角色：

- **admin**: 完全访问权限
  - 管理用户和 API 密钥
  - 修改系统配置
  - 所有读写操作

- **editor**: 读写权限
  - 管理仓库和 Prompt
  - 查看审查历史
  - 无法管理用户

- **viewer**: 只读权限
  - 查看仪表板
  - 查看审查历史
  - 无法修改任何数据

### API 密钥

管理员可以创建 API 密钥用于程序化访问：

```bash
# 使用 API 密钥访问
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/repositories
```

## 安全配置

### 1. 修改默认密码

首次登录后立即修改：

```bash
# 通过 Web 界面修改，或使用 API
curl -X POST http://localhost:8000/api/auth/change-password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"old_password":"admin123","new_password":"new-secure-password"}'
```

### 2. 生成安全的 JWT 密钥

```bash
# 生成随机密钥
openssl rand -hex 32

# 更新 .env 文件
JWT_SECRET_KEY=<生成的密钥>
```

### 3. 配置 HTTPS

生产环境必须使用 HTTPS：

```bash
# 使用 Let's Encrypt
certbot --nginx -d pr-agent.example.com
```

### 4. 限制网络访问

```yaml
# docker-compose.yml
services:
  backend:
    ports:
      - "127.0.0.1:8000:8000"  # 仅本地访问
```

### 5. 定期备份

```bash
# 备份数据库
docker cp pr-agent-backend:/data/db/pr_agent.db ./backup/

# 备份配置
cp pr_agent.toml ./backup/
cp .env ./backup/
```

## 监控和维护

### 健康检查

```bash
# 检查服务状态
curl http://localhost:8000/api/health

# 查看 Prometheus metrics
curl http://localhost:8000/metrics
```

### 日志查看

```bash
# Docker 日志
docker-compose logs -f backend
docker-compose logs -f polling
docker-compose logs -f frontend

# 系统日志（通过 API）
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/logs?level=error&limit=100"
```

### 性能监控

系统集成了 Prometheus metrics，可以配置 Grafana 进行可视化监控：

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'pr-agent'
    static_configs:
      - targets: ['localhost:8000']
```

### 数据清理

```bash
# 清理旧的仓库缓存
docker-compose exec backend python -c "
from pr_agent.algo.repo_context_analyzer import RepoContextAnalyzer
analyzer = RepoContextAnalyzer()
analyzer.cleanup_old_clones(days=30)
"

# 清理轮询状态
docker-compose exec backend python -c "
from pr_agent.storage.polling_state import PollingState
state = PollingState()
state.cleanup_old_entries(days=30)
"
```

### 更新部署

```bash
# 拉取最新代码
git pull origin auto-review

# 重新构建并重启
docker-compose down
docker-compose build
docker-compose up -d
```

## 故障排查

### 服务无法启动

```bash
# 检查日志
docker-compose logs backend

# 检查配置文件
docker-compose config

# 验证环境变量
docker-compose exec backend env | grep JWT
```

### 认证失败

```bash
# 检查 JWT 配置
docker-compose exec backend python -c "
import os
print('JWT_SECRET_KEY:', os.getenv('JWT_SECRET_KEY'))
"

# 重置管理员密码（需要直接访问数据库）
docker-compose exec backend python -c "
from pr_agent.security.auth import AuthManager
auth = AuthManager()
auth.create_user('admin', 'new-password', 'admin@example.com', 'admin')
"
```

### 轮询服务不工作

```bash
# 检查轮询日志
docker-compose logs polling

# 验证 Bitbucket 连接
docker-compose exec backend python -c "
from pr_agent.git_providers.bitbucket_server_provider import BitbucketServerProvider
provider = BitbucketServerProvider()
repos = provider.list_pull_requests('PROJECT', 'repo-name')
print(repos)
"
```

## 支持

如有问题，请：
1. 查看日志文件
2. 检查配置是否正确
3. 访问项目 GitHub Issues
4. 联系技术支持团队
