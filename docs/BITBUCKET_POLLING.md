# Bitbucket Server Polling Service

The polling service monitors configured Bitbucket Server / Data Center repositories for open pull requests. It runs configured PR-Agent commands when it sees a new PR or a newer PR version.

This deployment is designed for local or intranet OpenAI-compatible model services. Runtime should not fetch model or tokenizer assets from Hugging Face or other public networks.

## Required configuration

Keep non-secret behavior in `.pr_agent.toml`:

```toml
[config]
git_provider = "bitbucket_server"
model = "openai/local-review-model"
fallback_models = []
custom_model_max_tokens = 32768
response_language = "zh-CN"

[bitbucket_server]
enable_polling = true
polling_interval_seconds = 300
polling_repositories = [
    "PROJ/backend-api",
]
polling_commands = [
    "/describe --pr_description.final_update_message=false",
    "/review --pr_reviewer.require_security_review=true",
    "/improve --pr_code_suggestions.commitable_code_suggestions=true",
]
polling_state_file = "/data/state/polling_state.json"
max_parallel_tasks = 4
polling_review_timeout_seconds = 1800

[tokenizer]
local_cache_dir = "/data/tokenizers"
enable_local_cache = true
fallback_to_download = false
offline_estimate_fallback = true
skip_token_count = true
```

Keep secrets and endpoint addresses in environment variables:

```env
BITBUCKET_SERVER__URL=https://bitbucket.example.com
BITBUCKET_SERVER__BEARER_TOKEN=replace-with-token
BITBUCKET_SERVER__POLLING_REVIEW_TIMEOUT_SECONDS=1800
OPENAI__API_BASE=http://host.docker.internal:8000/v1
OPENAI__KEY=local-api-key
OPENAI_API_KEY=local-api-key
TIKTOKEN_CACHE_DIR=/data/tokenizers
```

`polling_repositories` values must use `PROJECT/repo-slug`, matching Bitbucket URLs like:

```text
https://bitbucket.example.com/projects/PROJECT/repos/repo-slug/pull-requests/123
```

## Local model endpoint

Any service compatible with OpenAI chat completions can be used:

- vLLM OpenAI-compatible server
- llama.cpp server with `/v1`
- LM Studio local server
- Ollama OpenAI-compatible endpoint
- Internal model gateway

PR-Agent only needs the service to be reachable at `OPENAI__API_BASE` and to expose the model name configured in `CONFIG__MODEL` / `[config].model`.

## Strict offline tokenizer mode

Set:

```env
TOKENIZER__ENABLE_LOCAL_CACHE=true
TOKENIZER__FALLBACK_TO_DOWNLOAD=false
TOKENIZER__OFFLINE_ESTIMATE_FALLBACK=true
TOKENIZER__SKIP_TOKEN_COUNT=true
TOKENIZER__LOCAL_CACHE_DIR=/data/tokenizers
TIKTOKEN_CACHE_DIR=/data/tokenizers
```

With this setting, PR-Agent will not download tokenizer data from public URLs. `TOKENIZER__SKIP_TOKEN_COUNT=true` bypasses tiktoken entirely and never loads tokenizer encodings; use it when the model service already enforces context limits or when avoiding outbound access is more important than local prompt sizing. If you keep token counting enabled and the tiktoken cache is missing, `TOKENIZER__OFFLINE_ESTIMATE_FALLBACK=true` uses local approximate token counting so the service can still start with local/intranet models. Set it to `false` if you prefer to fail fast on missing cache. For accurate token counts, prewarm cache on a machine that is allowed to access tokenizer assets, then copy the whole directory to the deployment host:

```bash
python -m pr_agent.algo.tokenizer_manager download \
  --cache-dir ./tokenizers \
  --models openai/local-review-model o200k_base
```

For unknown local models, `o200k_base` is used for estimation. Set `custom_model_max_tokens` to the context length your deployed model actually supports.

