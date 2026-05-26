# Issue 006: Document and Operate Agentic Review

Labels: ready-for-agent, AFK

## What to build

Document how to enable and operate agentic review in local and Bitbucket Server polling deployments. The documentation
should explain the safety model, command allowlist, cache behavior, fallback behavior, recommended defaults for local
models, and how to debug agent traces.

This slice should also add concise runtime logging for agent loop start/stop, blocked commands, forced final responses,
fallbacks, and context budget usage.

## Acceptance criteria

- [x] Configuration docs include all agentic review settings and recommended defaults.
- [x] Bitbucket polling docs explain how local repository search works in intranet deployments.
- [x] README mentions the feature and links to detailed docs.
- [x] Logs identify agent loop start, tool calls, blocked commands, final stop reason, and fallback events.
- [x] Documentation includes security guidance for command allowlists and secret handling.
- [x] Tests or snapshots verify that default configuration keys are present and valid.

## Blocked by

- Issue 003: Integrate Agentic Mode with `/review`
- Issue 004: Integrate Agentic Mode with `/improve`
- Issue 005: Resolve Local Repository Roots for Agentic Review
