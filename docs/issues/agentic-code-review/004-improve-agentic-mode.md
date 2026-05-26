# Issue 004: Integrate Agentic Mode with `/improve`

Labels: ready-for-agent, AFK

## What to build

Add an optional agentic path for `/improve`. When enabled, PR-Agent should allow the model to search local repository
context before returning the existing code-suggestions YAML. The final suggestions must still flow through the existing
suggestion parser, self-reflection, summarization, and inline/committable publishing paths.

This slice should focus on preserving precise suggestion location behavior. Agentic context may inform the suggestion,
but the final output must still identify changed files and existing code in the format that current `/improve` expects.

## Acceptance criteria

- [ ] New configuration enables agentic mode for `/improve` independently of `/review`.
- [ ] Existing improve prompt rendering remains the source of truth for the task and YAML output format.
- [ ] Agent final content is parsed by the existing code suggestion parser.
- [ ] Existing self-reflection behavior still runs after agent final suggestions are parsed.
- [ ] If agent mode fails and fallback is enabled, `/improve` uses the existing direct model path.
- [ ] Unit tests verify enabled, disabled, fallback, and parse-compatible final output behavior.
- [ ] Existing code suggestion tests continue to pass.

## Blocked by

- Issue 001: Add Agent Loop Core for Tool-Using Review
- Issue 002: Add Read-Only Local Repository Tools