## Running

Docker Compose:

```bash
cp .env.example .env
docker compose up -d --build
docker compose logs -f pr-agent-polling
```

The polling service defaults to readable console logs. Set `PR_AGENT_LOG_FORMAT=JSON` only when a log collector expects structured JSON records.

Python directly:

```bash
export PR_AGENT_CONFIG_FILE="$PWD/.pr_agent.toml"
export CONFIG__GIT_PROVIDER=bitbucket_server
export BITBUCKET_SERVER__URL=https://bitbucket.example.com
export BITBUCKET_SERVER__BEARER_TOKEN=replace-with-token
export BITBUCKET_SERVER__POLLING_REVIEW_TIMEOUT_SECONDS=1800
export CONFIG__MODEL=openai/local-review-model
export OPENAI__API_BASE=http://127.0.0.1:8000/v1
export OPENAI__KEY=local-api-key
export OPENAI_API_KEY=local-api-key
export TOKENIZER__LOCAL_CACHE_DIR="$PWD/tokenizers"
export TOKENIZER__ENABLE_LOCAL_CACHE=true
export TOKENIZER__FALLBACK_TO_DOWNLOAD=false
export TOKENIZER__OFFLINE_ESTIMATE_FALLBACK=true
export TOKENIZER__SKIP_TOKEN_COUNT=true
export TIKTOKEN_CACHE_DIR="$PWD/tokenizers"
PYTHONPATH=. python -m pr_agent.servers.bitbucket_server_polling
```

## State file

The state file prevents duplicate reviews:

```json
{
  "PROJ/backend-api": {
    "123": {
      "version": 5,
      "last_processed": "2026-05-22T10:30:00",
      "commands_run": ["/describe", "/review", "/improve"],
      "status": "processing"
    }
  }
}
```

The service skips only PR versions whose status is `completed` or `filtered`.

If a PR version is `failed` or left as `processing` after a crash, the same version is eligible for retry on the next polling iteration. This avoids permanently missing a PR because a model request, Bitbucket request, or review process failed once.

`polling_review_timeout_seconds` bounds each review process. If a child process exceeds this timeout, the polling service terminates it, marks the PR version as `failed`, and retries it in a later poll.

`max_parallel_tasks` limits how many PRs are reviewed in one batch. Extra PRs are deferred, not marked as processed, so they are picked up by a later poll.

Bitbucket Server pull request listing is paginated by the underlying client. The `limit` used internally is a page size, not a maximum number of PRs to scan.

## Filtering

The polling flow uses the same filtering logic as webhooks:

- `config.ignore_repositories`
- `config.ignore_pr_authors`
- `config.ignore_pr_title`
- `config.ignore_pr_source_branches`
- `config.ignore_pr_target_branches`

## Troubleshooting

`BITBUCKET_SERVER.URL not configured`: set `BITBUCKET_SERVER__URL`.

`Failed to list pull requests ... path "rest/api/1.0/projects/..." does not exist at revision`: set `BITBUCKET_SERVER__URL` to the Bitbucket Server site root only, not a REST API URL, repository `browse` URL, or PR URL. Use `https://bitbucket.example.com`, or `https://git.example.com/bitbucket` when Bitbucket is deployed under a context path.

`Failed to get git provider for .../browse/projects/.../pull-requests/...`: the PR URL was built from a repository page URL such as `https://bitbucket.example.com/projects/PROJ/repos/repo/browse`. Change `BITBUCKET_SERVER__URL` to the site root. Also check command typos such as `--pr_description.final_update_message=fales`; the boolean value should be `false`.

`No repositories configured for polling`: set `bitbucket_server.polling_repositories`.

`Tokenizer not available in local cache and download is disabled`: mount or copy a prewarmed tokenizer cache directory.

Model connection errors: check `OPENAI__API_BASE` from inside the PR-Agent process or container.

`401` or `403`: check the Bitbucket token and repository permissions.
