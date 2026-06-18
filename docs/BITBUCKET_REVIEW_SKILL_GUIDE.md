# Bitbucket Review Skill 使用指南

本指南介绍如何使用Bitbucket Review Skill来自动化PR审查流程。

---

## 概述

Bitbucket Review Skill是一个独立的skill，将以下功能整合在一起：
- **Webhook服务器** - 监听Bitbucket Server事件
- **API客户端** - 访问Bitbucket Server REST API
- **PR审查** - 执行AI驱动的代码审查

---

## 快速开始

### 1. 配置环境变量

```bash
# 必需
export BITBUCKET_URL="https://bitbucket.example.com"
export BITBUCKET_TOKEN="your_personal_access_token"
export OPENAI_API_KEY="sk-your-openai-key"

# 可选
export WEBHOOK_SECRET="your_webhook_secret"
export WEBHOOK_PORT=3000
```

### 2. 启动Webhook服务器

**方式1: 使用Python模块**
```bash
python -m pr_agent.skills.bitbucket_review.skill start-webhook
```

**方式2: 使用Claude Code (如果集成)**
```bash
/bitbucket-review start-webhook
```

### 3. 配置Bitbucket Server Webhook

1. 进入项目或仓库设置 → **Webhooks**
2. 创建新webhook：
   - **URL**: `http://your-server:3000/webhook`
   - **Events**: Pull Request (opened, updated, commented)
3. 保存

### 4. 测试

创建一个测试PR，应该会自动收到AI审查评论。

---

## 使用方式

### 方式1: Webhook自动触发

一旦配置好webhook，以下事件会自动触发审查：

- **PR opened** - 新PR创建时自动审查（可配置）
- **PR updated** - PR更新时重新审查（可配置）
- **Comment with command** - 在PR中评论 `/review`、`/improve` 等命令

### 方式2: 手动触发

```bash
# 审查特定PR
python -m pr_agent.skills.bitbucket_review.skill review \
  --pr-url https://bitbucket.example.com/projects/PROJ/repos/repo/pull-requests/123

# 运行多个命令
python -m pr_agent.skills.bitbucket_review.skill review \
  --pr-url https://bitbucket.example.com/projects/PROJ/repos/repo/pull-requests/123 \
  --commands review describe improve
```

### 方式3: 在代码中使用

```python
import asyncio
from pr_agent.skills.bitbucket_review import BitbucketReviewSkill

# 创建skill实例
skill = BitbucketReviewSkill()

# 审查PR
result = asyncio.run(
    skill.review_pr(
        "https://bitbucket.example.com/projects/PROJ/repos/repo/pull-requests/123"
    )
)
print(result)

# 启动webhook服务器
skill.start_webhook_server(blocking=True)
```

---

## 配置

### 通过环境变量

```bash
# Bitbucket Server连接
export BITBUCKET_URL="https://bitbucket.example.com"
export BITBUCKET_TOKEN="your_token"

# 或使用用户名密码
export BITBUCKET_USERNAME="your_username"
export BITBUCKET_PASSWORD="your_password"

# AI Provider
export OPENAI_API_KEY="sk-your-key"

# Webhook配置
export WEBHOOK_SECRET="secret_for_signature_verification"
export WEBHOOK_PORT=3000
export WEBHOOK_HOST="0.0.0.0"
```

### 通过配置文件 (`.pr_agent.toml`)

```toml
[bitbucket_server]
url = "https://bitbucket.example.com"
bearer_token = "your_token_here"

# Webhook设置
webhook_secret = "your_secret"
auto_review_on_open = true
auto_review_on_update = false

# 自动执行的命令
pr_commands = ["review"]

[config]
# 过滤规则（正则表达式）
ignore_repositories = [
    "archive/.*",
    "deprecated/.*"
]

ignore_pr_authors = [
    "bot-user",
    "automation-.*"
]

ignore_pr_title = [
    "WIP:.*",
    "Draft:.*",
    "\\[skip ci\\]"
]
```

---

## 支持的命令

在PR评论中使用以下命令触发操作：

### `/review`
AI驱动的代码审查，包括：
- 代码质量问题
- 潜在bug
- 安全漏洞
- 性能建议
- 最佳实践建议

**使用**:
```
/review
/review --num_code_suggestions=5
```

### `/describe`
自动生成PR描述

**使用**:
```
/describe
```

### `/improve`
生成代码改进建议

**使用**:
```
/improve
/improve --extended
```

### `/ask`
询问关于PR的问题

**使用**:
```
/ask "这个PR的主要变更是什么？"
```

---

## 高级功能

### 1. 过滤规则

使用正则表达式过滤不需要审查的PR：

```toml
[config]
# 忽略归档和测试仓库
ignore_repositories = ["archive/.*", ".*/test-.*"]

# 忽略bot用户
ignore_pr_authors = ["bot-.*", "github-actions"]

# 忽略WIP和草稿PR
ignore_pr_title = ["WIP:.*", "Draft:.*", "\\[WIP\\]"]
```

### 2. 自定义审查行为

