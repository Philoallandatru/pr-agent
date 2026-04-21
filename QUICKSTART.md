# PR-Agent 自动审查系统 - 快速开始

本项目是 PR-Agent 的增强版本，专为企业内网部署设计，支持 Bitbucket Server 自动监控和全代码库上下文分析。

## 主要特性

### ✅ 已实现功能

1. **本地 Tokenizer 缓存** - 支持完全离线部署
2. **Bitbucket Server 轮询** - 自动监控 PR 变化并触发审查
3. **全代码库上下文分析** - 基于完整仓库的智能审查
4. **Web 管理平台** - 现代化的管理界面
5. **JWT 认证系统** - 安全的用户认证和权限控制
6. **监控和可观测性** - Prometheus metrics 和结构化日志
7. **Docker 部署** - 一键部署所有服务

## 快速开始

### 前置要求

- Docker 20.10+
- Docker Compose 1.29+
- 2核心 CPU，4GB 内存，20GB 磁盘空间

### 一键部署

**Linux/Mac:**
```bash
git clone https://github.com/your-org/pr-agent.git
cd pr-agent
git checkout auto-review
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

**Windows:**
```cmd
git clone https://github.com/your-org/pr-agent.git
cd pr-agent
git checkout auto-review
scripts\deploy.bat
```

### 访问系统

部署完成后，访问：
- **Web 界面**: http://localhost
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/api/health

**默认登录凭据:**
- 用户名: `admin`
- 密码: `admin123`

⚠️ **首次登录后请立即修改密码！**

## 配置说明

### 环境变量配置

编辑 `.env` 文件：

```bash
# JWT 配置（必须修改）
JWT_SECRET_KEY=your-secure-random-string

# Bitbucket Server 配置
BITBUCKET_SERVER_URL=https://your-bitbucket.com
BITBUCKET_BEARER_TOKEN=your-token

# AI 模型配置
OPENAI_API_KEY=your-openai-key  # 如果使用 OpenAI
```

### PR-Agent 配置

编辑 `pr_agent.toml` 文件：

```toml
[config]
model = "gpt-4o"
git_provider = "bitbucket_server"

[bitbucket_server]
url = "https://your-bitbucket.com"
bearer_token = "${BITBUCKET_BEARER_TOKEN}"
enable_polling = true
polling_interval_seconds = 300
polling_repositories = [
    "PROJECT/repo-name"
]

[tokenizer]
local_cache_dir = "/data/tokenizers"
enable_local_cache = true
fallback_to_download = false  # 内网部署设为 false

[repo_context]
enable_full_context = true
clone_cache_dir = "/data/repos"
max_related_files = 20
```

## 功能详解

### 1. 本地 Tokenizer 缓存

支持完全离线部署，无需访问 HuggingFace：

```bash
# 预下载 tokenizer
docker-compose run --rm backend python -m pr_agent.algo.tokenizer_manager download --models gpt-4o

# 查看缓存状态
docker-compose run --rm backend python -m pr_agent.algo.tokenizer_manager list
```

### 2. Bitbucket Server 自动监控

自动轮询配置的仓库，检测 PR 变化并触发审查：

- 支持多仓库监控
- 自动检测 PR 更新
- 持久化状态管理
- 并行处理支持

### 3. 全代码库上下文分析

不仅分析 PR diff，还会：
- 克隆完整仓库
- 解析依赖关系（支持 Python/Java/JS/Go/TS/C#）
- 加载相关文件内容
- 提供更准确的审查建议

### 4. Web 管理平台

功能包括：
- 📊 Dashboard - 审查统计和系统状态
- 📁 仓库管理 - 配置监控的仓库
- 📝 审查历史 - 查看所有审查记录
- ✏️ Prompt 编辑器 - 自定义审查提示词
- 👥 用户管理 - 管理用户和权限
- 🔑 API 密钥 - 创建程序化访问密钥

### 5. 认证和权限

三种角色：
- **Admin**: 完全访问权限
- **Editor**: 读写权限
- **Viewer**: 只读权限

支持：
- JWT Token 认证
- API Key 认证
- 基于角色的访问控制（RBAC）

### 6. 监控和日志

- Prometheus metrics 端点: `/metrics`
- 结构化 JSON 日志
- 系统健康检查: `/api/health`
- 审查性能追踪

## 常用命令

### 服务管理

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 查看日志
docker-compose logs -f

# 重启服务
docker-compose restart

# 查看服务状态
docker-compose ps
```

### 数据备份

```bash
# 备份数据
./scripts/backup.sh

# 恢复数据
./scripts/restore.sh backups/pr-agent-backup-20240101_120000.tar.gz
```

### 维护操作

```bash
# 清理旧的仓库缓存
docker-compose exec backend python -c "
from pr_agent.algo.repo_context_analyzer import RepoContextAnalyzer
analyzer = RepoContextAnalyzer()
analyzer.cleanup_old_clones(days=30)
"

# 查看数据库统计
docker-compose exec backend python -c "
from pr_agent.storage.database import Database
db = Database()
print(db.get_statistics())
"
```

## 架构说明

```
┌─────────────────┐
│   Frontend      │  React + TypeScript
│   (Port 80)     │  Material-UI
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Backend       │  FastAPI + SQLite
│   (Port 8000)   │  JWT Auth
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Polling Service │  Async Polling
│                 │  State Management
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Bitbucket Server│  PR Monitoring
│                 │  Code Review
└─────────────────┘
```

## 文档

详细文档请参考：

- [部署指南](docs/DEPLOYMENT.md) - 完整的部署说明
- [安全配置](docs/SECURITY.md) - 认证和安全最佳实践
- [Tokenizer 缓存](docs/TOKENIZER_CACHING.md) - 离线部署配置
- [Bitbucket 轮询](docs/BITBUCKET_POLLING.md) - 自动监控配置
- [仓库上下文](docs/REPO_CONTEXT.md) - 全代码库分析
- [监控指南](docs/MONITORING.md) - Prometheus 和日志

## 故障排查

### 服务无法启动

```bash
# 检查日志
docker-compose logs backend

# 验证配置
docker-compose config
```

### 认证失败

```bash
# 检查 JWT 配置
docker-compose exec backend env | grep JWT

# 重置管理员密码
docker-compose exec backend python -c "
from pr_agent.security.auth import auth_manager
auth_manager.create_user('admin', 'admin@example.com', 'new-password', 'admin')
"
```

### 轮询不工作

```bash
# 检查轮询日志
docker-compose logs polling

# 测试 Bitbucket 连接
docker-compose exec backend python -c "
from pr_agent.git_providers.bitbucket_server_provider import BitbucketServerProvider
provider = BitbucketServerProvider()
print(provider.list_pull_requests('PROJECT', 'repo-name'))
"
```

## 性能优化

- 调整 `polling_interval_seconds` 控制轮询频率
- 配置 `max_related_files` 限制上下文文件数量
- 使用 `max_parallel_reviews` 控制并发审查数
- 定期清理旧的仓库缓存和轮询状态

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

Apache 2.0 License

## 支持

如有问题，请：
1. 查看文档和故障排查指南
2. 提交 GitHub Issue
3. 联系技术支持团队
