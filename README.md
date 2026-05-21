# Bitbucket Server PR AI Reviewer

这是一个面向 Bitbucket Server / Data Center 的 PR-Agent 精简部署版本。它不依赖 webhook，而是定时轮询指定仓库的 open pull requests，发现新 PR 或 PR version 更新后自动执行 AI review 命令，并把结果发布回 PR。

默认执行：

- `/describe`：生成 PR 摘要
- `/review`：发布代码审查意见
- `/improve`：发布可提交的改进建议

## 目录

- `pr_agent/servers/bitbucket_server_polling.py`：轮询服务入口
- `pr_agent/git_providers/bitbucket_server_provider.py`：Bitbucket Server API 与 PR 评论发布
- `.pr_agent.toml`：非敏感运行配置示例
- `.env.example`：敏感配置和容器环境变量示例
- `Dockerfile`、`docker-compose.yml`：推荐容器部署
- `deployment/systemd/`：systemd 部署示例
- `docs/BITBUCKET_POLLING.md`：更细的轮询机制说明

## 快速部署

### 1. 准备配置

复制环境变量模板：

```bash
cp .env.example .env
```

编辑 `.env`：

```env
CONFIG__GIT_PROVIDER=bitbucket_server
BITBUCKET_SERVER__URL=https://bitbucket.example.com
BITBUCKET_SERVER__BEARER_TOKEN=replace-with-bitbucket-personal-access-token
OPENAI__KEY=sk-replace-me
OPENAI_API_KEY=sk-replace-me
```

编辑 `.pr_agent.toml`，把仓库列表改成你的 Bitbucket Server 项目和仓库：

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
```

仓库格式必须是 `PROJECT/repo-slug`，对应 PR URL：

```text
https://bitbucket.example.com/projects/PROJECT/repos/repo-slug/pull-requests/123
```

### 2. Docker Compose 启动

```bash
docker compose up -d --build
docker compose logs -f pr-agent-polling
```

服务会每 `polling_interval_seconds` 秒查询一次配置里的仓库。状态文件保存在 Docker volume `polling-state` 中，重启后不会重复处理已处理过的 PR version。

### 3. 本地启动

Python 需要 `>=3.12`：

```bash
python -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/pip install -e .

export PR_AGENT_CONFIG_FILE="$PWD/.pr_agent.toml"
export CONFIG__GIT_PROVIDER=bitbucket_server
export BITBUCKET_SERVER__URL=https://bitbucket.example.com
export BITBUCKET_SERVER__BEARER_TOKEN=replace-with-token
export OPENAI__KEY=sk-replace-me

PYTHONPATH=. ./.venv/bin/python -m pr_agent.servers.bitbucket_server_polling
```

Windows PowerShell 等价命令：

```powershell
$env:PR_AGENT_CONFIG_FILE="$PWD\.pr_agent.toml"
$env:CONFIG__GIT_PROVIDER="bitbucket_server"
$env:BITBUCKET_SERVER__URL="https://bitbucket.example.com"
$env:BITBUCKET_SERVER__BEARER_TOKEN="replace-with-token"
$env:OPENAI__KEY="sk-replace-me"
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

## AI 模型配置

默认模型来自 `pr_agent/settings/configuration.toml`。可以在 `.env` 中覆盖：

```env
CONFIG__MODEL=gpt-4o
OPENAI__KEY=sk-replace-me
```

也可以使用 LiteLLM 支持的其他模型，只要补齐对应 provider 的环境变量。

## 轮询行为

每轮执行步骤：

1. 调用 Bitbucket Server API 列出每个仓库的 open PR
2. 读取 PR `version`
3. 和 `polling_state_file` 中记录的 version 比较
4. 新 PR 或 version 变化时执行 `polling_commands`
5. 写回状态，避免重复审查

如果你想让某个 PR 重新触发 review，可以删除状态文件里对应的 PR 条目，或直接清空 state volume。

## 常用配置

```toml
[config]
response_language = "zh-CN"
ignore_pr_title = ["^\\[WIP\\]", "^Draft"]
ignore_pr_source_branches = ["^dependabot/"]

[pr_reviewer]
require_security_review = true
require_tests_review = true
num_max_findings = 5

[pr_code_suggestions]
commitable_code_suggestions = true
focus_only_on_problems = true
```

更多配置项见 `pr_agent/settings/configuration.toml`，只把需要覆盖的配置写进 `.pr_agent.toml`。

## systemd 部署

参考：

```bash
cat deployment/systemd/README.md
```

核心服务文件是：

```text
deployment/systemd/pr-agent-polling.service
```

## 验证

本地基础验证：

```bash
PYTHONPATH=. ./.venv/bin/pytest tests/unittest/test_polling_state.py -q
PYTHONPATH=. ./.venv/bin/pytest tests/unittest/test_bitbucket_provider.py -q
```

启动服务后，在日志里应该看到：

```text
Starting Bitbucket Server polling service
Polling configuration: ...
Polling iteration #1 started
```

## 排错

`Bitbucket Server polling is not enabled`

确认 `.pr_agent.toml` 包含：

```toml
[bitbucket_server]
enable_polling = true
```

`No repositories configured for polling`

确认 `polling_repositories` 不为空，且格式是 `PROJECT/repo-slug`。

`BITBUCKET_SERVER.URL not configured`

确认容器或进程环境变量包含：

```env
BITBUCKET_SERVER__URL=https://bitbucket.example.com
```

`Invalid or missing Bitbucket Server URL parsed from PR URL`

通常是没有设置 `BITBUCKET_SERVER__URL`，或 `.env` 没有被 Docker Compose 传入容器。使用：

```bash
docker compose exec pr-agent-polling env | grep BITBUCKET_SERVER
```

`401` 或 `403`

检查 service account token 是否有效，以及是否有目标项目和仓库的 PR 读取与评论权限。

## 维护说明

这个仓库已经删除了与目标部署无关的前端管理台、通用 MkDocs 站点和一次性项目总结文档。保留内容聚焦于 Bitbucket Server 轮询 reviewer 的源码、测试、容器部署和 systemd 部署。
