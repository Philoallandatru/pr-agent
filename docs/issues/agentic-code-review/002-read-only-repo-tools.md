# Issue 002: Add Read-Only Local Repository Tools

Labels: ready-for-agent, AFK

## What to build

Build the read-only repository exploration tool layer used by agentic review. The first version should maximize reuse of
`ai-review` by supporting a shell-command allowlist for targeted repository exploration: file listing, file reading,
ripgrep search, grep search, and safe git inspection commands.

The tool layer must execute commands from a resolved repository root without shell interpolation, enforce a strict
allowlist, capture stdout and stderr, apply timeout and output-size limits, and return a deterministic textual result to
the agent loop. It must not allow mutating commands, package managers, network commands, test execution, or arbitrary
PowerShell/cmd syntax.

## Acceptance criteria

- [ ] Allowed commands include `ls`, `cat`, `rg`, `grep`, and limited `git status/show/diff/log/rev-parse/ls-files`.
- [ ] Disallowed commands return a blocked-command message and are never executed.
- [ ] Commands run with repository root as cwd and do not use a shell.
- [ ] Command parsing errors return a deterministic error message.
- [ ] Command timeout returns a deterministic timeout message.
- [ ] Large stdout/stderr output is truncated to the configured limit.
- [ ] Tool output includes command, exit code, stdout, and stderr.
- [ ] Unit tests cover allowlist behavior, blocked mutation commands, timeout, truncation, stderr capture, and parse errors.

## Blocked by

None - can start immediately

