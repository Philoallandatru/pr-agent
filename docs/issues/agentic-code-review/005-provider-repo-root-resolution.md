# Issue 005: Resolve Local Repository Roots for Agentic Review

Labels: ready-for-agent, AFK

## What to build

Build provider-aware repository root resolution for agentic review. The read-only tool layer needs a local repository
root regardless of how PR-Agent is invoked: CLI, GitHub/GitLab/Bitbucket provider context, or Bitbucket Server polling.

The resolver should prefer an already available local checkout when one exists, and use the existing repository context
cache/clone settings when a clone is required. It should integrate with the existing repository context configuration
instead of introducing a separate clone cache.

## Acceptance criteria

- [x] CLI/local invocation can resolve the current working repository root.
- [x] Bitbucket Server polling can resolve or prepare a local repository checkout for the PR under review.
- [x] Git provider integrations can opt into cached clone resolution without changing existing direct review behavior.
- [x] Resolved paths are normalized and guaranteed to be directories before tools execute.
- [x] Clone/cache failures produce clear log messages and trigger configured fallback behavior.
- [x] Unit tests cover current working repo, cached repo, missing repo, and clone failure scenarios.

## Blocked by

- Issue 002: Add Read-Only Local Repository Tools
