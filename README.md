# PR-Agent：AI 驱动的代码审查工具

<div align="center">

**智能、高效、可定制的 Pull Request 自动化审查系统**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12+-green.svg)](https://www.python.org/)

[功能特性](#功能特性) • [快速开始](#快速开始) • [部署方式](#部署方式) • [完整文档](PROJECT_OVERVIEW.md)

</div>

---

## 📖 项目简介

PR-Agent 是一个开源的 AI 驱动代码审查工具，支持多种 Git 平台（GitHub、GitLab、Bitbucket、Azure DevOps、Gitea），能够自动分析 Pull Request 并提供专业的代码审查建议。

**特别优化**：本项目针对 **Bitbucket Server / Data Center** 和**本地模型部署**进行了深度优化，支持完全离线的内网环境。

### 🎯 核心优势

- 🤖 **AI 驱动**：基于大语言模型的智能代码分析
- 🌐 **多平台支持**：GitHub、GitLab、Bitbucket Server、Azure DevOps、Gitea
- 🔧 **灵活部署**：CLI、Webhook、Polling、Docker、Kubernetes
- 🏠 **本地模型**：完整支持 llama.cpp、Ollama、vLLM 等本地服务
- 🔍 **深度分析**：Agentic Review 可搜索整个代码库
- 🌍 **离线运行**：无需公网访问，适合内网环境

---

## ✨ 功能特性

### 核心功能

| 命令 | 功能 | 说明 |
|------|------|------|
| `/review` | 代码审查 | 安全审计、性能建议、最佳实践检查 |
| `/improve` | 改进建议 | 提供具体的代码优化建议 |
| `/describe` | PR 描述生成 | 自动生成 PR 标题和描述 |
| `/ask` | 问答系统 | 针对 PR 提出问题并获得回答 |
| `/update_changelog` | 变更日志 | 自动生成结构化的变更日志 |
| `/add_docs` | 文档建议 | 识别缺少文档的代码 |
| `/generate_labels` | 标签生成 | 自动为 PR 添加合适的标签 |

### 🚀 高级特性

#### 1. **Agentic Review（智能仓库探索）**

允许 AI 在审查前主动探索代码库，获取更多上下文：

```
PR 提交 → AI 分析 → 执行只读命令（ls, cat, grep, git log）
  ↓
获取上下文 → 生成更准确的审查建议
```

**安全保障**：只读操作、仓库边界检查、命令白名单、完整审计日志

#### 2. **Fallback 模型支持**

主模型失败时自动尝试备用模型，确保审查始终能完成：

```toml
[config]
model = "openai/primary-model"
fallback_models = ["openai/backup-model"]
```

#### 3. **Polling 服务（Bitbucket Server）**

为不支持 Webhook 的环境提供轮询模式：
- 定期轮询指定仓库的 PR
- 自动检测新 PR 和更新
- 防止重复审查（原子性状态管理）
- 支持多进程并发处理

---

## 🚀 快速开始

### 前置要求

- Python ≥ 3.12
- 本地模型服务（llama.cpp / Ollama / vLLM）或 API 密钥

### 1. 启动本地 OpenAI-compatible 模型服务

先保证你已经有一个兼容 OpenAI `/v1/chat/completions` 的服务，例如 vLLM、llama.cpp server、LM Studio、Ollama 的 OpenAI-compatible endpoint，或公司内部模型网关。

PR-Agent 不负责下载或启动大模型本体。推荐先单独验证模型服务：

```bash
curl http://127.0.0.1:8000/v1/models
```

### 2. 安装配置

```bash
# 克隆仓库
git clone https://github.com/Philoallandatru/pr-agent.git
cd pr-agent

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置模型服务和 Bitbucket 信息
```

### 3. 配置示例

编辑 `.env`：

```env
# Bitbucket Server 配置
CONFIG__GIT_PROVIDER=bitbucket_server
BITBUCKET_SERVER__URL=https://bitbucket.example.com
BITBUCKET_SERVER__BEARER_TOKEN=your-token-here

# 本地模型配置
CONFIG__MODEL=openai/local-review-model
OPENAI__API_BASE=http://127.0.0.1:8080/v1
OPENAI__KEY=local-api-key

# Tokenizer 配置
TOKENIZER__BACKEND=modelscope
TOKENIZER__MODELSCOPE_MODEL_ID=Qwen/Qwen3.6-35B-A3B-FP8
TOKENIZER__LOCAL_CACHE_DIR=~/.cache/pr-agent/tokenizers
```

编辑 `.pr_agent.toml`：

```toml
[bitbucket_server]
enable_polling = true
polling_interval_seconds = 300
polling_repositories = [
    "PROJECT/repo-1",
    "PROJECT/repo-2",
]
polling_commands = [
    "/describe --pr_description.final_update_message=false",
    "/review",
    "/improve",
]
```

### 4. 启动服务

```bash
# 使用启动脚本（推荐，自动预下载 tokenizer）
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

启动：

```bash
docker compose up -d --build
```

### Kubernetes

参见 [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md#kubernetes) 获取完整的 Kubernetes 部署配置。

---

## 📚 文档

- **[完整项目文档](PROJECT_OVERVIEW.md)** - 所有功能的详细说明
- [Agentic Review 指南](docs/AGENTIC_REVIEW.md) - 智能仓库探索功能
- [Bitbucket Polling 配置](docs/BITBUCKET_POLLING.md) - Polling 服务配置
- [Tokenizer 预加载指南](docs/TOKENIZER_PRELOAD.md) - 避免多进程锁竞争
- [Polling 修复报告](docs/POLLING_FIXES.md) - 问题修复记录

---

## ⚙️ 核心配置

### Agentic Review

```toml
[agentic_review]
enabled = true
commands = ["review", "improve"]
max_iterations = 8
log_search_behavior = true  # 记录搜索行为
fallback_to_direct_review = true
```

### Polling 服务

```toml
[bitbucket_server]
polling_interval_seconds = 300
polling_repositories = ["PROJECT/repo-1"]
max_parallel_tasks = 10
polling_review_timeout_seconds = 1800
```

### 本地模型

```toml
[config]
model = "openai/local-model"
fallback_models = ["openai/backup-model"]
custom_model_max_tokens = 32768
```

---

## 🔒 安全性

- **Agentic Review**：只读操作、仓库边界检查、命令白名单
- **密钥管理**：使用环境变量，不提交到 Git
- **权限最小化**：只需要 READ 和 WRITE（评论）权限

---

## 🐛 故障排查

### Tokenizer 锁竞争

**症状**：`Still waiting to acquire lock on .../hub/.lock`

**解决方案**：
```bash
./scripts/start_polling_service.sh
```

### PR 重复审查

**症状**：同一个 PR 被多次审查

**解决方案**：已修复（使用原子性状态管理），确保使用最新版本

### 更多问题

参见 [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md#故障排查) 获取完整的故障排查指南。

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
```

---

## 📄 许可证

本项目基于 Apache 2.0 许可证开源。详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

- 基于 [Qodo Merge (PR-Agent)](https://github.com/Codium-ai/pr-agent) 项目
- 感谢所有贡献者和用户的支持

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给我们一个 Star！**

[完整文档](PROJECT_OVERVIEW.md) • [Issues](https://github.com/Philoallandatru/pr-agent/issues) • [Discussions](https://github.com/Philoallandatru/pr-agent/discussions)

Made with ❤️ by the PR-Agent Community

</div>

  --cache-dir ./tokenizers \
  --modelscope-model-id Qwen/Qwen3.6-35B-A3B-FP8
```

部署时挂载这个目录：

```yaml
volumes:
  - ./tokenizers:/data/tokenizers
```

如果你的本地模型不是 GPT 系列 tokenizer，PR-Agent 默认会用 ModelScope 上的 `Qwen/Qwen3.6-35B-A3B-FP8` tokenizer 做 token 计算。建议在 `.pr_agent.toml` 中设置：

```toml
[config]
custom_model_max_tokens = 32768
model_token_count_estimate_factor = 0.3
```

如果使用 Ollama，模型名通常应写成 `ollama/<model>`，例如 `ollama/qwen3:32b`。如果误写成 `ollam/<model>`，token 上限会走本地默认值，但后续 LiteLLM 调用模型时仍可能因为 provider 名错误而失败。

### 4. Docker Compose 启动

```bash
docker compose up -d --build
docker compose logs -f pr-agent-polling
```

默认日志格式是便于本地阅读的 console 输出。如果需要给日志系统采集结构化 JSON，可以设置：

```env
PR_AGENT_LOG_FORMAT=JSON
```

启动后日志中应看到：

```text
Starting Bitbucket Server polling service
Polling configuration: ...
Polling iteration #1 started
```

### 5. 直接用 Python 启动服务

Python 需要 `>=3.12`：

```bash
python -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/pip install -e .

export PR_AGENT_CONFIG_FILE="$PWD/.pr_agent.toml"
export CONFIG__GIT_PROVIDER=bitbucket_server
export BITBUCKET_SERVER__URL=https://bitbucket.example.com
export BITBUCKET_SERVER__BEARER_TOKEN=replace-with-token
export BITBUCKET_SERVER__POLLING_REVIEW_TIMEOUT_SECONDS=1800
export CONFIG__MODEL=openai/local-review-model
export CONFIG__FALLBACK_MODELS=[]
export CONFIG__CUSTOM_MODEL_MAX_TOKENS=32768
export OPENAI__API_BASE=http://127.0.0.1:8000/v1
export OPENAI__KEY=local-api-key
export OPENAI_API_KEY=local-api-key
export TOKENIZER__LOCAL_CACHE_DIR="$PWD/tokenizers"
export TOKENIZER__ENABLE_LOCAL_CACHE=true
export TOKENIZER__BACKEND=modelscope
export TOKENIZER__MODELSCOPE_MODEL_ID=Qwen/Qwen3.6-35B-A3B-FP8
export TOKENIZER__FALLBACK_TO_DOWNLOAD=true
export TOKENIZER__OFFLINE_ESTIMATE_FALLBACK=true
export TOKENIZER__SKIP_TOKEN_COUNT=false

PYTHONPATH=. ./.venv/bin/python -m pr_agent.servers.bitbucket_server_polling
```

Windows PowerShell：

```powershell
$env:PR_AGENT_CONFIG_FILE="$PWD\.pr_agent.toml"
$env:CONFIG__GIT_PROVIDER="bitbucket_server"
$env:BITBUCKET_SERVER__URL="https://bitbucket.example.com"
$env:BITBUCKET_SERVER__BEARER_TOKEN="replace-with-token"
$env:BITBUCKET_SERVER__POLLING_REVIEW_TIMEOUT_SECONDS="1800"
$env:CONFIG__MODEL="openai/local-review-model"
$env:CONFIG__FALLBACK_MODELS="[]"
$env:CONFIG__CUSTOM_MODEL_MAX_TOKENS="32768"
$env:OPENAI__API_BASE="http://127.0.0.1:8000/v1"
$env:OPENAI__KEY="local-api-key"
$env:OPENAI_API_KEY="local-api-key"
$env:TOKENIZER__LOCAL_CACHE_DIR="$PWD\tokenizers"
$env:TOKENIZER__ENABLE_LOCAL_CACHE="true"
$env:TOKENIZER__BACKEND="modelscope"
$env:TOKENIZER__MODELSCOPE_MODEL_ID="Qwen/Qwen3.6-35B-A3B-FP8"
$env:TOKENIZER__FALLBACK_TO_DOWNLOAD="true"
$env:TOKENIZER__OFFLINE_ESTIMATE_FALLBACK="true"
$env:TOKENIZER__SKIP_TOKEN_COUNT="false"
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe -m pr_agent.servers.bitbucket_server_polling
```

## Bitbucket token 权限

建议使用专门的 service account，并授予被轮询仓库：

- 读取项目和仓库
- 读取 pull request diff
- 在 pull request 上发表评论
- 如果启用 committable suggestions，需要允许写 PR 评论；不需要仓库写权限

不要把 token 写入 `.pr_agent.toml` 或提交到 git。使用 `.env`、CI/CD secret、Kubernetes Secret 或 systemd `EnvironmentFile`。

## 轮询行为

每轮执行步骤：

1. 调用 Bitbucket Server API 列出每个仓库的 open PR
2. 读取 PR `version`
3. 和 `polling_state_file` 中记录的 version/status 比较
4. 新 PR、version 变化、或上次状态为 `failed` / `processing` 时执行 `polling_commands`
5. 成功后写回 `completed`，过滤后写回 `filtered`，失败或超时写回 `failed`

只有 `completed` 和 `filtered` 会被视为已处理。`failed` 和异常遗留的 `processing` 会在下一轮继续重试，避免一次模型/API/进程异常导致 PR 永久漏审。

`max_parallel_tasks` 限制单轮最多同时 review 的 PR 数，超出的任务会延后到下一轮，不会被标记为已处理。

`polling_review_timeout_seconds` 是单个 PR review 子进程的超时时间。超过后服务会终止子进程并标记为 `failed`，后续轮询可重试。

Bitbucket PR 列表由底层客户端自动分页；内部 `limit=50` 是每页大小，不是最多只扫描 50 个 PR。

如果你想让某个 PR 重新触发 review，可以删除状态文件里对应的 PR 条目，或直接清空 state volume。

## 排错

`BITBUCKET_SERVER.URL not configured`

确认设置了 `BITBUCKET_SERVER__URL`。

`Failed to list pull requests ... path "rest/api/1.0/projects/..." does not exist at revision`

通常是 `BITBUCKET_SERVER__URL` 配成了 REST API 地址、仓库 `browse` 地址或 PR 地址，例如不要配置成 `https://bitbucket.example.com/projects/PROJ/repos/repo/browse`。
推荐配置 Bitbucket Server 站点根地址，例如：

```env
BITBUCKET_SERVER__URL=https://bitbucket.example.com
```

如果你的 Bitbucket 部署在 context path 下，例如 `/bitbucket`，则配置：

```env
BITBUCKET_SERVER__URL=https://git.example.com/bitbucket
```

程序会尽量在运行时把仓库地址或 PR 地址规范化为站点根地址，但配置文件里仍建议保持根地址，方便排查。

`Failed to get git provider for .../browse/projects/.../pull-requests/...`

这是 PR URL 被重复拼接的典型表现。先把 `BITBUCKET_SERVER__URL` 改成站点根地址；如果命令里有 `--pr_description.final_update_message=fales`，也要改成 `false`。

`No repositories configured for polling`

确认 `.pr_agent.toml` 里 `polling_repositories` 不为空，且格式是 `PROJECT/repo-slug`。

`Tokenizer not available in local cache and download is disabled`

说明当前缓存目录没有可用 tokenizer，且 `TOKENIZER__FALLBACK_TO_DOWNLOAD=false` 已阻止下载。默认情况下 `TOKENIZER__OFFLINE_ESTIMATE_FALLBACK=true` 会改用本地近似 token 估算并继续运行；如果你设置为 `false`，则需要复制预热好的 `tokenizers` 目录，或在允许联网的机器上先运行 `python -m pr_agent.algo.tokenizer_manager download --cache-dir ./tokenizers --modelscope-model-id Qwen/Qwen3.6-35B-A3B-FP8`。

模型服务连接失败

确认 `OPENAI__API_BASE` 可以从运行 PR-Agent 的进程或容器访问。容器内不要使用宿主机的 `127.0.0.1`，除非模型服务也在同一个容器里。

`401` 或 `403`

检查 Bitbucket service account token 是否有效，以及是否有目标项目和仓库的 PR 读取与评论权限。

## 验证

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/unittest/test_polling_state.py tests/unittest/test_bitbucket_provider.py tests/unittest/test_bitbucket_server_polling.py -q
docker compose config
```

## 目录

- `pr_agent/servers/bitbucket_server_polling.py`：轮询服务入口
- `pr_agent/git_providers/bitbucket_server_provider.py`：Bitbucket Server API 与 PR 评论发布
- `.pr_agent.toml`：非敏感运行配置示例
- `.env.example`：敏感配置和模型 endpoint 示例
- `Dockerfile`、`docker-compose.yml`：容器部署
- `deployment/systemd/`：systemd 部署示例
- `docs/BITBUCKET_POLLING.md`：轮询机制说明