```toml
[bitbucket_server]
# 新PR自动审查
auto_review_on_open = true

# PR更新时重新审查
auto_review_on_update = false

# 默认执行的命令
pr_commands = ["review", "describe"]
```

### 3. Webhook签名验证

增强安全性：

```bash
# 设置密钥
export WEBHOOK_SECRET="your_random_secret_string"
```

在Bitbucket Server webhook配置中设置相同的密钥。

### 4. 多实例部署

运行多个skill实例处理不同的仓库：

```python
# 实例1: 处理生产仓库
config1 = BitbucketReviewConfig(
    server_url="https://bitbucket.example.com",
    token="token1",
    webhook_port=3000,
    ignore_repositories=[]
)
skill1 = BitbucketReviewSkill(config1)

# 实例2: 处理开发仓库
config2 = BitbucketReviewConfig(
    server_url="https://bitbucket.example.com",
    token="token2",
    webhook_port=3001,
    ignore_repositories=["prod/.*"]
)
skill2 = BitbucketReviewSkill(config2)
```

---

## 监控和日志

### 查看连接状态

```bash
python -m pr_agent.skills.bitbucket_review.skill test-connection
```

**输出示例**:
```json
{
    "status": "connected",
    "server_url": "https://bitbucket.example.com",
    "version": "7.21.0",
    "display_name": "Bitbucket Server"
}
```

### 查看健康状态

访问健康检查端点：
```bash
curl http://localhost:3000/health
```

### 查看效率指标

```bash
python monitor_efficiency.py
```

---

## 故障排查

### 问题1: Webhook未触发

**检查清单**:
1. Webhook服务器是否运行？
   ```bash
   curl http://localhost:3000/
   ```

2. Bitbucket Server能否访问webhook URL？
   ```bash
   # 从Bitbucket Server主机测试
   curl http://your-webhook-server:3000/
   ```

3. Webhook配置是否正确？
   - URL正确
   - 事件类型已勾选
   - Webhook已激活

4. 查看webhook发送历史
   - 在Bitbucket Server webhook设置中查看最近的请求

### 问题2: PR未被审查

**检查清单**:
1. PR是否被过滤？
   - 检查 `ignore_repositories`
   - 检查 `ignore_pr_authors`
   - 检查 `ignore_pr_title`

2. 自动审查是否启用？
   - `auto_review_on_open`
   - `auto_review_on_update`

3. 查看日志
   ```bash
   # 日志会显示为什么跳过某个PR
   ```

### 问题3: 认证失败

**检查清单**:
1. Token是否有效？
   ```bash
   python -m pr_agent.skills.bitbucket_review.skill test-connection
   ```

2. Token权限是否足够？
   - 需要: PR读写权限
   - 需要: Repository读权限

3. URL是否正确？
   ```bash
   echo $BITBUCKET_URL
   ```

### 问题4: 签名验证失败

**解决方案**:
1. 确认两端密钥一致
   ```bash
   # Skill配置
   echo $WEBHOOK_SECRET
   
   # Bitbucket webhook配置中的密钥
   ```

2. 临时禁用签名验证进行调试
   ```bash
   unset WEBHOOK_SECRET
   ```

---

## 性能优化

### 1. 使用多worker

使用Gunicorn运行多个worker：

```bash
gunicorn pr_agent.skills.bitbucket_review.skill:skill.app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:3000
```

### 2. 异步处理

Skill已经使用异步处理，webhook请求立即返回，审查在后台执行。

### 3. 缓存Provider实例

BitbucketServerClient会缓存provider实例，避免重复初始化。

---

## 与其他工具集成

### 与CI/CD集成

在CI流程中手动触发审查：

```yaml
# .gitlab-ci.yml 示例
review-pr:
  script:
    - python -m pr_agent.skills.bitbucket_review.skill review --pr-url $CI_MERGE_REQUEST_URL
```

### 与监控系统集成

通过 `/health` 端点监控服务状态：

```bash
# Prometheus监控配置
curl http://localhost:3000/health
```

---

## 最佳实践

### 1. 使用Token认证
推荐使用Personal Access Token而不是用户名密码。

### 2. 设置合理的过滤规则
避免审查不重要的PR，节省API成本。

### 3. 启用效率监控
跟踪AI审查的ROI和提效情况。

### 4. 定期更新Token
定期轮换access token确保安全。

### 5. 使用Webhook密钥
启用签名验证防止未授权请求。

---

## 相关文档

- [Bitbucket Server Webhook指南](BITBUCKET_SERVER_WEBHOOK.md)
- [服务启动指南](HOW_TO_START_SERVICE.md)
- [监控指南](MONITORING_GUIDE.md)
- [Agent skill folder](../bitbucket-review/SKILL.md)
- [Claude Code skill definition](../.claude/skills/bitbucket-review.md)
- [实现计划](.claude/plans/bitbucket-review-skill-plan.md)

---

## 获取帮助

遇到问题？

1. 查看故障排查部分
2. 运行 `test-connection` 诊断连接
3. 查看服务器日志
4. 提交GitHub Issue
