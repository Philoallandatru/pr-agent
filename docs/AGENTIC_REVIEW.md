# Agentic Review

Agentic review is an optional mode for `/review` and `/improve`. It wraps the existing PR-Agent prompts with a small
tool loop so the model can inspect the local repository before returning the normal review YAML or code-suggestion YAML.

The feature is disabled by default. Enable it only where PR-Agent has access to a trusted local checkout or to the
existing repository context clone cache.

## Configuration

```toml
[agentic_review]
enabled = false
commands = ["review", "improve"]
repo_root = ""
use_repo_context_cache = false
force_repo_context_refresh = false
max_iterations = 8
max_total_context_chars = 40000
command_timeout_seconds = 10
max_command_output_chars = 40000
fallback_to_direct_review = true
```

Recommended local-model defaults:

- Keep `enabled = false` until the deployment has a predictable local checkout or clone cache.
- Use `commands = ["review"]` first, then add `"improve"` after validating suggestion quality.
- Leave `fallback_to_direct_review = true` in polling deployments so a repository search failure does not block PR
  processing.
- Keep `max_iterations` small. Most useful repository lookups finish within 3 to 5 tool calls.
- Use `use_repo_context_cache = true` only when `repo_context.clone_cache_dir` is configured on a persistent volume.

## Repository Root Resolution

The read-only tools run from a normalized repository root. PR-Agent resolves it in this order:

1. `agentic_review.repo_root`, when set.
2. A provider checkout path such as `LocalGitProvider.repo_path` or Gerrit `repo_path`.
3. The existing `repo_context` clone/cache when `use_repo_context_cache = true`.
4. The nearest parent directory containing `.git` from the current working directory.

If no directory can be resolved, agentic review raises a clear error. With `fallback_to_direct_review = true`, `/review`
and `/improve` continue through the existing direct model call path.

## Safety Model

The tool executor never invokes a shell. Commands are split into arguments, run with the repository root as `cwd`, and
checked against an allowlist.

Allowed command families:

- `ls`
- `cat`
- `rg`
- `grep`
- `git status`
- `git show`
- `git diff`
- `git log`
- `git rev-parse`
- `git ls-files`

Mutation commands, package managers, network tools, test execution, redirection, pipes, and arbitrary PowerShell/cmd
syntax are blocked. `ls` and `cat` are implemented as built-ins so they work consistently on Windows and Linux. Built-in
file reads reject paths outside the repository root.

Do not store Bitbucket, GitHub, GitLab, model, or registry tokens in repository files. Keep secrets in environment
variables or the deployment secret manager. Agentic tool output can include file content, so avoid enabling repository
search on checkouts that contain committed secrets.

## Bitbucket Server Polling

For polling deployments, the safest setup is:

```toml
[agentic_review]
enabled = true
commands = ["review", "improve"]
use_repo_context_cache = true
fallback_to_direct_review = true

[repo_context]
clone_cache_dir = "/data/pr-agent-repos"
clone_depth = 1
```

Mount `/data/pr-agent-repos` on persistent storage. PR-Agent reuses the existing `repo_context` clone/cache behavior
when the provider does not already expose a local checkout. Clone or update failures are logged and fall back to direct
review when fallback is enabled.

## Logs

Agentic review logs these events:

- loop start, including model and configured limits
- each tool call
- blocked or duplicate commands
- context budget exhaustion
- forced final responses
- final stop reason
- fallback events in `/review` and `/improve`

For JSON log collection, set `PR_AGENT_LOG_FORMAT=JSON`. Otherwise the default console format is easier to read during
local debugging.
