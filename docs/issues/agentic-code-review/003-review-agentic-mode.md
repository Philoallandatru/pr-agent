# Issue 003: Integrate Agentic Mode with `/review`

Labels: ready-for-agent, AFK

## What to build

Add an optional agentic path for `/review`. When enabled, PR-Agent should generate the normal review system and user
prompts, then pass them through the agent loop instead of making a direct one-shot model call. The agent final content
must remain the same YAML contract currently parsed by the review flow.

This slice should be end-to-end demoable with fake AI responses: the fake model first asks to search the repo, receives a
tool result, then returns a valid review YAML that is parsed and rendered by the existing review publication logic.

## Acceptance criteria

- [ ] New configuration enables agentic mode for `/review` without changing the default direct review behavior.
- [ ] Existing review prompt rendering remains the source of truth for the task and YAML output format.
- [ ] Agent final content is passed into the existing review YAML parser unchanged.
- [ ] If agent mode fails and fallback is enabled, `/review` uses the existing direct model path.
- [ ] If agent mode is disabled, no agent modules are invoked.
- [ ] Unit tests verify enabled, disabled, and fallback behavior with fake AI/tool components.
- [ ] Existing review tests continue to pass.

## Blocked by

- Issue 001: Add Agent Loop Core for Tool-Using Review
- Issue 002: Add Read-Only Local Repository Tools

