# CI/CD Pipeline

PR-Agent 使用 GitHub Actions 实现完整的 CI/CD 流程，包括自动化测试、代码质量检查、安全扫描和部署。

## 工作流概览

### 1. 主 CI/CD 流程 (ci-cd.yml)

在每次推送和 PR 时触发，包含以下阶段：

#### 后端测试
- 多版本 Python 测试 (3.9, 3.10, 3.11, 3.12)
- 单元测试执行
- 代码覆盖率报告
- 上传到 Codecov

#### 前端测试
- Node.js 18 环境
- 单元测试执行
- 生产构建验证

#### 代码质量检查
- **Python:**
  - flake8 - 代码风格检查
  - black - 代码格式化检查
  - isort - 导入排序检查
  - mypy - 类型检查
- **JavaScript/TypeScript:**
  - ESLint - 代码质量检查

#### 安全扫描
- safety - Python 依赖漏洞扫描
- bandit - Python 代码安全扫描
- 生成安全报告

#### Docker 构建
- 构建后端镜像
- 构建前端镜像
- 使用 BuildKit 缓存加速

#### 集成测试
- 使用 PostgreSQL 服务
- 端到端测试
- API 集成测试

#### 部署
- **Staging:** auto-review 分支自动部署到测试环境
- **Production:** main 分支自动部署到生产环境
- 自动创建 GitHub Release

### 2. Docker 构建和推送 (docker.yml)

构建并推送 Docker 镜像到 GitHub Container Registry：

- 支持多架构 (amd64, arm64)
- 自动版本标签
- 生成 SBOM (软件物料清单)
- 镜像缓存优化

**触发条件:**
- 推送到 main 或 auto-review 分支
- 创建版本标签 (v*)
- 发布 Release

**镜像标签:**
- `ghcr.io/philoallandatru/pr-agent-backend:main`
- `ghcr.io/philoallandatru/pr-agent-backend:v1.0.0`
- `ghcr.io/philoallandatru/pr-agent-backend:sha-abc123`

### 3. CodeQL 安全分析 (codeql.yml)

GitHub 的代码安全扫描：

- Python 和 JavaScript 代码分析
- 安全漏洞检测
- 代码质量问题识别
- 每周一自动扫描

### 4. 依赖审查 (dependency-review.yml)

PR 中的依赖变更审查：

- 检测新增依赖的安全漏洞
- 许可证合规性检查
- 在 PR 中自动评论结果

### 5. Dependabot 自动更新

自动创建依赖更新 PR：

- **Python 依赖:** 每周一检查
- **npm 依赖:** 每周一检查
- **GitHub Actions:** 每周一检查
- **Docker 基础镜像:** 每周一检查

## 本地开发工作流

### 运行测试

```bash
# 后端测试
pytest tests/unittest/ -v --cov=pr_agent

# 前端测试
cd frontend
npm test

# 集成测试
pytest tests/integration/ -v
```

### 代码质量检查

```bash
# Python 格式化
black pr_agent tests
isort pr_agent tests

# Python 代码检查
flake8 pr_agent
mypy pr_agent

# 前端代码检查
cd frontend
npm run lint
npm run lint:fix
```

### 安全扫描

```bash
# Python 依赖扫描
safety check

# Python 代码安全扫描
bandit -r pr_agent
```

### 本地 Docker 构建

```bash
# 构建后端
docker build -t pr-agent-backend .

# 构建前端
docker build -t pr-agent-frontend ./frontend

# 使用 docker-compose
docker-compose build
```

## 分支策略

### main 分支
- 生产环境代码
- 所有 PR 必须通过 CI 检查
- 自动部署到生产环境
- 创建 Release 标签

### auto-review 分支
- 开发和测试分支
- 自动部署到 Staging 环境
- 功能开发和测试

### 功能分支
- 从 auto-review 创建
- 命名格式: `feature/xxx`, `fix/xxx`, `chore/xxx`
- 完成后创建 PR 到 auto-review

## PR 工作流

### 1. 创建 PR

```bash
# 创建功能分支
git checkout -b feature/new-feature auto-review

# 开发和提交
git add .
git commit -m "feat: add new feature"
git push origin feature/new-feature

# 在 GitHub 创建 PR
```

### 2. 自动检查

PR 创建后自动触发：
- ✅ 后端测试
- ✅ 前端测试
- ✅ 代码质量检查
- ✅ 安全扫描
- ✅ 依赖审查
- ✅ Docker 构建
- ✅ 集成测试

### 3. 代码审查

- 至少一个审查者批准
- 所有 CI 检查通过
- 解决所有评论

### 4. 合并

```bash
# Squash and merge 到 auto-review
# 自动部署到 Staging

# 测试通过后，创建 PR 到 main
# 合并后自动部署到生产环境
```

## 部署流程

### Staging 部署

**触发:** 推送到 auto-review 分支

```yaml
deploy-staging:
  - 构建 Docker 镜像
  - 推送到 Container Registry
  - 部署到 Staging 环境
  - 运行烟雾测试
```

**环境变量:**
```bash
ENVIRONMENT=staging
DATABASE_URL=postgresql://...
BITBUCKET_URL=https://staging.bitbucket.example.com
```

