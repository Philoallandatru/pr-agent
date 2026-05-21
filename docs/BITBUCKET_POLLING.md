# Bitbucket Server Polling Service

The polling service monitors configured Bitbucket Server / Data Center repositories for open pull requests. It runs configured PR-Agent commands when it sees a new PR or a newer PR version.

Use this when webhook delivery is hard to expose from an internal Bitbucket instance.

## Required configuration

Keep non-secret behavior in `.pr_agent.toml`:

```toml
[config]
git_provider = "bitbucket_server"
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
```

Keep secrets in environment variables:

```env
BITBUCKET_SERVER__URL=https://bitbucket.example.com
BITBUCKET_SERVER__BEARER_TOKEN=replace-with-token
OPENAI__KEY=sk-replace-me
OPENAI_API_KEY=sk-replace-me
```

`polling_repositories` values must use `PROJECT/repo-slug`, matching Bitbucket URLs like:

```text
https://bitbucket.example.com/projects/PROJECT/repos/repo-slug/pull-requests/123
```

## Running

Docker Compose:

```bash
cp .env.example .env
docker compose up -d --build
docker compose logs -f pr-agent-polling
```

Local:

```bash
export PR_AGENT_CONFIG_FILE="$PWD/.pr_agent.toml"
export CONFIG__GIT_PROVIDER=bitbucket_server
export BITBUCKET_SERVER__URL=https://bitbucket.example.com
export BITBUCKET_SERVER__BEARER_TOKEN=replace-with-token
export OPENAI__KEY=sk-replace-me
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

The service processes the PR again only when Bitbucket reports a newer `version`.

## Filtering

The polling flow uses the same filtering logic as webhooks:

- `config.ignore_repositories`
- `config.ignore_pr_authors`
- `config.ignore_pr_title`
- `config.ignore_pr_source_branches`
- `config.ignore_pr_target_branches`

Example:

```toml
[config]
ignore_pr_title = ["^\\[WIP\\]", "^Draft"]
ignore_pr_source_branches = ["^dependabot/"]
```

## Operational notes

- Start with `polling_interval_seconds = 300`.
- Keep `max_parallel_tasks` conservative until you know the AI provider rate limit.
- Use a dedicated Bitbucket service account.
- Put the state file on persistent storage.
- Delete a PR entry from the state file if you intentionally want to re-run review on the same PR version.

## Troubleshooting

`Bitbucket Server polling is not enabled`: set `bitbucket_server.enable_polling = true`.

`No repositories configured for polling`: set `bitbucket_server.polling_repositories`.

`BITBUCKET_SERVER.URL not configured`: set `BITBUCKET_SERVER__URL` in the process environment.

`401` or `403`: check the Bitbucket token and repository permissions.

No comments appear on the PR: check service logs, token permissions, and whether filters skipped the PR.
