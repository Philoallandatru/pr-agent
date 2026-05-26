# PR-Agent：AI 驱动的代码审查工具

<div align="center">

**智能、高效、可定制的 Pull Request 自动化审查系统**

[功能特性](#功能特性) • [快速开始](#快速开始) • [部署方式](#部署方式) • [配置说明](#配置说明) • [高级特性](#高级特性)

</div>

---

## 📖 项目简介

PR-Agent 是一个开源的 AI 驱动代码审查工具，支持多种 Git 平台（GitHub、GitLab、Bitbucket、Azure DevOps、Gitea），能够自动分析 Pull Request 并提供专业的代码审查建议。

### 🎯 核心优势

- **🤖 AI 驱动**：基于大语言模型（LLM）的智能代码分析
- **🌐 多平台支持**：GitHub、GitLab、Bitbucket Server、Azure DevOps、Gitea
- **🔧 灵活部署**：CLI、Webhook、GitHub Action、Docker、Polling 等多种方式
- **🎨 高度可定制**：丰富的配置选项和提示词模板
- **🔍 深度分析**：支持 Agentic Review 模式，可搜索整个代码库
- **🌍 本地模型**：支持 llama.cpp、Ollama、vLLM 等本地模型服务

---

## ✨ 功能特性

### 核心功能

#### 1. **代码审查 (`/review`)**
- 自动分析代码变更，识别潜在问题
- 提供安全审计、性能建议、最佳实践检查
- 评估代码复杂度和审查工作量
- 支持增量审查（只审查新增变更）

#### 2. **代码改进建议 (`/improve`)**
- 提供具体的代码优化建议
- 支持内联评论和代码片段
- 可配置建议数量和类型

#### 3. **PR 描述生成 (`/describe`)**
- 自动生成 PR 标题和描述
- 提取变更类型（功能、修复、重构等）
- 生成变更摘要和影响分析

#### 4. **问答系统 (`/ask`)**
- 针对 PR 提出问题并获得 AI 回答
- 支持代码理解和实现细节查询

#### 5. **变更日志生成 (`/update_changelog`)**
- 自动生成结构化的变更日志
- 支持多种格式和模板

#### 6. **文档建议 (`/add_docs`)**
- 识别缺少文档的代码
- 提供文档编写建议

#### 7. **标签生成 (`/generate_labels`)**
- 自动为 PR 添加合适的标签
- 支持自定义标签规则

#### 8. **合规性检查 (`/ticket_compliance_check`)**
- 验证 PR 是否关联了 Issue/Ticket
- 检查分支命名规范

---

### 🚀 高级特性

#### Agentic Review（智能仓库探索）

Agentic Review 是一个革命性的功能，允许 AI 在审查代码前主动探索代码库：

**工作原理**：
```
PR 提交 → AI 分析 diff → 决定需要查看的文件
  ↓
执行只读命令（ls, cat, grep, git log 等）
  ↓
获取上下文信息 → 生成更准确的审查建议
```

**允许的命令**：
- `ls` - 列出目录内容
- `cat` - 读取文件
- `rg` / `grep` - 搜索代码
- `git status/show/diff/log` - Git 操作

**安全保障**：
- ✅ 只读操作，不能修改代码
- ✅ 仓库边界检查，不能访问外部文件
- ✅ 命令白名单，只能执行允许的命令
- ✅ 超时和输出限制
- ✅ 完整的审计日志

**配置示例**：
```toml
[agentic_review]
enabled = true
commands = ["review", "improve"]
max_iterations = 8
log_search_behavior = true  # 记录搜索行为
```

**日志示例**：
```
INFO: Agentic review tool call [1/8]: ls src
INFO: Agentic review tool result [1]: 72 chars
INFO: Agentic review tool call [2/8]: cat src/auth.py
INFO: Agentic review search summary: ['ls src', 'cat src/auth.py', 'grep login']
```

---

#### Fallback 模型支持

当主模型失败时，自动尝试备用模型，确保审查始终能完成：

```toml
[config]
model = "gpt-4"
fallback_models = ["gpt-4o-mini", "claude-3-5-sonnet"]
```

**工作流程**：
```
主模型失败 → 尝试 fallback_models[0] → 失败 → 尝试 fallback_models[1]
  ↓
所有模型都失败 → 回退到非 agentic 模式（如果启用）
```

---

#### Polling 服务（Bitbucket Server）

为不支持 Webhook 的环境提供轮询模式：

**特性**：
- 定期轮询指定仓库的 PR
- 自动检测新 PR 和更新
- 防止重复审查（原子性状态管理）
- 支持多进程并发处理
- 服务重启后自动恢复

**配置示例**：
```toml
[bitbucket_server]
polling_interval_seconds = 300
polling_repositories = ["PROJECT/repo-1", "PROJECT/repo-2"]
polling_commands = ["/describe", "/review", "/improve"]
max_parallel_tasks = 10
```

**状态管理**：
- 使用 JSON 文件持久化状态
- 跨平台文件锁（Unix fcntl / Windows msvcrt）
- 原子性 test-and-set 操作防止竞态条件
- 启动时自动清理过期状态

---

#### 本地模型支持

完整支持本地部署的大语言模型：

**支持的服务**：
- **llama.cpp** - 轻量级 C++ 推理引擎
- **Ollama** - 简单易用的本地模型服务
- **vLLM** - 高性能推理服务器
- **LM Studio** - 桌面端模型管理工具

**配置示例**：
```bash
# llama.cpp
CONFIG__MODEL=openai/Qwen3.5-9B-IQ4_XS.gguf
OPENAI__API_BASE=http://127.0.0.1:8080/v1

# Ollama
CONFIG__MODEL=ollama/qwen2.5:7b
OPENAI__API_BASE=http://127.0.0.1:11434/v1
```

**Tokenizer 预加载**：
为避免多进程竞争，提供 tokenizer 预下载工具：

```bash
# 使用启动脚本（推荐）
./scripts/start_polling_service.sh

# 手动预下载
python -m pr_agent.algo.tokenizer_manager download \
  --modelscope-model-id "Qwen/Qwen3.6-35B-A3B-FP8" \
  --cache-dir "~/.cache/pr-agent/tokenizers"
```

---

## 🚀 快速开始

### 前置要求

- Python ≥ 3.12
- Git
- 本地模型服务（llama.cpp / Ollama / vLLM）或 API 密钥

### 安装

```bash
# 克隆仓库
git clone https://github.com/Philoallandatru/pr-agent.git
cd pr-agent

# 安装依赖
pip install -r requirements.txt
```

### 配置

创建 `.env` 文件：

```bash
# 本地模型配置
CONFIG__MODEL=openai/local-review-model
OPENAI__API_BASE=http://127.0.0.1:8080/v1
OPENAI__KEY=local-api-key

# Git 平台配置
BITBUCKET_SERVER__URL=https://bitbucket.example.com
BITBUCKET_SERVER__BEARER_TOKEN=your-token-here
```

### 使用

#### CLI 模式

```bash
# 审查 PR
python -m pr_agent.cli --pr_url https://github.com/owner/repo/pull/123 review

# 生成 PR 描述
python -m pr_agent.cli --pr_url https://github.com/owner/repo/pull/123 describe

# 提供改进建议
python -m pr_agent.cli --pr_url https://github.com/owner/repo/pull/123 improve
```

#### Polling 服务模式

```bash
# 使用启动脚本（推荐）
./scripts/start_polling_service.sh

# 或直接启动
python -m pr_agent.servers.bitbucket_server_polling
```

---

## 🐳 部署方式

### Docker Compose

```yaml
version: '3.8'
services:
  pr-agent-polling:
    build: .
    environment:
      - CONFIG__MODEL=openai/local-model
      - OPENAI__API_BASE=http://llama-cpp:8080/v1
      - BITBUCKET_SERVER__URL=https://bitbucket.example.com
      - BITBUCKET_SERVER__BEARER_TOKEN=${BITBUCKET_TOKEN}
    volumes:
      - ./tokenizers:/root/.cache/pr-agent/tokenizers
      - ./.pr_agent.toml:/app/.pr_agent.toml
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pr-agent-polling
spec:
  replicas: 2
  template:
    spec:
      initContainers:
      - name: download-tokenizer
        image: pr-agent:latest
        command:
        - python
        - -m
        - pr_agent.algo.tokenizer_manager
        - download
        volumeMounts:
        - name: tokenizer-cache
          mountPath: /root/.cache/pr-agent/tokenizers
      containers:
      - name: polling-service
        image: pr-agent:latest
        command: ["./scripts/start_polling_service.sh"]
        volumeMounts:
        - name: tokenizer-cache
          mountPath: /root/.cache/pr-agent/tokenizers
      volumes:
      - name: tokenizer-cache
        persistentVolumeClaim:
          claimName: tokenizer-cache-pvc
```

---

## ⚙️ 配置说明

### 基础配置

```toml
[config]
# 模型配置
model = "openai/local-review-model"
fallback_models = ["openai/backup-model"]
custom_model_max_tokens = 32768

# Git 平台
git_provider = "bitbucket_server"
publish_output = true

# 日志
log_level = "INFO"

# 响应语言
response_language = "zh-CN"
```

### Agentic Review 配置

```toml
[agentic_review]
enabled = true
commands = ["review", "improve"]
repo_root = ""  # 空表示自动检测
use_repo_context_cache = true
max_iterations = 8
max_total_context_chars = 40000
command_timeout_seconds = 10
fallback_to_direct_review = true
log_search_behavior = true  # 记录搜索行为
```

### Polling 配置

```toml
[bitbucket_server]
url = "https://bitbucket.example.com"
polling_interval_seconds = 300
polling_repositories = ["PROJECT/repo-1", "PROJECT/repo-2"]
polling_commands = [
    "/describe --pr_description.final_update_message=false",
    "/review",
    "/improve"
]
max_parallel_tasks = 10
polling_review_timeout_seconds = 1800
polling_state_file = ".pr_agent_polling_state.json"
```

### Tokenizer 配置

```toml
[tokenizer]
backend = "modelscope"
modelscope_model_id = "Qwen/Qwen3.6-35B-A3B-FP8"
local_cache_dir = "~/.cache/pr-agent/tokenizers"
enable_local_cache = true
fallback_to_download = true
```

---

## 📊 性能优化

### Tokenizer 预加载

避免多进程启动时的锁竞争：

```bash
# 方法 1：使用启动脚本
./scripts/start_polling_service.sh

# 方法 2：手动预下载
python -m pr_agent.algo.tokenizer_manager download \
  --modelscope-model-id "Qwen/Qwen3.6-35B-A3B-FP8" \
  --cache-dir "~/.cache/pr-agent/tokenizers"

# 方法 3：Docker 构建时预下载
RUN python -m pr_agent.algo.tokenizer_manager download \
    --modelscope-model-id "Qwen/Qwen3.6-35B-A3B-FP8" \
    --cache-dir "/root/.cache/pr-agent/tokenizers"
```

### 并发控制

```toml
[bitbucket_server]
max_parallel_tasks = 10  # 最大并发 PR 处理数
polling_review_timeout_seconds = 1800  # 单个 PR 超时时间
```

### 上下文优化

```toml
[config]
max_model_tokens = 32000  # 模型上下文限制
max_description_tokens = 500
max_commits_tokens = 500

[agentic_review]
max_total_context_chars = 40000  # Agentic review 上下文限制
max_command_output_chars = 40000  # 单个命令输出限制
```

---

## 🔒 安全性

### Agentic Review 安全

- **只读操作**：不能修改、删除、创建文件
- **仓库边界**：不能访问仓库外的文件
- **命令白名单**：只能执行预定义的安全命令
- **无 Shell**：不能执行 shell 脚本或管道
- **审计日志**：记录所有命令执行

### 密钥管理

**不要在仓库中存储密钥**：
```bash
# ✅ 使用环境变量
export BITBUCKET_SERVER__BEARER_TOKEN=your-token

# ✅ 使用 .env 文件（添加到 .gitignore）
echo "BITBUCKET_SERVER__BEARER_TOKEN=your-token" > .env

# ❌ 不要提交到 Git
# .pr_agent.toml 中不要包含密钥
```

### 权限最小化

```bash
# Bitbucket Server Token 权限
- PROJECT_READ
- REPO_READ
- REPO_WRITE (仅用于发布评论)
```

---

## 🐛 故障排查

### 常见问题

#### 1. Tokenizer 锁竞争

**症状**：
```
Still waiting to acquire lock on /homessd/.cache/modelscope/hub/.lock
```

**解决方案**：
```bash
# 使用启动脚本预下载
./scripts/start_polling_service.sh

# 或手动预下载
python -m pr_agent.algo.tokenizer_manager download \
  --modelscope-model-id "Qwen/Qwen3.6-35B-A3B-FP8" \
  --cache-dir "~/.cache/pr-agent/tokenizers"
```

#### 2. PR 重复审查

**症状**：同一个 PR 被多次审查

**解决方案**：已修复（使用原子性状态管理）

确保使用最新版本：
```bash
git pull origin main
```

#### 3. Agentic Review 格式错误

**症状**：本地模型返回无法解析的响应

**解决方案**：已实现 fallback 机制

配置备用模型：
```toml
[config]
model = "openai/primary-model"
fallback_models = ["openai/backup-model"]
```

#### 4. 权限问题

**症状**：
```
PermissionError: [Errno 13] Permission denied: '/data/tokenizers'
```

**解决方案**：
```bash
# 使用用户目录（推荐）
mkdir -p ~/.cache/pr-agent/tokenizers

# 或修改权限
sudo chown -R $(whoami):$(whoami) /data/tokenizers
```

---

## 📚 文档

- [Agentic Review 指南](docs/AGENTIC_REVIEW.md)
- [Bitbucket Polling 配置](docs/BITBUCKET_POLLING.md)
- [Tokenizer 预加载指南](docs/TOKENIZER_PRELOAD.md)
- [Polling 修复报告](docs/POLLING_FIXES.md)

---

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详情。

### 开发环境

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试
PYTHONPATH=. pytest tests/unittest -v

# 运行 linter
ruff check .

# 运行 pre-commit hooks
pre-commit run --all-files
```

---

## 📄 许可证

本项目基于 Apache 2.0 许可证开源。详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

- 基于 [Qodo Merge (PR-Agent)](https://github.com/Codium-ai/pr-agent) 项目
- 感谢所有贡献者和用户的支持

---

## 📞 联系方式

- **Issues**: [GitHub Issues](https://github.com/Philoallandatru/pr-agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Philoallandatru/pr-agent/discussions)

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给我们一个 Star！**

Made with ❤️ by the PR-Agent Community

</div>