### Production 部署

**触发:** 推送到 main 分支

```yaml
deploy-production:
  - 构建 Docker 镜像
  - 推送到 Container Registry
  - 部署到生产环境
  - 运行烟雾测试
  - 创建 GitHub Release
```

**环境变量:**
```bash
ENVIRONMENT=production
DATABASE_URL=postgresql://...
BITBUCKET_URL=https://bitbucket.example.com
```

## 环境配置

### GitHub Secrets

在 GitHub 仓库设置中配置以下 Secrets：

```bash
# 数据库
DATABASE_URL=postgresql://user:pass@host:5432/db

# Bitbucket
BITBUCKET_URL=https://bitbucket.example.com
BITBUCKET_TOKEN=xxx

# OpenAI
OPENAI_API_KEY=sk-xxx

# 部署
DEPLOY_SSH_KEY=xxx
DEPLOY_HOST=xxx
```

### 环境变量

```bash
# 应用配置
APP_ENV=production
LOG_LEVEL=INFO
DEBUG=false

# 数据库
DATABASE_URL=postgresql://...
DATABASE_POOL_SIZE=20

# Web 平台
WEB_HOST=0.0.0.0
WEB_PORT=8000
JWT_SECRET=xxx

# 轮询服务
POLLING_ENABLED=true
POLLING_INTERVAL=300

# 监控
PROMETHEUS_ENABLED=true
SENTRY_DSN=xxx
```

## 监控和告警

### 构建状态

在 README 中添加徽章：

```markdown
![CI/CD](https://github.com/Philoallandatru/pr-agent/workflows/CI%2FCD%20Pipeline/badge.svg)
![CodeQL](https://github.com/Philoallandatru/pr-agent/workflows/CodeQL/badge.svg)
![Docker](https://github.com/Philoallandatru/pr-agent/workflows/Docker/badge.svg)
```

### 代码覆盖率

```markdown
[![codecov](https://codecov.io/gh/Philoallandatru/pr-agent/branch/main/graph/badge.svg)](https://codecov.io/gh/Philoallandatru/pr-agent)
```

### 通知

配置 GitHub Actions 通知：
- Slack 集成
- 邮件通知
- GitHub 通知

## 故障排查

### CI 失败

#### 测试失败
```bash
# 本地运行失败的测试
pytest tests/unittest/test_xxx.py -v

# 查看详细日志
pytest tests/unittest/test_xxx.py -v -s
```

#### 代码质量检查失败
```bash
# 自动修复格式问题
black pr_agent tests
isort pr_agent tests

# 查看具体问题
flake8 pr_agent --show-source
```

#### Docker 构建失败
```bash
# 本地构建测试
docker build -t test .

# 查看构建日志
docker build -t test . --progress=plain
```

### 部署失败

#### 回滚部署
```bash
# 回滚到上一个版本
kubectl rollout undo deployment/pr-agent-backend

# 查看部署历史
kubectl rollout history deployment/pr-agent-backend
```

#### 查看日志
```bash
# 查看 Pod 日志
kubectl logs -f deployment/pr-agent-backend

# 查看事件
kubectl get events --sort-by=.metadata.creationTimestamp
```

## 性能优化

### 缓存策略

#### pip 缓存
```yaml
- uses: actions/cache@v4
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
```

#### npm 缓存
```yaml
- uses: actions/setup-node@v4
  with:
    cache: 'npm'
    cache-dependency-path: frontend/package-lock.json
```

#### Docker 层缓存
```yaml
- uses: docker/build-push-action@v5
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

### 并行执行

```yaml
strategy:
  matrix:
    python-version: ['3.9', '3.10', '3.11', '3.12']
```

### 条件执行

```yaml
if: github.ref == 'refs/heads/main' && github.event_name == 'push'
```

## 最佳实践

### 1. 提交消息规范

使用 Conventional Commits：

```bash
feat: add new feature
fix: resolve bug
docs: update documentation
chore: update dependencies
test: add tests
refactor: refactor code
perf: improve performance
ci: update CI configuration
```

### 2. PR 描述模板

```markdown
## 变更说明
简要描述此 PR 的变更内容

## 变更类型
- [ ] 新功能
- [ ] Bug 修复
- [ ] 文档更新
- [ ] 重构
- [ ] 性能优化

## 测试
- [ ] 添加了单元测试
- [ ] 添加了集成测试
- [ ] 手动测试通过

## 检查清单
- [ ] 代码遵循项目规范
- [ ] 更新了相关文档
- [ ] 所有测试通过
- [ ] 无安全漏洞
```

### 3. 版本发布

```bash
# 创建版本标签
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0

# 自动触发生产部署和 Release 创建
```

### 4. 安全实践

- 不在代码中硬编码密钥
- 使用 GitHub Secrets 管理敏感信息
- 定期更新依赖
- 启用 Dependabot 安全更新
- 定期审查 CodeQL 报告

## 相关文档

- [部署指南](DEPLOYMENT.md)
- [开发指南](../README.md)
- [安全文档](SECURITY.md)
- [监控文档](MONITORING.md)
