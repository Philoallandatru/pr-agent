# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PR-Agent is an open-source AI-powered code review tool that automates pull request analysis across multiple git providers (GitHub, GitLab, Bitbucket, Azure DevOps, Gitea). The system uses LLM models to provide reviews, code suggestions, PR descriptions, and other automated feedback.

## Development Setup

**Requirements**: Python ≥ 3.12

**Install dependencies**:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

**Environment variables**: Set API keys for LLM providers (e.g., `OPENAI_KEY`) and git provider tokens (e.g., `GITHUB_TOKEN`) as needed.

## Common Commands

**Run CLI locally**:
```bash
python -m pr_agent.cli --pr_url https://github.com/owner/repo/pull/123 review
```

Available commands: `review`, `describe`, `improve`, `ask`, `reflect`, `update_changelog`, `add_docs`, `generate_labels`, `help_docs`

**Run single test** (always set `PYTHONPATH=.`):
```bash
PYTHONPATH=. pytest tests/unittest/test_fix_json_escape_char.py -q
```

**Run all unit tests**:
```bash
PYTHONPATH=. pytest tests/unittest -v
```

**Run e2e tests** (requires provider tokens):
```bash
PYTHONPATH=. pytest tests/e2e_tests -v
```

**Lint with Ruff**:
```bash
ruff check .
```

**Run pre-commit hooks**:
```bash
pre-commit run --all-files
```

**Build Docker test target**:
```bash
docker build -f docker/Dockerfile --target test .
```

**Serve documentation locally**:
```bash
mkdocs serve -f docs/mkdocs.yml
```

## Architecture

### Core Components

- **`pr_agent/agent/pr_agent.py`**: Main orchestrator that routes commands (`review`, `describe`, `improve`, etc.) to appropriate tool classes via the `command2class` mapping.

- **`pr_agent/tools/`**: Individual tool implementations:
  - `pr_reviewer.py` - Code review with suggestions
  - `pr_code_suggestions.py` - Improvement suggestions
  - `pr_description.py` - Auto-generate PR descriptions
  - `pr_questions.py` - Answer questions about PRs
  - `pr_update_changelog.py` - Changelog generation
  - `pr_add_docs.py` - Documentation suggestions
  - `pr_generate_labels.py` - Auto-label PRs
  - `pr_help_docs.py` - Context-aware help
  - `ticket_pr_compliance_check.py` - Compliance validation

- **`pr_agent/git_providers/`**: Adapters for different git platforms (GitHub, GitLab, Bitbucket, Azure DevOps, Gitea, Gerrit, CodeCommit). Each provider implements the `GitProvider` interface for fetching PR data, posting comments, updating descriptions, etc.

- **`pr_agent/algo/`**: Core algorithms and utilities:
  - `git_patch_processing.py` - Parse and process git diffs
  - `pr_processing.py` - PR compression and token management
  - `token_handler.py` - Token counting and limits
  - `file_filter.py` - Filter files based on patterns
  - `language_handler.py` - Language-specific processing
  - `ai_handlers/` - LLM provider integrations (LiteLLM, OpenAI, Anthropic, etc.)

- **`pr_agent/servers/`**: Deployment modes:
  - `github_app.py` - GitHub App webhook server
  - `gitlab_webhook.py` - GitLab webhook server
  - `bitbucket_app.py` - Bitbucket webhook server
  - `github_action_runner.py` - GitHub Actions integration
  - `azuredevops_server_webhook.py` - Azure DevOps webhook

- **`pr_agent/settings/`**: Configuration and prompts stored as TOML files:
  - `configuration.toml` - Main configuration defaults
  - `pr_description_prompts.toml` - Prompts for PR descriptions
  - `pr_code_suggestions_prompts.toml` - Prompts for code suggestions
  - `ignore.toml` - File/pattern ignore rules
  - `language_extensions.toml` - Language detection mappings

### Configuration System

PR-Agent uses **Dynaconf** for hierarchical configuration:

1. **Base defaults**: `pr_agent/settings/configuration.toml`
2. **Repository overrides**: `.pr_agent.toml` in repo root
3. **Wiki settings**: Fetched from repo wiki if enabled
4. **CLI arguments**: Override via `--config_path=value` syntax

Example CLI override:
```bash
pr-agent --pr_url=... review --pr_reviewer.extra_instructions="focus on security"
```

### PR Compression Strategy

PR-Agent handles large PRs through token-aware compression:
- Dynamically includes context lines around hunks (configurable via `patch_extra_lines_before/after`)
- Clips or skips large patches based on `large_patch_policy`
- Uses `max_model_tokens` to stay within model limits
- Supports dynamic context expansion to include enclosing functions/classes

## Testing Guidelines

- **Unit tests**: `tests/unittest/` - Test individual functions and utilities
- **E2E tests**: `tests/e2e_tests/` - Integration tests requiring provider credentials
- **Health tests**: `tests/health_test/` - Smoke tests for core commands

Always run pytest with `PYTHONPATH=.` to avoid import errors.

E2E tests require environment variables: `TOKEN_GITHUB`, `TOKEN_GITLAB`, `BITBUCKET_USERNAME`, `BITBUCKET_PASSWORD`, etc.

## Code Style

- **Line length**: 120 characters (enforced by Ruff)
- **Import ordering**: isort (auto-fixed by Ruff)
- **Linting**: Ruff checks Pyflakes, flake8-bugbear rules
- **Pre-commit**: Enforces trailing whitespace, final newlines, TOML/YAML validity

Match existing code style - avoid mass reformatting or reordering.

## Configuration Files

- **`.pr_agent.toml`**: Repository-specific overrides (this repo's config enables auto-approval, review labels, and agentic review)
- **`pr_agent/settings/*.toml`**: Prompt templates and configuration defaults - treat as single source of truth
- **`pyproject.toml`**: Python packaging, Ruff config, pytest settings

When modifying prompts or configuration, update the appropriate TOML file and test with the affected command.

## Deployment Modes

PR-Agent supports multiple deployment patterns:

1. **CLI**: Local execution via `python -m pr_agent.cli`
2. **GitHub Action**: `.github/workflows/pr-agent.yml` workflow
3. **Webhook servers**: FastAPI-based servers in `pr_agent/servers/`
4. **Docker**: Multi-stage Dockerfile with service-specific targets
5. **GitHub App**: Installable app with webhook integration

Each mode uses the same core tools but different entry points and authentication methods.

## Important Notes

- **Never commit secrets**: Use environment variables for API keys and tokens
- **PYTHONPATH requirement**: Always set `PYTHONPATH=.` when running pytest from repo root
- **Configuration hierarchy**: Repository `.pr_agent.toml` overrides base `configuration.toml`
- **Prompt modifications**: Update TOML files in `pr_agent/settings/`, not hardcoded strings
- **Provider-specific features**: Some tools (e.g., `ask_lines`, `chat_on_code_suggestions`) are GitHub-only
- **Token limits**: Respect `max_model_tokens` and `max_description_tokens` to avoid model failures
