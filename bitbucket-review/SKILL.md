---
name: bitbucket-review
description: Review Bitbucket Server pull requests by reusing this repository's BitbucketReviewSkill wrapper around PR-Agent. Use when the user wants to review, describe, improve, or webhook-process Bitbucket Server PRs through an agent skill folder.
---

# Bitbucket Review

Use this skill to run AI-assisted review workflows for Bitbucket Server / Data Center pull requests from this
repository. It wraps the implementation in `pr_agent.skills.bitbucket_review` and reuses PR-Agent's existing
`/review`, `/describe`, `/improve`, and related command handling.

## Preconditions

- Run from the repository root.
- Install the project dependencies for this repo.
- Configure Bitbucket and model credentials through environment variables or `.pr_agent.toml`.
- Do not write tokens or secrets into repository files.

Required Bitbucket configuration:

```bash
BITBUCKET_SERVER__URL=https://bitbucket.example.com
BITBUCKET_SERVER__BEARER_TOKEN=replace-with-token
```

Required model configuration:

```bash
CONFIG__GIT_PROVIDER=bitbucket_server
CONFIG__MODEL=openai/local-review-model
OPENAI__API_BASE=http://127.0.0.1:8000/v1
OPENAI__KEY=local-api-key
OPENAI_API_KEY=local-api-key
```

## Manual PR Review

Run one command:

```bash
python -m pr_agent.skills.bitbucket_review.skill review \
  --pr-url https://bitbucket.example.com/projects/PROJ/repos/repo/pull-requests/123 \
  --commands review
```

Run several commands:

```bash
python -m pr_agent.skills.bitbucket_review.skill review \
  --pr-url https://bitbucket.example.com/projects/PROJ/repos/repo/pull-requests/123 \
  --commands review describe improve
```

## Webhook Mode

Start the webhook server:

```bash
python -m pr_agent.skills.bitbucket_review.skill start-webhook
```

Configure Bitbucket Server to send pull request opened, updated, and commented events to:

```text
http://your-host:3000/webhook
```

Use `WEBHOOK_SECRET` when Bitbucket is configured to sign webhook payloads.

## Connection Check

```bash
python -m pr_agent.skills.bitbucket_review.skill test-connection
```

## Python API

```python
import asyncio
from pr_agent.skills.bitbucket_review import BitbucketReviewSkill

async def main():
    skill = BitbucketReviewSkill()
    result = await skill.review_pr(
        "https://bitbucket.example.com/projects/PROJ/repos/repo/pull-requests/123",
        commands=["review", "describe", "improve"],
    )
    print(result)

asyncio.run(main())
```

## Notes For Agents

- Prefer the Python module entry points above instead of reimplementing Bitbucket API calls.
- Use `review_pr` for direct reviews and `start-webhook` for long-running server mode.
- Pass command names without leading slash: `review`, `describe`, `improve`.
- Configure agentic repository search through `[agentic_review]`; see `docs/AGENTIC_REVIEW.md`.
