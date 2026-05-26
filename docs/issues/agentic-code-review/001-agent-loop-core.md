# Issue 001: Add Agent Loop Core for Tool-Using Review

Labels: ready-for-agent, AFK

## What to build

Build the reusable agent loop core that can wrap an existing PR-Agent prompt and repeatedly ask the model for either a
tool call or a final answer. The loop should adapt the `ai-review` agent loop design to PR-Agent's existing AI handler
interface, preserving the existing final output contracts for `/review` and `/improve`.

The implementation should reuse the `ai-review` concepts of agent step, trace, loop result, duplicate command blocking,
context budget, max iteration limit, force-final behavior, and fallback handling. Because this project is AGPLv3 and
`ai-review` is Apache-2.0, adapted code must include clear attribution where appropriate.

## Acceptance criteria

- [ ] A reusable agent loop module can run with a fake AI handler and a fake tool executor.
- [ ] The model protocol supports exactly two actions: `TOOL_CALL` and `FINAL`.
- [ ] Tool calls are recorded as traces with command, output, raw model response, iteration, and token metadata when available.
- [ ] Duplicate tool calls are blocked and surfaced as warnings in the trace.
- [ ] The loop stops when the model returns `FINAL` and exposes the final content without the agent envelope.
- [ ] The loop force-finalizes when max iterations or context budget is reached.
- [ ] If the model returns unparseable output, the behavior is deterministic and covered by tests.
- [ ] Unit tests cover final response, tool call, duplicate command, max iteration, context budget, and malformed model output.

## Blocked by

None - can start immediately

