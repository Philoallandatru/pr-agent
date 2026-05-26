# Bitbucket Server PR AI Reviewer

Agentic review is an optional repository-search mode for `/review` and `/improve`. When enabled, PR-Agent keeps the
existing review/improve prompts and final YAML contracts, but lets the model run a small read-only loop over local
repository tools before producing the final answer. See `docs/AGENTIC_REVIEW.md` for the full configuration, safety
model, and operational logs.

这是一个面向 Bitbucket Server / Data Center 的轮询式 PR AI reviewer。它不依赖 webhook，而是定时扫描指定仓库的 open pull requests，发现新 PR 或 PR version 更新后自动执行 `/describe`、`/review`、`/improve`，并把结果发布回 PR。

本仓库的默认部署目标是：使用本地或内网已经部署好的 OpenAI-compatible 模型服务，不依赖 OpenAI 公网，不在运行时从 Hugging Face 或其他公网下载模型资源。

## 快速开始

### 1. 启动本地 OpenAI-compatible 模型服务

先保证你已经有一个兼容 OpenAI `/v1/chat/completions` 的服务，例如 vLLM、llama.cpp server、LM Studio、Ollama 的 OpenAI-compatible endpoint，或公司内部模型网关。

PR-Agent 不负责下载或启动大模型本体。推荐先单独验证模型服务：

```bash
curl http://127.0.0.1:8000/v1/models
```

如果服务需要 API key，记下 key；如果不需要，也填写一个占位值，例如 `local-api-key`。

### 2. 准备配置

```bash
cp .env.example .env
```

编辑 `.env`：

```env
CONFIG__GIT_PROVIDER=bitbucket_server
BITBUCKET_SERVER__URL=https://bitbucket.example.com
BITBUCKET_SERVER__BEARER_TOKEN=replace-with-bitbucket-personal-access-token
BITBUCKET_SERVER__POLLING_REVIEW_TIMEOUT_SECONDS=1800

CONFIG__MODEL=openai/local-review-model
CONFIG__FALLBACK_MODELS=[]
CONFIG__CUSTOM_MODEL_MAX_TOKENS=32768
OPENAI__API_BASE=http://host.docker.internal:8000/v1
OPENAI__KEY=local-api-key
OPENAI_API_KEY=local-api-key

TOKENIZER__LOCAL_CACHE_DIR=/data/tokenizers
TOKENIZER__ENABLE_LOCAL_CACHE=true
TOKENIZER__BACKEND=modelscope
TOKENIZER__MODELSCOPE_MODEL_ID=Qwen/Qwen3.6-35B-A3B-FP8
TOKENIZER__FALLBACK_TO_DOWNLOAD=true
TOKENIZER__OFFLINE_ESTIMATE_FALLBACK=true
TOKENIZER__SKIP_TOKEN_COUNT=false
```

说明：

- `OPENAI__API_BASE` 指向你已经部署好的 OpenAI-compatible 服务。
- `CONFIG__MODEL` 使用 LiteLLM 的 OpenAI provider 写法，建议保留 `openai/` 前缀。
- `CONFIG__FALLBACK_MODELS=[]` 避免主模型失败后切到公网模型。
- `CONFIG__CUSTOM_MODEL_MAX_TOKENS` 是本地/自定义模型的上下文上限；默认已经是 `32768`，可按你的模型实际上下文调大或调小。
- `TOKENIZER__BACKEND=modelscope` 表示使用 ModelScope 下载 tokenizer，并用 Transformers 加载。
- `TOKENIZER__MODELSCOPE_MODEL_ID=Qwen/Qwen3.6-35B-A3B-FP8` 是默认的 Qwen3.6 tokenizer 模型。
- `TOKENIZER__FALLBACK_TO_DOWNLOAD=true` 表示本地缓存缺失时允许从 ModelScope 下载 tokenizer。
- `TOKENIZER__OFFLINE_ESTIMATE_FALLBACK=true` 表示没有本地 tokenizer/cache 时使用本地近似 token 估算，服务仍可启动；如果你希望缺缓存直接失败，可设为 `false`。
- `TOKENIZER__SKIP_TOKEN_COUNT=false` 表示启用 token 计算；如果设为 `true`，会完全跳过 token 计算。
- Docker Desktop 场景下，容器访问宿主机服务通常用 `http://host.docker.internal:端口/v1`。Linux 服务器上建议用模型服务的内网 IP、容器网络名或网关地址。

编辑 `.pr_agent.toml`，配置要轮询的仓库：

```toml
[bitbucket_server]
enable_polling = true
polling_interval_seconds = 300
polling_repositories = [
    "PROJ/backend-api",
    "PROJ/frontend-app",
]
polling_commands = [
    "/describe --pr_description.final_update_message=false",
    "/review --pr_reviewer.require_security_review=true",
    "/improve --pr_code_suggestions.commitable_code_suggestions=true",
]
polling_state_file = "/data/state/polling_state.json"
max_parallel_tasks = 4
polling_review_timeout_seconds = 1800
```

仓库格式必须是 `PROJECT/repo-slug`，对应 PR URL：

```text
https://bitbucket.example.com/projects/PROJECT/repos/repo-slug/pull-requests/123
```

### 3. 预置 tokenizer/cache

严格内网环境下，运行服务前要确保 `/data/tokenizers` 已经有 tokenizer 缓存。可以在有网络的同构环境中预热一次，再把整个缓存目录复制到部署机器：

```bash
python -m pr_agent.algo.tokenizer_manager download \
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
